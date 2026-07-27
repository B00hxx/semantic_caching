from semantic_caching.embedding_services.embedding_service import Embedder
import numpy as np

class FakeEmbedder(Embedder):
    def __init__(self, model="fake_emb"):
        self.model = model
    
    async def embed(self, query: str) -> np.ndarray:
        query_lower = query.lower().strip()
        embedding_map = {
            "hello": np.array([1.0, 0.0, 0.0]),           
            "hi": np.array([0.95, 0.05, 0.01]),           
            "hey": np.array([0.94, 0.06, 0.02]),          
            "baha": np.array([0.0, 1.0, 0.0]),            
            "random": np.array([0.3, np.sqrt(0.91), 0.0]),
        }
        
        if query_lower in embedding_map:
            return embedding_map[query_lower]
        return np.array([0.5, 0.5, 0.0])