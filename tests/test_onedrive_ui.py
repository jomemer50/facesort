import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTreeWidgetItem

from facesort.ui.integrations_panel import IntegrationsPanel
from facesort.ui.one_picker import OneDrivePicker


def _app():
    return QApplication.instance() or QApplication([])


class _FakeClient:
    def __init__(self, tree):
        self.tree = tree

    def list_children(self, item_id="root"):
        return iter(self.tree.get(item_id, []))


class _FakeAuth:
    def __init__(self, connected=True, username="me@example.com"):
        self.connected = connected
        self.username = username

    @property
    def is_connected(self):
        return self.connected

    def account_username(self):
        return self.username

    def get_token(self):
        return "fake-token"

    def disconnect(self):
        self.connected = False


def test_picker_applies_children() -> None:
    _app()
    pick = OneDrivePicker(lambda: None)
    root_item = pick.tree.topLevelItem(0)
    tree = {
        "root": [
            {"id": "f1", "name": "Albums", "folder": {}},
            {"id": "i1", "name": "a.jpg"},
        ],
    }
    client = _FakeClient(tree)
    root_children = list(client.list_children("root"))
    pick._apply_children(root_item, root_children)
    assert root_item.childCount() == 1
    folder_row = root_item.child(0)
    assert folder_row.text(0) == "Albums"
    assert folder_row.data(0, Qt.UserRole) == "f1"


def test_picker_select_node() -> None:
    _app()
    pick = OneDrivePicker(lambda: None)
    pick.selected = None
    node = QTreeWidgetItem(["Albums"])
    node.setData(0, Qt.UserRole, "f1")
    pick._select_node(node)
    assert pick.selected == ("f1", "Albums")
    assert pick.ok_btn.isEnabled()


def test_panel_construct_not_connected() -> None:
    _app()
    panel = IntegrationsPanel(auth=_FakeAuth(connected=False))
    assert not panel.is_connected()
    assert panel.output_parent() is None


def test_panel_connected_state() -> None:
    _app()
    panel = IntegrationsPanel(auth=_FakeAuth(connected=True))
    assert panel.is_connected()
    panel._disconnect()
    assert not panel.is_connected()


def test_mainwindow_has_integrations_panel() -> None:
    from PySide6.QtWidgets import QApplication as QA

    qa = QA.instance() or QA([])
    from facesort.ui.main_window import MainWindow

    win = MainWindow()
    assert win.integrations is not None
    assert win.upload_btn is not None
    assert not win.upload_btn.isEnabled()
