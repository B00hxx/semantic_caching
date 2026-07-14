from fake_embedding import FakeEmbedder
from fake_llm import Fake_LLM
from cache_entry import CacheEntry
from cosine_sim import cosine_similarity
from fake_redis import FakeRedisService

class SemanticCaching():
    def __init__(self, llm_model : str, embedding_model: str, threshold : float = 0.5):
        self.llm = Fake_LLM(llm_model)
        self.embedding = FakeEmbedder(embedding_model)
        self.threshold = threshold
        self.saved_answers = [] 
        self.redis = FakeRedisService()
    
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
        