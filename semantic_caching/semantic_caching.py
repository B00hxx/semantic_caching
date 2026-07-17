from .llm_services.llm_service import LLM
from .embedding_services.embedding_service import Embedder
from .cache_entry import CacheEntry
from .cosine_sim import cosine_similarity
from .vector_store_services.vector_store_services import VectorStore
from .config import redis_client

class SemanticCaching():
    def __init__(self, llm_model : LLM, embedding_model: Embedder, vector_store : VectorStore, threshold : float = 0.5):
        self.llm = llm_model
        self.embedding = embedding_model
        self.threshold = threshold
        self.vector_store = vector_store
    
    def get_answers(self, query:str)->dict:
        close_entries = []
        embedded = self.embedding.embed(query)
        saved_answers = self.vector_store.get_everything()  
        for saved_entry in saved_answers:
            similarity = cosine_similarity(embedded, saved_entry["embedding"])
            if similarity >= self.threshold:
                close_entries.append([saved_entry, similarity])
        
        if len(close_entries) == 0:
            answer_by_llm = self.llm.generate(query=query)
            entry = CacheEntry(query, list(embedded), answer_by_llm)
            self.vector_store.add_entry(entry)
            
            return {
                "cache_hit" : False,
                "similarity" : None,
                "answer" : answer_by_llm,
                "time" : entry.current_time
            }
        
        else:
            close_entries.sort(key=lambda item: item[1], reverse=True)
            return {
                "cache_hit" : True,
                "similarity" : close_entries[0][1],
                "answer" : close_entries[0][0]["answer"],
                "time" : close_entries[0][0]["time"]
            }
        