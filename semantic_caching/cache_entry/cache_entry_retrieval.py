from .cache_entry import CacheEntry
from uuid import UUID

class CacheEntryForRetrieval(CacheEntry):
    def __init__(self, 
                 question : str,
                 embedding : list[float], 
                 answer : str, 
                 ttl_seconds : int = 3600, 
                 id : UUID | None = None, 
                 namespace : str = "default"):
        super().__init__(id = id
                    ,question=question,
                    embedding=embedding,
                    answer=answer,
                    ttl_seconds=ttl_seconds,)
        if not namespace:
            raise ValueError("namespace cannot be empty")
        self.namespace = namespace
        