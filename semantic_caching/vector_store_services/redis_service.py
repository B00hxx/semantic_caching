import redis
import json
import uuid
import numpy as np
from redis.commands.search.field import TagField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from ..cache_entry import CacheEntry
from .vector_store_services import VectorStore

class RedisService(VectorStore):
    def __init__(self, client : redis.Redis, dimension : int):
        self.client = client
        self.status = "Redis has connected successfully" if self.client.ping() else "There might be an issue, check the docker container ya baha!"
        self.dimension = dimension
    def create_index(self):
        schema = (
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE" : "FLOAT32",
                    "DIM" : self.dimension,
                    "DISTANCE_METRIC" : "COSINE",
                    "M": 16,
                    "EF_CONSTRUCTION": 200
                }
            )
        )
        definition = IndexDefinition(
            prefix=["cache:"],
            index_type=IndexType.HASH
        )
        self.client.ft("cache_index").create_index(
            schema,
            definition=definition
        )

    def add_entry(self, entry : CacheEntry):
        cache_id = f"cache:{str(uuid.uuid4())}" 
        self.client.hset(
            cache_id,
            mapping={
                "question" : entry.question,
                "embedding" : entry.embedding.astype(np.float32).tobytes(),
                "answer" : entry.answer,
                "time" : str(entry.current_time)
            }
        )
        return cache_id
    
    def get_entry(self, identifier : str):
        return self.client.hgetall(identifier)
    
    def get_size(self)->int:
        return self.client.dbsize()

    def get_everything(self)->list:
        entries = []
        for key in self.client.scan_iter("cache:*"):
            data = self.client.get(key)
            if data:
                entries.append(json.loads(data))
        return entries
    
    def empty_database(self):
        self.client.flushall()
        print("cleaned!")
