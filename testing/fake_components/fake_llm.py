from semantic_caching.llm_services.llm_service import LLM

class Fake_LLM(LLM):
    def __init__(self, model = "fake_llm"):
        self.model = model
        self.calls = 0
    def generate(self, query):
        self.calls += 1
        if query == "hello!":
            return "what do you want?"
        elif query == "hi!":
            return "here we go"
        elif query == "baha":
            return "he's the man"
        elif query == "random":
            return "idk what to say"
