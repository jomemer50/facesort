import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from facesort.ui.cluster_review import ClusterReview
from facesort.ui.main_window import MainWindow


def _app():
    return QApplication.instance() or QApplication([])


def test_mainwindow_constructs() -> None:
    _app()
    win = MainWindow()
    assert win.mode_combo.count() == 3

    win.mode_combo.setCurrentText("Auto-cluster")
    assert win._current_modes() == {"cluster"}

    win.mode_combo.setCurrentText("Reference matching")
    assert win._current_modes() == {"reference"}

    win.mode_combo.setCurrentText("Both (cluster + reference)")
    assert win._current_modes() == {"cluster", "reference"}


def test_cluster_review_collect_empty() -> None:
    _app()
    cr = ClusterReview()
    cr.populate({})
    assert cr.collect() == {}


def test_mainwindow_importable() -> None:
    import facesort.app as app

    assert callable(app.main)
