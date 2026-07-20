from .config import MODELS, redis_client, ollama_client
from .semantic_caching import SemanticCaching
from .timing import timer_decorator
from .vector_store_services.redis_service import RedisService
from .embedding_services.ollama_embedding import OllamaEmbeddingModel
from .llm_services.ollama_service import OllamaLLM


testing_llm = OllamaLLM(client=ollama_client, model_name=MODELS["chat"])
testing_embedding_model = OllamaEmbeddingModel(client=ollama_client, embedding_model=MODELS["emb"])
testing_redis = RedisService(client=redis_client, dimension=1024)

testing = SemanticCaching(llm_model=testing_llm, embedding_model=testing_embedding_model, vector_store=testing_redis, threshold=0.8)

testing.vector_store.empty_database()



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
    while True:
        process()