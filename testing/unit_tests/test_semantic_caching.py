import pytest
from semantic_caching.semantic_caching import SemanticCaching
from fake_components.settings import fake_redis_service, fake_llm_service, fake_embedding_service

@pytest.fixture
def create_selective_semantic_layer():
    return SemanticCaching(llm_model=fake_llm_service, embedding_model=fake_embedding_service, vector_store=fake_redis_service, threshold=0.9)

@pytest.fixture
def create_non_selective_semantic_layer():
    return SemanticCaching(llm_model=fake_llm_service, embedding_model=fake_embedding_service, vector_store=fake_redis_service, threshold=0.3)

def test_semantic_pipeline(create_semantic_layer):
    answer_dict = create_semantic_layer.get_answers("hello")
    assert answer_dict["cache_hit"] == False
    assert create_semantic_layer.llm.calls == 1
    answer_dict = create_semantic_layer.get_answers("hello")
    assert answer_dict["cache_hit"] == True
    assert create_semantic_layer.llm.calls == 1

def test_true_positive(create_semantic_layer):
    """With vectors that are super close we can guarantee to get the right hit even for a small thresshold"""
    create_semantic_layer.get_answers("hello!")
    assert create_semantic_layer.llm.calls == 1
    create_semantic_layer.get_answers("hi!")
    assert create_semantic_layer.llm.calls == 1

def test_false_cache_hit(create_very_small_semantic_layer):
    """the 2 words are not the same semantically but their embedding is close so for a small thrsshold we end up getting a respinse from the cache which is the wrong behavior"""
    create_very_small_semantic_layer.get_answers("hello!")
    assert create_very_small_semantic_layer.llm.calls == 1
    create_very_small_semantic_layer.get_answers("random")
    assert create_very_small_semantic_layer.llm.calls == 1

def test_better_threshold(create_selective_semantic_layer):
    """for the same as above and with a more selective thresshold we end up getting the right behavior which is calling the LLM"""
    create_selective_semantic_layer.get_answers("hello!")
    assert create_selective_semantic_layer.llm.calls == 1
    create_selective_semantic_layer.get_answers("random")
    assert create_selective_semantic_layer.llm.calls == 2

