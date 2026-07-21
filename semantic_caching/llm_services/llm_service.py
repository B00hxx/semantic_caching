from abc import ABC, abstractmethod

class LLM(ABC):
    """Class that defines the expected behavior of multiple LLM providers"""
    @abstractmethod
    def generate(self, query : str) -> str:
        """Abstract method to get back an answer from LLM provider"""
        pass
