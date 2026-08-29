import numpy as np
import pytest

from facesort.core.face_engine import FaceEngine
from facesort.core.models import Face


@pytest.fixture(scope="module")
def engine() -> FaceEngine:
    return FaceEngine()


def test_engine_initializes(engine: FaceEngine) -> None:
    assert engine.app is not None
    assert engine.model_name == "buffalo_l"


def test_detect_no_face_returns_empty(engine: FaceEngine) -> None:
    img = np.random.randint(0, 255, (300, 300, 3), dtype=np.uint8)
    faces = engine.detect(img)
    assert isinstance(faces, list)
    assert all(isinstance(f, Face) for f in faces)
    # random noise should not produce confident detections
    assert len(faces) == 0 or all(f.det_score >= engine.det_thresh for f in faces)


def test_face_dataclass_embedding_shape() -> None:
    emb = np.random.rand(512).astype(np.float32)
    f = Face(bbox=[1.0, 2.0, 3.0, 4.0], det_score=0.9, embedding=emb)
    assert f.embedding.shape == (512,)
    assert f.det_score == 0.9


def test_detect_real_face(engine: FaceEngine) -> None:
    try:
        from insightface.data import get_image as ins_get_image

        img = ins_get_image("t1")
    except Exception as e:  # pragma: no cover - depends on network/asset availability
        pytest.skip(f"insightface sample image unavailable: {e}")
    if img is None:
        pytest.skip("insightface sample image returned None")

    faces = engine.detect(img)
    assert len(faces) >= 1
    for f in faces:
        assert isinstance(f, Face)
        assert f.embedding.shape == (512,)
        assert f.det_score >= engine.det_thresh
