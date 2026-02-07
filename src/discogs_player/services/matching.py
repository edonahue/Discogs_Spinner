"""Discogs-to-Spotify matching service."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any


class MatchingDependencyError(Exception):
    """Raised when an optional matching dependency is missing."""


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _token_set(value: str) -> set[str]:
    if not value:
        return set()
    return set(value.split(" "))


def _token_set_ratio_stdlib(left: str, right: str) -> float:
    left_tokens = " ".join(sorted(_token_set(left)))
    right_tokens = " ".join(sorted(_token_set(right)))
    if not left_tokens and not right_tokens:
        return 100.0
    ratio = SequenceMatcher(None, left_tokens, right_tokens).ratio()
    return ratio * 100.0


def _token_set_ratio(left: str, right: str) -> float:
    try:
        from rapidfuzz import fuzz
    except ModuleNotFoundError:
        return _token_set_ratio_stdlib(left, right)
    except Exception as exc:  # pragma: no cover
        raise MatchingDependencyError(
            f"Failed to use rapidfuzz for matching: {exc}. Reinstall dependencies."
        ) from exc

    return float(fuzz.token_set_ratio(left, right))


def _parse_year(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.match(r"\s*(\d{4})", value)
        if match:
            return int(match.group(1))
    return None


def _year_score(release_year: int | None, candidate_year: int | None) -> float:
    if release_year is None or candidate_year is None:
        return 50.0
    diff = abs(release_year - candidate_year)
    if diff == 0:
        return 100.0
    if diff == 1:
        return 85.0
    if diff == 2:
        return 70.0
    if diff == 3:
        return 55.0
    if diff <= 5:
        return 40.0
    return 20.0


@dataclass
class MatchingResult:
    matched: bool
    discogs_release_id: int
    spotify_album_id: str | None
    confidence: float
    best_candidate: dict[str, object] | None
    candidates: list[dict[str, object]]


class MatchingService:
    def __init__(self, spotify_client, *, threshold: float = 0.72, search_limit: int = 10):
        self.spotify_client = spotify_client
        self.threshold = threshold
        self.search_limit = max(1, min(20, int(search_limit)))

    def _candidate_score(self, release: dict[str, Any], candidate: dict[str, Any]) -> float:
        artist = _normalize_text(str(release.get("artist") or ""))
        title = _normalize_text(str(release.get("title") or ""))

        candidate_artists = candidate.get("artists")
        artists_joined = ", ".join(candidate_artists) if isinstance(candidate_artists, list) else ""
        candidate_artist = _normalize_text(artists_joined)
        candidate_title = _normalize_text(str(candidate.get("name") or ""))

        artist_score = _token_set_ratio(artist, candidate_artist)
        title_score = _token_set_ratio(title, candidate_title)

        release_year = _parse_year(release.get("year"))
        candidate_year = _parse_year(candidate.get("release_date"))
        year_score = _year_score(release_year, candidate_year)

        weighted = (0.45 * artist_score) + (0.45 * title_score) + (0.10 * year_score)
        return max(0.0, min(100.0, weighted))

    def _search_candidates(self, release: dict[str, Any]) -> list[dict[str, Any]]:
        artist = str(release.get("artist") or "").strip()
        title = str(release.get("title") or "").strip()

        queries: list[str] = []
        if title and artist:
            queries.append(f"album:{title} artist:{artist}")
        if title:
            queries.append(title)
        if artist and title:
            queries.append(f"{artist} {title}")

        seen_ids: set[str] = set()
        candidates: list[dict[str, Any]] = []
        for query in queries:
            rows = self.spotify_client.search_albums(query=query, limit=self.search_limit)
            for row in rows:
                album_id = row.get("id")
                if not isinstance(album_id, str) or not album_id:
                    continue
                if album_id in seen_ids:
                    continue
                seen_ids.add(album_id)
                candidates.append(row)
        return candidates

    def match_release(self, release: dict[str, Any]) -> MatchingResult:
        release_id = int(release["discogs_release_id"])
        candidates = self._search_candidates(release)

        scored: list[dict[str, object]] = []
        for candidate in candidates:
            score = self._candidate_score(release, candidate)
            scored.append({
                **candidate,
                "confidence": round(score / 100.0, 4),
            })

        scored.sort(
            key=lambda item: (
                float(item.get("confidence") or 0.0),
                str(item.get("name") or ""),
                str(item.get("id") or ""),
            ),
            reverse=True,
        )

        best = scored[0] if scored else None
        best_confidence = float(best.get("confidence")) if best else 0.0
        matched = bool(best and best_confidence >= self.threshold)

        return MatchingResult(
            matched=matched,
            discogs_release_id=release_id,
            spotify_album_id=str(best.get("id")) if matched and best else None,
            confidence=best_confidence,
            best_candidate=best,
            candidates=scored[:5],
        )


def clamp_threshold(raw: float) -> float:
    if math.isnan(raw):
        raise ValueError("Threshold must be a numeric value between 0 and 1.")
    if raw < 0 or raw > 1:
        raise ValueError("Threshold must be between 0 and 1.")
    return raw
