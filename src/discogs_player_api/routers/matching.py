"""Matching and audit review routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from discogs_player.use_cases.ensure_mapping import (
    run_match_audit,
    run_match_audit_review_action,
    run_match_audit_review_list,
    run_match_release,
)
from discogs_player_api.models import (
    MatchAuditRequest,
    MatchReleaseRequest,
    MatchReviewActionRequest,
)
from discogs_player_api.runtime import run_use_case

router = APIRouter(tags=["matching"])


@router.post("/match/{discogs_release_id}")
def api_match_release(
    discogs_release_id: int,
    request: MatchReleaseRequest,
) -> dict[str, object]:
    return run_use_case(
        lambda: run_match_release(
            discogs_release_id=discogs_release_id,
            threshold=float(request.threshold),
            max_retries=int(request.max_retries),
            backoff_seconds=float(request.backoff_seconds),
            external_fallback=bool(request.external_fallback),
            external_fallback_timeout_seconds=float(
                request.external_fallback_timeout_seconds
            ),
        )
    )


@router.post("/match/audit")
def api_match_audit(request: MatchAuditRequest) -> dict[str, object]:
    return run_use_case(
        lambda: run_match_audit(
            scope=request.scope,
            limit=request.limit,
            review_threshold=float(request.review_threshold),
            auto_apply_threshold=float(request.auto_apply_threshold),
            apply_safe_matches=bool(request.apply_safe_matches),
            resume=bool(request.resume),
            request_delay_seconds=float(request.request_delay_seconds),
            backoff_seconds=float(request.backoff_seconds),
            max_retries=int(request.max_retries),
            retry_errors_on_resume=bool(request.retry_errors_on_resume),
            compact_output=bool(request.compact_output),
        )
    )


@router.get("/match/review")
def api_match_review_list(
    report_path: str | None = None,
    limit: int | None = Query(default=50, ge=1),
) -> dict[str, object]:
    return run_use_case(
        lambda: run_match_audit_review_list(
            report_path=report_path,
            limit=limit,
        )
    )


@router.post("/match/review/{action}")
def api_match_review_action(
    action: Literal["apply", "reject"],
    request: MatchReviewActionRequest,
    report_path: str | None = None,
) -> dict[str, object]:
    return run_use_case(
        lambda: run_match_audit_review_action(
            action=action,
            report_path=report_path,
            release_ids=request.release_ids,
            apply_all=bool(request.apply_all),
        )
    )
