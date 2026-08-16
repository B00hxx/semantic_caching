from abc import ABC, abstractmethod
class Embedder(ABC):
    def __init__(self, model_name: str, embedding_dimension : int):
        self.model_name = model_name
        self.embedding_dimension = embedding_dimension
        
    @abstractmethod
    async def embed(self, query : str):
        """Abstract method to get the embedding of the queries"""
        pass
