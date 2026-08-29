from __future__ import annotations

from pathlib import Path

import cv2
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QWidget,
)


class FolderPicker(QWidget):
    """Label + read-only path field + native Browse button."""

    def __init__(self, label: str, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(label))
        self.line = QLineEdit()
        self.line.setReadOnly(True)
        layout.addWidget(self.line, 1)
        self.btn = QPushButton("Browse…")
        self.btn.clicked.connect(self._browse)
        layout.addWidget(self.btn)

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select folder")
        if d:
            self.line.setText(d)

    def path(self) -> str:
        return self.line.text().strip()

    def set_path(self, p: str) -> None:
        self.line.setText(p)


class ThumbnailLabel(QLabel):
    """Renders a cropped face thumbnail from a cached ``Face``."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(96, 96)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid #888;")

    def set_face(self, face, size: int = 96) -> None:
        img = cv2.imread(face.image_path)
        if img is None:
            return
        x1, y1, x2, y2 = [int(round(v)) for v in face.bbox]
        h, w = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return
        crop = img[y1:y2, x1:x2]
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0],
                      rgb.shape[1] * 3, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(
            size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(pix)
