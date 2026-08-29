from facesort.core.face_engine import FaceEngine
from facesort.core.models import Face


def main(argv=None) -> int:
    import sys

    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("Usage: python -m facesort.scripts.smoke <image_path> [image_path ...]")
        return 1

    engine = FaceEngine()
    import cv2

    for p in argv:
        img = cv2.imread(p)
        if img is None:
            print(f"[skip] cannot read {p}")
            continue
        faces = engine.detect(img)
        print(f"{p}: {len(faces)} face(s)")
        for i, f in enumerate(faces):
            print(f"  face {i}: score={f.det_score:.3f} bbox={[round(x) for x in f.bbox]}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
