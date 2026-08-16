import os
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
from dotenv import load_dotenv

@asynccontextmanager
async def lifespan(app : FastAPI):
    redis_client = settings.redis_client.get_client()
    lite_redis = RedisService(client=redis_client, dimension=1024, prefix="lite")
    testing_fake_redis = RedisService(client=redis_client, dimension=1024, prefix="fake_cache")
    query_processor = QueryProcessor()
    postgres_service = await settings.postgres_service.get_service()

    #LLMs
    lite_llm_service = LiteLLMService(
        api_key= settings.lite_llm_settings.api_key,
        model_name= settings.lite_llm_settings.model_name,
        link="http://litellm:4000"
    )
    fake_llm = FakeLLMToDeploy()
    
    

    #embedding services
    litellm_embedding_service = LiteLLMEmbedder(
        api_key = settings.lite_llm_settings.embedding_model_key,
        model_name = settings.lite_llm_settings.embedding_model_name,
        link="http://litellm:4000",
        embedding_dimension=settings.lite_llm_settings.embedding_model_dimension
    )
    
    
    await testing_fake_redis.initialize()
    await lite_redis.initialize()
    
    

    fake_testing = SemanticCaching(llm_model=fake_llm, 
                                   embedding_model=litellm_embedding_service, 
                                   vector_store=testing_fake_redis, 
                                   threshold=0.95, 
                                   query_processor=query_processor,
                                   namespace="fake_test",
                                   )
    lite_testing = SemanticCaching(llm_model=lite_llm_service, 
                                   embedding_model=litellm_embedding_service, 
                                   vector_store=lite_redis, 
                                   query_processor=query_processor, 
                                   threshold=0.8,
                                   postgres=postgres_service)
    
    app.state.redis_client = redis_client
    app.state.fake_testing = fake_testing
    app.state.lite_testing = lite_testing

    print("Started the pipeline with success!")
    
    yield
    load_dotenv()
    try:
        feature_flag = (os.getenv("DELETE_ON_SHUTDOWN", "false").lower() == "true")
        if feature_flag:
            await app.state.semantic_caching_service.vector_store.empty_database()
            print("The database is clear!")
        else:
            print("keeping the database!")
    except Exception as exc:
        print(f"Shutdown cleanup skipped: {exc}")
    finally:
        try:
            await redis_client.aclose()
        except Exception as exc:
            print(f"Redis client close skipped: {exc}")