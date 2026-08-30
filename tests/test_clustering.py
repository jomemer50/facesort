import numpy as np
import pytest

from facesort.core.clustering import cluster_embeddings, count_clusters, group_by_label
from facesort.core.models import Face
from facesort.core.similarity import cosine_similarity, mean_embedding


def _face(embedding) -> Face:
    return Face(bbox=[0, 0, 1, 1], det_score=0.9, embedding=np.asarray(embedding, dtype=np.float32))


def test_cosine_similarity_identical() -> None:
    a = np.random.rand(512).astype(np.float32)
    assert abs(cosine_similarity(a, a) - 1.0) < 1e-5


def test_cosine_similarity_orthogonal() -> None:
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    assert abs(cosine_similarity(a, b)) < 1e-5


def test_mean_embedding() -> None:
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([3.0, 0.0], dtype=np.float32)
    m = mean_embedding([a, b])
    assert np.allclose(m, [2.0, 0.0])


def test_cluster_groups_same_person() -> None:
    base = np.random.rand(512).astype(np.float32)
    same_a = base + 1e-3 * np.random.rand(512).astype(np.float32)
    same_b = base + 1e-3 * np.random.rand(512).astype(np.float32)
    different = np.random.rand(512).astype(np.float32)
    embs = [same_a, same_b, different, different + 1e-3 * np.random.rand(512).astype(np.float32)]

    labels = cluster_embeddings(embs, eps=0.2, min_samples=2)
    assert count_clusters(labels) == 2
    groups = group_by_label([_face(e) for e in embs], labels)
    sizes = sorted(len(v) for v in groups.values())
    assert sizes == [2, 2]


def test_cluster_single_face() -> None:
    labels = cluster_embeddings([np.random.rand(512).astype(np.float32)])
    assert list(labels) == [0]


def test_cluster_empty() -> None:
    labels = cluster_embeddings([])
    assert len(labels) == 0


def test_faiss_noise_small_components() -> None:
    """Components smaller than min_samples are labeled -1 (noise)."""
    rng = np.random.default_rng(0)
    c1 = rng.standard_normal(512).astype(np.float32)
    c1 /= np.linalg.norm(c1)
    c2 = rng.standard_normal(512).astype(np.float32)
    c2 /= np.linalg.norm(c2)
    p1a = c1 + 1e-3 * rng.standard_normal(512).astype(np.float32)
    p1b = c1 + 1e-3 * rng.standard_normal(512).astype(np.float32)
    embs = [p1a, p1b, c2, -c2]
    labels = cluster_embeddings(embs, eps=0.2, min_samples=2)
    assert count_clusters(labels) == 1
    assert list(labels).count(-1) == 2


def test_faiss_large_approx() -> None:
    """The approximate HNSW path clusters >2000 faces into clean groups."""
    rng = np.random.default_rng(1)
    n_clusters, per = 5, 500
    base = rng.standard_normal((n_clusters, 512)).astype(np.float32)
    base /= np.linalg.norm(base, axis=1, keepdims=True)
    embs = []
    for ci in range(n_clusters):
        for _ in range(per):
            e = base[ci] + 0.001 * rng.standard_normal(512).astype(np.float32)
            embs.append(e)
    labels = cluster_embeddings(embs, eps=0.05, min_samples=5)
    assert count_clusters(labels) == n_clusters
    for group in group_by_label([_face(e) for e in embs], labels).values():
        assert len(group) == per
