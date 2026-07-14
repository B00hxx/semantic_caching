class Fake_LLM():
    def __init__(self, model = "fake_llm"):
        self.model = model
        self.calls = 0
    def get_answer(self, query):
        self.calls += 1
        if query == "hello!":
            return "what do you want?"
        elif query == "hi!":
            return "here we go"
        elif query == "baha":
            return "he's the man"
        return "fake anwswer"

