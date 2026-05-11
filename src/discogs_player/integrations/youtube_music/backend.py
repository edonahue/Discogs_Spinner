"""YouTube Music player backend (v1: unauthenticated album search + open in browser)."""

from __future__ import annotations

import importlib.util
import webbrowser

from discogs_player.integrations.player_backend import (
    PlayerBackend,
    ProviderDescriptor,
)
from discogs_player.integrations.youtube_music.auth import get_youtube_music_auth_diagnostics
from discogs_player.integrations.youtube_music.ytmusic_client import YouTubeMusicClient

_YTM_BROWSE_BASE = "https://music.youtube.com/browse/"

_BROWSER_DEVICE: dict[str, object] = {
    "id": "browser",
    "name": "Browser (YouTube Music)",
    "type": "Browser",
    "is_active": True,
    "is_restricted": False,
}


class YouTubeMusicPlayerBackend(PlayerBackend):
    """v1 YouTube Music backend: unauthenticated search + open album in browser."""

    @property
    def name(self) -> str:
        return "youtube_music"

    @classmethod
    def addon_available(cls) -> bool:
        return importlib.util.find_spec("ytmusicapi") is not None

    @classmethod
    def provider_descriptor(cls) -> ProviderDescriptor:
        return {
            "auth_required": False,
            "supported_capabilities": [
                "playback",
                "catalog_matching",
                "browser_playback",
            ],
            "setup_url": "https://music.youtube.com/",
            "next_actions_when_unconfigured": [
                "Enable provider in environment if experimental.",
                "Install optional addon dependencies for this provider.",
            ],
            "can_skip_setup": True,
            "can_retry_setup": True,
        }

    def is_configured(self, *, conn=None) -> bool:
        return True

    def list_devices(self, *, conn=None) -> list[dict[str, object]]:
        return [dict(_BROWSER_DEVICE)]

    def start_album_playback(
        self,
        provider_album_id: str,
        *,
        device_id: str | None = None,
        conn=None,
    ) -> None:
        url = f"{_YTM_BROWSE_BASE}{provider_album_id}"
        webbrowser.open(url)

    def create_matching_client(self, *, conn=None) -> YouTubeMusicClient:
        return YouTubeMusicClient()

    def run_oauth_login(self, **kwargs: object) -> dict[str, object]:
        return {
            "ok": True,
            "message": "YouTube Music v1 requires no authentication.",
        }

    def auth_diagnostics(self, *, conn=None, **kwargs: object) -> dict[str, object]:
        diag = get_youtube_music_auth_diagnostics()
        diag["addon_available"] = self.addon_available()
        return diag
