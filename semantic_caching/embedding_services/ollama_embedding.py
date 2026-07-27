from .embedding_service import Embedder
import ollama
import numpy as np
import asyncio

class OllamaEmbeddingModel(Embedder):
    def __init__(self, client, embedding_model : str):
        self.embedding_model = embedding_model
        self.client = client
    async def embed(self, query : str) -> np.ndarray:
        embedded_dictionary = await self.client.embed(model=self.embedding_model,input=query)
        embedded_query = np.squeeze(np.asarray(embedded_dictionary["embeddings"]))
        return embedded_query
