#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_AUTH=0
RELEASE_ID="${SPOTIFY_SMOKE_RELEASE_ID:-}"
AUTH_TIMEOUT_SECONDS="${SPOTIFY_SMOKE_AUTH_TIMEOUT_SECONDS:-240}"

usage() {
  cat <<'TXT'
Usage: ./scripts/spotify_live_smoke.sh [--auth] [--release-id <discogs_release_id>]

Live Spotify smoke checks:
1) Validate Spotify capability/config state.
2) Optionally run interactive auth (--auth).
3) Validate devices API path.
4) Validate dry playback/open fallback path.

Environment overrides:
  PYTHON_BIN                       Python executable (default: python3)
  SPOTIFY_SMOKE_RELEASE_ID         Explicit release id for play --open smoke check
  SPOTIFY_SMOKE_AUTH_TIMEOUT_SECONDS OAuth timeout when --auth is used (default: 240)
TXT
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --auth)
      RUN_AUTH=1
      shift
      ;;
    --release-id)
      if [[ $# -lt 2 ]]; then
        echo "--release-id requires a value" >&2
        exit 2
      fi
      RELEASE_ID="$2"
      shift 2
      ;;
    --help|-h)
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

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python executable not found: $PYTHON_BIN" >&2
  exit 1
fi

LAST_CMD_OUTPUT=""
LAST_CMD_RC=0

run_capture() {
  local tmp_file
  tmp_file="$(mktemp)"
  set +e
  "$@" >"$tmp_file" 2>&1
  LAST_CMD_RC=$?
  set -e
  LAST_CMD_OUTPUT="$(cat "$tmp_file")"
  rm -f "$tmp_file"
}

parse_status() {
  local status_json="$1"
  mapfile -t STATUS_FIELDS < <(
    STATUS_JSON_INPUT="$status_json" "$PYTHON_BIN" - <<'PY'
import json
import os

data = json.loads(os.environ["STATUS_JSON_INPUT"])
cap = data.get("spotify_capability") or {}
print("1" if cap.get("addon_available") else "0")
print("1" if cap.get("configured") else "0")
print(str(cap.get("action_label") or ""))
last_spin = data.get("last_spin_release_id")
print("" if last_spin is None else str(last_spin))
PY
  )
}

parse_first_release_id() {
  local list_json="$1"
  LIST_JSON_INPUT="$list_json" "$PYTHON_BIN" - <<'PY'
import json
import os

items = json.loads(os.environ["LIST_JSON_INPUT"])
if isinstance(items, list) and items:
    value = items[0].get("discogs_release_id")
    if value is not None:
        print(str(value))
PY
}

parse_device_count() {
  local devices_json="$1"
  DEVICES_JSON_INPUT="$devices_json" "$PYTHON_BIN" - <<'PY'
import json
import os

items = json.loads(os.environ["DEVICES_JSON_INPUT"])
print(len(items) if isinstance(items, list) else 0)
PY
}

parse_play_result() {
  local play_json="$1"
  mapfile -t PLAY_FIELDS < <(
    PLAY_JSON_INPUT="$play_json" "$PYTHON_BIN" - <<'PY'
import json
import os

item = json.loads(os.environ["PLAY_JSON_INPUT"])
print("1" if item.get("playback_started") else "0")
print(str(item.get("fallback_open_url") or ""))
print(str(item.get("fallback_reason") or ""))
PY
  )
}

echo "Running Spotify smoke check: status"
run_capture "$PYTHON_BIN" -m discogs_player.main status --json
if [[ "$LAST_CMD_RC" -ne 0 ]]; then
  echo "status command failed:" >&2
  echo "$LAST_CMD_OUTPUT" >&2
  exit "$LAST_CMD_RC"
fi
STATUS_JSON="$LAST_CMD_OUTPUT"
parse_status "$STATUS_JSON"

ADDON_AVAILABLE="${STATUS_FIELDS[0]}"
CONFIGURED="${STATUS_FIELDS[1]}"
ACTION_LABEL="${STATUS_FIELDS[2]}"
LAST_SPIN_RELEASE_ID="${STATUS_FIELDS[3]}"

if [[ "$ADDON_AVAILABLE" != "1" ]]; then
  echo "Spotify addon unavailable. Install plus profile: pip install -e \".[spotify]\"" >&2
  exit 1
fi

if [[ "$CONFIGURED" != "1" ]]; then
  if [[ "$RUN_AUTH" -ne 1 ]]; then
    echo "Spotify is not configured ($ACTION_LABEL)." >&2
    echo "Re-run with --auth to complete OAuth before smoke checks." >&2
    exit 3
  fi

  echo "Running Spotify OAuth auth flow (--auth)"
  "$PYTHON_BIN" -m discogs_player.main auth spotify \
    --open-browser \
    --manual \
    --timeout-seconds "$AUTH_TIMEOUT_SECONDS"

  echo "Re-checking Spotify status after auth"
  run_capture "$PYTHON_BIN" -m discogs_player.main status --json
  if [[ "$LAST_CMD_RC" -ne 0 ]]; then
    echo "status command failed after auth:" >&2
    echo "$LAST_CMD_OUTPUT" >&2
    exit "$LAST_CMD_RC"
  fi
  STATUS_JSON="$LAST_CMD_OUTPUT"
  parse_status "$STATUS_JSON"
  CONFIGURED="${STATUS_FIELDS[1]}"
  ACTION_LABEL="${STATUS_FIELDS[2]}"
  LAST_SPIN_RELEASE_ID="${STATUS_FIELDS[3]}"

  if [[ "$CONFIGURED" != "1" ]]; then
    echo "Spotify still not configured after auth ($ACTION_LABEL)." >&2
    exit 3
  fi
fi

echo "Running Spotify smoke check: devices"
run_capture "$PYTHON_BIN" -m discogs_player.main devices --json
if [[ "$LAST_CMD_RC" -ne 0 ]]; then
  echo "devices command failed:" >&2
  echo "$LAST_CMD_OUTPUT" >&2
  exit "$LAST_CMD_RC"
fi
DEVICES_JSON="$LAST_CMD_OUTPUT"
DEVICE_COUNT="$(parse_device_count "$DEVICES_JSON")"

if [[ -z "$RELEASE_ID" && -n "$LAST_SPIN_RELEASE_ID" ]]; then
  RELEASE_ID="$LAST_SPIN_RELEASE_ID"
fi

if [[ -z "$RELEASE_ID" ]]; then
  run_capture "$PYTHON_BIN" -m discogs_player.main list --limit 1 --json
  if [[ "$LAST_CMD_RC" -ne 0 ]]; then
    echo "list command failed while choosing a release id:" >&2
    echo "$LAST_CMD_OUTPUT" >&2
    exit "$LAST_CMD_RC"
  fi
  RELEASE_ID="$(parse_first_release_id "$LAST_CMD_OUTPUT")"
fi

if [[ -z "$RELEASE_ID" ]]; then
  echo "Spotify is not configured for release smoke checks (no local release id)." >&2
  echo "Unable to choose a release id for play --open smoke check." >&2
  echo "Set SPOTIFY_SMOKE_RELEASE_ID or run sync first." >&2
  exit 3
fi

if ! [[ "$RELEASE_ID" =~ ^[0-9]+$ ]]; then
  echo "Release id must be numeric: $RELEASE_ID" >&2
  exit 2
fi

echo "Running Spotify smoke check: play --open (release_id=${RELEASE_ID})"
run_capture "$PYTHON_BIN" -m discogs_player.main play "$RELEASE_ID" --open --json
if [[ "$LAST_CMD_RC" -ne 0 ]]; then
  echo "play command failed:" >&2
  echo "$LAST_CMD_OUTPUT" >&2
  exit "$LAST_CMD_RC"
fi
PLAY_JSON="$LAST_CMD_OUTPUT"
parse_play_result "$PLAY_JSON"
PLAYBACK_STARTED="${PLAY_FIELDS[0]}"
FALLBACK_OPEN_URL="${PLAY_FIELDS[1]}"
FALLBACK_REASON="${PLAY_FIELDS[2]}"

if [[ "$PLAYBACK_STARTED" != "1" && -z "$FALLBACK_OPEN_URL" ]]; then
  echo "play --open did not start playback and did not return fallback_open_url." >&2
  echo "$PLAY_JSON" >&2
  exit 5
fi

AUTH_ATTEMPTED="false"
if [[ "$RUN_AUTH" -eq 1 ]]; then
  AUTH_ATTEMPTED="true"
fi

export AUTH_ATTEMPTED
export DEVICE_COUNT
export FALLBACK_OPEN_URL
export FALLBACK_REASON
export PLAYBACK_STARTED
export RELEASE_ID

"$PYTHON_BIN" - <<'PY'
import json
import os

report = {
    "ok": True,
    "auth_attempted": os.environ["AUTH_ATTEMPTED"] == "true",
    "device_count": int(os.environ["DEVICE_COUNT"]),
    "playback_started": os.environ["PLAYBACK_STARTED"] == "1",
    "fallback_open_url": os.environ["FALLBACK_OPEN_URL"] or None,
    "fallback_reason": os.environ["FALLBACK_REASON"] or None,
    "release_id": int(os.environ["RELEASE_ID"]),
}
print(json.dumps(report, indent=2, sort_keys=True))
PY
