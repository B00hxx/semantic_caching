from semantic_caching.llm_services.llm_service import LLM

class FakeLLM(LLM):
    def __init__(self, model = "fake_llm"):
        self.model = model
        self.calls = 0
    def generate(self, query):
        self.calls += 1
        responses = {
            "hello": "what do you want?",
            "hi": "here we go",
            "baha": "he's the man",
            "random": "idk what to say",
        }
        return responses[query]