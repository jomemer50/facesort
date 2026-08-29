from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow


def _redirect_streams_if_windowed() -> None:
    """In a PyInstaller --windowed build there is no console, so sys.stdout /
    sys.stderr are None. Libraries (e.g. InsightFace) print status messages
    during model loading, which would raise ``'NoneType' object has no
    attribute 'write'``. Redirect them to a log file instead."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_path = Path.home() / ".facesort" / "facesort.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "a", buffering=1, encoding="utf-8", errors="replace")
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file


def main() -> int:
    _redirect_streams_if_windowed()
    app = QApplication([])
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
