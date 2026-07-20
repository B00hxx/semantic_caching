import datetime
class CacheEntry():
    def __init__(self, question : str, embedding : list, answer : str, ttl_seconds : int = 3600):
        self.question = question
        self.embedding = embedding
        self.answer = answer
        self.created_at = datetime.datetime.now()
        self.ttl_seconds = ttl_seconds