import numpy as np
from utils.cosine_similarity import cosine_similarity


def test_cosine_similarity():
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([1.0, 0.0, 0.0])
    assert np.isclose(cosine_similarity(v1, v2), 1.0)

    v3 = np.array([0.0, 1.0, 0.0])
    assert np.isclose(cosine_similarity(v1, v3), 0.0)

    v4 = np.array([-1.0, 0.0, 0.0])
    assert np.isclose(cosine_similarity(v1, v4), -1.0)
