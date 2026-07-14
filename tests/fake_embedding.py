import numpy as np

class FakeEmbedder():
    def __init__(self, model = "fake_emb"):
        self.model = model
    
    def get_embedding(self, query : str)->np.array:
        if query == "hello!":
            return np.array([1,2,3])
        elif query == "hi!":
            return np.array([4,5,6])
        elif query == "baha":
            return np.array([10,11,12])
        fake_vect = np.array([7,8,9])
        return fake_vect
    
