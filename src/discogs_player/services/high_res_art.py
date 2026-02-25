"""Optional high-resolution Discogs cover-art helpers."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from discogs_player.core.settings import get_int_setting, get_setting

HIGH_RES_ART_ENABLED_SETTING = "high_res_art_enabled"
HIGH_RES_ART_TARGET_SIZE_SETTING = "high_res_art_target_size"

DEFAULT_HIGH_RES_ART_TARGET_SIZE = 1200
MIN_HIGH_RES_ART_TARGET_SIZE = 600
MAX_HIGH_RES_ART_TARGET_SIZE = 2400

_TRUE_VALUES: frozenset[str] = frozenset(
    {"1", "true", "yes", "on", "enabled", "enable"}
)
_FALSE_VALUES: frozenset[str] = frozenset(
    {"0", "false", "no", "off", "disabled", "disable"}
)
_DISCOGS_IMAGE_HOSTS: frozenset[str] = frozenset({"i.discogs.com"})
_SIGNED_DISCOGS_MARKERS: tuple[str, ...] = ("/czM6Ly9", "/q:")
_SIZE_SEGMENT_RE = re.compile(r"/h:(\d+)/w:(\d+)/")


def _coerce_int(value: object | None, *, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped.lstrip("-").isdigit():
            return int(stripped)
    return default


def _coerce_bool(value: object | None, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) != 0
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    return default


def normalize_high_res_art_target_size(value: object | None) -> int:
    parsed = _coerce_int(value, default=DEFAULT_HIGH_RES_ART_TARGET_SIZE)
    return max(
        MIN_HIGH_RES_ART_TARGET_SIZE,
        min(MAX_HIGH_RES_ART_TARGET_SIZE, int(parsed)),
    )


def get_high_res_art_preference(conn=None) -> tuple[bool, int]:
    enabled_raw = get_setting(HIGH_RES_ART_ENABLED_SETTING, conn=conn)
    enabled = _coerce_bool(enabled_raw, default=False)
    target_raw = get_int_setting(
        HIGH_RES_ART_TARGET_SIZE_SETTING,
        default=DEFAULT_HIGH_RES_ART_TARGET_SIZE,
        conn=conn,
    )
    target_size = normalize_high_res_art_target_size(target_raw)
    return enabled, target_size


def upgrade_discogs_cover_url(
    cover_url: str | None,
    *,
    target_size: int | None = None,
) -> str | None:
    if not isinstance(cover_url, str):
        return None

    normalized = cover_url.strip()
    if not normalized:
        return None

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        return normalized

    host = (parsed.hostname or "").strip().casefold()
    if host not in _DISCOGS_IMAGE_HOSTS:
        return normalized

    path = str(parsed.path or "")
    if any(marker in path for marker in _SIGNED_DISCOGS_MARKERS):
        # Signed proxy URLs include transforms in the signature payload.
        # Mutating /h:/w: commonly returns 403 and does not produce true higher-res art.
        return normalized

    target = normalize_high_res_art_target_size(target_size)
    match = _SIZE_SEGMENT_RE.search(normalized)
    if match is None:
        return normalized

    current_h = _coerce_int(match.group(1), default=0)
    current_w = _coerce_int(match.group(2), default=0)
    if current_h >= target and current_w >= target:
        return normalized

    return _SIZE_SEGMENT_RE.sub(f"/h:{target}/w:{target}/", normalized, count=1)


def resolve_cover_url_for_preference(
    cover_url: str | None,
    *,
    prefer_high_res: bool,
    target_size: int,
) -> str | None:
    if not isinstance(cover_url, str):
        return None
    normalized = cover_url.strip()
    if not normalized:
        return None
    if not prefer_high_res:
        return normalized
    upgraded = upgrade_discogs_cover_url(normalized, target_size=target_size)
    if not upgraded:
        return normalized
    return upgraded
