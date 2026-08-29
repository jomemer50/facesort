from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np
from sklearn.cluster import DBSCAN

from ..config import CLUSTER_EPS, CLUSTER_MIN_SAMPLES
from .models import Face


def cluster_embeddings(
    embeddings: Iterable[np.ndarray],
    eps: float = CLUSTER_EPS,
    min_samples: int = CLUSTER_MIN_SAMPLES,
    metric: str = "cosine",
) -> np.ndarray:
    """Cluster face embeddings via DBSCAN.

    Returns an array of integer labels aligned with ``embeddings``.
    Label ``-1`` means "noise" (not enough neighbors to form a cluster).
    """
    embs = [np.asarray(e, dtype=np.float32) for e in embeddings]
    if len(embs) == 0:
        return np.array([], dtype=int)
    if len(embs) == 1:
        # A single face cannot satisfy min_samples, so it is its own cluster.
        return np.array([0], dtype=int)

    X = np.vstack(embs)
    db = DBSCAN(eps=eps, min_samples=min_samples, metric=metric)
    return db.fit_predict(X)


def group_by_label(faces: list[Face], labels: np.ndarray) -> dict[int, list[Face]]:
    """Group faces by their cluster label (noise = -1 kept separately)."""
    groups: dict[int, list[Face]] = defaultdict(list)
    for face, lab in zip(faces, labels):
        groups[int(lab)].append(face)
    return dict(groups)


def count_clusters(labels: np.ndarray) -> int:
    """Number of non-noise clusters."""
    unique = set(int(l) for l in labels)
    unique.discard(-1)
    return len(unique)
