from config import settings
from semantic_caching.semantic_caching import SemanticCaching
from semantic_caching.llm_services.ollama_service import OllamaLLM
from semantic_caching.embedding_services.ollama_embedding import OllamaEmbeddingModel
from semantic_caching.vector_store_services.redis_service import RedisService
from semantic_caching.timing import timer_decorator


MODELS = {
    "chat" : "qwen2.5:0.5b",
    "emb" : "qwen3-embedding:0.6b"
}




redis_client = settings.redis_client.get_client()
ollama_client = settings.ollama_client.get_client()


testing_llm = OllamaLLM(client=ollama_client, model_name=MODELS["chat"])
testing_embedding_model = OllamaEmbeddingModel(client=ollama_client, embedding_model=MODELS["emb"])
testing_redis = RedisService(client=redis_client, dimension=1024)

testing = SemanticCaching(llm_model=testing_llm, embedding_model=testing_embedding_model, vector_store=testing_redis, threshold=0.8)




@timer_decorator
def process():
    query = input("what do u wanna know? ")
    data = testing.get_answers(query=query)
    if data["cache_hit"]:
        print("used the semantic caching")
        print("================================================")
        print(f"the similarity is basically {data["cosine_distance"]}")
        print(f"this was created at {data["time"]}")
        print(f"this answer still works for {testing.vector_store.ttl(data["id"])}")
        print(f"the answer is {data["answer"]}")
        print("================================================")

    else:
        print("used the LLM")
        print("================================================")
        print(f"this was created at {data["time"]}")
        print(f"the answer is {data["answer"]}")
        print("================================================")

if __name__ == "__main__":
    testing.vector_store.empty_database()
    while True:
        process()