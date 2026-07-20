from .llm_services.llm_service import LLM
from .embedding_services.embedding_service import Embedder
from .cache_entry import CacheEntry
from .vector_store_services.vector_store_services import VectorStore
from .vector_store_services.vector_search_result import VectorSearchResult

class SemanticCaching():
    def __init__(self, llm_model : LLM, embedding_model: Embedder, vector_store : VectorStore, threshold : float = 0.5):
        self.llm = llm_model
        self.embedding = embedding_model
        self.threshold = threshold
        self.vector_store = vector_store
    
    def get_answers(self, query:str)->dict:
        embedded = self.embedding.embed(query)
        response_from_vector_store = self.vector_store.search(query_embedding=embedded, threshold=self.threshold)
        if response_from_vector_store == None:
            answer_by_llm = self.llm.generate(query=query)
            entry = CacheEntry(query, embedded, answer_by_llm)
            self.vector_store.add_entry(entry)
            return {
                "cache_hit" : False,
                "cosine_distance" : None,
                "answer" : answer_by_llm,
                "time" : entry.created_at
            }
        else:

            return {
                "cache_hit" : True,
                "cosine_distance" : response_from_vector_store.score,
                "answer" : response_from_vector_store.answer,
                "time" : response_from_vector_store.time,
                "id" : response_from_vector_store.identifier
            }
        