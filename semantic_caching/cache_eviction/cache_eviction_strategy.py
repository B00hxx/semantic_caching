from abc import ABC, abstractmethod
from ..cache_entry import CacheEntry


class CacheEvictionStrategy(ABC):
    @abstractmethod
    async def select_entries_for_eviction(self, entries: list[CacheEntry], number_to_evict: int) -> list[CacheEntry]:
        """
        Select entries that should be evicted from the cache.

        Args:
            entries: Current cache entries.
            number_to_evict: Number of entries that should be removed.

        Returns:
            Entries selected for eviction.
        """
        pass