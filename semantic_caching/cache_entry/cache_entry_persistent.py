from .cache_entry import CacheEntry
from uuid import UUID

class CacheEntryForPersistence(CacheEntry):
    def __init__(self, 
                 embedding_model : str,
                 embedding_dimension : int,
                 question : str, 
                 embedding : list[float], 
                 answer : str, 
                 namespace : str,
                 ttl_seconds : int = 3600, 
                 id : UUID | None = None,
                 ):
        super().__init__(question, embedding, answer, ttl_seconds, id)
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension
        self.namespace = namespace
    def storage_type(self):
            return "Persistent Storage"