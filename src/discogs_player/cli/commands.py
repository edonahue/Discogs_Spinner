"""Typer command definitions for dplayer."""

from __future__ import annotations

import json
import sys
from typing import Callable

import typer
from rich.console import Console
from rich.table import Table

from discogs_player.use_cases.list_releases import run_list_releases
from discogs_player.use_cases.status_report import get_status_report

APT_INSTALL_CMD = "sudo apt update && sudo apt install -y python3 python3-venv python3-pip libsecret-1-0"

app = typer.Typer(help="Discogs Player CLI")
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
        from discogs_player.services.discogs_client import DiscogsApiError, DiscogsAuthError
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
            summary = run_sync_collection(progress_callback=progress_callback)
        else:
            with console.status("Syncing Discogs collection..."):
                summary = run_sync_collection(progress_callback=None)
    except MissingDiscogsTokenError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
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
    console.print(table)


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
