# Spotify External Catalog Mapping

## Why this exists

For large collections, interactive matching is not the most reliable path when
Spotify Search API rate limits (`429`) are frequent. This workflow prioritizes:

- resumable progress
- conservative request pacing
- import-first bootstrapping from external mapping sources

## Recommended flow

1. Bootstrap import any known mappings first:

```bash
dplayer bootstrap import --input <path> --format discogs-to-spotify --conflict-mode merge --dry-run
dplayer bootstrap import --input <path> --format discogs-to-spotify --conflict-mode merge
```

Supported `--format` values:

- `auto`
- `discofy`
- `direct`
- `discogs-to-spotify` (alias to nested discofy-style parser)

2. Run the slow catalog worker:

```bash
./scripts/spotify_catalog_map_slow.sh \
  --batch-limit 1 \
  --request-delay-seconds 0.5 \
  --max-retries 2 \
  --backoff-seconds 3 \
  --api-max-retries 1 \
  --loop-sleep-seconds 45 \
  --rate-limit-cooldown-seconds 180 \
  --heartbeat-seconds 10 \
  --audit-timeout-seconds 1200 \
  --stop-on-auth-errors \
  --no-retry-errors \
  --log-path ~/.local/state/discogs_player/spotify_catalog_map_slow.log
```

`spotify_catalog_map_slow.sh` uses compact audit output by default (`match audit --compact`)
to minimize stdout and memory churn during long runs. Use `--full-audit-output` if you need
the full JSON payload in command output.
The worker also passes `match audit --progress-log <log_path>` so each release emits
`event=start`, `event=retry_wait`, and `event=complete` rows while a batch is still running.
It now applies conservative Spotify API retry defaults in worker mode to avoid one
release consuming many minutes under heavy `429` responses. Override with:

- `--api-max-retries`
- `--api-backoff-seconds`
- `--api-max-sleep-seconds`
- `--api-jitter-seconds`

Worker runs now use `match audit --apply-safe` by default so high-confidence safe
matches are persisted during the long-running job. Use `--no-apply-safe-matches`
to keep audit-only behavior.
Worker now uses a lock file to prevent concurrent mapper instances from running
at the same time.
Worker also uses a dedicated report file by default:

`~/.local/share/discogs_player/reports/spotify_match_audit_slow.json`

This avoids clobbering the interactive audit report and prevents stale resume state
from previous one-off audit runs.

If auth expires, batches now classify errors as non-retryable `auth` errors and
the worker stops early (default behavior) so it does not spin for hours on stale tokens.
Use `--no-stop-on-auth-errors` only if you intentionally want to continue.

Use `--reset-report` to force a clean pass with no previous resume state.

Tail incremental progress:

```bash
tail -f ~/.local/state/discogs_player/spotify_catalog_map_slow.log
```

Inspect persisted mapping progress directly from SQLite:

```bash
./scripts/spotify_mapping_report.sh
./scripts/spotify_mapping_report.sh --limit 50
```

The worker now writes per-release rows after each audit batch, for example:

`release_row release_id=2252753 status=error matched=False ...`

3. Review queue/errors in chunks:

```bash
dplayer review list --report ~/.local/share/discogs_player/reports/spotify_match_audit_latest.json
dplayer review retry-errors --report ~/.local/share/discogs_player/reports/spotify_match_audit_latest.json
```

For the slow worker report specifically:

```bash
dplayer review list --report ~/.local/share/discogs_player/reports/spotify_match_audit_slow.json
dplayer review retry-errors --report ~/.local/share/discogs_player/reports/spotify_match_audit_slow.json
```

4. Apply manual decisions where needed:

```bash
dplayer review apply --all
dplayer review reject --all
```

## One-off fallback mode

For a single release, `dplayer match <release_id>` now has a 429 fallback chain:

- if live Spotify API search is rate-limited, it tries existing audit report candidates
- then optional bootstrap files (`DP_SPOTIFY_FALLBACK_BOOTSTRAP_PATHS`)
- then public web search (`site:open.spotify.com/album ...`) as a last resort

Disable it for strict live-only behavior:

```bash
dplayer match <release_id> --no-external-fallback
```

## Rate-limit tuning

Core audit pacing controls:

- `--request-delay-seconds`
- `--max-retries`
- `--backoff-seconds`
- `--heartbeat-seconds`
- `--status-timeout-seconds`
- `--bootstrap-timeout-seconds`
- `--audit-timeout-seconds`

Spotify client retry controls (global):

- `DP_SPOTIFY_API_MAX_RETRIES`
- `DP_SPOTIFY_API_BACKOFF_SECONDS`
- `DP_SPOTIFY_API_MAX_SLEEP_SECONDS`
- `DP_SPOTIFY_API_JITTER_SECONDS`

Backoff reminder:

- one-release worst-case wait for audit retry budget is
  `backoff_seconds * (2^max_retries - 1)`
- with `--max-retries 10 --backoff-seconds 4`, this is `4092s` (~68 minutes)

## Design note for future edits

Keep this workflow outside the GUI/interactive happy path:

- external worker scripts should orchestrate long-running catalog jobs
- core use-cases should remain resumable/report-driven
- bootstrap import stays integration-agnostic and tolerant of multiple external schemas
