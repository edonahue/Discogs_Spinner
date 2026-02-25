"""GUI-friendly wrappers for spin and play-last-spin actions."""

from __future__ import annotations

from discogs_player.use_cases.play_release import run_play_release
from discogs_player.use_cases.spin_release import run_spin_release


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


def run_spin_action(
    *,
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = None,
    styles: list[str] | None = None,
    unmatched: bool = False,
    seed: int | None = None,
) -> dict[str, object]:
    chosen = run_spin_release(
        q=q,
        year=year,
        genres=genres or [],
        styles=styles or [],
        unmatched=unmatched,
        seed=seed,
    )

    release_id = _to_int(chosen.get("discogs_release_id"))
    artist = str(chosen.get("artist") or "Unknown Artist")
    title = str(chosen.get("title") or "Unknown Title")
    year_value = chosen.get("year")
    year_text = str(year_value) if year_value is not None else "Unknown Year"
    seed_text = str(seed) if seed is not None else "random"

    return {
        "ok": True,
        "action": "spin",
        "release": chosen,
        "discogs_release_id": release_id,
        "status_message": (
            f"Spin selected #{release_id}: {artist} - {title} ({year_text}) [seed={seed_text}]"
        ),
    }


def run_play_last_spin_action() -> dict[str, object]:
    raw = run_play_release(
        use_last_spin=True,
        auto_match=True,
        open_fallback=True,
    )

    playback_started = bool(raw.get("playback_started"))
    if playback_started:
        status_message = (
            f"Playing last spin on {raw.get('device_name') or raw.get('device_id')}: "
            f"{raw.get('spotify_album_id')}"
        )
    else:
        status_message = str(raw.get("message") or "Could not play last spin.")
        fallback_url = str(raw.get("fallback_open_url") or "").strip()
        if fallback_url:
            status_message = f"{status_message} Open URL: {fallback_url}"

    return {
        "ok": True,
        "action": "play_last_spin",
        "playback_started": playback_started,
        "status_message": status_message,
        "raw": raw,
    }
