from semantic_caching.embedding_services.embedding_service import Embedder
import numpy as np

class FakeEmbedder(Embedder):
    def __init__(self, model = "fake_emb"):
        self.model = model
    
    def embed(self, query : str)->np.ndarray:
        if query == "hello!":
            return np.array([1,0,0])
        elif query == "hi!":
            return np.array([0.95, 0.05, 0.01])
        elif query == "baha":
            return np.array([0,1,0])
        elif query == "random":
            return np.array([0.3, np.sqrt(0.91), 0])
    
