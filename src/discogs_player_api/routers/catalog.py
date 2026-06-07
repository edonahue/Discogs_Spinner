"""Collection and wantlist catalog routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from discogs_player.use_cases.get_release import run_get_release
from discogs_player.use_cases.get_wantlist_entry import run_get_wantlist_entry
from discogs_player.use_cases.list_recent import run_recent_releases
from discogs_player.use_cases.release_collection_summary import (
    run_release_collection_summary,
)
from discogs_player.use_cases.list_releases import run_list_releases
from discogs_player.use_cases.list_wantlist import run_list_wantlist
from discogs_player.use_cases.tracklist_show import run_release_tracklist_show
from discogs_player_api.runtime import run_use_case

router = APIRouter(tags=["catalog"])


@router.get("/releases")
def api_list_releases(
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = Query(default=None),
    styles: list[str] | None = Query(default=None),
    limit: int | None = Query(default=25, ge=1),
    unmatched: bool = False,
    with_value: bool = False,
) -> dict[str, object]:
    return run_use_case(
        lambda: run_list_releases(
            q=q,
            year=year,
            genres=genres or [],
            styles=styles or [],
            limit=limit,
            unmatched=unmatched,
            with_value=with_value,
        )
    )


@router.get("/releases/summary")
def api_release_summary(
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = Query(default=None),
    styles: list[str] | None = Query(default=None),
    unmatched: bool = False,
) -> dict[str, object]:
    return run_use_case(
        lambda: run_release_collection_summary(
            q=q,
            year=year,
            genres=genres or [],
            styles=styles or [],
            unmatched=unmatched,
        )
    )


@router.get("/releases/recent")
def api_recent_releases(
    days: int = Query(default=7, ge=1),
    limit: int = Query(default=25, ge=1),
) -> dict[str, object]:
    return run_use_case(lambda: run_recent_releases(days=days, limit=limit))


@router.get("/releases/{discogs_release_id}")
def api_get_release(
    discogs_release_id: int,
    with_value: bool = False,
) -> dict[str, object]:
    return run_use_case(
        lambda: run_get_release(
            discogs_release_id,
            with_value=with_value,
        )
    )


@router.get("/releases/{discogs_release_id}/tracklist")
def api_get_tracklist(
    discogs_release_id: int,
) -> dict[str, object]:
    return run_use_case(
        lambda: run_release_tracklist_show(discogs_release_id, refresh=False)
    )


@router.get("/wantlist")
def api_list_wantlist(
    q: str | None = None,
    year: str | None = None,
    genres: list[str] | None = Query(default=None),
    styles: list[str] | None = Query(default=None),
    limit: int = Query(default=25, ge=1),
    with_value: bool = False,
) -> dict[str, object]:
    return run_use_case(
        lambda: run_list_wantlist(
            q=q,
            year=year,
            genres=genres or [],
            styles=styles or [],
            limit=limit,
            with_value=with_value,
        )
    )


@router.get("/wantlist/{discogs_release_id}")
def api_get_wantlist_entry(
    discogs_release_id: int,
    with_value: bool = False,
) -> dict[str, object]:
    return run_use_case(
        lambda: run_get_wantlist_entry(
            discogs_release_id,
            with_value=with_value,
        )
    )
