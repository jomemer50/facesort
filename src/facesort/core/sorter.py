from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional


def _dedup_path(dest_dir: Path, name: str) -> Path:
    dest = dest_dir / name
    if not dest.exists():
        return dest
    stem, ext = os.path.splitext(name)
    i = 1
    while True:
        cand = dest_dir / f"{stem}_{i}{ext}"
        if not cand.exists():
            return cand
        i += 1


def sort_images(
    image_to_persons: dict[str, set[str]],
    output_root,
    unknown_folder: Optional[str] = "Unknown",
    dry_run: bool = False,
) -> dict[str, int]:
    """Copy each image into every person folder it belongs to.

    A photo mapping to multiple persons (group photo) is copied into each.
    Photos mapping to no person go to ``unknown_folder`` (if set).
    Returns a per-folder copy count.
    """
    output_root = Path(output_root)
    counts: dict[str, int] = {}

    for image_path, persons in image_to_persons.items():
        targets = set(persons)
        if not targets and unknown_folder:
            targets = {unknown_folder}

        src = Path(image_path)
        for person in targets:
            dest_dir = output_root / person
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
            dest = _dedup_path(dest_dir, src.name)
            if not dry_run:
                shutil.copy2(src, dest)
            counts[person] = counts.get(person, 0) + 1

    return counts
