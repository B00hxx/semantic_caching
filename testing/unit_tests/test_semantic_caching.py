import pytest
from semantic_caching.semantic_caching import SemanticCaching
from ..fake_components.fake_llm import FakeLLM
from ..fake_components.fake_embedding import FakeEmbedder
from ..fake_components.fake_redis.fake_redis_client import FakeRedisClient
from ..fake_components.fake_redis.fake_redis import FakeRedisService


@pytest.fixture
def fake_components():
    return {
        "llm": FakeLLM(),
        "embedding": FakeEmbedder(),
        "redis_service": FakeRedisService(client=FakeRedisClient())
    }


@pytest.fixture
def semantic_layer_factory(fake_components):
    def _create_semantic_layer(threshold=0.5):
        return SemanticCaching(
            llm_model=fake_components["llm"],
            embedding_model=fake_components["embedding"],
            vector_store=fake_components["redis_service"],
            threshold=threshold
        )
    return _create_semantic_layer


def test_semantic_pipeline(semantic_layer_factory):
    semantic_layer = semantic_layer_factory()
    answer_dict = semantic_layer.get_answers("hello")
    assert answer_dict["cache_hit"] == False
    assert semantic_layer.llm.calls == 1
    answer_dict = semantic_layer.get_answers("hello")
    assert answer_dict["cache_hit"] == True
    assert semantic_layer.llm.calls == 1


def test_true_positive(semantic_layer_factory):
    """With vectors that are super close we can guarantee to get the right hit even for a small threshold"""
    semantic_layer = semantic_layer_factory(threshold=0.1)
    semantic_layer.get_answers("hello")
    assert semantic_layer.llm.calls == 1
    semantic_layer.get_answers("hi")
    assert semantic_layer.llm.calls == 1


def test_false_cache_hit(semantic_layer_factory):
    """With a very permissive threshold, unrelated words might incorrectly hit the cache"""
    semantic_layer = semantic_layer_factory(threshold=0.1) 
    
    semantic_layer.get_answers("hello")
    assert semantic_layer.llm.calls == 1
    
    semantic_layer.get_answers("random")
    assert semantic_layer.llm.calls == 1


def test_better_threshold(semantic_layer_factory):
    """With a more selective threshold, unrelated words should miss the cache"""
    semantic_layer = semantic_layer_factory(threshold=0.9)
    semantic_layer.get_answers("hello")
    assert semantic_layer.llm.calls == 1
    semantic_layer.get_answers("random")
    assert semantic_layer.llm.calls == 2 