import pytest
from datetime import datetime, timezone, timedelta
from semantic_caching.cache_invalidation.ttl_invalidation_strategy import TTLInvalidationStrategy
from semantic_caching.cache_invalidation.inactivity_invalidation_strategy import InactivityInvalidationStrategy
from semantic_caching.cache_invalidation.hit_count_invalidation_strategy import HitCountInvalidationStrategy
from semantic_caching.cache_entry import CacheEntry


@pytest.mark.asyncio
async def test_ttl_invalidation_strategy():
    strategy = TTLInvalidationStrategy(ttl_seconds=60)

    # Fresh entry (created just now)
    fresh_entry = CacheEntry(
        question="What is TTL?",
        embedding=[0.1, 0.2, 0.3],
        answer="Time to live",
        created_at=datetime.now(timezone.utc),
        namespace="test_namespace"
    )
    assert await strategy.should_invalidate_entry(fresh_entry) is False

    # Old entry (created 100 seconds ago)
    old_entry = CacheEntry(
        question="What is TTL?",
        embedding=[0.1, 0.2, 0.3],
        answer="Time to live",
        created_at=datetime.now(timezone.utc) - timedelta(seconds=100),
        namespace="test_namespace"
    )
    assert await strategy.should_invalidate_entry(old_entry) is True


@pytest.mark.asyncio
async def test_ttl_invalidation_validation():
    with pytest.raises(ValueError):
        TTLInvalidationStrategy(ttl_seconds=0)

    with pytest.raises(ValueError):
        TTLInvalidationStrategy(ttl_seconds=-10)


@pytest.mark.asyncio
async def test_inactivity_invalidation_strategy():
    strategy = InactivityInvalidationStrategy(inactivity_seconds=60)

    # Recently accessed entry
    active_entry = CacheEntry(
        question="What is Inactivity?",
        embedding=[0.1, 0.2, 0.3],
        answer="Inactivity test",
        created_at=datetime.now(timezone.utc) - timedelta(seconds=200),
        last_accessed_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        namespace="test_namespace"
    )
    assert await strategy.should_invalidate_entry(active_entry) is False

    # Stale inactive entry
    inactive_entry = CacheEntry(
        question="What is Inactivity?",
        embedding=[0.1, 0.2, 0.3],
        answer="Inactivity test",
        created_at=datetime.now(timezone.utc) - timedelta(seconds=200),
        last_hit_at=datetime.now(timezone.utc) - timedelta(seconds=120),
        namespace="test_namespace"
    )
    assert await strategy.should_invalidate_entry(inactive_entry) is True


@pytest.mark.asyncio
async def test_hit_count_invalidation_strategy():
    strategy = HitCountInvalidationStrategy(min_hit_count=5)

    # Entry with insufficient hits
    low_hit_entry = CacheEntry(
        question="What is hit count?",
        embedding=[0.1, 0.2, 0.3],
        answer="Hit count test",
        hit_count=3,
        namespace="test_namespace"
    )
    assert await strategy.should_invalidate_entry(low_hit_entry) is True

    # Entry with sufficient hits
    high_hit_entry = CacheEntry(
        question="What is hit count?",
        embedding=[0.1, 0.2, 0.3],
        answer="Hit count test",
        hit_count=10,
        namespace="test_namespace"
    )
    assert await strategy.should_invalidate_entry(high_hit_entry) is False
