from .embedding_service import Embedder
import ollama
from semantic_caching.config import ollama_client, MODELS
import numpy as np


class OllamaEmbeddingModel(Embedder):
    def __init__(self, embedding_model : str):
        self.embedding_model = embedding_model
    def embed(self, query : str) -> np.array:
        embedded_dictionary = ollama_client.embed(model=self.embedding_model,input=query)
        embedded_query = np.squeeze(np.asarray(embedded_dictionary["embeddings"]))
        return embedded_query
