#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUNNER_PATH="${REPO_ROOT}/scripts/run_scheduled_sync.sh"
CRON_TAG="discogs-player-sync"
DEFAULT_SCHEDULE="17 */6 * * *"

usage() {
  cat <<USAGE
Usage:
  ./scripts/setup_sync_schedule.sh show
  ./scripts/setup_sync_schedule.sh print [\"<cron schedule>\"]
  ./scripts/setup_sync_schedule.sh install [\"<cron schedule>\"]
  ./scripts/setup_sync_schedule.sh remove

Examples:
  ./scripts/setup_sync_schedule.sh install \"17 */6 * * *\"
  ./scripts/setup_sync_schedule.sh show
  ./scripts/setup_sync_schedule.sh remove
USAGE
}

if ! command -v crontab >/dev/null 2>&1; then
  echo "crontab command not found. Install cron on Pop!_OS: sudo apt update && sudo apt install -y cron" >&2
  exit 1
fi

ACTION="${1:-show}"
SCHEDULE="${2:-${DP_SYNC_CRON_SCHEDULE:-${DEFAULT_SCHEDULE}}}"
CRON_LINE="${SCHEDULE} ${RUNNER_PATH} # ${CRON_TAG}"

current_crontab() {
  crontab -l 2>/dev/null || true
}

filter_without_tag() {
  sed "/# ${CRON_TAG}\$/d"
}

case "${ACTION}" in
  show)
    MATCHES="$(current_crontab | grep "# ${CRON_TAG}\$" || true)"
    if [ -z "${MATCHES}" ]; then
      echo "No discogs_player sync schedule is installed."
      exit 0
    fi
    echo "${MATCHES}"
    ;;
  print)
    echo "${CRON_LINE}"
    ;;
  install)
    if [ ! -x "${RUNNER_PATH}" ]; then
      echo "Sync runner script is not executable: ${RUNNER_PATH}" >&2
      echo "Run: chmod +x ${RUNNER_PATH}" >&2
      exit 1
    fi
    EXISTING="$(current_crontab)"
    FILTERED="$(printf "%s\n" "${EXISTING}" | filter_without_tag | sed '/^[[:space:]]*$/d' || true)"
    if [ -n "${FILTERED}" ]; then
      NEW_CRONTAB="${FILTERED}"$'\n'"${CRON_LINE}"
    else
      NEW_CRONTAB="${CRON_LINE}"
    fi
    printf "%s\n" "${NEW_CRONTAB}" | crontab -
    echo "Installed sync schedule:"
    echo "${CRON_LINE}"
    ;;
  remove)
    EXISTING="$(current_crontab)"
    FILTERED="$(printf "%s\n" "${EXISTING}" | filter_without_tag | sed '/^[[:space:]]*$/d' || true)"
    if [ -n "${FILTERED}" ]; then
      printf "%s\n" "${FILTERED}" | crontab -
    else
      crontab -r 2>/dev/null || true
    fi
    echo "Removed sync schedule entries tagged with '${CRON_TAG}'."
    ;;
  --help|-h|help)
    usage
    ;;
  *)
    echo "Unknown action: ${ACTION}" >&2
    usage >&2
    exit 2
    ;;
esac
