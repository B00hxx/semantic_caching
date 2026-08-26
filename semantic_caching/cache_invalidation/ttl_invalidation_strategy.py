from datetime import datetime, timezone
from .cache_invalidation_strategy import CacheInvalidationStrategy
from ..cache_entry import CacheEntry


class TTLInvalidationStrategy(CacheInvalidationStrategy):

    def __init__(self, ttl_seconds: int):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than 0")
        self.ttl_seconds = ttl_seconds

    async def should_invalidate_entry(self, entry: CacheEntry) -> bool:
        now = datetime.now(timezone.utc)
        age = (now - entry.created_at).total_seconds()
        return age >= self.ttl_seconds