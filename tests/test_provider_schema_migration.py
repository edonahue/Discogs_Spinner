"""Tests for migration 9: provider_id column added to spotify_mapping."""

from __future__ import annotations

import sqlite3

import pytest

from discogs_player.data.db import apply_migrations, LATEST_SCHEMA_VERSION, MIGRATIONS


def _fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def test_latest_schema_version_is_at_least_9():
    assert LATEST_SCHEMA_VERSION >= 9


def test_migration_9_adds_provider_id_column():
    conn = _fresh_conn()
    apply_migrations(conn)
    # Verify column exists
    cols = {row[1] for row in conn.execute("PRAGMA table_info(spotify_mapping)")}
    assert "provider_id" in cols


def test_migration_9_provider_id_defaults_to_spotify():
    conn = _fresh_conn()
    apply_migrations(conn)

    # Insert a row without specifying provider_id
    conn.execute(
        """
        INSERT INTO spotify_mapping(discogs_release_id, spotify_album_id, confidence,
            last_checked_at, is_override)
        VALUES (1, 'spotify:album:abc', 0.95, '2026-01-01', 0)
        """
    )
    conn.commit()

    row = conn.execute(
        "SELECT provider_id FROM spotify_mapping WHERE discogs_release_id = 1"
    ).fetchone()
    assert row is not None
    assert row[0] == "spotify"


def test_migration_9_index_created():
    conn = _fresh_conn()
    apply_migrations(conn)
    indexes = {
        row[1]
        for row in conn.execute("PRAGMA index_list(spotify_mapping)")
    }
    assert "idx_spotify_mapping_provider_id" in indexes


def test_upsert_spotify_mapping_stores_provider_id():
    from discogs_player.data.repo import upsert_spotify_mapping

    conn = _fresh_conn()
    apply_migrations(conn)

    upsert_spotify_mapping(
        conn,
        discogs_release_id=42,
        spotify_album_id="MPREb_abc",
        confidence=0.9,
        last_checked_at="2026-03-07",
        provider_id="youtube_music",
    )

    row = conn.execute(
        "SELECT provider_id FROM spotify_mapping WHERE discogs_release_id = 42"
    ).fetchone()
    assert row is not None
    assert row[0] == "youtube_music"


def test_upsert_spotify_mapping_defaults_to_spotify():
    from discogs_player.data.repo import upsert_spotify_mapping

    conn = _fresh_conn()
    apply_migrations(conn)

    upsert_spotify_mapping(
        conn,
        discogs_release_id=99,
        spotify_album_id="spotify:album:xyz",
        confidence=0.85,
        last_checked_at="2026-03-07",
    )

    row = conn.execute(
        "SELECT provider_id FROM spotify_mapping WHERE discogs_release_id = 99"
    ).fetchone()
    assert row is not None
    assert row[0] == "spotify"
