# Strategic Expansion Notes (2026-02-26)

## Purpose

Capture long-range vision, medium-term product goals, and short-term release priorities for `discogs_player`, including technical, infrastructure, cost, and legal considerations.

## Vision Horizons

### 1) Aspirational / Long-Term

- Release widely across major platforms.
- Potential monetization paths:
  - paid apps in Apple/Android stores,
  - ad-supported options,
  - or free model.
- Expand beyond Spotify to multiple streaming providers.
- Maintain Discogs as the constant core dependency.

### 2) Medium-Term

- Deliver easy-install releases for:
  - Windows
  - Debian Linux
  - macOS
- Provide stable FTUX for:
  - Discogs connection/setup
  - Spotify connection/setup
  - future provider setup support

### 3) Short-Term

- Prepare a polished shareable GitHub personal-project release.
- Support initial real users:
  - Pilot user A (Windows + Linux, technically savvy)
  - Pilot user B (Windows, less technical)
- Ensure setup is simple and reliable for both.

## Planning Defaults Chosen (Decision Log)

- Monetization strategy: **Free first**
- License direction: **MIT open source**
- Desktop rollout order: **Windows -> Debian -> macOS**
- Mobile approach: **Companion remote-control app first**
- Streaming strategy: **Provider plugin architecture + one additional provider first**
- First additional provider assumption: **YouTube Music**
- Support posture for non-technical users: **Installer + guided FTUX**
- Budget assumption (next 6 months): **< $50/month**
- Near-term milestone target: **shareable release in 8-12 weeks**

## Technical Strategy

### Core Product

- Keep local-first architecture (SQLite + local cache).
- Preserve shared business logic across CLI/GUI/API layers.
- Maintain optional-provider model (Spotify optional, Discogs core).

### Distribution and Installability

- Automate artifact generation for Windows/macOS/Linux.
- Add installer-focused delivery for Windows first.
- Include checksums and versioned release manifests.
- Improve first-run onboarding and recovery paths.

### Provider Expansion

- Introduce provider-agnostic streaming interface.
- Keep Spotify as reference implementation.
- Add one next provider behind feature flags and capability checks.
- Avoid tight coupling between core use-cases and provider-specific modules.

### UX / FTUX

- First-run setup should cover:
  - Discogs token/config
  - optional provider auth
  - device selection
  - initial sync and first successful playback/open flow
- Include in-app diagnostic export for support.

## Infrastructure Strategy

- Use GitHub Actions and GitHub Releases as primary CI/CD channel.
- Keep release checklist and issue templates for support triage.
- Add OS-specific quickstart docs.
- Expand smoke/regression coverage for install and onboarding paths.

## Cost Strategy

- Prefer low-cost local-first operations.
- Avoid paid backend dependencies unless usage requires it.
- Expected near-term recurring costs:
  - mostly $0 infrastructure,
  - optional signing/notarization costs as release maturity increases.

## Legal and Compliance Strategy

- Add and maintain:
  - `LICENSE` (MIT target),
  - privacy policy,
  - terms/disclaimer,
  - third-party attribution.
- Explicitly document trademark/non-affiliation language for Discogs/Spotify/other services.
- Enforce API-terms compliance per provider before broad rollout.
- Keep security hygiene for public release:
  - secret scanning,
  - `.gitignore` hardening,
  - no personal tokens or private data in repo/history.

## Risks and Mitigations

- Risk: platform packaging complexity.
  - Mitigation: staged rollout (Windows first), strict release checklist.
- Risk: provider policy/API constraints.
  - Mitigation: capability-gated plugin design and legal review per provider.
- Risk: non-technical support burden.
  - Mitigation: guided FTUX + diagnostics export + concise docs.
- Risk: premature monetization complexity.
  - Mitigation: free-first validation before pricing/ads decisions.

## Milestone Intent

- **By ~8-12 weeks:** shareable release suitable for two pilot-user trials.
- **After stabilization:** multi-OS easy-install hardening.
- **Later:** mobile companion and monetization experiments based on usage evidence.

## Notes

This document records intention and direction, not implementation completion.
Execution should be tracked through roadmap/backlog/testing docs.
