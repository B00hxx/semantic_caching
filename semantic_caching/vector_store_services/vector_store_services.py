from abc import ABC, abstractmethod
from .vector_search_result import VectorSearchResult
from uuid import UUID
class VectorStore(ABC):
    @abstractmethod
    async def add_entry(self, entry):
        """Abstract method to add entries to vector store"""
        pass
    @abstractmethod
    async def get_entry(self, identifier : str):
        """Abstract method to retrieve an entry from vector store"""
        pass
    @abstractmethod
    async def get_size(self) -> int:
        """Method to get the size of cache"""
        pass
    @abstractmethod
    async def empty_database(self):
        """Method to lowkey drop table"""
        pass
    @abstractmethod
    async def search(self, query_embedding, threshold : float, namespace : str) -> VectorSearchResult:
        """Searching through the vector db for closest match"""
        pass
    @abstractmethod
    async def ttl(self, identifier : str):
        """Method to get back the time to live of an entry"""
        pass
    @abstractmethod
    async def update_access_metadata(self, identifier : str):
        pass
    @abstractmethod
    async def get_all_entries(self):
        pass
    @abstractmethod
    async def delete_entry(self, identifier: UUID):
        """Delete an entry from the vector store."""
        pass
