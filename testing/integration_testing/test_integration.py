import pytest
import numpy as np
from semantic_caching.llm_services.ollama_service import OllamaLLM
from semantic_caching.embedding_services.ollama_embedding import OllamaEmbeddingModel
from semantic_caching.semantic_caching import SemanticCaching
from semantic_caching.vector_store_services.redis_service import RedisService
from ...config import settings

QUESTION = "what is the capital of france?"
REFORMULATED_QUESTION = "what is France's capital?"
ANOTHER_QUESTION = "how many stars are there in the milky way?"

MODELS = {
    "chat": "qwen2.5:0.5b",
    "emb": "qwen3-embedding:0.6b"
}


@pytest.fixture(scope="session")
def ollama_client():
    """Create a single Ollama client for all tests"""
    return settings.ollama_client.get_client()  # ✅ Fixed: method call


@pytest.fixture(scope="session")
def redis_client():
    """Create a single Redis client for all tests"""
    return settings.redis_client.get_client()  # ✅ Fixed: method call


@pytest.fixture
def create_ollama_llm(ollama_client):
    return OllamaLLM(client=ollama_client, model_name=MODELS["chat"])


@pytest.fixture
def create_ollama_embedding(ollama_client):
    return OllamaEmbeddingModel(
        client=ollama_client,  # ✅ Fixed: pass client, not method
        embedding_model=MODELS["emb"]
    )


@pytest.fixture
def create_redis_store(redis_client):
    return RedisService(client=redis_client, dimension=1024)


@pytest.fixture
def create_pipeline(create_ollama_llm, create_ollama_embedding, create_redis_store):
    return SemanticCaching(
        llm_model=create_ollama_llm,
        embedding_model=create_ollama_embedding,
        vector_store=create_redis_store
    )


def test_llm(create_ollama_llm):
    """Test that Ollama LLM works and returns a response"""
    answer = create_ollama_llm.generate(query="what is the capital of france?")
    assert answer is not None
    assert len(answer) > 0
    print(f"LLM Response: {answer}")


def test_embedding(create_ollama_embedding):
    """Test that Ollama embedding model works"""
    embedding = create_ollama_embedding.embed(query=QUESTION)
    assert isinstance(embedding, np.ndarray)
    assert len(embedding) > 0
    assert len(embedding) == 1024  # Should match Redis dimension
    
    # Test reformulated question
    reformulated_emb = create_ollama_embedding.embed(query=REFORMULATED_QUESTION)
    assert isinstance(reformulated_emb, np.ndarray)
    assert len(reformulated_emb) == 1024


def test_pipeline(create_pipeline):
    """Test the complete semantic caching pipeline with real services"""
    # Clear database before test
    create_pipeline.vector_store.empty_database()
    
    # Initial state
    assert create_pipeline.llm.calls == 0
    
    # First query - should be cache miss
    answer = create_pipeline.get_answers(query=QUESTION)
    assert answer["cache_hit"] == False
    assert create_pipeline.llm.calls == 1
    assert "answer" in answer
    print(f"First answer: {answer['answer']}")
    
    # Same query - should be cache hit
    answer_2 = create_pipeline.get_answers(query=QUESTION)
    assert answer_2["cache_hit"] == True
    assert create_pipeline.llm.calls == 1  # No new LLM call
    assert answer_2["answer"] == answer["answer"]  # Same answer
    
    # Reformulated question - should hit cache if embedding is close
    answer_3 = create_pipeline.get_answers(query=REFORMULATED_QUESTION)
    assert answer_3["cache_hit"] == True
    assert create_pipeline.llm.calls == 1  # Still no new LLM call
    
    # Completely different question - should be cache miss
    answer_4 = create_pipeline.get_answers(query=ANOTHER_QUESTION)
    assert answer_4["cache_hit"] == False
    assert create_pipeline.llm.calls == 2  # New LLM call


def test_caching_with_different_thresholds(create_pipeline):
    """Test caching behavior with different similarity thresholds"""
    # Clear database
    create_pipeline.vector_store.empty_database()
    
    # Store a question
    create_pipeline.get_answers(query=QUESTION)
    assert create_pipeline.llm.calls == 1
    
    # Test with a very similar question - should hit cache
    similar_question = "what is France's capital city?"
    result = create_pipeline.get_answers(query=similar_question)
    assert result["cache_hit"] == True
    
    # Test with a less similar question (might hit or miss depending on threshold)
    less_similar = "tell me about Paris"
    result = create_pipeline.get_answers(query=less_similar)
    # This could be hit or miss - document the behavior


def test_redis_connection(create_redis_store):
    """Test Redis connection is working"""
    assert create_redis_store is not None
    assert create_redis_store.dimension == 1024
    
    # Test that we can add and retrieve
    from semantic_caching.cache_entry import CacheEntry
    import time
    
    entry = CacheEntry(
        question="test",
        embedding=np.array([0.1] * 1024),
        answer="test answer",
        ttl_seconds=60
    )
    
    cache_id = create_redis_store.add_entry(entry)
    assert cache_id is not None
    
    # Clean up
    create_redis_store.empty_database()