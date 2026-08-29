from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import cv2
import numpy as np

from facesort.core.pipeline import Session


OBAMA_URL = "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/obama.jpg"
BIDEN_URL = "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/biden.jpg"


def _download(url: str) -> np.ndarray:
    import urllib.request

    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read()
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("decode failed")
    return img


def build_sample_library(lib: Path) -> bool:
    """Create a 2-person sample library + a group photo. Returns False if offline."""
    try:
        obama = _download(OBAMA_URL)
        biden = _download(BIDEN_URL)
    except Exception as e:
        print(f"[demo] could not download sample faces ({e}); aborting demo.")
        return False

    (lib / "obama1.jpg").write_bytes(cv2.imencode(".jpg", obama)[1].tobytes())
    (lib / "obama2.jpg").write_bytes(cv2.imencode(".jpg", obama)[1].tobytes())
    (lib / "biden1.jpg").write_bytes(cv2.imencode(".jpg", biden)[1].tobytes())
    (lib / "biden2.jpg").write_bytes(cv2.imencode(".jpg", biden)[1].tobytes())
    h = min(obama.shape[0], biden.shape[0])
    group = np.hstack([
        cv2.resize(obama, (obama.shape[1], h)),
        cv2.resize(biden, (biden.shape[1], h)),
    ])
    (lib / "group.jpg").write_bytes(cv2.imencode(".jpg", group)[1].tobytes())
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="FaceSort CLI demo / runner")
    ap.add_argument("input", nargs="?", help="Input photo folder (omit to build a sample)")
    ap.add_argument("--output", help="Output folder (default: <input>/../facesort_out)")
    ap.add_argument(
        "--modes", default="cluster,reference",
        help="comma-separated of cluster,reference (default: cluster,reference)",
    )
    args = ap.parse_args(argv)

    if args.input:
        in_root = Path(args.input)
    else:
        in_root = Path(tempfile.mkdtemp()) / "sample_library"
        in_root.mkdir(parents=True)
        if not build_sample_library(in_root):
            return 2
        print(f"[demo] built sample library at {in_root}")

    out_root = Path(args.output) if args.output else in_root.parent / "facesort_out"
    modes = {m.strip() for m in args.modes.split(",") if m.strip()}
    if modes == {"both"}:
        modes = {"cluster", "reference"}

    sess = Session(input_root=in_root, output_root=out_root)
    scan = sess.scan()
    print(f"[scan] {scan}")

    if "cluster" in modes:
        groups = sess.cluster()
        named = {k: v for k, v in groups.items() if k != -1}
        for i, (cid, _faces) in enumerate(named.items(), 1):
            sess.name_cluster(cid, f"Person-{i}")

    counts = sess.sort(modes, unknown_folder="Unknown")
    print(f"[sort] copied into: {counts}")
    sess.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
