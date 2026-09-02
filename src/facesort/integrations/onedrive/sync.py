from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from .client import OneDriveClient

logger = logging.getLogger(__name__)

ProgressCb = Callable[[int, int, str], None]


def default_cache_dir() -> Path:
    return Path.home() / ".facesort" / "cache" / "onedrive"


def stage_folder(
    client: OneDriveClient,
    folder_id: str,
    dest_root: Path,
    progress: ProgressCb | None = None,
) -> int:
    """Download every image under ``folder_id`` into ``dest_root``.

    Returns the number of images downloaded. Files are placed under a stable
    local filename derived from the Drive item id so the cache is robust to
    name collisions/renames and re-scans reuse the cache.
    """
    items = client.walk_images(folder_id)
    total = len(items)
    for i, item in enumerate(items, 1):
        item_id = item["id"]
        ext = Path(item.get("name") or "image").suffix.lower() or ".jpg"
        dest = dest_root / f"{item_id}{ext}"
        if not dest.exists():
            client.download(item_id, dest)
        if progress:
            progress(i, total, item.get("name", ""))
    return total


def upload_tree(
    client: OneDriveClient,
    local_root: Path,
    parent_id: str = "root",
    progress: ProgressCb | None = None,
) -> dict[str, int]:
    """Upload a local directory tree into a OneDrive folder.

    Every top-level directory (a person folder) becomes a OneDrive folder;
    files are uploaded into the matching folder. Returns per-folder counts.
    """
    local_root = Path(local_root)
    if not local_root.is_dir():
        return {}

    persons = sorted(
        d.name for d in local_root.iterdir() if d.is_dir() and not d.name.startswith(".")
    )
    total_files = sum(
        1 for d in local_root.iterdir() if d.is_dir() and not d.name.startswith(".")
        for _ in d.iterdir()
    )
    counts: dict[str, int] = {}
    done = 0

    for person in persons:
        person_dir = local_root / person
        folder_id = client.ensure_folder(person, parent_id)
        n = 0
        for f in sorted(p for p in person_dir.iterdir() if p.is_file()):
            client.upload(folder_id, f.name, f)
            n += 1
            done += 1
            if progress:
                progress(done, total_files, person)
        counts[person] = n
    return counts


def resolve_output_name(local_root: Path) -> str:
    """Human-friendly name for the uploaded OneDrive root folder."""
    return local_root.name or "FaceSort"
