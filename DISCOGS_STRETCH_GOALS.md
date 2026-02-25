# Discogs-Only Stretch Goals (Pre-Spotify)

This backlog is scoped to features that deliver clear user value before Spotify connection work resumes next week.

## Priority Backlog

| Goal | ROI | Effort | Why It Matters | Deliverable |
|---|---|---|---|---|
| Market Ops Presets (Fast/Deep) | High | S | One-click control over stale days + refresh limit by use case | Preset buttons that fill ops controls |
| Value Movers Panel | High | M | Shows what changed most between snapshots | Top gainers/decliners since last snapshot |
| Price Refresh Prioritizer | High | M | Uses refresh budget where it matters most | Queue ordered by `unpriced > stale > high-value` |
| Collection Health Score | High | M | Makes cleanup measurable | Single score + issue buckets + drill-down |
| Data Quality Queue | High | M | Actionable fixes for missing metadata | Queue for missing year/genre/style/cover/price |
| Duplicate & Variant Detector | High | M | Finds collection redundancy and variant overlap | Duplicate candidates + merge/ignore workflow |
| Top Labels / Formats Dashboard | Medium | S | Better curation and discovery from local data | Charts for labels, formats, decades |
| Price Alert Rules | Medium | M | Enables watchlist behavior without Spotify dependency | Alerts when median crosses thresholds |
| Repricing Cadence Engine | Medium | M | Reduces API usage while keeping data fresh | Rules by value tier + last-updated window |
| Value-at-Risk View | Medium | M | Better visibility into collection downside | Spread analysis by item and total |
| Wantlist Opportunity View | Medium | M | Discogs-native buying insight | Compare wantlist medians to collection medians |
| Collection Story Timeline | Medium | S | High-engagement visual for ownership history | Timeline by acquisition year and value growth |
| Cover Cache Manager | Medium | S | Better UX and disk control | Cache stats, prune controls, warm-cache action |
| Shareable Reports Export | Medium | S | Useful artifacts for external analysis | CSV/Markdown export templates |

## Suggested Sequence (Before Spotify)

1. Value Movers Panel
2. Price Refresh Prioritizer
3. Collection Health Score + Data Quality Queue
4. Duplicate & Variant Detector
5. Price Alert Rules

## Ultimate Stretch Goal: Cross-Platform & Public Release

**Goal**: Make discogs_player portable to Windows and macOS, then publish to a public GitHub repository.

### Portability Roadmap

| Area | Current State | Work Required | Effort |
|---|---|---|---|
| CLI core (sync, list, spin, play, value, etc.) | Cross-platform (Python + SQLite) | Minimal - already portable | S |
| Path management (`core/paths.py`) | XDG-only (Linux conventions) | Replace with `platformdirs` library for Windows/macOS paths | S |
| GUI (`ui/`) | GTK4/libadwaita (Linux-native) | Evaluate alternatives: Qt6 (PySide6), or accept CLI-only on non-Linux | L |
| Desktop integration scripts | Bash + .desktop + cron | Platform-specific launchers (macOS .app bundle, Windows shortcut/Task Scheduler) | L |
| Error messages / help text | References Pop!_OS and apt-get | Platform-detect and show OS-appropriate install guidance | S |
| Scheduled sync | cron-based (Linux/macOS) | Add Windows Task Scheduler support or Python-native scheduling | M |
| Credential storage (keyring) | Already cross-platform | No changes needed (uses macOS Keychain, Windows Credential Store) | - |

### Pre-Publish Safety Checklist

Before making the repo public:

- [ ] Add a LICENSE file (MIT, Apache 2.0, or GPL)
- [ ] Harden `.gitignore` (add `.env`, `*.db`, `exports/`, `*.log`, `.coverage`)
- [ ] Audit git history for any committed secrets or personal tokens
- [ ] Remove or genericize hardcoded paths (e.g., `<home-user>/` in walkthrough docs)
- [ ] Remove personal collection data from `exports/` directory
- [ ] Remove scratch/debug scripts from repo root (`test_carousel_crash.py`, `test_spin_debug.py`, `reproduce_carousel_spin.py`)
- [ ] Review all markdown files for personal information
- [ ] Add GitHub Actions CI workflow (pytest + linting)
- [ ] Consider squashing or rebasing history to start clean

### Cross-Platform Strategy Options

1. **CLI-first portable** (recommended first step): Ship CLI (`dplayer`) on all platforms; GUI stays Linux-only initially.
2. **Qt migration**: Replace GTK4 UI with PySide6/PyQt6 for true cross-platform GUI. Significant effort but best long-term reach.
3. **Web UI**: Add a lightweight web interface (Flask/FastAPI) alongside or replacing the GTK GUI. Works everywhere with a browser.

## Notes

- Favor features that reuse existing value snapshot/refresh infrastructure.
- Keep operations asynchronous in the GUI.
- For each feature, add one concise summary card and one actionable table/list.
