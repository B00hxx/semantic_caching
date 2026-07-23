from .fake_redis.fake_redis import FakeRedisService
from .fake_llm import Fake_LLM
from .fake_embedding import FakeEmbedder

fake_redis_service = FakeRedisService()
fake_llm_service = Fake_LLM()
fake_embedding_service = FakeEmbedder()
