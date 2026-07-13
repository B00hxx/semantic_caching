import ollama
import numpy as np
from config import ollama_client, MODELS



class embedder():
    def __init__(self, model):
        self.model = model
    def get_embedding(self, query : str)->np.array:
        embedded_thing = ollama_client.embed(model='qwen3-embedding:0.6b',input=query)
        embedded_query = np.squeeze(np.asarray(embedded_thing["embeddings"]))
        return embedded_query