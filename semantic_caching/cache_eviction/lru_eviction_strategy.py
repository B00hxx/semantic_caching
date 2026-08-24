from .cache_eviction_strategy import CacheEvictionStrategy
from ..cache_entry.cache_entry_retrieval import CacheEntryForRetrieval


class LRUEvictionStrategy(CacheEvictionStrategy):

    async def select_entries_for_eviction(self, entries: list[CacheEntryForRetrieval], number_to_evict: int) -> list[CacheEntryForRetrieval]:
        if number_to_evict <= 0:
            return []
        sorted_entries = sorted(
            entries,
            key=lambda entry: (
                entry.last_accessed_at
                if entry.last_accessed_at is not None
                else entry.created_at
            )
        )
        return sorted_entries[:number_to_evict]