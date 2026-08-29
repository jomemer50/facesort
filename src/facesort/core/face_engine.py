from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

from ..config import DEFAULT_DET_SIZE, DEFAULT_DET_THRESH, DEFAULT_MODEL
from .models import Face

logger = logging.getLogger(__name__)

CPU_PROVIDERS = ["CPUExecutionProvider"]


class FaceEngine:
    """Thin wrapper around InsightFace ``buffalo_l`` for detection + embedding."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        providers: Optional[list[str]] = None,
        det_thresh: float = DEFAULT_DET_THRESH,
        det_size=DEFAULT_DET_SIZE,
    ) -> None:
        if providers is None:
            providers = list(CPU_PROVIDERS)
        self.model_name = model_name
        self.providers = providers
        self.det_thresh = det_thresh
        self.det_size = det_size

        # ctx_id=-1 forces CPU on the onnxruntime backend.
        ctx_id = -1 if providers == CPU_PROVIDERS else 0

        from insightface.app import FaceAnalysis

        self.app = FaceAnalysis(name=model_name, providers=providers)
        self.app.prepare(ctx_id=ctx_id, det_thresh=det_thresh, det_size=det_size)
        logger.info("FaceEngine ready: model=%s providers=%s", model_name, providers)

    def detect(self, image: np.ndarray) -> list[Face]:
        """Detect faces in a BGR image and return ``Face`` objects."""
        if image is None or image.size == 0:
            return []
        raw = self.app.get(image)
        faces: list[Face] = []
        for f in raw:
            score = float(getattr(f, "det_score", 0.0))
            if score < self.det_thresh:
                continue
            kps = getattr(f, "kps", None)
            faces.append(
                Face(
                    bbox=f.bbox.astype(float).tolist(),
                    det_score=score,
                    embedding=np.asarray(f.embedding, dtype=np.float32),
                    kps=kps.astype(float).tolist() if kps is not None else None,
                )
            )
        return faces

    def detect_path(self, path) -> list[Face]:
        img = cv2.imread(str(path))
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {path}")
        faces = self.detect(img)
        for f in faces:
            f.image_path = str(path)
        return faces
