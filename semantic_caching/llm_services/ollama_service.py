import ollama
from semantic_caching.config import ollama_client, MODELS
from .llm_service import LLM

class OllamaLLM(LLM):
    def __init__(self, model_name:str):
        self.model_name = model_name
    
    def generate(self, query : str):
        response = ollama_client.chat(
            model=self.model_name,
            messages=[
                    {'role': 'user', 'content': query}
                    ]
        )
        response = response['message']['content']
        return response
