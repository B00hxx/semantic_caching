import pytest
import numpy as np
from semantic_caching.config import MODELS, ollama_client, redis_client
from semantic_caching.llm_services.ollama_service import OllamaLLM
from semantic_caching.embedding_services.ollama_embedding import OllamaEmbeddingModel
from semantic_caching.cosine_sim import cosine_similarity
from semantic_caching.semantic_caching import SemanticCaching
from semantic_caching.vector_store_services.redis_service import RedisService

QUESTION = "what is the capital of france?"
REFORMULATED_QUESTION = "what is France's capital?"
ANOTHER_QUESTION = "how many stars are there in the milky way?"

@pytest.fixture
def create_ollama_llm():
    return  OllamaLLM(client=ollama_client, model_name=MODELS["chat"])

@pytest.fixture
def create_ollama_embedding():
    return OllamaEmbeddingModel(client=ollama_client, embedding_model=MODELS["emb"])

@pytest.fixture
def create_redis_store():
    return RedisService(client=redis_client)

@pytest.fixture
def create_pipeline(create_ollama_llm ,create_ollama_embedding, create_redis_store):
    return SemanticCaching(llm_model=create_ollama_llm, embedding_model=create_ollama_embedding, vector_store=create_redis_store)

def test_llm(create_ollama_llm):
    answer = create_ollama_llm.generate(query = "what is the capital of france")
    assert answer



def test_embedding(create_ollama_embedding):
    embedding = create_ollama_embedding.embed(query=QUESTION)
    assert isinstance(embedding, np.ndarray)
    assert len(embedding) > 0
    reformulated_emb = create_ollama_embedding.embed(query=REFORMULATED_QUESTION)
    assert cosine_similarity(embedding, reformulated_emb) > 0.9

def test_pipeline(create_pipeline):
    create_pipeline.vector_store.empty_database()
    assert create_pipeline.llm.calls == 0
    answer = create_pipeline.get_answers(query=QUESTION)
    assert answer["cache_hit"] == False
    assert create_pipeline.llm.calls == 1
    answer_2 = create_pipeline.get_answers(query=QUESTION)
    assert answer_2["cache_hit"] == True
    assert create_pipeline.llm.calls == 1
    answer_3 = create_pipeline.get_answers(query=REFORMULATED_QUESTION)
    assert answer_3["cache_hit"] == True
    assert create_pipeline.llm.calls == 1
    answer_4 = create_pipeline.get_answers(query=ANOTHER_QUESTION)
    assert answer_4["cache_hit"] == False
    assert create_pipeline.llm.calls == 2