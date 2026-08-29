from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .similarity import mean_embedding


@dataclass
class Face:
    """A single detected face in an image."""

    bbox: list[float]               # [x1, y1, x2, y2] in pixel coords
    det_score: float               # detection confidence in [0, 1]
    embedding: np.ndarray           # 512-d ArcFace embedding
    kps: Optional[list] = None     # 5-point landmarks (optional)
    image_path: Optional[str] = None

    def __post_init__(self) -> None:
        self.embedding = np.asarray(self.embedding, dtype=np.float32)
        if self.bbox is not None:
            self.bbox = [float(v) for v in self.bbox]
        self.det_score = float(self.det_score)


@dataclass
class Person:
    """A named identity, optionally built from reference face embeddings."""

    name: str
    reference_embeddings: list[np.ndarray] = field(default_factory=list)
    cluster_id: Optional[int] = None

    def add_reference(self, embedding: np.ndarray) -> None:
        self.reference_embeddings.append(np.asarray(embedding, dtype=np.float32))

    def centroid(self) -> Optional[np.ndarray]:
        if not self.reference_embeddings:
            return None
        return mean_embedding(self.reference_embeddings)
