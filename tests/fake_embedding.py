import numpy as np

class FakeEmbedder():
    def __init__(self, model = "fake_emb"):
        self.model = model
    
    def get_embedding(self, query : str)->np.array:
        if query == "hello!":
            return np.array([1,0,0])
        elif query == "hi!":
            return np.array([0.95, 0.05, 0.01])
        elif query == "baha":
            return np.array([0,1,0])
        fake_vect = np.array([0,0,1])
        return fake_vect
    
