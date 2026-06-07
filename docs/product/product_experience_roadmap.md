# Discogs Spinner Product Experience Roadmap

## What The App Is For

Discogs Spinner is a local-first collector companion for people who already maintain a Discogs collection and want a better daily loop than living in browser tabs.

Core promise:

- Browse your collection quickly
- Decide what to spin now
- Understand value/wantlist/health context
- Optionally hand off to playback providers
- Stay useful even when optional providers are unavailable

## First-Run Experience Target

First run should feel predictable and calm:

1. Launch app and immediately understand that Discogs token setup is required.
2. Paste token once and confirm setup state clearly.
3. Run first sync with visible progress and no ambiguous blank states.
4. Land in a useful collection view with clear “what next” actions.
5. Optionally connect playback providers later without blocking collection use.

## Top 5 User Journeys

1. First-time setup and first sync
2. “What should I spin tonight?” from collection filters and discovery signals
3. Jump from selected release to play/open flow with minimal friction
4. Weekly check-in: value movers, hidden gems, queue, collection health
5. Wantlist opportunity review and action planning

## What Should Be Great By v1.0

- Reliable install and first-run flow on Windows/macOS/Linux
- Clear setup/status/readiness messaging across CLI, web, and GTK
- Fast browse + stable spin flows
- Useful discovery surfaces from local data (hidden gems, health, queue, summary)
- Polished “local dashboard” feeling in web and native modes
- Strong docs for friend trials and issue reporting

## What Belongs Later (Not v1.0 Core)

- Mobile apps (companion or full-featured)
- Paid/pro packaging or subscription systems
- New third-party providers beyond current scaffolding
- Cloud account systems and remote sync
- Deep social/community features

## Biggest Product Gaps Today

1. Web has no direct spin/play workflow parity with CLI/native.
2. Discovery signals exist but are split across surfaces without one “collector insights” entrypoint.
3. Public trial docs are good but still verbose for totally new users.
4. Optional-provider messaging can still feel Spotify-centric in places.
5. Cross-surface consistency of terminology (“setup”, “readiness”, “daily use”) needs tightening.

## Delivery Phases

### Phase 1: Daily-Use Clarity (Now)

- Tighten first-run and daily-use next actions
- Improve status/setup/providers/diagnostics guidance
- Add collector-insights summary entrypoint

### Phase 2: Dashboard Cohesion

- Align web + GTK home/dashboard concepts
- Promote discovery cards (hidden gems, health, queue, recent)
- Improve degraded-mode confidence messaging

### Phase 3: Trial Readiness

- Sharpen README and friend-trial docs for cold starts
- Make support/reporting paths easy and explicit
- Validate smoke/test scripts as support tools

### Phase 4: v1.0 Hardening

- Fix top friction from friend trials
- Stabilize performance-sensitive UX paths
- Freeze contract/docs for public launch confidence

## Open Questions (Non-Blocking)

See `docs/product/open_questions.md` for decisions that need product-owner direction after this implementation run.

