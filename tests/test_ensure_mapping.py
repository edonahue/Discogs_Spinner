from __future__ import annotations

import json

import pytest

from discogs_player.data.db import get_connection
from discogs_player.data.repo import (
    get_spotify_mapping,
    upsert_releases,
    upsert_wantlist_entries,
)
from discogs_player.integrations.player_backend import PlayerApiError
from discogs_player.services.matching import MatchingResult
from discogs_player.use_cases import ensure_mapping
from discogs_player.use_cases.external_match_fallback import ExternalFallbackMatch


class _FakeBackend:
    @classmethod
    def addon_available(cls) -> bool:
        return True

    def is_configured(self, *, conn=None) -> bool:
        _ = conn
        return True

    def create_matching_client(self, *, conn=None):
        _ = conn
        return object()


class _FakeMatchingService:
    def __init__(
        self, spotify_client, *, threshold: float = 0.72, search_limit: int = 10
    ):
        _ = (spotify_client, threshold, search_limit)

    def match_release(self, release: dict[str, object]) -> MatchingResult:
        release_id = int(release["discogs_release_id"])
        if release_id == 1:
            return MatchingResult(
                matched=True,
                discogs_release_id=1,
                spotify_album_id="album-1",
                confidence=0.94,
                best_candidate={"id": "album-1", "name": "Nevermind"},
                candidates=[{"id": "album-1", "name": "Nevermind", "confidence": 0.94}],
            )

        return MatchingResult(
            matched=False,
            discogs_release_id=release_id,
            spotify_album_id=None,
            confidence=0.41,
            best_candidate={"id": "candidate-low", "name": "Low Match"},
            candidates=[
                {"id": "candidate-low", "name": "Low Match", "confidence": 0.41}
            ],
        )


class _SafePolicyMatchingService:
    def __init__(
        self, spotify_client, *, threshold: float = 0.72, search_limit: int = 10
    ):
        _ = (spotify_client, search_limit)
        self.threshold = threshold

    def match_release(self, release: dict[str, object]) -> MatchingResult:
        release_id = int(release["discogs_release_id"])
        if release_id == 10:
            confidence = 0.95
            album_id = "album-10"
        elif release_id == 11:
            confidence = 0.78
            album_id = "album-11"
        else:
            confidence = 0.33
            album_id = None

        matched = bool(album_id and confidence >= self.threshold)
        return MatchingResult(
            matched=matched,
            discogs_release_id=release_id,
            spotify_album_id=album_id if matched else None,
            confidence=confidence,
            best_candidate={
                "id": album_id,
                "name": f"Candidate {release_id}",
                "artists": [str(release.get("artist") or "")],
                "release_date": str(release.get("year") or ""),
            }
            if album_id
            else None,
            candidates=[
                {
                    "id": album_id,
                    "name": f"Candidate {release_id}",
                    "artists": [str(release.get("artist") or "")],
                    "confidence": confidence,
                }
            ]
            if album_id
            else [],
        )


class _RetryingMatchingService:
    attempts: dict[int, int] = {}

    def __init__(
        self, spotify_client, *, threshold: float = 0.72, search_limit: int = 10
    ):
        _ = (spotify_client, search_limit)
        self.threshold = threshold

    def match_release(self, release: dict[str, object]) -> MatchingResult:
        release_id = int(release["discogs_release_id"])
        current_attempt = self.attempts.get(release_id, 0)
        self.attempts[release_id] = current_attempt + 1

        if release_id == 21 and current_attempt == 0:
            raise RuntimeError("Spotify API request failed (429): Too many requests")

        confidence = 0.93 if release_id == 21 else 0.76
        album_id = f"album-{release_id}"
        matched = confidence >= self.threshold
        return MatchingResult(
            matched=matched,
            discogs_release_id=release_id,
            spotify_album_id=album_id if matched else None,
            confidence=confidence,
            best_candidate={
                "id": album_id,
                "name": f"Candidate {release_id}",
                "artists": [str(release.get("artist") or "")],
            },
            candidates=[
                {
                    "id": album_id,
                    "name": f"Candidate {release_id}",
                    "artists": [str(release.get("artist") or "")],
                    "confidence": confidence,
                }
            ],
        )


class _AlwaysRateLimitedMatchingService:
    def __init__(
        self, spotify_client, *, threshold: float = 0.72, search_limit: int = 10
    ):
        _ = (spotify_client, threshold, search_limit)

    def match_release(self, release: dict[str, object]) -> MatchingResult:
        _ = release
        raise RuntimeError("Spotify API request failed (429): Too many requests")


class _AlwaysAuthFailingMatchingService:
    def __init__(
        self, spotify_client, *, threshold: float = 0.72, search_limit: int = 10
    ):
        _ = (spotify_client, threshold, search_limit)

    def match_release(self, release: dict[str, object]) -> MatchingResult:
        _ = release
        raise RuntimeError(
            "Spotify auth failed. Re-authenticate or provide a valid access token."
        )


def _release(
    release_id: int, *, artist: str, title: str, year: int
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": ["Rock"],
        "styles": ["Alternative"],
        "thumb_url": None,
        "cover_url": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def _wantlist_entry(
    release_id: int, *, artist: str, title: str, year: int
) -> dict[str, object]:
    return {
        "discogs_release_id": release_id,
        "artist": artist,
        "title": title,
        "year": year,
        "genres": ["Rock"],
        "styles": ["Alternative"],
        "thumb_url": None,
        "cover_url": None,
        "notes": None,
        "added_at": "2026-01-01T00:00:00Z",
        "last_synced_at": "2026-01-01T00:00:00Z",
        "is_active": 1,
    }


def test_run_match_release_persists_mapping(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(
            conn, [_release(1, artist="Nirvana", title="Nevermind", year=1991)]
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _FakeMatchingService)

    result = ensure_mapping.run_match_release(1, threshold=0.7)

    assert result["matched"] is True
    assert result["spotify_album_id"] == "album-1"

    conn = get_connection()
    try:
        mapping = get_spotify_mapping(conn, 1)
    finally:
        conn.close()

    assert mapping is not None
    assert mapping["spotify_album_id"] == "album-1"
    assert mapping["is_override"] is False


def test_run_match_release_retries_rate_limited_matches(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [_release(21, artist="Alpha", title="Retry Single Release", year=1995)],
        )
    finally:
        conn.close()

    _RetryingMatchingService.attempts = {}
    wait_calls: list[float] = []

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _RetryingMatchingService)
    monkeypatch.setattr(
        ensure_mapping.time, "sleep", lambda seconds: wait_calls.append(float(seconds))
    )

    result = ensure_mapping.run_match_release(
        21,
        threshold=0.72,
        max_retries=1,
        backoff_seconds=0.5,
    )

    assert result["matched"] is True
    assert result["spotify_album_id"] == "album-21"
    assert wait_calls == [0.5]


def test_run_match_release_raises_player_api_error_after_retry_exhausted(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [_release(51, artist="Gamma", title="Still Rate Limited", year=1999)],
        )
    finally:
        conn.close()

    wait_calls: list[float] = []
    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(
        ensure_mapping, "MatchingService", _AlwaysRateLimitedMatchingService
    )
    monkeypatch.setattr(
        ensure_mapping.time, "sleep", lambda seconds: wait_calls.append(float(seconds))
    )

    with pytest.raises(PlayerApiError, match="429"):
        ensure_mapping.run_match_release(
            51,
            threshold=0.72,
            max_retries=2,
            backoff_seconds=0.25,
            external_fallback=False,
        )

    assert wait_calls == [0.25, 0.5]


def test_run_match_release_uses_external_fallback_on_rate_limited_error(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [_release(52, artist="Black Sabbath", title="Paranoid", year=1970)],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(
        ensure_mapping, "MatchingService", _AlwaysRateLimitedMatchingService
    )
    monkeypatch.setattr(
        ensure_mapping,
        "resolve_external_fallback_match",
        lambda release, timeout_seconds=8.0: ExternalFallbackMatch(
            spotify_album_id="fallback-52",
            source="bootstrap:test.json",
            confidence=0.74,
            note="Recovered mapping from test fallback.",
        ),
    )

    result = ensure_mapping.run_match_release(
        52,
        threshold=0.72,
        max_retries=0,
        backoff_seconds=0.25,
        external_fallback=True,
    )

    assert result["matched"] is True
    assert result["spotify_album_id"] == "fallback-52"
    assert str(result["source"]).startswith("external_fallback:")
    assert "Recovered mapping from test fallback." in str(result["note"])

    conn = get_connection()
    try:
        mapping = get_spotify_mapping(conn, 52)
    finally:
        conn.close()
    assert mapping is not None
    assert mapping["spotify_album_id"] == "fallback-52"
    assert mapping["is_override"] is False


def test_run_match_release_external_fallback_disabled_raises_player_api_error(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [_release(53, artist="Black Sabbath", title="Paranoid", year=1970)],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(
        ensure_mapping, "MatchingService", _AlwaysRateLimitedMatchingService
    )
    monkeypatch.setattr(
        ensure_mapping,
        "resolve_external_fallback_match",
        lambda release, timeout_seconds=8.0: ExternalFallbackMatch(
            spotify_album_id="fallback-53",
            source="bootstrap:test.json",
            confidence=0.74,
            note="Recovered mapping from test fallback.",
        ),
    )

    with pytest.raises(PlayerApiError, match="429"):
        ensure_mapping.run_match_release(
            53,
            threshold=0.72,
            max_retries=0,
            backoff_seconds=0.25,
            external_fallback=False,
        )


def test_run_match_unmatched_batch_summary(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(1, artist="Nirvana", title="Nevermind", year=1991),
                _release(2, artist="Pixies", title="Doolittle", year=1989),
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _FakeMatchingService)

    summary = ensure_mapping.run_match_unmatched(limit=10)

    assert summary["processed_count"] == 2
    assert summary["matched_count"] == 1
    assert len(summary["results"]) == 2


def test_run_match_unmatched_applies_safe_only_and_queues_review(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(10, artist="Alpha", title="High Confidence", year=1990),
                _release(11, artist="Beta", title="Review Candidate", year=1991),
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _SafePolicyMatchingService)

    summary = ensure_mapping.run_match_unmatched(
        limit=10,
        threshold=0.72,
        auto_apply_threshold=0.90,
    )

    assert summary["processed_count"] == 2
    assert summary["matched_count"] == 1
    assert summary["review_count"] == 1

    conn = get_connection()
    try:
        mapping_10 = get_spotify_mapping(conn, 10)
        mapping_11 = get_spotify_mapping(conn, 11)
    finally:
        conn.close()

    assert mapping_10 is not None
    assert mapping_10["spotify_album_id"] == "album-10"
    assert mapping_11 is None


def test_run_match_audit_scope_wantlist_only_does_not_mix_collection(
    isolated_xdg, monkeypatch
):
    class _AlwaysSafeMatchService:
        def __init__(
            self, spotify_client, *, threshold: float = 0.72, search_limit: int = 10
        ):
            _ = (spotify_client, threshold, search_limit)

        def match_release(self, release: dict[str, object]) -> MatchingResult:
            release_id = int(release["discogs_release_id"])
            album_id = f"album-{release_id}"
            return MatchingResult(
                matched=True,
                discogs_release_id=release_id,
                spotify_album_id=album_id,
                confidence=0.95,
                best_candidate={
                    "id": album_id,
                    "name": f"Candidate {release_id}",
                    "artists": [str(release.get("artist") or "")],
                },
                candidates=[
                    {
                        "id": album_id,
                        "name": f"Candidate {release_id}",
                        "artists": [str(release.get("artist") or "")],
                        "confidence": 0.95,
                    }
                ],
            )

    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [_release(2101, artist="Collection Artist", title="Collection Album", year=1991)],
        )
        upsert_wantlist_entries(
            conn,
            [_wantlist_entry(2102, artist="Wantlist Artist", title="Wantlist Album", year=1992)],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _AlwaysSafeMatchService)

    summary = ensure_mapping.run_match_audit(
        scope="wantlist",
        apply_safe_matches=True,
        resume=False,
        export_report=False,
        request_delay_seconds=0.0,
    )

    assert summary["scope"] == "wantlist"
    assert summary["run_processed_count"] == 1
    run_entries = list(summary.get("run_entries") or [])
    assert len(run_entries) == 1
    assert int(run_entries[0].get("discogs_release_id") or 0) == 2102
    assert run_entries[0].get("scope_source") == "wantlist"

    conn = get_connection()
    try:
        collection_mapping = get_spotify_mapping(conn, 2101)
        wantlist_mapping = get_spotify_mapping(conn, 2102)
    finally:
        conn.close()

    assert collection_mapping is None
    assert wantlist_mapping is not None
    assert wantlist_mapping["spotify_album_id"] == "album-2102"


def test_run_match_audit_resume_scope_mismatch_raises(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [_release(2111, artist="Collection Artist", title="Collection Album", year=1994)],
        )
        upsert_wantlist_entries(
            conn,
            [_wantlist_entry(2112, artist="Wantlist Artist", title="Wantlist Album", year=1995)],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _FakeMatchingService)

    report_path = isolated_xdg["data"] / "reports" / "audit_scope_mismatch.json"
    ensure_mapping.run_match_audit(
        scope="wantlist",
        limit=1,
        resume=False,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
    )

    with pytest.raises(ValueError, match="Requested scope does not match existing report scope"):
        ensure_mapping.run_match_audit(
            scope="collection",
            limit=1,
            resume=True,
            report_path=str(report_path),
            export_report=True,
            request_delay_seconds=0.0,
        )


def test_run_match_audit_resume_backoff_and_report_export(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(21, artist="Alpha", title="Resume First", year=1995),
                _release(22, artist="Beta", title="Resume Second", year=1996),
            ],
        )
    finally:
        conn.close()

    _RetryingMatchingService.attempts = {}
    wait_calls: list[float] = []

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _RetryingMatchingService)
    monkeypatch.setattr(ensure_mapping.time, "sleep", lambda seconds: wait_calls.append(float(seconds)))

    report_path = isolated_xdg["data"] / "reports" / "audit_resume.json"
    first = ensure_mapping.run_match_audit(
        limit=1,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=False,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
        backoff_seconds=1.0,
        max_retries=2,
    )
    assert first["run_processed_count"] == 1
    assert first["run_error_count"] == 0
    assert wait_calls == [1.0]
    assert report_path.exists()

    second = ensure_mapping.run_match_audit(
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=True,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
        backoff_seconds=1.0,
        max_retries=2,
    )
    assert second["resumed_entry_count"] == 1
    assert second["run_processed_count"] == 1
    assert second["processed_count"] == 2
    assert second["run_review_queue_count"] == 1
    assert second["report_path"] == str(report_path)


def test_run_match_audit_resume_retries_prior_error_entries(isolated_xdg, monkeypatch):
    class _FailOnceThenMatch:
        attempts: dict[int, int] = {}

        def __init__(self, spotify_client, *, threshold: float = 0.72, search_limit: int = 10):
            _ = (spotify_client, threshold, search_limit)

        def match_release(self, release: dict[str, object]) -> MatchingResult:
            release_id = int(release["discogs_release_id"])
            attempt = self.attempts.get(release_id, 0)
            self.attempts[release_id] = attempt + 1
            if release_id == 31 and attempt == 0:
                raise RuntimeError("Spotify API request failed (429): Too many requests")
            return MatchingResult(
                matched=True,
                discogs_release_id=release_id,
                spotify_album_id=f"album-{release_id}",
                confidence=0.95,
                best_candidate={"id": f"album-{release_id}", "name": "Retry Match"},
                candidates=[{"id": f"album-{release_id}", "name": "Retry Match"}],
            )

    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(31, artist="Alpha", title="Retry Me", year=2000),
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _FailOnceThenMatch)

    report_path = isolated_xdg["data"] / "reports" / "audit_retry_errors.json"
    first = ensure_mapping.run_match_audit(
        limit=1,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=False,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
        max_retries=0,
    )
    assert first["run_error_count"] == 1

    second = ensure_mapping.run_match_audit(
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=True,
        resume=True,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
        max_retries=0,
        retry_errors_on_resume=True,
    )
    assert second["run_processed_count"] == 1
    assert second["run_error_count"] == 0
    assert second["run_auto_applied_count"] == 1

    conn = get_connection()
    try:
        mapping = get_spotify_mapping(conn, 31)
    finally:
        conn.close()
    assert mapping is not None
    assert mapping["spotify_album_id"] == "album-31"


def test_run_match_audit_marks_auth_errors_non_retryable(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [_release(63, artist="Auth", title="Needs Reauth", year=2005)],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(
        ensure_mapping, "MatchingService", _AlwaysAuthFailingMatchingService
    )

    summary = ensure_mapping.run_match_audit(
        limit=1,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=False,
        export_report=False,
        request_delay_seconds=0.0,
        max_retries=2,
    )

    assert summary["run_processed_count"] == 1
    assert summary["run_error_count"] == 1
    assert summary["run_auth_error_count"] == 1
    assert summary["run_retryable_error_count"] == 0

    run_entries = list(summary.get("run_entries") or [])
    assert len(run_entries) == 1
    assert run_entries[0]["status"] == "error"
    assert run_entries[0]["error_category"] == "auth"
    assert run_entries[0]["error_retryable"] is False


def test_run_match_audit_resume_skips_non_retryable_auth_errors(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [_release(64, artist="Auth", title="Skip Resume Retry", year=2006)],
        )
    finally:
        conn.close()

    report_path = isolated_xdg["data"] / "reports" / "audit_auth_skip_retry.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "discogs_release_id": 64,
                        "status": "error",
                        "error": "Spotify auth failed. Re-authenticate or provide a valid access token.",
                        "error_category": "auth",
                        "error_retryable": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    class _ShouldNotRunMatchingService(_FakeMatchingService):
        def match_release(self, release):  # pragma: no cover - should not run.
            raise AssertionError("auth errors should be skipped on resume retries")

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _ShouldNotRunMatchingService)

    summary = ensure_mapping.run_match_audit(
        limit=1,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=True,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
        max_retries=0,
        retry_errors_on_resume=True,
    )
    assert summary["run_processed_count"] == 0


def test_run_match_audit_compact_output_strips_large_fields(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(61, artist="Alpha", title="Compact Safe", year=2001),
                _release(62, artist="Beta", title="Compact Review", year=2002),
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _SafePolicyMatchingService)

    summary = ensure_mapping.run_match_audit(
        limit=2,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=False,
        export_report=False,
        request_delay_seconds=0.0,
        compact_output=True,
    )

    assert summary["compact_output"] is True
    assert summary["run_processed_count"] == 2
    assert "entries" not in summary
    assert "processed_release_ids" not in summary
    assert "review_queue" not in summary
    assert "safe_auto_candidates" not in summary
    assert "auto_applied" not in summary
    assert "errors" not in summary

    run_entries = list(summary.get("run_entries") or [])
    assert len(run_entries) == 2
    assert all(isinstance(item, dict) for item in run_entries)
    assert all("discogs_release_id" in item for item in run_entries)
    assert all("status" in item for item in run_entries)
    assert all("best_candidate" not in item for item in run_entries)
    assert all("candidates" not in item for item in run_entries)


def test_run_match_audit_writes_in_batch_progress_log(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(71, artist="Gamma", title="Progress Logging", year=2003),
            ],
        )
    finally:
        conn.close()

    wait_calls: list[float] = []
    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(
        ensure_mapping, "MatchingService", _AlwaysRateLimitedMatchingService
    )
    monkeypatch.setattr(
        ensure_mapping.time, "sleep", lambda seconds: wait_calls.append(float(seconds))
    )

    progress_log = isolated_xdg["data"] / "reports" / "audit_progress.log"
    summary = ensure_mapping.run_match_audit(
        limit=1,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=False,
        export_report=False,
        request_delay_seconds=0.0,
        backoff_seconds=0.25,
        max_retries=1,
        progress_log_path=str(progress_log),
    )

    assert summary["run_error_count"] == 1
    assert wait_calls == [0.25]
    assert progress_log.exists()
    progress_text = progress_log.read_text(encoding="utf-8")
    assert "event=start" in progress_text
    assert "event=retry_wait" in progress_text
    assert "event=complete" in progress_text
    assert "release_id=71" in progress_text


def test_run_match_audit_resume_limit_advances_past_completed_entries(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(81, artist="Alpha", title="Completed First", year=2001),
                _release(82, artist="Beta", title="Should Advance", year=2002),
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _FakeMatchingService)

    report_path = isolated_xdg["data"] / "reports" / "audit_limit_resume.json"
    first = ensure_mapping.run_match_audit(
        limit=1,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=False,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
    )
    assert first["run_processed_count"] == 1

    second = ensure_mapping.run_match_audit(
        limit=1,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=True,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
    )
    assert second["run_processed_count"] == 1
    run_entries = list(second.get("run_entries") or [])
    assert len(run_entries) == 1
    assert int(run_entries[0].get("discogs_release_id") or 0) == 82


def test_run_match_audit_resume_limit_prioritizes_fresh_before_retry_errors(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(91, artist="Alpha", title="Prior Error", year=2001),
                _release(92, artist="Beta", title="Fresh Release", year=2002),
            ],
        )
    finally:
        conn.close()

    report_path = isolated_xdg["data"] / "reports" / "audit_retry_order.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "discogs_release_id": 91,
                        "status": "error",
                        "error": "Spotify API request failed (429): Too many requests",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _FakeMatchingService)

    summary = ensure_mapping.run_match_audit(
        limit=1,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=True,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
        retry_errors_on_resume=True,
    )
    assert summary["run_processed_count"] == 1
    run_entries = list(summary.get("run_entries") or [])
    assert len(run_entries) == 1
    assert int(run_entries[0].get("discogs_release_id") or 0) == 92


def test_run_match_audit_resume_limit_rotates_oldest_retry_error_first(
    isolated_xdg, monkeypatch
):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(101, artist="Alpha", title="Older Error", year=2001),
                _release(102, artist="Beta", title="Newer Error", year=2002),
            ],
        )
    finally:
        conn.close()

    report_path = isolated_xdg["data"] / "reports" / "audit_retry_rotation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "discogs_release_id": 101,
                        "status": "error",
                        "checked_at": "2026-02-12T00:00:00+00:00",
                        "error": "Spotify API request failed (429): Too many requests",
                    },
                    {
                        "discogs_release_id": 102,
                        "status": "error",
                        "checked_at": "2026-02-13T00:00:00+00:00",
                        "error": "Spotify API request failed (429): Too many requests",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(
        ensure_mapping, "MatchingService", _AlwaysRateLimitedMatchingService
    )
    monkeypatch.setattr(ensure_mapping.time, "sleep", lambda seconds: None)

    first = ensure_mapping.run_match_audit(
        limit=1,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=True,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
        max_retries=0,
        retry_errors_on_resume=True,
    )
    first_run_entries = list(first.get("run_entries") or [])
    assert len(first_run_entries) == 1
    assert int(first_run_entries[0].get("discogs_release_id") or 0) == 101

    second = ensure_mapping.run_match_audit(
        limit=1,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=True,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
        max_retries=0,
        retry_errors_on_resume=True,
    )
    second_run_entries = list(second.get("run_entries") or [])
    assert len(second_run_entries) == 1
    assert int(second_run_entries[0].get("discogs_release_id") or 0) == 102


def test_run_match_audit_review_apply_reject_and_list(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(
            conn,
            [
                _release(10, artist="Alpha", title="Safe Candidate", year=2001),
                _release(11, artist="Beta", title="Review Candidate", year=2002),
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(ensure_mapping, "MatchingService", _SafePolicyMatchingService)

    report_path = isolated_xdg["data"] / "reports" / "audit_review.json"
    summary = ensure_mapping.run_match_audit(
        limit=2,
        review_threshold=0.72,
        auto_apply_threshold=0.90,
        apply_safe_matches=False,
        resume=False,
        report_path=str(report_path),
        export_report=True,
        request_delay_seconds=0.0,
    )
    assert summary["run_review_queue_count"] == 1
    assert summary["run_safe_auto_candidate_count"] == 1

    listing = ensure_mapping.run_match_audit_review_list(
        report_path=str(report_path),
        limit=10,
    )
    assert listing["review_count"] == 2

    apply_result = ensure_mapping.run_match_audit_review_action(
        action="apply",
        report_path=str(report_path),
        release_ids=[11],
        apply_all=False,
    )
    assert apply_result["updated_count"] == 1
    assert apply_result["run_manual_applied_count"] == 1

    reject_result = ensure_mapping.run_match_audit_review_action(
        action="reject",
        report_path=str(report_path),
        release_ids=[10],
        apply_all=False,
    )
    assert reject_result["updated_count"] == 1
    assert reject_result["run_manual_rejected_count"] == 1

    conn = get_connection()
    try:
        mapping_11 = get_spotify_mapping(conn, 11)
        mapping_10 = get_spotify_mapping(conn, 10)
    finally:
        conn.close()

    assert mapping_11 is not None
    assert mapping_11["spotify_album_id"] == "album-11"
    assert mapping_10 is None

    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    entries = report_payload.get("entries")
    assert isinstance(entries, list)
    statuses = {
        int(item["discogs_release_id"]): str(item.get("status") or "")
        for item in entries
        if isinstance(item, dict) and isinstance(item.get("discogs_release_id"), int)
    }
    assert statuses[11] == "manual_applied"
    assert statuses[10] == "manual_rejected"


def test_run_match_override_and_preserve_override(isolated_xdg, monkeypatch):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(3, artist="U2", title="Boy", year=1980)])
    finally:
        conn.close()

    override = ensure_mapping.run_match_override(3, "spotify:album:boy123")
    assert override["spotify_album_id"] == "boy123"
    assert override["is_override"] is True

    class _ShouldNotBeCalledMatchingService(_FakeMatchingService):
        def match_release(
            self, release
        ):  # pragma: no cover - this should never execute
            raise AssertionError("match_release should not run for override mappings")

    monkeypatch.setattr(ensure_mapping, "get_player_backend", lambda: _FakeBackend())
    monkeypatch.setattr(
        ensure_mapping, "MatchingService", _ShouldNotBeCalledMatchingService
    )

    result = ensure_mapping.run_match_release(3)
    assert result["source"] == "override"
    assert result["spotify_album_id"] == "boy123"
    assert result["matched"] is True


def test_run_match_override_accepts_open_spotify_album_url(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(conn, [_release(4, artist="Blur", title="Parklife", year=1994)])
    finally:
        conn.close()

    result = ensure_mapping.run_match_override(
        4,
        "https://open.spotify.com/album/4Z8W4fKeB5YxbusRsdQVPb?si=abc123",
    )
    assert result["spotify_album_id"] == "4Z8W4fKeB5YxbusRsdQVPb"


def test_run_match_override_rejects_invalid_album_id(isolated_xdg):
    conn = get_connection()
    try:
        upsert_releases(
            conn, [_release(5, artist="The Cure", title="Disintegration", year=1989)]
        )
    finally:
        conn.close()

    with pytest.raises(ValueError):
        ensure_mapping.run_match_override(5, "spotify:album:bad-id!")
