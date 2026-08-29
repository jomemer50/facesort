from __future__ import annotations

from typing import Optional

import numpy as np

from ..config import MATCH_THRESHOLD
from .similarity import cosine_similarity
from .models import Face, Person


class PersonMatcher:
    """Matches faces against named reference persons via cosine similarity."""

    def __init__(self, threshold: float = MATCH_THRESHOLD) -> None:
        self.threshold = threshold
        self.persons: dict[str, Person] = {}

    def add_person(self, name: str) -> Person:
        if name not in self.persons:
            self.persons[name] = Person(name=name)
        return self.persons[name]

    def add_reference(self, name: str, embedding: np.ndarray) -> None:
        self.add_person(name).add_reference(embedding)

    def match(self, embedding: np.ndarray) -> tuple[Optional[str], float]:
        """Return (person_name, score); name is None if below threshold."""
        best_name: Optional[str] = None
        best_score = -1.0
        for name, person in self.persons.items():
            centroid = person.centroid()
            if centroid is None:
                continue
            score = cosine_similarity(embedding, centroid)
            if score > best_score:
                best_score = score
                best_name = name
        if best_score >= self.threshold:
            return best_name, float(best_score)
        return None, float(best_score)

    def match_faces(self, faces: list[Face]) -> list[tuple[Optional[str], float]]:
        return [self.match(f.embedding) for f in faces]
