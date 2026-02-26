from __future__ import annotations

from discogs_player import capabilities


class _FakeSpotifyBackend:
    @property
    def name(self) -> str:
        return "spotify"

    @classmethod
    def addon_available(cls) -> bool:
        return True

    def is_configured(self, *, conn=None) -> bool:
        _ = conn
        return True


def test_get_capabilities_includes_listed_provider_states(monkeypatch):
    monkeypatch.setattr(capabilities, "get_player_backend", lambda: _FakeSpotifyBackend())
    monkeypatch.setattr(
        capabilities,
        "listed_provider_ids",
        lambda: ("spotify", "youtube_music"),
    )
    monkeypatch.setattr(
        capabilities,
        "provider_metadata",
        lambda provider_id: {
            "provider_id": provider_id,
            "display_name": "Spotify"
            if provider_id == "spotify"
            else "YouTube Music",
            "docs_url": "https://example.test/docs",
            "experimental": provider_id == "youtube_music",
            "enabled": provider_id != "youtube_music",
        },
    )
    monkeypatch.setattr(
        capabilities,
        "experimental_flag",
        lambda provider_id: "DP_ENABLE_EXPERIMENTAL_YOUTUBE_MUSIC"
        if provider_id == "youtube_music"
        else None,
    )
    monkeypatch.setattr(
        capabilities,
        "get_backend_type",
        lambda provider_id: _FakeSpotifyBackend if provider_id == "spotify" else None,
    )

    report = capabilities.get_capabilities()
    providers = {item.provider_id: item for item in report.providers}

    spotify = providers["spotify"]
    assert spotify.enabled is True
    assert spotify.importable is True
    assert spotify.action_label == "Ready"

    youtube = providers["youtube_music"]
    assert youtube.enabled is False
    assert youtube.importable is False
    assert youtube.action_label == "Planned"
    assert youtube.experimental is True
    assert youtube.experimental_flag == "DP_ENABLE_EXPERIMENTAL_YOUTUBE_MUSIC"
