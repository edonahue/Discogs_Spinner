#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}"
PYTHON_BIN="${PYTHON_BIN:-}"
BATCH_LIMIT="${DP_SPOTIFY_MAP_BATCH_LIMIT:-1}"
REQUEST_DELAY_SECONDS="${DP_SPOTIFY_MAP_REQUEST_DELAY_SECONDS:-0.35}"
MAX_RETRIES="${DP_SPOTIFY_MAP_MAX_RETRIES:-2}"
BACKOFF_SECONDS="${DP_SPOTIFY_MAP_BACKOFF_SECONDS:-3.0}"
LOOP_SLEEP_SECONDS="${DP_SPOTIFY_MAP_LOOP_SLEEP_SECONDS:-20}"
MATCH_SCOPE="${DP_SPOTIFY_MAP_SCOPE:-collection}"
MAX_BATCHES="${DP_SPOTIFY_MAP_MAX_BATCHES:-0}"
HEARTBEAT_SECONDS="${DP_SPOTIFY_MAP_HEARTBEAT_SECONDS:-15}"
STATUS_TIMEOUT_SECONDS="${DP_SPOTIFY_MAP_STATUS_TIMEOUT_SECONDS:-60}"
BOOTSTRAP_TIMEOUT_SECONDS="${DP_SPOTIFY_MAP_BOOTSTRAP_TIMEOUT_SECONDS:-600}"
AUDIT_TIMEOUT_SECONDS="${DP_SPOTIFY_MAP_AUDIT_TIMEOUT_SECONDS:-7200}"
API_MAX_RETRIES="${DP_SPOTIFY_API_MAX_RETRIES:-1}"
API_BACKOFF_SECONDS="${DP_SPOTIFY_API_BACKOFF_SECONDS:-1.0}"
API_MAX_SLEEP_SECONDS="${DP_SPOTIFY_API_MAX_SLEEP_SECONDS:-15.0}"
API_JITTER_SECONDS="${DP_SPOTIFY_API_JITTER_SECONDS:-0.1}"
API_RETRY_AFTER_CAP_SECONDS_EXPLICIT=0
if [[ -n "${DP_SPOTIFY_API_RETRY_AFTER_CAP_SECONDS+x}" ]]; then
  API_RETRY_AFTER_CAP_SECONDS_EXPLICIT=1
fi
API_RETRY_AFTER_CAP_SECONDS="${DP_SPOTIFY_API_RETRY_AFTER_CAP_SECONDS:-15.0}"
APPLY_SAFE_MATCHES="${DP_SPOTIFY_MAP_APPLY_SAFE_MATCHES:-1}"
RETRY_ERRORS="${DP_SPOTIFY_MAP_RETRY_ERRORS:-0}"
STOP_ON_AUTH_ERRORS="${DP_SPOTIFY_MAP_STOP_ON_AUTH_ERRORS:-1}"
RATE_LIMIT_COOLDOWN_SECONDS="${DP_SPOTIFY_MAP_RATE_LIMIT_COOLDOWN_SECONDS:-120}"
RETRY_AFTER_CAP_SECONDS_EXPLICIT=0
if [[ -n "${DP_SPOTIFY_MAP_RETRY_AFTER_CAP_SECONDS+x}" ]]; then
  RETRY_AFTER_CAP_SECONDS_EXPLICIT=1
fi
RETRY_AFTER_CAP_SECONDS="${DP_SPOTIFY_MAP_RETRY_AFTER_CAP_SECONDS:-900}"
RATE_LIMIT_HARD_STOP_SECONDS="${DP_SPOTIFY_MAP_RATE_LIMIT_HARD_STOP_SECONDS:-3600}"
RESET_REPORT="${DP_SPOTIFY_MAP_RESET_REPORT:-0}"
REPORT_PATH_EXPLICIT=0
if [[ -n "${DP_SPOTIFY_MAP_REPORT_PATH+x}" ]]; then
  REPORT_PATH_EXPLICIT=1
fi
REPORT_PATH="${DP_SPOTIFY_MAP_REPORT_PATH:-${DATA_ROOT}/discogs_player/reports/spotify_match_audit_slow.json}"
LOG_PATH="${DP_SPOTIFY_MAP_LOG_PATH:-${STATE_ROOT}/discogs_player/spotify_catalog_map_slow.log}"
LOCK_PATH="${DP_SPOTIFY_MAP_LOCK_PATH:-${STATE_ROOT}/discogs_player/spotify_catalog_map_slow.lock}"
AUDIT_COMPACT_OUTPUT="${DP_SPOTIFY_MAP_AUDIT_COMPACT_OUTPUT:-1}"
BOOTSTRAP_INPUT="${DP_SPOTIFY_BOOTSTRAP_INPUT:-}"
BOOTSTRAP_FORMAT="${DP_SPOTIFY_BOOTSTRAP_FORMAT:-auto}"
BOOTSTRAP_CONFLICT_MODE="${DP_SPOTIFY_BOOTSTRAP_CONFLICT_MODE:-merge}"
BOOTSTRAP_DRY_RUN="${DP_SPOTIFY_BOOTSTRAP_DRY_RUN:-0}"

usage() {
  cat <<'TXT'
Usage: ./scripts/spotify_catalog_map_slow.sh [options]

Purpose:
  Slowly build Discogs->Spotify mappings outside normal interactive app flow.
  Runs resumable audit batches with explicit rate-limit tuning.

Options:
  --bootstrap-input <path>         Optional bootstrap JSON/CSV to import first
  --bootstrap-format <value>       auto|discofy|direct|discogs-to-spotify (default: auto)
  --bootstrap-conflict <value>     merge|replace (default: merge)
  --bootstrap-dry-run              Validate bootstrap input only
  --batch-limit <n>                Releases per audit batch (default: 1)
  --request-delay-seconds <n>      Delay between releases in one batch (default: 0.35)
  --scope <value>                  collection|wantlist|both (default: collection)
  --max-retries <n>                Per-release 429 retries in audit mode (default: 2)
  --backoff-seconds <n>            Base backoff for 429 retries (default: 3.0)
  --loop-sleep-seconds <n>         Delay between audit batches (default: 20)
  --max-batches <n>                0 = run until unmatched_count reaches 0 (default: 0)
  --heartbeat-seconds <n>          Progress heartbeat cadence while commands run (default: 15)
  --status-timeout-seconds <n>     Timeout for status probes (default: 60)
  --bootstrap-timeout-seconds <n>  Timeout for bootstrap import (default: 600)
  --audit-timeout-seconds <n>      Timeout per audit batch command (default: 7200)
  --api-max-retries <n>            Spotify API per-request 429 retries (default: 1)
  --api-backoff-seconds <n>        Spotify API per-request backoff base (default: 1.0)
  --api-max-sleep-seconds <n>      Spotify API max sleep for one 429 wait (default: 15.0)
  --api-jitter-seconds <n>         Spotify API retry jitter (default: 0.1)
  --api-retry-after-cap-seconds <n> Cap API Retry-After wait per request (default: 15.0, 0 = no cap)
  --apply-safe-matches             Persist safe auto-matches during audit (default)
  --no-apply-safe-matches          Do not persist safe auto-matches
  --retry-errors                   Retry prior retryable error entries when resuming
  --no-retry-errors                Do not retry prior error entries when resuming (default)
  --stop-on-auth-errors            Exit early when auth errors are detected in a batch (default)
  --no-stop-on-auth-errors         Continue batches even if auth errors are detected
  --rate-limit-cooldown-seconds <n> Minimum sleep after retryable/rate-limited errors (default: 120)
  --retry-after-cap-seconds <n>    Cap honored Retry-After to avoid very long sleeps (default: 900, 0 = no cap)
  --rate-limit-hard-stop-seconds <n> Stop run when a batch is fully rate-limited and Retry-After exceeds threshold (default: 3600, 0 = disabled)
  --reset-report                   Delete existing report at startup before batching
  --lock-path <path>               Lock file path (default: ~/.local/state/discogs_player/spotify_catalog_map_slow.lock)
  --log-path <path>                Log file path for incremental progress rows
  --compact-audit-output           Use compact JSON payload for match audit output (default)
  --full-audit-output              Disable compact audit output
  --report-path <path>             Optional explicit audit report path
  --python-bin <path>              Python executable (default: .venv/bin/python, fallback python3)
  -h|--help                        Show this help

Environment overrides:
  PYTHON_BIN
  DP_SPOTIFY_MAP_BATCH_LIMIT
  DP_SPOTIFY_MAP_REQUEST_DELAY_SECONDS
  DP_SPOTIFY_MAP_SCOPE
  DP_SPOTIFY_MAP_MAX_RETRIES
  DP_SPOTIFY_MAP_BACKOFF_SECONDS
  DP_SPOTIFY_MAP_LOOP_SLEEP_SECONDS
  DP_SPOTIFY_MAP_MAX_BATCHES
  DP_SPOTIFY_MAP_HEARTBEAT_SECONDS
  DP_SPOTIFY_MAP_STATUS_TIMEOUT_SECONDS
  DP_SPOTIFY_MAP_BOOTSTRAP_TIMEOUT_SECONDS
  DP_SPOTIFY_MAP_AUDIT_TIMEOUT_SECONDS
  DP_SPOTIFY_API_MAX_RETRIES
  DP_SPOTIFY_API_BACKOFF_SECONDS
  DP_SPOTIFY_API_MAX_SLEEP_SECONDS
  DP_SPOTIFY_API_JITTER_SECONDS
  DP_SPOTIFY_API_RETRY_AFTER_CAP_SECONDS
  DP_SPOTIFY_MAP_APPLY_SAFE_MATCHES
  DP_SPOTIFY_MAP_RETRY_ERRORS
  DP_SPOTIFY_MAP_STOP_ON_AUTH_ERRORS
  DP_SPOTIFY_MAP_RATE_LIMIT_COOLDOWN_SECONDS
  DP_SPOTIFY_MAP_RETRY_AFTER_CAP_SECONDS
  DP_SPOTIFY_MAP_RATE_LIMIT_HARD_STOP_SECONDS
  DP_SPOTIFY_MAP_RESET_REPORT
  DP_SPOTIFY_MAP_LOCK_PATH
  DP_SPOTIFY_MAP_REPORT_PATH
  DP_SPOTIFY_MAP_LOG_PATH
  DP_SPOTIFY_MAP_AUDIT_COMPACT_OUTPUT
  DP_SPOTIFY_BOOTSTRAP_INPUT
  DP_SPOTIFY_BOOTSTRAP_FORMAT
  DP_SPOTIFY_BOOTSTRAP_CONFLICT_MODE
  DP_SPOTIFY_BOOTSTRAP_DRY_RUN
TXT
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bootstrap-input)
      BOOTSTRAP_INPUT="${2:-}"
      shift 2
      ;;
    --bootstrap-format)
      BOOTSTRAP_FORMAT="${2:-}"
      shift 2
      ;;
    --bootstrap-conflict)
      BOOTSTRAP_CONFLICT_MODE="${2:-}"
      shift 2
      ;;
    --bootstrap-dry-run)
      BOOTSTRAP_DRY_RUN="1"
      shift
      ;;
    --batch-limit)
      BATCH_LIMIT="${2:-}"
      shift 2
      ;;
    --request-delay-seconds)
      REQUEST_DELAY_SECONDS="${2:-}"
      shift 2
      ;;
    --scope)
      MATCH_SCOPE="${2:-}"
      shift 2
      ;;
    --max-retries)
      MAX_RETRIES="${2:-}"
      shift 2
      ;;
    --backoff-seconds)
      BACKOFF_SECONDS="${2:-}"
      shift 2
      ;;
    --loop-sleep-seconds)
      LOOP_SLEEP_SECONDS="${2:-}"
      shift 2
      ;;
    --max-batches)
      MAX_BATCHES="${2:-}"
      shift 2
      ;;
    --heartbeat-seconds)
      HEARTBEAT_SECONDS="${2:-}"
      shift 2
      ;;
    --status-timeout-seconds)
      STATUS_TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --bootstrap-timeout-seconds)
      BOOTSTRAP_TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --audit-timeout-seconds)
      AUDIT_TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --api-max-retries)
      API_MAX_RETRIES="${2:-}"
      shift 2
      ;;
    --api-backoff-seconds)
      API_BACKOFF_SECONDS="${2:-}"
      shift 2
      ;;
    --api-max-sleep-seconds)
      API_MAX_SLEEP_SECONDS="${2:-}"
      shift 2
      ;;
    --api-jitter-seconds)
      API_JITTER_SECONDS="${2:-}"
      shift 2
      ;;
    --api-retry-after-cap-seconds)
      API_RETRY_AFTER_CAP_SECONDS="${2:-}"
      API_RETRY_AFTER_CAP_SECONDS_EXPLICIT=1
      shift 2
      ;;
    --apply-safe-matches)
      APPLY_SAFE_MATCHES="1"
      shift
      ;;
    --no-apply-safe-matches)
      APPLY_SAFE_MATCHES="0"
      shift
      ;;
    --retry-errors)
      RETRY_ERRORS="1"
      shift
      ;;
    --no-retry-errors)
      RETRY_ERRORS="0"
      shift
      ;;
    --stop-on-auth-errors)
      STOP_ON_AUTH_ERRORS="1"
      shift
      ;;
    --no-stop-on-auth-errors)
      STOP_ON_AUTH_ERRORS="0"
      shift
      ;;
    --rate-limit-cooldown-seconds)
      RATE_LIMIT_COOLDOWN_SECONDS="${2:-}"
      shift 2
      ;;
    --retry-after-cap-seconds)
      RETRY_AFTER_CAP_SECONDS="${2:-}"
      RETRY_AFTER_CAP_SECONDS_EXPLICIT=1
      shift 2
      ;;
    --rate-limit-hard-stop-seconds)
      RATE_LIMIT_HARD_STOP_SECONDS="${2:-}"
      shift 2
      ;;
    --reset-report)
      RESET_REPORT="1"
      shift
      ;;
    --lock-path)
      LOCK_PATH="${2:-}"
      shift 2
      ;;
    --log-path)
      LOG_PATH="${2:-}"
      shift 2
      ;;
    --compact-audit-output)
      AUDIT_COMPACT_OUTPUT="1"
      shift
      ;;
    --full-audit-output)
      AUDIT_COMPACT_OUTPUT="0"
      shift
      ;;
    --report-path)
      REPORT_PATH="${2:-}"
      REPORT_PATH_EXPLICIT=1
      shift 2
      ;;
    --python-bin)
      PYTHON_BIN="${2:-}"
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

if [[ "$AUDIT_COMPACT_OUTPUT" != "0" && "$AUDIT_COMPACT_OUTPUT" != "1" ]]; then
  echo "Invalid compact mode toggle: ${AUDIT_COMPACT_OUTPUT} (expected 0 or 1)" >&2
  exit 2
fi
if [[ "$APPLY_SAFE_MATCHES" != "0" && "$APPLY_SAFE_MATCHES" != "1" ]]; then
  echo "Invalid safe-apply toggle: ${APPLY_SAFE_MATCHES} (expected 0 or 1)" >&2
  exit 2
fi
if [[ "$RETRY_ERRORS" != "0" && "$RETRY_ERRORS" != "1" ]]; then
  echo "Invalid retry-errors toggle: ${RETRY_ERRORS} (expected 0 or 1)" >&2
  exit 2
fi
if [[ "$STOP_ON_AUTH_ERRORS" != "0" && "$STOP_ON_AUTH_ERRORS" != "1" ]]; then
  echo "Invalid stop-on-auth-errors toggle: ${STOP_ON_AUTH_ERRORS} (expected 0 or 1)" >&2
  exit 2
fi
if [[ "$RESET_REPORT" != "0" && "$RESET_REPORT" != "1" ]]; then
  echo "Invalid reset-report toggle: ${RESET_REPORT} (expected 0 or 1)" >&2
  exit 2
fi
case "${MATCH_SCOPE}" in
  collection|wantlist|both) ;;
  *)
    echo "Invalid scope: ${MATCH_SCOPE} (expected collection|wantlist|both)" >&2
    exit 2
    ;;
esac

# If the operator explicitly tunes API Retry-After capping but does not set the
# worker-level cooldown cap, align worker sleep cap to the same value.
if [[ "$RETRY_AFTER_CAP_SECONDS_EXPLICIT" == "0" && "$API_RETRY_AFTER_CAP_SECONDS_EXPLICIT" == "1" ]]; then
  RETRY_AFTER_CAP_SECONDS="$API_RETRY_AFTER_CAP_SECONDS"
fi

if [[ "$REPORT_PATH_EXPLICIT" == "0" ]]; then
  case "${MATCH_SCOPE}" in
    collection)
      REPORT_PATH="${DATA_ROOT}/discogs_player/reports/spotify_match_audit_slow.json"
      ;;
    wantlist)
      REPORT_PATH="${DATA_ROOT}/discogs_player/reports/spotify_match_audit_slow_wantlist.json"
      ;;
    both)
      REPORT_PATH="${DATA_ROOT}/discogs_player/reports/spotify_match_audit_slow_combined.json"
      ;;
  esac
fi

mkdir -p "$(dirname "$LOCK_PATH")"
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_PATH"
  if ! flock -n 9; then
    holder_pid="$(cat "${LOCK_PATH}.pid" 2>/dev/null || true)"
    if [[ -n "$holder_pid" ]]; then
      echo "Another spotify catalog mapper is already running (pid=${holder_pid})." >&2
    else
      echo "Another spotify catalog mapper is already running." >&2
    fi
    echo "Lock path: ${LOCK_PATH}" >&2
    exit 1
  fi
  printf '%s\n' "$$" > "${LOCK_PATH}.pid"
  cleanup_lock() {
    rm -f "${LOCK_PATH}.pid"
  }
  trap cleanup_lock EXIT
fi

if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python executable not found: $PYTHON_BIN" >&2
  exit 1
fi

mkdir -p "$(dirname "$LOG_PATH")"
touch "$LOG_PATH"
mkdir -p "$(dirname "$REPORT_PATH")"
if [[ "$RESET_REPORT" == "1" && -f "$REPORT_PATH" ]]; then
  rm -f "$REPORT_PATH"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  line="[${ts}] [INFO] removed existing report before run: ${REPORT_PATH}"
  printf '%s\n' "$line" >> "$LOG_PATH"
  printf '%s\n' "$line"
fi

log_line() {
  local level="$1"
  shift
  local message="$*"
  local ts
  local line
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  line="[${ts}] [${level}] ${message}"
  printf '%s\n' "$line" >> "$LOG_PATH"
  if [[ "$level" == "ERROR" ]]; then
    printf '%s\n' "$line" >&2
  else
    printf '%s\n' "$line"
  fi
}

LAST_CMD_OUTPUT=""
LAST_CMD_RC=0

run_capture() {
  local label="$1"
  local timeout_seconds="$2"
  shift 2
  local tmp_file
  local start_epoch
  local now_epoch
  local elapsed_seconds
  local timeout_rc=124
  local cmd_pid
  local heartbeat_interval
  local next_heartbeat_epoch
  tmp_file="$(mktemp)"

  start_epoch="$(date +%s)"
  log_line INFO "${label}: starting"

  set +e
  if command -v timeout >/dev/null 2>&1 && [[ "$timeout_seconds" != "0" ]]; then
    timeout --foreground "${timeout_seconds}s" "$@" >"$tmp_file" 2>&1 &
  else
    "$@" >"$tmp_file" 2>&1 &
  fi
  cmd_pid=$!
  set -e

  heartbeat_interval="${HEARTBEAT_SECONDS%.*}"
  if ! [[ "$heartbeat_interval" =~ ^[0-9]+$ ]] || [[ "$heartbeat_interval" -lt 1 ]]; then
    heartbeat_interval=1
  fi
  next_heartbeat_epoch=$((start_epoch + heartbeat_interval))

  while kill -0 "$cmd_pid" >/dev/null 2>&1; do
    sleep 1
    if ! kill -0 "$cmd_pid" >/dev/null 2>&1; then
      break
    fi
    now_epoch="$(date +%s)"
    if [[ "$now_epoch" -ge "$next_heartbeat_epoch" ]]; then
      elapsed_seconds=$((now_epoch - start_epoch))
      log_line INFO "${label}: still running (${elapsed_seconds}s elapsed)"
      next_heartbeat_epoch=$((next_heartbeat_epoch + heartbeat_interval))
    fi
  done

  set +e
  wait "$cmd_pid"
  LAST_CMD_RC=$?
  set -e
  LAST_CMD_OUTPUT="$(cat "$tmp_file")"
  rm -f "$tmp_file"

  now_epoch="$(date +%s)"
  elapsed_seconds=$((now_epoch - start_epoch))
  if [[ "$LAST_CMD_RC" -eq "$timeout_rc" ]]; then
    log_line ERROR "${label}: timed out after ${elapsed_seconds}s"
  else
    log_line INFO "${label}: completed rc=${LAST_CMD_RC} (${elapsed_seconds}s)"
  fi
  if [[ "$LAST_CMD_RC" -ne 0 && -n "$LAST_CMD_OUTPUT" ]]; then
    while IFS= read -r row; do
      log_line ERROR "${label}: output: ${row}"
    done <<<"$LAST_CMD_OUTPUT"
  fi
}

parse_status_fields() {
  local status_json="$1"
  mapfile -t STATUS_FIELDS < <(
    "$PYTHON_BIN" -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
cap = data.get("spotify_capability") if isinstance(data, dict) else {}
if not isinstance(cap, dict):
    cap = {}
print("1" if cap.get("addon_available") else "0")
print("1" if cap.get("configured") else "0")
print(str(cap.get("action_label") or ""))
unmatched = data.get("unmatched_count") if isinstance(data, dict) else 0
try:
    unmatched_value = int(unmatched)
except Exception:
    unmatched_value = 0
print(str(max(0, unmatched_value)))
wantlist_unmatched = data.get("wantlist_unmatched_count") if isinstance(data, dict) else 0
try:
    wantlist_unmatched_value = int(wantlist_unmatched)
except Exception:
    wantlist_unmatched_value = 0
print(str(max(0, wantlist_unmatched_value)))
' <<<"$status_json"
  )
  if [[ "${#STATUS_FIELDS[@]}" -lt 5 ]]; then
    STATUS_FIELDS=("0" "0" "" "0" "0")
  fi
}

scope_unmatched_count() {
  local collection_unmatched="$1"
  local wantlist_unmatched="$2"
  case "${MATCH_SCOPE}" in
    collection)
      printf '%s\n' "$collection_unmatched"
      ;;
    wantlist)
      printf '%s\n' "$wantlist_unmatched"
      ;;
    both)
      printf '%s\n' "$((collection_unmatched + wantlist_unmatched))"
      ;;
  esac
}

parse_audit_fields() {
  local audit_json="$1"
  mapfile -t AUDIT_FIELDS < <(
    "$PYTHON_BIN" -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

def as_int(name: str) -> int:
    value = data.get(name) if isinstance(data, dict) else 0
    try:
        return int(value)
    except Exception:
        return 0

def run_retry_after_max_seconds() -> float:
    if not isinstance(data, dict):
        return 0.0
    rows = data.get("run_entries")
    if not isinstance(rows, list):
        return 0.0
    max_value = 0.0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("error_category") or "").strip().lower() != "rate_limited":
            continue
        raw = row.get("retry_after_seconds")
        if raw is None:
            continue
        try:
            value = float(raw)
        except Exception:
            continue
        if value > max_value:
            max_value = value
    return max_value

def run_header_retry_after_max_seconds() -> float:
    if not isinstance(data, dict):
        return 0.0
    rows = data.get("run_entries")
    if not isinstance(rows, list):
        return 0.0
    max_value = 0.0
    import re
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("error_category") or "").strip().lower() != "rate_limited":
            continue
        error_text = str(row.get("error") or "")
        match = re.search(
            r"header_retry_after\s*=\s*([0-9]+(?:\.[0-9]+)?)",
            error_text,
            re.IGNORECASE,
        )
        if not match:
            continue
        try:
            value = float(match.group(1))
        except Exception:
            continue
        if value > max_value:
            max_value = value
    return max_value

print(str(as_int("run_processed_count")))
print(str(as_int("run_auto_applied_count")))
print(str(as_int("run_review_queue_count")))
print(str(as_int("run_error_count")))
print(str(as_int("run_retryable_error_count")))
print(str(as_int("run_auth_error_count")))
print(str((data.get("report_path") if isinstance(data, dict) else "") or ""))
print(f"{run_retry_after_max_seconds():.3f}")
print(f"{run_header_retry_after_max_seconds():.3f}")
' <<<"$audit_json"
  )
  if [[ "${#AUDIT_FIELDS[@]}" -lt 9 ]]; then
    AUDIT_FIELDS=("0" "0" "0" "0" "0" "0" "" "0.000" "0.000")
  fi
}

parse_audit_run_entry_lines() {
  local audit_json="$1"
  mapfile -t AUDIT_ENTRY_LINES < <(
    "$PYTHON_BIN" -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
rows = data.get("run_entries") if isinstance(data, dict) else None
if not isinstance(rows, list):
    rows = []
for row in rows:
    if not isinstance(row, dict):
        continue
    release_id = row.get("discogs_release_id")
    status = str(row.get("status") or "")
    matched = bool(row.get("matched"))
    confidence = row.get("confidence")
    album_id = str(
        row.get("spotify_album_id")
        or row.get("candidate_album_id")
        or ""
    ).strip()
    retry_count = row.get("retry_count")
    error_category = str(row.get("error_category") or "").strip()
    error_retryable = bool(row.get("error_retryable"))
    retry_after_seconds = row.get("retry_after_seconds")
    header_retry_after_seconds = None
    artist = str(row.get("artist") or "").replace("\n", " ").strip()
    title = str(row.get("title") or "").replace("\n", " ").strip()
    error = str(row.get("error") or "").replace("\n", " ").strip()
    import re
    header_match = re.search(r"header_retry_after\s*=\s*([0-9]+(?:\.[0-9]+)?)", error, re.IGNORECASE)
    if header_match:
        try:
            header_retry_after_seconds = float(header_match.group(1))
        except Exception:
            header_retry_after_seconds = None
    album_text = album_id or "none"
    category_text = error_category or "none"
    error_text = error or "none"
    retry_after_text = "none"
    header_retry_after_text = "none"
    if isinstance(retry_after_seconds, (int, float)):
        retry_after_text = f"{float(retry_after_seconds):.3f}"
    if isinstance(header_retry_after_seconds, (int, float)):
        header_retry_after_text = f"{float(header_retry_after_seconds):.3f}"
    print(
        "release_row "
        f"release_id={release_id} status={status} matched={matched} "
        f"confidence={confidence} album_id={album_text} "
        f"retry_count={retry_count} artist={artist} title={title} "
        f"error={error_text} error_category={category_text} "
        f"error_retryable={error_retryable} retry_after_seconds={retry_after_text} "
        f"header_retry_after_seconds={header_retry_after_text}"
    )
' <<<"$audit_json"
  )
}

parse_bootstrap_fields() {
  local bootstrap_json="$1"
  mapfile -t BOOTSTRAP_FIELDS < <(
    "$PYTHON_BIN" -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

def as_int(name: str) -> int:
    value = data.get(name) if isinstance(data, dict) else 0
    try:
        return int(value)
    except Exception:
        return 0

print(str(as_int("parsed_mapping_count")))
print(str(as_int("imported_mapping_count")))
print(str(as_int("invalid_row_count")))
print(str(as_int("duplicate_row_count")))
print(str(as_int("skipped_missing_release_count")))
print(str(as_int("skipped_existing_mapping_count")))
print(str(as_int("skipped_override_mapping_count")))
' <<<"$bootstrap_json"
  )
  if [[ "${#BOOTSTRAP_FIELDS[@]}" -lt 7 ]]; then
    BOOTSTRAP_FIELDS=("0" "0" "0" "0" "0" "0" "0")
  fi
}

log_line INFO "spotify catalog mapping worker: checking status"
run_capture "status-check" "$STATUS_TIMEOUT_SECONDS" "$PYTHON_BIN" -m discogs_player.main status --json
if [[ "$LAST_CMD_RC" -ne 0 ]]; then
  log_line ERROR "status command failed"
  exit "$LAST_CMD_RC"
fi
parse_status_fields "$LAST_CMD_OUTPUT"

ADDON_AVAILABLE="${STATUS_FIELDS[0]}"
CONFIGURED="${STATUS_FIELDS[1]}"
ACTION_LABEL="${STATUS_FIELDS[2]}"
UNMATCHED_COLLECTION_COUNT="${STATUS_FIELDS[3]}"
UNMATCHED_WANTLIST_COUNT="${STATUS_FIELDS[4]}"
UNMATCHED_COUNT="$(scope_unmatched_count "$UNMATCHED_COLLECTION_COUNT" "$UNMATCHED_WANTLIST_COUNT")"

if [[ "$ADDON_AVAILABLE" != "1" ]]; then
  log_line ERROR "Spotify addon unavailable. Install plus profile: pip install -e \".[spotify]\""
  exit 1
fi
if [[ "$CONFIGURED" != "1" ]]; then
  log_line ERROR "Spotify is not configured (${ACTION_LABEL})."
  log_line ERROR "Run: dplayer auth spotify --open-browser --manual"
  exit 3
fi

log_line INFO "status ready addon_available=${ADDON_AVAILABLE} configured=${CONFIGURED} action_label=${ACTION_LABEL} scope=${MATCH_SCOPE} unmatched_count=${UNMATCHED_COUNT} unmatched_collection_count=${UNMATCHED_COLLECTION_COUNT} unmatched_wantlist_count=${UNMATCHED_WANTLIST_COUNT} compact_output=${AUDIT_COMPACT_OUTPUT}"
log_line INFO "spotify api retry profile max_retries=${API_MAX_RETRIES} backoff_seconds=${API_BACKOFF_SECONDS} max_sleep_seconds=${API_MAX_SLEEP_SECONDS} jitter_seconds=${API_JITTER_SECONDS} retry_after_cap_seconds=${API_RETRY_AFTER_CAP_SECONDS}"
log_line INFO "safe auto-apply during audit: ${APPLY_SAFE_MATCHES}"
log_line INFO "retry-errors-on-resume: ${RETRY_ERRORS}"
log_line INFO "stop-on-auth-errors: ${STOP_ON_AUTH_ERRORS}"
log_line INFO "match scope: ${MATCH_SCOPE}"
log_line INFO "rate-limit cooldown seconds: ${RATE_LIMIT_COOLDOWN_SECONDS}"
log_line INFO "retry-after cap seconds: ${RETRY_AFTER_CAP_SECONDS}"
log_line INFO "rate-limit hard-stop seconds: ${RATE_LIMIT_HARD_STOP_SECONDS}"
log_line INFO "audit report path: ${REPORT_PATH}"

MAX_RETRY_WAIT_SECONDS="$(
  MAX_RETRIES_INPUT="$MAX_RETRIES" BACKOFF_SECONDS_INPUT="$BACKOFF_SECONDS" "$PYTHON_BIN" - <<'PY'
import os

try:
    retries = int(float(os.environ.get("MAX_RETRIES_INPUT", "0")))
except Exception:
    retries = 0
try:
    backoff = float(os.environ.get("BACKOFF_SECONDS_INPUT", "0"))
except Exception:
    backoff = 0.0
total = 0.0
for i in range(max(0, retries)):
    total += backoff * (2 ** i)
print(f"{total:.2f}")
PY
)"
log_line INFO "per-release retry wait ceiling (audit layer): ${MAX_RETRY_WAIT_SECONDS}s (max_retries=${MAX_RETRIES}, backoff_seconds=${BACKOFF_SECONDS})"
log_line INFO "progress log path: ${LOG_PATH}"
log_line INFO "in-batch audit progress is enabled via --progress-log ${LOG_PATH}"

if [[ -n "$BOOTSTRAP_INPUT" ]]; then
  log_line INFO "importing bootstrap mappings from: ${BOOTSTRAP_INPUT}"
  BOOTSTRAP_CMD=(
    "$PYTHON_BIN" -m discogs_player.main bootstrap import
    --input "$BOOTSTRAP_INPUT"
    --format "$BOOTSTRAP_FORMAT"
    --conflict-mode "$BOOTSTRAP_CONFLICT_MODE"
    --json
  )
  if [[ "$BOOTSTRAP_DRY_RUN" == "1" ]]; then
    BOOTSTRAP_CMD+=(--dry-run)
  fi
  run_capture "bootstrap-import" "$BOOTSTRAP_TIMEOUT_SECONDS" "${BOOTSTRAP_CMD[@]}"
  if [[ "$LAST_CMD_RC" -ne 0 ]]; then
    log_line ERROR "bootstrap import failed"
    exit "$LAST_CMD_RC"
  fi
  parse_bootstrap_fields "$LAST_CMD_OUTPUT"
  log_line INFO "bootstrap summary parsed=${BOOTSTRAP_FIELDS[0]} imported=${BOOTSTRAP_FIELDS[1]} invalid=${BOOTSTRAP_FIELDS[2]} duplicates=${BOOTSTRAP_FIELDS[3]} skipped_missing=${BOOTSTRAP_FIELDS[4]} skipped_existing=${BOOTSTRAP_FIELDS[5]} skipped_override=${BOOTSTRAP_FIELDS[6]}"
fi

BATCH_INDEX=0
while true; do
  run_capture "status-before-batch" "$STATUS_TIMEOUT_SECONDS" "$PYTHON_BIN" -m discogs_player.main status --json
  if [[ "$LAST_CMD_RC" -ne 0 ]]; then
    log_line ERROR "status command failed before batch"
    exit "$LAST_CMD_RC"
  fi
  parse_status_fields "$LAST_CMD_OUTPUT"
  UNMATCHED_BEFORE="$(scope_unmatched_count "${STATUS_FIELDS[3]}" "${STATUS_FIELDS[4]}")"
  log_line INFO "batch precheck unmatched_before=${UNMATCHED_BEFORE} batch_index=${BATCH_INDEX} max_batches=${MAX_BATCHES}"
  if [[ "$UNMATCHED_BEFORE" -le 0 ]]; then
    log_line INFO "spotify catalog mapping complete: unmatched_count=0"
    exit 0
  fi

  if [[ "$MAX_BATCHES" -gt 0 && "$BATCH_INDEX" -ge "$MAX_BATCHES" ]]; then
    log_line INFO "max batch limit reached (${MAX_BATCHES}); stopping with unmatched_count=${UNMATCHED_BEFORE}"
    exit 0
  fi

  BATCH_INDEX=$((BATCH_INDEX + 1))
  AUDIT_CMD=(
    "$PYTHON_BIN" -m discogs_player.main match audit
    --resume
    --scope "$MATCH_SCOPE"
    --limit "$BATCH_LIMIT"
    --request-delay-seconds "$REQUEST_DELAY_SECONDS"
    --max-retries "$MAX_RETRIES"
    --backoff-seconds "$BACKOFF_SECONDS"
    --progress-log "$LOG_PATH"
    --json
  )
  if [[ "$RETRY_ERRORS" == "1" ]]; then
    AUDIT_CMD+=(--retry-errors)
  else
    AUDIT_CMD+=(--no-retry-errors)
  fi
  if [[ "$APPLY_SAFE_MATCHES" == "1" ]]; then
    AUDIT_CMD+=(--apply-safe)
  fi
  if [[ "$AUDIT_COMPACT_OUTPUT" == "1" ]]; then
    AUDIT_CMD+=(--compact)
  fi
  AUDIT_CMD+=(--report "$REPORT_PATH")

  run_capture \
    "match-audit-batch-${BATCH_INDEX}" \
    "$AUDIT_TIMEOUT_SECONDS" \
    env \
    "DP_SPOTIFY_API_MAX_RETRIES=${API_MAX_RETRIES}" \
    "DP_SPOTIFY_API_BACKOFF_SECONDS=${API_BACKOFF_SECONDS}" \
    "DP_SPOTIFY_API_MAX_SLEEP_SECONDS=${API_MAX_SLEEP_SECONDS}" \
    "DP_SPOTIFY_API_JITTER_SECONDS=${API_JITTER_SECONDS}" \
    "DP_SPOTIFY_API_RETRY_AFTER_CAP_SECONDS=${API_RETRY_AFTER_CAP_SECONDS}" \
    "${AUDIT_CMD[@]}"
  if [[ "$LAST_CMD_RC" -ne 0 ]]; then
    log_line ERROR "match audit batch failed (batch=${BATCH_INDEX})"
    exit "$LAST_CMD_RC"
  fi
  parse_audit_fields "$LAST_CMD_OUTPUT"
  parse_audit_run_entry_lines "$LAST_CMD_OUTPUT"

  RUN_PROCESSED="${AUDIT_FIELDS[0]}"
  RUN_AUTO_APPLIED="${AUDIT_FIELDS[1]}"
  RUN_REVIEW_QUEUE="${AUDIT_FIELDS[2]}"
  RUN_ERRORS="${AUDIT_FIELDS[3]}"
  RUN_RETRYABLE_ERRORS="${AUDIT_FIELDS[4]}"
  RUN_AUTH_ERRORS="${AUDIT_FIELDS[5]}"
  EFFECTIVE_REPORT_PATH="${AUDIT_FIELDS[6]}"
  RUN_RETRY_AFTER_MAX_SECONDS="${AUDIT_FIELDS[7]}"
  RUN_HEADER_RETRY_AFTER_MAX_SECONDS="${AUDIT_FIELDS[8]}"
  RATE_LIMIT_SIGNAL_SECONDS="$(
    awk -v capped="$RUN_RETRY_AFTER_MAX_SECONDS" -v header="$RUN_HEADER_RETRY_AFTER_MAX_SECONDS" 'BEGIN { if (header + 0 > capped + 0) print header; else print capped }'
  )"

  run_capture "status-after-batch-${BATCH_INDEX}" "$STATUS_TIMEOUT_SECONDS" "$PYTHON_BIN" -m discogs_player.main status --json
  if [[ "$LAST_CMD_RC" -ne 0 ]]; then
    log_line ERROR "status command failed after audit batch ${BATCH_INDEX}"
    exit "$LAST_CMD_RC"
  fi
  parse_status_fields "$LAST_CMD_OUTPUT"
  UNMATCHED_AFTER="$(scope_unmatched_count "${STATUS_FIELDS[3]}" "${STATUS_FIELDS[4]}")"

  log_line INFO "batch=${BATCH_INDEX} unmatched_before=${UNMATCHED_BEFORE} run_processed=${RUN_PROCESSED} run_auto_applied=${RUN_AUTO_APPLIED} run_review_queue=${RUN_REVIEW_QUEUE} run_error_count=${RUN_ERRORS} run_retryable_error_count=${RUN_RETRYABLE_ERRORS} run_auth_error_count=${RUN_AUTH_ERRORS} run_retry_after_max_seconds=${RUN_RETRY_AFTER_MAX_SECONDS} run_header_retry_after_max_seconds=${RUN_HEADER_RETRY_AFTER_MAX_SECONDS} rate_limit_signal_seconds=${RATE_LIMIT_SIGNAL_SECONDS} unmatched_after=${UNMATCHED_AFTER} report_path=${EFFECTIVE_REPORT_PATH}"
  if [[ "${#AUDIT_ENTRY_LINES[@]}" -eq 0 ]]; then
    log_line INFO "batch=${BATCH_INDEX} release_row none"
  else
    for row in "${AUDIT_ENTRY_LINES[@]}"; do
      log_line INFO "batch=${BATCH_INDEX} ${row}"
    done
  fi

  if [[ "$UNMATCHED_AFTER" -le 0 ]]; then
    log_line INFO "spotify catalog mapping complete: unmatched_count=0"
    exit 0
  fi

  if [[ "$RUN_AUTH_ERRORS" -gt 0 && "$STOP_ON_AUTH_ERRORS" == "1" ]]; then
    log_line ERROR "auth errors detected in batch=${BATCH_INDEX}; stopping to avoid looping stale tokens. Re-run: dplayer auth spotify --open-browser --manual"
    exit 3
  fi

  if awk \
    -v hard_stop="$RATE_LIMIT_HARD_STOP_SECONDS" \
    -v retry_after="$RATE_LIMIT_SIGNAL_SECONDS" \
    -v processed="$RUN_PROCESSED" \
    -v errors="$RUN_ERRORS" \
    -v retryable_errors="$RUN_RETRYABLE_ERRORS" \
    'BEGIN { exit !((hard_stop + 0 > 0) && (processed + 0 > 0) && (errors + 0 >= processed + 0) && (retryable_errors + 0 > 0) && (retry_after + 0 >= hard_stop + 0)) }'
  then
    log_line ERROR "detected sustained global rate limiting in batch=${BATCH_INDEX}: run_processed=${RUN_PROCESSED} run_errors=${RUN_ERRORS} run_retry_after_max_seconds=${RUN_RETRY_AFTER_MAX_SECONDS} run_header_retry_after_max_seconds=${RUN_HEADER_RETRY_AFTER_MAX_SECONDS} rate_limit_signal_seconds=${RATE_LIMIT_SIGNAL_SECONDS} hard_stop_seconds=${RATE_LIMIT_HARD_STOP_SECONDS}. Stopping early to avoid long sleep loops."
    log_line ERROR "Re-run after Spotify rate limit reset, or tune --rate-limit-hard-stop-seconds / --retry-after-cap-seconds for your tolerance."
    exit 4
  fi

  if [[ "$RUN_PROCESSED" -le 0 ]]; then
    log_line ERROR "no additional releases processed; stopping to avoid a busy loop"
    exit 0
  fi

  SLEEP_SECONDS="$LOOP_SLEEP_SECONDS"
  if [[ "$RUN_RETRYABLE_ERRORS" -gt 0 ]]; then
    EFFECTIVE_RETRY_AFTER_SECONDS="$RUN_RETRY_AFTER_MAX_SECONDS"
    SLEEP_SECONDS="$(
      awk -v base="$LOOP_SLEEP_SECONDS" -v cooldown="$RATE_LIMIT_COOLDOWN_SECONDS" 'BEGIN { if (base + 0 > cooldown + 0) print base; else print cooldown }'
    )"
    log_line INFO "retryable errors detected; applying cooldown before next batch (${SLEEP_SECONDS}s)"
    if awk -v retry_after="$RUN_RETRY_AFTER_MAX_SECONDS" -v cap="$RETRY_AFTER_CAP_SECONDS" 'BEGIN { exit !((cap + 0 > 0) && (retry_after + 0 > cap + 0)) }'; then
      EFFECTIVE_RETRY_AFTER_SECONDS="$RETRY_AFTER_CAP_SECONDS"
      log_line INFO "capping retry-after from ${RUN_RETRY_AFTER_MAX_SECONDS}s to ${EFFECTIVE_RETRY_AFTER_SECONDS}s"
    fi
    if awk -v value="$EFFECTIVE_RETRY_AFTER_SECONDS" 'BEGIN { exit !(value + 0 > 0) }'; then
      SLEEP_SECONDS="$(
        awk -v current="$SLEEP_SECONDS" -v retry_after="$EFFECTIVE_RETRY_AFTER_SECONDS" 'BEGIN { if (current + 0 > retry_after + 0) print current; else print retry_after }'
      )"
      log_line INFO "retry-after aware cooldown selected (${SLEEP_SECONDS}s) from run_retry_after_max_seconds=${RUN_RETRY_AFTER_MAX_SECONDS} effective_retry_after_seconds=${EFFECTIVE_RETRY_AFTER_SECONDS}"
    fi
  fi
  if [[ "$SLEEP_SECONDS" != "0" ]]; then
    log_line INFO "sleeping between batches for ${SLEEP_SECONDS}s"
    sleep "$SLEEP_SECONDS"
  fi
done
