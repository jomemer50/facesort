from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

_CONFIG_FILENAMES = ("onedrive_client.json", "client_config.onedrive.json")
_CLIENT_ID_ENV = "FACESORT_ONEDRIVE_CLIENT_ID"
_DEFAULT_AUTHORITY = "https://login.microsoftonline.com/common"


@dataclass
class OneDriveAppConfig:
    client_id: str
    authority: str = _DEFAULT_AUTHORITY
    redirect_uri: str = "http://localhost"
    scopes: list[str] = field(
        default_factory=lambda: [
            "Files.ReadWrite",
            "offline_access",
            "User.Read",
        ]
    )


def search_paths() -> list[Path]:
    paths: list[Path] = []
    for base in (Path.cwd(), Path.home() / ".facesort", Path.home()):
        for name in _CONFIG_FILENAMES:
            cand = base / name
            if cand not in paths:
                paths.append(cand)
    return paths


def load_config(
    explicit_path: str | None = None,
) -> OneDriveAppConfig | None:
    """Load OAuth config from env var or a local client config file.

    Precedence: explicit path > env var > config files on disk.
    Returns ``None`` when no client id is configured.
    """
    if explicit_path:
        p = Path(explicit_path)
        if p.exists():
            return _from_file(p)
        return None

    env = os.environ.get(_CLIENT_ID_ENV)
    if env:
        return OneDriveAppConfig(client_id=env.strip())

    for p in search_paths():
        if p.exists():
            cfg = _from_file(p)
            if cfg is not None:
                return cfg
    return None


def _from_file(p: Path) -> OneDriveAppConfig | None:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    client_id = data.get("client_id") or data.get("clientId") or data.get("id")
    if not client_id:
        return None
    return OneDriveAppConfig(
        client_id=str(client_id).strip(),
        authority=str(data.get("authority") or _DEFAULT_AUTHORITY),
        redirect_uri=str(data.get("redirect_uri") or "http://localhost"),
    )
