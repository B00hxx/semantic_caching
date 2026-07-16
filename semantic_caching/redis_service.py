import json
import uuid
from .cache_entry import CacheEntry
class RedisService():
    def __init__(self, client):
        self.client = client
        self.status = "Redis has connected successfully" if self.client.ping() else "There might be an issue, check the docker container ya baha!"
    
    def add_entry(self, entry : CacheEntry):
        cache_id = str(uuid.uuid4())
        print(cache_id)
        data = {
            "question" : entry.question,
            "embedding" : entry.embedding,
            "answer" : entry.answer,
            "time" : str(entry.current_time)
        }
        self.client.set(
            f"cache:{cache_id}",
            json.dumps(data)
        )
        return f"cache:{cache_id}"
    
    def get_entry(self, identifier : str):
        return self.client.get(identifier)
    
    def get_everything(self)->list:
        entries = []
        for key in self.client.scan_iter("cache:*"):
            data = self.client.get(key)
            if data:
                entries.append(json.loads(data))
        return entries
    
    def get_size(self)->int:
        return self.client.dbsize()
    
    def empty_database(self):
        self.client.flushall()
        print("cleaned!")