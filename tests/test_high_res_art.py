from __future__ import annotations

from discogs_player.core.settings import set_setting
from discogs_player.services.high_res_art import (
    DEFAULT_HIGH_RES_ART_TARGET_SIZE,
    HIGH_RES_ART_ENABLED_SETTING,
    HIGH_RES_ART_TARGET_SIZE_SETTING,
    get_high_res_art_preference,
    normalize_high_res_art_target_size,
    resolve_cover_url_for_preference,
    upgrade_discogs_cover_url,
)


def test_normalize_high_res_art_target_size_clamps_range():
    assert normalize_high_res_art_target_size(None) == DEFAULT_HIGH_RES_ART_TARGET_SIZE
    assert normalize_high_res_art_target_size(300) == 600
    assert normalize_high_res_art_target_size(2401) == 2400
    assert normalize_high_res_art_target_size("1300") == 1300


def test_upgrade_discogs_cover_url_rewrites_proxy_size():
    upgraded = upgrade_discogs_cover_url(
        "https://i.discogs.com/hash/rs:fit/h:600/w:600/format:webp/"
        "discogs-images/R-123-1700000000-0000.jpg",
        target_size=1400,
    )
    assert "/h:1400/w:1400/" in str(upgraded)


def test_upgrade_discogs_cover_url_does_not_rewrite_signed_proxy_urls():
    original = (
        "https://i.discogs.com/hash/rs:fit/g:sm/q:90/h:600/w:600/"
        "czM6Ly9kaXNjb2dzLWRhdGFiYXNlLWltYWdlcy9SLTEyMy5qcGVn.jpeg"
    )
    upgraded = upgrade_discogs_cover_url(original, target_size=1400)
    assert upgraded == original


def test_upgrade_discogs_cover_url_ignores_non_discogs_hosts():
    original = "https://img.example.com/path/h:600/w:600/cover.jpg"
    assert upgrade_discogs_cover_url(original, target_size=1400) == original


def test_get_high_res_art_preference_reads_settings(isolated_xdg):
    set_setting(HIGH_RES_ART_ENABLED_SETTING, "enabled")
    set_setting(HIGH_RES_ART_TARGET_SIZE_SETTING, "1500")

    enabled, target_size = get_high_res_art_preference()
    assert enabled is True
    assert target_size == 1500


def test_resolve_cover_url_for_preference_returns_original_when_disabled():
    original = (
        "https://i.discogs.com/hash/rs:fit/h:600/w:600/format:webp/"
        "discogs-images/R-123-1700000000-0000.jpg"
    )
    resolved = resolve_cover_url_for_preference(
        original,
        prefer_high_res=False,
        target_size=1400,
    )
    assert resolved == original
