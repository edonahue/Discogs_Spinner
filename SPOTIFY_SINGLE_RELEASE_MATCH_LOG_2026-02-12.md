# Spotify Single-Release Match Log (2026-02-12)

## Goal

Run one focused Discogs -> Spotify mapping attempt against a single album from the local collection, validate the result, and capture implementation notes for follow-up work.

## Selected Release

- Discogs release id: `2252753`
- Artist: `Al Di Meola`
- Title: `Elegant Gypsy`
- Year: `1977`

## Approach Used

1. Tried direct automatic match flow for a single release (`dplayer match <release_id>`), but Spotify Search API was rate-limited (`429`).
2. Ran one-item audit mode with retry to confirm behavior and capture structured error output.
3. Used direct fallback mapping approach:
   - identified Spotify album id candidate: `2aZJ2ficY62PipHzQRJ7IK`
   - applied explicit override with `dplayer match override`
4. Validated operationally with `dplayer play --open --json`:
   - playback started on an active device
   - open URL resolved correctly
5. Pulled Discogs tracklist cache for track-level notes.

## Commands + Outcomes

### 1) One-item audit (to capture rate-limit behavior)

Command:

```bash
venv/bin/python -m discogs_player.main match audit --limit 1 --max-retries 1 --backoff-seconds 1 --request-delay-seconds 0 --json
```

Outcome (key fields):

- `processed_release_ids: [2252753]`
- `status: "error"`
- `error: "Spotify API request failed (429): Too many requests"`
- `retry_count: 1`

### 2) Apply manual override mapping

Command:

```bash
venv/bin/python -m discogs_player.main match override 2252753 2aZJ2ficY62PipHzQRJ7IK --json
```

Outcome:

```json
{
  "confidence": 1.0,
  "discogs_release_id": 2252753,
  "is_override": true,
  "spotify_album_id": "2aZJ2ficY62PipHzQRJ7IK"
}
```

### 3) Validate playback/open path

Command:

```bash
venv/bin/python -m discogs_player.main play 2252753 --open --json
```

Outcome (key fields):

- `playback_started: true`
- `device_name: "desktop-host"`
- `spotify_album_id: "2aZJ2ficY62PipHzQRJ7IK"`
- `spotify_open_url: "https://open.spotify.com/album/2aZJ2ficY62PipHzQRJ7IK"`

### 4) Capture Discogs tracklist for song-level notes

Command:

```bash
venv/bin/python -m discogs_player.main tracks show 2252753 --json
```

Discogs cached tracks:

1. `Flight Over Rio`
2. `Midnight Tango`
3. `Mediterranean Sundance`
4. `Race With Devil On Spanish Highway`
5. `Lady Of Rome, Sister Of Brazil`
6. `Elegant Gypsy Suite`

## Match Result Summary

- Album mapping result: `SUCCESS (manual override fallback)`
- Final mapped Spotify album id: `2aZJ2ficY62PipHzQRJ7IK`
- Operational validation: `SUCCESS (playback started)`
- Blocking issue encountered in automatic mode: `Spotify Search API 429 rate limiting`

## Notes for Next Iteration

- Single-release `match` mode should support explicit retry/backoff like audit mode does.
- Song-level verification can be strengthened by adding a CLI command that fetches Spotify album tracks for a mapped release id and reports title overlap/confidence.
- Keep manual override as a first-class fallback for public-facing FTUX when API rate limits or fuzzy scores block auto-match.
