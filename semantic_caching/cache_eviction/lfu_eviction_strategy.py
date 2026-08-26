from .cache_eviction_strategy import CacheEvictionStrategy
from ..cache_entry import CacheEntry


class LFUEvictionStrategy(CacheEvictionStrategy):
    async def select_entries_for_eviction(self, entries: list[CacheEntry], number_to_evict: int) -> list[CacheEntry]:
        if number_to_evict <= 0:
            return []
        sorted_entries = sorted(
            entries,
            key=lambda entry: entry.hit_count
        )
        return sorted_entries[:number_to_evict]