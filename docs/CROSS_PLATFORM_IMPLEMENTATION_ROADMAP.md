# Cross-Platform + Web Implementation Roadmap

Date: 2026-02-23 (UTC)
Status: Active

## Priority Order

1. API-first backend foundation (`discogs_player_api`)
2. Web app UX implementation (`webapp`)
3. Desktop shell convergence (`desktop_shell`)
4. Packaging/signing/release hardening per OS

## Phase Snapshot

## Phase 0: Foundation (in progress)

- [x] Add API package scaffolding with stable JSON envelope contract
- [x] Add initial `/api/v1` endpoints for status/catalog/sync/match/play/value
- [x] Add capability-gated error handling for optional integrations
- [x] Add API test coverage scaffold
- [x] Add web and desktop-shell project scaffolds

## Phase 1: Web-first parity (next)

- [ ] Build browse/wantlist/value views against API
- [ ] Add auth/capability-aware UX state handling
- [ ] Add behavior tests for gallery and detail interactions
- [ ] Add frontend performance budgets and loading-state audits

## Phase 2: Desktop shell parity

- [ ] Integrate local API lifecycle into desktop shell
- [ ] Add cross-platform smoke tests for shell startup and API connectivity
- [x] Produce portable bundles for Windows/macOS/Debian
- [x] Add Linux real-build validation for Tauri sidecar + bundle packaging
- [x] Add native macOS and Windows installer bundle validation to CI

## Phase 3: Release hardening

- [ ] Installer/signing/notarization pipeline (`v1.0.0` gate)
- [x] Separate static sidecar-contract validation from real Tauri bundle-build validation
- [x] Require native per-OS artifact validation before upload in installer CI
- [ ] Documentation and support matrix by OS/profile (`v1.0.0` gate)
- [ ] RC validation matrix and launch checklist (`v1.0.0` gate)
