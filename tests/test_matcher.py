import numpy as np
import pytest

from facesort.core.matcher import PersonMatcher


def _emb(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(512).astype(np.float32)


def test_matcher_identifies_correct_person() -> None:
    m = PersonMatcher(threshold=0.4)
    alice_center = _emb(1)
    bob_center = _emb(2)
    m.add_reference("Alice", alice_center)
    m.add_reference("Bob", bob_center)

    name, score = m.match(alice_center + 1e-3 * _emb(99))
    assert name == "Alice"
    assert score >= 0.4


def test_matcher_returns_none_below_threshold() -> None:
    m = PersonMatcher(threshold=0.9)
    m.add_reference("Alice", _emb(1))
    name, score = m.match(_emb(2))
    assert name is None
    assert score < 0.9


def test_matcher_match_faces() -> None:
    m = PersonMatcher(threshold=0.4)
    m.add_reference("Alice", _emb(1))
    m.add_reference("Bob", _emb(2))
    faces_emb = [_emb(1) + 1e-3 * _emb(7), _emb(2) + 1e-3 * _emb(8)]
    results = m.match_faces([type("F", (), {"embedding": e})() for e in faces_emb])
    assert [r[0] for r in results] == ["Alice", "Bob"]


def test_matcher_no_references() -> None:
    m = PersonMatcher()
    name, score = m.match(_emb(1))
    assert name is None
