class VectorSearchResult():
    def __init__(self, answer, score, identifier, question, time, ttl):
        self.answer = answer
        self.score = score
        self.identifier = identifier
        self.question = question
        self.time = time
        self.ttl = ttl