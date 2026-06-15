# UI Polish Handoff — Discogs Spinner Web UI

## Context

This document is a handoff prompt for a new Claude Code session. The goal is to take the Discogs Spinner web UI from functional to polished and professional. A deep audit was completed in a prior session. Before writing any code, **interview the user with the options below** — they have opinions on direction and priority.

---

## What the App Is

Discogs Spinner is a local-first desktop companion for vinyl collectors. It wraps a FastAPI Python backend with a React frontend served via Tauri on Windows/macOS, and a GTK4 native app on Linux. Current version is `v0.2.2`. The web UI is the surface this handoff concerns.

**Pages:** Home, Collection, Wantlist, Value, Health, Recent, Analytics, Setup  
**Key files:** `webapp/src/pages/`, `webapp/src/components/Nav.tsx`, `webapp/src/styles.css`

---

## What the Audit Found

### The Design System Is Actually Solid

`webapp/src/styles.css` is cohesive and well-structured:
- Warm beige base (`#f4f0e8`), teal accent (`#0c5d7c`), professional shadow system
- Fluid typography scaling with `clamp()`
- Consistent border radii, spacing increments, 140ms transitions on interactive elements
- CSS variables used throughout — easy to extend

The bones are good. The problems are in the copy, missing interactions, and a few structural inconsistencies.

---

### Issue 1 — CRITICAL: The App Is Called "Spinner" But There Is No Spin Feature in the Web UI

The app's brand and name center on "Spin a random record." The backend tracks `last_spin_release_id` (in `webapp/src/api.ts`). The GTK4 native app has a spin interaction. **The React web UI has no spin button, no randomization UI, no reveal moment.** The Collection page lists records but offers no way to pick one randomly.

This is the most significant gap between the brand promise and the actual product experience.

**Options to discuss with user:**
- A) Add a **Spin button to the Collection page** — picks a random record from the filtered set, highlights/scrolls to it, shows a brief animation
- B) Add a **dedicated Spin page or modal** — full-screen "reveal" moment, themed, with animation
- C) Add a **persistent Spin button in the Nav or Home page** — always accessible, calls the backend spin endpoint and redirects to the result

---

### Issue 2 — HIGH: Dev/Changelog Language Left in User-Facing Page Subtitles

Multiple pages have subtitles that read like PR descriptions, not UI copy. These are confirmed in the code:

- **Home** (`HomePage.tsx` line 129): *"Desktop collection control without browser tab sprawl. This shell now reflows more predictably when the window narrows."*
- **Collection** (`CollectionPage.tsx` line 271): *"Browse your synced releases, keep text readable at narrower window widths, and jump back here when another section promises more detail."*
- **Wantlist** (`WantlistPage.tsx` line 177): *"Keep the browsing view readable at narrower sizes and use the focused detail panel for richer wantlist context without leaving the page."*
- **Health** (`HealthPage.tsx`): *"Health remains summary-only, but the page now reflows cleanly at smaller desktop widths instead of forcing clipped table columns."*
- **Analytics** (`AnalyticsPage.tsx`): *"Analytics stays aggregate-only, but the dense ranking tables now stack cleanly instead of clipping at smaller desktop widths."*

All of these need to be replaced with copy that speaks to the user's needs, not the developer's implementation notes.

**Options to discuss with user:**
- A) **Remove subtitles entirely** — let the page content speak for itself; most are self-explanatory
- B) **Replace with user-benefit copy** — e.g., Home: *"Your records, your market, your daily collector loop."*
- C) **Keep subtitles only where they add context** — remove them on Collection/Wantlist/Analytics, keep a brief one on Home and Setup

---

### Issue 3 — HIGH: Terminal Command Surfaced in GUI

`webapp/src/components/TracklistModal.tsx` line 75:
```
"No tracklist cached — run dplayer tracks refresh to populate it."
```
A GUI user has no idea what `dplayer` is. This should be a UI affordance (a Refresh button) or at minimum plain English with no CLI reference.

**Options:**
- A) **Add a "Refresh Tracklist" button** in the modal that calls the backend endpoint directly
- B) **Replace with plain copy** — *"Tracklist not yet loaded. Try syncing this release."* with a sync CTA
- C) **Both** — button + fallback copy if the API is unavailable

---

### Issue 4 — HIGH: Setup Page Debug Info Block

`webapp/src/pages/SetupPage.tsx` lines 65–83 renders a visible block showing:
- `Onboarding state: needs_discogs_token` (raw internal string)
- `Optional providers ready: 0/1`
- `Next actions: Configure Discogs token to enable collection browsing | ...` (pipe-separated — looks like a data dump)

This reads as unfinished debug output, not intentional UX.

**Options:**
- A) **Remove the block entirely** — the form is self-explanatory; the user just needs to paste a token
- B) **Replace with clean onboarding copy** — a warm, human explanation of what happens after setup
- C) **Keep provider status but style it properly** — convert to a well-designed checklist/progress indicator

---

### Issue 5 — MEDIUM: No Icons in Navigation

`webapp/src/components/Nav.tsx` — text-only links, eight of them in a row. At a desktop width this is functional but sparse. Icons would improve scannability and make the app feel more like a native product.

**Options:**
- A) **Add icons alongside text** — e.g., using a small icon library (Lucide, Phosphor, or inline SVGs) next to each label
- B) **Icon-only nav on narrow widths, icon + text on wide** — responsive treatment
- C) **No icons** — keep it typographic; focus effort elsewhere

---

### Issue 6 — MEDIUM: Loading States Are Text-Only

All async states show plain text ("Loading…", "Loading status…", "Syncing…"). No visual feedback beyond button state changes. On first launch this is the first thing a user sees.

**Options:**
- A) **Add a CSS spinner animation** — a small rotating ring on loading states (no library needed, pure CSS `@keyframes`)
- B) **Add skeleton screens** — placeholder card shapes while content loads
- C) **Keep text loading states** — focus effort on other areas; text is technically sufficient

---

### Issue 7 — MEDIUM: Error Messages Have No Recovery Path

All pages catch API errors and show a generic message (`"Failed to load collection."`, `"Unknown API error."`). No retry button, no diagnosis hint, no next step.

**Options:**
- A) **Add a Retry button** to all error states — re-calls the failed API endpoint
- B) **Improve error copy** with contextual guidance — *"Can't reach the Discogs API. Make sure your token is valid."*
- C) **Both** — better copy + retry button

---

### Issue 8 — MEDIUM: "Tonight's Collector Insights" Heading

`webapp/src/pages/HomePage.tsx` line 231. "Tonight's" is too casual and time-bound in a way that doesn't match how people actually use the app (any time of day, any day).

**Options:**
- A) Rename to **"Collector Insights"** — clean, timeless
- B) Rename to **"Collection Highlights"** — warmer, slightly more evocative
- C) Leave it — not worth changing in isolation

---

### Issue 9 — LOW: AnalyticsPage Uses Inline Styles

`webapp/src/pages/AnalyticsPage.tsx` defines `thStyle` and `tdStyle` objects and applies them to table cells directly, inconsistent with the rest of the codebase which uses CSS classes from `styles.css`.

**Options:**
- A) **Extract to CSS classes** — move table styles to `styles.css` as `.app-table th`, `.app-table td`
- B) **Leave** — functional, low user impact

---

### Issue 10 — LOW: ValuePage Detects Errors via String Matching

`webapp/src/pages/ValuePage.tsx` determines whether a message is an error by checking `message.toLowerCase().includes("fail")`. This is brittle.

**Options:**
- A) **Use a proper error state flag** — `const [refreshError, setRefreshError] = useState(false)`
- B) **Leave** — works in practice, low user impact

---

## Interview Instructions for the New Session

Before writing any code, ask the user about these areas in order of impact. You don't need to ask about all of them in one go — ask 2–3 at a time, get answers, then continue. Good questions to lead with:

1. **On the Spin feature** — "The web UI has no spin/randomization interaction yet, even though the backend supports it and it's the app's core brand moment. How prominent do you want this to be — a button on the Collection page, a dedicated page, or something else?"

2. **On the page copy** — "Several page subtitles contain developer notes rather than user-facing copy. Do you want to remove them, replace them, or only fix certain pages?"

3. **On the nav icons** — "The nav is text-only right now. Do you want to add icons, or keep it typographic?"

Then proceed through the remaining issues based on what the user says about their priorities.

---

## Files to Touch (by issue)

| Issue | Files |
|-------|-------|
| Spin feature | `webapp/src/pages/CollectionPage.tsx`, `webapp/src/api.ts`, possibly new `SpinModal.tsx` |
| Dev copy in subtitles | `HomePage.tsx`, `CollectionPage.tsx`, `WantlistPage.tsx`, `HealthPage.tsx`, `AnalyticsPage.tsx` |
| Terminal command in modal | `webapp/src/components/TracklistModal.tsx` |
| Setup page debug block | `webapp/src/pages/SetupPage.tsx` |
| Nav icons | `webapp/src/components/Nav.tsx`, `webapp/src/styles.css` |
| Loading states | `webapp/src/styles.css` (add `@keyframes`), all page components |
| Error recovery | All page components |
| "Tonight's" copy | `webapp/src/pages/HomePage.tsx` |
| Analytics inline styles | `webapp/src/pages/AnalyticsPage.tsx`, `webapp/src/styles.css` |
| ValuePage error flag | `webapp/src/pages/ValuePage.tsx` |

---

## Verification After Changes

```bash
cd webapp && npm run build   # must pass with no TypeScript errors
```

For UI changes, describe what was changed and what the rendered result should look like — there's no browser automation available in this environment.

---

## What NOT to Change

- The CSS design tokens (`--bg`, `--accent`, `--panel`, etc.) — the color system is well-designed
- The overall page layout structure — grid, card, and surface system is solid
- The API layer in `api.ts` — touch only if needed for the Spin feature endpoint
- Any Python backend code — out of scope for this session
