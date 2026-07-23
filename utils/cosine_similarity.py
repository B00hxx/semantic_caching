# Source - https://stackoverflow.com/a/43043160
# Posted by dontloo, modified by community. See post 'Timeline' for change history
# Retrieved 2026-07-23, License - CC BY-SA 4.0

from numpy import dot, ndarray
from numpy.linalg import norm

def cosine_similarity(a : ndarray, b : ndarray):
    cos_sim = dot(a, b)/(norm(a)*norm(b))
    return cos_sim
