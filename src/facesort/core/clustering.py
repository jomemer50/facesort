from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

import numpy as np

from ..config import CLUSTER_EPS, CLUSTER_MIN_SAMPLES
from .models import Face

# Optional FAISS accelerates nearest-neighbour search, turning the previous
# pairwise DBSCAN (O(n^2)) into a scalable k-NN graph cluster. When faiss is
# not installed we fall back to sklearn DBSCAN so the app still works.
try:
    import faiss as _FAISS
except Exception:  # pragma: no cover - depends on environment
    _FAISS = None

from sklearn.cluster import DBSCAN  # noqa: E402

# Above this many embeddings we switch from the exact flat index to an
# approximate HNSW index to keep large libraries fast.
_APPROX_THRESHOLD = 2000

# Number of neighbours to probe when building the k-NN graph. Large enough to
# connect real clusters but bounded to keep the search sub-quadratic.
_DEFAULT_KNN_K = 16


def cluster_embeddings(
    embeddings: Iterable[np.ndarray],
    eps: float = CLUSTER_EPS,
    min_samples: int = CLUSTER_MIN_SAMPLES,
    metric: str = "cosine",
) -> np.ndarray:
    """Cluster face embeddings into groups (FAISS k-NN graph).

    Returns an array of integer labels aligned with ``embeddings``.
    Label ``-1`` means "noise" (component too small to be a cluster).

    Requires the caller to pass embeddings grouped by order; the returned
    labels are indices into the same sequence.
    """
    embs = [np.asarray(e, dtype=np.float32) for e in embeddings]
    if len(embs) == 0:
        return np.array([], dtype=int)
    if len(embs) == 1:
        # A single face cannot satisfy min_samples, so it is its own cluster.
        return np.array([0], dtype=int)

    X = np.vstack(embs)
    if _FAISS is not None:
        return _cluster_with_faiss(X, eps, min_samples)
    # Fallback: exact pairwise DBSCAN when faiss is unavailable.
    db = DBSCAN(eps=eps, min_samples=min_samples, metric=metric)
    return db.fit_predict(X)


def _cluster_with_faiss(
    X: np.ndarray, eps: float, min_samples: int
) -> np.ndarray:
    """Cluster via a cosine k-NN graph + connected components (single-linkage).

    ``eps`` is cosine *distance*; two faces are connected when their cosine
    similarity is >= ``1 - eps``. Components smaller than ``min_samples`` are
    treated as noise (label -1).
    """
    n = X.shape[0]
    thr = float(1.0 - eps)

    Y = X.copy()
    _FAISS.normalize_L2(Y)
    dim = Y.shape[1]

    if n > _APPROX_THRESHOLD:
        # HNSW over normalized vectors; inner-product = cosine similarity.
        index = _FAISS.index_factory(
            dim, "HNSW32,Flat", _FAISS.METRIC_INNER_PRODUCT
        )
        index.hnsw.efSearch = 128
    else:
        index = _FAISS.IndexFlatIP(dim)
    index.add(Y)

    k = min(n, max(min_samples, _DEFAULT_KNN_K))
    sims, idxs = index.search(Y, k)

    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        for j in range(k):
            jj = int(idxs[i][j])
            if jj == i:
                continue
            if float(sims[i][j]) >= thr:
                union(i, jj)

    roots = [find(i) for i in range(n)]
    root_sizes = Counter(roots)

    labels = np.empty(n, dtype=int)
    comp_to_label: dict[int, int] = {}
    next_label = 0
    for i in range(n):
        r = roots[i]
        if root_sizes[r] < min_samples:
            labels[i] = -1
            continue
        if r not in comp_to_label:
            comp_to_label[r] = next_label
            next_label += 1
        labels[i] = comp_to_label[r]
    return labels


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
