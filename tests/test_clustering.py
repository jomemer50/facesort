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
