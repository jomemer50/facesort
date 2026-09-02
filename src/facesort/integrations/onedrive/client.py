from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, Iterator

import requests

logger = logging.getLogger(__name__)

_DEFAULT_BASE = "https://graph.microsoft.com/v1.0"
_CHUNK_SIZE = 320 * 1024  # 320 KiB upload session fragments


class OneDriveError(RuntimeError):
    pass


class OneDriveClient:
    """Minimal Microsoft Graph client for the user's own OneDrive.

    ``item_id`` values are Drive item ids; ``"root"`` refers to the drive root.
    Works for both personal and organizational accounts via the ``me/drive``
    convenience endpoint.
    """

    def __init__(self, access_token: str, base_url: str | None = None) -> None:
        self.base_url = (base_url or _DEFAULT_BASE).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
        )

    # --- low-level -----------------------------------------------------
    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        resp = self.session.request(method, self._url(path), **kwargs)
        if resp.status_code in (401, 403):
            raise OneDriveError(
                f"OneDrive API {resp.status_code}: permission or token problem"
            )
        if resp.status_code >= 400:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except ValueError:
                pass
            raise OneDriveError(
                f"OneDrive API {resp.status_code}: {resp.reason} {detail}".strip()
            )
        return resp

    def _json(self, method: str, path: str, **kwargs) -> dict:
        return self._request(method, path, **kwargs).json()

    # --- drive info ----------------------------------------------------
    def whoami(self) -> dict:
        return self._json("GET", "/me")

    def drive_root(self) -> dict:
        return self._json("GET", "/me/drive/root")

    # --- listing -------------------------------------------------------
    def list_children(self, item_id: str = "root") -> Iterator[dict]:
        """Yield all children of a folder, following pagination."""
        url = f"/me/drive/items/{item_id}/children"
        while True:
            data = self._fetch_json(url)
            for v in data.get("value", []):
                yield v
            nxt = data.get("@odata.nextLink")
            if not nxt:
                break
            url = nxt  # absolute nextLink from Graph

    def _fetch_json(self, url: str) -> dict:
        from urllib.parse import urlparse

        if urlparse(url).netloc:
            return self.session.get(url).json()
        return self._json("GET", url)

    # --- download ------------------------------------------------------
    def download(self, item_id: str, dest: Path) -> None:
        resp = self._request("GET", f"/me/drive/items/{item_id}/content", stream=True)
        resp.raw.decode_content = True
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    fh.write(chunk)

    # --- upload --------------------------------------------------------
    def create_folder(self, name: str, parent_id: str = "root") -> str:
        body = {
            "name": name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename",
        }
        data = self._json(
            "POST", f"/me/drive/items/{parent_id}/children", json=body
        )
        return data["id"]

    def ensure_folder(self, name: str, parent_id: str = "root") -> str:
        """Find or create a folder; return its item id."""
        for child in self.list_children(parent_id):
            if "folder" in child and child.get("name") == name:
                return child["id"]
        return self.create_folder(name, parent_id)

    def upload_small(self, parent_id: str, name: str, local: Path) -> str:
        data = self._request(
            "PUT",
            f"/me/drive/items/{parent_id}:/{_quote(name)}:/content",
            data=local.read_bytes(),
            headers={"Content-Type": "application/octet-stream"},
        ).json()
        return data["id"]

    def upload(self, parent_id: str, name: str, local: Path) -> str:
        if local.stat().st_size < _CHUNK_SIZE:
            return self.upload_small(parent_id, name, local)
        return self._upload_session(parent_id, name, local)

    def _upload_session(self, parent_id: str, name: str, local: Path) -> str:
        created = self._json(
            "POST",
            f"/me/drive/items/{parent_id}:/{_quote(name)}:/createUploadSession",
            json={"item": {"@microsoft.graph.conflictBehavior": "rename"}},
        )
        upload_url = created["uploadUrl"]
        size = local.stat().st_size
        with open(local, "rb") as fh:
            offset = 0
            while offset < size:
                chunk = fh.read(_CHUNK_SIZE)
                end = min(offset + len(chunk), size) - 1
                headers = {
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{end}/{size}",
                }
                resp = self.session.put(upload_url, data=chunk, headers=headers)
                if resp.status_code in (200, 201):
                    return resp.json()["id"]
                if resp.status_code != 202:
                    raise OneDriveError(
                        f"upload fragment {resp.status_code}: {resp.reason}"
                    )
                offset += len(chunk)
        raise OneDriveError("upload session finished without final response")

    # --- helpers -------------------------------------------------------
    def walk_images(
        self,
        item_id: str,
        limit: int | None = None,
        progress: Callable[[int, str], None] | None = None,
    ) -> list[dict]:
        """Recursively collect image-file items under a folder."""
        IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
        result: list[dict] = []
        stack = [item_id]
        while stack:
            cur = stack.pop()
            for child in self.list_children(cur):
                name = (child.get("name") or "").lower()
                ext = Path(name).suffix
                if "folder" in child:
                    stack.append(child["id"])
                elif ext in IMAGE_EXTS:
                    result.append(child)
                    if limit is not None and len(result) >= limit:
                        if progress:
                            progress(len(result), "")
                        return result
                    if progress:
                        progress(len(result), child.get("name", ""))
        return result


def _quote(name: str) -> str:
    from urllib.parse import quote

    return quote(name, safe="")
