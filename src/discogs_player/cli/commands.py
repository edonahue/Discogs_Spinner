"""Typer command definitions for dplayer."""

from __future__ import annotations

import json
import sys
import importlib
from typing import Protocol, cast

import typer
from rich.console import Console
from rich.table import Table

from discogs_player.capabilities import get_capabilities, get_player_backend
from discogs_player.integrations.player_backend import (
    PlayerApiError,
    PlayerAuthError,
    PlayerDependencyError,
    PlayerPlaybackError,
)
from discogs_player.services.matching import MatchingDependencyError
from discogs_player.services.discogs_client import (
    DiscogsApiError,
    DiscogsAuthError,
    DiscogsDependencyError,
)
from discogs_player.services.high_res_art import (
    HIGH_RES_ART_ENABLED_SETTING,
    HIGH_RES_ART_TARGET_SIZE_SETTING,
    get_high_res_art_preference,
    normalize_high_res_art_target_size,
)
from discogs_player.services.sync_manager import MissingDiscogsTokenError
from discogs_player.use_cases.device_management import (
    NoSpotifyDevicesError,
    run_auto_set_default_device,
    run_list_devices,
    run_set_default_device,
)
from discogs_player.use_cases.config_management import (
    run_config_set,
    run_config_show,
    run_config_unset,
)
from discogs_player.use_cases.ensure_mapping import (
    SAFE_AUTO_APPLY_THRESHOLD,
    run_match_audit,
    run_match_audit_review_action,
    run_match_audit_review_list,
    run_match_audit_retry_errors,
    run_match_override,
    run_match_release,
    run_match_unmatched,
)
from discogs_player.use_cases.collection_analytics import run_collection_analytics
from discogs_player.use_cases.bootstrap_import import run_bootstrap_mapping_import
from discogs_player.use_cases.export_collection import run_export_collection
from discogs_player.use_cases.import_collection import run_import_collection
from discogs_player.use_cases.list_releases import run_list_releases
from discogs_player.use_cases.list_wantlist import run_list_wantlist
from discogs_player.use_cases.play_release import (
    MissingLastSpinError,
    MissingSpotifyMappingError,
    NoPlayableDeviceError,
    run_play_release,
)
from discogs_player.use_cases.spin_release import NoReleasesFoundError, run_spin_release
from discogs_player.use_cases.status_report import get_status_report
from discogs_player.use_cases.setup_report import run_setup_report
from discogs_player.use_cases.high_res_art_refresh import run_refresh_high_res_art
from discogs_player.use_cases.sync_wantlist import run_sync_wantlist
from discogs_player.use_cases.value_missing import (
    run_market_value_missing,
    write_market_value_missing_csv,
)
from discogs_player.use_cases.value_examples import run_market_value_examples
from discogs_player.use_cases.value_refresh import run_refresh_market_values
from discogs_player.use_cases.value_show import run_market_value_show
from discogs_player.use_cases.value_snapshot import run_market_value_snapshot
from discogs_player.use_cases.value_status import run_market_value_status
from discogs_player.use_cases.value_trend import run_market_value_trend
from discogs_player.use_cases.tracklist_refresh import run_refresh_release_tracklists
from discogs_player.use_cases.tracklist_show import run_release_tracklist_show
from discogs_player.cli.stats_commands import refresh_release_stats


APT_INSTALL_CMD = (
    "sudo apt update && sudo apt install -y "
    "python3 python3-venv python3-pip python3-setuptools libsecret-1-0 "
    "build-essential python3-dev"
)

app = typer.Typer(help="Discogs Player CLI")
device_app = typer.Typer(help="Manage default playback device (Spotify addon)")
config_app = typer.Typer(help="Manage local app settings")
auth_app = typer.Typer(help="Authenticate with external services")
wantlist_app = typer.Typer(help="Sync and browse Discogs wantlist")
value_app = typer.Typer(help="Refresh and view collection market values")
tracks_app = typer.Typer(help="Refresh and view cached Discogs tracklists")
stats_app = typer.Typer(help="Refresh release statistics")
art_app = typer.Typer(help="Optional high-resolution album art controls")
bootstrap_app = typer.Typer(help="Bootstrap mapping import helpers")
review_app = typer.Typer(help="Review/apply/retry match audit results")
app.add_typer(device_app, name="device")
app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")
app.add_typer(wantlist_app, name="wantlist")
app.add_typer(value_app, name="value")
app.add_typer(tracks_app, name="tracks")
app.add_typer(stats_app, name="stats")
app.add_typer(art_app, name="art")
app.add_typer(bootstrap_app, name="bootstrap")
app.add_typer(review_app, name="review")
console = Console()

# Backwards-compatible aliases for tests and existing imports.
SpotifyDependencyError = PlayerDependencyError
SpotifyAuthError = PlayerAuthError
SpotifyApiError = PlayerApiError
SpotifyPlaybackError = PlayerPlaybackError


def run_spotify_oauth_login(**kwargs: object) -> dict[str, object]:
    backend = get_player_backend()
    return backend.run_oauth_login(**kwargs)


def run_spotify_auth_diagnostics(**kwargs: object) -> dict[str, object]:
    backend = get_player_backend()
    return backend.auth_diagnostics(**kwargs)


class _PyperclipModule(Protocol):
    def copy(self, text: str) -> None: ...


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _as_object_list(value: object) -> list[object]:
    if isinstance(value, list):
        return list(value)
    return []


def _as_dict_list(value: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in _as_object_list(value):
        if isinstance(item, dict):
            rows.append(cast(dict[str, object], item))
    return rows


def _to_int(value: object, *, default: int = 0) -> int:
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


def _to_float(value: object, *, default: float = 0.0) -> float:
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


def _print_missing_dependency(module_name: str | None) -> None:
    missing = module_name or "unknown"
    message = "\n".join(
        [
            f"Missing Python dependency: {missing}",
            "",
            "Install required system packages on Pop!_OS:",
            f"  {APT_INSTALL_CMD}",
            "",
            "Then install project dependencies:",
            "  python3 -m venv .venv",
            "  source .venv/bin/activate",
            "  pip install -r requirements.txt",
            "  pip install -e .",
        ]
    )
    print(message, file=sys.stderr)


def _emit_json(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
    sys.stdout.write("\n")


def _render_status_table(report: dict[str, object]) -> None:
    table = Table(title="discogs_player status")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("release_count_total", str(report["release_count_total"]))
    table.add_row("release_count_active", str(report["release_count_active"]))
    table.add_row("mapped_count", str(report["mapped_count"]))
    table.add_row("unmatched_count", str(report["unmatched_count"]))
    table.add_row("last_sync_time", str(report["last_sync_time"]))

    default_device = report["default_spotify_device"]
    if isinstance(default_device, dict):
        device_str = f"id={default_device.get('id')} name={default_device.get('name')}"
    else:
        device_str = str(default_device)
    table.add_row("default_spotify_device", device_str)
    capability = report.get("spotify_capability")
    if isinstance(capability, dict):
        table.add_row("spotify_capability", str(capability.get("action_label") or ""))
    else:
        table.add_row("spotify_capability", get_capabilities().spotify.action_label)

    table.add_row("last_spin_release_id", str(report["last_spin_release_id"]))
    table.add_row("market_value_last_updated", str(report["market_value_last_updated"]))
    table.add_row("wantlist_count", str(report["wantlist_count"]))
    table.add_row(
        "wantlist_mapped_count", str(report.get("wantlist_mapped_count") or 0)
    )
    table.add_row(
        "wantlist_unmatched_count", str(report.get("wantlist_unmatched_count") or 0)
    )

    console.print(table)


def _render_setup_table(report: dict[str, object]) -> None:
    table = Table(title="discogs_player setup")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("profile", str(report.get("profile") or ""))
    table.add_row("onboarding_stage", str(report.get("onboarding_stage") or ""))

    discogs = _as_dict(report.get("discogs"))
    table.add_row("discogs_configured", str(discogs.get("configured")))
    table.add_row("discogs_token_source", str(discogs.get("token_source") or ""))
    table.add_row("discogs_status", str(discogs.get("status_message") or ""))
    table.add_row("discogs_token_url", str(discogs.get("token_setup_url") or ""))

    collection = _as_dict(report.get("collection"))
    table.add_row(
        "release_count_active", str(collection.get("release_count_active") or 0)
    )
    table.add_row("last_sync_time", str(collection.get("last_sync_time")))

    spotify = _as_dict(report.get("spotify"))
    table.add_row("spotify_addon_available", str(spotify.get("addon_available")))
    table.add_row("spotify_configured", str(spotify.get("configured")))
    table.add_row("spotify_status", str(spotify.get("status_message") or ""))
    table.add_row("spotify_next_action", str(spotify.get("next_action") or ""))
    table.add_row("spotify_dashboard_url", str(spotify.get("dashboard_url") or ""))
    table.add_row("spotify_oauth_guide_url", str(spotify.get("oauth_guide_url") or ""))
    table.add_row("spotify_redirect_uri", str(spotify.get("redirect_uri") or ""))

    links = _as_dict(report.get("links"))
    if links:
        table.add_row("links_discogs_token_url", str(links.get("discogs_token_url") or ""))
        table.add_row(
            "links_spotify_dashboard_url",
            str(links.get("spotify_dashboard_url") or ""),
        )
        table.add_row(
            "links_spotify_oauth_guide_url",
            str(links.get("spotify_oauth_guide_url") or ""),
        )
    console.print(table)

    next_steps = _as_object_list(report.get("next_steps"))
    if not next_steps:
        return
    console.print("[bold]Next Steps[/bold]")
    for index, step in enumerate(next_steps, start=1):
        console.print(f"{index}. [cyan]{step}[/cyan]")


def _render_spotify_auth_doctor_table(report: dict[str, object]) -> None:
    table = Table(title="Spotify auth doctor")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("backend", str(report.get("backend") or ""))
    table.add_row("diagnosis", str(report.get("diagnosis") or ""))
    table.add_row("addon_available", str(report.get("addon_available")))
    table.add_row("configured", str(report.get("configured")))
    table.add_row("keyring_available", str(report.get("keyring_available")))
    table.add_row("expected_redirect_uri", str(report.get("expected_redirect_uri")))
    table.add_row("redirect_uri_setup_hint", str(report.get("redirect_uri_setup_hint") or ""))

    credentials = _as_dict(report.get("credentials"))
    table.add_row(
        "client_id_available", str(credentials.get("client_id_available", False))
    )
    table.add_row(
        "client_secret_available",
        str(credentials.get("client_secret_available", False)),
    )
    table.add_row(
        "refresh_token_available",
        str(credentials.get("refresh_token_available", False)),
    )

    access_token = _as_dict(report.get("access_token"))
    table.add_row("access_token_available", str(access_token.get("available", False)))
    table.add_row("access_token_fresh", str(access_token.get("fresh", False)))
    table.add_row(
        "access_token_expires_in_seconds",
        str(access_token.get("expires_in_seconds")),
    )

    table.add_row(
        "device_probe_attempted", str(report.get("device_probe_attempted", False))
    )
    table.add_row("device_probe_ok", str(report.get("device_probe_ok")))
    table.add_row("device_count", str(report.get("device_count")))
    table.add_row("device_probe_error", str(report.get("device_probe_error")))
    table.add_row("recommended_action", str(report.get("recommended_action") or ""))
    console.print(table)


def _render_analytics_summary_table(report: dict[str, object]) -> None:
    table = Table(title="collection analytics")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    active = _to_int(report.get("release_count_active"))
    mapped = _to_int(report.get("mapped_count"))
    unmatched = _to_int(report.get("unmatched_count"))
    mapping_rate = (mapped / active * 100.0) if active > 0 else 0.0

    table.add_row("release_count_active", str(active))
    table.add_row("mapped_count", str(mapped))
    table.add_row("unmatched_count", str(unmatched))
    table.add_row("mapping_rate_percent", f"{mapping_rate:.1f}")
    table.add_row("top_limit", str(report.get("top_limit")))
    console.print(table)


def _render_analytics_list_table(
    *,
    title: str,
    rows: list[dict[str, object]],
    key_field: str,
    key_header: str,
) -> None:
    table = Table(title=title)
    table.add_column(key_header, style="cyan")
    table.add_column("Count", style="white", justify="right")

    for item in rows:
        table.add_row(
            str(item.get(key_field) or ""),
            str(item.get("count") or 0),
        )
    console.print(table)


def _fmt_market_number(value: object) -> str:
    if not isinstance(value, (int, float)):
        return ""
    return f"{float(value):.2f}"


def _render_release_table(
    releases: list[dict[str, object]],
    *,
    include_value: bool = False,
) -> None:
    table = Table(title="discogs_player releases")
    table.add_column("Discogs ID", style="cyan", justify="right")
    table.add_column("Artist", style="white")
    table.add_column("Title", style="white")
    table.add_column("Year", style="magenta", justify="right")
    table.add_column("Mapped", style="green", justify="center")
    if include_value:
        table.add_column("Low", style="yellow", justify="right")
        table.add_column("Median", style="yellow", justify="right")
        table.add_column("High", style="yellow", justify="right")
        table.add_column("CCY", style="yellow")

    for item in releases:
        mapped = "yes" if item.get("spotify_album_id") else "no"
        year = item.get("year")
        row = [
            str(item.get("discogs_release_id")),
            str(item.get("artist") or ""),
            str(item.get("title") or ""),
            str(year) if year is not None else "",
            mapped,
        ]
        if include_value:
            row.extend(
                [
                    _fmt_market_number(item.get("market_lowest")),
                    _fmt_market_number(item.get("market_median")),
                    _fmt_market_number(item.get("market_highest")),
                    str(item.get("market_currency") or ""),
                ]
            )
        table.add_row(*row)

    console.print(table)


def _render_wantlist_table(
    entries: list[dict[str, object]],
    *,
    include_value: bool = False,
) -> None:
    table = Table(title="discogs_player wantlist")
    table.add_column("Discogs ID", style="cyan", justify="right")
    table.add_column("Artist", style="white")
    table.add_column("Title", style="white")
    table.add_column("Year", style="magenta", justify="right")
    table.add_column("Notes", style="yellow")
    if include_value:
        table.add_column("Low", style="yellow", justify="right")
        table.add_column("Median", style="yellow", justify="right")
        table.add_column("High", style="yellow", justify="right")
        table.add_column("CCY", style="yellow")

    for item in entries:
        year = item.get("year")
        row = [
            str(item.get("discogs_release_id")),
            str(item.get("artist") or ""),
            str(item.get("title") or ""),
            str(year) if year is not None else "",
            str(item.get("notes") or ""),
        ]
        if include_value:
            row.extend(
                [
                    _fmt_market_number(item.get("market_lowest")),
                    _fmt_market_number(item.get("market_median")),
                    _fmt_market_number(item.get("market_highest")),
                    str(item.get("market_currency") or ""),
                ]
            )
        table.add_row(*row)

    console.print(table)


def _render_market_value_status(summary: dict[str, object]) -> None:
    table = Table(title="collection market value")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("active_release_count", str(summary.get("active_release_count") or 0))
    table.add_row("priced_release_count", str(summary.get("priced_release_count") or 0))
    table.add_row(
        "unpriced_release_count", str(summary.get("unpriced_release_count") or 0)
    )
    table.add_row("total_lowest", f"{_to_float(summary.get('total_lowest')):.2f}")
    table.add_row("total_median", f"{_to_float(summary.get('total_median')):.2f}")
    table.add_row("total_highest", f"{_to_float(summary.get('total_highest')):.2f}")
    table.add_row(
        "market_value_last_updated", str(summary.get("market_value_last_updated"))
    )
    console.print(table)

    currencies = summary.get("currency_counts")
    if not isinstance(currencies, list) or not currencies:
        return

    currency_table = Table(title="market value currencies")
    currency_table.add_column("Currency", style="cyan")
    currency_table.add_column("Count", style="white", justify="right")
    for item in currencies:
        if not isinstance(item, dict):
            continue
        currency_table.add_row(
            str(item.get("currency") or ""),
            str(item.get("count") or 0),
        )
    console.print(currency_table)


def _render_market_value_examples(report: dict[str, object]) -> None:
    rendered_any = False
    for key, title in (
        ("high_priced", "highest-priced examples (median)"),
        ("low_priced", "lowest-priced examples (median)"),
    ):
        rows_raw = report.get(key)
        if not isinstance(rows_raw, list) or not rows_raw:
            continue

        table = Table(title=title)
        table.add_column("Discogs ID", style="cyan", justify="right")
        table.add_column("Artist", style="white")
        table.add_column("Album", style="white")
        table.add_column("Median", style="yellow", justify="right")
        table.add_column("Low", style="yellow", justify="right")
        table.add_column("High", style="yellow", justify="right")
        table.add_column("CCY", style="yellow")

        for item in rows_raw:
            if not isinstance(item, dict):
                continue
            table.add_row(
                str(item.get("discogs_release_id") or ""),
                str(item.get("artist") or ""),
                str(item.get("title") or ""),
                _fmt_market_number(item.get("market_median")),
                _fmt_market_number(item.get("market_lowest")),
                _fmt_market_number(item.get("market_highest")),
                str(item.get("market_currency") or ""),
            )

        console.print(table)
        rendered_any = True

    if not rendered_any:
        console.print("No priced releases with median values found.")


def _render_market_value_snapshot(snapshot: dict[str, object]) -> None:
    table = Table(title="market value snapshot")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("snapshot_id", str(snapshot.get("snapshot_id")))
    table.add_row("captured_at", str(snapshot.get("captured_at")))
    table.add_row(
        "active_release_count", str(snapshot.get("active_release_count") or 0)
    )
    table.add_row(
        "priced_release_count", str(snapshot.get("priced_release_count") or 0)
    )
    table.add_row(
        "unpriced_release_count", str(snapshot.get("unpriced_release_count") or 0)
    )
    table.add_row("total_lowest", _fmt_market_number(snapshot.get("total_lowest")))
    table.add_row("total_median", _fmt_market_number(snapshot.get("total_median")))
    table.add_row("total_highest", _fmt_market_number(snapshot.get("total_highest")))
    table.add_row(
        "market_value_last_updated", str(snapshot.get("market_value_last_updated"))
    )
    console.print(table)


def _render_market_value_trend(report: dict[str, object]) -> None:
    summary_table = Table(title="market value trend")
    summary_table.add_column("Field", style="cyan")
    summary_table.add_column("Value", style="white")
    summary_table.add_row("snapshot_count", str(report.get("snapshot_count") or 0))
    summary_table.add_row("window_start", str(report.get("window_start")))
    summary_table.add_row("window_end", str(report.get("window_end")))
    summary_table.add_row(
        "window_delta_total_median",
        _fmt_market_number(report.get("window_delta_total_median")),
    )
    delta_pct = report.get("window_delta_total_median_percent")
    summary_table.add_row(
        "window_delta_total_median_percent",
        f"{float(delta_pct):.2f}" if isinstance(delta_pct, (int, float)) else "",
    )
    console.print(summary_table)

    points = report.get("points")
    if not isinstance(points, list) or not points:
        return

    points_table = Table(title="snapshot points")
    points_table.add_column("Snapshot", style="cyan", justify="right")
    points_table.add_column("Captured At", style="white")
    points_table.add_column("Active", style="white", justify="right")
    points_table.add_column("Priced", style="white", justify="right")
    points_table.add_column("Median Total", style="yellow", justify="right")
    points_table.add_column("Delta Median", style="yellow", justify="right")
    points_table.add_column("Delta %", style="yellow", justify="right")
    for item in points:
        delta = item.get("delta_total_median")
        delta_pct_item = item.get("delta_total_median_percent")
        points_table.add_row(
            str(item.get("id") or ""),
            str(item.get("captured_at") or ""),
            str(item.get("active_release_count") or 0),
            str(item.get("priced_release_count") or 0),
            _fmt_market_number(item.get("total_median")),
            _fmt_market_number(delta),
            f"{float(delta_pct_item):.2f}"
            if isinstance(delta_pct_item, (int, float))
            else "",
        )
    console.print(points_table)


def _render_market_value_show(item: dict[str, object]) -> None:
    table = Table(title="release market value")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("discogs_release_id", str(item.get("discogs_release_id")))
    table.add_row("artist", str(item.get("artist") or ""))
    table.add_row("title", str(item.get("title") or ""))
    table.add_row("year", str(item.get("year") or ""))
    table.add_row("is_active", str(item.get("is_active")))
    table.add_row("spotify_album_id", str(item.get("spotify_album_id") or ""))
    table.add_row("market_lowest", _fmt_market_number(item.get("market_lowest")))
    table.add_row("market_median", _fmt_market_number(item.get("market_median")))
    table.add_row("market_highest", _fmt_market_number(item.get("market_highest")))
    table.add_row("market_currency", str(item.get("market_currency") or ""))
    table.add_row(
        "market_last_updated_at", str(item.get("market_last_updated_at") or "")
    )
    table.add_row("market_spread", _fmt_market_number(item.get("market_spread")))
    table.add_row("market_midpoint", _fmt_market_number(item.get("market_midpoint")))
    table.add_row(
        "market_price_point_count", str(item.get("market_price_point_count") or 0)
    )
    table.add_row("has_market_value", str(item.get("has_market_value")))
    console.print(table)


def _render_release_tracklist_show(item: dict[str, object]) -> None:
    summary = Table(title="release tracklist")
    summary.add_column("Field", style="cyan")
    summary.add_column("Value", style="white")
    summary.add_row("discogs_release_id", str(item.get("discogs_release_id")))
    summary.add_row("artist", str(item.get("artist") or ""))
    summary.add_row("title", str(item.get("title") or ""))
    summary.add_row("year", str(item.get("year") or ""))
    summary.add_row("track_count", str(item.get("track_count") or 0))
    summary.add_row("audio_track_count", str(item.get("audio_track_count") or 0))
    summary.add_row("has_cached_tracklist", str(item.get("has_cached_tracklist")))
    summary.add_row(
        "tracklist_last_refreshed_at",
        str(item.get("tracklist_last_refreshed_at") or ""),
    )
    console.print(summary)

    tracks_raw = item.get("tracks")
    tracks = tracks_raw if isinstance(tracks_raw, list) else []
    if not tracks:
        return

    tracks_table = Table(title="track rows")
    tracks_table.add_column("Seq", style="cyan", justify="right")
    tracks_table.add_column("Pos", style="magenta")
    tracks_table.add_column("Title", style="white")
    tracks_table.add_column("Duration", style="yellow", justify="right")
    tracks_table.add_column("Type", style="yellow")
    tracks_table.add_column("Audio", style="green", justify="center")
    for track in tracks:
        if not isinstance(track, dict):
            continue
        tracks_table.add_row(
            str(track.get("seq") or ""),
            str(track.get("position") or ""),
            str(track.get("title") or ""),
            str(track.get("duration") or ""),
            str(track.get("type") or ""),
            "yes" if track.get("is_audio_track") else "no",
        )
    console.print(tracks_table)


def _render_market_missing_table(
    releases: list[dict[str, object]],
    *,
    include_value: bool = False,
) -> None:
    table = Table(title="releases needing market refresh")
    table.add_column("Discogs ID", style="cyan", justify="right")
    table.add_column("Artist", style="white")
    table.add_column("Title", style="white")
    table.add_column("Year", style="magenta", justify="right")
    table.add_column("Mapped", style="green", justify="center")
    table.add_column("Need", style="yellow")
    if include_value:
        table.add_column("Low", style="yellow", justify="right")
        table.add_column("Median", style="yellow", justify="right")
        table.add_column("High", style="yellow", justify="right")
        table.add_column("CCY", style="yellow")
        table.add_column("Updated", style="yellow")

    for item in releases:
        mapped = "yes" if item.get("spotify_album_id") else "no"
        year = item.get("year")
        row = [
            str(item.get("discogs_release_id")),
            str(item.get("artist") or ""),
            str(item.get("title") or ""),
            str(year) if year is not None else "",
            mapped,
            str(item.get("market_need_reason") or ""),
        ]
        if include_value:
            row.extend(
                [
                    _fmt_market_number(item.get("market_lowest")),
                    _fmt_market_number(item.get("market_median")),
                    _fmt_market_number(item.get("market_highest")),
                    str(item.get("market_currency") or ""),
                    str(item.get("market_last_updated_at") or ""),
                ]
            )
        table.add_row(*row)

    console.print(table)


def _render_devices_table(devices: list[dict[str, object]]) -> None:
    table = Table(title="spotify devices")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Type", style="white")
    table.add_column("Active", justify="center")
    table.add_column("Restricted", justify="center")
    table.add_column("Default", justify="center")

    for item in devices:
        table.add_row(
            str(item.get("id") or ""),
            str(item.get("name") or ""),
            str(item.get("type") or ""),
            "yes" if item.get("is_active") else "no",
            "yes" if item.get("is_restricted") else "no",
            "yes" if item.get("is_default") else "no",
        )

    console.print(table)


def _render_settings_table(settings: dict[str, str]) -> None:
    table = Table(title="app settings")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    for key, value in settings.items():
        table.add_row(key, value)

    console.print(table)


def _render_art_status_table(report: dict[str, object]) -> None:
    table = Table(title="high-res art")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("enabled", str(bool(report.get("enabled"))))
    table.add_row("target_size", str(report.get("target_size")))
    table.add_row("enabled_setting_key", str(report.get("enabled_setting_key") or ""))
    table.add_row("target_size_setting_key", str(report.get("target_size_setting_key") or ""))
    console.print(table)


def _render_art_refresh_table(report: dict[str, object]) -> None:
    table = Table(title="high-res art refresh")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("scope", str(report.get("scope") or ""))
    table.add_row("limit", str(report.get("limit")))
    table.add_row("target_size", str(report.get("target_size")))
    table.add_row("workers", str(report.get("workers")))
    table.add_row("dry_run", str(bool(report.get("dry_run"))))
    table.add_row("scanned_count", str(report.get("scanned_count") or 0))
    table.add_row("eligible_count", str(report.get("eligible_count") or 0))
    table.add_row(
        "unique_upgraded_url_count",
        str(report.get("unique_upgraded_url_count") or 0),
    )
    table.add_row(
        "unique_candidate_url_count",
        str(report.get("unique_candidate_url_count") or 0),
    )
    table.add_row(
        "fallback_original_url_count",
        str(report.get("fallback_original_url_count") or 0),
    )
    table.add_row("warmed_url_count", str(report.get("warmed_url_count") or 0))
    table.add_row("failed_url_count", str(report.get("failed_url_count") or 0))
    table.add_row("warmed_release_count", str(report.get("warmed_release_count") or 0))
    table.add_row(
        "collection_scanned_count",
        str(report.get("collection_scanned_count") or 0),
    )
    table.add_row("wantlist_scanned_count", str(report.get("wantlist_scanned_count") or 0))
    table.add_row("enabled", str(bool(report.get("enabled"))))
    console.print(table)


def _render_match_results_table(items: list[dict[str, object]], *, title: str) -> None:
    table = Table(title=title)
    table.add_column("Discogs ID", style="cyan", justify="right")
    table.add_column("Artist", style="white")
    table.add_column("Title", style="white")
    table.add_column("Matched", justify="center")
    table.add_column("Outcome", style="magenta")
    table.add_column("Spotify Album", style="green")
    table.add_column("Confidence", justify="right")
    table.add_column("Source", style="magenta")

    for item in items:
        confidence = item.get("confidence")
        confidence_str = (
            f"{float(confidence):.3f}" if isinstance(confidence, (int, float)) else ""
        )
        status = str(item.get("status") or "").strip()
        if not status:
            status = "matched" if item.get("matched") else "candidate"
        table.add_row(
            str(item.get("discogs_release_id") or ""),
            str(item.get("artist") or ""),
            str(item.get("title") or ""),
            "yes" if item.get("matched") else "no",
            status,
            str(item.get("spotify_album_id") or ""),
            confidence_str,
            str(item.get("source") or ""),
        )

    console.print(table)


def _render_match_audit_summary(report: dict[str, object]) -> None:
    table = Table(title="match audit summary")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("population_unmatched", str(report.get("population_unmatched") or 0))
    table.add_row("run_processed_count", str(report.get("run_processed_count") or 0))
    table.add_row("run_auto_applied_count", str(report.get("run_auto_applied_count") or 0))
    table.add_row(
        "run_safe_auto_candidate_count",
        str(report.get("run_safe_auto_candidate_count") or 0),
    )
    table.add_row(
        "run_review_queue_count",
        str(report.get("run_review_queue_count") or 0),
    )
    table.add_row("run_error_count", str(report.get("run_error_count") or 0))
    table.add_row("review_threshold", str(report.get("review_threshold")))
    table.add_row("auto_apply_threshold", str(report.get("auto_apply_threshold")))
    table.add_row("apply_safe_matches", str(bool(report.get("apply_safe_matches"))))
    table.add_row("resume", str(bool(report.get("resume"))))
    table.add_row("resumed_entry_count", str(report.get("resumed_entry_count") or 0))
    table.add_row("report_path", str(report.get("report_path") or ""))
    console.print(table)


def _parse_release_id(raw: str) -> int:
    value = raw.strip()
    if not value:
        raise ValueError("Release id cannot be empty.")
    if not value.isdigit():
        raise ValueError("Release id must be an integer.")
    return int(value)


@app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show current local sync and mapping status."""
    report = get_status_report()
    if json_output:
        _emit_json(report)
        return
    _render_status_table(report)


@app.command("setup")
def setup(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
    """Show first-time setup readiness and recommended next steps."""
    report = run_setup_report()
    if json_output:
        _emit_json(report)
        return
    _render_setup_table(report)


@app.command("analytics")
def analytics(
    limit: int = typer.Option(
        10, "--limit", min=1, help="Max rows for top genre/style/artist lists"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show collection analytics from local data (year/genre/style/timeline)."""
    try:
        report = run_collection_analytics(limit=limit)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if json_output:
        _emit_json(report)
        return

    _render_analytics_summary_table(report)
    _render_analytics_list_table(
        title="release years",
        rows=_as_dict_list(report.get("by_release_year")),
        key_field="year",
        key_header="Year",
    )
    _render_analytics_list_table(
        title="acquisition timeline",
        rows=_as_dict_list(report.get("acquisition_timeline")),
        key_field="year",
        key_header="Year",
    )
    _render_analytics_list_table(
        title="top genres",
        rows=_as_dict_list(report.get("top_genres")),
        key_field="genre",
        key_header="Genre",
    )
    _render_analytics_list_table(
        title="top styles",
        rows=_as_dict_list(report.get("top_styles")),
        key_field="style",
        key_header="Style",
    )
    _render_analytics_list_table(
        title="top artists",
        rows=_as_dict_list(report.get("top_artists")),
        key_field="artist",
        key_header="Artist",
    )


@app.command("sync")
def sync(
    full: bool = typer.Option(False, "--full", help="Force a full sync pass"),
    no_images: bool = typer.Option(
        False, "--no-images", help="Skip image work (no-op for MVP)"
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Show page-by-page progress"),
) -> None:
    """Sync Discogs collection into local database."""
    _ = full
    _ = no_images

    try:
        from discogs_player.services.discogs_client import (
            DiscogsApiError,
            DiscogsAuthError,
            DiscogsDependencyError,
        )
        from discogs_player.services.sync_manager import MissingDiscogsTokenError
        from discogs_player.use_cases.sync_collection import run_sync_collection
    except ModuleNotFoundError as exc:
        _print_missing_dependency(exc.name)
        raise typer.Exit(code=1) from exc

    def progress_callback(
        page: int, pages: int, page_count: int, total_count: int
    ) -> None:
        if verbose:
            console.print(
                f"Fetched page {page}/{pages}: {page_count} releases (total={total_count})"
            )

    try:
        if verbose:
            summary = run_sync_collection(
                progress_callback=progress_callback,
                allow_empty_deactivate=full,
            )
        else:
            with console.status("Syncing Discogs collection..."):
                summary = run_sync_collection(
                    progress_callback=None,
                    allow_empty_deactivate=full,
                )
    except MissingDiscogsTokenError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except DiscogsAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    table = Table(title="Sync complete")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("fetched_count", str(summary["fetched_count"]))
    table.add_row("upserted_count", str(summary["upserted_count"]))
    table.add_row("deactivated_count", str(summary["deactivated_count"]))
    table.add_row("last_sync_time", str(summary["last_sync_time"]))
    table.add_row("skipped_empty_deactivate", str(summary["skipped_empty_deactivate"]))
    console.print(table)

    for warning in _as_object_list(summary.get("warnings")):
        console.print(f"[yellow]warning:[/yellow] {warning}")


@value_app.command("status")
def value_status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show aggregated market value totals and coverage."""
    summary = run_market_value_status()
    if json_output:
        _emit_json(summary)
        return
    _render_market_value_status(summary)
    _render_market_value_examples(run_market_value_examples(limit=2))


@value_app.command("examples")
def value_examples(
    limit: int = typer.Option(
        2, "--limit", min=1, help="Examples to show per high/low group"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show high/low priced examples with artist and album names."""
    try:
        report = run_market_value_examples(limit=limit)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if json_output:
        _emit_json(report)
        return
    _render_market_value_examples(report)


@value_app.command("snapshot")
def value_snapshot(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Capture and store a point-in-time market value snapshot."""
    snapshot = run_market_value_snapshot()
    if json_output:
        _emit_json(snapshot)
        return
    _render_market_value_snapshot(snapshot)


@value_app.command("trend")
def value_trend(
    limit: int = typer.Option(30, "--limit", min=1, help="Max snapshots to include"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show trend deltas from stored market value snapshots."""
    try:
        report = run_market_value_trend(limit=limit)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if json_output:
        _emit_json(report)
        return

    _render_market_value_trend(report)


@value_app.command("show")
def value_show(
    release_id: int = typer.Argument(..., min=1, help="Discogs release id"),
    refresh: bool = typer.Option(
        False, "--refresh", help="Fetch fresh market value from Discogs first."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show cached market value details for one release id."""
    try:
        if refresh and not json_output:
            with console.status("Refreshing market value..."):
                item = run_market_value_show(release_id, refresh=True)
        else:
            item = run_market_value_show(release_id, refresh=refresh)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except MissingDiscogsTokenError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except DiscogsAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(item)
        return

    _render_market_value_show(item)


@value_app.command("missing")
def value_missing(
    limit: int = typer.Option(
        25, "--limit", min=1, help="Max missing releases to return"
    ),
    stale_days: int | None = typer.Option(
        None,
        "--stale-days",
        min=0,
        help="Also include stale market entries older than N days.",
    ),
    with_value: bool = typer.Option(
        False,
        "--with-value",
        help="Include cached market fields for each release row.",
    ),
    csv_output: str | None = typer.Option(
        None, "--csv", help="Write results to CSV output path."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """List active releases missing values (and optionally stale for refresh)."""
    try:
        releases = run_market_value_missing(
            limit=limit,
            stale_days=stale_days,
            with_value=with_value or bool(csv_output),
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    csv_result: dict[str, object] | None = None
    if csv_output:
        try:
            csv_result = write_market_value_missing_csv(
                releases=releases,
                output_path=csv_output,
            )
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2) from exc
        except OSError as exc:
            console.print(f"[red]Failed to write CSV export: {exc}[/red]")
            raise typer.Exit(code=4) from exc

    if json_output:
        if csv_result is not None:
            _emit_json(
                {
                    "releases": releases,
                    "csv_output_path": csv_result["output_path"],
                    "csv_row_count": csv_result["row_count"],
                }
            )
        else:
            _emit_json(releases)
        return

    _render_market_missing_table(releases, include_value=with_value)
    if csv_result is not None:
        console.print(
            f"CSV export written: [cyan]{csv_result['output_path']}[/cyan] "
            f"(rows={csv_result['row_count']})"
        )


@value_app.command("refresh")
def value_refresh(
    limit: int = typer.Option(
        100, "--limit", min=1, help="Max releases to refresh per run"
    ),
    stale_days: int = typer.Option(
        30, "--stale-days", min=0, help="Refresh only entries older than N days"
    ),
    from_missing: bool = typer.Option(
        False,
        "--from-missing",
        help="Use the `value missing` backlog selection (missing + unpriced + stale).",
    ),
    release_id: list[int] | None = typer.Option(
        None,
        "--release-id",
        help="Refresh specific active release id(s); repeatable.",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Show detailed refresh warnings"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Refresh cached market value stats for active releases."""
    try:
        from discogs_player.services.discogs_client import (
            DiscogsApiError,
            DiscogsAuthError,
            DiscogsDependencyError,
        )
        from discogs_player.services.sync_manager import MissingDiscogsTokenError
    except ModuleNotFoundError as exc:
        _print_missing_dependency(exc.name)
        raise typer.Exit(code=1) from exc

    try:
        if verbose:
            summary = run_refresh_market_values(
                limit=limit,
                stale_days=stale_days,
                release_ids=release_id or None,
                from_missing=from_missing,
            )
        else:
            with console.status("Refreshing market values..."):
                summary = run_refresh_market_values(
                    limit=limit,
                    stale_days=stale_days,
                    release_ids=release_id or None,
                    from_missing=from_missing,
                )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except MissingDiscogsTokenError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except DiscogsAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(summary)
        return

    table = Table(title="Market value refresh complete")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("limit", str(summary.get("limit")))
    table.add_row("stale_days", str(summary.get("stale_days")))
    table.add_row("from_missing", str(summary.get("from_missing")))
    table.add_row(
        "release_ids_requested",
        str(len(_as_object_list(summary.get("release_ids_requested")))),
    )
    table.add_row("candidate_count", str(summary.get("candidate_count")))
    table.add_row("refreshed_count", str(summary.get("refreshed_count")))
    table.add_row("priced_count", str(summary.get("priced_count")))
    table.add_row("unpriced_count", str(summary.get("unpriced_count")))
    table.add_row("error_count", str(summary.get("error_count")))
    table.add_row("last_refresh_time", str(summary.get("last_refresh_time")))
    console.print(table)

    for warning in _as_object_list(summary.get("warnings")):
        console.print(f"[yellow]warning:[/yellow] {warning}")
    skipped_release_ids = _as_object_list(summary.get("skipped_release_ids"))
    if skipped_release_ids:
        console.print(
            "[yellow]skipped_release_ids:[/yellow] "
            f"{', '.join(str(x) for x in skipped_release_ids)}"
        )


@tracks_app.command("show")
def tracks_show(
    release_id: int = typer.Argument(..., min=1, help="Discogs release id"),
    refresh: bool = typer.Option(
        False, "--refresh", help="Fetch fresh tracklist from Discogs first."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show cached tracklist details for one release id."""
    try:
        if refresh and not json_output:
            with console.status("Refreshing tracklist..."):
                item = run_release_tracklist_show(release_id, refresh=True)
        else:
            item = run_release_tracklist_show(release_id, refresh=refresh)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except MissingDiscogsTokenError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except DiscogsAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(item)
        return
    _render_release_tracklist_show(item)


@tracks_app.command("refresh")
def tracks_refresh(
    limit: int = typer.Option(
        100, "--limit", min=1, help="Max releases to refresh per run"
    ),
    stale_days: int = typer.Option(
        30, "--stale-days", min=0, help="Refresh tracklists older than N days"
    ),
    from_missing: bool = typer.Option(
        False,
        "--from-missing",
        help="Only refresh active releases without cached tracklist rows.",
    ),
    release_id: list[int] | None = typer.Option(
        None,
        "--release-id",
        help="Refresh specific active release id(s); repeatable.",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Show detailed refresh warnings"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Refresh cached release tracklists for active releases."""
    try:
        if verbose:
            summary = run_refresh_release_tracklists(
                limit=limit,
                stale_days=stale_days,
                release_ids=release_id or None,
                from_missing=from_missing,
            )
        else:
            with console.status("Refreshing cached tracklists..."):
                summary = run_refresh_release_tracklists(
                    limit=limit,
                    stale_days=stale_days,
                    release_ids=release_id or None,
                    from_missing=from_missing,
                )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except MissingDiscogsTokenError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except DiscogsAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(summary)
        return

    table = Table(title="Tracklist refresh complete")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("limit", str(summary.get("limit")))
    table.add_row("stale_days", str(summary.get("stale_days")))
    table.add_row("from_missing", str(summary.get("from_missing")))
    table.add_row(
        "release_ids_requested",
        str(len(_as_object_list(summary.get("release_ids_requested")))),
    )
    table.add_row("candidate_count", str(summary.get("candidate_count")))
    table.add_row("refreshed_count", str(summary.get("refreshed_count")))
    table.add_row("with_audio_track_count", str(summary.get("with_audio_track_count")))
    table.add_row(
        "without_audio_track_count", str(summary.get("without_audio_track_count"))
    )
    table.add_row("error_count", str(summary.get("error_count")))
    table.add_row("last_refresh_time", str(summary.get("last_refresh_time")))
    console.print(table)

    for warning in _as_object_list(summary.get("warnings")):
        console.print(f"[yellow]warning:[/yellow] {warning}")
    skipped_release_ids = _as_object_list(summary.get("skipped_release_ids"))
    if skipped_release_ids:
        console.print(
            "[yellow]skipped_release_ids:[/yellow] "
            f"{', '.join(str(x) for x in skipped_release_ids)}"
        )


@wantlist_app.command("sync")
def wantlist_sync(
    full: bool = typer.Option(False, "--full", help="Force a full sync pass"),
    verbose: bool = typer.Option(False, "--verbose", help="Show page-by-page progress"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Sync Discogs wantlist into local database."""
    try:
        from discogs_player.services.discogs_client import (
            DiscogsApiError,
            DiscogsAuthError,
            DiscogsDependencyError,
        )
        from discogs_player.services.sync_manager import MissingDiscogsTokenError
    except ModuleNotFoundError as exc:
        _print_missing_dependency(exc.name)
        raise typer.Exit(code=1) from exc

    def progress_callback(
        page: int, pages: int, page_count: int, total_count: int
    ) -> None:
        if verbose:
            console.print(
                f"Fetched wantlist page {page}/{pages}: {page_count} releases (total={total_count})"
            )

    try:
        if verbose:
            summary = run_sync_wantlist(
                progress_callback=progress_callback,
                allow_empty_deactivate=full,
            )
        else:
            with console.status("Syncing Discogs wantlist..."):
                summary = run_sync_wantlist(
                    progress_callback=None,
                    allow_empty_deactivate=full,
                )
    except MissingDiscogsTokenError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except DiscogsAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except DiscogsApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(summary)
        return

    table = Table(title="Wantlist sync complete")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("fetched_count", str(summary["fetched_count"]))
    table.add_row("upserted_count", str(summary["upserted_count"]))
    table.add_row("deactivated_count", str(summary["deactivated_count"]))
    table.add_row("last_sync_time", str(summary["last_sync_time"]))
    table.add_row("skipped_empty_deactivate", str(summary["skipped_empty_deactivate"]))
    console.print(table)

    for warning in _as_object_list(summary.get("warnings")):
        console.print(f"[yellow]warning:[/yellow] {warning}")


@wantlist_app.command("list")
def wantlist_list(
    limit: int = typer.Option(
        25, "--limit", min=1, help="Max wantlist releases to return"
    ),
    q: str | None = typer.Option(None, "--q", help="Search artist/title substring"),
    year: str | None = typer.Option(
        None, "--year", help="Single year or range like 1990:1999"
    ),
    genre: list[str] | None = typer.Option(
        None, "--genre", help="Filter by genre, repeatable"
    ),
    style: list[str] | None = typer.Option(
        None, "--style", help="Filter by style, repeatable"
    ),
    with_value: bool = typer.Option(
        False,
        "--with-value",
        help="Include cached market value fields (lowest/median/highest/currency).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """List wantlist releases from local database."""
    try:
        entries = run_list_wantlist(
            limit=limit,
            q=q,
            year=year,
            genres=genre or [],
            styles=style or [],
            with_value=with_value,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if json_output:
        _emit_json(entries)
        return

    _render_wantlist_table(entries, include_value=with_value)


@wantlist_app.command("spin")
def wantlist_spin(
    q: str | None = typer.Option(None, "--query", "-q", help="Text query for artist or title"),
    year: str | None = typer.Option(
        None, "--year", help="Filter by year or year range (YYYY or YYYY:YYYY)"
    ),
    genre: list[str] | None = typer.Option(
        None, "--genre", help="Filter by genre (can specify multiple)"
    ),
    style: list[str] | None = typer.Option(
        None, "--style", help="Filter by style (can specify multiple)"
    ),
    unmatched: bool = typer.Option(False, "--unmatched", help="Only spin from releases without a Spotify match"),
    seed: int | None = typer.Option(None, "--seed", help="Random seed"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Spin for a random wantlist item."""
    from discogs_player.use_cases.spin_wantlist import (
        NoWantlistItemsFoundError,
        run_spin_wantlist,
    )
    try:
        result = run_spin_wantlist(
            q=q,
            year=year,
            genres=genre or [],
            styles=style or [],
            unmatched=unmatched,
            seed=seed,
        )
        if json_output:
            _emit_json(result)
        else:
            artist = str(result.get("artist") or "Unknown Artist")
            title = str(result.get("title") or "Unknown Title")
            year_val = result.get("year")
            year_text = str(year_val) if year_val is not None else "Unknown Year"
            console.print(f"Selected: {artist} - {title} ({year_text})")
    except NoWantlistItemsFoundError as exc:
        if json_output:
            _emit_json({"error": str(exc)})
        else:
            console.print(f"[yellow]{exc}[/yellow]")
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc


@app.command("list")
def list_releases(
    limit: int = typer.Option(25, "--limit", min=1, help="Max releases to return"),
    q: str | None = typer.Option(None, "--q", help="Search artist/title substring"),
    year: str | None = typer.Option(
        None, "--year", help="Single year or range like 1990:1999"
    ),
    genre: list[str] | None = typer.Option(
        None, "--genre", help="Filter by genre, repeatable"
    ),
    style: list[str] | None = typer.Option(
        None, "--style", help="Filter by style, repeatable"
    ),
    unmatched: bool = typer.Option(
        False, "--unmatched", help="Only show unmapped releases"
    ),
    with_value: bool = typer.Option(
        False,
        "--with-value",
        help="Include cached market value fields (lowest/median/highest/currency).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """List releases from local database."""
    try:
        releases = run_list_releases(
            limit=limit,
            q=q,
            year=year,
            genres=genre or [],
            styles=style or [],
            unmatched=unmatched,
            with_value=with_value,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if json_output:
        _emit_json(releases)
        return

    _render_release_table(releases, include_value=with_value)


@app.command("export")
def export_collection(
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    export_format: str = typer.Option(
        "json",
        "--format",
        help="Export format: json or csv",
    ),
    active_only: bool = typer.Option(
        False, "--active-only", help="Only export active releases"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Export local collection and settings snapshot for backup portability."""
    try:
        result = run_export_collection(
            output_path=output,
            export_format=export_format,
            include_inactive=not active_only,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except OSError as exc:
        console.print(f"[red]Failed to write export: {exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(result)
        return

    table = Table(title="Export complete")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("output_path", str(result["output_path"]))
    table.add_row("format", str(result["export_format"]))
    table.add_row("release_count", str(result["release_count"]))
    table.add_row("include_inactive", str(result["include_inactive"]))
    console.print(table)


@stats_app.command("refresh")
def stats_refresh(
    limit: int = typer.Option(20, "--limit", min=1, help="Max items to refresh"),
    force: bool = typer.Option(False, "--force", help="Force refresh even if recent"),
    wantlist: bool = typer.Option(
        False, "--wantlist", help="Refresh wantlist items instead of collection"
    ),
) -> None:
    """Refresh release statistics (community ratings, have/want, market counts)."""
    refresh_release_stats(limit=limit, force=force, wantlist=wantlist)


@art_app.command("status")
def art_status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show current high-resolution art preference."""
    enabled, target_size = get_high_res_art_preference()
    report = {
        "enabled": enabled,
        "target_size": target_size,
        "enabled_setting_key": HIGH_RES_ART_ENABLED_SETTING,
        "target_size_setting_key": HIGH_RES_ART_TARGET_SIZE_SETTING,
    }
    if json_output:
        _emit_json(report)
        return
    _render_art_status_table(report)


@art_app.command("refresh")
def art_refresh(
    scope: str = typer.Option(
        "collection",
        "--scope",
        help="Population to warm: collection, wantlist, or both",
    ),
    limit: int | None = typer.Option(
        None, "--limit", min=1, help="Max releases to scan in selected scope"
    ),
    target_size: int | None = typer.Option(
        None,
        "--target-size",
        min=600,
        max=2400,
        help="Requested upgraded Discogs image size (square px)",
    ),
    workers: int = typer.Option(
        8, "--workers", min=1, max=16, help="Concurrent cache warm workers"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Analyze candidates without fetching images"
    ),
    enable: bool = typer.Option(
        False, "--enable", help="Persist high-res art opt-in before refresh"
    ),
    disable: bool = typer.Option(
        False, "--disable", help="Persist high-res art opt-out before refresh"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Pre-warm cache using upgraded Discogs cover URLs for high-resolution art."""
    if enable and disable:
        console.print("[red]Do not combine --enable and --disable.[/red]")
        raise typer.Exit(code=2)

    try:
        if enable:
            run_config_set(HIGH_RES_ART_ENABLED_SETTING, "1")
        if disable:
            run_config_set(HIGH_RES_ART_ENABLED_SETTING, "0")
        if target_size is not None:
            normalized_target = normalize_high_res_art_target_size(target_size)
            run_config_set(HIGH_RES_ART_TARGET_SIZE_SETTING, str(normalized_target))

        summary = run_refresh_high_res_art(
            scope=scope,
            limit=limit,
            target_size=target_size,
            workers=workers,
            dry_run=dry_run,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    enabled_pref, target_pref = get_high_res_art_preference()
    summary["enabled"] = enabled_pref
    summary["configured_target_size"] = target_pref

    if json_output:
        _emit_json(summary)
        return

    _render_art_refresh_table(summary)


@app.command("import")
def import_collection(
    input_path: str = typer.Option(
        ..., "--input", "-i", help="Input JSON snapshot path"
    ),
    conflict_mode: str = typer.Option(
        "merge",
        "--conflict-mode",
        help="Conflict mode: merge or replace",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate and preview import without writing"
    ),
    include_settings: bool = typer.Option(
        True,
        "--settings/--no-settings",
        help="Import app settings from snapshot",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Import local collection/settings snapshot from JSON export."""
    try:
        result = run_import_collection(
            input_path=input_path,
            conflict_mode=conflict_mode,
            dry_run=dry_run,
            include_settings=include_settings,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except OSError as exc:
        console.print(f"[red]Failed to read import file: {exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(result)
        return

    title = "Import dry run complete" if dry_run else "Import complete"
    table = Table(title=title)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("input_path", str(result["input_path"]))
    table.add_row("conflict_mode", str(result["conflict_mode"]))
    table.add_row("dry_run", str(result["dry_run"]))
    table.add_row("include_settings", str(result["include_settings"]))
    table.add_row("snapshot_schema_version", str(result["snapshot_schema_version"]))
    table.add_row("payload_release_count", str(result["payload_release_count"]))
    table.add_row("imported_release_count", str(result["imported_release_count"]))
    table.add_row("imported_mapping_count", str(result["imported_mapping_count"]))
    table.add_row(
        "imported_market_price_count", str(result["imported_market_price_count"])
    )
    table.add_row("imported_settings_count", str(result["imported_settings_count"]))
    table.add_row(
        "pre_import_release_count_total", str(result["pre_import_release_count_total"])
    )
    table.add_row(
        "pre_import_release_count_active",
        str(result["pre_import_release_count_active"]),
    )
    table.add_row("pre_import_mapped_count", str(result["pre_import_mapped_count"]))
    table.add_row("pre_import_settings_count", str(result["pre_import_settings_count"]))
    console.print(table)


@bootstrap_app.command("import")
def bootstrap_import(
    input_path: str = typer.Option(
        ..., "--input", "-i", help="Input JSON/CSV bootstrap path"
    ),
    source_format: str = typer.Option(
        "auto",
        "--format",
        help=(
            "Bootstrap source format: auto, discofy, direct, "
            "or discogs-to-spotify (alias for discofy parser)"
        ),
    ),
    conflict_mode: str = typer.Option(
        "merge",
        "--conflict-mode",
        help="Conflict mode for existing mappings: merge or replace",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate and preview without writing"
    ),
    default_confidence: float = typer.Option(
        0.85,
        "--default-confidence",
        min=0.0,
        max=1.0,
        help="Default confidence for rows without confidence",
    ),
    mark_override: bool = typer.Option(
        False, "--mark-override", help="Persist imported mappings as overrides"
    ),
    skip_missing_releases: bool = typer.Option(
        True,
        "--skip-missing-releases/--allow-missing-releases",
        help="Skip mappings whose Discogs release id is not present locally",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Bootstrap-import mapping candidates from external tools."""
    try:
        result = run_bootstrap_mapping_import(
            input_path=input_path,
            source_format=source_format,
            conflict_mode=conflict_mode,
            dry_run=dry_run,
            default_confidence=default_confidence,
            mark_override=mark_override,
            skip_missing_releases=skip_missing_releases,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except OSError as exc:
        console.print(f"[red]Failed to read bootstrap file: {exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(result)
        return

    title = "Bootstrap import dry run complete" if dry_run else "Bootstrap import complete"
    table = Table(title=title)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    for key in (
        "input_path",
        "input_kind",
        "source_format_requested",
        "source_format_used",
        "conflict_mode",
        "dry_run",
        "default_confidence",
        "mark_override",
        "skip_missing_releases",
        "parsed_mapping_count",
        "invalid_row_count",
        "duplicate_row_count",
        "imported_mapping_count",
        "skipped_missing_release_count",
        "skipped_existing_mapping_count",
        "skipped_override_mapping_count",
        "pre_import_release_count_total",
        "pre_import_release_count_active",
        "pre_import_mapped_count",
    ):
        table.add_row(key, str(result.get(key)))
    console.print(table)

    preview = result.get("preview")
    if not isinstance(preview, list) or not preview:
        return

    preview_table = Table(title=f"bootstrap preview ({len(preview)} shown)")
    preview_table.add_column("discogs_release_id", style="cyan")
    preview_table.add_column("spotify_album_id", style="white")
    preview_table.add_column("confidence", style="magenta")
    preview_table.add_column("is_override", style="yellow")
    for row in preview:
        if not isinstance(row, dict):
            continue
        preview_table.add_row(
            str(row.get("discogs_release_id")),
            str(row.get("spotify_album_id")),
            str(row.get("confidence")),
            str(row.get("is_override")),
        )
    console.print(preview_table)


@review_app.command("list")
def review_list(
    report_path: str | None = typer.Option(
        None,
        "--report",
        help="Match audit report path (default: XDG latest report).",
    ),
    limit: int = typer.Option(50, "--limit", min=1, help="Rows per section"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show queued audit review candidates and unresolved audit errors."""
    try:
        result = run_match_audit_review_list(report_path=report_path, limit=limit)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except OSError as exc:
        console.print(f"[red]Failed to read review report: {exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(result)
        return

    table = Table(title="match review queue")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("report_path", str(result.get("report_path") or ""))
    table.add_row("review_count", str(result.get("review_count") or 0))
    table.add_row("error_count", str(result.get("error_count") or 0))
    table.add_row(
        "manual_applied_count", str(result.get("manual_applied_count") or 0)
    )
    table.add_row(
        "manual_rejected_count", str(result.get("manual_rejected_count") or 0)
    )
    console.print(table)

    review_queue = _as_dict_list(result.get("review_queue"))
    if review_queue:
        _render_match_results_table(
            review_queue,
            title=f"review candidates ({len(review_queue)} shown)",
        )

    errors = _as_dict_list(result.get("errors"))
    if errors:
        _render_match_results_table(errors, title=f"audit errors ({len(errors)} shown)")


def _validate_review_selection(*, release_ids: list[int], apply_all: bool) -> None:
    if apply_all and release_ids:
        raise ValueError("Use either --all or one or more --release-id values, not both.")
    if not apply_all and not release_ids:
        raise ValueError("Provide --all or at least one --release-id.")


@review_app.command("apply")
def review_apply(
    release_ids: list[int] = typer.Option(
        None,
        "--release-id",
        help="Discogs release id to apply from the review queue (repeatable).",
    ),
    apply_all: bool = typer.Option(False, "--all", help="Apply all review candidates."),
    report_path: str | None = typer.Option(
        None,
        "--report",
        help="Match audit report path (default: XDG latest report).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Apply review-candidate mappings from an audit report."""
    try:
        _validate_review_selection(release_ids=release_ids, apply_all=apply_all)
        result = run_match_audit_review_action(
            action="apply",
            report_path=report_path,
            release_ids=release_ids,
            apply_all=apply_all,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except OSError as exc:
        console.print(f"[red]Failed to update review report: {exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(result)
        return

    table = Table(title="review apply complete")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("report_path", str(result.get("report_path") or ""))
    table.add_row("selected_count", str(result.get("selected_count") or 0))
    table.add_row("updated_count", str(result.get("updated_count") or 0))
    table.add_row(
        "run_manual_applied_count", str(result.get("run_manual_applied_count") or 0)
    )
    table.add_row("review_queue_count", str(result.get("review_queue_count") or 0))
    console.print(table)


@review_app.command("reject")
def review_reject(
    release_ids: list[int] = typer.Option(
        None,
        "--release-id",
        help="Discogs release id to reject from the review queue (repeatable).",
    ),
    apply_all: bool = typer.Option(
        False, "--all", help="Reject all review candidates."
    ),
    report_path: str | None = typer.Option(
        None,
        "--report",
        help="Match audit report path (default: XDG latest report).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Reject review-candidate mappings from an audit report."""
    try:
        _validate_review_selection(release_ids=release_ids, apply_all=apply_all)
        result = run_match_audit_review_action(
            action="reject",
            report_path=report_path,
            release_ids=release_ids,
            apply_all=apply_all,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except OSError as exc:
        console.print(f"[red]Failed to update review report: {exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(result)
        return

    table = Table(title="review reject complete")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("report_path", str(result.get("report_path") or ""))
    table.add_row("selected_count", str(result.get("selected_count") or 0))
    table.add_row("updated_count", str(result.get("updated_count") or 0))
    table.add_row(
        "run_manual_rejected_count", str(result.get("run_manual_rejected_count") or 0)
    )
    table.add_row("review_queue_count", str(result.get("review_queue_count") or 0))
    console.print(table)


@review_app.command("retry-errors")
def review_retry_errors(
    report_path: str | None = typer.Option(
        None,
        "--report",
        help="Match audit report path (default: XDG latest report).",
    ),
    limit: int | None = typer.Option(
        None, "--limit", min=1, help="Optional unmatched-release limit for retry pass."
    ),
    request_delay_seconds: float = typer.Option(
        0.15,
        "--request-delay-seconds",
        min=0.0,
        help="Delay between releases to reduce rate limits.",
    ),
    max_retries: int = typer.Option(
        5,
        "--max-retries",
        min=0,
        help="Max retries for 429 responses per release.",
    ),
    backoff_seconds: float = typer.Option(
        2.0,
        "--backoff-seconds",
        min=0.0,
        help="Base backoff seconds for retry waits.",
    ),
    scope: str | None = typer.Option(
        None,
        "--scope",
        help="Match scope for retry run: collection, wantlist, or both.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Retry previously errored audit entries from the current report."""
    try:
        result = run_match_audit_retry_errors(
            report_path=report_path,
            limit=limit,
            scope=scope,
            request_delay_seconds=request_delay_seconds,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            apply_safe_matches=False,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except MatchingDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(
            "Install missing dependency: [cyan]pip install rapidfuzz[/cyan] "
            "or [cyan]pip install -r requirements.txt[/cyan]"
        )
        raise typer.Exit(code=1) from exc
    except SpotifyDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except SpotifyAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except SpotifyApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(result)
        return

    _render_match_audit_summary(result)


@app.command("spin")
def spin(
    q: str | None = typer.Option(None, "--q", help="Search artist/title substring"),
    year: str | None = typer.Option(
        None, "--year", help="Single year or range like 1990:1999"
    ),
    genre: list[str] | None = typer.Option(
        None, "--genre", help="Filter by genre, repeatable"
    ),
    style: list[str] | None = typer.Option(
        None, "--style", help="Filter by style, repeatable"
    ),
    unmatched: bool = typer.Option(
        False, "--unmatched", help="Only spin from unmapped releases"
    ),
    seed: int | None = typer.Option(None, "--seed", help="Deterministic random seed"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Choose a random release from filtered results and persist last spin."""
    try:
        selected = run_spin_release(
            q=q,
            year=year,
            genres=genre or [],
            styles=style or [],
            unmatched=unmatched,
            seed=seed,
        )
    except (ValueError, NoReleasesFoundError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if json_output:
        _emit_json(selected)
        return

    console.print("[bold green]Spin result[/bold green]")
    _render_release_table([selected])


@app.command("devices")
def devices(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """List Spotify playback devices."""
    try:
        items = run_list_devices()
    except SpotifyDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except SpotifyAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except SpotifyApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(items)
        return

    _render_devices_table(items)


@device_app.command("set")
def device_set(device_id: str) -> None:
    """Persist the default Spotify playback device id."""
    try:
        selected = run_set_default_device(device_id)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except SpotifyDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except SpotifyAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except SpotifyApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    console.print(
        f"Default Spotify device set: id={selected.get('id')} name={selected.get('name')}"
    )


@device_app.command("auto")
def device_auto() -> None:
    """Auto-select and persist a likely desktop Spotify device."""
    try:
        selected = run_auto_set_default_device()
    except NoSpotifyDevicesError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=5) from exc
    except SpotifyDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except SpotifyAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except SpotifyApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    console.print(
        f"Auto-selected default device: id={selected.get('id')} name={selected.get('name')}"
    )


@config_app.command("show")
def config_show(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show persisted app settings."""
    settings = run_config_show()
    if json_output:
        _emit_json(settings)
        return

    if not settings:
        console.print("No stored app settings.")
        return

    _render_settings_table(settings)


@config_app.command("set")
def config_set(
    key: str,
    value: str,
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Set an app setting key/value pair."""
    try:
        result = run_config_set(key, value)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if json_output:
        _emit_json(result)
        return

    console.print(f"Set config: {result['key']}={result['value']}")


@config_app.command("unset")
def config_unset(
    key: str, json_output: bool = typer.Option(False, "--json", help="Output JSON")
) -> None:
    """Remove an app setting key."""
    try:
        result = run_config_unset(key)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if json_output:
        _emit_json(result)
        return

    if result["removed"]:
        console.print(f"Unset config key: {result['key']}")
    else:
        console.print(f"Config key was not set: {result['key']}")


@auth_app.command("spotify")
def auth_spotify(
    listen_host: str = typer.Option(
        "127.0.0.1", "--listen-host", help="OAuth callback host"
    ),
    listen_port: int = typer.Option(
        8765,
        "--listen-port",
        min=1,
        max=65535,
        help="OAuth callback port",
    ),
    timeout_seconds: int = typer.Option(
        180,
        "--timeout-seconds",
        min=10,
        max=3600,
        help="Max seconds to wait for browser callback",
    ),
    open_browser: bool = typer.Option(
        False,
        "--open-browser",
        help="Attempt to open browser automatically with Spotify authorization URL.",
    ),
    manual: bool = typer.Option(
        False,
        "--manual",
        help="Skip local callback server and enter callback URL/code manually.",
    ),
    callback_url: str | None = typer.Option(
        None,
        "--callback-url",
        help="Manual mode: full Spotify redirect callback URL containing code/state.",
    ),
    code: str | None = typer.Option(
        None,
        "--code",
        help="Manual mode: Spotify authorization code.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Run Spotify OAuth login via local callback server."""

    def _on_authorization_url(url: str) -> None:
        if json_output:
            return
        console.print("Open this Spotify authorization URL in a browser:")
        console.print(f"[cyan]{url}[/cyan]")
        console.print("Waiting for Spotify callback...")

    def _on_manual_authorization_input() -> str:
        console.print(
            "[yellow]Local callback unavailable or timed out. Using manual authorization input.[/yellow]"
        )
        console.print(
            "Paste the full callback URL (preferred) or the authorization code:"
        )
        return typer.prompt("Callback URL or code", prompt_suffix=": ")

    manual_requested = bool(manual or callback_url or code)
    if json_output and manual_requested and not callback_url and not code:
        console.print(
            "[red]Manual mode with --json requires --callback-url or --code.[/red]"
        )
        raise typer.Exit(code=2)

    try:
        result = run_spotify_oauth_login(
            listen_host=listen_host,
            listen_port=listen_port,
            timeout_seconds=timeout_seconds,
            open_browser=open_browser,
            manual_mode=manual,
            manual_callback_url=callback_url,
            manual_code=code,
            allow_manual_fallback=bool(not json_output and not manual_requested),
            on_authorization_url=_on_authorization_url,
            on_manual_authorization_input=(
                _on_manual_authorization_input if not json_output else None
            ),
        )
    except SpotifyDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except SpotifyAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc

    if json_output:
        _emit_json(result)
        return

    table = Table(title="Spotify OAuth complete")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("listen_host", str(result.get("listen_host")))
    table.add_row("listen_port", str(result.get("listen_port")))
    table.add_row("redirect_uri", str(result.get("redirect_uri")))
    table.add_row("access_token_expires_in", str(result.get("access_token_expires_in")))
    table.add_row("received_refresh_token", str(result.get("received_refresh_token")))
    table.add_row("stored_refresh_token", str(result.get("stored_refresh_token")))
    table.add_row("open_browser_requested", str(result.get("open_browser_requested")))
    table.add_row("open_browser_succeeded", str(result.get("open_browser_succeeded")))
    table.add_row("manual_mode_requested", str(result.get("manual_mode_requested")))
    table.add_row("manual_fallback_used", str(result.get("manual_fallback_used")))
    table.add_row("authorization_code_source", str(result.get("authorization_code_source")))
    console.print(table)


@auth_app.command("spotify-doctor")
def auth_spotify_doctor(
    listen_host: str = typer.Option(
        "127.0.0.1",
        "--listen-host",
        help="Expected OAuth callback host for redirect URI validation hints.",
    ),
    listen_port: int = typer.Option(
        8765,
        "--listen-port",
        min=1,
        max=65535,
        help="Expected OAuth callback port for redirect URI validation hints.",
    ),
    probe_devices: bool = typer.Option(
        True,
        "--probe-devices/--no-probe-devices",
        help="Attempt Spotify devices call as part of diagnostics.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Diagnose Spotify auth/setup state with actionable next steps."""
    report = dict(
        run_spotify_auth_diagnostics(listen_host=listen_host, listen_port=listen_port)
    )
    report.setdefault("device_probe_attempted", False)
    report.setdefault("device_probe_ok", None)
    report.setdefault("device_count", None)
    report.setdefault("device_probe_error", None)

    should_probe = bool(probe_devices and report.get("addon_available"))
    if should_probe:
        report["device_probe_attempted"] = True
        try:
            devices = run_list_devices()
        except (SpotifyDependencyError, SpotifyAuthError, SpotifyApiError) as exc:
            report["device_probe_ok"] = False
            report["device_probe_error"] = str(exc)
        else:
            report["device_probe_ok"] = True
            report["device_count"] = len(devices)
    if json_output:
        _emit_json(report)
        return
    _render_spotify_auth_doctor_table(report)


@app.command("play")
def play(
    discogs_release_id: int | None = typer.Argument(
        None,
        help="Discogs release id to play (uses mapped Spotify album).",
    ),
    last_spin: bool = typer.Option(
        False, "--last-spin", help="Play the most recent spin result"
    ),
    auto_match: bool = typer.Option(
        False,
        "--auto-match",
        help="Attempt automatic Discogs->Spotify mapping when missing.",
    ),
    open_fallback: bool = typer.Option(
        False,
        "--open",
        help="Print a Spotify URL fallback instead of failing when playback cannot start.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Start Spotify playback for a mapped Discogs release."""
    spotify_capability = get_capabilities().spotify
    effective_open_fallback = bool(open_fallback)
    if not spotify_capability.addon_available:
        effective_open_fallback = True

    try:
        result = run_play_release(
            discogs_release_id=discogs_release_id,
            use_last_spin=last_spin,
            auto_match=auto_match,
            open_fallback=effective_open_fallback,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except MissingLastSpinError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=5) from exc
    except MissingSpotifyMappingError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=5) from exc
    except NoPlayableDeviceError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=5) from exc
    except MatchingDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(
            "Install missing dependency: [cyan]pip install rapidfuzz[/cyan] "
            "or [cyan]pip install -r requirements.txt[/cyan]"
        )
        raise typer.Exit(code=1) from exc
    except SpotifyDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except SpotifyAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except SpotifyPlaybackError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=5) from exc
    except SpotifyApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc

    if json_output:
        _emit_json(result)
        return

    if result.get("playback_started"):
        table = Table(title="Playback started")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("discogs_release_id", str(result["discogs_release_id"]))
        table.add_row("spotify_album_id", str(result["spotify_album_id"]))
        table.add_row("device_id", str(result["device_id"]))
        table.add_row("device_name", str(result["device_name"]))
        table.add_row("used_last_spin", str(result["used_last_spin"]))
        table.add_row("auto_match_attempted", str(result["auto_match_attempted"]))
        table.add_row("auto_matched", str(result["auto_matched"]))
        table.add_row("spotify_open_url", str(result["spotify_open_url"]))
        console.print(table)
        return

    console.print(
        f"[yellow]Playback fallback:[/yellow] {result.get('message') or 'Playback was not started.'}"
    )
    if result.get("fallback_open_url"):
        prefix = "Open in Spotify"
        if spotify_capability.addon_available:
            prefix = "Spotify URL"
        console.print(f"{prefix}: [cyan]{result['fallback_open_url']}[/cyan]")


@app.command("open")
def open_discogs(
    discogs_release_id: int = typer.Argument(
        ...,
        help="Discogs release id to open in marketplace.",
    ),
    copy: bool = typer.Option(
        False,
        "--copy",
        "-c",
        help="Copy URL to clipboard instead of opening browser.",
    ),
) -> None:
    """Open a release on Discogs marketplace in your browser."""
    url = f"https://www.discogs.com/sell/release/{discogs_release_id}"

    if copy:
        try:
            pyperclip = cast(_PyperclipModule, importlib.import_module("pyperclip"))
            pyperclip.copy(url)
            console.print(f"[green]Copied to clipboard:[/green] {url}")
        except ModuleNotFoundError:
            console.print(f"[yellow]URL (install pyperclip for --copy):[/yellow] {url}")
    else:
        import webbrowser
        console.print(f"[cyan]Opening:[/cyan] {url}")
        webbrowser.open(url)


@app.command("recent")
def recent(
    days: int = typer.Option(7, "--days", "-d", min=1, help="Number of days to look back"),
    limit: int = typer.Option(10, "--limit", "-l", min=1, help="Maximum releases to show"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show recently added releases from your collection."""
    from discogs_player.use_cases.list_recent import run_recent_releases
    
    result = run_recent_releases(days=days, limit=limit)
    
    if json_output:
        _emit_json(result)
        return
    
    releases = result.get("releases", [])
    if not releases:
        console.print(f"[yellow]No releases added in the last {days} days.[/yellow]")
        return
    
    table = Table(title=f"Recently Added (last {days} days)")
    table.add_column("Added", style="cyan")
    table.add_column("Artist", style="magenta")
    table.add_column("Title", style="white")
    table.add_column("Year", style="green")
    table.add_column("Release ID", style="dim")
    
    for release in releases:
        added_at = str(release.get("added_at", "")[:10])
        table.add_row(
            added_at,
            str(release.get("artist", "Unknown")),
            str(release.get("title", "Unknown")),
            str(release.get("year", "")),
            str(release.get("discogs_release_id", "")),
        )
    
    console.print(table)
    console.print(f"[dim]Showing {len(releases)} release(s)[/dim]")


@app.command("match")
def match(
    arg1: str | None = typer.Argument(
        None,
        help="Either <discogs_release_id> or literals `override` / `audit`.",
    ),
    arg2: str | None = typer.Argument(
        None,
        help="When using override: <discogs_release_id>.",
    ),
    arg3: str | None = typer.Argument(
        None,
        help="When using override: <spotify_album_id>.",
    ),
    unmatched: bool = typer.Option(
        False, "--unmatched", help="Match a batch of unmatched releases"
    ),
    scope: str = typer.Option(
        "collection",
        "--scope",
        help="Match scope: collection, wantlist, or both.",
    ),
    limit: int | None = typer.Option(
        None, "--limit", min=1, help="Batch size for --unmatched or audit."
    ),
    threshold: float = typer.Option(
        0.72, "--threshold", help="Review threshold (0.0 to 1.0)."
    ),
    auto_apply_threshold: float = typer.Option(
        SAFE_AUTO_APPLY_THRESHOLD,
        "--auto-apply-threshold",
        help="Safe auto-apply threshold (0.0 to 1.0).",
    ),
    apply_safe_matches: bool = typer.Option(
        False,
        "--apply-safe",
        help="For audit mode, persist only safe matches above auto-apply threshold.",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="For audit mode, resume from report path if it exists.",
    ),
    report_path: str | None = typer.Option(
        None,
        "--report",
        help="For audit mode, JSON report path (default: XDG data report file).",
    ),
    request_delay_seconds: float = typer.Option(
        0.15,
        "--request-delay-seconds",
        min=0.0,
        help="For audit mode, delay between releases to reduce rate limits.",
    ),
    max_retries: int = typer.Option(
        5,
        "--max-retries",
        min=0,
        help="For audit mode, max retries for 429 responses per release.",
    ),
    backoff_seconds: float = typer.Option(
        2.0,
        "--backoff-seconds",
        min=0.0,
        help="For audit mode, base backoff seconds for retry waits.",
    ),
    external_fallback: bool = typer.Option(
        True,
        "--external-fallback/--no-external-fallback",
        help=(
            "For single-release match only: on Spotify 429 rate-limit errors, "
            "try local/bootstrap/web fallback providers."
        ),
    ),
    retry_errors: bool = typer.Option(
        True,
        "--retry-errors/--no-retry-errors",
        help="When resuming audit, retry previously failed error entries.",
    ),
    compact: bool = typer.Option(
        False,
        "--compact",
        help="For audit mode, emit compact JSON output without full entry arrays.",
    ),
    progress_log: str | None = typer.Option(
        None,
        "--progress-log",
        help="For audit mode, append in-batch per-release progress rows to a log file.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """
    Match Discogs releases to Spotify albums.

    Supported forms:
    - `dplayer match <release_id>`
    - `dplayer match --unmatched --limit N`
    - `dplayer match override <release_id> <spotify_album_id>`
    - `dplayer match audit --resume --report <path>`
    """
    try:
        if arg1 == "audit":
            if unmatched:
                raise ValueError("Do not combine --unmatched with `match audit`.")
            if arg2 is not None or arg3 is not None:
                raise ValueError("Usage: dplayer match audit [--options]")

            summary = run_match_audit(
                scope=scope,
                limit=limit,
                review_threshold=threshold,
                auto_apply_threshold=auto_apply_threshold,
                apply_safe_matches=apply_safe_matches,
                resume=resume,
                report_path=report_path,
                request_delay_seconds=request_delay_seconds,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
                retry_errors_on_resume=retry_errors,
                compact_output=compact,
                progress_log_path=progress_log,
            )
            if json_output:
                _emit_json(summary)
                return

            _render_match_audit_summary(summary)
            review_queue = _as_dict_list(summary.get("review_queue"))
            if review_queue:
                _render_match_results_table(
                    review_queue[:20],
                    title=f"match audit review queue ({len(review_queue)} total)",
                )
            errors = _as_dict_list(summary.get("errors"))
            if errors:
                _render_match_results_table(
                    errors[:20],
                    title=f"match audit errors ({len(errors)} total)",
                )
            console.print(
                "run_processed_count="
                f"{summary.get('run_processed_count', 0)} "
                "run_auto_applied_count="
                f"{summary.get('run_auto_applied_count', 0)} "
                "run_review_queue_count="
                f"{summary.get('run_review_queue_count', 0)} "
                f"run_error_count={summary.get('run_error_count', 0)}"
            )
            return

        if arg1 == "override":
            if arg2 is None or arg3 is None:
                raise ValueError(
                    "Usage: dplayer match override <release_id> <spotify_album_id>"
                )
            if unmatched:
                raise ValueError("Do not use --unmatched with `match override`.")

            release_id = _parse_release_id(arg2)
            result = run_match_override(release_id, arg3)
            if json_output:
                _emit_json(result)
                return

            table = Table(title="Mapping override saved")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            table.add_row("discogs_release_id", str(result["discogs_release_id"]))
            table.add_row("spotify_album_id", str(result["spotify_album_id"]))
            table.add_row("confidence", str(result["confidence"]))
            table.add_row("is_override", str(result["is_override"]))
            console.print(table)
            return

        if arg2 is not None or arg3 is not None:
            raise ValueError(
                "Unexpected extra arguments. Use `dplayer match <release_id>` or "
                "`dplayer match override <release_id> <spotify_album_id>`."
            )

        if unmatched:
            if arg1 is not None:
                raise ValueError("Do not pass <release_id> when using --unmatched.")
            summary = run_match_unmatched(
                limit=limit if limit is not None else 25,
                scope=scope,
                threshold=threshold,
                auto_apply_threshold=auto_apply_threshold,
            )
            if json_output:
                _emit_json(summary)
                return

            unmatched_results = _as_dict_list(summary.get("results"))
            _render_match_results_table(
                unmatched_results, title="match --unmatched results"
            )
            console.print(
                "processed_count="
                f"{summary['processed_count']} "
                f"matched_count={summary['matched_count']} "
                f"review_count={summary.get('review_count', 0)} "
                f"error_count={summary.get('error_count', 0)}"
            )
            return

        if arg1 is None:
            raise ValueError(
                "Usage: dplayer match <release_id> | dplayer match --unmatched "
                "--limit N | dplayer match audit [--options]"
            )

        release_id = _parse_release_id(arg1)
        result = run_match_release(
            release_id,
            threshold=threshold,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            external_fallback=external_fallback,
        )
        if json_output:
            _emit_json(result)
            return

        _render_match_results_table([result], title="match result")
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    except MatchingDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(
            "Install missing dependency: [cyan]pip install rapidfuzz[/cyan] "
            "or [cyan]pip install -r requirements.txt[/cyan]"
        )
        raise typer.Exit(code=1) from exc
    except SpotifyDependencyError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(f"Install command (Pop!_OS): [cyan]{APT_INSTALL_CMD}[/cyan]")
        raise typer.Exit(code=1) from exc
    except SpotifyAuthError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    except SpotifyApiError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=4) from exc
