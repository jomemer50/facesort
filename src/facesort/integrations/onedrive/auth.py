from __future__ import annotations

import atexit
import json
import logging
import threading
from pathlib import Path

import msal

from .config import OneDriveAppConfig

logger = logging.getLogger(__name__)

_SCOPES_FOR_TOKEN = ["Files.ReadWrite", "offline_access", "User.Read"]


class OneDriveAuthError(RuntimeError):
    """Raised when authentication fails."""


class OneDriveAuth:
    """MSAL (public client) OAuth via the system browser + loopback redirect.

    Tokens are cached in ~/.facesort/onedrive_token.json via MSAL's
    SerializableTokenCache so re-launches reuse/refresh the session silently,
    and the user only re-consents when the cached token is revoked.
    """

    def __init__(
        self,
        app_config: OneDriveAppConfig | None = None,
        token_file: Path | None = None,
    ) -> None:
        self.app_config = app_config
        home = Path.home() / ".facesort"
        home.mkdir(parents=True, exist_ok=True)
        self.token_file = token_file or (home / "onedrive_token.json")
        self._cache = msal.SerializableTokenCache()
        if self.token_file.exists():
            try:
                self._cache.deserialize(self.token_file.read_text(encoding="utf-8"))
                logger.info("loaded cached OneDrive token")
            except Exception:  # noqa: BLE001
                logger.warning("could not deserialize OneDrive token cache")
        self._app: msal.ConfidentialClientApplication | None = None
        self._lock = threading.Lock()
        atexit.register(self._persist)

    def _get_app(self) -> msal.PublicClientApplication:
        if self.app_config is None:
            raise OneDriveAuthError(
                "OneDrive is not configured. Set FACESORT_ONEDRIVE_CLIENT_ID or "
                "create a onedrive_client.json with a 'client_id'."
            )
        acc = msal.PublicClientApplication(
            client_id=self.app_config.client_id,
            authority=self.app_config.authority,
            token_cache=self._cache,
        )
        # Keep the app alive across the interactive flow so the token cache
        # we serialize at exit matches the cache used by the flow.
        self._app = acc
        return acc

    def _persist(self) -> None:
        if not self._cache.has_state_changed:
            return
        try:
            self.token_file.write_text(
                self._cache.serialize(), encoding="utf-8"
            )
            logger.info("persisted OneDrive token cache")
        except OSError:  # pragma: no cover - IO failure
            logger.warning("could not persist OneDrive token cache")

    def get_accounts(self):
        app = self._get_app()
        return app.get_accounts()

    @property
    def is_connected(self) -> bool:
        return bool(self.get_accounts())

    def acquire_token_silent(self) -> dict | None:
        app = self._get_app()
        accounts = app.get_accounts()
        result = None
        for acc in accounts:
            result = app.acquire_token_silent(
                _SCOPES_FOR_TOKEN, account=acc, force_refresh=False
            )
            if result and "access_token" in result:
                break
        if result and "error" in result:
            logger.warning("silent token refresh failed: %s", result.get("error"))
            return None
        return result if (result and "access_token" in result) else None

    def get_token(self) -> str:
        """Return a valid access token, prompting the browser if needed."""
        silent = self.acquire_token_silent()
        if silent:
            return silent["access_token"]
        with self._lock:
            # Re-check under lock in case another thread already refreshed.
            silent = self.acquire_token_silent()
            if silent:
                return silent["access_token"]
            app = self._get_app()
            result = app.acquire_token_interactive(
                scopes=_SCOPES_FOR_TOKEN,
                port=self.app_config.redirect_uri.rsplit(":", 1)[-1]
                if ":" in self.app_config.redirect_uri
                else None,
            )
        if "access_token" not in result:
            raise OneDriveAuthError(
                "OneDrive authentication failed: "
                + str(result.get("error_description") or result.get("error"))
            )
        return result["access_token"]

    def account_username(self) -> str | None:
        accounts = self.get_accounts()
        if not accounts:
            return None
        return accounts[0].get("username")

    def disconnect(self) -> None:
        self._cache.reset()
        self._persist_with_force()
        self.token_file.unlink(missing_ok=True)
        self._app = None

    def _persist_with_force(self) -> None:
        self.token_file.write_text(self._cache.serialize(), encoding="utf-8")
