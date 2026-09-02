from pathlib import Path

import pytest
from pytest_httpserver import HTTPServer

from facesort.integrations.onedrive.client import OneDriveClient
from facesort.integrations.onedrive.config import load_config
from facesort.integrations.onedrive.sync import stage_folder, upload_tree


# ------------------------------------------------------------------ client
def _client(server: HTTPServer) -> OneDriveClient:
    return OneDriveClient("fake-token", base_url=server.url_for(""))


def test_list_children_follows_pagination(httpserver: HTTPServer) -> None:
    httpserver.expect_request(
        "/me/drive/items/root/children", query_string={}
    ).respond_with_json(
        {
            "value": [{"id": "a", "name": "x.jpg", "folder": None}],
            "@odata.nextLink": httpserver.url_for(
                "/me/drive/items?page=2"
            ),
        }
    )
    httpserver.expect_request(
        "/me/drive/items", query_string={"page": "2"}
    ).respond_with_json(
        {"value": [{"id": "b", "name": "y.jpg", "folder": None}]}
    )
    items = list(_client(httpserver).list_children("root"))
    assert [n["name"] for n in items] == ["x.jpg", "y.jpg"]


def test_walk_images_recursive(httpserver: HTTPServer) -> None:
    server = httpserver
    server.expect_request("/me/drive/items/folder/children").respond_with_json(
        {
            "value": [
                {"id": "pic", "name": "a.JPG"},
                {"id": "sub", "name": "sub", "folder": {}},
                {"id": "txt", "name": "notes.txt"},
            ]
        }
    )
    server.expect_request("/me/drive/items/sub/children").respond_with_json(
        {"value": [{"id": "inner", "name": "b.png"}]}
    )
    found = _client(server).walk_images("folder")
    names = sorted(item["name"] for item in found)
    assert names == ["a.JPG", "b.png"]


def test_ensure_folder_finds_existing(httpserver: HTTPServer) -> None:
    server = httpserver
    server.expect_request("/me/drive/items/root/children").respond_with_json(
        {"value": [{"id": "f1", "name": "Alice", "folder": {}}]}
    )
    c = _client(server)
    assert c.ensure_folder("Alice", "root") == "f1"


def test_ensure_folder_creates_missing(httpserver: HTTPServer) -> None:
    server = httpserver
    server.expect_request(
        "/me/drive/items/root/children", method="GET"
    ).respond_with_json({"value": []})
    server.expect_request(
        "/me/drive/items/root/children", method="POST"
    ).respond_with_json({"id": "new-folder"})
    assert _client(server).ensure_folder("Alice", "root") == "new-folder"


def test_upload_small(httpserver: HTTPServer, tmp_path: Path) -> None:
    server = httpserver
    f = tmp_path / "a.jpg"
    f.write_bytes(b"abc")
    server.expect_request(
        "/me/drive/items/folder:/a.jpg:/content", method="PUT"
    ).respond_with_json({"id": "file1"})
    assert _client(server).upload("folder", "a.jpg", f) == "file1"


def test_api_error_raises(httpserver: HTTPServer) -> None:
    server = httpserver
    server.expect_request("/me/drive/root").respond_with_json(
        {"error": {"code": "invalid", "message": "nope"}}, status=400
    )
    with pytest.raises(Exception):
        _client(server).drive_root()


# -------------------------------------------------------------------- sync
class _FakeClient:
    def __init__(self, items, downloads=None):
        self.items = items
        self.downloads = downloads or {}
        self.uploads = []
        self.downloaded = []

    def walk_images(self, item_id):
        return self.items

    def download(self, item_id, dest):
        self.downloaded.append(item_id)
        dest.write_bytes(self.downloads.get(item_id, b"data"))

    def ensure_folder(self, name, parent_id="root"):
        self.uploads.append(("ensure", name, parent_id))
        return f"{name}-id"

    def upload(self, parent_id, name, local):
        self.uploads.append(("upload", parent_id, name))


def test_stage_folder_downloads_images(tmp_path: Path) -> None:
    fake = _FakeClient(
        items=[{"id": "id1", "name": "a.jpg"}, {"id": "id2", "name": "b.png"}]
    )
    root = tmp_path / "stage"
    root.mkdir()
    n = stage_folder(fake, "folder", root)
    assert n == 2
    assert (root / "id1.jpg").exists()
    assert (root / "id2.png").exists()
    # re-run: cached, no re-download
    fake.downloaded.clear()
    n2 = stage_folder(fake, "folder", root)
    assert n2 == 2
    assert fake.downloaded == []


def test_upload_tree_uploads_person_folders(tmp_path: Path) -> None:
    out = tmp_path / "out"
    (out / "Alice").mkdir(parents=True)
    (out / "Bob").mkdir()
    (out / "Alice" / "a.jpg").write_bytes(b"1")
    (out / "Alice" / "b.jpg").write_bytes(b"2")
    (out / "Bob" / "c.jpg").write_bytes(b"3")
    fake = _FakeClient(items=[])
    counts = upload_tree(fake, out, parent_id="root")
    assert counts == {"Alice": 2, "Bob": 1}


# ------------------------------------------------------------------ config
def test_load_config_env(monkeypatch) -> None:
    monkeypatch.setenv("FACESORT_ONEDRIVE_CLIENT_ID", "abc-123")
    cfg = load_config()
    assert cfg is not None and cfg.client_id == "abc-123"


def test_load_config_file(tmp_path: Path) -> None:
    f = tmp_path / "onedrive_client.json"
    f.write_text('{"client_id": "file-id"}')
    cfg = load_config(str(f))
    assert cfg is not None and cfg.client_id == "file-id"


def test_load_config_returns_none_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("FACESORT_ONEDRIVE_CLIENT_ID", raising=False)
    assert load_config(str(Path("/nonexistent/x/onedrive_client.json"))) is None
