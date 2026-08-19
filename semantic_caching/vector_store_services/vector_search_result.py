class VectorSearchResult():
    def __init__(self ,answer : str,
    score : float, identifier : str, question : str,
    created_at, ttl : float, namespace : str = "default"):
        self.answer = answer
        self.score = score
        self.identifier = identifier
        self.question = question
        self.created_at = created_at
        self.ttl = ttl
        self.namespace = namespace