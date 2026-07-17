import pytest
import numpy as np
from semantic_caching.config import MODELS
from semantic_caching.llm_services.llm_service import LLM
from semantic_caching.embedding_services.embedding_service import Embedder
from semantic_caching.cosine_sim import cosine_similarity
from semantic_caching.semantic_caching import SemanticCaching


QUESTION = "what is the capital of france?"
REFORMULATED_QUESTION = "what is France's capital?"
ANOTHER_QUESTION = "how many stars are there in the milky way?"

@pytest.fixture
def create_llm():
    return LLM(MODELS["chat"])

@pytest.fixture
def create_embedding():
    return Embedder(MODELS["emb"])

@pytest.fixture
def create_pipeline():
    return SemanticCaching(MODELS["chat"], MODELS["emb"])

def test_llm(create_llm):
    answer = create_llm.get_answer("what is the capital of france")
    assert answer

def test_embedding(create_embedding):
    embedding = create_embedding.get_embedding(query=QUESTION)
    assert isinstance(embedding, np.ndarray)
    assert len(embedding) > 0
    reformulated_emb = create_embedding.get_embedding(query=REFORMULATED_QUESTION)
    assert cosine_similarity(embedding, reformulated_emb) > 0.9

def test_pipeline(create_pipeline):
    create_pipeline.redis.empty_database()
    assert create_pipeline.llm.calls == 0
    answer = create_pipeline.get_answers(prompt=QUESTION)
    assert answer["cache_hit"] == False
    assert create_pipeline.llm.calls == 1
    answer_2 = create_pipeline.get_answers(prompt=QUESTION)
    assert answer_2["cache_hit"] == True
    assert create_pipeline.llm.calls == 1
    answer_3 = create_pipeline.get_answers(prompt=REFORMULATED_QUESTION)
    assert answer_3["cache_hit"] == True
    assert create_pipeline.llm.calls == 1
    answer_4 = create_pipeline.get_answers(prompt=ANOTHER_QUESTION)
    assert answer_4["cache_hit"] == False
    assert create_pipeline.llm.calls == 2

