"""Cover image caching helpers for GUI consumption."""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from discogs_player.core.paths import cover_cache_dir

DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_IMAGE_BYTES = 8 * 1024 * 1024
USER_AGENT = "discogs_player/0.1"


def _cache_path_for_url(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cover_cache_dir() / f"{digest}.img"


def get_or_fetch_cover_path(
    cover_url: str | None,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_image_bytes: int = MAX_IMAGE_BYTES,
) -> str | None:
    """Return a local cached cover path, fetching once if needed."""
    if not cover_url:
        return None

    normalized_url = str(cover_url).strip()
    if not normalized_url or not normalized_url.startswith(("http://", "https://")):
        return None

    cache_dir = cover_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = _cache_path_for_url(normalized_url)

    if target.exists() and target.stat().st_size > 0:
        return str(target)

    request = urllib.request.Request(
        normalized_url,
        headers={"User-Agent": USER_AGENT, "Accept": "image/*"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            content_type = str(response.headers.get("Content-Type") or "").lower()
            if content_type and not content_type.startswith("image/"):
                return None

            data = response.read(max_image_bytes + 1)
            if not data or len(data) > max_image_bytes:
                return None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    fd, temp_path = tempfile.mkstemp(prefix="cover_", suffix=".tmp", dir=str(cache_dir))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temp_path, target)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    return str(target)

