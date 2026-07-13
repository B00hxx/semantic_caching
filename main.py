from config import MODELS
from semantic_caching import SemanticCaching
from timing import timer_decorator

testing = SemanticCaching(MODELS["chat"], MODELS["emb"])
testing.redis.empty_database()

@timer_decorator
def process():
    prompt = input("what do u wanna know? ")
    data = testing.get_answers(prompt=prompt)
    if data[0]:
        print("used the semantic caching")
        print("================================================")
        print(data[1])
    else:
        print("used the LLM")
        print("================================================")
        print(data[1])

while True:
    process()