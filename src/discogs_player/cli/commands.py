"""Typer command definitions for dplayer."""

from __future__ import annotations

import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from discogs_player.services.spotify_client import SpotifyApiError, SpotifyPlaybackError
from discogs_player.services.matching import MatchingDependencyError
from discogs_player.services.spotify_oauth import SpotifyAuthError, SpotifyDependencyError
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
from discogs_player.use_cases.list_releases import run_list_releases
from discogs_player.use_cases.play_release import (
    MissingLastSpinError,
    MissingSpotifyMappingError,
    NoPlayableDeviceError,
    run_play_release,
)
from discogs_player.use_cases.spin_release import NoReleasesFoundError, run_spin_release
from discogs_player.use_cases.status_report import get_status_report

APT_INSTALL_CMD = (
    "sudo apt update && sudo apt install -y "
    "python3 python3-venv python3-pip python3-setuptools libsecret-1-0 "
    "build-essential python3-dev"
)

app = typer.Typer(help="Discogs Player CLI")
device_app = typer.Typer(help="Manage the default Spotify playback device")
config_app = typer.Typer(help="Manage local app settings")
app.add_typer(device_app, name="device")
app.add_typer(config_app, name="config")
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


def _render_release_table(releases: list[dict[str, object]]) -> None:
    table = Table(title="discogs_player releases")
    table.add_column("Discogs ID", style="cyan", justify="right")
    table.add_column("Artist", style="white")
    table.add_column("Title", style="white")
    table.add_column("Year", style="magenta", justify="right")
    table.add_column("Mapped", style="green", justify="center")

    for item in releases:
        mapped = "yes" if item.get("spotify_album_id") else "no"
        year = item.get("year")
        table.add_row(
            str(item.get("discogs_release_id")),
            str(item.get("artist") or ""),
            str(item.get("title") or ""),
            str(year) if year is not None else "",
            mapped,
        )

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
        console.print(json.dumps(report, indent=2, sort_keys=True))
        return
    _render_status_table(report)


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


@app.command("list")
def list_releases(
    limit: int = typer.Option(25, "--limit", min=1, help="Max releases to return"),
    q: str | None = typer.Option(None, "--q", help="Search artist/title substring"),
    year: str | None = typer.Option(None, "--year", help="Single year or range like 1990:1999"),
    genre: list[str] | None = typer.Option(None, "--genre", help="Filter by genre, repeatable"),
    style: list[str] | None = typer.Option(None, "--style", help="Filter by style, repeatable"),
    unmatched: bool = typer.Option(False, "--unmatched", help="Only show unmapped releases"),
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
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if json_output:
        console.print(json.dumps(releases, indent=2, sort_keys=True))
        return

    _render_release_table(releases)


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
        console.print(json.dumps(selected, indent=2, sort_keys=True))
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
        console.print(json.dumps(items, indent=2, sort_keys=True))
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
        console.print(json.dumps(settings, indent=2, sort_keys=True))
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
        console.print(json.dumps(result, indent=2, sort_keys=True))
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
        console.print(json.dumps(result, indent=2, sort_keys=True))
        return

    if result["removed"]:
        console.print(f"Unset config key: {result['key']}")
    else:
        console.print(f"Config key was not set: {result['key']}")


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
        console.print(json.dumps(result, indent=2, sort_keys=True))
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
                console.print(json.dumps(result, indent=2, sort_keys=True))
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
                console.print(json.dumps(summary, indent=2, sort_keys=True))
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
            console.print(json.dumps(result, indent=2, sort_keys=True))
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
