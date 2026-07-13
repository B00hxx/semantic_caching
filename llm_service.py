from config import ollama_client, MODELS

class LLM():
    def __init__(self, model : str):
        self.model = model
    def get_answer(self, query):
        response = ollama_client.chat(model=self.model,messages=[
                    {'role': 'user', 'content': query}
                    ]
                )
        response = response['message']['content']
        return response
