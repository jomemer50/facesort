from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.models import Face
from .widgets import ThumbnailLabel


class ClusterReview(QScrollArea):
    """Shows auto-detected clusters; user assigns a name to each."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.cards: list[tuple[int, QLineEdit, QCheckBox]] = []

    def populate(self, groups: dict[int, list[Face]], max_thumbs: int = 8) -> None:
        self.clear()
        # Put noise (-1) last; order others by size descending.
        items = sorted(
            groups.items(), key=lambda kv: (kv[0] == -1, -len(kv[1]))
        )
        for cid, faces in items:
            title = "Unclustered (noise)" if cid == -1 else f"Cluster {cid}"
            box = QGroupBox(f"{title}  ({len(faces)} faces)")
            v = QVBoxLayout(box)

            strip = QHBoxLayout()
            for f in faces[:max_thumbs]:
                t = ThumbnailLabel()
                try:
                    t.set_face(f)
                except Exception:
                    pass
                strip.addWidget(t)
            strip.addStretch(1)
            v.addLayout(strip)

            row = QHBoxLayout()
            if cid != -1:
                include = QCheckBox("include")
                include.setChecked(True)
                row.addWidget(include)
            name_edit = QLineEdit()
            name_edit.setPlaceholderText("Person name…")
            row.addWidget(QLabel("Name:"))
            row.addWidget(name_edit, 1)
            v.addLayout(row)

            self.layout.addWidget(box)
            if cid != -1:
                self.cards.append((cid, name_edit, include))

    def clear(self) -> None:
        while self.layout.count():
            child = self.layout.takeAt(0)
            w = child.widget()
            if w:
                w.deleteLater()
        self.cards.clear()

    def collect(self) -> dict[int, str]:
        """Return {cluster_id: name} for included, named clusters."""
        result: dict[int, str] = {}
        for cid, edit, include in self.cards:
            if include.isChecked():
                name = edit.text().strip()
                if name:
                    result[cid] = name
        return result
