from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.pipeline import Session
from .cluster_review import ClusterReview
from .integrations_panel import IntegrationsPanel
from .reference_manager import ReferenceManager
from .widgets import FolderPicker
from .worker import Worker


MODES = {
    "Auto-cluster": {"cluster"},
    "Reference matching": {"reference"},
    "Both (cluster + reference)": {"cluster", "reference"},
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FaceSort")
        self.resize(900, 700)
        self.session: Session | None = None
        self._scan_worker: Worker | None = None
        self._sort_worker: Worker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        self.integrations = IntegrationsPanel()
        self.integrations.on_input_staged = self._on_onedrive_input_staged
        self.integrations.on_output_chosen = self._on_onedrive_output_chosen
        root.addWidget(self.integrations)

        self.input_picker = FolderPicker("Input folder:")
        self.output_picker = FolderPicker("Output folder:")
        root.addWidget(self.input_picker)
        root.addWidget(self.output_picker)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(MODES.keys())
        mode_row.addWidget(self.mode_combo, 1)
        self.force_checkbox = QCheckBox("Force re-scan (ignore cache)")
        mode_row.addWidget(self.force_checkbox)
        root.addLayout(mode_row)

        self.ref_manager = ReferenceManager()
        root.addWidget(self.ref_manager)

        btn_row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan")
        self.sort_btn = QPushButton("Sort")
        self.sort_btn.setEnabled(False)
        self.upload_btn = QPushButton("Upload to OneDrive")
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self._run_upload)
        btn_row.addWidget(self.scan_btn)
        btn_row.addWidget(self.sort_btn)
        btn_row.addWidget(self.upload_btn)
        root.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        root.addWidget(self.progress)
        self.status = QLabel("Ready.")
        root.addWidget(self.status)

        self.cluster_review = ClusterReview()
        root.addWidget(self.cluster_review, 1)

        self.scan_btn.clicked.connect(self._run_scan)
        self.sort_btn.clicked.connect(self._run_sort)

    # --- helpers ----------------------------------------------------------
    def _current_modes(self) -> set[str]:
        return set(MODES[self.mode_combo.currentText()])

    def _set_status(self, text: str) -> None:
        self.status.setText(text)

    # --- OneDrive ---------------------------------------------------------
    def _on_onedrive_input_staged(self, local_dir, od_info) -> None:
        self.input_picker.set_path(str(local_dir))
        self.upload_btn.setEnabled(
            od_info is not None and self.integrations.output_parent() is not None
        )

    def _on_onedrive_output_chosen(self, od_info, staging_dir) -> None:
        self.output_picker.set_path(str(staging_dir))
        self.upload_btn.setEnabled(True)
        self._set_status(
            "OneDrive output set. Run Scan + Sort, then click 'Upload to OneDrive'."
        )

    def _run_upload(self) -> None:
        out_path = self.output_picker.path()
        if not out_path or not Path(out_path).is_dir():
            QMessageBox.warning(self, "Upload", "Select a valid output folder first.")
            return
        self.upload_btn.setEnabled(False)
        self.progress.setRange(0, 0)
        self._set_status("Uploading to OneDrive…")
        w = self.integrations.upload_output(Path(out_path))
        if w is None:
            QMessageBox.information(
                self, "Upload", "No OneDrive output selected yet."
            )
            self.upload_btn.setEnabled(False)
            self.progress.setRange(0, 1)
            self._set_status("Ready.")
            return
        w.finished.connect(lambda _r: self._on_upload_done())
        w.error.connect(self._on_upload_error)

    def _on_upload_done(self) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.upload_btn.setEnabled(True)
        self._set_status("Upload to OneDrive complete.")

    def _on_upload_error(self, msg: str) -> None:
        self.progress.setRange(0, 1)
        self.upload_btn.setEnabled(True)
        QMessageBox.critical(self, "Upload error", msg)
        self._set_status("OneDrive upload failed.")

    # --- scan -------------------------------------------------------------
    def _run_scan(self) -> None:
        in_path = self.input_picker.path()
        out_path = self.output_picker.path()
        if not in_path or not Path(in_path).is_dir():
            QMessageBox.warning(self, "Input", "Select a valid input folder.")
            return
        if not out_path or not Path(out_path).is_dir():
            QMessageBox.warning(self, "Output", "Select a valid output folder.")
            return

        self.scan_btn.setEnabled(False)
        self.sort_btn.setEnabled(False)
        self.progress.setRange(0, 0)
        self._set_status("Loading face-recognition model… (first run downloads ~330 MB)")

        # Build the Session (and load/download the model) OFF the GUI thread so
        # the window stays responsive and we can show status/progress.
        in_p, out_p = in_path, out_path
        force = self.force_checkbox.isChecked()

        def do_work():
            self._scan_worker.status.emit("Loading face-recognition model…")
            if force:
                # Drop any previously cached (possibly empty) results first.
                db = Path(in_p) / ".facesort_cache.db"
                if db.exists():
                    db.unlink()
            session = Session(input_root=in_p, output_root=out_p)
            self.ref_manager.apply_to_session(session)
            self.session = session
            return session.scan(
                progress=lambda i, t, p: self._scan_worker.progress.emit(i, t, p)
            )

        self._scan_worker = Worker(fn=do_work)
        self._scan_worker.status.connect(self._set_status)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_scan_done)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    def _on_scan_progress(self, i: int, total: int, path: str) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(i)
        self._set_status(f"Scanning {i}/{total}: {Path(path).name}")

    def _on_scan_done(self, result) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self._set_status(
            f"Scanned {result.scanned} images, {result.faces} faces "
            f"({result.cached} cached)."
        )
        if "cluster" in self._current_modes():
            self.session.cluster()
            self.cluster_review.populate(self.session.cluster_groups())
        self.scan_btn.setEnabled(True)
        self.sort_btn.setEnabled(True)

    def _on_scan_error(self, msg: str) -> None:
        self.progress.setRange(0, 1)
        self.scan_btn.setEnabled(True)
        QMessageBox.critical(self, "Scan error", msg)
        self._set_status("Scan failed.")

    # --- sort -------------------------------------------------------------
    def _run_sort(self) -> None:
        if self.session is None:
            return
        modes = self._current_modes()
        if "cluster" in modes:
            # Auto-name included-but-unnamed clusters ("Person 1", …) so Sort
            # always produces output; the user can rename folders afterwards.
            n = 1
            for cid, edit, include in self.cluster_review.cards:
                if include.isChecked():
                    name = edit.text().strip() or f"Cluster {cid}"
                    n += 1
                    self.session.name_cluster(cid, name)

        self.sort_btn.setEnabled(False)
        self.progress.setRange(0, 0)

        def prog(i, total, p):
            self._sort_worker.progress.emit(i, total, p)

        self._sort_worker = Worker(
            fn=lambda: self.session.sort(modes, unknown_folder="Unknown")
        )
        self._sort_worker.finished.connect(self._on_sort_done)
        self._sort_worker.error.connect(self._on_sort_error)
        self._sort_worker.start()

    def _on_sort_done(self, counts: dict) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.sort_btn.setEnabled(True)
        if not counts:
            QMessageBox.warning(
                self,
                "Nothing to sort",
                "No photos were copied. This usually means there were no named "
                "clusters and no reference people.\n\n"
                "In Auto-cluster mode, type a name for at least one cluster "
                "(or leave it blank to use 'Person 1', etc.). In Reference mode, "
                "add at least one reference photo.",
            )
            self._set_status("Sort produced no output.")
            return
        summary = "\n".join(f"  {name}: {n} photo(s)" for name, n in sorted(counts.items()))
        QMessageBox.information(self, "Sorting complete", f"Copied photos into:\n{summary}")
        self._set_status(f"Sorted into {len(counts)} folders.")

    def _on_sort_error(self, msg: str) -> None:
        self.progress.setRange(0, 1)
        self.sort_btn.setEnabled(True)
        QMessageBox.critical(self, "Sort error", msg)
        self._set_status("Sort failed.")
