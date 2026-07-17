import ollama
from .llm_service import LLM

class OllamaLLM(LLM):
    def __init__(self, client, model_name:str):
        self.client = client
        self.model_name = model_name
        self.calls = 0
    
    def generate(self, query : str):
        self.calls += 1
        response = self.client.chat(
            model=self.model_name,
            messages=[
                    {'role': 'user', 'content': query}
                    ]
        )
        response = response['message']['content']
        return response
