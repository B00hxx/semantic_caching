import copy

class FakeRedisClient:
    def __init__(self):
        self.storage = {}
    def hset(self, key : str, mapping : dict) -> None:
        self.storage[key] = copy.deepcopy(mapping)
        return
    def hgetall(self, key : str) -> dict:
        return copy.deepcopy(self.storage.get(key, {}))
    def delete(self, key : str) -> None:
        self.storage.pop(key, None)

fake_redis_client = FakeRedisClient()