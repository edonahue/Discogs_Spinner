"""External fallback providers for one-off Discogs->Spotify mapping."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote

import httpx


@dataclass(frozen=True)
class ExternalFallbackMatch:
    spotify_album_id: str
    source: str
    confidence: float
    note: str


_SPOTIFY_ALBUM_ID_PATTERN = re.compile(r"[A-Za-z0-9]{22}")
_SPOTIFY_ALBUM_URL_PATTERN = re.compile(
    r"open\.spotify\.com/album/([A-Za-z0-9]{22})",
    flags=re.IGNORECASE,
)
_SPOTIFY_ALBUM_URL_ENCODED_PATTERN = re.compile(
    r"open\.spotify\.com%2Falbum%2F([A-Za-z0-9]{22})",
    flags=re.IGNORECASE,
)


def _normalize_spotify_album_id(raw: Any) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.startswith("spotify:album:"):
        text = text.removeprefix("spotify:album:").strip()
    else:
        match = _SPOTIFY_ALBUM_URL_PATTERN.search(text)
        if match:
            text = match.group(1)
    text = text.split("?", 1)[0].strip().strip("/")
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    if not _SPOTIFY_ALBUM_ID_PATTERN.fullmatch(text):
        return None
    return text


def _to_float(value: Any, default: float) -> float:
    if isinstance(value, (int, float)):
        parsed = float(value)
    else:
        try:
            parsed = float(str(value))
        except Exception:
            parsed = default
    if parsed < 0.0:
        return 0.0
    if parsed > 1.0:
        return 1.0
    return parsed


def _candidate_report_paths() -> list[Path]:
    data_home = Path(os.environ.get("XDG_DATA_HOME") or "~/.local/share").expanduser()
    base = data_home / "discogs_player" / "reports"
    return [
        base / "spotify_match_audit_single_live.json",
        base / "spotify_match_audit_slow.json",
        base / "spotify_match_audit_latest.json",
    ]


def _candidate_bootstrap_paths() -> list[Path]:
    configured = str(os.environ.get("DP_SPOTIFY_FALLBACK_BOOTSTRAP_PATHS") or "").strip()
    if configured:
        paths: list[Path] = []
        for part in configured.split(os.pathsep):
            candidate = str(part or "").strip()
            if candidate:
                paths.append(Path(candidate).expanduser())
        if paths:
            return paths

    data_home = Path(os.environ.get("XDG_DATA_HOME") or "~/.local/share").expanduser()
    base = data_home / "discogs_player" / "bootstrap"
    return [
        base / "discogs_to_spotify.json",
        base / "mappings.json",
        base / "bootstrap_mappings.json",
    ]


def _lookup_in_report(release_id: int, *, min_confidence: float) -> ExternalFallbackMatch | None:
    for path in _candidate_report_paths():
        if not path.exists() or path.is_dir():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except Exception:
            continue

        entries = payload.get("entries")
        if not isinstance(entries, list):
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if int(entry.get("discogs_release_id") or 0) != release_id:
                continue
            status = str(entry.get("status") or "").strip().lower()
            if status in {"error", "manual_rejected"}:
                continue

            album_id = _normalize_spotify_album_id(
                entry.get("spotify_album_id") or entry.get("candidate_album_id")
            )
            if not album_id:
                continue

            confidence = _to_float(entry.get("confidence"), 0.70)
            if confidence < min_confidence:
                continue

            return ExternalFallbackMatch(
                spotify_album_id=album_id,
                source=f"audit-report:{path.name}",
                confidence=confidence,
                note="Recovered mapping from existing audit report.",
            )
    return None


def _lookup_in_bootstrap(release_id: int, *, min_confidence: float) -> ExternalFallbackMatch | None:
    # Local import avoids pulling bootstrap parser unless fallback is needed.
    from discogs_player.use_cases.bootstrap_import import extract_bootstrap_mappings

    for path in _candidate_bootstrap_paths():
        if not path.exists() or path.is_dir():
            continue
        try:
            extracted = extract_bootstrap_mappings(
                input_path=str(path),
                source_format="auto",
            )
        except Exception:
            continue

        rows = extracted.get("mappings")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            if int(row.get("discogs_release_id") or 0) != release_id:
                continue
            album_id = _normalize_spotify_album_id(row.get("spotify_album_id"))
            if not album_id:
                continue
            confidence = _to_float(row.get("confidence"), 0.78)
            if confidence < min_confidence:
                continue
            return ExternalFallbackMatch(
                spotify_album_id=album_id,
                source=f"bootstrap:{path.name}",
                confidence=confidence,
                note="Recovered mapping from local bootstrap mapping file.",
            )
    return None


def _clean_search_term(value: str) -> str:
    cleaned = re.sub(r"\([^)]*\)", " ", value)
    cleaned = re.sub(r"\[[^\]]*\]", " ", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9\s]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _extract_first_album_id(text: str) -> str | None:
    match = _SPOTIFY_ALBUM_URL_PATTERN.search(text)
    if match:
        return match.group(1)
    encoded = _SPOTIFY_ALBUM_URL_ENCODED_PATTERN.search(text)
    if encoded:
        return encoded.group(1)
    return None


def _lookup_via_web_search(
    artist: str,
    title: str,
    *,
    timeout_seconds: float,
) -> ExternalFallbackMatch | None:
    clean_artist = _clean_search_term(artist)
    clean_title = _clean_search_term(title)
    if not clean_artist and not clean_title:
        return None

    user_agent = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    headers = {"User-Agent": user_agent}
    timeout = httpx.Timeout(timeout_seconds)

    queries = [
        f'site:open.spotify.com/album "{clean_artist}" "{clean_title}"',
        f"site:open.spotify.com/album {clean_artist} {clean_title}",
    ]

    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        for query in queries:
            try:
                response = client.get(
                    "https://duckduckgo.com/html/",
                    params={"q": query},
                )
            except Exception:
                continue
            if response.status_code >= 400:
                continue
            album_id = _extract_first_album_id(response.text)
            if album_id:
                return ExternalFallbackMatch(
                    spotify_album_id=album_id,
                    source="web:duckduckgo",
                    confidence=0.62,
                    note="Recovered mapping from public web search fallback.",
                )

        # Secondary fallback: parse open search page for album ids.
        open_query = quote(" ".join(part for part in (clean_artist, clean_title) if part))
        if open_query:
            open_response: httpx.Response | None = None
            try:
                open_response = client.get(
                    f"https://open.spotify.com/search/{open_query}/albums"
                )
            except Exception:
                pass
            if open_response is not None and open_response.status_code < 400:
                album_id = _extract_first_album_id(open_response.text)
                if album_id:
                    return ExternalFallbackMatch(
                        spotify_album_id=album_id,
                        source="web:spotify-open-search",
                        confidence=0.60,
                        note="Recovered mapping from public Spotify web search page.",
                    )

    return None


def resolve_external_fallback_match(
    release: dict[str, Any],
    *,
    timeout_seconds: float = 8.0,
    min_confidence: float = 0.55,
) -> ExternalFallbackMatch | None:
    release_id = int(release.get("discogs_release_id") or 0)
    if release_id <= 0:
        return None

    report_match = _lookup_in_report(release_id, min_confidence=min_confidence)
    if report_match is not None:
        return report_match

    bootstrap_match = _lookup_in_bootstrap(release_id, min_confidence=min_confidence)
    if bootstrap_match is not None:
        return bootstrap_match

    artist = str(release.get("artist") or "").strip()
    title = str(release.get("title") or "").strip()
    return _lookup_via_web_search(
        artist,
        title,
        timeout_seconds=max(1.0, float(timeout_seconds)),
    )
