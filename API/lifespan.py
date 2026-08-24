import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from config import settings
from semantic_caching.semantic_caching import SemanticCaching
from semantic_caching.llm_services.fake_llm_to_deploy import FakeLLMToDeploy
from semantic_caching.vector_store_services.redis_service import RedisService
from semantic_caching.query import QueryProcessor
from semantic_caching.llm_services.lite_llm_service import LiteLLMService
from semantic_caching.embedding_services.litellm_embedding_service import LiteLLMEmbedder
from semantic_caching.postgres_service.postgres_service import PostgresService
from semantic_caching.cache_invalidation.ttl_invalidation_strategy import TTLInvalidationStrategy
from semantic_caching.cache_invalidation.inactivity_invalidation_strategy import InactivityInvalidationStrategy
from semantic_caching.cache_invalidation.hit_count_invalidation_strategy import HitCountInvalidationStrategy
from semantic_caching.cache_eviction.lru_eviction_strategy import LRUEvictionStrategy
from semantic_caching.cache_eviction.lfu_eviction_strategy import LFUEvictionStrategy
from semantic_caching.cache_eviction.fifo_eviction_strategy import FIFOEvictionStrategy
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

async def invalidation_loop(cache, interval_seconds: int):
    while True:
        try:
            invalidated = await cache.invalidate_entries()

            logger.info(
                "Cache invalidation completed: %d entries invalidated",
                invalidated
            )

        except Exception:
            logger.exception("Cache invalidation failed")

        await asyncio.sleep(interval_seconds)

async def eviction_loop(cache, interval_seconds: int, max_size: int):
    while True:
        try:
            evicted = await cache.evict_entries(max_size=max_size)
            logger.info(
                "Cache eviction completed: %d entries evicted",
                evicted
            )
        except Exception:
            logger.exception("Cache eviction failed")
        await asyncio.sleep(interval_seconds)

@asynccontextmanager
async def lifespan(app : FastAPI):
    redis_client = settings.redis_client.get_client()
    
    ttl_redis = RedisService(client=redis_client, dimension=1024, prefix="lite_ttl")
    inactivity_redis = RedisService(client=redis_client, dimension=1024, prefix="lite_inactivity")
    hit_count_redis = RedisService(client=redis_client, dimension=1024, prefix="lite_hit_count")

    testing_fake_redis = RedisService(client=redis_client, dimension=1024, prefix="fake_cache")
    query_processor = QueryProcessor()
    postgres_service = await settings.postgres_service.get_service()

    await testing_fake_redis.initialize()
    await ttl_redis.initialize()
    await inactivity_redis.initialize()
    await hit_count_redis.initialize()

    #Eviction strategies
    lru_eviction_strategy = LRUEvictionStrategy()
    lfu_eviction_strategy = LFUEvictionStrategy()
    fifo_eviction_strategy = FIFOEvictionStrategy()
    
    #LLMs
    lite_llm_service = LiteLLMService(
        api_key= settings.lite_llm_settings.api_key,
        model_name= settings.lite_llm_settings.model_name,
        link="http://litellm:4000"
    )
    fake_llm = FakeLLMToDeploy()
    
    

    #embedding services
    litellm_embedding_service = LiteLLMEmbedder(api_key = settings.lite_llm_settings.embedding_model_key, model_name = settings.lite_llm_settings.embedding_model_name, link="http://litellm:4000", embedding_dimension=settings.lite_llm_settings.embedding_model_dimension)
    
    
    #cache invalidation
    ttl_invalidation_strategy = TTLInvalidationStrategy(ttl_seconds=60)
    inactivity_invalidation_strategy = InactivityInvalidationStrategy(inactivity_seconds=60)
    hit_count_invalidation_strategy = HitCountInvalidationStrategy(min_hit_count=2)
    
    #Cache
    fake_testing = SemanticCaching(llm_model=fake_llm, embedding_model=litellm_embedding_service, vector_store=testing_fake_redis, threshold=0.95, query_processor=query_processor, namespace="fake_test")
    
    ttl_cache = SemanticCaching(
        llm_model=lite_llm_service,
        embedding_model=litellm_embedding_service,
        vector_store=ttl_redis,
        query_processor=query_processor,
        threshold=0.8,
        postgres=postgres_service,
        namespace="ttl",
        invalidation_strategy=ttl_invalidation_strategy,
        eviction_strategy=lru_eviction_strategy
    )

    inactivity_cache = SemanticCaching(
        llm_model=lite_llm_service,
        embedding_model=litellm_embedding_service,
        vector_store=inactivity_redis,
        query_processor=query_processor,
        threshold=0.8,
        postgres=postgres_service,
        namespace="inactivity",
        invalidation_strategy=inactivity_invalidation_strategy,
        eviction_strategy=lfu_eviction_strategy
    )

    hit_count_cache = SemanticCaching(
        llm_model=lite_llm_service,
        embedding_model=litellm_embedding_service,
        vector_store=hit_count_redis,
        query_processor=query_processor,
        threshold=0.8,
        postgres=postgres_service,
        namespace="hit_count",
        invalidation_strategy=hit_count_invalidation_strategy,
        eviction_strategy=fifo_eviction_strategy
    )
    
    
    await ttl_cache.initialize(limit=10)
    await inactivity_cache.initialize(limit=10)
    await hit_count_cache.initialize(limit=10)
    
    app.state.ttl_cache = ttl_cache
    app.state.inactivity_cache = inactivity_cache
    app.state.hit_count_cache = hit_count_cache
    app.state.lite_testing = ttl_cache
    app.state.redis_client = redis_client
    app.state.fake_testing = fake_testing
    app.state.postgres_service = postgres_service


    ttl_invalidation_task = asyncio.create_task(
    invalidation_loop(
        app.state.ttl_cache,
        interval_seconds=settings.cache_invalidation_interval
    )
)

    inactivity_invalidation_task = asyncio.create_task(
        invalidation_loop(
            app.state.inactivity_cache,
            interval_seconds=settings.cache_invalidation_interval
        )
    )

    hit_count_invalidation_task = asyncio.create_task(
        invalidation_loop(
            app.state.hit_count_cache,
            interval_seconds=settings.cache_invalidation_interval
        )
    )
    ttl_eviction_task = asyncio.create_task(
    eviction_loop(
        app.state.ttl_cache,
        interval_seconds=settings.cache_eviction_interval,
        max_size=100
        )
    )

    inactivity_eviction_task = asyncio.create_task(
        eviction_loop(
            app.state.inactivity_cache,
            interval_seconds=settings.cache_eviction_interval,
            max_size=100
            )
    )

    hit_count_eviction_task = asyncio.create_task(
        eviction_loop(
            app.state.hit_count_cache,
            interval_seconds=settings.cache_eviction_interval,
            max_size=100
        )
    )
    
    yield
    load_dotenv()
    try:
        feature_flag = settings.delete_on_shutdown
        if feature_flag:
            await app.state.ttl_cache.vector_store.empty_database()
            await app.state.inactivity_cache.vector_store.empty_database()
            await app.state.hit_count_cache.vector_store.empty_database()
            logger.info("All cache entries were wiped out")
    
    except Exception as exc:
        logger.info(f"Shutdown cleanup skipped: {exc}")
    finally:
        try:
            await redis_client.aclose()
        except Exception as exc:
            print(f"Redis client close skipped: {exc}")
        try:
            await postgres_service.close()
        except Exception as exc:
            print(f"PostgreSQL close skipped: {exc}")
        tasks = (
            ttl_invalidation_task,
            inactivity_invalidation_task,
            hit_count_invalidation_task,
            ttl_eviction_task,
            inactivity_eviction_task,
            hit_count_eviction_task,
        )

        for task in tasks:
            task.cancel()

        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass