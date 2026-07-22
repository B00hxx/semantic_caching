import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from ..config import settings
from ..semantic_caching.semantic_caching import SemanticCaching
from ..semantic_caching.llm_services.ollama_service import OllamaLLM
from ..semantic_caching.embedding_services.ollama_embedding import OllamaEmbeddingModel
from ..semantic_caching.vector_store_services.redis_service import RedisService
from dotenv import load_dotenv


MODELS = {
    "chat" : "qwen2.5:0.5b",
    "emb" : "qwen3-embedding:0.6b"
}

@asynccontextmanager
async def lifespan(app : FastAPI):
    redis_client = settings.redis_client.get_client()
    ollama_client = settings.ollama_client.get_client()

    testing_llm = OllamaLLM(client=ollama_client, model_name=MODELS["chat"])
    testing_embedding_model = OllamaEmbeddingModel(client=ollama_client, embedding_model=MODELS["emb"])
    testing_redis = RedisService(client=redis_client, dimension=1024)

    testing = SemanticCaching(llm_model=testing_llm, embedding_model=testing_embedding_model, vector_store=testing_redis, threshold=0.8)
    
    app.state.semantic_caching_service = testing
    print("Started the pipeline with success!")
    
    yield
    load_dotenv()
    feature_flag = (os.getenv("DELETE_ON_SHUTDOWN").lower() == "true")
    if feature_flag:
        app.state.semantic_caching_service.vector_store.empty_database()
        print("The database is clear!")
    else:
        print("keeping the database!")