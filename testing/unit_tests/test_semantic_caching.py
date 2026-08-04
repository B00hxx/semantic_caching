import pytest
from semantic_caching.semantic_caching import SemanticCaching
from ..fake_components.fake_llm import FakeLLM
from ..fake_components.fake_embedding import FakeEmbedder
from ..fake_components.fake_query_processor import FakeQueryProcessor
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
    def _create_semantic_layer(threshold=0.5, query_processor=None):
        return SemanticCaching(
            llm_model=fake_components["llm"],
            embedding_model=fake_components["embedding"],
            vector_store=fake_components["redis_service"],
            threshold=threshold,
            query_processor=query_processor
        )
    return _create_semantic_layer


@pytest.mark.asyncio
async def test_semantic_pipeline(semantic_layer_factory):
    semantic_layer = semantic_layer_factory()
    answer_dict = await semantic_layer.get_answers("hello")
    assert answer_dict["cache_hit"] is False
    assert semantic_layer.llm.calls == 1
    answer_dict = await semantic_layer.get_answers("hello")
    assert answer_dict["cache_hit"] is True
    assert semantic_layer.llm.calls == 1


@pytest.mark.asyncio
async def test_true_positive(semantic_layer_factory):
    """With vectors that are super close we can guarantee to get the right hit even for a small threshold"""
    semantic_layer = semantic_layer_factory(threshold=0.1)
    await semantic_layer.get_answers("hello")
    assert semantic_layer.llm.calls == 1
    await semantic_layer.get_answers("hi")
    assert semantic_layer.llm.calls == 1


@pytest.mark.asyncio
async def test_false_cache_hit(semantic_layer_factory):
    """With a very permissive threshold, unrelated words might incorrectly hit the cache"""
    semantic_layer = semantic_layer_factory(threshold=0.1)

    await semantic_layer.get_answers("hello")
    assert semantic_layer.llm.calls == 1

    await semantic_layer.get_answers("random")
    assert semantic_layer.llm.calls == 1


@pytest.mark.asyncio
async def test_better_threshold(semantic_layer_factory):
    """With a more selective threshold, unrelated words should miss the cache"""
    semantic_layer = semantic_layer_factory(threshold=0.9)
    await semantic_layer.get_answers("hello")
    assert semantic_layer.llm.calls == 1
    await semantic_layer.get_answers("random")
    assert semantic_layer.llm.calls == 2


@pytest.mark.asyncio
async def test_clean_query_is_cached(semantic_layer_factory):
    """A query with no sensitive entities keeps the normal cache behaviour"""
    processor = FakeQueryProcessor(entities=[])
    semantic_layer = semantic_layer_factory(query_processor=processor)

    first = await semantic_layer.get_answers("hello")
    assert first["cache_hit"] is False
    assert first["cache_bypassed"] is False

    second = await semantic_layer.get_answers("hello")
    assert second["cache_hit"] is True
    assert semantic_layer.llm.calls == 1
    assert await semantic_layer.vector_store.get_size() == 1


@pytest.mark.asyncio
async def test_sensitive_query_is_never_cached(semantic_layer_factory):
    """Detected entities collapse to one placeholder, so those queries bypass the cache"""
    processor = FakeQueryProcessor(
        entities=[{"entity_type": "CREDIT_CARD", "start": 0, "end": 4, "score": 1.0}],
        redacted_text="hello",
    )
    semantic_layer = semantic_layer_factory(query_processor=processor)

    first = await semantic_layer.get_answers("card 4111111111111111")
    assert first["cache_hit"] is False
    assert first["cache_bypassed"] is True

    # Same redacted text, different secret: must not be served the first answer.
    second = await semantic_layer.get_answers("card 5500000000000004")
    assert second["cache_hit"] is False
    assert second["cache_bypassed"] is True

    assert semantic_layer.llm.calls == 2
    assert await semantic_layer.vector_store.get_size() == 0


@pytest.mark.asyncio
async def test_sensitive_query_does_not_read_existing_entries(semantic_layer_factory):
    """A cached clean answer must not be handed to a query carrying entities"""
    clean_processor = FakeQueryProcessor(entities=[])
    semantic_layer = semantic_layer_factory(query_processor=clean_processor)
    await semantic_layer.get_answers("hello")
    assert semantic_layer.llm.calls == 1

    semantic_layer.query_processor = FakeQueryProcessor(
        entities=[{"entity_type": "PERSON", "start": 0, "end": 4, "score": 1.0}],
        redacted_text="hello",
    )
    result = await semantic_layer.get_answers("hello, I am Baha")
    assert result["cache_hit"] is False
    assert semantic_layer.llm.calls == 2
