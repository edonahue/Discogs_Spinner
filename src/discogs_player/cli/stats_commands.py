import logging
from discogs_player.cli.render import print_json
from discogs_player.use_cases.release_stats_refresh import run_refresh_release_stats

_logger = logging.getLogger(__name__)


def refresh_release_stats(
    limit: int = 20,
    force: bool = False,
    wantlist: bool = False,
) -> None:
    """Refresh release statistics (community ratings, have/want, market counts)."""
    result = run_refresh_release_stats(
        limit=limit, force_refresh=force, is_wantlist=wantlist
    )
    print_json(result)
