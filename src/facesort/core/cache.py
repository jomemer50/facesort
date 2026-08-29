from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

import numpy as np

from .models import Face

_SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    path      TEXT PRIMARY KEY,
    mtime     REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS faces (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path  TEXT NOT NULL,
    bbox        TEXT NOT NULL,
    det_score   REAL NOT NULL,
    kps         TEXT,
    embedding   BLOB NOT NULL,
    FOREIGN KEY(image_path) REFERENCES images(path) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_faces_image ON faces(image_path);
"""


class FaceCache:
    """SQLite-backed store of detected faces keyed by image path + mtime."""

    def __init__(self, db_path) -> None:
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def is_fresh(self, path, mtime: float) -> bool:
        row = self.conn.execute(
            "SELECT mtime FROM images WHERE path=?", (str(path),)
        ).fetchone()
        return row is not None and abs(row["mtime"] - mtime) < 1e-6

    def upsert(self, path, mtime: float, faces: list[Face]) -> None:
        with self._lock:
            cur = self.conn.cursor()
            cur.execute("BEGIN")
            cur.execute("DELETE FROM faces WHERE image_path=?", (str(path),))
            cur.execute(
                "INSERT OR REPLACE INTO images(path, mtime, updated_at) VALUES (?,?,?)",
                (str(path), float(mtime), time.time()),
            )
            for f in faces:
                cur.execute(
                    "INSERT INTO faces(image_path, bbox, det_score, kps, embedding) "
                    "VALUES (?,?,?,?,?)",
                    (
                        str(path),
                        json.dumps(f.bbox),
                        float(f.det_score),
                        json.dumps(f.kps) if f.kps is not None else None,
                        np.asarray(f.embedding, dtype=np.float32).tobytes(),
                    ),
                )
            self.conn.commit()

    def get_faces(self, path) -> list[Face]:
        rows = self.conn.execute(
            "SELECT bbox, det_score, kps, embedding FROM faces WHERE image_path=?",
            (str(path),),
        ).fetchall()
        return [self._row_to_face(r, str(path)) for r in rows]

    def iter_all_faces(self):
        rows = self.conn.execute(
            "SELECT image_path, bbox, det_score, kps, embedding FROM faces"
        ).fetchall()
        for r in rows:
            yield self._row_to_face(r, r["image_path"])

    def all_embeddings_with_paths(self):
        rows = self.conn.execute(
            "SELECT image_path, embedding FROM faces"
        ).fetchall()
        paths = [r["image_path"] for r in rows]
        embs = [np.frombuffer(r["embedding"], dtype=np.float32) for r in rows]
        return paths, embs

    def count_images(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]

    def count_faces(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM faces").fetchone()[0]

    def _row_to_face(self, r, path: str) -> Face:
        return Face(
            bbox=json.loads(r["bbox"]),
            det_score=float(r["det_score"]),
            embedding=np.frombuffer(r["embedding"], dtype=np.float32),
            kps=json.loads(r["kps"]) if r["kps"] else None,
            image_path=path,
        )
