from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..integrations.onedrive.auth import OneDriveAuth
from ..integrations.onedrive.client import OneDriveClient
from ..integrations.onedrive.config import load_config
from ..integrations.onedrive.sync import default_cache_dir, stage_folder, upload_tree
from .one_picker import OneDrivePicker
from .worker import Worker


class IntegrationsPanel(QGroupBox):
    """OneDrive connect + use-as-input/output controls.

    Communicates with the rest of the app via the ``on_input_staged`` and
    ``on_output_chosen`` callbacks (set by the owner) so the panel stays
    decoupled from a particular window/state.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        auth: OneDriveAuth | None = None,
    ) -> None:
        super().__init__("Cloud", parent)
        self._auth = auth  # may be None -> built lazily from config
        self._client: OneDriveClient | None = None
        self._od_out: tuple[str, str] | None = None
        self._staged_dir: Path | None = None

        self.on_input_staged: Callable[[Path, tuple[str, str]], None] | None = None
        self.on_output_chosen: Callable[[tuple[str, str], Path], None] | None = None

        v = QVBoxLayout(self)

        self.od_status = QLabel("OneDrive: not connected.")
        v.addWidget(self.od_status)

        row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect OneDrive…")
        self.connect_btn.clicked.connect(self._connect)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self._disconnect)
        self.disconnect_btn.setEnabled(False)
        row.addWidget(self.connect_btn)
        row.addWidget(self.disconnect_btn)
        row.addStretch(1)
        v.addLayout(row)

        row2 = QHBoxLayout()
        self.in_btn = QPushButton("Use OneDrive as input…")
        self.in_btn.clicked.connect(self._browse_input)
        self.out_btn = QPushButton("Use OneDrive as output…")
        self.out_btn.clicked.connect(self._browse_output)
        row2.addWidget(self.in_btn)
        row2.addWidget(self.out_btn)
        row2.addStretch(1)
        v.addLayout(row2)

        self.note = QLabel("")
        self.note.setWordWrap(True)
        v.addWidget(self.note)

        self._sync_emoji()
        if load_config() is None:
            self.od_status.setText(
                "OneDrive: not configured (set FACESORT_ONEDRIVE_CLIENT_ID or "
                "add onedrive_client.json)."
            )
            self.connect_btn.setEnabled(False)

    # --- auth -------------------------------------------------------------
    def _get_auth(self) -> OneDriveAuth:
        if self._auth is None:
            self._auth = OneDriveAuth(app_config=load_config())
            if self._auth.is_connected:
                self._client = OneDriveClient(self._auth.get_token())
        return self._auth

    def _client_provider(self) -> OneDriveClient:
        if self._client is None:
            token = self._get_auth().get_token()
            self._client = OneDriveClient(token)
        return self._client

    def is_connected(self) -> bool:
        try:
            self._get_auth()
        except Exception:  # noqa: BLE001
            return False
        return self._auth.is_connected if self._auth else False

    def _sync_emoji(self) -> None:
        try:
            connected = self._auth is not None and self._auth.is_connected
        except Exception:  # noqa: BLE001
            connected = False
        if connected:
            self.od_status.setText(
                f"OneDrive: connected ({self._auth.account_username()})."
            )
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
        else:
            self.od_status.setText("OneDrive: not connected.")
            self.connect_btn.setEnabled(load_config() is not None)

    def _connect(self) -> None:
        cfg = load_config()
        if cfg is None:
            return
        self.connect_btn.setEnabled(False)
        self.od_status.setText("Opening browser for OneDrive sign-in…")

        def work():
            auth = self._get_auth()
            auth.get_token()
            self._client = OneDriveClient(auth.get_token())
            return auth.account_username()

        def done(username) -> None:
            self.od_status.setText(f"OneDrive: connected ({username}).")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)

        def err(msg) -> None:
            self.od_status.setText(f"OneDrive: sign-in failed ({msg}).")
            self.connect_btn.setEnabled(True)

        self._worker = Worker(work, self)
        self._worker.finished.connect(done)
        self._worker.error.connect(err)
        self._worker.start()

    def _disconnect(self) -> None:
        try:
            self._get_auth().disconnect()
        except Exception:  # noqa: BLE001
            pass
        self._client = None
        self._od_out = None
        self._sync_emoji()

    # --- input / output ---------------------------------------------------
    def _browse_input(self) -> None:
        if not self.is_connected():
            return
        pick = OneDrivePicker(self._client_provider, "Choose a OneDrive input folder", self)
        if pick.exec_() and pick.selected:
            item_id, name = pick.selected
            self._stage(item_id, name)

    def _browse_output(self) -> None:
        if not self.is_connected():
            return
        pick = OneDrivePicker(
            self._client_provider, "Choose a OneDrive output folder", self
        )
        if pick.exec_() and pick.selected:
            item_id, name = pick.selected
            self._od_out = (item_id, name)
            # Local staging dir that Sort writes into before upload.
            staging = default_cache_dir().parent / "onedrive-out" / item_id
            staging.mkdir(parents=True, exist_ok=True)
            self._staged_dir = staging
            self.note.setText(
                "OneDrive output: sorting locally, will upload to "
                f"'{name}' after Sort."
            )
            if self.on_output_chosen:
                self.on_output_chosen(pick.selected, staging)

    def _stage(self, item_id: str, name: str) -> None:
        self.in_btn.setEnabled(False)
        self.note.setText(f"Downloading '{name}' from OneDrive…")
        dest = default_cache_dir() / item_id
        dest.mkdir(parents=True, exist_ok=True)

        def work():
            client = self._client_provider()
            return stage_folder(client, item_id, dest)

        def done(count) -> None:
            self.in_btn.setEnabled(True)
            self._staged_dir = dest
            self.note.setText(
                f"Downloaded {count} image(s) from OneDrive to a local cache."
            )
            if self.on_input_staged:
                self.on_input_staged(dest, (item_id, name))

        def err(msg) -> None:
            self.in_btn.setEnabled(True)
            self.note.setText(f"OneDrive download failed: {msg}")

        self._worker = Worker(work, self)
        self._worker.finished.connect(done)
        self._worker.error.connect(err)
        self._worker.start()

    # --- upload -----------------------------------------------------------
    def output_parent(self) -> tuple[str, str] | None:
        return self._od_out

    def upload_output(self, local_root: Path, progress=None) -> Worker | None:
        if self._od_out is None:
            return None
        parent_id, name = self._od_out
        self.note.setText(f"Uploading to OneDrive ('{name}')…")

        def work():
            client = self._client_provider()
            return upload_tree(client, local_root, parent_id)

        self._worker = Worker(work, self)
        self._worker.finished.connect(
            lambda counts: self.note.setText(
                f"OneDrive upload complete: "
                + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
            )
        )
        self._worker.error.connect(
            lambda msg: self.note.setText(f"OneDrive upload failed: {msg}")
        )
        self._worker.start()
        return self._worker
