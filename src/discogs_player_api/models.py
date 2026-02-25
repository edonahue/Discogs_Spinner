"""Pydantic request models for API routes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from discogs_player.use_cases.ensure_mapping import (
    DEFAULT_MATCH_AUDIT_BACKOFF_SECONDS,
    DEFAULT_MATCH_AUDIT_MAX_RETRIES,
    DEFAULT_MATCH_AUDIT_REQUEST_DELAY_SECONDS,
    DEFAULT_REVIEW_THRESHOLD,
    SAFE_AUTO_APPLY_THRESHOLD,
)


class SyncRequest(BaseModel):
    allow_empty_deactivate: bool = False


class PlayRequest(BaseModel):
    auto_match: bool = False
    open_fallback: bool = True


class MatchReleaseRequest(BaseModel):
    threshold: float = DEFAULT_REVIEW_THRESHOLD
    max_retries: int = DEFAULT_MATCH_AUDIT_MAX_RETRIES
    backoff_seconds: float = DEFAULT_MATCH_AUDIT_BACKOFF_SECONDS
    external_fallback: bool = True
    external_fallback_timeout_seconds: float = 8.0


class MatchAuditRequest(BaseModel):
    scope: Literal["collection", "wantlist", "both"] | None = None
    limit: int | None = Field(default=None, ge=1)
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD
    auto_apply_threshold: float = SAFE_AUTO_APPLY_THRESHOLD
    apply_safe_matches: bool = False
    resume: bool = False
    request_delay_seconds: float = DEFAULT_MATCH_AUDIT_REQUEST_DELAY_SECONDS
    backoff_seconds: float = DEFAULT_MATCH_AUDIT_BACKOFF_SECONDS
    max_retries: int = DEFAULT_MATCH_AUDIT_MAX_RETRIES
    retry_errors_on_resume: bool = True
    compact_output: bool = True


class MatchReviewActionRequest(BaseModel):
    release_ids: list[int] | None = None
    apply_all: bool = False


class ValueRefreshRequest(BaseModel):
    limit: int = Field(default=100, ge=1)
    stale_days: int = Field(default=30, ge=0)
    release_ids: list[int] | None = None
    from_missing: bool = False
