from abc import ABC, abstractmethod
from datetime import datetime, timezone
from uuid import UUID, uuid4

class CacheEntry(ABC):
    def __init__(self, question : str, embedding : list[float], answer : str, ttl_seconds : int = 3600, id : UUID | None = None, created_at: datetime | None = None):
        self.id = id or uuid4()
        self.question = question
        self.embedding = embedding
        self.answer = answer
        self.created_at = created_at or datetime.now(timezone.utc)
        self.ttl_seconds = ttl_seconds
    
