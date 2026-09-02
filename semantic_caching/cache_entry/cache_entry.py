from datetime import datetime, timezone
from uuid import UUID, uuid4

class CacheEntry:
    def __init__(self, 
                 question : str,
                 answer : str, 
                 embedding : list[float], 
                 embedding_model : str | None = None,
                 embedding_dimension : int | None = None,
                 id : UUID | None = None, 
                 created_at: datetime | None = None,
                 hit_count : int = 0,
                 last_hit_at : datetime | None = None,
                 last_accessed_at : datetime | None = None,
                 evicted : bool = False,
                 invalidated : bool = False,
                 namespace : str | None = None,):
        
        if not namespace:
            raise ValueError("namespace cannot be empty")
        
        self.id = id or uuid4()
        self.question = question
        self.embedding = embedding
        self.answer = answer
        self.namespace = namespace
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension
        self.created_at = created_at or datetime.now(timezone.utc)
        self.hit_count = hit_count
        self.last_hit_at = last_hit_at
        self.last_accessed_at = last_accessed_at
        self.evicted = evicted
        self.invalidated = invalidated 
