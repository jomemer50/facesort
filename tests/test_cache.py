from pathlib import Path

import numpy as np
import pytest

from facesort.core.cache import FaceCache
from facesort.core.models import Face


def _make_face() -> Face:
    emb = np.random.rand(512).astype(np.float32)
    return Face(bbox=[1.0, 2.0, 3.0, 4.0], det_score=0.9, embedding=emb,
                kps=[[1.0, 1.0], [2.0, 2.0]])


def test_cache_roundtrip(tmp_path: Path) -> None:
    c = FaceCache(tmp_path / "cache.db")
    p = tmp_path / "a.jpg"
    f = _make_face()
    c.upsert(p, 123.0, [f])
    got = c.get_faces(p)
    assert len(got) == 1
    assert np.allclose(got[0].embedding, f.embedding)
    assert got[0].det_score == 0.9
    assert got[0].kps == f.kps
    assert c.count_images() == 1
    assert c.count_faces() == 1
    c.close()


def test_cache_freshness(tmp_path: Path) -> None:
    c = FaceCache(tmp_path / "cache.db")
    p = tmp_path / "a.jpg"
    assert c.is_fresh(p, 1.0) is False
    c.upsert(p, 1.0, [])
    assert c.is_fresh(p, 1.0) is True
    assert c.is_fresh(p, 2.0) is False
    c.close()


def test_cache_iter_all(tmp_path: Path) -> None:
    c = FaceCache(tmp_path / "cache.db")
    for i in range(3):
        c.upsert(tmp_path / f"img{i}.jpg", float(i), [_make_face()])
    faces = list(c.iter_all_faces())
    assert len(faces) == 3
    assert all(f.image_path for f in faces)
    paths, embs = c.all_embeddings_with_paths()
    assert len(paths) == 3
    assert all(e.shape == (512,) for e in embs)
    c.close()
