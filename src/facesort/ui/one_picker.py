from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..integrations.onedrive.client import OneDriveClient
from .worker import Worker

# Non-folder items are hidden from the tree; images/folders are distinguished by
# the presence of a "folder" facet in the Graph children response.
_LOADING = "<loading…>"


class OneDrivePicker(QDialog):
    """Browse a OneDrive folder tree (lazy, background-loaded) and pick one.

    Use ``exec_()`` and then read :attr:`selected` which is a tuple
    ``(item_id, name)`` for the chosen folder, or ``None`` if cancelled.
    """

    def __init__(
        self,
        client_provider: Callable[[], OneDriveClient],
        title: str = "Choose a OneDrive folder",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(520, 460)
        self._client_provider = client_provider
        self._client: OneDriveClient | None = None
        self.selected: tuple[str, str] | None = None
        self._worker: Worker | None = None
        self._path: list[tuple[str, str]] = [("root", "My Drive / root")]
        self._loaded: set[str] = set()
        self._loading_nodes: set[str] = set()

        root = QVBoxLayout(self)
        self.breadcrumb = QLabel(self._path_str())
        root.addWidget(self.breadcrumb)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        self.tree.itemExpanded.connect(self._on_expanded)
        self.tree.itemDoubleClicked.connect(self._on_double_clicked)
        root.addWidget(self.tree, 1)

        self.result_lbl = QLabel("Select a folder to use.")
        root.addWidget(self.result_lbl)

        btns = QHBoxLayout()
        self.ok_btn = QPushButton("Use selected")
        self.ok_btn.setEnabled(False)
        self.ok_btn.clicked.connect(self._accept_current)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch(1)
        btns.addWidget(self.ok_btn)
        btns.addWidget(cancel_btn)
        root.addLayout(btns)

        self._populate_root()

    # --- helpers ----------------------------------------------------------
    def _path_str(self) -> str:
        return " / ".join(n for _, n in self._path)

    def _build_client(self) -> OneDriveClient:
        if self._client is None:
            self._client = self._client_provider()
        return self._client

    def _populate_root(self) -> None:
        node = QTreeWidgetItem(["My Drive / root"])
        node.setData(0, Qt.UserRole, "root")
        node.addChild(QTreeWidgetItem([_LOADING]))
        self.tree.addTopLevelItem(node)
        node.setExpanded(True)

    # --- event handlers ---------------------------------------------------
    def _on_expanded(self, item: QTreeWidgetItem) -> None:
        node_id = item.data(0, Qt.UserRole)
        if node_id in self._loaded:
            return
        self._update_path(item)
        self._load_children(item, node_id)

    def _on_double_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        self._update_path(item)
        node_id = item.data(0, Qt.UserRole)
        if node_id == "root" or "folder" in (
            item.data(0, Qt.UserRole + 1) or ""
        ):
            self._select_node(item)

    def _update_path(self, item: QTreeWidgetItem) -> None:
        trail: list[tuple[str, str]] = []
        cur: QTreeWidgetItem | None = item
        while cur is not None:
            trail.insert(0, (cur.data(0, Qt.UserRole), cur.text(0)))
            cur = cur.parent()
        self._path = trail
        self.breadcrumb.setText(self._path_str())

    def _select_node(self, item: QTreeWidgetItem) -> None:
        node_id = item.data(0, Qt.UserRole)
        if node_id == "root":
            self.selected = ("root", "My Drive / root")
        else:
            self.selected = (node_id, item.text(0))
        self.ok_btn.setEnabled(True)
        self.result_lbl.setText(f"Selected: {self._path_str()}")

    def _accept_current(self) -> None:
        if self.selected:
            self.accept()

    # --- background loading -----------------------------------------------
    def _load_children(self, item: QTreeWidgetItem, node_id: str) -> None:
        if node_id in self._loading_nodes:
            return
        self._loading_nodes.add(node_id)

        def work():
            client = self._build_client()
            return list(client.list_children(node_id))

        def on_done(children: list) -> None:
            self._loading_nodes.discard(node_id)
            self._loaded.add(node_id)
            self._apply_children(item, children)

        def on_error(msg: str) -> None:
            self._loading_nodes.discard(node_id)
            item.takeChildren()
            item.addChild(QTreeWidgetItem([f"error: {msg}"]))

        self._worker = Worker(work, self)
        self._worker.finished.connect(on_done)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _apply_children(self, item: QTreeWidgetItem, children: list) -> None:
        """Replace ``item``'s placeholder with folder rows from ``children``."""
        item.takeChildren()
        for child in children:
            cid = child.get("id")
            name = child.get("name") or "unnamed"
            if "folder" in child:
                row = QTreeWidgetItem([name])
                row.setData(0, Qt.UserRole, cid)
                row.setData(0, Qt.UserRole + 1, "folder")
                row.addChild(QTreeWidgetItem([_LOADING]))
                item.addChild(row)
        if item.childCount() == 0:
            item.addChild(QTreeWidgetItem(["empty"]))
