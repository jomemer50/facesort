from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from ..config import IMAGE_EXTENSIONS
from .cache import FaceCache
from .face_engine import FaceEngine
from .models import Face

logger = logging.getLogger(__name__)

ProgressCb = Callable[[int, int, str], None]  # current, total, current_path
CancelCb = Callable[[], bool]


class ScanResult:
    def __init__(self) -> None:
        self.scanned = 0
        self.cached = 0
        self.faces = 0
        self.errors: list[tuple[str, str]] = []

    def __repr__(self) -> str:
        return (
            f"ScanResult(scanned={self.scanned}, cached={self.cached}, "
            f"faces={self.faces}, errors={len(self.errors)})"
        )


class Scanner:
    """Walks a directory, detects faces, and caches results for fast re-scans."""

    def __init__(self, engine: FaceEngine, cache: FaceCache) -> None:
        self.engine = engine
        self.cache = cache

    def scan(
        self,
        root,
        progress: Optional[ProgressCb] = None,
        cancel: Optional[CancelCb] = None,
    ) -> ScanResult:
        root = Path(root)
        files = sorted(
            p for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        total = len(files)
        result = ScanResult()

        for i, p in enumerate(files, 1):
            if cancel is not None and cancel():
                logger.info("scan cancelled at %s/%s", i - 1, total)
                break
            try:
                mtime = p.stat().st_mtime
                if self.cache.is_fresh(p, mtime):
                    faces = self.cache.get_faces(p)
                    result.cached += 1
                else:
                    faces = self.engine.detect_path(p)
                    self.cache.upsert(p, mtime, faces)
                result.faces += len(faces)
            except Exception as e:  # noqa: BLE001 - keep scanning on bad files
                logger.warning("failed to process %s: %s", p, e)
                result.errors.append((str(p), str(e)))
            result.scanned += 1
            if progress is not None:
                progress(i, total, str(p))

        return result
