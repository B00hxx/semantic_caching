from .cache_invalidation_strategy import CacheInvalidationStrategy
from ..cache_entry.cache_entry_retrieval import CacheEntryForRetrieval


class HitCountInvalidationStrategy(CacheInvalidationStrategy):

    def __init__(self, min_hit_count: int):
        if min_hit_count < 0:
            raise ValueError(
                "min_hit_count cannot be negative"
            )
        self.min_hit_count = min_hit_count

    async def should_invalidate_entry(self, entry: CacheEntryForRetrieval) -> bool:
        return entry.hit_count < self.min_hit_count