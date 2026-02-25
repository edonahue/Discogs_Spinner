#!/usr/bin/env bash
set -euo pipefail

DEFAULT_DB_PATH="${XDG_DATA_HOME:-$HOME/.local/share}/discogs_player/app.db"
DB_PATH="$DEFAULT_DB_PATH"
LIMIT="${SPOTIFY_MAPPING_REPORT_LIMIT:-20}"

usage() {
  cat <<'TXT'
Usage: ./scripts/spotify_mapping_report.sh [options]

Show persisted Discogs->Spotify mapping status from the local SQLite database.

Options:
  --db <path>      SQLite DB path (default: ${XDG_DATA_HOME:-$HOME/.local/share}/discogs_player/app.db)
  --limit <n>      Number of latest mappings to show (default: 20)
  -h, --help       Show this help
TXT
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --db)
      DB_PATH="${2:-}"
      shift 2
      ;;
    --limit)
      LIMIT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 not found. Install it with: sudo apt install sqlite3" >&2
  exit 1
fi

if [[ ! "$LIMIT" =~ ^[0-9]+$ ]] || [[ "$LIMIT" -lt 1 ]]; then
  echo "Invalid --limit value: ${LIMIT} (expected integer >= 1)" >&2
  exit 2
fi

if [[ ! -f "$DB_PATH" ]]; then
  echo "DB not found: $DB_PATH" >&2
  exit 1
fi

echo "DB: $DB_PATH"
echo
echo "== Summary =="
sqlite3 -readonly -header -column "$DB_PATH" "
SELECT
  (SELECT COUNT(*) FROM releases WHERE is_active = 1) AS active_releases,
  (SELECT COUNT(*) FROM releases r
     LEFT JOIN spotify_mapping m ON m.discogs_release_id = r.discogs_release_id
    WHERE r.is_active = 1
      AND m.spotify_album_id IS NOT NULL
      AND TRIM(m.spotify_album_id) <> '') AS mapped_active_releases,
  (SELECT COUNT(*) FROM releases r
     LEFT JOIN spotify_mapping m ON m.discogs_release_id = r.discogs_release_id
    WHERE r.is_active = 1
      AND (m.spotify_album_id IS NULL OR TRIM(m.spotify_album_id) = '')) AS unmatched_active_releases,
  (SELECT COUNT(*) FROM spotify_mapping
    WHERE spotify_album_id IS NOT NULL AND TRIM(spotify_album_id) <> '') AS persisted_mappings_total;
"

echo
echo "== Latest ${LIMIT} persisted mappings =="
sqlite3 -readonly -header -column "$DB_PATH" "
SELECT
  m.discogs_release_id,
  COALESCE(r.artist, w.artist, 'Unknown') AS artist,
  COALESCE(r.title, w.title, 'Unknown') AS title,
  m.spotify_album_id,
  ROUND(COALESCE(m.confidence, 0), 3) AS confidence,
  m.is_override,
  m.last_checked_at
FROM spotify_mapping m
LEFT JOIN releases r ON r.discogs_release_id = m.discogs_release_id
LEFT JOIN wantlist w ON w.discogs_release_id = m.discogs_release_id
WHERE m.spotify_album_id IS NOT NULL
  AND TRIM(m.spotify_album_id) <> ''
ORDER BY datetime(COALESCE(m.last_checked_at, '1970-01-01T00:00:00Z')) DESC
LIMIT ${LIMIT};
"
