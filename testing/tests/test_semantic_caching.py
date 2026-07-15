import pytest
from testing.fake_components.fake_semantic_caching import SemanticCaching

@pytest.fixture
def create_semantic_layer():
    return SemanticCaching()

@pytest.fixture
def create_selective_semantic_layer():
    return SemanticCaching(threshold=0.9)

@pytest.fixture
def create_very_small_semantic_layer():
    return SemanticCaching(threshold=0.29)

def test_basic(create_semantic_layer):
    assert create_semantic_layer.saved_answers == []

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

