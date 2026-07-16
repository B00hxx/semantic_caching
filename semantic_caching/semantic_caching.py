from .llm_service import LLM
from .embedding import Embedder
from .cache_entry import CacheEntry
from .cosine_sim import cosine_similarity
from .redis_service import RedisService
from .config import redis_client

class SemanticCaching():
    def __init__(self, llm_model : LLM, embedding_model: Embedder, threshold : float = 0.5):
        self.llm = LLM(llm_model)
        self.embedding = Embedder(embedding_model)
        self.threshold = threshold
        self.saved_answers = [] #made this into an instance's thingy coz then we can have a cache for each instance for different departmenets or use cases
        self.redis = RedisService(client = redis_client)
    
    def get_answers(self, prompt:str)->dict:
        close_entries = []
        embedded = self.embedding.get_embedding(prompt)
        self.saved_answers = self.redis.get_everything()
        
        for saved_entry in self.saved_answers:
            similarity = cosine_similarity(embedded, saved_entry["embedding"])
            if similarity >= self.threshold:
                close_entries.append([saved_entry, similarity])
        
        if len(close_entries) == 0:
            answer_by_llm = self.llm.get_answer(prompt)
            entry = CacheEntry(prompt, list(embedded), answer_by_llm)
            self.redis.add_entry(entry)
            
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
        