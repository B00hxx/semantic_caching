from abc import ABC, abstractmethod
from ..cache_entry import CacheEntry
class CacheInvalidationStrategy(ABC):
    @abstractmethod
    async def should_invalidate_entry(self, entry : CacheEntry) -> bool:
        pass

