import json
import uuid
from .fake_redis_client import FakeRedisClient
from semantic_caching.cache_entry import CacheEntry
from semantic_caching.vector_store_services.vector_store_services import VectorStore, VectorSearchResult
from utils.cosine_similarity import cosine_similarity
from numpy import ndarray


class FakeRedisService(VectorStore):
    def __init__(self, client : FakeRedisClient, dimension : int = 3):
        self.client = client
        self.dimension = dimension
        self.status = "Redis has connected successfully"

    async def add_entry(self, entry : CacheEntry):
        cache_id = f"cache:{str(uuid.uuid4())}"

        data = {
            "question": entry.question,
            "embedding": entry.embedding,
            "answer": entry.answer,
            "time": str(entry.created_at),
            "ttl": getattr(entry, "ttl_seconds", 60),
            "namespace": getattr(entry, "namespace", "default"),
            "hit_count": getattr(entry, "hit_count", 0),
        }

        await self.client.hset(key=cache_id, mapping=data)

        return cache_id

    async def get_entry(self, identifier : str):
        return await self.client.hgetall(key = identifier)
    
    async def get_size(self)->int:
        return len(self.client.storage.keys())
    
    async def empty_database(self):
        self.client.storage.clear()

    async def search(self, query_embedding: ndarray, threshold: float, namespace: str = "default"):
        max: float = 0.0
        key_to_return: str = ""
        for key in self.client.storage.keys():
            similarity = cosine_similarity(query_embedding, self.client.storage[key]["embedding"])
            if similarity > threshold:
                if similarity > max:
                    max = similarity
                    key_to_return = key
        if key_to_return == "":
            return None
        vector_search_result = VectorSearchResult(
            answer=self.client.storage[key_to_return]["answer"],
            question=self.client.storage[key_to_return]["question"],
            score=max,
            identifier=key_to_return,
            created_at=self.client.storage[key_to_return]['time'],
            namespace=self.client.storage[key_to_return].get('namespace', namespace),
        )
        return vector_search_result

    async def update_access_metadata(self, identifier: str):
        if identifier in self.client.storage:
            self.client.storage[identifier]["hit_count"] = self.client.storage[identifier].get("hit_count", 0) + 1

    async def delete_entry(self, identifier):
        key = str(identifier)
        for k in list(self.client.storage.keys()):
            if key in k:
                del self.client.storage[k]

    async def get_all_entries(self):
        return list(self.client.storage.values())

    async def ttl(self, identifier: str):
        return await self.client.ttl(key=identifier)