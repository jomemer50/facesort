from __future__ import annotations

import os

import PyInstaller.__main__
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

import insightface

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# InsightFace's get_object() resolves data files relative to sys._MEIPASS/objects
# when frozen, so its `data/objects` directory must be bundled at the bundle
# root as `objects/`. collect_data_files alone puts it under insightface/data/...
# which does NOT match, so add the explicit mapping.
_OBJECTS_SRC = os.path.join(os.path.dirname(insightface.__file__), "data", "objects")

_INSIGHTFACE_DATAS = [
    f"{src};{dest}" for src, dest in collect_data_files("insightface")
]
# Explicit: insightface/data/objects  ->  <bundle>/objects
_INSIGHTFACE_DATAS.append(f"{_OBJECTS_SRC};objects")

ARGS = [
    str(ROOT / "run.py"),
    "--name", "FaceSort",
    "--onefile",
    "--windowed",
    "--clean",
    "--paths", str(SRC),
    "--hidden-import", "sklearn",
    "--hidden-import", "scipy",
    "--hidden-import", "onnxruntime",
    "--hidden-import", "cv2",
    "--hidden-import", "insightface",
    "--hidden-import", "PySide6.QtWidgets",
    "--hidden-import", "PySide6.QtGui",
    "--hidden-import", "PySide6.QtCore",
]
for d in _INSIGHTFACE_DATAS:
    ARGS += ["--add-data", d]


def main() -> None:
    PyInstaller.__main__.run(ARGS)


if __name__ == "__main__":
    main()
