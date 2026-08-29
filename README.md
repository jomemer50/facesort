# FaceSort

Sort your photo library into per-person folders by **face identity** — like Google
Photos, but local and private. Group photos are copied into **every** person's
folder who appears in them. Originals are never moved or deleted (non-destructive).

![modes: auto-cluster, reference matching, or both]

## Features
- **Native desktop GUI** (Python + PySide6) with native file dialogs — direct access to your file system.
- **Face recognition** via [InsightFace](https://github.com/deepinsight/insightface) `buffalo_l` (RetinaFace detector + ArcFace, 512-d embeddings).
- **Two identification modes** (use either or both):
  - **Auto-cluster**: faces are grouped automatically (DBSCAN on cosine distance); you name each cluster.
  - **Reference matching**: supply a few photos of known people; everything is matched against them.
- **Group photos** → copied into each recognized person's folder.
- **Fast re-scans**: detections are cached in a SQLite database keyed by file mtime. A **Force re-scan** option (in the GUI) drops the cache when you need a clean start.
- **CPU-first** (runs anywhere); GPU can be enabled later via `onnxruntime-gpu`.

## Install (from source)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```
On first run the `buffalo_l` model (~330 MB) downloads to `~/.insightface`.

## Run
```bash
facesort                 # launches the GUI
python -m facesort       # same
python -m facesort.scripts.demo   # build a 2-person sample library + group photo and sort it (great smoke test)
```

## How it works
1. **Scan** — recursively reads the input folder, detects faces, stores embeddings in a cache
   (`<input>/.facesort_cache.db`). Tick **Force re-scan** to ignore/regenerate the cache.
2. **Identify** — auto-clusters faces and/or matches against reference people.
3. **Sort** — copies each photo into `<output>/<PersonName>/`. A photo with multiple
   faces is copied into each of those people's folders. Unrecognized faces go to
   `<output>/Unknown/` (configurable). Filenames are de-duplicated (`photo_1.jpg`).

## Packaging (PyInstaller)
Produces a standalone native binary on each platform:
```bash
pip install pyinstaller
python build.py
# output: dist/FaceSort  (or FaceSort.exe on Windows, FaceSort.app on macOS)
```
Build on the OS you target (PyInstaller does not cross-compile).

## Project layout
```
src/facesort/
  core/        face engine, cache, scanner, clustering, matcher, sorter, pipeline
  ui/          PySide6 main window, cluster review, reference manager, widgets
  scripts/     demo + smoke CLI helpers
tests/         pytest suite (unit + full end-to-end with real faces)
```

## License / model terms
The application code is MIT. The `buffalo_l` InsightFace model is released for
**non-commercial research use only** — check InsightFace's license before any
commercial deployment.

## Limitations
- DBSCAN clustering is O(n²) in the number of faces; very large libraries may
  need a FAISS index (noted as a future optimization).
- A person who appears in **only** a single photo and is never named (or given a
  reference) cannot be identified; they land in `Unknown`.
