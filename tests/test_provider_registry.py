from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from discogs_player.integrations import provider_registry
from discogs_player.integrations.null_backend import NullPlayerBackend
from discogs_player.integrations.player_backend import PlayerBackend


class _FakeBaseBackend(PlayerBackend):
    @property
    def name(self) -> str:
        return "fake"

    def is_configured(self, *, conn=None) -> bool:
        _ = conn
        return True

    def list_devices(self, *, conn=None) -> list[dict[str, object]]:
        _ = conn
        return []

    def start_album_playback(
        self,
        provider_album_id: str,
        *,
        device_id: str | None = None,
        conn=None,
    ) -> None:
        _ = (provider_album_id, device_id, conn)

    def create_matching_client(self, *, conn=None) -> Any:
        _ = conn
        return object()

    def run_oauth_login(self, **kwargs: object) -> dict[str, object]:
        _ = kwargs
        return {"ok": True}

    def auth_diagnostics(self, *, conn=None, **kwargs: object) -> dict[str, object]:
        _ = (conn, kwargs)
        return {"backend": "fake"}


class _FakeUnavailableBackend(_FakeBaseBackend):
    @classmethod
    def addon_available(cls) -> bool:
        return False


class _FakeAvailableBackend(_FakeBaseBackend):
    @classmethod
    def addon_available(cls) -> bool:
        return True


def test_registered_provider_ids_contains_spotify():
    assert "spotify" in provider_registry.registered_provider_ids()


def test_youtube_music_stub_is_listed_but_disabled_by_default():
    assert "youtube_music" in provider_registry.listed_provider_ids()
    assert "youtube_music" not in provider_registry.registered_provider_ids()
    metadata = provider_registry.provider_metadata("youtube_music")
    assert isinstance(metadata, dict)
    assert metadata["experimental"] is True
    assert metadata["enabled"] is False
    assert (
        metadata["experimental_flag"] == "DP_ENABLE_EXPERIMENTAL_YOUTUBE_MUSIC"
    )


def test_get_backend_type_unknown_provider_returns_none():
    assert provider_registry.get_backend_type("unknown-provider") is None


def test_get_backend_returns_null_when_addon_not_available(monkeypatch):
    monkeypatch.setitem(
        provider_registry._BACKEND_SPECS,
        "fake_provider",
        ("fake.module", "FakeBackend"),
    )
    monkeypatch.setattr(
        provider_registry,
        "import_module",
        lambda module_name: SimpleNamespace(FakeBackend=_FakeUnavailableBackend),
    )

    backend = provider_registry.get_backend("fake_provider")
    assert isinstance(backend, NullPlayerBackend)


def test_get_backend_returns_provider_backend_when_available(monkeypatch):
    monkeypatch.setitem(
        provider_registry._BACKEND_SPECS,
        "fake_provider",
        ("fake.module", "FakeBackend"),
    )
    monkeypatch.setattr(
        provider_registry,
        "import_module",
        lambda module_name: SimpleNamespace(FakeBackend=_FakeAvailableBackend),
    )

    backend = provider_registry.get_backend("fake_provider")
    assert isinstance(backend, _FakeAvailableBackend)
    assert backend.name == "fake"


def test_get_backend_type_returns_none_when_experimental_provider_disabled(monkeypatch):
    monkeypatch.setenv("DP_ENABLE_EXPERIMENTAL_YOUTUBE_MUSIC", "0")
    assert provider_registry.get_backend_type("youtube_music") is None
