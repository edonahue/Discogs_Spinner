"""SQLite database initialization and connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from discogs_player.core.paths import db_path, ensure_runtime_dirs

MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS releases (
            discogs_release_id INTEGER PRIMARY KEY,
            artist TEXT,
            title TEXT,
            year INTEGER,
            genres TEXT,
            styles TEXT,
            thumb_url TEXT,
            cover_url TEXT,
            added_at TEXT,
            last_synced_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS spotify_mapping (
            discogs_release_id INTEGER PRIMARY KEY,
            spotify_album_id TEXT,
            confidence REAL,
            last_checked_at TEXT,
            is_override INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(discogs_release_id) REFERENCES releases(discogs_release_id)
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_releases_is_active ON releases(is_active);
        CREATE INDEX IF NOT EXISTS idx_releases_year ON releases(year);
        CREATE INDEX IF NOT EXISTS idx_releases_artist_title ON releases(artist, title);
        """,
    ),
    (
        2,
        """
        CREATE TABLE IF NOT EXISTS wantlist (
            discogs_release_id INTEGER PRIMARY KEY,
            artist TEXT,
            title TEXT,
            year INTEGER,
            genres TEXT,
            styles TEXT,
            thumb_url TEXT,
            cover_url TEXT,
            notes TEXT,
            added_at TEXT,
            last_synced_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_wantlist_is_active ON wantlist(is_active);
        CREATE INDEX IF NOT EXISTS idx_wantlist_year ON wantlist(year);
        CREATE INDEX IF NOT EXISTS idx_wantlist_artist_title ON wantlist(artist, title);
        """,
    ),
    (
        3,
        """
        CREATE TABLE IF NOT EXISTS market_prices (
            discogs_release_id INTEGER PRIMARY KEY,
            lowest REAL,
            median REAL,
            highest REAL,
            currency TEXT,
            last_updated_at TEXT,
            FOREIGN KEY(discogs_release_id) REFERENCES releases(discogs_release_id)
        );

        CREATE INDEX IF NOT EXISTS idx_market_prices_last_updated_at
          ON market_prices(last_updated_at);
        CREATE INDEX IF NOT EXISTS idx_market_prices_currency
          ON market_prices(currency);
        """,
    ),
    (
        4,
        """
        CREATE TABLE IF NOT EXISTS market_value_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TEXT NOT NULL,
            active_release_count INTEGER NOT NULL,
            priced_release_count INTEGER NOT NULL,
            unpriced_release_count INTEGER NOT NULL,
            total_lowest REAL NOT NULL DEFAULT 0.0,
            total_median REAL NOT NULL DEFAULT 0.0,
            total_highest REAL NOT NULL DEFAULT 0.0
        );

        CREATE INDEX IF NOT EXISTS idx_market_value_snapshots_captured_at
          ON market_value_snapshots(captured_at);
        """,
    ),
    (
        5,
        """
        CREATE TABLE IF NOT EXISTS release_tracklist_cache (
            discogs_release_id INTEGER PRIMARY KEY,
            track_count INTEGER NOT NULL DEFAULT 0,
            audio_track_count INTEGER NOT NULL DEFAULT 0,
            last_refreshed_at TEXT NOT NULL,
            FOREIGN KEY(discogs_release_id) REFERENCES releases(discogs_release_id)
        );

        CREATE TABLE IF NOT EXISTS release_tracks (
            discogs_release_id INTEGER NOT NULL,
            seq INTEGER NOT NULL,
            position TEXT,
            title TEXT,
            duration TEXT,
            type TEXT,
            is_audio_track INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(discogs_release_id, seq),
            FOREIGN KEY(discogs_release_id) REFERENCES releases(discogs_release_id)
        );

        CREATE INDEX IF NOT EXISTS idx_release_tracklist_cache_last_refreshed_at
          ON release_tracklist_cache(last_refreshed_at);
        CREATE INDEX IF NOT EXISTS idx_release_tracks_release_id_seq
          ON release_tracks(discogs_release_id, seq);
        """,
    ),
    (
        6,
        """
        CREATE TABLE IF NOT EXISTS wantlist_market_prices (
            discogs_release_id INTEGER PRIMARY KEY,
            lowest REAL,
            median REAL,
            highest REAL,
            currency TEXT,
            last_updated_at TEXT,
            FOREIGN KEY(discogs_release_id) REFERENCES wantlist(discogs_release_id)
        );

        CREATE INDEX IF NOT EXISTS idx_wantlist_market_prices_last_updated_at
          ON wantlist_market_prices(last_updated_at);
        CREATE INDEX IF NOT EXISTS idx_wantlist_market_prices_currency
          ON wantlist_market_prices(currency);

        CREATE TABLE IF NOT EXISTS wantlist_tracklist_cache (
            discogs_release_id INTEGER PRIMARY KEY,
            track_count INTEGER NOT NULL DEFAULT 0,
            audio_track_count INTEGER NOT NULL DEFAULT 0,
            last_refreshed_at TEXT NOT NULL,
            FOREIGN KEY(discogs_release_id) REFERENCES wantlist(discogs_release_id)
        );

        CREATE TABLE IF NOT EXISTS wantlist_tracks (
            discogs_release_id INTEGER NOT NULL,
            seq INTEGER NOT NULL,
            position TEXT,
            title TEXT,
            duration TEXT,
            type TEXT,
            is_audio_track INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(discogs_release_id, seq),
            FOREIGN KEY(discogs_release_id) REFERENCES wantlist(discogs_release_id)
        );

        CREATE INDEX IF NOT EXISTS idx_wantlist_tracklist_cache_last_refreshed_at
          ON wantlist_tracklist_cache(last_refreshed_at);
        CREATE INDEX IF NOT EXISTS idx_wantlist_tracks_release_id_seq
          ON wantlist_tracks(discogs_release_id, seq);
        """,
    ),
    (
        7,
        """
        CREATE TABLE IF NOT EXISTS release_stats (
            discogs_release_id INTEGER PRIMARY KEY,
            num_for_sale INTEGER,
            lowest_price REAL,
            community_have INTEGER,
            community_want INTEGER,
            rating_count INTEGER,
            rating_average REAL,
            last_updated_at TEXT,
            FOREIGN KEY(discogs_release_id) REFERENCES releases(discogs_release_id)
        );

        CREATE TABLE IF NOT EXISTS wantlist_stats (
            discogs_release_id INTEGER PRIMARY KEY,
            num_for_sale INTEGER,
            lowest_price REAL,
            community_have INTEGER,
            community_want INTEGER,
            rating_count INTEGER,
            rating_average REAL,
            last_updated_at TEXT,
            FOREIGN KEY(discogs_release_id) REFERENCES wantlist(discogs_release_id)
        );

        CREATE INDEX IF NOT EXISTS idx_release_stats_last_updated_at
          ON release_stats(last_updated_at);
        CREATE INDEX IF NOT EXISTS idx_wantlist_stats_last_updated_at
          ON wantlist_stats(last_updated_at);
        """,
    ),
    (
        8,
        """
        CREATE TABLE spotify_mapping_new (
            discogs_release_id INTEGER PRIMARY KEY,
            spotify_album_id TEXT,
            confidence REAL,
            last_checked_at TEXT,
            is_override INTEGER NOT NULL DEFAULT 0
        );

        INSERT INTO spotify_mapping_new(
            discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override
        )
        SELECT
            discogs_release_id, spotify_album_id, confidence, last_checked_at, is_override
        FROM spotify_mapping;

        DROP TABLE spotify_mapping;

        ALTER TABLE spotify_mapping_new RENAME TO spotify_mapping;
        """,
    ),
    (
        9,
        """
        ALTER TABLE spotify_mapping ADD COLUMN provider_id TEXT NOT NULL DEFAULT 'spotify';

        CREATE INDEX IF NOT EXISTS idx_spotify_mapping_provider_id
          ON spotify_mapping(provider_id);
        """,
    ),
)
LATEST_SCHEMA_VERSION = MIGRATIONS[-1][0]


def _get_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    if not row:
        return 0
    return int(row[0])


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    # SQLite PRAGMA doesn't support bind parameters; int() is the injection guard.
    conn.execute(f"PRAGMA user_version = {int(version)}")


def apply_migrations(conn: sqlite3.Connection) -> None:
    version = _get_schema_version(conn)
    if version >= LATEST_SCHEMA_VERSION:
        return

    for target_version, sql in MIGRATIONS:
        if target_version <= version:
            continue
        conn.executescript(sql)
        _set_schema_version(conn, target_version)
        conn.commit()
        version = target_version


def init_schema(conn: sqlite3.Connection) -> None:
    apply_migrations(conn)


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    ensure_runtime_dirs()
    target = path or db_path()
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    init_schema(conn)
    return conn
