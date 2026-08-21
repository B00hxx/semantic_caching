from abc import ABC, abstractmethod
from ..cache_entry.cache_entry_retrieval import CacheEntryForRetrieval
class CacheInvalidationStrategy(ABC):
    @abstractmethod
    async def should_invalidate_entry(self, entry : CacheEntryForRetrieval) -> bool:
        pass

