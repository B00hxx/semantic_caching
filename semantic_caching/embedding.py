import ollama
import numpy as np
from .config import ollama_client



class Embedder():
    def __init__(self, model):
        self.model = model
    def get_embedding(self, query : str)->np.array:
        embedded_thing = ollama_client.embed(model=self.model,input=query)
        embedded_query = np.squeeze(np.asarray(embedded_thing["embeddings"]))
        return embedded_query