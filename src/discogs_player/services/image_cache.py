"""Cover image caching helpers for GUI consumption."""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from discogs_player.core.paths import cover_cache_dir

DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_IMAGE_BYTES = 8 * 1024 * 1024
USER_AGENT = "discogs_player/0.1"
LEGACY_CACHE_EXTENSION = ".img"

_CONTENT_TYPE_TO_EXTENSION: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/x-ms-bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "image/avif": ".avif",
    "image/heic": ".heic",
    "image/heif": ".heif",
}

_URL_EXTENSION_ALIASES: dict[str, str] = {
    ".jpeg": ".jpg",
    ".jpe": ".jpg",
    ".jfif": ".jpg",
    ".tif": ".tiff",
}

_KNOWN_IMAGE_EXTENSIONS: tuple[str, ...] = (
    ".jpg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".tiff",
    ".ico",
    ".avif",
    ".heic",
    ".heif",
)


def _digest_for_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _cache_path_for_digest(digest: str, extension: str) -> Path:
    return cover_cache_dir() / f"{digest}{extension}"


def _cache_path_for_url(url: str, *, extension: str = LEGACY_CACHE_EXTENSION) -> Path:
    return _cache_path_for_digest(_digest_for_url(url), extension)


def _extension_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    media_type = str(content_type).strip().lower().split(";", 1)[0].strip()
    if not media_type:
        return None
    return _CONTENT_TYPE_TO_EXTENSION.get(media_type)


def _extension_from_url(url: str) -> str | None:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return None
    suffix = Path(parsed.path or "").suffix.strip().lower()
    if not suffix:
        return None
    canonical = _URL_EXTENSION_ALIASES.get(suffix, suffix)
    if canonical in _KNOWN_IMAGE_EXTENSIONS:
        return canonical
    return None


def _extension_from_magic(data: bytes) -> str | None:
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if len(data) >= 2 and data[:2] == b"BM":
        return ".bmp"
    if len(data) >= 4 and data[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tiff"
    if len(data) >= 4 and data[:4] == b"\x00\x00\x01\x00":
        return ".ico"

    # ISO BMFF images such as AVIF/HEIF carry the brand after `ftyp`.
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"avif", b"avis"):
            return ".avif"
        if brand in (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"):
            return ".heic"
    return None


def _choose_cache_extension(
    *,
    cover_url: str,
    content_type: str | None,
    data: bytes,
) -> str:
    for extension in (
        _extension_from_content_type(content_type),
        _extension_from_magic(data),
        _extension_from_url(cover_url),
    ):
        if extension:
            return extension
    return LEGACY_CACHE_EXTENSION


def _find_existing_cache_path(digest: str) -> Path | None:
    candidates: list[Path] = []
    for extension in _KNOWN_IMAGE_EXTENSIONS:
        path = _cache_path_for_digest(digest, extension)
        if path.exists() and path.stat().st_size > 0:
            candidates.append(path)

    legacy = _cache_path_for_digest(digest, LEGACY_CACHE_EXTENSION)
    if legacy.exists() and legacy.stat().st_size > 0:
        candidates.append(legacy)

    if not candidates:
        return None
    return candidates[0]


def _maybe_migrate_legacy_cache_path(legacy_path: Path, *, cover_url: str) -> Path:
    if legacy_path.suffix.lower() != LEGACY_CACHE_EXTENSION:
        return legacy_path

    try:
        with legacy_path.open("rb") as handle:
            head = handle.read(64)
    except OSError:
        return legacy_path

    extension = _extension_from_magic(head) or _extension_from_url(cover_url)
    if not extension or extension == LEGACY_CACHE_EXTENSION:
        return legacy_path

    target = legacy_path.with_suffix(extension)
    if target.exists() and target.stat().st_size > 0:
        try:
            legacy_path.unlink()
        except OSError:
            pass
        return target

    try:
        os.replace(legacy_path, target)
    except OSError:
        return legacy_path
    return target


def _write_cache_file(*, target: Path, data: bytes, cache_dir: Path) -> None:
    fd, temp_path = tempfile.mkstemp(prefix="cover_", suffix=".tmp", dir=str(cache_dir))
    try:
        with os.fdopen(fd, "wb") as handle:
            # Raw byte copy only; no image transcoding, so quality/resolution is preserved.
            handle.write(data)
        os.replace(temp_path, target)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _cleanup_legacy_cache_file(*, digest: str, current_target: Path) -> None:
    legacy = _cache_path_for_digest(digest, LEGACY_CACHE_EXTENSION)
    if legacy == current_target or not legacy.exists():
        return
    try:
        legacy.unlink()
    except OSError:
        pass


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
    digest = _digest_for_url(normalized_url)

    existing = _find_existing_cache_path(digest)
    if existing is not None:
        migrated = _maybe_migrate_legacy_cache_path(existing, cover_url=normalized_url)
        return str(migrated)

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

    extension = _choose_cache_extension(
        cover_url=normalized_url,
        content_type=content_type,
        data=data,
    )
    target = _cache_path_for_digest(digest, extension)
    _write_cache_file(target=target, data=data, cache_dir=cache_dir)
    _cleanup_legacy_cache_file(digest=digest, current_target=target)
    return str(target)
