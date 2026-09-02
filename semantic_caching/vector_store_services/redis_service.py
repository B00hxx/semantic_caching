import uuid
import numpy as np
import redis.asyncio as redis
from redis.commands.search.field import VectorField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from .vector_store_services import VectorStore
from .vector_search_result import VectorSearchResult
from ..cache_entry import CacheEntry 
from datetime import datetime, timezone

class RedisService(VectorStore):
    def __init__(self, client: redis.Redis, dimension: int, prefix : str):
        self.client = client
        self.status = "Not initialized yet!"
        self.dimension = dimension
        self.prefix = prefix
    
    async def initialize(self) -> None:
        """Call this method in lifespan after creating the RedisService instance."""
        try:
            if await self.client.ping():
                self.status = "Redis has connected successfully"
        except Exception as e:
            self.status = f"Redis connection issue: {e}"
            
        await self.create_index()

    async def create_index(self):
        schema = (
            TagField("namespace"),
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.dimension,
                    "DISTANCE_METRIC": "COSINE",
                    "M": 16,
                    "EF_CONSTRUCTION": 200
                }
            ),
        )
        definition = IndexDefinition(
            prefix=[f"{self.prefix}:"],
            index_type=IndexType.HASH
        )
        try:
            await self.client.ft(f"{self.prefix}_index").create_index(
                schema,
                definition=definition
            )
        except Exception as e:
            print("INDEX CREATION LOG:", e)

    async def add_entry(self, entry: CacheEntry) -> str:
        cache_id = f"{self.prefix}:{entry.id}"
        await self.client.hset(
        cache_id,
        mapping={
            "question": entry.question,
            "embedding": np.asarray(entry.embedding, dtype=np.float32).tobytes(),
            "answer": entry.answer,
            "created_at": entry.created_at.isoformat(),
            "namespace": entry.namespace,
            "hit_count": entry.hit_count,
            "last_hit_at": (entry.last_hit_at.isoformat() if entry.last_hit_at else ""),
            "last_accessed_at": (entry.last_accessed_at.isoformat() if entry.last_accessed_at else ""),
        }
    )
        return cache_id
    
    
    async def get_entry(self, identifier: uuid.UUID):
        cache_id = f"{self.prefix}:{identifier}"
        return await self.client.hgetall(cache_id)
    
    async def get_size(self) -> int:
        count = 0
        async for _ in self.client.scan_iter(match=f"{self.prefix}:*"):
            count += 1
        return count
    
    async def empty_database(self) -> int:
        keys = [
            key async for key in self.client.scan_iter(
                match=f"{self.prefix}:*"
            )   
        ]
        if keys:
            await self.client.delete(*keys)
        return len(keys)
    
    async def search(self, query_embedding: np.ndarray, threshold: float, namespace : str):
        query = (
            Query(
                "(@namespace:{$ns})=>[KNN 1 @embedding $vec AS score]"
            )
            .sort_by("score")
            .return_fields("question", "answer", "score", "created_at", "namespace")
            .dialect(2)
        )
        results = await self.client.ft(f"{self.prefix}_index").search(
            query,
            query_params={
                "vec": np.asarray(query_embedding, dtype=np.float32).tobytes(),
                "ns": namespace,
            }
        )
        if not results.docs:
            return None
            
        result = results.docs[0]
        score = float(result.score)
        
        if score <= 1 - threshold:
            vector_search_result = VectorSearchResult(
                answer=result.answer,
                question=result.question,
                score= 1 - score,
                identifier = result.id,
                created_at = result.created_at,
                namespace= result.namespace
            )
            return vector_search_result
        return None
    
    
    async def update_access_metadata(self, identifier: str):
        now = datetime.now(timezone.utc).isoformat()
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hincrby(identifier, "hit_count", 1)
            pipe.hset(
                identifier,
                mapping={
                    "last_hit_at": now,
                    "last_accessed_at": now,
                    }
                )
            await pipe.execute()
    
    async def delete_entry(self, identifier: uuid.UUID):
        cache_id = f"{self.prefix}:{identifier}"
        return await self.client.delete(cache_id)
    
    async def get_all_entries(self) -> list[CacheEntry]:
        entries = []
        async for key in self.client.scan_iter(match=f"{self.prefix}:*"):
            data = await self.client.hgetall(key)
            if not data:
                continue
            entry = CacheEntry(
                id=uuid.UUID(key.decode().split(":")[-1]),
                question=data[b"question"].decode(),
                embedding=np.frombuffer(
                    data[b"embedding"],
                    dtype=np.float32
                ).tolist(),
                answer=data[b"answer"].decode(),
                created_at=datetime.fromisoformat(
                    data[b"created_at"].decode()
                ),
                namespace=data[b"namespace"].decode(),
                hit_count=int(data.get(b"hit_count", 0)),
                last_hit_at=(
                    datetime.fromisoformat(data[b"last_hit_at"].decode())
                    if data.get(b"last_hit_at")
                    else None
                ),
                last_accessed_at=(
                    datetime.fromisoformat(data[b"last_accessed_at"].decode())
                    if data.get(b"last_accessed_at")
                    else None
                ),
            )
            entries.append(entry)

        return entries