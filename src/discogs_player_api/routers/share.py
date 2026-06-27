"""Analytics and value export routes (returns rendered content, not files)."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from discogs_player.use_cases.collection_analytics import run_collection_analytics
from discogs_player.use_cases.export import _analytics_to_markdown, _value_to_markdown
from discogs_player.use_cases.value_status import run_market_value_status
from discogs_player_api.runtime import run_use_case_raw

router = APIRouter(tags=["share"])


@router.get("/share/collection/markdown", response_class=PlainTextResponse)
def api_share_collection_markdown(
    limit: int = Query(default=20, ge=1),
) -> str:
    """Return collection analytics as a Markdown document."""
    def _payload() -> str:
        report = run_collection_analytics(limit=limit)
        return _analytics_to_markdown(report)

    return run_use_case_raw(_payload)


@router.get("/share/value/markdown", response_class=PlainTextResponse)
def api_share_value_markdown() -> str:
    """Return market value summary as a Markdown document."""
    def _payload() -> str:
        summary = run_market_value_status()
        return _value_to_markdown(summary)

    return run_use_case_raw(_payload)
