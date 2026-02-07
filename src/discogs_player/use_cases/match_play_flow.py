"""GUI-friendly wrappers for match/override/play release actions."""

from __future__ import annotations

from typing import Any

from discogs_player.use_cases.ensure_mapping import run_match_override, run_match_release
from discogs_player.use_cases.play_release import run_play_release


def _format_confidence(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.3f}"
    return "n/a"


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
    raw = run_match_release(discogs_release_id, threshold=threshold)

    matched = bool(raw.get("matched"))
    spotify_album_id = raw.get("spotify_album_id")
    confidence = raw.get("confidence")
    source = str(raw.get("source") or "auto")

    candidate_summary = _candidate_summary(raw.get("best_candidate"))  # type: ignore[arg-type]
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

    return {
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


def run_override_action(discogs_release_id: int, spotify_album_id: str) -> dict[str, object]:
    raw = run_match_override(discogs_release_id, spotify_album_id)
    return {
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

    return {
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

