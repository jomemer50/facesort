from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QInputDialog,
    QPushButton,
    QListWidget,
    QVBoxLayout,
    QWidget,
)


class ReferenceManager(QWidget):
    """Manage named reference persons and their sample face images."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.session = None
        self.references: dict[str, list[str]] = {}  # name -> reference image paths
        layout = QVBoxLayout(self)

        box = QGroupBox("Reference people (optional)")
        v = QVBoxLayout(box)
        self.list = QListWidget()
        v.addWidget(self.list)

        row = QHBoxLayout()
        self.add_person_btn = QPushButton("Add person")
        self.add_ref_btn = QPushButton("Add reference images")
        self.add_ref_btn.setEnabled(False)
        row.addWidget(self.add_person_btn)
        row.addWidget(self.add_ref_btn)
        v.addLayout(row)
        layout.addWidget(box)

        self.add_person_btn.clicked.connect(self._add_person)
        self.add_ref_btn.clicked.connect(self._add_reference)
        self.list.currentItemChanged.connect(lambda *a: self._update_ref_btn())

    def set_session(self, session) -> None:
        self.session = session

    def _update_ref_btn(self) -> None:
        self.add_ref_btn.setEnabled(self.list.currentItem() is not None)

    def _add_person(self) -> None:
        name, ok = QInputDialog.getText(self, "New person", "Name:")
        if ok and name.strip():
            name = name.strip()
            self.references.setdefault(name, [])
            if self.session is not None:
                self.session.add_person(name)
            self.list.addItem(name)

    def _add_reference(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        name = item.text()
        files, _ = QFileDialog.getOpenFileNames(
            self, f"Reference images for {name}", "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp)",
        )
        for f in files:
            self.references.setdefault(name, []).append(f)
            if self.session is not None:
                self.session.add_reference_image(name, f)

    def apply_to_session(self, session) -> None:
        """Replay stored reference images into a (re)created session."""
        session.matcher.persons.clear()
        for name, paths in self.references.items():
            session.add_person(name)
            for f in paths:
                session.add_reference_image(name, f)
