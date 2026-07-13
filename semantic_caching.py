from llm_service import LLM
from embedding import embedder
from cache_entry import CacheEntry
from cosine_sim import cosine_similarity


class SemanticCaching():
    def __init__(self, llm_model : LLM, embedding_model: embedder, threshold : float = 0.5):
        self.llm = LLM(llm_model)
        self.embedding = embedder(embedding_model)
        self.threshold = threshold
        self.saved_answers = [] #made this into an instance's thingy coz then we can have a cache for each instance for different departmenets or use cases
    def get_answers(self, prompt:str)-> tuple[bool, str]:
        state = False
        embedded = self.embedding.get_embedding(prompt)
        for saved_entry in self.saved_answers:
            if cosine_similarity(embedded, saved_entry.embedding) >= self.threshold:
                state = True
                return state, saved_entry.answer
        if state == False:
            answer_by_llm = self.llm.get_answer(prompt)
            self.saved_answers.append(CacheEntry(prompt, embedded, answer_by_llm))
            return state, answer_by_llm
