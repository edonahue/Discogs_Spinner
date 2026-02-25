import logging

import typer

from discogs_player.cli.render import print_json as render_json
from discogs_player.use_cases.list_wantlist import run_list_wantlist
from discogs_player.use_cases.spin_wantlist import (
    NoWantlistItemsFoundError,
    run_spin_wantlist,
)
from discogs_player.use_cases.sync_wantlist import run_sync_wantlist
from discogs_player.use_cases.wantlist_tracklist_cached import (
    run_wantlist_tracklist_cached,
)
from discogs_player.use_cases.wantlist_tracklist_show import run_wantlist_tracklist_show
from discogs_player.use_cases.wantlist_value_refresh import (
    run_refresh_wantlist_market_values,
)

_logger = logging.getLogger(__name__)


def sync(json_output: bool = False, full: bool = False) -> None:
    """Sync wantlist with Discogs."""
    summary = run_sync_wantlist(allow_empty_deactivate=full)
    if json_output:
        render_json(summary)


def refresh_values(
    limit: int = 10000,
    stale_days: int = 30,
) -> None:
    """Refresh stale market prices for wantlist items."""
    run_refresh_wantlist_market_values(limit=limit, stale_days=stale_days)


def tracks_show(discogs_release_id: int, refresh: bool = False) -> None:
    """Show cached tracklist for a release in your wantlist."""
    run_wantlist_tracklist_show(discogs_release_id, refresh=refresh)


def tracks_cached(limit: int | None = 25) -> None:
    """List releases in your wantlist with cached tracklists."""
    normalized_limit = max(1, int(limit)) if limit is not None else 25
    entries = run_list_wantlist(limit=normalized_limit)
    cached_entries: list[dict[str, object]] = []
    for entry in entries:
        release_id = entry.get("discogs_release_id")
        if not isinstance(release_id, int) or release_id <= 0:
            continue
        cached = run_wantlist_tracklist_cached(release_id)
        if bool(cached.get("has_cached_tracklist")):
            cached_entries.append(cached)
    render_json(
        {
            "ok": True,
            "limit": normalized_limit,
            "cached_count": len(cached_entries),
            "cached_tracklists": cached_entries,
        }
    )


def spin(
    q: str | None = typer.Option(
        None, "--query", "-q", help="Text query for artist or title"
    ),
    year: str | None = typer.Option(
        None, "--year", help="Filter by year or year range (YYYY or YYYY:YYYY)"
    ),
    genre: list[str] | None = typer.Option(
        None, "--genre", help="Filter by genre (can specify multiple)"
    ),
    style: list[str] | None = typer.Option(
        None, "--style", help="Filter by style (can specify multiple)"
    ),
    unmatched: bool = typer.Option(
        False, "--unmatched", help="Only spin from releases without a Spotify match"
    ),
    seed: int | None = typer.Option(None, "--seed", help="Random seed"),
) -> None:
    """Spin for a random wantlist item."""
    try:
        result = run_spin_wantlist(
            q=q,
            year=year,
            genres=genre or [],
            styles=style or [],
            unmatched=unmatched,
            seed=seed,
        )
        render_json(result)
    except NoWantlistItemsFoundError as exc:
        _logger.warning(str(exc))
