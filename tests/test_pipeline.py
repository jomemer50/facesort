from pathlib import Path

import cv2
import numpy as np
import pytest

from facesort.core.pipeline import Session

OBAMA_URL = "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/obama.jpg"
BIDEN_URL = "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/biden.jpg"


def _download(url: str) -> np.ndarray:
    import urllib.request

    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read()
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("failed to decode image")
    return img


def _build_library(lib: Path) -> dict[str, str]:
    try:
        obama = _download(OBAMA_URL)
        biden = _download(BIDEN_URL)
    except Exception as e:  # pragma: no cover - depends on network
        pytest.skip(f"could not download sample faces: {e}")

    (lib / "obama1.jpg").write_bytes(cv2.imencode(".jpg", obama)[1].tobytes())
    (lib / "obama2.jpg").write_bytes(cv2.imencode(".jpg", obama)[1].tobytes())
    (lib / "biden1.jpg").write_bytes(cv2.imencode(".jpg", biden)[1].tobytes())
    (lib / "biden2.jpg").write_bytes(cv2.imencode(".jpg", biden)[1].tobytes())

    # Synthetic group photo: both faces side by side.
    h = min(obama.shape[0], biden.shape[0])
    obama_crop = cv2.resize(obama, (obama.shape[1], h))
    biden_crop = cv2.resize(biden, (biden.shape[1], h))
    group = np.hstack([obama_crop, biden_crop])
    (lib / "group.jpg").write_bytes(cv2.imencode(".jpg", group)[1].tobytes())

    return {
        "obama": str(lib / "obama1.jpg"),
        "biden": str(lib / "biden1.jpg"),
        "group": str(lib / "group.jpg"),
    }


def test_full_pipeline_cluster_mode(tmp_path: Path) -> None:
    lib = tmp_path / "library"
    lib.mkdir()
    out = tmp_path / "output"
    db = tmp_path / "cache.db"
    files = _build_library(lib)

    sess = Session(input_root=lib, output_root=out, db_path=db)
    scan = sess.scan()
    assert scan.faces >= 5  # 4 single + 2 in group

    groups = sess.cluster()
    # Exactly two distinct people (noise ignored).
    named = {k: v for k, v in groups.items() if k != -1}
    assert len(named) == 2

    # Determine which cluster is Obama vs Biden by inspecting source files.
    obama_cluster = biden_cluster = None
    for cid, faces in named.items():
        paths = {Path(f.image_path).name for f in faces}
        if "obama1.jpg" in paths:
            obama_cluster = cid
        if "biden1.jpg" in paths:
            biden_cluster = cid
    assert obama_cluster is not None and biden_cluster is not None
    sess.name_cluster(obama_cluster, "Obama")
    sess.name_cluster(biden_cluster, "Biden")

    counts = sess.sort(modes={"cluster"})
    assert counts["Obama"] == 3  # obama1, obama2, group
    assert counts["Biden"] == 3  # biden1, biden2, group
    assert (out / "Obama" / "obama1.jpg").exists()
    assert (out / "Obama" / "group.jpg").exists()
    assert (out / "Biden" / "biden1.jpg").exists()
    assert (out / "Biden" / "group.jpg").exists()
    sess.close()


def test_full_pipeline_reference_mode(tmp_path: Path) -> None:
    lib = tmp_path / "library"
    lib.mkdir()
    out = tmp_path / "output"
    db = tmp_path / "cache.db"
    files = _build_library(lib)

    sess = Session(input_root=lib, output_root=out, db_path=db)
    sess.scan()
    sess.add_reference_image("Obama", files["obama"])
    sess.add_reference_image("Biden", files["biden"])

    counts = sess.sort(modes={"reference"})
    assert counts["Obama"] == 3
    assert counts["Biden"] == 3
    assert (out / "Obama" / "group.jpg").exists()
    assert (out / "Biden" / "group.jpg").exists()
    sess.close()
