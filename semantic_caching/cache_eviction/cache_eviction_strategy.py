from abc import ABC, abstractmethod

from ..cache_entry.cache_entry_retrieval import CacheEntryForRetrieval


class CacheEvictionStrategy(ABC):

    @abstractmethod
    async def select_entries_for_eviction(self, entries: list[CacheEntryForRetrieval], number_to_evict: int) -> list[CacheEntryForRetrieval]:
        """
        Select entries that should be evicted from the cache.

        Args:
            entries: Current cache entries.
            number_to_evict: Number of entries that should be removed.

        Returns:
            Entries selected for eviction.
        """
        pass