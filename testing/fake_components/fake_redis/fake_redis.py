import json
import uuid
from semantic_caching.cache_entry import CacheEntry
from semantic_caching.vector_store_services.vector_store_services import VectorStore, VectorSearchResult
from utils.cosine_similarity import cosine_similarity
from .fake_redis_client import fake_redis_client
from numpy import ndarray


class FakeRedisService(VectorStore):
    def __init__(self, client = fake_redis_client, dimension : int = 3):
        self.client = client
        self.dimension = dimension
        self.status = "Redis has connected successfully"

    def add_entry(self, entry : CacheEntry):
        cache_id = f"cache:{str(uuid.uuid4())}"

        data = {
            "question" : entry.question,
            "embedding" : entry.embedding,
            "answer" : entry.answer,
            "time" : str(entry.current_time),
            "ttl" : entry.ttl_seconds
        }

        self.client.hset(key=cache_id, mapping=data)

        return cache_id
    
    def get_entry(self, identifier : str):
        return self.client.hgetall(key = identifier)
    
    def get_size(self)->int:
        return len(self.client.storage.keys())
    
    def empty_database(self):
        self.client.storage.clear()

    def search(self, query_embedding : ndarray, threshold : float):
        max : float = 0.0
        key_to_return : str = ""
        for key in self.client.storage.keys():
            similarity = cosine_similarity(query_embedding, self.client.storage[key]["embedding"])
            if similarity > threshold:
                if similarity > max:
                    max = similarity
                    key_to_return = key
        vector_search_result = VectorSearchResult(
                        answer = self.client.storage[key_to_return].answer,
                        question = self.client.storage[key_to_return].question,
                        score= max,
                        identifier = key_to_return,
                        time = self.client.storage[key_to_return].time,
                        ttl=self.ttl(key_to_return)
                    )
        return vector_search_result
    

    def ttl(self, identifier : str):
        return self.client.storage[identifier]["ttl"]