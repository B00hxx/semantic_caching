import copy

class FakeRedisClient:
    def __init__(self):
        self.storage = {}

    async def hset(self, key: str, mapping: dict) -> None:
        self.storage[key] = copy.deepcopy(mapping)

    async def hgetall(self, key: str) -> dict:
        return copy.deepcopy(self.storage.get(key, {}))

    async def delete(self, key: str) -> None:
        self.storage.pop(key, None)

    async def ttl(self, key: str):
        return None
