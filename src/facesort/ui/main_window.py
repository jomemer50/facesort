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
        btn_row.addWidget(self.scan_btn)
        btn_row.addWidget(self.sort_btn)
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
            for cid, name in self.cluster_review.collect().items():
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
        summary = "\n".join(f"  {name}: {n} photo(s)" for name, n in sorted(counts.items()))
        QMessageBox.information(self, "Sorting complete", f"Copied photos into:\n{summary}")
        self._set_status(f"Sorted into {len(counts)} folders.")

    def _on_sort_error(self, msg: str) -> None:
        self.progress.setRange(0, 1)
        self.sort_btn.setEnabled(True)
        QMessageBox.critical(self, "Sort error", msg)
        self._set_status("Sort failed.")
