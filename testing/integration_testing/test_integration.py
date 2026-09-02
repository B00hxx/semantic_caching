import asyncio

import pytest
import pytest_asyncio

from datetime import datetime, timedelta, timezone

from config import settings

from semantic_caching.vector_store_services.redis_service import RedisService
from semantic_caching.semantic_caching import SemanticCaching
from semantic_caching.query import QueryProcessor
from semantic_caching.cache_entry import CacheEntry

from semantic_caching.llm_services.lite_llm_service import LiteLLMService
from semantic_caching.embedding_services.litellm_embedding_service import (
    LiteLLMEmbedder,
)

from semantic_caching.cache_invalidation.ttl_invalidation_strategy import (
    TTLInvalidationStrategy,
)
from semantic_caching.cache_invalidation.inactivity_invalidation_strategy import (
    InactivityInvalidationStrategy,
)
from semantic_caching.cache_invalidation.hit_count_invalidation_strategy import (
    HitCountInvalidationStrategy,
)

from semantic_caching.cache_eviction.lru_eviction_strategy import (
    LRUEvictionStrategy,
)
from semantic_caching.cache_eviction.lfu_eviction_strategy import (
    LFUEvictionStrategy,
)
from semantic_caching.cache_eviction.fifo_eviction_strategy import (
    FIFOEvictionStrategy,
)


# ============================================================
# Fixtures
# ============================================================


@pytest_asyncio.fixture
async def postgres_instance():
    postgres_service = await settings.postgres_service.get_service()

    try:
        yield postgres_service
    finally:
        await postgres_service.close()


@pytest_asyncio.fixture
async def redis_client():
    client = settings.redis_client.get_client()

    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def query_processor():
    return QueryProcessor()


@pytest.fixture
def llm():
    return LiteLLMService(
        api_key=settings.lite_llm_settings.api_key,
        model_name=settings.lite_llm_settings.model_name,
    )


@pytest.fixture
def embedder():
    return LiteLLMEmbedder(
        api_key=settings.lite_llm_settings.embedding_model_key,
        model_name=settings.lite_llm_settings.embedding_model_name,
        embedding_dimension=settings.lite_llm_settings.embedding_model_dimension,
    )


@pytest_asyncio.fixture
async def redis_store(redis_client):
    store = RedisService(
        client=redis_client,
        dimension=settings.lite_llm_settings.embedding_model_dimension,
        prefix="integration_test",
    )

    await store.empty_database()
    await store.initialize()

    yield store

    await store.empty_database()


@pytest_asyncio.fixture
async def cache(
    redis_store,
    postgres_instance,
    llm,
    embedder,
    query_processor,
):
    cache = SemanticCaching(
        llm_model=llm,
        embedding_model=embedder,
        vector_store=redis_store,
        cache_name="integration_test",
        query_processor=query_processor,
        threshold=0.5,
        namespace="integration_test",
        postgres=postgres_instance,
    )

    yield cache

    await redis_store.empty_database()


# ============================================================
# Helpers
# ============================================================


async def populate_entries(
    redis_store,
    namespace,
    count=5,
):
    """
    Populate Redis directly with deterministic entries.

    This is intentionally NOT using SemanticCaching.get_answers()
    because eviction/invalidation tests should not depend on
    embeddings, semantic similarity, or the LLM.
    """

    dimension = settings.lite_llm_settings.embedding_model_dimension
    now = datetime.now(timezone.utc)

    entries = []

    for i in range(count):
        entry = CacheEntry(
            question=f"test question {i}",
            answer=f"test answer {i}",
            embedding=[0.1] * dimension,
            embedding_model="test-model",
            embedding_dimension=dimension,
            namespace=namespace,
            created_at=now + timedelta(seconds=i),
            hit_count=1,
        )

        await redis_store.add_entry(entry)
        entries.append(entry)

    return entries


# ============================================================
# Infrastructure
# ============================================================


@pytest.mark.asyncio
async def test_postgres(postgres_instance):
    result = await postgres_instance.test_connection()

    assert result is True


@pytest.mark.asyncio
async def test_redis(redis_client):
    result = await redis_client.ping()

    assert result is True


@pytest.mark.asyncio
async def test_presidio(query_processor):
    result = await query_processor.process(
        "My email is test@example.com"
    )

    assert isinstance(result, list)

    assert any(
        span["entity_type"] == "EMAIL_ADDRESS"
        for span in result
    )


@pytest.mark.asyncio
async def test_llm(llm):
    result = await llm.generate(
        "Say exactly: hello"
    )

    assert isinstance(result, str)
    assert len(result.strip()) > 0


@pytest.mark.asyncio
async def test_embedding(embedder):
    result = await embedder.embed(
        "This is an integration test sentence."
    )

    assert isinstance(result, list)

    assert len(result) == (
        settings.lite_llm_settings.embedding_model_dimension
    )

    assert all(
        isinstance(value, float)
        for value in result
    )


# ============================================================
# Basic Cache Behaviour
# ============================================================


@pytest.mark.asyncio
async def test_cache_miss(
    cache,
    redis_store,
):
    query = "What is machine learning?"

    result = await cache.get_answers(query)

    assert result["cache_hit"] is False
    assert result["answer"]
    assert "cosine_distance" in result

    assert await redis_store.get_size() == 1


@pytest.mark.asyncio
async def test_cache_hit(
    cache,
    redis_store,
):
    query = "What is machine learning?"

    first = await cache.get_answers(query)
    second = await cache.get_answers(query)

    assert first["cache_hit"] is False

    assert second["cache_hit"] is True
    assert second["answer"] == first["answer"]

    assert await redis_store.get_size() == 1


@pytest.mark.asyncio
async def test_semantic_cache_hit(cache):
    first = await cache.get_answers(
        "What is machine learning?"
    )

    second = await cache.get_answers(
        "Can you explain machine learning?"
    )

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True

    assert second["answer"] == first["answer"]


# ============================================================
# PII / Cache Bypass
# ============================================================


@pytest.mark.asyncio
async def test_pii_bypasses_cache(
    cache,
    redis_store,
):
    query = "My email is test@example.com"

    result = await cache.get_answers(query)

    assert result["cache_hit"] is False
    assert result["cache_bypassed"] is True
    assert result["answer"]

    assert await redis_store.get_size() == 0


# ============================================================
# PostgreSQL Persistence
# ============================================================


@pytest.mark.asyncio
async def test_cache_entry_persisted_to_postgres(
    cache,
    postgres_instance,
):
    query = "What is artificial intelligence?"

    result = await cache.get_answers(query)

    assert result["cache_hit"] is False

    entries = await postgres_instance.get_top_entries(
        embedding_model=settings.lite_llm_settings.embedding_model_name,
        embedding_dimension=(
            settings.lite_llm_settings.embedding_model_dimension
        ),
        namespace="integration_test",
        limit=10,
    )

    assert len(entries) >= 1

    assert any(
        entry.question == query
        for entry in entries
    )


@pytest.mark.asyncio
async def test_initialize_loads_postgres_entries(
    cache,
    redis_store,
):
    query = "Explain neural networks."

    await cache.get_answers(query)

    assert await redis_store.get_size() == 1

    await redis_store.empty_database()

    assert await redis_store.get_size() == 0

    loaded = await cache.initialize(limit=10)

    assert loaded >= 1
    assert await redis_store.get_size() >= 1

    result = await cache.get_answers(query)

    assert result["cache_hit"] is True


# ============================================================
# TTL Invalidation
# ============================================================


@pytest.mark.asyncio
async def test_ttl_invalidation(
    redis_store,
    postgres_instance,
):
    strategy = TTLInvalidationStrategy(
        ttl_seconds=60
    )

    cache = SemanticCaching(
        llm_model=None,
        embedding_model=None,
        vector_store=redis_store,
        cache_name="ttl_test",
        invalidation_strategy=strategy,
        namespace="ttl_test",
        postgres=postgres_instance,
    )

    entries = await populate_entries(
        redis_store,
        "ttl_test",
        count=1,
    )

    old_time = datetime.now(timezone.utc) - timedelta(
        minutes=10
    )

    await redis_store.client.hset(
        f"{redis_store.prefix}:{entries[0].id}",
        "created_at",
        old_time.isoformat(),
    )

    assert await redis_store.get_size() == 1

    invalidated = await cache.invalidate_entries()

    assert invalidated == 1
    assert await redis_store.get_size() == 0


# ============================================================
# Inactivity Invalidation
# ============================================================


@pytest.mark.asyncio
async def test_inactivity_invalidation(
    redis_store,
    postgres_instance,
):
    strategy = InactivityInvalidationStrategy(
        inactivity_seconds=60
    )

    cache = SemanticCaching(
        llm_model=None,
        embedding_model=None,
        vector_store=redis_store,
        cache_name="inactivity_test",
        invalidation_strategy=strategy,
        namespace="inactivity_test",
        postgres=postgres_instance,
    )

    entries = await populate_entries(
        redis_store,
        "inactivity_test",
        count=1,
    )

    old_time = datetime.now(timezone.utc) - timedelta(
        minutes=10
    )

    await redis_store.client.hset(
        f"{redis_store.prefix}:{entries[0].id}",
        "last_accessed_at",
        old_time.isoformat(),
    )

    assert await redis_store.get_size() == 1

    invalidated = await cache.invalidate_entries()

    assert invalidated == 1
    assert await redis_store.get_size() == 0


# ============================================================
# Hit Count Invalidation
# ============================================================


@pytest.mark.asyncio
async def test_hit_count_invalidation(
    redis_store,
    postgres_instance,
):
    strategy = HitCountInvalidationStrategy(
        min_hit_count=2
    )

    cache = SemanticCaching(
        llm_model=None,
        embedding_model=None,
        vector_store=redis_store,
        cache_name="hit_count_test",
        invalidation_strategy=strategy,
        namespace="hit_count_test",
        postgres=postgres_instance,
    )

    entries = await populate_entries(
        redis_store,
        "hit_count_test",
        count=1,
    )

    assert await redis_store.get_size() == 1

    # Entry starts with hit_count=1.
    # Therefore it should be invalidated because
    # min_hit_count is 2.
    invalidated = await cache.invalidate_entries()

    assert invalidated == 1
    assert await redis_store.get_size() == 0


# ============================================================
# FIFO Eviction
# ============================================================


@pytest.mark.asyncio
async def test_fifo_eviction(
    redis_store,
    postgres_instance,
):
    strategy = FIFOEvictionStrategy()

    cache = SemanticCaching(
        llm_model=None,
        embedding_model=None,
        vector_store=redis_store,
        cache_name="fifo_test",
        eviction_strategy=strategy,
        namespace="fifo_test",
        postgres=postgres_instance,
    )

    entries = await populate_entries(
        redis_store,
        "fifo_test",
        count=5,
    )

    assert await redis_store.get_size() == 5

    selected = await strategy.select_entries_for_eviction(
        entries,
        2,
    )

    assert [entry.id for entry in selected] == [
        entries[0].id,
        entries[1].id,
    ]

    evicted = await cache.evict_entries(
        max_size=3
    )

    assert evicted == 2
    assert await redis_store.get_size() == 3


# ============================================================
# LFU Eviction
# ============================================================


@pytest.mark.asyncio
async def test_lfu_eviction(
    redis_store,
    postgres_instance,
):
    strategy = LFUEvictionStrategy()

    cache = SemanticCaching(
        llm_model=None,
        embedding_model=None,
        vector_store=redis_store,
        cache_name="lfu_test",
        eviction_strategy=strategy,
        namespace="lfu_test",
        postgres=postgres_instance,
    )

    entries = await populate_entries(
        redis_store,
        "lfu_test",
        count=5,
    )

    assert await redis_store.get_size() == 5

    # Desired hit counts:
    #
    # entry 0 -> 10
    # entry 1 -> 8
    # entry 2 -> 1
    # entry 3 -> 2
    # entry 4 -> 5
    #
    # Therefore entry 2 and entry 3 should be evicted.

    hit_counts = [10, 8, 1, 2, 5]

    for entry, hit_count in zip(entries, hit_counts):
        await redis_store.client.hset(
            f"{redis_store.prefix}:{entry.id}",
            "hit_count",
            hit_count,
        )

    actual_entries = await redis_store.get_all_entries()

    selected = await strategy.select_entries_for_eviction(
        actual_entries,
        2,
    )

    selected_ids = {
        entry.id
        for entry in selected
    }

    assert selected_ids == {
        entries[2].id,
        entries[3].id,
    }

    evicted = await cache.evict_entries(
        max_size=3
    )

    assert evicted == 2
    assert await redis_store.get_size() == 3


# ============================================================
# LRU Eviction
# ============================================================


@pytest.mark.asyncio
async def test_lru_eviction(
    redis_store,
    postgres_instance,
):
    strategy = LRUEvictionStrategy()

    cache = SemanticCaching(
        llm_model=None,
        embedding_model=None,
        vector_store=redis_store,
        cache_name="lru_test",
        eviction_strategy=strategy,
        namespace="lru_test",
        postgres=postgres_instance,
    )

    entries = await populate_entries(
        redis_store,
        "lru_test",
        count=5,
    )

    assert await redis_store.get_size() == 5

    base_time = datetime.now(timezone.utc)

    timestamps = [
        base_time - timedelta(minutes=10),
        base_time - timedelta(minutes=9),
        base_time - timedelta(minutes=5),
        base_time - timedelta(minutes=3),
        base_time,
    ]

    for entry, timestamp in zip(
        entries,
        timestamps,
    ):
        await redis_store.client.hset(
            f"{redis_store.prefix}:{entry.id}",
            "last_accessed_at",
            timestamp.isoformat(),
        )

    actual_entries = await redis_store.get_all_entries()

    selected = await strategy.select_entries_for_eviction(
        actual_entries,
        2,
    )

    selected_ids = {
        entry.id
        for entry in selected
    }

    assert selected_ids == {
        entries[0].id,
        entries[1].id,
    }

    evicted = await cache.evict_entries(
        max_size=3
    )

    assert evicted == 2
    assert await redis_store.get_size() == 3


# ============================================================
# Eviction Edge Cases
# ============================================================


@pytest.mark.asyncio
async def test_eviction_does_nothing_when_under_limit(
    cache,
    redis_store,
):
    await cache.get_answers(
        "What is Kubernetes?"
    )

    assert await redis_store.get_size() == 1

    evicted = await cache.evict_entries(
        max_size=10
    )

    assert evicted == 0
    assert await redis_store.get_size() == 1


@pytest.mark.asyncio
async def test_eviction_rejects_negative_max_size(
    cache,
):
    with pytest.raises(ValueError):
        await cache.evict_entries(
            max_size=-1
        )


# ============================================================
# Strategy Edge Cases
# ============================================================


@pytest.mark.asyncio
async def test_fifo_returns_empty_for_zero_entries(
    redis_store,
):
    strategy = FIFOEvictionStrategy()

    entries = await redis_store.get_all_entries()

    selected = await strategy.select_entries_for_eviction(
        entries,
        0,
    )

    assert selected == []


@pytest.mark.asyncio
async def test_lfu_returns_empty_for_zero_entries(
    redis_store,
):
    strategy = LFUEvictionStrategy()

    entries = await redis_store.get_all_entries()

    selected = await strategy.select_entries_for_eviction(
        entries,
        0,
    )

    assert selected == []


@pytest.mark.asyncio
async def test_lru_returns_empty_for_zero_entries(
    redis_store,
):
    strategy = LRUEvictionStrategy()

    entries = await redis_store.get_all_entries()

    selected = await strategy.select_entries_for_eviction(
        entries,
        0,
    )

    assert selected == []


# ============================================================
# Full End-to-End Pipeline
# ============================================================


@pytest.mark.asyncio
async def test_full_pipeline(
    redis_store,
    postgres_instance,
    llm,
    embedder,
    query_processor,
):
    cache = SemanticCaching(
        llm_model=llm,
        embedding_model=embedder,
        vector_store=redis_store,
        cache_name="full_pipeline",
        query_processor=query_processor,
        threshold=0.5,
        namespace="full_pipeline",
        postgres=postgres_instance,
    )

    query = (
        "What is the difference between AI and machine learning?"
    )

    # --------------------------------------------------------
    # 1. First request -> cache miss -> LLM -> Redis -> Postgres
    # --------------------------------------------------------

    first = await cache.get_answers(query)

    assert first["cache_hit"] is False
    assert first["answer"]

    assert await redis_store.get_size() == 1

    # --------------------------------------------------------
    # 2. Exact same query -> cache hit
    # --------------------------------------------------------

    second = await cache.get_answers(query)

    assert second["cache_hit"] is True
    assert second["answer"] == first["answer"]

    assert await redis_store.get_size() == 1

    # --------------------------------------------------------
    # 3. Semantically similar query -> cache hit
    # --------------------------------------------------------

    third = await cache.get_answers(
        "How are artificial intelligence and machine learning different?"
    )

    assert third["cache_hit"] is True

    # --------------------------------------------------------
    # 4. PII -> bypass cache
    # --------------------------------------------------------

    pii_result = await cache.get_answers(
        "My email is test@example.com"
    )

    assert pii_result["cache_hit"] is False
    assert pii_result["cache_bypassed"] is True

    assert await redis_store.get_size() == 1

    # --------------------------------------------------------
    # 5. Simulate Redis restart
    # --------------------------------------------------------

    await redis_store.empty_database()

    assert await redis_store.get_size() == 0

    # --------------------------------------------------------
    # 6. Recover cache from PostgreSQL
    # --------------------------------------------------------

    loaded = await cache.initialize(
        limit=10
    )

    assert loaded >= 1
    assert await redis_store.get_size() >= 1

    # --------------------------------------------------------
    # 7. Recovered entry must produce cache hit
    # --------------------------------------------------------

    restored = await cache.get_answers(query)

    assert restored["cache_hit"] is True
    assert restored["answer"] == first["answer"]

    # --------------------------------------------------------
    # 8. Verify persisted entry exists
    # --------------------------------------------------------

    entries = await postgres_instance.get_top_entries(
        embedding_model=settings.lite_llm_settings.embedding_model_name,
        embedding_dimension=(
            settings.lite_llm_settings.embedding_model_dimension
        ),
        namespace="full_pipeline",
        limit=10,
    )

    assert any(
        entry.question == query
        for entry in entries
    )
