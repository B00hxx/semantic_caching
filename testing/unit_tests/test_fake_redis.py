import pytest
from testing.fake_components.fake_redis import FakeRedisService
from testing.fake_components.cache_entry import CacheEntry

@pytest.fixture
def create_redis():
    return FakeRedisService()

def test_redis_started(create_redis):
    assert create_redis.status == "Redis has connected successfully"

def test_redis_behavior(create_redis):
    fake_entry = CacheEntry("what is the capital of france?", [0,0,1], "Paris")
    assert not create_redis.storage
    create_redis.add_entry(fake_entry)
    assert create_redis.get_size() == 1
    stored_entry = next(iter(create_redis.storage.values()))

    assert stored_entry["question"] == "what is the capital of france?"
    assert stored_entry["answer"] == "Paris"
    assert stored_entry["embedding"] == [0, 0, 1]

    create_redis.empty_database()
    assert create_redis.get_size() == 0


