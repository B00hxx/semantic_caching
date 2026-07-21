from abc import ABC, abstractmethod
from .vector_search_result import VectorSearchResult
#from cache_entry import CacheEntry

class VectorStore(ABC):
    @abstractmethod
    def add_entry(self, entry):
        """Abstract method to add entries to vector store"""
        pass
    @abstractmethod
    def get_entry(self, identifier : str):
        """Abstract method to retrieve an entry from vector store"""
        pass
    @abstractmethod
    def get_size(self) -> int:
        """Method to get the size of cache"""
        pass
    @abstractmethod
    def empty_database(self):
        """Method to lowkey drop table"""
        pass
    @abstractmethod
    def search(self, query_embedding, threshold : float) -> VectorSearchResult:
        """Searching through the vector db for closest match"""
        pass
    @abstractmethod
    def ttl(self, identifier : str):
        """Method to get back the time to live of an entry"""
        pass


