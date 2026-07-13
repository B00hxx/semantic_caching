import numpy as np

def cosine_similarity(vec1, vec2):
    dot = np.dot(vec1, vec2)
    return dot / (np.linalg.norm(vec1) * np.linalg.norm(vec2))