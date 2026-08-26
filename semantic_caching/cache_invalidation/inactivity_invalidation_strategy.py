from datetime import datetime, timezone
from .cache_invalidation_strategy import CacheInvalidationStrategy
from ..cache_entry import CacheEntry


class InactivityInvalidationStrategy(CacheInvalidationStrategy):

    def __init__(self, inactivity_seconds: int):
        if inactivity_seconds <= 0:
            raise ValueError(
                "inactivity_seconds must be greater than 0"
            )
        self.inactivity_seconds = inactivity_seconds

    async def should_invalidate_entry(self, entry: CacheEntry) -> bool:
        now = datetime.now(timezone.utc)
        last_activity = (entry.last_accessed_at or entry.created_at)
        inactivity_duration = (now - last_activity).total_seconds()
        return inactivity_duration >= self.inactivity_seconds