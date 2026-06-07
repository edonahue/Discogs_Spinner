"""GUI-friendly wrappers for match/override/play release actions."""

from __future__ import annotations

from typing import Any

from discogs_player.provider_mapping import with_provider_mapping_aliases
from discogs_player.use_cases.ensure_mapping import (
    SAFE_AUTO_APPLY_THRESHOLD,
    run_match_audit,
    run_match_audit_review_action,
    run_match_audit_review_list,
    run_match_audit_retry_errors,
    run_match_override,
    run_match_release,
)
from discogs_player.use_cases.play_release import run_play_release


def _format_confidence(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.3f}"
    return "n/a"


def _as_dict(value: object | None) -> dict[str, object] | None:
    if isinstance(value, dict):
        return value
    return None


def _to_int(value: object | None, *, default: int = 0) -> int:
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


def _candidate_summary(candidate: dict[str, object] | None) -> str | None:
    if not isinstance(candidate, dict):
        return None

    name = str(candidate.get("name") or "").strip()
    artists_raw = candidate.get("artists")
    artists: list[str] = []
    if isinstance(artists_raw, list):
        for value in artists_raw:
            text = str(value).strip()
            if text:
                artists.append(text)

    release_date = str(candidate.get("release_date") or "").strip()
    summary_parts: list[str] = []
    if name:
        summary_parts.append(name)
    if artists:
        summary_parts.append(", ".join(artists))
    if release_date:
        summary_parts.append(release_date)

    return " - ".join(summary_parts) if summary_parts else None


def run_match_action(
    discogs_release_id: int,
    *,
    threshold: float = 0.72,
) -> dict[str, object]:
    raw = run_match_release(
        discogs_release_id,
        threshold=threshold,
        max_retries=0,
        backoff_seconds=1.0,
    )

    matched = bool(raw.get("matched"))
    spotify_album_id = raw.get("spotify_album_id")
    confidence = raw.get("confidence")
    source = str(raw.get("source") or "auto")

    candidate_summary = _candidate_summary(_as_dict(raw.get("best_candidate")))
    if matched and spotify_album_id:
        status_message = (
            f"Matched release {discogs_release_id} to {spotify_album_id} "
            f"(confidence {_format_confidence(confidence)}, source {source})."
        )
    else:
        status_message = (
            f"No confident match for release {discogs_release_id} "
            f"(best confidence {_format_confidence(confidence)})."
        )
        if source == "override":
            status_message = (
                f"Override mapping is active for release {discogs_release_id}: "
                f"{spotify_album_id or 'none'}."
            )

    return with_provider_mapping_aliases(
        {
        "ok": True,
        "action": "match",
        "discogs_release_id": discogs_release_id,
        "matched": matched,
        "spotify_album_id": spotify_album_id,
        "confidence": confidence,
        "source": source,
        "candidate_summary": candidate_summary,
        "status_message": status_message,
        "raw": raw,
        }
    )


def run_match_audit_action(
    *,
    apply_safe_matches: bool = False,
    limit: int | None = None,
    resume: bool = True,
    retry_errors_on_resume: bool = True,
) -> dict[str, object]:
    raw = run_match_audit(
        limit=limit,
        apply_safe_matches=apply_safe_matches,
        auto_apply_threshold=SAFE_AUTO_APPLY_THRESHOLD,
        resume=resume,
        retry_errors_on_resume=retry_errors_on_resume,
    )

    run_processed = _to_int(raw.get("run_processed_count"))
    run_auto_applied = _to_int(raw.get("run_auto_applied_count"))
    run_review_queue = _to_int(raw.get("run_review_queue_count"))
    run_errors = _to_int(raw.get("run_error_count"))
    report_path = str(raw.get("report_path") or "").strip() or None

    action_label = "safe apply + audit" if apply_safe_matches else "audit"
    status_message = (
        f"Match {action_label} complete: processed {run_processed}, "
        f"auto-applied {run_auto_applied}, review queue {run_review_queue}, "
        f"errors {run_errors}."
    )
    if report_path:
        status_message = f"{status_message} Report: {report_path}"

    return {
        "ok": True,
        "action": "match_audit",
        "apply_safe_matches": apply_safe_matches,
        "run_processed_count": run_processed,
        "run_auto_applied_count": run_auto_applied,
        "run_review_queue_count": run_review_queue,
        "run_error_count": run_errors,
        "report_path": report_path,
        "status_message": status_message,
        "raw": raw,
    }


def run_match_review_list_action(
    *,
    report_path: str | None = None,
    limit: int | None = 50,
) -> dict[str, object]:
    raw = run_match_audit_review_list(report_path=report_path, limit=limit)
    review_count = _to_int(raw.get("review_count"))
    error_count = _to_int(raw.get("error_count"))
    return {
        "ok": True,
        "action": "match_review_list",
        "report_path": raw.get("report_path"),
        "review_count": review_count,
        "error_count": error_count,
        "status_message": (
            f"Match review queue loaded: {review_count} candidates, {error_count} errors."
        ),
        "raw": raw,
    }


def run_match_review_apply_action(
    *,
    report_path: str | None = None,
    release_ids: list[int] | None = None,
    apply_all: bool = False,
) -> dict[str, object]:
    raw = run_match_audit_review_action(
        action="apply",
        report_path=report_path,
        release_ids=release_ids,
        apply_all=apply_all,
    )
    updated_count = _to_int(raw.get("updated_count"))
    return {
        "ok": True,
        "action": "match_review_apply",
        "updated_count": updated_count,
        "report_path": raw.get("report_path"),
        "status_message": (
            f"Applied {updated_count} review candidate mappings."
        ),
        "raw": raw,
    }


def run_match_review_reject_action(
    *,
    report_path: str | None = None,
    release_ids: list[int] | None = None,
    apply_all: bool = False,
) -> dict[str, object]:
    raw = run_match_audit_review_action(
        action="reject",
        report_path=report_path,
        release_ids=release_ids,
        apply_all=apply_all,
    )
    updated_count = _to_int(raw.get("updated_count"))
    return {
        "ok": True,
        "action": "match_review_reject",
        "updated_count": updated_count,
        "report_path": raw.get("report_path"),
        "status_message": (
            f"Rejected {updated_count} review candidate mappings."
        ),
        "raw": raw,
    }


def run_match_retry_errors_action(
    *,
    report_path: str | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    raw = run_match_audit_retry_errors(report_path=report_path, limit=limit)
    run_processed = _to_int(raw.get("run_processed_count"))
    run_errors = _to_int(raw.get("run_error_count"))
    return {
        "ok": True,
        "action": "match_retry_errors",
        "run_processed_count": run_processed,
        "run_error_count": run_errors,
        "report_path": raw.get("report_path"),
        "status_message": (
            f"Retried audit error entries: processed {run_processed}, "
            f"remaining errors {run_errors}."
        ),
        "raw": raw,
    }


def run_override_action(
    discogs_release_id: int, spotify_album_id: str
) -> dict[str, object]:
    raw = run_match_override(discogs_release_id, spotify_album_id)
    return with_provider_mapping_aliases(
        {
        "ok": True,
        "action": "override",
        "discogs_release_id": discogs_release_id,
        "spotify_album_id": raw.get("spotify_album_id"),
        "confidence": raw.get("confidence"),
        "is_override": raw.get("is_override"),
        "status_message": (
            f"Override saved for release {discogs_release_id}: "
            f"{raw.get('spotify_album_id')}"
        ),
        "raw": raw,
        }
    )


def run_play_action(
    discogs_release_id: int,
    *,
    auto_match: bool = True,
    open_fallback: bool = True,
) -> dict[str, object]:
    raw = run_play_release(
        discogs_release_id=discogs_release_id,
        auto_match=auto_match,
        open_fallback=open_fallback,
    )

    playback_started = bool(raw.get("playback_started"))
    if playback_started:
        status_message = (
            f"Playback started on {raw.get('device_name') or raw.get('device_id')}: "
            f"{raw.get('spotify_album_id')}"
        )
    else:
        status_message = str(raw.get("message") or "Playback did not start.")
        fallback_url = str(raw.get("fallback_open_url") or "").strip()
        if fallback_url:
            status_message = f"{status_message} Open URL: {fallback_url}"

    return with_provider_mapping_aliases(
        {
        "ok": True,
        "action": "play",
        "discogs_release_id": discogs_release_id,
        "playback_started": playback_started,
        "spotify_album_id": raw.get("spotify_album_id"),
        "fallback_reason": raw.get("fallback_reason"),
        "fallback_open_url": raw.get("fallback_open_url"),
        "status_message": status_message,
        "raw": raw,
        }
    )
