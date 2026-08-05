class VectorSearchResult():
    def __init__(self ,answer : str,
    score : float, identifier : str, question : str,
    time, ttl : float, namespace : str = "default"):
        self.answer = answer
        self.score = score
        self.identifier = identifier
        self.question = question
        self.time = time
        self.ttl = ttl
        self.namespace = namespace