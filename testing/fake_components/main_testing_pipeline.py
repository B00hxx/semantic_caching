from testing.fake_components.fake_semantic_caching import SemanticCaching
from timing import timer_decorator

testing = SemanticCaching()
testing.redis.empty_database()

@timer_decorator
def process():
    prompt = input("what do u wanna know? ")
    data = testing.get_answers(prompt=prompt)
    if data["cache_hit"]:
        print("used the semantic caching")
        print("================================================")
        print(data["similarity"])
        print(data["time"])
        print(data["answer"])
        print("================================================")

    else:
        print("used the LLM")
        print("================================================")
        print(data["time"])
        print(data["answer"])
        print("================================================")


while True:
    process()