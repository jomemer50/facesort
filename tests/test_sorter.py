from pathlib import Path

import pytest

from facesort.core.sorter import sort_images


def _make_file(folder: Path, name: str, content: bytes = b"data") -> Path:
    p = folder / name
    p.write_bytes(content)
    return p


def test_sort_copies_into_person_folders(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    a = _make_file(src, "a.jpg")
    b = _make_file(src, "b.jpg")

    counts = sort_images(
        {str(a): {"Alice"}, str(b): {"Bob"}},
        out,
    )
    assert (out / "Alice" / "a.jpg").exists()
    assert (out / "Bob" / "b.jpg").exists()
    assert counts == {"Alice": 1, "Bob": 1}


def test_sort_group_photo_copied_to_multiple_folders(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    group = _make_file(src, "group.jpg")

    counts = sort_images({str(group): {"Alice", "Bob"}}, out)
    assert (out / "Alice" / "group.jpg").exists()
    assert (out / "Bob" / "group.jpg").exists()
    assert counts == {"Alice": 1, "Bob": 1}


def test_sort_unknown_folder(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    a = _make_file(src, "a.jpg")

    counts = sort_images({str(a): set()}, out, unknown_folder="Unknown")
    assert (out / "Unknown" / "a.jpg").exists()
    assert counts == {"Unknown": 1}


def test_sort_no_unknown_when_disabled(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    a = _make_file(src, "a.jpg")
    counts = sort_images({str(a): set()}, out, unknown_folder=None)
    assert counts == {}
    assert not (out / "Unknown").exists()


def test_sort_dedup(tmp_path: Path) -> None:
    src1 = tmp_path / "src1"
    src2 = tmp_path / "src2"
    src1.mkdir()
    src2.mkdir()
    out = tmp_path / "out"
    a = _make_file(src1, "a.jpg", b"v1")
    b = _make_file(src2, "a.jpg", b"v2")  # same name, different content, diff source
    sort_images({str(a): {"Alice"}, str(b): {"Alice"}}, out)
    files = sorted(p.name for p in (out / "Alice").iterdir())
    assert files == ["a.jpg", "a_1.jpg"]


def test_sort_dry_run_does_not_write(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    a = _make_file(src, "a.jpg")
    counts = sort_images({str(a): {"Alice"}}, out, dry_run=True)
    assert counts == {"Alice": 1}
    assert not out.exists()
