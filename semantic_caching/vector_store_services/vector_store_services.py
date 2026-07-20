from abc import ABC, abstractmethod
from .vector_search_result import VectorSearchResult
from semantic_caching.cache_entry import CacheEntry

class VectorStore(ABC):
    @abstractmethod
    def add_entry(self, entry : CacheEntry):
        """Abstract method to add entries to vector store"""
        pass
    def get_entry(self, identifier : str):
        """Abstract method to retrieve an entry from vector store"""
        pass
    def get_size(self) -> int:
        """Method to get the size of cache"""
        pass
    def empty_database(self):
        """Method to lowkey drop table"""
        pass
    def search(self, query_embedding, threshold : float) -> VectorSearchResult:
        """Searching through the vector db for closest match"""
        pass
    def ttl(self, identifier : str):
        """Method to get back the time to live of an entry"""
        pass


