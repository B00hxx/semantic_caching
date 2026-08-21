from .cache_entry import CacheEntry
from uuid import UUID
from datetime import datetime

class CacheEntryForRetrieval(CacheEntry):
    def __init__(
        self,
        question: str,
        embedding: list[float],
        answer: str,
        ttl_seconds: int = 3600,
        id: UUID | None = None,
        created_at: datetime | None = None,
        namespace: str = "default",
        hit_count: int = 0,
        last_hit_at: datetime | None = None,
        last_accessed_at: datetime | None = None,
    ):
        super().__init__(
            id=id,
            question=question,
            embedding=embedding,
            answer=answer,
            ttl_seconds=ttl_seconds,
            created_at=created_at,
        )

        if not namespace:
            raise ValueError("namespace cannot be empty")

        self.namespace = namespace
        self.hit_count = hit_count
        self.last_hit_at = last_hit_at
        self.last_accessed_at = last_accessed_at