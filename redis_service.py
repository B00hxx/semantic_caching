import json
import uuid
from cache_entry import CacheEntry
from config import redis_client


class RedisService():
    def __init__(self, client):
        self.client = client
        self.status = redis_client.ping()
    def add_entry(self, entry : CacheEntry):
        cache_id = str(uuid.uuid4())
        print(cache_id)
        data = {
            "question" : entry.question,
            "embedding" : entry.embedding,
            "answer" : entry.answer
        }
        self.client.set(
            f"cache:{cache_id}",
            json.dumps(data)
        )
        return f"cache:{cache_id}"
    def get_entry(self, identifier : str):
        return self.client.get(identifier)



testing = RedisService(client=redis_client)
print(testing.status)
test_entry = CacheEntry("hello?", [0,1,2], "baha?")
id = testing.add_entry(test_entry)
print(testing.get_entry(id))