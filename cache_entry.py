import datetime
class CacheEntry():
    def __init__(self, question, embedding, answer):
        self.question = question
        self.embedding = embedding
        self.answer = answer
        self.current_time = datetime.datetime.now()
