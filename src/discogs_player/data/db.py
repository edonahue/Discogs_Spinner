"""SQLite database initialization and connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from discogs_player.core.paths import db_path, ensure_runtime_dirs

SCHEMA_SQL = """
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
"""


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    ensure_runtime_dirs()
    target = path or db_path()
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn
