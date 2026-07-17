from abc import ABC, abstractmethod
class Embedder(ABC):
    @abstractmethod
    def embed(self, query : str):
        """Abstract method to get the embedding of the queries"""
        pass
