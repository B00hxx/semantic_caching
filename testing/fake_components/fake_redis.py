import json
import uuid
from testing.fake_components.cache_entry import CacheEntry


class FakeRedisService():
    def __init__(self, client = None):
        self.client = client
        self.status = "Redis has connected successfully"
        self.storage = dict()
    def add_entry(self, entry : CacheEntry):
        cache_id = str(uuid.uuid4())
        data = {
            "question" : entry.question,
            "embedding" : entry.embedding,
            "answer" : entry.answer,
            "time" : str(entry.current_time)
        }
        self.storage[f"cache:{cache_id}"] = data
        return f"cache:{cache_id}"
    
    def get_entry(self, identifier : str):
        return self.storage.get(identifier)
    
    def get_everything(self):
        return self.storage
    
    def get_size(self)->int:
        return len(self.storage)
    
    def empty_database(self):
        self.storage.clear()