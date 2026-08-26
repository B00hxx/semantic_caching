import asyncpg
import asyncio
from uuid import UUID
from pgvector.asyncpg import register_vector
from ..cache_entry import CacheEntry

class PostgresService:
    def __init__(self, host : str, database : str, user : str, password : str, port : int = 5432):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool = None
    
    async def initialize(self) -> None:
        self.pool = await asyncpg.create_pool(host=self.host, 
                                              port=self.port, 
                                              database=self.database, 
                                              user=self.user, 
                                              password=self.password, 
                                              init=register_vector,)
    
    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def save_entry(self, entry: CacheEntry):
        async with self.pool.acquire() as connection:
            await connection.execute(
            """
            INSERT INTO cache_entries (
                id,
                question,
                embedding,
                embedding_model,
                embedding_dimension,
                answer,
                namespace,
                created_at,
                hit_count,
                last_hit_at,
                last_accessed_at,
                evicted,
                invalidated
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13);
            """,
            entry.id,
            entry.question,
            entry.embedding,
            entry.embedding_model,
            entry.embedding_dimension,
            entry.answer,
            entry.namespace,
            entry.created_at,
            entry.hit_count,
            entry.last_hit_at,
            entry.last_accessed_at,
            entry.evicted,
            entry.invalidated
        )
    async def get_top_entries(self, 
                              embedding_model: str, 
                              embedding_dimension: int, 
                              namespace: str, 
                              limit: int) -> list[CacheEntry]:
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(
            """
            SELECT
                id,
                question,
                embedding,
                embedding_model,
                embedding_dimension,
                answer,
                namespace,
                created_at,
                hit_count,
                last_hit_at,
                last_accessed_at,
                evicted,
                invalidated
                FROM cache_entries
                WHERE embedding_model = $1
                AND embedding_dimension = $2
                AND namespace = $3
                AND evicted = FALSE
                AND invalidated = FALSE
                ORDER BY hit_count DESC
                LIMIT $4;
            """,
                embedding_model,
                embedding_dimension,
                namespace,
                limit,
        )
            return [
            CacheEntry(
                id=row["id"],
                question=row["question"],
                embedding=row["embedding"].to_list(),
                answer=row["answer"],
                embedding_model=row["embedding_model"],
                embedding_dimension=row["embedding_dimension"],
                namespace=row["namespace"],
                hit_count=row["hit_count"],
                created_at=row["created_at"],
                last_hit_at=row["last_hit_at"],
                last_accessed_at=row["last_accessed_at"],
                evicted=row["evicted"],
                invalidated=row["invalidated"]
            )
            for row in rows
        ]

    async def update_hit_count(self, id : UUID):
        async with self.pool.acquire() as connection:
            await connection.execute(
            """
            UPDATE cache_entries
            SET
                hit_count = hit_count + 1,
                last_hit_at = NOW(),
                last_accessed_at = NOW()
            WHERE id = $1;
            """,
            id
        )
    async def mark_evicted(self, id: UUID, strategy: str) -> None:
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE cache_entries
                SET evicted_at = NOW(), eviction_strategy = $2, evicted = TRUE
                WHERE id = $1;
                """,
                id,
                strategy
            )

    async def mark_invalidated(self, id: UUID, strategy: str) -> None:
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE cache_entries
                SET invalidated_at = NOW(), invalidation_strategy = $2, invalidated = TRUE
                WHERE id = $1;
                """,
                id,
                strategy
            )