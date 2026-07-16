from .config import ollama_client

class LLM():
    def __init__(self, model : str):
        self.model = model
        self.calls = 0
    def get_answer(self, query):
        self.calls += 1
        response = ollama_client.chat(model=self.model,messages=[
                    {'role': 'user', 'content': query}
                    ]
                )
        response = response['message']['content']
        return response
