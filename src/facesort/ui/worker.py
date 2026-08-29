from __future__ import annotations

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    """Runs a callable off the GUI thread and reports progress / completion."""

    progress = Signal(int, int, str)  # current, total, current_path
    status = Signal(str)               # human-readable status text
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, fn, parent=None) -> None:
        super().__init__(parent)
        self.fn = fn

    def run(self) -> None:
        try:
            result = self.fn()
            self.finished.emit(result)
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))
