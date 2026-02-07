"""Use-cases for Discogs-to-Spotify mapping."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_release_by_id,
    get_spotify_mapping,
    query_releases,
    upsert_spotify_mapping,
)
from discogs_player.services.matching import MatchingResult, MatchingService, clamp_threshold
from discogs_player.services.spotify_client import SpotifyClient
from discogs_player.services.spotify_oauth import get_spotify_access_token


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_album_id(raw: str) -> str:
    album = raw.strip()
    if album.startswith("spotify:album:"):
        album = album.removeprefix("spotify:album:")
    if not album:
        raise ValueError("Spotify album id cannot be empty.")
    return album


def _result_from_matching(
    release: dict[str, Any],
    match: MatchingResult,
    *,
    source: str = "auto",
) -> dict[str, object]:
    return {
        "discogs_release_id": release["discogs_release_id"],
        "artist": release.get("artist"),
        "title": release.get("title"),
        "matched": match.matched,
        "spotify_album_id": match.spotify_album_id,
        "confidence": match.confidence,
        "best_candidate": match.best_candidate,
        "candidates": match.candidates,
        "source": source,
    }


def _match_single_release(
    conn,
    *,
    release: dict[str, Any],
    matcher: MatchingService,
) -> dict[str, object]:
    existing = get_spotify_mapping(conn, int(release["discogs_release_id"]))
    if existing and existing.get("is_override"):
        matched = bool(existing.get("spotify_album_id"))
        return {
            "discogs_release_id": release["discogs_release_id"],
            "artist": release.get("artist"),
            "title": release.get("title"),
            "matched": matched,
            "spotify_album_id": existing.get("spotify_album_id"),
            "confidence": float(existing.get("confidence") or 1.0),
            "best_candidate": None,
            "candidates": [],
            "source": "override",
            "note": "Override mapping preserved",
        }

    match = matcher.match_release(release)
    upsert_spotify_mapping(
        conn,
        discogs_release_id=int(release["discogs_release_id"]),
        spotify_album_id=match.spotify_album_id,
        confidence=match.confidence,
        last_checked_at=_now_iso(),
        is_override=False,
    )
    return _result_from_matching(release, match)


def run_match_release(
    discogs_release_id: int,
    *,
    threshold: float = 0.72,
) -> dict[str, object]:
    threshold = clamp_threshold(float(threshold))

    conn = get_connection()
    try:
        release = get_release_by_id(conn, int(discogs_release_id))
        if release is None:
            raise ValueError(f"Discogs release {discogs_release_id} was not found in local database.")

        existing = get_spotify_mapping(conn, int(discogs_release_id))
        if existing and existing.get("is_override"):
            matched = bool(existing.get("spotify_album_id"))
            return {
                "discogs_release_id": release["discogs_release_id"],
                "artist": release.get("artist"),
                "title": release.get("title"),
                "matched": matched,
                "spotify_album_id": existing.get("spotify_album_id"),
                "confidence": float(existing.get("confidence") or 1.0),
                "best_candidate": None,
                "candidates": [],
                "source": "override",
                "note": "Override mapping preserved",
            }

        token = get_spotify_access_token(conn=conn)
        client = SpotifyClient(access_token=token)
        matcher = MatchingService(client, threshold=threshold)
        result = _match_single_release(conn, release=release, matcher=matcher)
    finally:
        conn.close()

    return result


def run_match_unmatched(
    *,
    limit: int = 25,
    threshold: float = 0.72,
) -> dict[str, object]:
    threshold = clamp_threshold(float(threshold))

    conn = get_connection()
    try:
        releases = query_releases(conn, unmatched=True, limit=max(1, int(limit)))
        if not releases:
            return {"processed_count": 0, "matched_count": 0, "results": []}

        token = get_spotify_access_token(conn=conn)
        client = SpotifyClient(access_token=token)
        matcher = MatchingService(client, threshold=threshold)

        results: list[dict[str, object]] = []
        matched_count = 0
        for release in releases:
            item = _match_single_release(conn, release=release, matcher=matcher)
            results.append(item)
            if item.get("matched"):
                matched_count += 1

        return {
            "processed_count": len(results),
            "matched_count": matched_count,
            "results": results,
        }
    finally:
        conn.close()


def run_match_override(discogs_release_id: int, spotify_album_id: str) -> dict[str, object]:
    normalized_album_id = _normalize_album_id(spotify_album_id)

    conn = get_connection()
    try:
        release = get_release_by_id(conn, int(discogs_release_id))
        if release is None:
            raise ValueError(f"Discogs release {discogs_release_id} was not found in local database.")

        upsert_spotify_mapping(
            conn,
            discogs_release_id=int(discogs_release_id),
            spotify_album_id=normalized_album_id,
            confidence=1.0,
            last_checked_at=_now_iso(),
            is_override=True,
        )
    finally:
        conn.close()

    return {
        "discogs_release_id": int(discogs_release_id),
        "spotify_album_id": normalized_album_id,
        "confidence": 1.0,
        "is_override": True,
    }
