import pytest
import numpy as np
from semantic_caching.llm_services.ollama_service import OllamaLLM
from semantic_caching.embedding_services.ollama_embedding import OllamaEmbeddingModel
from semantic_caching.semantic_caching import SemanticCaching
from semantic_caching.vector_store_services.redis_service import RedisService
from semantic_caching.cache_entry.cache_entry_retrieval import CacheEntryForRetrieval
from config import settings

pytestmark = pytest.mark.asyncio

QUESTION = "what is the capital of france?"
REFORMULATED_QUESTION = "what is France's capital?"
ANOTHER_QUESTION = "how many stars are there in the milky way?"


async def _resolve_ollama_models(client):
    chat_model = "qwen:0.5b"
    emb_model = "qwen3-embedding:0.6b"

    try:
        tags = await client.list()
        models = [m.model for m in tags.models] if hasattr(tags, "models") else []
        for candidate in ["qwen:0.5b", "qwen2.5:0.5b", "qwen"]:
            if any(candidate in m for m in models):
                chat_model = candidate
                break
        for candidate in ["qwen3-embedding:0.6b", "qwen3-embedding", "nomic-embed-text"]:
            if any(candidate in m for m in models):
                emb_model = candidate
                break
    except Exception:
        pass

    return chat_model, emb_model


async def _build_pipeline_components():
    try:
        ollama_client = settings.ollama_client.get_client()
        await ollama_client.list()
    except Exception as e:
        pytest.skip(f"Ollama server not reachable: {e}")

    try:
        redis_client = settings.redis_client.get_client()
        await redis_client.ping()
    except Exception as e:
        pytest.skip(f"Redis server not reachable: {e}")

    chat_model, emb_model = await _resolve_ollama_models(ollama_client)

    llm = OllamaLLM(client=ollama_client, model_name=chat_model)
    embedder = OllamaEmbeddingModel(client=ollama_client, embedding_model=emb_model)
    redis_store = RedisService(client=redis_client, dimension=1024, prefix="test_integration")
    await redis_store.initialize()

    return llm, embedder, redis_store


async def test_llm():
    """Test that Ollama LLM works and returns a response"""
    llm, _, _ = await _build_pipeline_components()
    answer = await llm.generate(query="what is the capital of france?")
    assert answer is not None
    assert len(answer) > 0
    print(f"LLM Response: {answer}")


async def test_embedding():
    """Test that Ollama embedding model works"""
    _, embedder, _ = await _build_pipeline_components()
    embedding = await embedder.embed(query=QUESTION)
    assert isinstance(embedding, np.ndarray)
    assert len(embedding) > 0
    assert len(embedding) == 1024
    reformulated_emb = await embedder.embed(query=REFORMULATED_QUESTION)
    assert isinstance(reformulated_emb, np.ndarray)
    assert len(reformulated_emb) == 1024


async def test_pipeline():
    """Test the complete semantic caching pipeline with real services"""
    llm, embedder, redis_store = await _build_pipeline_components()
    pipeline = SemanticCaching(
        llm_model=llm,
        embedding_model=embedder,
        vector_store=redis_store,
        threshold=0.8,
        namespace="test_integration",
    )

    await pipeline.vector_store.empty_database()
    assert pipeline.llm.calls == 0

    answer = await pipeline.get_answers(query=QUESTION)
    assert answer["cache_hit"] is False
    assert pipeline.llm.calls == 1
    assert "answer" in answer
    print(f"First answer: {answer['answer']}")

    answer_2 = await pipeline.get_answers(query=QUESTION)
    assert answer_2["cache_hit"] is True
    assert pipeline.llm.calls == 1
    assert answer_2["answer"] == answer["answer"]

    answer_3 = await pipeline.get_answers(query=REFORMULATED_QUESTION)
    assert answer_3["cache_hit"] is True
    assert pipeline.llm.calls == 1

    answer_4 = await pipeline.get_answers(query=ANOTHER_QUESTION)
    assert answer_4["cache_hit"] is False
    assert pipeline.llm.calls == 2

    await pipeline.vector_store.empty_database()


async def test_caching_with_different_thresholds():
    """Test caching behavior with different similarity thresholds"""
    llm, embedder, redis_store = await _build_pipeline_components()
    pipeline = SemanticCaching(
        llm_model=llm,
        embedding_model=embedder,
        vector_store=redis_store,
        threshold=0.8,
        namespace="test_integration",
    )

    await pipeline.vector_store.empty_database()
    await pipeline.get_answers(query=QUESTION)
    assert pipeline.llm.calls == 1

    similar_question = "what is France's capital city?"
    result = await pipeline.get_answers(query=similar_question)
    assert result["cache_hit"] is True

    less_similar = "tell me about Paris"
    result = await pipeline.get_answers(query=less_similar)
    assert "cache_hit" in result

    await pipeline.vector_store.empty_database()


async def test_redis_connection():
    """Test Redis connection is working"""
    _, _, redis_store = await _build_pipeline_components()
    assert redis_store is not None
    assert redis_store.dimension == 1024

    entry = CacheEntryForRetrieval(
        question="test",
        embedding=np.array([0.1] * 1024, dtype=np.float32).tolist(),
        answer="test answer",
        namespace="test_integration",
    )

    cache_id = await redis_store.add_entry(entry)
    assert cache_id is not None

    entry_data = await redis_store.get_entry(entry.id)
    assert entry_data is not None

    await redis_store.empty_database()
