from .cache_entry import CacheEntry
from uuid import UUID
from datetime import datetime

class CacheEntryForPersistence(CacheEntry):
    def __init__(
        self,
        embedding_model: str,
        embedding_dimension: int,
        question: str,
        embedding: list[float],
        answer: str,
        namespace: str,
        hit_count: int = 0,
        ttl_seconds: int = 3600,
        id: UUID | None = None,
        created_at: datetime | None = None,
    ):
        super().__init__(
            question=question,
            embedding=embedding,
            answer=answer,
            ttl_seconds=ttl_seconds,
            id=id,
            created_at=created_at,
        )

        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension
        self.namespace = namespace
        self.hit_count = hit_count