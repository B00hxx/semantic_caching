from abc import ABC, abstractmethod
from semantic_caching.cache_entry import CacheEntry

class VectorStore(ABC):
    @abstractmethod
    def add_entry(self, entry : CacheEntry):
        """Abstract method to add entries to vector store"""
        pass
    def get_entry(self, identifier : str):
        """Abstract method to retrieve an entry from vector store"""
        pass
    def get_everything(self) -> list:
        """Method to get the entire stored cache"""
        pass
    def get_size(self) -> int:
        """Method to get the size of cache"""
        pass
    def empty_database(self):
        """Method to lowkey drop table"""
        pass


