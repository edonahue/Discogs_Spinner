# ADR-004: Provider-Neutral Integration and Onboarding Roadmap

## Status
Accepted

## Context

Discogs Spinner already follows a layered architecture where CLI/UI/API adapters call shared use cases and services. That shape is a good foundation for cross-platform growth, but core vocabulary and contracts are still heavily Spotify-shaped in several paths.

This ADR defines the roadmap and compatibility policy to evolve provider support and onboarding without a rewrite and without breaking existing Spotify/YouTube behavior.

## Current Architecture Assessment

1. Layering is intact: adapters (CLI/UI/API) stay thin over use cases and services.
2. Local API + webapp + desktop shell already provide a multi-platform delivery seam.
3. Data and use-case paths contain provider abstractions, but runtime behavior still has Spotify-centric assumptions in naming and flow.

## Current Provider Model Strengths

1. A provider backend interface and registry already exist.
2. Capability/status reporting exists and can drive adapter behavior.
3. Optional-provider intent is established: core Discogs functionality remains useful without a provider.
4. Existing packaging and CI surfaces support staged architectural changes without delivery disruption.

## Current Brittleness (Spotify/YouTube Specificity)

1. Some runtime flows effectively default to Spotify behavior.
2. Mapping/data/API fields are still Spotify-shaped (`spotify_*` naming) in core use cases and adapters.
3. CLI and UI semantics expose provider-specific terms where generic provider contracts should be used.
4. Partial multi-provider schema changes exist, but contract semantics are not yet consistently provider-neutral end to end.

## Decision

We adopt a provider-neutral contract strategy while preserving behavior:

1. Canonical vocabulary in domain and API contracts will be provider-neutral:
   - `provider_id`
   - `provider_release_id`
   - `provider_track_id`
2. Capability-driven behavior becomes the default control plane for adapters (CLI/UI/web), not provider-specific branching.
3. Core/use-case code remains independent of provider SDK details through integration interfaces.
4. Layering guardrails remain mandatory:
   - No direct provider API calls in CLI/UI modules.
   - CLI/UI/API remain adapters over use cases/services.

## Legacy Compatibility Policy

1. Existing Spotify-shaped fields remain temporarily supported as compatibility aliases at adapter boundaries.
2. Canonical provider-neutral fields become the source of truth for new and migrated contracts.
3. Legacy field support is transitional and must not block adding non-Spotify providers later.
4. Migration/deprecation timing will be documented per implementation stage; this ADR does not force immediate removals.

## Staged Roadmap

### Stage 0 (this ADR)

Document architecture direction, vocabulary, compatibility policy, staged work, and non-goals.

### Stage 1

Introduce the smallest safe provider-neutral seam:

1. Add canonical generic mapping DTO fields in core/API contracts.
2. Keep legacy Spotify-shaped fields as aliases for backward compatibility.
3. Avoid flow rewrites and avoid behavioral changes to Spotify/YouTube paths.

### Stage 2

Normalize data/API contracts around provider-neutral mapping and capability discovery:

1. Complete mapping semantics for provider-aware identity in data access patterns.
2. Expand capability contracts for adapter-driven setup/readiness/degraded states.
3. Maintain compatibility shims until clients migrate.

### Stage 3

Onboarding and FTUX modernization:

1. Keep Discogs as required setup.
2. Make providers explicitly optional, independently connectable, and skippable.
3. Drive setup UX from capability state rather than provider hardcoding.

### Stage 4

Future platform/commercial readiness seams (design-only in this roadmap):

1. Keep API contracts portable for web/local API and potential mobile clients.
2. Reserve service boundaries for future account linking and entitlement models.
3. Avoid packaging/profile assumptions that equate one provider with paid tiers.

## Non-Goals for This First Run

1. No new provider implementation.
2. No payments, subscriptions, account linking, entitlement checks, or mobile implementation.
3. No rewrite of existing use-case architecture.
4. No breaking changes to current Spotify/YouTube behavior.
5. No direct provider API calls added to CLI/UI modules.

## Smallest Safe Next Implementation Slice

After this ADR, implement only a narrow Stage 1 slice:

1. Add canonical provider-neutral mapping fields to shared DTOs/API responses.
2. Preserve legacy Spotify-shaped fields as adapter-level aliases.
3. Ship with focused compatibility tests and zero functional behavior change.

## Validation Commands for Future Implementation Work

Run lightweight checks after Stage 1+ code changes:

```bash
venv/bin/python -m pytest -q tests/test_provider_registry.py tests/test_capabilities_providers.py tests/test_provider_schema_migration.py
venv/bin/python -m pytest -q tests/test_api_setup.py tests/test_api_service.py tests/test_setup_wizard.py tests/test_first_run_onboarding.py
venv/bin/python -m pytest -q tests/test_play_release.py tests/test_ensure_mapping.py tests/test_cli_exit_codes.py
venv/bin/python -m pytest -q tests/test_spotify_live_smoke_script.py tests/test_gui_smoke_script.py tests/test_gallery_ux_smoke_script.py tests/test_deb_packaging_scripts.py tests/test_tauri_installer_contract.py
npm --prefix webapp run build
venv/bin/python -m discogs_player.main status --json
venv/bin/python -m discogs_player.main setup --json
```
