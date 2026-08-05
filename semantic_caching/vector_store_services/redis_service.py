import uuid
import numpy as np
import redis.asyncio as redis
from redis.commands.search.field import VectorField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from ..cache_entry import CacheEntry
from .vector_store_services import VectorStore
from .vector_search_result import VectorSearchResult


class RedisService(VectorStore):
    def __init__(self, client: redis.Redis, dimension: int, prefix : str, namespace: str = "default"):
        self.client = client
        self.status = "Not initialized yet!"
        self.dimension = dimension
        self.prefix = prefix
        if not namespace:
            raise ValueError("namespace cannot be empty")
        self.namespace = namespace
        # Removed self.create_index() because __init__ cannot await async functions

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
            # Awaited async index creation
            await self.client.ft(f"{self.prefix}_index").create_index(
                schema,
                definition=definition
            )
        except Exception as e:
            print("INDEX CREATION LOG:", e)

    async def add_entry(self, entry: CacheEntry) -> str:
        cache_id = f"{self.prefix}:{str(uuid.uuid4())}" 
        await self.client.hset(
            cache_id,
            mapping={
                "question": entry.question,
                "embedding": entry.embedding.astype(np.float32).tobytes(),
                "answer": entry.answer,
                "time": str(entry.created_at),
                "ttl": entry.ttl_seconds,
                "namespace" : self.namespace
            }
        )
        await self.client.expire(cache_id, entry.ttl_seconds)
        return cache_id
    
    async def get_entry(self, identifier: str):
        return await self.client.hgetall(identifier)
    
    async def get_size(self) -> int:
        count = 0
        async for _ in self.client.scan_iter(match=f"{self.prefix}:*"):
            count += 1
        return count
    
    async def empty_database(self) -> None:
        keys = [key async for key in self.client.scan_iter(match=f"{self.prefix}:*")]
        if keys:
            await self.client.delete(*keys)
        print(f"Cleared {len(keys)} cache keys!")
    
    async def search(self, query_embedding: np.ndarray, threshold: float):
        query = (
            Query(
                "(@namespace:{$ns})=>[KNN 1 @embedding $vec AS score]"
            )
            .sort_by("score")
            .return_fields("question", "answer", "score", "time")
            .dialect(2)
        )
        results = await self.client.ft(f"{self.prefix}_index").search(
            query,
            query_params={
                "vec": query_embedding.astype(np.float32).tobytes(),
                "ns": self.namespace,
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
                time = result.time,
                ttl = await self.ttl(result.id),
                namespace=self.namespace
            )
            return vector_search_result
        return None

    async def ttl(self, identifier: str):
        return await self.client.ttl(identifier)