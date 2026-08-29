import os
import time
from pathlib import Path

import cv2
import pytest

from facesort.core.cache import FaceCache
from facesort.core.face_engine import FaceEngine
from facesort.core.scanner import ScanResult, Scanner


def _write_sample_image(folder: Path, name: str):
    try:
        from insightface.data import get_image as ins_get_image

        img = ins_get_image("t1")
    except Exception as e:  # pragma: no cover - depends on bundled asset
        pytest.skip(f"insightface sample image unavailable: {e}")
    if img is None:
        pytest.skip("insightface sample image returned None")
    path = folder / name
    cv2.imwrite(str(path), img)
    return path


@pytest.fixture
def engine() -> FaceEngine:
    return FaceEngine()


def test_scanner_detects_and_caches(tmp_path: Path, engine: FaceEngine) -> None:
    img = _write_sample_image(tmp_path, "person.jpg")
    cache = FaceCache(tmp_path / "cache.db")
    scanner = Scanner(engine, cache)

    r1 = scanner.scan(tmp_path)
    assert isinstance(r1, ScanResult)
    assert r1.scanned == 1
    assert r1.faces >= 1
    assert r1.cached == 0

    # Re-scan: results served from cache.
    r2 = scanner.scan(tmp_path)
    assert r2.cached == 1
    assert r2.faces == r1.faces
    cache.close()


def test_scanner_reprocess_on_mtime_change(tmp_path: Path, engine: FaceEngine) -> None:
    img = _write_sample_image(tmp_path, "person.jpg")
    cache = FaceCache(tmp_path / "cache.db")
    scanner = Scanner(engine, cache)

    scanner.scan(tmp_path)
    # Touch the file so mtime changes -> should reprocess, not use cache.
    new_mtime = time.time() + 60
    os.utime(img, (new_mtime, new_mtime))
    r = scanner.scan(tmp_path)
    assert r.cached == 0
    assert r.scanned == 1
    cache.close()


def test_scanner_cancel(tmp_path: Path, engine: FaceEngine) -> None:
    for i in range(3):
        _write_sample_image(tmp_path, f"p{i}.jpg")
    cache = FaceCache(tmp_path / "cache.db")
    scanner = Scanner(engine, cache)

    state = {"n": 0}

    def cancel() -> bool:
        state["n"] += 1
        return state["n"] >= 1

    r = scanner.scan(tmp_path, cancel=cancel)
    assert r.scanned < 3
    cache.close()


def test_scanner_skips_non_images(tmp_path: Path, engine: FaceEngine) -> None:
    _write_sample_image(tmp_path, "person.jpg")
    (tmp_path / "notes.txt").write_text("not an image")
    cache = FaceCache(tmp_path / "cache.db")
    scanner = Scanner(engine, cache)
    r = scanner.scan(tmp_path)
    assert r.scanned == 1
    cache.close()
