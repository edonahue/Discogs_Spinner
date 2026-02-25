# User-Facing Link Audit (2026-02-23)

## Scope

Audit target:

- GUI user-facing text/actions (`src/discogs_player/ui/**`)
- CLI user-facing output/help (`src/discogs_player/cli/commands.py`)
- onboarding/status messaging (`src/discogs_player/use_cases/setup_report.py`, `src/discogs_player/capabilities.py`)
- top-level docs (`README.md`, `docs/source/**`)

Goal:

- identify existing internal/external navigation links,
- find missing link opportunities,
- prioritize additions by user impact and implementation risk.

## Existing Link Inventory

### GUI External Links

1. Album detail Discogs link button

- File: `src/discogs_player/ui/widgets/album_detail.py:79`
- Dynamic URI set per selected release at `src/discogs_player/ui/widgets/album_detail.py:350`

2. Album detail marketplace button

- File: `src/discogs_player/ui/widgets/album_detail.py:87`
- Opens `https://www.discogs.com/sell/release/<id>` at `src/discogs_player/ui/widgets/album_detail.py:365`

3. Wantlist detail Discogs link button

- File: `src/discogs_player/ui/widgets/wantlist_detail.py:80`
- Dynamic URI set per selected release at `src/discogs_player/ui/widgets/wantlist_detail.py:273`

4. Wantlist detail marketplace button

- File: `src/discogs_player/ui/widgets/wantlist_detail.py:88`
- Opens `https://www.discogs.com/sell/release/<id>` at `src/discogs_player/ui/widgets/wantlist_detail.py:288`

### GUI Internal In-App Navigation

1. Market Value dashboard rows are clickable and focus Browse release

- Clickable rows: `src/discogs_player/ui/widgets/value_dashboard.py:535`
- Clickable detector items: `src/discogs_player/ui/widgets/value_dashboard.py:648`
- Navigation handler in main window: `src/discogs_player/ui/main_window.py:1286`

2. Gallery selection has an explicit back affordance

- Back button in hero selection overlay: `src/discogs_player/ui/widgets/cover_grid.py:109`
- Back callback wiring (Browse): `src/discogs_player/ui/main_window.py:1939`
- Back callback wiring (Wantlist): `src/discogs_player/ui/main_window.py:1943`

### CLI External Link Surfaces

1. Spotify OAuth authorization URL is printed for manual browser open

- File: `src/discogs_player/cli/commands.py:2225`

2. Playback fallback prints Spotify URL when playback does not start

- File: `src/discogs_player/cli/commands.py:2425`

3. `dplayer open` opens or copies Discogs marketplace URL

- Command: `src/discogs_player/cli/commands.py:2432`
- URL build/open: `src/discogs_player/cli/commands.py:2446`
- Copy path: `src/discogs_player/cli/commands.py:2448`

### Docs Internal Cross-Linking

- Canonical product-state references now exist in `README.md:5`
- Sphinx docs index now resolves to concrete pages at `docs/source/index.rst:9`

## Gaps And Opportunities

## P1: High-Impact, Low-Risk

1. Add mapped Spotify album links in GUI detail panels

Problem:

- Mapping is shown as plain text (`Mapping: ...`) in both detail widgets.
- Users cannot directly open mapped Spotify album from GUI detail context.

Where:

- `src/discogs_player/ui/widgets/album_detail.py:162`
- `src/discogs_player/ui/widgets/wantlist_detail.py:172`

Recommendation:

- Add a `Gtk.LinkButton` for mapped Spotify album URI when mapping exists.
- Fallback to disabled state with label "Spotify album link unavailable".

2. Add setup/auth help links near Spotify capability hints

Problem:

- Hints like "Enable Spotify (optional)" and "Connect Spotify" are text-only.
- No direct path to docs or external setup pages.

Where:

- `src/discogs_player/ui/widgets/album_detail.py:172`
- `src/discogs_player/ui/widgets/wantlist_detail.py:182`
- `src/discogs_player/ui/widgets/device_picker.py:37`

Recommendation:

- Add one compact help row with links:
  - external: Spotify dashboard (`https://developer.spotify.com/dashboard`)
  - internal/docs: onboarding docs (README/setup section or product state)

3. Improve CLI setup/onboarding with explicit URLs (not command-only)

Problem:

- `setup` and capability messaging mostly reference commands but not primary web targets.

Where:

- `src/discogs_player/use_cases/setup_report.py:62`
- `src/discogs_player/capabilities.py:66`

Recommendation:

- Include optional URL fields in setup report payload:
  - Discogs token page (`https://www.discogs.com/settings/developers`)
  - Spotify dashboard (`https://developer.spotify.com/dashboard`)
- Render these in table output for discoverability.

## P2: Medium-Impact

1. Add GUI "Help" entrypoint (header menu)

Problem:

- No single in-app location to discover docs/workflows.

Where:

- Main window titlebar creation: `src/discogs_player/ui/main_window.py:754`

Recommendation:

- Add a `Gtk.MenuButton` to header bar with actions:
  - Open README
  - Open Product State
  - Open Spotify walkthrough
  - Open troubleshooting/setup commands dialog

2. Add internal jump links from detail panel to Market Value tab

Problem:

- Users can navigate Value -> Browse by clicking rows, but not easily reverse.

Where:

- Detail widgets currently have no "show in dashboard" action:
  - `src/discogs_player/ui/widgets/album_detail.py`
  - `src/discogs_player/ui/widgets/wantlist_detail.py`

Recommendation:

- Add callback button "View in Market Value Dashboard" to selected-release context.
- Navigate to Value tab and pre-highlight release where applicable.

3. Add gallery hero quick links for selected album context

Problem:

- Gallery selection currently emphasizes cover art and a back affordance.
- Fast external actions (Discogs release/marketplace/Spotify mapped album) still require scanning the right detail panel.

Where:

- Hero overlay shell in gallery widget: `src/discogs_player/ui/widgets/cover_grid.py:99`
- Gallery selection callbacks and selected item wiring: `src/discogs_player/ui/main_window.py:1115`, `src/discogs_player/ui/main_window.py:975`

Recommendation:

- Add compact action chips/buttons under the hero subtitle:
  - Open Discogs release
  - Open Discogs Marketplace
  - Open mapped Spotify album (when available)
- Keep these actions synchronized with right-panel detail data and hide when unavailable.

## P3: Nice-To-Have

1. `dplayer docs` command

Problem:

- CLI has no first-class docs discovery command.

Recommendation:

- Add command to print (or open) canonical docs paths and core external URLs.
- Keep behavior SSH-safe by default (`print`), with optional `--open`.

2. Copy URL actions in GUI for link-heavy flows

Problem:

- GUI often opens URLs directly; no copy fallback for headless/remote use.

Recommendation:

- Add "Copy URL" companion actions in detail widgets and auth-related UI contexts.

3. Add actionable links in GUI empty/error states (not CLI-only instructions)

Problem:

- Some GUI states show CLI command strings but no in-app action path.

Where:

- Market dashboard empty state message: `src/discogs_player/ui/widgets/value_dashboard.py:489`

Recommendation:

- Add inline actions:
  - "Refresh market values now" (internal callback to existing refresh flow)
  - "Open docs" link for advanced/CLI workflows

4. Add external links in interactive Market Value lists

Problem:

- Interactive value rows currently navigate internally to Browse only.
- No quick path to Discogs/Marketplace from this flow.

Where:

- Interactive list item construction and click behavior:
  - `src/discogs_player/ui/widgets/interactive_value_list.py:125`
  - `src/discogs_player/ui/widgets/interactive_value_list.py:219`

Recommendation:

- Add secondary per-row link affordance (or context menu):
  - Discogs release page
  - Marketplace listing
- Preserve existing primary click behavior for in-app navigation.

## Suggested Implementation Order

1. P1-1 mapped Spotify link buttons in detail widgets.
2. P1-2 capability-hint help links (GUI).
3. P1-3 setup payload URL enrichment + CLI render.
4. P2-1 header help menu.
5. P2-2 detail -> value tab jump action.
6. P2-3 gallery hero quick links.
7. P3-3 GUI empty-state actionable links.
8. P3-4 interactive value list external links.

## Acceptance Criteria For Link Additions

1. Links are visible only when contextually relevant (avoid visual noise).
2. External URLs are clearly labeled and safe to copy/open.
3. All new link surfaces have tests (at least static marker + behavior where practical).
4. CLI behavior remains SSH-safe (no implicit browser open unless explicitly requested).
