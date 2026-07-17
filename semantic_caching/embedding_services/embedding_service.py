import ollama
import numpy as np
from ..config import ollama_client
from abc import ABC, abstractmethod



class Embedder(ABC):
    @abstractmethod
    def embed(self, query : str):
        """Abstract method to get the embedding of the queries"""
        pass
