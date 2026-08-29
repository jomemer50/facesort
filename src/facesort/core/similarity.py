from __future__ import annotations

import numpy as np


def cosine_similarity(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def mean_embedding(embeddings) -> np.ndarray:
    """Centroid of a set of embeddings (used for reference persons)."""
    if not embeddings:
        raise ValueError("cannot average empty embedding set")
    return np.mean(np.vstack([np.asarray(e, dtype=np.float32) for e in embeddings]), axis=0)
