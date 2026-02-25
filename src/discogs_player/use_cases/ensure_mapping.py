"""Use-cases for Discogs-to-Spotify mapping."""

from __future__ import annotations

import json
from pathlib import Path
import re
import time
from datetime import datetime, timezone
from collections.abc import Callable
from typing import Any

from discogs_player.capabilities import get_player_backend
from discogs_player.core.paths import data_dir
from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_release_by_id,
    get_spotify_mapping,
    get_wantlist_by_id,
    query_releases,
    query_wantlist,
    upsert_spotify_mapping,
)
from discogs_player.integrations.player_backend import PlayerApiError, PlayerAuthError
from discogs_player.services.matching import (
    MatchingResult,
    MatchingService,
    clamp_threshold,
)
from discogs_player.use_cases.external_match_fallback import (
    ExternalFallbackMatch,
    resolve_external_fallback_match,
)

DEFAULT_REVIEW_THRESHOLD = 0.72
SAFE_AUTO_APPLY_THRESHOLD = 0.90
DEFAULT_MATCH_AUDIT_MAX_RETRIES = 5
DEFAULT_MATCH_AUDIT_BACKOFF_SECONDS = 2.0
DEFAULT_MATCH_AUDIT_REQUEST_DELAY_SECONDS = 0.15
DEFAULT_EXTERNAL_FALLBACK_TIMEOUT_SECONDS = 8.0
_DEFAULT_MATCH_AUDIT_REPORT_NAME = "spotify_match_audit_latest.json"
_MATCH_AUDIT_CHECKPOINT_INTERVAL = 10
_SUSPECT_MATCH_TERMS: tuple[str, ...] = (
    "cover",
    "covers",
    "tribute",
    "karaoke",
    "instrumental",
    "remix",
    "remixes",
    "live",
    "acoustic",
    "demo",
    "edit",
    "piano",
    "lullaby",
    "reimagined",
    "orchestra",
    "versions",
)
_RETRYABLE_AUDIT_STATUSES: set[str] = {"error"}
_RETRYABLE_ERROR_CATEGORIES: set[str] = {"rate_limited", "transient"}
_AUDIT_REVIEWABLE_STATUSES: set[str] = {
    "review_queue",
    "review_suspicious",
    "safe_auto_candidate",
    "low_confidence",
}
_MATCH_AUDIT_SCOPES: tuple[str, ...] = ("collection", "wantlist", "both")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return int(text)
            except ValueError:
                return default
    return default


def _coerce_int_optional(value: object) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return int(text)
            except ValueError:
                return None
    return None


def _coerce_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return float(text)
            except ValueError:
                return default
    return default


def _entry_release_id(entry: dict[str, object]) -> int:
    return _coerce_int(entry.get("discogs_release_id"), 0)


def _as_dict_list(value: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not isinstance(value, list):
        return rows
    for item in value:
        if isinstance(item, dict):
            rows.append(dict(item))
    return rows


def _normalize_album_id(raw: str) -> str:
    album = raw.strip()
    if not album:
        raise ValueError("Spotify album id cannot be empty.")

    if album.startswith("spotify:album:"):
        album = album.removeprefix("spotify:album:")

    url_match = re.search(
        r"(?:https?://)?open\.spotify\.com/album/([A-Za-z0-9]+)", album
    )
    if url_match:
        album = url_match.group(1)

    album = album.split("?", 1)[0].strip("/")
    if "/" in album:
        album = album.rsplit("/", 1)[-1]

    if not album:
        raise ValueError("Spotify album id cannot be empty.")
    if not re.fullmatch(r"[A-Za-z0-9]+", album):
        raise ValueError(
            "Spotify album id must be an alphanumeric album id, spotify:album URI, or open.spotify.com album URL."
        )
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


def _result_from_external_fallback(
    release: dict[str, Any],
    fallback: ExternalFallbackMatch,
    *,
    trigger_error: str,
) -> dict[str, object]:
    return {
        "discogs_release_id": release["discogs_release_id"],
        "artist": release.get("artist"),
        "title": release.get("title"),
        "matched": True,
        "spotify_album_id": fallback.spotify_album_id,
        "confidence": float(fallback.confidence),
        "best_candidate": None,
        "candidates": [],
        "source": f"external_fallback:{fallback.source}",
        "note": f"{fallback.note} Triggered by: {trigger_error}",
    }


def _match_single_release(
    conn,
    *,
    release: dict[str, Any],
    matcher: MatchingService,
    max_retries: int = DEFAULT_MATCH_AUDIT_MAX_RETRIES,
    backoff_seconds: float = DEFAULT_MATCH_AUDIT_BACKOFF_SECONDS,
    commit_mapping: bool = True,
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

    match, error_message, _retry_count, error_category = _match_with_backoff(
        matcher,
        release,
        max_retries=max(0, int(max_retries)),
        backoff_seconds=max(0.0, float(backoff_seconds)),
    )
    if match is None:
        if str(error_category or "").strip().lower() == "auth":
            raise PlayerAuthError(error_message or "Spotify auth failed.")
        raise PlayerApiError(error_message or "Spotify matching failed.")

    upsert_spotify_mapping(
        conn,
        discogs_release_id=int(release["discogs_release_id"]),
        spotify_album_id=match.spotify_album_id,
        confidence=match.confidence,
        last_checked_at=_now_iso(),
        is_override=False,
        commit=commit_mapping,
    )
    return _result_from_matching(release, match)


def _default_match_audit_report_path() -> Path:
    return data_dir() / "reports" / _DEFAULT_MATCH_AUDIT_REPORT_NAME


def _normalize_match_audit_scope(scope: str | None) -> str:
    value = str(scope or "collection").strip().lower() or "collection"
    if value not in _MATCH_AUDIT_SCOPES:
        valid = ", ".join(_MATCH_AUDIT_SCOPES)
        raise ValueError(f"scope must be one of: {valid}.")
    return value


def _query_unmatched_scope_releases(conn, *, scope: str) -> list[dict[str, Any]]:
    if scope == "collection":
        releases = query_releases(conn, unmatched=True, limit=None)
        return [{**dict(item), "match_scope_source": "collection"} for item in releases]

    if scope == "wantlist":
        releases = query_wantlist(conn, unmatched=True, limit=None)
        return [{**dict(item), "match_scope_source": "wantlist"} for item in releases]

    # scope == "both": de-duplicate by Discogs release id while preserving order.
    combined: list[dict[str, Any]] = []
    seen_release_ids: set[int] = set()
    for source_name, source_rows in (
        ("collection", query_releases(conn, unmatched=True, limit=None)),
        ("wantlist", query_wantlist(conn, unmatched=True, limit=None)),
    ):
        for item in source_rows:
            release_id_raw = item.get("discogs_release_id")
            if not isinstance(release_id_raw, int):
                continue
            release_id = int(release_id_raw)
            if release_id in seen_release_ids:
                continue
            seen_release_ids.add(release_id)
            combined.append({**dict(item), "match_scope_source": source_name})
    return combined


def _resolve_match_audit_report_path(
    report_path: str | None, *, export_report: bool
) -> Path | None:
    if not export_report:
        return None
    if report_path:
        return Path(report_path).expanduser()
    return _default_match_audit_report_path()


def _write_match_audit_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def _load_resume_entries(path: Path) -> dict[int, dict[str, object]]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("entries")
    if not isinstance(rows, list):
        return {}

    entries: dict[int, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        release_id = row.get("discogs_release_id")
        if not isinstance(release_id, int):
            continue
        entries[int(release_id)] = dict(row)
    return entries


def _load_match_audit_payload(path: Path) -> dict[str, object]:
    if not path.exists():
        raise ValueError(f"Match audit report path does not exist: {path}")
    if path.is_dir():
        raise ValueError(f"Match audit report path is a directory: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Match audit report is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Match audit report payload must be a JSON object.")
    return raw


def _entry_status(entry: dict[str, object]) -> str:
    return str(entry.get("status") or "").strip().lower()


def _should_retry_resume_entry(
    entry: dict[str, object], *, retry_errors_on_resume: bool
) -> bool:
    if not retry_errors_on_resume:
        return False
    if _entry_status(entry) not in _RETRYABLE_AUDIT_STATUSES:
        return False

    retryable_field = entry.get("error_retryable")
    if isinstance(retryable_field, bool):
        return retryable_field

    category = str(entry.get("error_category") or "").strip().lower()
    if category:
        return category in _RETRYABLE_ERROR_CATEGORIES

    # Backward compatibility for older reports that only have a free-form error string.
    inferred = _classify_error_text(str(entry.get("error") or ""))
    return inferred in _RETRYABLE_ERROR_CATEGORIES


def _entry_has_candidate(entry: dict[str, object]) -> bool:
    candidate_album_id = str(entry.get("candidate_album_id") or "").strip()
    return bool(candidate_album_id)


def _entry_is_review_candidate(entry: dict[str, object]) -> bool:
    status = _entry_status(entry)
    if status in {"auto_applied", "manual_applied", "manual_rejected", "error"}:
        return False
    if not _entry_has_candidate(entry):
        return False
    if bool(entry.get("queued_for_review")):
        return True
    return status in _AUDIT_REVIEWABLE_STATUSES


def _coerce_release_ids(values: list[int] | None) -> set[int]:
    if not values:
        return set()
    normalized: set[int] = set()
    for raw in values:
        release_id = int(raw)
        if release_id <= 0:
            raise ValueError("release_ids values must be positive integers.")
        normalized.add(release_id)
    return normalized


def _serialize_candidate(candidate: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(candidate, dict):
        return None
    artists_raw = candidate.get("artists")
    artists: list[str] = []
    if isinstance(artists_raw, list):
        for value in artists_raw:
            text = str(value).strip()
            if text:
                artists.append(text)
    payload: dict[str, object] = {
        "id": str(candidate.get("id") or "").strip() or None,
        "name": str(candidate.get("name") or "").strip() or None,
        "artists": artists,
        "release_date": str(candidate.get("release_date") or "").strip() or None,
        "external_url": str(candidate.get("external_url") or "").strip() or None,
    }
    confidence = candidate.get("confidence")
    if isinstance(confidence, (int, float)):
        payload["confidence"] = float(confidence)
    return payload


def _candidate_album_id(candidate: dict[str, object] | None) -> str | None:
    if not isinstance(candidate, dict):
        return None
    album_id = str(candidate.get("id") or "").strip()
    return album_id or None


def _is_suspicious_candidate(
    release: dict[str, Any], candidate: dict[str, object] | None
) -> bool:
    if not isinstance(candidate, dict):
        return False
    candidate_name = str(candidate.get("name") or "")
    artists_raw = candidate.get("artists")
    artists_joined = ", ".join(artists_raw) if isinstance(artists_raw, list) else ""
    candidate_text = f"{candidate_name} {artists_joined}".lower()
    release_text = (
        f"{str(release.get('artist') or '')} {str(release.get('title') or '')}".lower()
    )
    return any(term in candidate_text and term not in release_text for term in _SUSPECT_MATCH_TERMS)


def _is_rate_limited_error_text(text: str) -> bool:
    text = str(text or "").lower()
    return "429" in text or "too many requests" in text


_RETRY_AFTER_PATTERN = re.compile(
    r"retry_after\s*=\s*([0-9]+(?:\.[0-9]+)?)",
    flags=re.IGNORECASE,
)


def _extract_retry_after_seconds(error_text: str | None) -> float | None:
    if not error_text:
        return None
    match = _RETRY_AFTER_PATTERN.search(str(error_text))
    if not match:
        return None
    raw = str(match.group(1) or "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if value < 0:
        return None
    return value


def _is_auth_error_text(text: str) -> bool:
    normalized = str(text or "").lower()
    markers = (
        "spotify auth failed",
        "re-authenticate",
        "invalid access token",
        "invalid refresh token",
        "invalid_client",
        "invalid_grant",
        "expired token",
        "authentication",
        "unauthorized",
        "forbidden",
    )
    return any(marker in normalized for marker in markers) or "(401)" in normalized or "(403)" in normalized


def _is_transient_error_text(text: str) -> bool:
    normalized = str(text or "").lower()
    markers = (
        "timed out",
        "timeout",
        "connection reset",
        "connection refused",
        "temporary failure",
        "temporarily unavailable",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "network",
    )
    return any(marker in normalized for marker in markers) or "(502)" in normalized or "(503)" in normalized or "(504)" in normalized


def _classify_error_text(text: str) -> str:
    normalized = str(text or "")
    if _is_rate_limited_error_text(normalized):
        return "rate_limited"
    if _is_auth_error_text(normalized):
        return "auth"
    if _is_transient_error_text(normalized):
        return "transient"
    return "api"


def _format_progress_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    if len(text) > 180:
        text = f"{text[:177]}..."
    return json.dumps(text, ensure_ascii=True)


def _append_match_audit_progress(
    progress_log_file: Path | None,
    *,
    event: str,
    release_id: int | None = None,
    fields: dict[str, object] | None = None,
) -> None:
    if progress_log_file is None:
        return

    segments: list[str] = [f"[{_now_iso()}]", "[AUDIT]", f"event={event}"]
    if release_id is not None:
        segments.append(f"release_id={int(release_id)}")
    if fields:
        for key in sorted(fields.keys()):
            value = fields[key]
            if value is None:
                continue
            formatted = _format_progress_value(value)
            if formatted:
                segments.append(f"{key}={formatted}")

    line = " ".join(segments)
    try:
        progress_log_file.parent.mkdir(parents=True, exist_ok=True)
        with progress_log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")
    except Exception:
        # Progress logging is best-effort and must never break match audit.
        return


def _retry_entry_sort_key(entry: dict[str, object] | None) -> tuple[str, int]:
    if not isinstance(entry, dict):
        return ("", 0)
    checked_at = str(entry.get("checked_at") or "").strip()
    release_id = _coerce_int(entry.get("discogs_release_id"), 0)
    return (checked_at, release_id)


def _match_with_backoff(
    matcher: MatchingService,
    release: dict[str, Any],
    *,
    max_retries: int,
    backoff_seconds: float,
    on_retry: Callable[[int, float, str], None] | None = None,
) -> tuple[MatchingResult | None, str | None, int, str | None]:
    attempts = 0
    while True:
        try:
            return matcher.match_release(release), None, attempts, None
        except Exception as exc:  # noqa: BLE001 - match audit should continue per release.
            category = _classify_error_text(str(exc))
            retryable = category in _RETRYABLE_ERROR_CATEGORIES
            if retryable and attempts < max_retries:
                wait_seconds = float(backoff_seconds) * (2**attempts)
                if on_retry is not None:
                    on_retry(attempts + 1, wait_seconds, str(exc))
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                attempts += 1
                continue
            return None, str(exc), attempts, category


def _confidence_bucket(
    confidence: float | None,
    *,
    has_candidate: bool,
    review_threshold: float,
) -> str:
    if not has_candidate or confidence is None:
        return "no_candidate"
    if confidence >= 0.90:
        return ">=0.90"
    if confidence >= 0.80:
        return "0.80-0.89"
    if confidence >= review_threshold:
        return "0.72-0.79"
    if confidence >= 0.60:
        return "0.60-0.71"
    return "<0.60"


def _match_row_from_audit_entry(entry: dict[str, object]) -> dict[str, object]:
    candidate_album_id = str(entry.get("candidate_album_id") or "").strip() or None
    mapped_album_id = str(entry.get("spotify_album_id") or "").strip() or None
    return {
        "discogs_release_id": entry.get("discogs_release_id"),
        "artist": entry.get("artist"),
        "title": entry.get("title"),
        "scope_source": entry.get("scope_source"),
        "matched": bool(entry.get("applied")),
        "spotify_album_id": mapped_album_id or candidate_album_id,
        "candidate_album_id": candidate_album_id,
        "confidence": entry.get("confidence"),
        "best_candidate": entry.get("best_candidate"),
        "candidates": entry.get("candidates"),
        "source": entry.get("source") or "auto_safe",
        "status": entry.get("status"),
        "note": entry.get("note"),
        "error_category": entry.get("error_category"),
        "error_retryable": entry.get("error_retryable"),
    }


def _summarize_audit_entries(
    entries: list[dict[str, object]],
    *,
    review_threshold: float,
) -> dict[str, object]:
    buckets: dict[str, int] = {
        ">=0.90": 0,
        "0.80-0.89": 0,
        "0.72-0.79": 0,
        "0.60-0.71": 0,
        "<0.60": 0,
        "no_candidate": 0,
    }
    auto_applied_count = 0
    manual_applied_count = 0
    manual_rejected_count = 0
    safe_auto_candidate_count = 0
    review_queue_count = 0
    low_confidence_count = 0
    no_candidate_count = 0
    error_count = 0
    retryable_error_count = 0
    auth_error_count = 0
    rate_limited_error_count = 0
    transient_error_count = 0
    suspicious_count = 0

    review_queue: list[dict[str, object]] = []
    safe_auto_candidates: list[dict[str, object]] = []
    auto_applied: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []

    for entry in entries:
        status = str(entry.get("status") or "")
        has_candidate = bool(str(entry.get("candidate_album_id") or "").strip())
        confidence_raw = entry.get("confidence")
        confidence = (
            float(confidence_raw)
            if isinstance(confidence_raw, (int, float))
            else None
        )

        if status == "error":
            error_count += 1
            error_category = _classify_error_text(str(entry.get("error") or ""))
            if isinstance(entry.get("error_category"), str):
                raw_category = str(entry.get("error_category") or "").strip().lower()
                if raw_category:
                    error_category = raw_category
            if error_category in _RETRYABLE_ERROR_CATEGORIES:
                retryable_error_count += 1
            if error_category == "auth":
                auth_error_count += 1
            if error_category == "rate_limited":
                rate_limited_error_count += 1
            if error_category == "transient":
                transient_error_count += 1
            row = _match_row_from_audit_entry(entry)
            errors.append(
                {
                    **row,
                    "error": entry.get("error"),
                    "error_category": error_category,
                    "error_retryable": error_category in _RETRYABLE_ERROR_CATEGORIES,
                    "retry_count": entry.get("retry_count"),
                }
            )
            continue

        bucket = _confidence_bucket(
            confidence,
            has_candidate=has_candidate,
            review_threshold=review_threshold,
        )
        buckets[bucket] += 1

        if bool(entry.get("suspicious")):
            suspicious_count += 1

        row = _match_row_from_audit_entry(entry)
        if status == "auto_applied":
            auto_applied_count += 1
            auto_applied.append(row)
        if status == "manual_applied":
            manual_applied_count += 1
        if status == "manual_rejected":
            manual_rejected_count += 1
        if bool(entry.get("auto_apply_eligible")):
            safe_auto_candidate_count += 1
            safe_auto_candidates.append(row)
        if bool(entry.get("queued_for_review")):
            review_queue_count += 1
            review_queue.append(row)
        if status == "low_confidence":
            low_confidence_count += 1
        if status == "no_candidate":
            no_candidate_count += 1

    processed_count = len(entries)
    matched_count = auto_applied_count + manual_applied_count
    match_rate_pct = (
        round((matched_count / processed_count) * 100.0, 2) if processed_count else 0.0
    )

    return {
        "processed_count": processed_count,
        "matched_count": matched_count,
        "match_rate_pct": match_rate_pct,
        "auto_applied_count": auto_applied_count,
        "manual_applied_count": manual_applied_count,
        "manual_rejected_count": manual_rejected_count,
        "safe_auto_candidate_count": safe_auto_candidate_count,
        "review_queue_count": review_queue_count,
        "low_confidence_count": low_confidence_count,
        "no_candidate_count": no_candidate_count,
        "error_count": error_count,
        "retryable_error_count": retryable_error_count,
        "auth_error_count": auth_error_count,
        "rate_limited_error_count": rate_limited_error_count,
        "transient_error_count": transient_error_count,
        "suspicious_count": suspicious_count,
        "buckets": buckets,
        "review_queue": review_queue,
        "safe_auto_candidates": safe_auto_candidates,
        "auto_applied": auto_applied,
        "errors": errors,
    }


def _build_match_audit_payload(
    *,
    scope: str,
    entries: list[dict[str, object]],
    run_entries: list[dict[str, object]],
    report_path: Path | None,
    population_unmatched: int,
    review_threshold: float,
    auto_apply_threshold: float,
    apply_safe_matches: bool,
    resume: bool,
    resumed_entry_count: int,
    request_delay_seconds: float,
    backoff_seconds: float,
    max_retries: int,
    retry_errors_on_resume: bool,
    in_progress: bool,
) -> dict[str, object]:
    summary_all = _summarize_audit_entries(entries, review_threshold=review_threshold)
    summary_run = _summarize_audit_entries(
        run_entries, review_threshold=review_threshold
    )

    return {
        "mode": "match_audit",
        "scope": str(scope),
        "in_progress": bool(in_progress),
        "generated_at": _now_iso(),
        "report_path": str(report_path) if report_path is not None else None,
        "resume": bool(resume),
        "resumed_entry_count": int(resumed_entry_count),
        "population_unmatched": int(population_unmatched),
        "review_threshold": float(review_threshold),
        "auto_apply_threshold": float(auto_apply_threshold),
        "apply_safe_matches": bool(apply_safe_matches),
        "request_delay_seconds": float(request_delay_seconds),
        "backoff_seconds": float(backoff_seconds),
        "max_retries": int(max_retries),
        "retry_errors_on_resume": bool(retry_errors_on_resume),
        "processed_release_ids": [
            release_id
            for item in entries
            if (release_id := _coerce_int_optional(item.get("discogs_release_id")))
            is not None
        ],
        "entries": entries,
        "run_entries": run_entries,
        "processed_count": summary_all["processed_count"],
        "run_processed_count": summary_run["processed_count"],
        "matched_count": summary_all["matched_count"],
        "run_matched_count": summary_run["matched_count"],
        "match_rate_pct": summary_all["match_rate_pct"],
        "run_match_rate_pct": summary_run["match_rate_pct"],
        "auto_applied_count": summary_all["auto_applied_count"],
        "run_auto_applied_count": summary_run["auto_applied_count"],
        "manual_applied_count": summary_all["manual_applied_count"],
        "run_manual_applied_count": summary_run["manual_applied_count"],
        "manual_rejected_count": summary_all["manual_rejected_count"],
        "run_manual_rejected_count": summary_run["manual_rejected_count"],
        "safe_auto_candidate_count": summary_all["safe_auto_candidate_count"],
        "run_safe_auto_candidate_count": summary_run["safe_auto_candidate_count"],
        "review_queue_count": summary_all["review_queue_count"],
        "run_review_queue_count": summary_run["review_queue_count"],
        "low_confidence_count": summary_all["low_confidence_count"],
        "run_low_confidence_count": summary_run["low_confidence_count"],
        "no_candidate_count": summary_all["no_candidate_count"],
        "run_no_candidate_count": summary_run["no_candidate_count"],
        "error_count": summary_all["error_count"],
        "run_error_count": summary_run["error_count"],
        "retryable_error_count": summary_all["retryable_error_count"],
        "run_retryable_error_count": summary_run["retryable_error_count"],
        "auth_error_count": summary_all["auth_error_count"],
        "run_auth_error_count": summary_run["auth_error_count"],
        "rate_limited_error_count": summary_all["rate_limited_error_count"],
        "run_rate_limited_error_count": summary_run["rate_limited_error_count"],
        "transient_error_count": summary_all["transient_error_count"],
        "run_transient_error_count": summary_run["transient_error_count"],
        "suspicious_count": summary_all["suspicious_count"],
        "run_suspicious_count": summary_run["suspicious_count"],
        "buckets": summary_all["buckets"],
        "run_buckets": summary_run["buckets"],
        "review_queue": summary_all["review_queue"],
        "safe_auto_candidates": summary_all["safe_auto_candidates"],
        "auto_applied": summary_all["auto_applied"],
        "errors": summary_all["errors"],
    }


_COMPACT_RUN_ENTRY_KEYS: tuple[str, ...] = (
    "discogs_release_id",
    "artist",
    "title",
    "scope_source",
    "status",
    "matched",
    "applied",
    "auto_apply_eligible",
    "queued_for_review",
    "confidence",
    "spotify_album_id",
    "candidate_album_id",
    "suspicious",
    "retry_count",
    "error",
    "error_category",
    "error_retryable",
    "retry_after_seconds",
    "note",
    "source",
    "checked_at",
)


def _compact_run_entry_for_output(entry: dict[str, object]) -> dict[str, object]:
    compact: dict[str, object] = {}
    for key in _COMPACT_RUN_ENTRY_KEYS:
        if key in entry:
            compact[key] = entry[key]
    return compact


def _compact_match_audit_output(payload: dict[str, object]) -> dict[str, object]:
    compact = {
        key: value
        for key, value in payload.items()
        if key
        not in {
            "entries",
            "processed_release_ids",
            "review_queue",
            "safe_auto_candidates",
            "auto_applied",
            "errors",
        }
    }
    run_entries_raw = payload.get("run_entries")
    run_entries: list[dict[str, object]] = []
    if isinstance(run_entries_raw, list):
        for item in run_entries_raw:
            if isinstance(item, dict):
                run_entries.append(_compact_run_entry_for_output(item))
    compact["run_entries"] = run_entries
    compact["compact_output"] = True
    return compact


def run_match_release(
    discogs_release_id: int,
    *,
    threshold: float = DEFAULT_REVIEW_THRESHOLD,
    max_retries: int = DEFAULT_MATCH_AUDIT_MAX_RETRIES,
    backoff_seconds: float = DEFAULT_MATCH_AUDIT_BACKOFF_SECONDS,
    external_fallback: bool = True,
    external_fallback_timeout_seconds: float = DEFAULT_EXTERNAL_FALLBACK_TIMEOUT_SECONDS,
) -> dict[str, object]:
    threshold = clamp_threshold(float(threshold))
    if int(max_retries) < 0:
        raise ValueError("max_retries must be >= 0.")
    if float(backoff_seconds) < 0:
        raise ValueError("backoff_seconds must be >= 0.")
    if float(external_fallback_timeout_seconds) < 0:
        raise ValueError("external_fallback_timeout_seconds must be >= 0.")

    conn = get_connection()
    try:
        release = get_release_by_id(conn, int(discogs_release_id))
        if release is None:
            # Fallback to wantlist.
            release = get_wantlist_by_id(conn, int(discogs_release_id))

        if release is None:
            raise ValueError(
                f"Discogs release {discogs_release_id} was not found in local database."
            )

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

        backend = get_player_backend()
        client = backend.create_matching_client(conn=conn)
        matcher = MatchingService(client, threshold=threshold)
        try:
            result = _match_single_release(
                conn,
                release=release,
                matcher=matcher,
                max_retries=int(max_retries),
                backoff_seconds=float(backoff_seconds),
            )
        except PlayerApiError as exc:
            if (not external_fallback) or (
                _classify_error_text(str(exc)) != "rate_limited"
            ):
                raise
            fallback = resolve_external_fallback_match(
                release,
                timeout_seconds=max(1.0, float(external_fallback_timeout_seconds)),
            )
            if fallback is None:
                raise
            upsert_spotify_mapping(
                conn,
                discogs_release_id=int(release["discogs_release_id"]),
                spotify_album_id=fallback.spotify_album_id,
                confidence=float(fallback.confidence),
                last_checked_at=_now_iso(),
                is_override=False,
            )
            result = _result_from_external_fallback(
                release,
                fallback,
                trigger_error=str(exc),
            )
    finally:
        conn.close()

    return result


def run_match_audit(
    *,
    scope: str | None = None,
    limit: int | None = None,
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
    auto_apply_threshold: float = SAFE_AUTO_APPLY_THRESHOLD,
    apply_safe_matches: bool = False,
    resume: bool = False,
    report_path: str | None = None,
    export_report: bool = True,
    request_delay_seconds: float = DEFAULT_MATCH_AUDIT_REQUEST_DELAY_SECONDS,
    backoff_seconds: float = DEFAULT_MATCH_AUDIT_BACKOFF_SECONDS,
    max_retries: int = DEFAULT_MATCH_AUDIT_MAX_RETRIES,
    retry_errors_on_resume: bool = True,
    compact_output: bool = False,
    progress_log_path: str | None = None,
) -> dict[str, object]:
    scope_value = _normalize_match_audit_scope(scope)
    review_threshold = clamp_threshold(float(review_threshold))
    auto_apply_threshold = clamp_threshold(float(auto_apply_threshold))
    if auto_apply_threshold < review_threshold:
        raise ValueError(
            "auto_apply_threshold must be greater than or equal to review_threshold."
        )
    if limit is not None and int(limit) < 1:
        raise ValueError("limit must be >= 1 when provided.")
    if float(request_delay_seconds) < 0:
        raise ValueError("request_delay_seconds must be >= 0.")
    if float(backoff_seconds) < 0:
        raise ValueError("backoff_seconds must be >= 0.")
    if int(max_retries) < 0:
        raise ValueError("max_retries must be >= 0.")

    request_delay_seconds = float(request_delay_seconds)
    backoff_seconds = float(backoff_seconds)
    max_retries = int(max_retries)

    report_file = _resolve_match_audit_report_path(
        report_path, export_report=export_report
    )
    if resume and report_file is not None and report_file.exists():
        try:
            prior_payload = _load_match_audit_payload(report_file)
            report_scope_raw = prior_payload.get("scope")
            report_scope = (
                _normalize_match_audit_scope(str(report_scope_raw))
                if str(report_scope_raw or "").strip()
                else None
            )
            if report_scope is not None:
                if scope is None:
                    scope_value = report_scope
                elif report_scope != scope_value:
                    raise ValueError(
                        "Requested scope does not match existing report scope: "
                        f"requested={scope_value}, report={report_scope}. "
                        "Use matching --scope or a different --report path."
                    )
        except ValueError:
            raise
        except Exception:
            # Ignore legacy/malformed report parsing errors here; resume loading
            # will handle them through standard validation paths.
            pass

    progress_log_text = str(progress_log_path or "").strip()
    progress_log_file = (
        Path(progress_log_text).expanduser() if progress_log_text else None
    )
    resumed_entries: dict[int, dict[str, object]] = {}
    if resume and report_file is not None:
        resumed_entries = _load_resume_entries(report_file)

    conn = get_connection()
    try:
        releases = _query_unmatched_scope_releases(conn, scope=scope_value)
        backend = get_player_backend()
        client = backend.create_matching_client(conn=conn)
        matcher = MatchingService(client, threshold=review_threshold)

        entries_by_id: dict[int, dict[str, object]] = dict(resumed_entries)
        run_ids: list[int] = []
        fresh_pending_releases: list[dict[str, Any]] = []
        retry_pending_releases: list[dict[str, Any]] = []
        for release in releases:
            release_id = int(release["discogs_release_id"])
            resumed_entry = entries_by_id.get(release_id)
            if resumed_entry is None:
                fresh_pending_releases.append(release)
                continue
            if _should_retry_resume_entry(
                resumed_entry, retry_errors_on_resume=retry_errors_on_resume
            ):
                retry_pending_releases.append(release)

        # When retrying errors with a small batch limit, rotate across oldest
        # errored entries first instead of repeatedly hammering the same ID.
        retry_pending_releases.sort(
            key=lambda release: _retry_entry_sort_key(
                entries_by_id.get(int(release.get("discogs_release_id") or 0))
            )
        )

        pending_releases = [*fresh_pending_releases, *retry_pending_releases]
        if limit is not None:
            pending_releases = pending_releases[: max(1, int(limit))]

        pending_mapping_updates = 0
        for index, release in enumerate(pending_releases):
            release_id = int(release["discogs_release_id"])
            _append_match_audit_progress(
                progress_log_file,
                event="start",
                release_id=release_id,
                fields={
                    "index": index + 1,
                    "total": len(pending_releases),
                    "artist": release.get("artist"),
                    "title": release.get("title"),
                },
            )
            def _on_retry_wait(
                attempt: int,
                wait_seconds: float,
                reason: str,
                rid: int = release_id,
            ) -> None:
                _append_match_audit_progress(
                    progress_log_file,
                    event="retry_wait",
                    release_id=rid,
                    fields={
                        "attempt": attempt,
                        "wait_seconds": wait_seconds,
                        "reason": reason,
                    },
                )

            match, error_message, retry_count, error_category = _match_with_backoff(
                matcher,
                release,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
                on_retry=_on_retry_wait,
            )

            entry: dict[str, object]
            if match is None:
                error_category_value = str(error_category or "api").strip().lower() or "api"
                error_retryable = error_category_value in _RETRYABLE_ERROR_CATEGORIES
                retry_after_seconds = _extract_retry_after_seconds(error_message)
                entry = {
                    "discogs_release_id": release_id,
                    "artist": release.get("artist"),
                    "title": release.get("title"),
                    "scope_source": release.get("match_scope_source"),
                    "matched": False,
                    "applied": False,
                    "auto_apply_eligible": False,
                    "queued_for_review": False,
                    "status": "error",
                    "confidence": None,
                    "spotify_album_id": None,
                    "candidate_album_id": None,
                    "best_candidate": None,
                    "candidates": [],
                    "suspicious": False,
                    "error": error_message,
                    "error_category": error_category_value,
                    "error_retryable": error_retryable,
                    "retry_after_seconds": retry_after_seconds,
                    "retry_count": int(retry_count),
                    "source": "audit",
                    "checked_at": _now_iso(),
                }
            else:
                best_candidate = _serialize_candidate(match.best_candidate)
                candidate_album_id = _candidate_album_id(match.best_candidate)
                confidence = float(match.confidence)
                suspicious = _is_suspicious_candidate(release, match.best_candidate)
                auto_apply_eligible = bool(
                    candidate_album_id
                    and confidence >= auto_apply_threshold
                    and not suspicious
                )
                queued_for_review = bool(
                    candidate_album_id
                    and (
                        (confidence >= review_threshold and confidence < auto_apply_threshold)
                        or suspicious
                    )
                )

                applied = bool(auto_apply_eligible and apply_safe_matches)
                status = "no_candidate"
                note = ""
                spotify_album_id = None
                if applied:
                    status = "auto_applied"
                    spotify_album_id = candidate_album_id
                    note = "Safe auto-apply persisted."
                    upsert_spotify_mapping(
                        conn,
                        discogs_release_id=release_id,
                        spotify_album_id=candidate_album_id,
                        confidence=confidence,
                        last_checked_at=_now_iso(),
                        is_override=False,
                        commit=False,
                    )
                    pending_mapping_updates += 1
                elif auto_apply_eligible:
                    status = "safe_auto_candidate"
                    note = "Eligible for safe auto-apply."
                elif queued_for_review:
                    status = "review_suspicious" if suspicious else "review_queue"
                    note = "Queued for manual review."
                elif candidate_album_id:
                    status = "low_confidence"
                    note = "Best candidate below review threshold."

                entry = {
                    "discogs_release_id": release_id,
                    "artist": release.get("artist"),
                    "title": release.get("title"),
                    "scope_source": release.get("match_scope_source"),
                    "matched": applied,
                    "applied": applied,
                    "auto_apply_eligible": auto_apply_eligible,
                    "queued_for_review": queued_for_review,
                    "status": status,
                    "note": note,
                    "confidence": confidence,
                    "spotify_album_id": spotify_album_id,
                    "candidate_album_id": candidate_album_id,
                    "best_candidate": best_candidate,
                    "candidates": [
                        _serialize_candidate(item)
                        for item in match.candidates
                        if isinstance(item, dict)
                    ],
                    "suspicious": suspicious,
                    "error": None,
                    "error_category": None,
                    "error_retryable": False,
                    "retry_after_seconds": None,
                    "retry_count": int(retry_count),
                    "source": "audit",
                    "checked_at": _now_iso(),
                }

            entries_by_id[release_id] = entry
            run_ids.append(release_id)
            _append_match_audit_progress(
                progress_log_file,
                event="complete",
                release_id=release_id,
                fields={
                    "status": entry.get("status"),
                    "matched": entry.get("matched"),
                    "retry_count": entry.get("retry_count"),
                    "confidence": entry.get("confidence"),
                    "spotify_album_id": entry.get("spotify_album_id"),
                    "candidate_album_id": entry.get("candidate_album_id"),
                    "error": entry.get("error"),
                    "error_category": entry.get("error_category"),
                    "retry_after_seconds": entry.get("retry_after_seconds"),
                },
            )

            should_checkpoint = (
                report_file is not None
                and (
                    (index + 1) % _MATCH_AUDIT_CHECKPOINT_INTERVAL == 0
                    or index == (len(pending_releases) - 1)
                )
            )
            if should_checkpoint:
                assert report_file is not None
                all_entries = sorted(
                    entries_by_id.values(),
                    key=_entry_release_id,
                )
                run_entries = [
                    entries_by_id[row_id] for row_id in run_ids if row_id in entries_by_id
                ]
                checkpoint = _build_match_audit_payload(
                    scope=scope_value,
                    entries=all_entries,
                    run_entries=run_entries,
                    report_path=report_file,
                    population_unmatched=len(releases),
                    review_threshold=review_threshold,
                    auto_apply_threshold=auto_apply_threshold,
                    apply_safe_matches=apply_safe_matches,
                    resume=resume,
                    resumed_entry_count=len(resumed_entries),
                    request_delay_seconds=request_delay_seconds,
                    backoff_seconds=backoff_seconds,
                    max_retries=max_retries,
                    retry_errors_on_resume=retry_errors_on_resume,
                    in_progress=True,
                )
                _write_match_audit_report(report_file, checkpoint)

            if request_delay_seconds > 0 and index < (len(pending_releases) - 1):
                time.sleep(request_delay_seconds)

        if pending_mapping_updates > 0:
            conn.commit()

        all_entries = sorted(
            entries_by_id.values(),
            key=_entry_release_id,
        )
        run_entries = [entries_by_id[row_id] for row_id in run_ids if row_id in entries_by_id]
        payload = _build_match_audit_payload(
            scope=scope_value,
            entries=all_entries,
            run_entries=run_entries,
            report_path=report_file,
            population_unmatched=len(releases),
            review_threshold=review_threshold,
            auto_apply_threshold=auto_apply_threshold,
            apply_safe_matches=apply_safe_matches,
            resume=resume,
            resumed_entry_count=len(resumed_entries),
            request_delay_seconds=request_delay_seconds,
            backoff_seconds=backoff_seconds,
            max_retries=max_retries,
            retry_errors_on_resume=retry_errors_on_resume,
            in_progress=False,
        )
    finally:
        conn.close()

    if report_file is not None:
        _write_match_audit_report(report_file, payload)

    if compact_output:
        return _compact_match_audit_output(payload)
    return payload


def _resolve_existing_match_audit_report_path(report_path: str | None) -> Path:
    if report_path:
        path = Path(report_path).expanduser()
    else:
        path = _default_match_audit_report_path()
    if not path.exists():
        raise ValueError(f"Match audit report path does not exist: {path}")
    if path.is_dir():
        raise ValueError(f"Match audit report path is a directory: {path}")
    return path


def _read_report_entries(raw: dict[str, object]) -> list[dict[str, object]]:
    entries_raw = raw.get("entries")
    if not isinstance(entries_raw, list):
        raise ValueError("Match audit report is missing a valid 'entries' list.")
    entries: list[dict[str, object]] = []
    for item in entries_raw:
        if isinstance(item, dict):
            entries.append(dict(item))
    return entries


def _report_float(raw: dict[str, object], key: str, default: float) -> float:
    value = raw.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except Exception:  # noqa: BLE001 - fallback to stable defaults.
        return float(default)


def _report_int(raw: dict[str, object], key: str, default: int) -> int:
    value = raw.get(key)
    if isinstance(value, int):
        return int(value)
    try:
        return int(str(value))
    except Exception:  # noqa: BLE001 - fallback to stable defaults.
        return int(default)


def _rebuild_audit_payload(
    *,
    raw: dict[str, object],
    report_file: Path,
    entries: list[dict[str, object]],
    run_entries: list[dict[str, object]],
) -> dict[str, object]:
    return _build_match_audit_payload(
        scope=_normalize_match_audit_scope(str(raw.get("scope") or "collection")),
        entries=entries,
        run_entries=run_entries,
        report_path=report_file,
        population_unmatched=_report_int(raw, "population_unmatched", len(entries)),
        review_threshold=clamp_threshold(
            _report_float(raw, "review_threshold", DEFAULT_REVIEW_THRESHOLD)
        ),
        auto_apply_threshold=clamp_threshold(
            _report_float(raw, "auto_apply_threshold", SAFE_AUTO_APPLY_THRESHOLD)
        ),
        apply_safe_matches=bool(raw.get("apply_safe_matches")),
        resume=bool(raw.get("resume")),
        resumed_entry_count=_report_int(raw, "resumed_entry_count", 0),
        request_delay_seconds=max(
            0.0,
            _report_float(
                raw, "request_delay_seconds", DEFAULT_MATCH_AUDIT_REQUEST_DELAY_SECONDS
            ),
        ),
        backoff_seconds=max(
            0.0,
            _report_float(raw, "backoff_seconds", DEFAULT_MATCH_AUDIT_BACKOFF_SECONDS),
        ),
        max_retries=max(0, _report_int(raw, "max_retries", DEFAULT_MATCH_AUDIT_MAX_RETRIES)),
        retry_errors_on_resume=bool(raw.get("retry_errors_on_resume", True)),
        in_progress=False,
    )


def run_match_audit_review_list(
    *,
    report_path: str | None = None,
    limit: int | None = 50,
) -> dict[str, object]:
    if limit is not None and int(limit) < 1:
        raise ValueError("limit must be >= 1 when provided.")

    report_file = _resolve_existing_match_audit_report_path(report_path)
    raw = _load_match_audit_payload(report_file)
    entries = _read_report_entries(raw)

    review_entries: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    for entry in entries:
        status = _entry_status(entry)
        row = _match_row_from_audit_entry(entry)
        row["status"] = status
        if _entry_is_review_candidate(entry):
            review_entries.append(row)
        elif status == "error":
            row["error"] = entry.get("error")
            row["retry_count"] = entry.get("retry_count")
            row["error_category"] = entry.get("error_category")
            row["error_retryable"] = entry.get("error_retryable")
            errors.append(row)

    review_entries.sort(key=lambda item: _coerce_float(item.get("confidence"), -1.0), reverse=True)
    errors.sort(key=_entry_release_id)

    if limit is not None:
        review_items = review_entries[: int(limit)]
        error_items = errors[: int(limit)]
    else:
        review_items = review_entries
        error_items = errors

    return {
        "ok": True,
        "report_path": str(report_file),
        "review_count": len(review_entries),
        "error_count": len(errors),
        "manual_applied_count": sum(
            1 for item in entries if _entry_status(item) == "manual_applied"
        ),
        "manual_rejected_count": sum(
            1 for item in entries if _entry_status(item) == "manual_rejected"
        ),
        "review_queue": review_items,
        "errors": error_items,
    }


def run_match_audit_review_action(
    *,
    action: str,
    report_path: str | None = None,
    release_ids: list[int] | None = None,
    apply_all: bool = False,
) -> dict[str, object]:
    action_value = str(action or "").strip().lower()
    if action_value not in {"apply", "reject"}:
        raise ValueError("action must be 'apply' or 'reject'.")

    selected_release_ids = _coerce_release_ids(release_ids)
    if apply_all and selected_release_ids:
        raise ValueError("Use either apply_all=True or release_ids, not both.")
    if not apply_all and not selected_release_ids:
        raise ValueError("Provide release_ids or apply_all=True.")

    report_file = _resolve_existing_match_audit_report_path(report_path)
    raw = _load_match_audit_payload(report_file)
    entries = _read_report_entries(raw)

    entries_by_id: dict[int, dict[str, object]] = {}
    candidate_ids: set[int] = set()
    for entry in entries:
        release_id = entry.get("discogs_release_id")
        if not isinstance(release_id, int):
            continue
        entries_by_id[int(release_id)] = entry
        if _entry_is_review_candidate(entry):
            candidate_ids.add(int(release_id))

    if apply_all:
        target_ids = set(candidate_ids)
    else:
        target_ids = set(release_id for release_id in selected_release_ids if release_id in candidate_ids)

    if not target_ids:
        raise ValueError("No matching review-candidate entries found for requested release ids.")

    updated_entries: list[dict[str, object]] = []

    conn = get_connection() if action_value == "apply" else None
    pending_mapping_updates = 0
    try:
        for release_id in sorted(target_ids):
            entry = entries_by_id[release_id]
            candidate_album_id = str(entry.get("candidate_album_id") or "").strip()
            if not candidate_album_id:
                continue

            confidence_raw = entry.get("confidence")
            confidence = (
                float(confidence_raw)
                if isinstance(confidence_raw, (int, float))
                else None
            )

            if conn is not None:
                upsert_spotify_mapping(
                    conn,
                    discogs_release_id=release_id,
                    spotify_album_id=candidate_album_id,
                    confidence=confidence,
                    last_checked_at=_now_iso(),
                    is_override=False,
                    commit=False,
                )
                pending_mapping_updates += 1

            if action_value == "apply":
                entry["matched"] = True
                entry["applied"] = True
                entry["spotify_album_id"] = candidate_album_id
                entry["status"] = "manual_applied"
                entry["note"] = "Applied from audit review."
            else:
                entry["matched"] = False
                entry["applied"] = False
                entry["spotify_album_id"] = None
                entry["status"] = "manual_rejected"
                entry["note"] = "Rejected from audit review."

            entry["queued_for_review"] = False
            entry["source"] = "audit_review"
            entry["checked_at"] = _now_iso()
            entry["error"] = None
            updated_entries.append(dict(entry))
        if conn is not None and pending_mapping_updates > 0:
            conn.commit()
    finally:
        if conn is not None:
            conn.close()

    all_entries = sorted(
        entries_by_id.values(),
        key=_entry_release_id,
    )
    run_entries = sorted(
        updated_entries,
        key=_entry_release_id,
    )
    payload = _rebuild_audit_payload(
        raw=raw,
        report_file=report_file,
        entries=all_entries,
        run_entries=run_entries,
    )
    _write_match_audit_report(report_file, payload)

    return {
        "ok": True,
        "action": action_value,
        "report_path": str(report_file),
        "selected_count": len(target_ids),
        "updated_count": len(run_entries),
        "updated_release_ids": [
            _entry_release_id(item) for item in run_entries
        ],
        "run_manual_applied_count": _coerce_int(payload.get("run_manual_applied_count"), 0),
        "run_manual_rejected_count": _coerce_int(payload.get("run_manual_rejected_count"), 0),
        "run_review_queue_count": _coerce_int(payload.get("run_review_queue_count"), 0),
        "review_queue_count": _coerce_int(payload.get("review_queue_count"), 0),
        "status_message": (
            "Applied selected review candidates."
            if action_value == "apply"
            else "Rejected selected review candidates."
        ),
    }


def run_match_audit_retry_errors(
    *,
    limit: int | None = None,
    scope: str | None = None,
    report_path: str | None = None,
    request_delay_seconds: float = DEFAULT_MATCH_AUDIT_REQUEST_DELAY_SECONDS,
    backoff_seconds: float = DEFAULT_MATCH_AUDIT_BACKOFF_SECONDS,
    max_retries: int = DEFAULT_MATCH_AUDIT_MAX_RETRIES,
    apply_safe_matches: bool = False,
) -> dict[str, object]:
    return run_match_audit(
        scope=scope,
        limit=limit,
        apply_safe_matches=apply_safe_matches,
        resume=True,
        report_path=report_path,
        request_delay_seconds=request_delay_seconds,
        backoff_seconds=backoff_seconds,
        max_retries=max_retries,
        retry_errors_on_resume=True,
    )


def run_match_unmatched(
    *,
    limit: int = 25,
    scope: str = "collection",
    threshold: float = DEFAULT_REVIEW_THRESHOLD,
    auto_apply_threshold: float = SAFE_AUTO_APPLY_THRESHOLD,
) -> dict[str, object]:
    summary = run_match_audit(
        scope=scope,
        limit=max(1, int(limit)),
        review_threshold=threshold,
        auto_apply_threshold=auto_apply_threshold,
        apply_safe_matches=True,
        resume=False,
        export_report=False,
        request_delay_seconds=0.0,
    )

    run_entries = [dict(item) for item in _as_dict_list(summary.get("run_entries"))]
    results = [_match_row_from_audit_entry(item) for item in run_entries]
    matched_count = _coerce_int(summary.get("run_auto_applied_count"), 0)
    review_count = _coerce_int(summary.get("run_review_queue_count"), 0)
    error_count = _coerce_int(summary.get("run_error_count"), 0)

    return {
        "processed_count": len(run_entries),
        "matched_count": matched_count,
        "review_count": review_count,
        "error_count": error_count,
        "auto_apply_threshold": float(auto_apply_threshold),
        "review_threshold": float(threshold),
        "results": results,
    }


def run_match_override(
    discogs_release_id: int, spotify_album_id: str
) -> dict[str, object]:
    normalized_album_id = _normalize_album_id(spotify_album_id)

    conn = get_connection()
    try:
        release = get_release_by_id(conn, int(discogs_release_id))
        if release is None:
            # Fallback to wantlist.
            release = get_wantlist_by_id(conn, int(discogs_release_id))

        if release is None:
            raise ValueError(
                f"Discogs release {discogs_release_id} was not found in local database."
            )

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
