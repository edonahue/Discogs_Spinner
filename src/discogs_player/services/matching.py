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


_TITLE_NOISE_TOKENS: frozenset[str] = frozenset(
    {
        "deluxe",
        "expanded",
        "edition",
        "remaster",
        "remastered",
        "anniversary",
        "bonus",
        "tracks",
        "track",
        "version",
        "versions",
        "mono",
        "stereo",
        "reissue",
        "mix",
        "mixes",
        "super",
        "special",
        "digital",
        "explicit",
        "clean",
        "remix",
        "remixes",
        "live",
        "acoustic",
        "edit",
        "radio",
        "demo",
    }
)
_ARTIST_SPLIT_TERMS = ("feat", "featuring", "with", "vs")
_ARTIST_NOISE_TOKENS: frozenset[str] = frozenset({"the"})
_TITLE_VARIANT_TOKENS: frozenset[str] = frozenset(
    {
        "remix",
        "remixes",
        "live",
        "acoustic",
        "instrumental",
        "karaoke",
        "tribute",
        "cover",
        "covers",
        "demo",
        "edit",
        "rework",
        "session",
        "sessions",
        "version",
        "versions",
    }
)
_SINGLE_RELEASE_HINT_TOKENS: tuple[str, ...] = (
    "single",
    "ep",
    "remix",
    "remixes",
    "mix",
    "mixes",
    "instrumental",
    "radio edit",
    "demo",
)


def _canonical_title(value: str | None) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        return ""

    source_tokens = normalized.split()
    filtered_tokens = [
        token
        for token in source_tokens
        if token not in _TITLE_NOISE_TOKENS and not re.fullmatch(r"(19|20)\d{2}", token)
    ]
    if len(filtered_tokens) < 2:
        return normalized
    return " ".join(filtered_tokens)


def _canonical_artist(value: str | None) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        return ""

    split_pattern = r"\b(?:" + "|".join(_ARTIST_SPLIT_TERMS) + r")\b"
    primary = re.split(split_pattern, normalized, maxsplit=1)[0].strip()
    tokens = [token for token in primary.split() if token not in _ARTIST_NOISE_TOKENS]
    compact = " ".join(tokens).strip()
    return compact or primary


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


def _as_float(value: object | None, *, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return float(stripped)
        except ValueError:
            return default
    return default


def _as_int(value: object | None, *, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return int(stripped)
        except ValueError:
            return default
    return default


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


_SUSPICIOUS_MATCH_TERMS: tuple[tuple[str, float], ...] = (
    ("tribute", 20.0),
    ("karaoke", 20.0),
    ("piano", 16.0),
    ("instrumental", 12.0),
    ("cover", 16.0),
    ("covers", 16.0),
    ("lullaby", 16.0),
    ("reimagined", 12.0),
    ("orchestra", 8.0),
    ("versions", 8.0),
)


def _contains_token(text: str, token: str) -> bool:
    return bool(re.search(rf"\b{re.escape(token)}\b", text))


def _suspicious_candidate_penalty(release_text: str, candidate_text: str) -> float:
    """
    Penalize likely non-canonical candidates (covers/tributes/etc.) unless those
    same terms are present in the Discogs release metadata.
    """
    penalty = 0.0
    for term, weight in _SUSPICIOUS_MATCH_TERMS:
        if _contains_token(candidate_text, term) and not _contains_token(
            release_text, term
        ):
            penalty += weight
    return min(penalty, 42.0)


def _edition_noise_penalty(release_title: str, candidate_title: str) -> float:
    release_tokens = _token_set(_normalize_text(release_title))
    candidate_tokens = _token_set(_normalize_text(candidate_title))
    extra_noise_count = len((candidate_tokens - release_tokens) & _TITLE_NOISE_TOKENS)
    return min(10.0, 2.5 * extra_noise_count)


def _various_artists_penalty(release_artist: str, candidate_artist: str) -> float:
    release_normalized = _normalize_text(release_artist)
    candidate_normalized = _normalize_text(candidate_artist)
    if (
        "various" not in release_normalized
        and "various" in candidate_normalized
        and "artists" in candidate_normalized
    ):
        return 14.0
    return 0.0


def _title_extra_token_count(release_title: str, candidate_title: str) -> int:
    release_tokens = _token_set(_canonical_title(release_title))
    candidate_tokens = _token_set(_canonical_title(candidate_title))
    if not release_tokens or not candidate_tokens:
        return 0
    return max(0, len(candidate_tokens - release_tokens))


def _title_extra_tokens_penalty(release_title: str, candidate_title: str) -> float:
    release_tokens = _token_set(_canonical_title(release_title))
    candidate_tokens = _token_set(_canonical_title(candidate_title))
    if not release_tokens or not candidate_tokens:
        return 0.0

    extras = candidate_tokens - release_tokens
    if not extras:
        return 0.0

    variant_hits = extras & _TITLE_VARIANT_TOKENS
    non_noise_extras = extras - _TITLE_NOISE_TOKENS

    penalty = 0.0
    if variant_hits:
        penalty += min(16.0, 8.0 + (2.5 * max(0, len(variant_hits) - 1)))
    if len(non_noise_extras) >= 2:
        penalty += min(8.0, 1.75 * len(non_noise_extras))
    return min(20.0, penalty)


def _looks_like_single_release(release_title: str) -> bool:
    normalized = _normalize_text(release_title)
    if not normalized:
        return False
    return any(token in normalized for token in _SINGLE_RELEASE_HINT_TOKENS)


def _album_type_penalty(release_title: str, candidate: dict[str, Any]) -> float:
    album_type = _normalize_text(str(candidate.get("album_type") or ""))
    total_tracks = _as_int(candidate.get("total_tracks"), default=0)
    likely_single_release = _looks_like_single_release(release_title)

    penalty = 0.0
    if album_type == "single":
        penalty += 3.0 if likely_single_release else 12.0
    elif album_type in {"appears on", "appears_on"}:
        penalty += 8.0

    if total_tracks > 0 and not likely_single_release:
        if total_tracks <= 2:
            penalty += 8.0
        elif total_tracks <= 4:
            penalty += 4.0
    return min(18.0, penalty)


def _album_type_priority(album_type: object | None) -> int:
    normalized = _normalize_text(str(album_type or ""))
    if normalized == "album":
        return 4
    if normalized == "compilation":
        return 3
    if normalized in {"single", "appears on", "appears_on"}:
        return 1
    if normalized:
        return 2
    return 0


def _title_match_specificity(release_title: str, candidate_title: str) -> int:
    release_normalized = _normalize_text(release_title)
    candidate_normalized = _normalize_text(candidate_title)
    if release_normalized and release_normalized == candidate_normalized:
        return 2
    release_canonical = _canonical_title(release_title)
    candidate_canonical = _canonical_title(candidate_title)
    if release_canonical and release_canonical == candidate_canonical:
        return 1
    return 0


@dataclass
class MatchingResult:
    matched: bool
    discogs_release_id: int
    spotify_album_id: str | None
    confidence: float
    best_candidate: dict[str, object] | None
    candidates: list[dict[str, object]]


class MatchingService:
    def __init__(
        self, spotify_client, *, threshold: float = 0.72, search_limit: int = 10
    ):
        self.spotify_client = spotify_client
        self.threshold = threshold
        self.search_limit = max(1, min(20, int(search_limit)))

    def _candidate_score(
        self, release: dict[str, Any], candidate: dict[str, Any]
    ) -> float:
        artist_raw = str(release.get("artist") or "")
        title_raw = str(release.get("title") or "")
        artist = _normalize_text(artist_raw)
        title = _normalize_text(title_raw)
        release_artist_canonical = _canonical_artist(artist_raw)
        release_title_canonical = _canonical_title(title_raw)
        release_identity = _normalize_text(f"{artist} {title}")

        candidate_artists = candidate.get("artists")
        artists_joined = (
            ", ".join(candidate_artists) if isinstance(candidate_artists, list) else ""
        )
        candidate_title_raw = str(candidate.get("name") or "")
        candidate_artist = _normalize_text(artists_joined)
        candidate_artist_canonical = _canonical_artist(artists_joined)
        candidate_title = _normalize_text(candidate_title_raw)
        candidate_title_canonical = _canonical_title(candidate_title_raw)

        artist_score = max(
            _token_set_ratio(artist, candidate_artist),
            _token_set_ratio(release_artist_canonical, candidate_artist_canonical),
        )
        title_score = max(
            _token_set_ratio(title, candidate_title),
            _token_set_ratio(release_title_canonical, candidate_title_canonical),
        )

        release_year = _parse_year(release.get("year"))
        candidate_year = _parse_year(candidate.get("release_date"))
        year_score = _year_score(release_year, candidate_year)
        candidate_identity = _normalize_text(f"{candidate_artist} {candidate_title}")
        title_extra_tokens = _title_extra_token_count(title_raw, candidate_title_raw)
        penalty = _suspicious_candidate_penalty(release_identity, candidate_identity)
        penalty += _edition_noise_penalty(title_raw, candidate_title_raw)
        penalty += _title_extra_tokens_penalty(title_raw, candidate_title_raw)
        penalty += _various_artists_penalty(artist_raw, artists_joined)
        penalty += _album_type_penalty(title_raw, candidate)
        bonus = 0.0
        if (
            release_title_canonical
            and release_title_canonical == candidate_title_canonical
            and artist_score >= 80.0
        ):
            bonus += 3.0
        if (
            release_artist_canonical
            and release_artist_canonical == candidate_artist_canonical
            and title_score >= 80.0
            and title_extra_tokens == 0
        ):
            bonus += 2.0

        weighted = (
            (0.42 * artist_score) + (0.46 * title_score) + (0.12 * year_score) + bonus
        ) - penalty
        return max(0.0, min(100.0, weighted))

    def _search_candidates(self, release: dict[str, Any]) -> list[dict[str, Any]]:
        artist = str(release.get("artist") or "").strip()
        title = str(release.get("title") or "").strip()
        artist_canonical = _canonical_artist(artist)
        title_canonical = _canonical_title(title)

        queries: list[str] = []
        if title and artist:
            queries.append(f"album:{title} artist:{artist}")
        if title_canonical and artist_canonical and (
            title_canonical != _normalize_text(title)
            or artist_canonical != _normalize_text(artist)
        ):
            queries.append(f"album:{title_canonical} artist:{artist_canonical}")
        if title:
            queries.append(title)
        if title_canonical and title_canonical != _normalize_text(title):
            queries.append(title_canonical)
        if artist and title:
            queries.append(f"{artist} {title}")
        if artist_canonical and title_canonical:
            queries.append(f"{artist_canonical} {title_canonical}")

        # Preserve query order while dropping duplicates.
        deduped_queries: list[str] = []
        seen_queries: set[str] = set()
        for query in queries:
            normalized_query = re.sub(r"\s+", " ", query).strip()
            if not normalized_query:
                continue
            key = normalized_query.lower()
            if key in seen_queries:
                continue
            seen_queries.add(key)
            deduped_queries.append(normalized_query)

        seen_ids: set[str] = set()
        candidates: list[dict[str, Any]] = []
        for query in deduped_queries:
            rows = self.spotify_client.search_albums(
                query=query, limit=self.search_limit
            )
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

        ranked: list[tuple[tuple[object, ...], dict[str, object]]] = []
        release_title_raw = str(release.get("title") or "")
        for index, candidate in enumerate(candidates):
            score = self._candidate_score(release, candidate)
            confidence = round(score / 100.0, 4)
            candidate_title_raw = str(candidate.get("name") or "")
            scored_candidate: dict[str, object] = {
                **candidate,
                "confidence": confidence,
            }
            rank_key: tuple[object, ...] = (
                confidence,
                _title_match_specificity(release_title_raw, candidate_title_raw),
                _album_type_priority(candidate.get("album_type")),
                -_title_extra_token_count(release_title_raw, candidate_title_raw),
                _as_int(candidate.get("total_tracks"), default=0),
                -index,
            )
            ranked.append(
                (
                    rank_key,
                    scored_candidate,
                )
            )

        ranked.sort(key=lambda item: item[0], reverse=True)
        scored = [item[1] for item in ranked]

        best = scored[0] if scored else None
        best_confidence = (
            _as_float(best.get("confidence"), default=0.0) if best is not None else 0.0
        )
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
