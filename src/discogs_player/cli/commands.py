"""Typer command definitions for dplayer."""

from __future__ import annotations

import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from discogs_player.services.spotify_client import SpotifyApiError, SpotifyPlaybackError
from discogs_player.services.matching import MatchingDependencyError
from discogs_player.services.discogs_client import (
    DiscogsApiError,
    DiscogsAuthError,
    DiscogsDependencyError,
)
from discogs_player.services.spotify_oauth import (
    SpotifyAuthError,
    SpotifyDependencyError,
    run_spotify_oauth_login,
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
    run_match_override,
    run_match_release,
    run_match_unmatched,
)
from discogs_player.use_cases.collection_analytics import run_collection_analytics
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

APT_INSTALL_CMD = (
    "sudo apt update && sudo apt install -y "
    "python3 python3-venv python3-pip python3-setuptools libsecret-1-0 "
    "build-essential python3-dev"
)

app = typer.Typer(help="Discogs Player CLI")
device_app = typer.Typer(help="Manage the default Spotify playback device")
config_app = typer.Typer(help="Manage local app settings")
auth_app = typer.Typer(help="Authenticate with external services")
wantlist_app = typer.Typer(help="Sync and browse Discogs wantlist")
value_app = typer.Typer(help="Refresh and view collection market values")
app.add_typer(device_app, name="device")
app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")
app.add_typer(wantlist_app, name="wantlist")
app.add_typer(value_app, name="value")
console = Console()


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

    table.add_row("last_spin_release_id", str(report["last_spin_release_id"]))
    table.add_row("market_value_last_updated", str(report["market_value_last_updated"]))
    table.add_row("wantlist_count", str(report["wantlist_count"]))

    console.print(table)


def _render_analytics_summary_table(report: dict[str, object]) -> None:
    table = Table(title="collection analytics")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    active = int(report.get("release_count_active") or 0)
    mapped = int(report.get("mapped_count") or 0)
    unmatched = int(report.get("unmatched_count") or 0)
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
    table.add_row("unpriced_release_count", str(summary.get("unpriced_release_count") or 0))
    table.add_row("total_lowest", f"{float(summary.get('total_lowest') or 0.0):.2f}")
    table.add_row("total_median", f"{float(summary.get('total_median') or 0.0):.2f}")
    table.add_row("total_highest", f"{float(summary.get('total_highest') or 0.0):.2f}")
    table.add_row("market_value_last_updated", str(summary.get("market_value_last_updated")))
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
    table.add_row("active_release_count", str(snapshot.get("active_release_count") or 0))
    table.add_row("priced_release_count", str(snapshot.get("priced_release_count") or 0))
    table.add_row("unpriced_release_count", str(snapshot.get("unpriced_release_count") or 0))
    table.add_row("total_lowest", _fmt_market_number(snapshot.get("total_lowest")))
    table.add_row("total_median", _fmt_market_number(snapshot.get("total_median")))
    table.add_row("total_highest", _fmt_market_number(snapshot.get("total_highest")))
    table.add_row("market_value_last_updated", str(snapshot.get("market_value_last_updated")))
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
            f"{float(delta_pct_item):.2f}" if isinstance(delta_pct_item, (int, float)) else "",
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
    table.add_row("market_last_updated_at", str(item.get("market_last_updated_at") or ""))
    table.add_row("market_spread", _fmt_market_number(item.get("market_spread")))
    table.add_row("market_midpoint", _fmt_market_number(item.get("market_midpoint")))
    table.add_row("market_price_point_count", str(item.get("market_price_point_count") or 0))
    table.add_row("has_market_value", str(item.get("has_market_value")))
    console.print(table)


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


def _render_match_results_table(items: list[dict[str, object]], *, title: str) -> None:
    table = Table(title=title)
    table.add_column("Discogs ID", style="cyan", justify="right")
    table.add_column("Artist", style="white")
    table.add_column("Title", style="white")
    table.add_column("Matched", justify="center")
    table.add_column("Spotify Album", style="green")
    table.add_column("Confidence", justify="right")
    table.add_column("Source", style="magenta")

    for item in items:
        confidence = item.get("confidence")
        confidence_str = f"{float(confidence):.3f}" if isinstance(confidence, (int, float)) else ""
        table.add_row(
            str(item.get("discogs_release_id") or ""),
            str(item.get("artist") or ""),
            str(item.get("title") or ""),
            "yes" if item.get("matched") else "no",
            str(item.get("spotify_album_id") or ""),
            confidence_str,
            str(item.get("source") or ""),
        )

    console.print(table)


def _parse_release_id(raw: str) -> int:
    value = raw.strip()
    if not value:
        raise ValueError("Release id cannot be empty.")
    if not value.isdigit():
        raise ValueError("Release id must be an integer.")
    return int(value)


@app.command("status")
def status(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
    """Show current local sync and mapping status."""
    report = get_status_report()
    if json_output:
        _emit_json(report)
        return
    _render_status_table(report)


@app.command("analytics")
def analytics(
    limit: int = typer.Option(10, "--limit", min=1, help="Max rows for top genre/style/artist lists"),
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
        rows=list(report.get("by_release_year") or []),
        key_field="year",
        key_header="Year",
    )
    _render_analytics_list_table(
        title="acquisition timeline",
        rows=list(report.get("acquisition_timeline") or []),
        key_field="year",
        key_header="Year",
    )
    _render_analytics_list_table(
        title="top genres",
        rows=list(report.get("top_genres") or []),
        key_field="genre",
        key_header="Genre",
    )
    _render_analytics_list_table(
        title="top styles",
        rows=list(report.get("top_styles") or []),
        key_field="style",
        key_header="Style",
    )
    _render_analytics_list_table(
        title="top artists",
        rows=list(report.get("top_artists") or []),
        key_field="artist",
        key_header="Artist",
    )


@app.command("sync")
def sync(
    full: bool = typer.Option(False, "--full", help="Force a full sync pass"),
    no_images: bool = typer.Option(False, "--no-images", help="Skip image work (no-op for MVP)"),
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

    def progress_callback(page: int, pages: int, page_count: int, total_count: int) -> None:
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

    for warning in summary.get("warnings", []):
        console.print(f"[yellow]warning:[/yellow] {warning}")


@value_app.command("status")
def value_status(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
    """Show aggregated market value totals and coverage."""
    summary = run_market_value_status()
    if json_output:
        _emit_json(summary)
        return
    _render_market_value_status(summary)
    _render_market_value_examples(run_market_value_examples(limit=2))


@value_app.command("examples")
def value_examples(
    limit: int = typer.Option(2, "--limit", min=1, help="Examples to show per high/low group"),
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
def value_snapshot(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
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
    refresh: bool = typer.Option(False, "--refresh", help="Fetch fresh market value from Discogs first."),
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
    limit: int = typer.Option(25, "--limit", min=1, help="Max missing releases to return"),
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
    csv_output: str | None = typer.Option(None, "--csv", help="Write results to CSV output path."),
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
    limit: int = typer.Option(100, "--limit", min=1, help="Max releases to refresh per run"),
    stale_days: int = typer.Option(30, "--stale-days", min=0, help="Refresh only entries older than N days"),
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
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed refresh warnings"),
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
    table.add_row("release_ids_requested", str(len(summary.get("release_ids_requested") or [])))
    table.add_row("candidate_count", str(summary.get("candidate_count")))
    table.add_row("refreshed_count", str(summary.get("refreshed_count")))
    table.add_row("priced_count", str(summary.get("priced_count")))
    table.add_row("unpriced_count", str(summary.get("unpriced_count")))
    table.add_row("error_count", str(summary.get("error_count")))
    table.add_row("last_refresh_time", str(summary.get("last_refresh_time")))
    console.print(table)

    for warning in summary.get("warnings", []):
        console.print(f"[yellow]warning:[/yellow] {warning}")
    if summary.get("skipped_release_ids"):
        console.print(
            f"[yellow]skipped_release_ids:[/yellow] {', '.join(str(x) for x in summary['skipped_release_ids'])}"
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

    def progress_callback(page: int, pages: int, page_count: int, total_count: int) -> None:
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

    for warning in summary.get("warnings", []):
        console.print(f"[yellow]warning:[/yellow] {warning}")


@wantlist_app.command("list")
def wantlist_list(
    limit: int = typer.Option(25, "--limit", min=1, help="Max wantlist releases to return"),
    q: str | None = typer.Option(None, "--q", help="Search artist/title substring"),
    year: str | None = typer.Option(None, "--year", help="Single year or range like 1990:1999"),
    genre: list[str] | None = typer.Option(None, "--genre", help="Filter by genre, repeatable"),
    style: list[str] | None = typer.Option(None, "--style", help="Filter by style, repeatable"),
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


@app.command("list")
def list_releases(
    limit: int = typer.Option(25, "--limit", min=1, help="Max releases to return"),
    q: str | None = typer.Option(None, "--q", help="Search artist/title substring"),
    year: str | None = typer.Option(None, "--year", help="Single year or range like 1990:1999"),
    genre: list[str] | None = typer.Option(None, "--genre", help="Filter by genre, repeatable"),
    style: list[str] | None = typer.Option(None, "--style", help="Filter by style, repeatable"),
    unmatched: bool = typer.Option(False, "--unmatched", help="Only show unmapped releases"),
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
    active_only: bool = typer.Option(False, "--active-only", help="Only export active releases"),
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


@app.command("import")
def import_collection(
    input_path: str = typer.Option(..., "--input", "-i", help="Input JSON snapshot path"),
    conflict_mode: str = typer.Option(
        "merge",
        "--conflict-mode",
        help="Conflict mode: merge or replace",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and preview import without writing"),
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
    table.add_row("imported_market_price_count", str(result["imported_market_price_count"]))
    table.add_row("imported_settings_count", str(result["imported_settings_count"]))
    table.add_row("pre_import_release_count_total", str(result["pre_import_release_count_total"]))
    table.add_row("pre_import_release_count_active", str(result["pre_import_release_count_active"]))
    table.add_row("pre_import_mapped_count", str(result["pre_import_mapped_count"]))
    table.add_row("pre_import_settings_count", str(result["pre_import_settings_count"]))
    console.print(table)


@app.command("spin")
def spin(
    q: str | None = typer.Option(None, "--q", help="Search artist/title substring"),
    year: str | None = typer.Option(None, "--year", help="Single year or range like 1990:1999"),
    genre: list[str] | None = typer.Option(None, "--genre", help="Filter by genre, repeatable"),
    style: list[str] | None = typer.Option(None, "--style", help="Filter by style, repeatable"),
    unmatched: bool = typer.Option(False, "--unmatched", help="Only spin from unmapped releases"),
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
def devices(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
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
def config_show(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
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
def config_set(key: str, value: str, json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
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
def config_unset(key: str, json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
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
    listen_host: str = typer.Option("127.0.0.1", "--listen-host", help="OAuth callback host"),
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
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Run Spotify OAuth login via local callback server."""

    def _on_authorization_url(url: str) -> None:
        if json_output:
            return
        console.print("Open this Spotify authorization URL in a browser:")
        console.print(f"[cyan]{url}[/cyan]")
        console.print("Waiting for Spotify callback...")

    try:
        result = run_spotify_oauth_login(
            listen_host=listen_host,
            listen_port=listen_port,
            timeout_seconds=timeout_seconds,
            open_browser=open_browser,
            on_authorization_url=_on_authorization_url,
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
    console.print(table)


@app.command("play")
def play(
    discogs_release_id: int | None = typer.Argument(
        None,
        help="Discogs release id to play (uses mapped Spotify album).",
    ),
    last_spin: bool = typer.Option(False, "--last-spin", help="Play the most recent spin result"),
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
    try:
        result = run_play_release(
            discogs_release_id=discogs_release_id,
            use_last_spin=last_spin,
            auto_match=auto_match,
            open_fallback=open_fallback,
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
        console.print(f"Spotify URL: [cyan]{result['fallback_open_url']}[/cyan]")


@app.command("match")
def match(
    arg1: str | None = typer.Argument(
        None,
        help="Either <discogs_release_id> or the literal `override`.",
    ),
    arg2: str | None = typer.Argument(
        None,
        help="When using override: <discogs_release_id>.",
    ),
    arg3: str | None = typer.Argument(
        None,
        help="When using override: <spotify_album_id>.",
    ),
    unmatched: bool = typer.Option(False, "--unmatched", help="Match a batch of unmatched releases"),
    limit: int = typer.Option(25, "--limit", min=1, help="Batch size for --unmatched"),
    threshold: float = typer.Option(0.72, "--threshold", help="Match threshold (0.0 to 1.0)"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """
    Match Discogs releases to Spotify albums.

    Supported forms:
    - `dplayer match <release_id>`
    - `dplayer match --unmatched --limit N`
    - `dplayer match override <release_id> <spotify_album_id>`
    """
    try:
        if arg1 == "override":
            if arg2 is None or arg3 is None:
                raise ValueError("Usage: dplayer match override <release_id> <spotify_album_id>")
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
            summary = run_match_unmatched(limit=limit, threshold=threshold)
            if json_output:
                _emit_json(summary)
                return

            _render_match_results_table(summary["results"], title="match --unmatched results")
            console.print(
                f"processed_count={summary['processed_count']} matched_count={summary['matched_count']}"
            )
            return

        if arg1 is None:
            raise ValueError(
                "Usage: dplayer match <release_id> or dplayer match --unmatched --limit N"
            )

        release_id = _parse_release_id(arg1)
        result = run_match_release(release_id, threshold=threshold)
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
