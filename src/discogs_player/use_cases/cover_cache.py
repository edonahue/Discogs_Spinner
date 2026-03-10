"""Cover image cache management use-cases."""

from __future__ import annotations

import time
from pathlib import Path

from discogs_player.core.paths import cover_cache_dir
from discogs_player.data.db import get_connection
from discogs_player.data.repo import query_releases
from discogs_player.services.image_cache import (
    _digest_for_url,
    _find_existing_cache_path,
    get_or_fetch_cover_path,
)

_KNOWN_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".ico", ".avif", ".heic", ".heif", ".img"}
)


def _iter_cache_files(cache_dir: Path) -> list[Path]:
    if not cache_dir.exists():
        return []
    return [
        p
        for p in cache_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _KNOWN_EXTENSIONS
    ]


def run_cover_cache_stats() -> dict[str, object]:
    """Return stats about the local cover image cache."""
    cache_dir = cover_cache_dir()
    files = _iter_cache_files(cache_dir)

    if not files:
        return {
            "item_count": 0,
            "total_bytes": 0,
            "oldest_entry_mtime": None,
            "newest_entry_mtime": None,
            "cache_dir": str(cache_dir),
        }

    mtimes = [p.stat().st_mtime for p in files]
    total_bytes = sum(p.stat().st_size for p in files)
    oldest_ts = min(mtimes)
    newest_ts = max(mtimes)

    import datetime

    def _fmt(ts: float) -> str:
        return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat()

    return {
        "item_count": len(files),
        "total_bytes": total_bytes,
        "oldest_entry_mtime": _fmt(oldest_ts),
        "newest_entry_mtime": _fmt(newest_ts),
        "cache_dir": str(cache_dir),
    }


def run_cover_cache_prune(*, days: int) -> dict[str, object]:
    """Delete cover cache entries older than ``days`` days.

    Returns a summary with the number of files deleted and bytes freed.
    """
    if days < 1:
        raise ValueError("days must be >= 1")

    cache_dir = cover_cache_dir()
    files = _iter_cache_files(cache_dir)
    cutoff = time.time() - days * 86400

    deleted_count = 0
    freed_bytes = 0
    errors: list[str] = []

    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_mtime < cutoff:
            try:
                size = stat.st_size
                path.unlink()
                deleted_count += 1
                freed_bytes += size
            except OSError as exc:
                errors.append(f"{path.name}: {exc}")

    return {
        "days": days,
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
        "error_count": len(errors),
        "errors": errors,
    }


def run_cover_cache_warm(*, limit: int | None = None) -> dict[str, object]:
    """Pre-fetch missing cover images for active collection releases.

    Checks which active releases have a ``cover_url`` but no cached file,
    then downloads up to ``limit`` of them (all if ``limit`` is None).
    Returns a summary of fetched, already-cached, and missing-url counts.
    """
    if limit is not None and limit < 1:
        raise ValueError("limit must be >= 1")

    conn = get_connection()
    try:
        releases = query_releases(conn, limit=None)
    finally:
        conn.close()

    already_cached = 0
    no_url = 0
    fetched = 0
    fetch_errors = 0
    candidates: list[str] = []

    for item in releases:
        url = str(item.get("cover_url") or item.get("thumb_url") or "").strip()
        if not url or not url.startswith(("http://", "https://")):
            no_url += 1
            continue
        digest = _digest_for_url(url)
        existing = _find_existing_cache_path(digest)
        if existing is not None:
            already_cached += 1
        else:
            candidates.append(url)

    if limit is not None:
        candidates = candidates[:limit]

    for url in candidates:
        result = get_or_fetch_cover_path(url)
        if result is not None:
            fetched += 1
        else:
            fetch_errors += 1

    return {
        "already_cached": already_cached,
        "no_url": no_url,
        "fetched": fetched,
        "fetch_errors": fetch_errors,
        "limit": limit,
    }
