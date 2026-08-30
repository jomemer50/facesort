from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import Callable, Optional

from ..config import (
    CLUSTER_EPS,
    CLUSTER_MIN_SAMPLES,
    DEFAULT_DET_SIZE,
    DEFAULT_DET_THRESH,
    DEFAULT_MODEL,
    MATCH_THRESHOLD,
)
from .cache import FaceCache
from .clustering import cluster_embeddings, group_by_label
from .face_engine import FaceEngine
from .matcher import PersonMatcher
from .models import Face
from .scanner import ScanResult, Scanner
from .similarity import cosine_similarity, mean_embedding
from .sorter import sort_images


class Session:
    """End-to-end workflow controller for one photo library."""

    def __init__(
        self,
        input_root,
        output_root=None,
        db_path=None,
        model_name: str = DEFAULT_MODEL,
        providers=None,
    ) -> None:
        self.input_root = Path(input_root)
        self.output_root = Path(output_root) if output_root else None
        self.engine = FaceEngine(
            model_name=model_name,
            providers=providers,
            det_thresh=DEFAULT_DET_THRESH,
            det_size=DEFAULT_DET_SIZE,
        )
        default_db = self.input_root / ".facesort_cache.db"
        self.cache = FaceCache(db_path or default_db)
        self.scanner = Scanner(self.engine, self.cache)

        self.faces: list[Face] = []
        self.labels: list[int] = []
        self.matcher = PersonMatcher()
        self.cluster_names: dict[int, str] = {}

    # --- scanning ---------------------------------------------------------
    def scan(
        self,
        progress: Optional[Callable[[int, int, str], None]] = None,
        cancel: Optional[Callable[[], bool]] = None,
    ) -> ScanResult:
        result = self.scanner.scan(self.input_root, progress, cancel)
        self.faces = list(self.cache.iter_all_faces())
        return result

    # --- clustering (auto mode) ------------------------------------------
    def cluster(self, eps: float = CLUSTER_EPS, min_samples: int = CLUSTER_MIN_SAMPLES):
        embs = [f.embedding for f in self.faces]
        self.labels = list(cluster_embeddings(embs, eps=eps, min_samples=min_samples))
        return self.cluster_groups()

    def cluster_groups(self) -> dict[int, list[Face]]:
        return group_by_label(self.faces, np.array(self.labels))

    def name_cluster(self, cluster_id: int, name: str) -> None:
        self.cluster_names[cluster_id] = name

    # --- reference matching (reference mode) -----------------------------
    def add_reference_image(self, name: str, image_path) -> int:
        faces = self.engine.detect_path(image_path)
        for f in faces:
            self.matcher.add_reference(name, f.embedding)
        return len(faces)

    def add_reference_embedding(self, name: str, embedding: np.ndarray) -> None:
        self.matcher.add_reference(name, embedding)

    # --- combine ----------------------------------------------------------
    def build_image_to_persons(self, modes: set[str]) -> dict[str, set[str]]:
        """Map each image path -> set of person names.

        ``modes`` is a subset of ``{"cluster", "reference"}``.
        Group photos naturally resolve to multiple persons.

        In cluster mode every face is classified against the *named* cluster
        centroids (not just DBSCAN labels), so a person who only appears once
        in a group photo still lands in the right folder.
        """
        mapping: dict[str, set[str]] = {}

        if "cluster" in modes and self.cluster_names:
            centroids: dict[str, np.ndarray] = {}
            for cid, name in self.cluster_names.items():
                embs = [
                    f.embedding
                    for f, lab in zip(self.faces, self.labels)
                    if int(lab) == cid
                ]
                if embs:
                    centroids[name] = mean_embedding(embs)

            unclustered_name = self.cluster_names.get(-1)
            for f in self.faces:
                best_name, best_score = None, -1.0
                for name, cen in centroids.items():
                    if name == unclustered_name:
                        continue
                    score = cosine_similarity(f.embedding, cen)
                    if score > best_score:
                        best_score, best_name = score, name
                if best_name is not None and best_score >= MATCH_THRESHOLD:
                    mapping.setdefault(f.image_path, set()).add(best_name)
                elif unclustered_name is not None:
                    # Faces that don't match any named person land in Unclustered.
                    mapping.setdefault(f.image_path, set()).add(unclustered_name)

        if "reference" in modes:
            for face in self.faces:
                name, _ = self.matcher.match(face.embedding)
                if name:
                    mapping.setdefault(face.image_path, set()).add(name)

        return mapping

    def sort(
        self,
        modes: set[str],
        output_root=None,
        unknown_folder: Optional[str] = "Unknown",
        dry_run: bool = False,
    ) -> dict[str, int]:
        output_root = Path(output_root) if output_root else self.output_root
        if output_root is None:
            raise ValueError("output_root is required")
        mapping = self.build_image_to_persons(modes)
        return sort_images(mapping, output_root, unknown_folder=unknown_folder, dry_run=dry_run)

    def close(self) -> None:
        self.cache.close()
