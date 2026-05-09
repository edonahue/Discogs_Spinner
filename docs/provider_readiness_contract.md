# Provider Readiness Contract

This document defines the additive `provider_readiness` contract used by setup, status, API, CLI, web, and GTK surfaces.

## Stability

- Current contract version: `schema_version = 2`
- Backward compatibility:
  - Legacy Spotify-shaped fields (`spotify`, `spotify_capability`, `spotify_*`) remain available.
  - `provider_readiness` is additive and canonical for required/optional onboarding semantics.

## Top-Level Shape

```json
{
  "schema_version": 2,
  "core_service": {},
  "providers": [],
  "next_actions": [],
  "summary": {}
}
```

## Core Fields

- `core_service`: required Discogs readiness object.
- `providers[]`: optional provider readiness rows.
- `next_actions[]`: aggregated next actions across required and optional setup.
- `summary`:
  - `required_services_configured`
  - `optional_provider_count`
  - `ready_provider_count`
  - `degraded_mode`
  - `onboarding_state`
  - `collection_synced`
  - `next_actions`
  - `can_skip_optional_setup`

## Example: Missing Discogs Token

```json
{
  "schema_version": 2,
  "core_service": {
    "service_id": "discogs",
    "required": true,
    "configured": false,
    "readiness": "blocked",
    "degraded_reasons": ["core_not_configured"]
  },
  "providers": [],
  "next_actions": [
    "Open token page: https://www.discogs.com/settings/developers"
  ],
  "summary": {
    "required_services_configured": false,
    "optional_provider_count": 0,
    "ready_provider_count": 0,
    "degraded_mode": false,
    "onboarding_state": "needs_required_setup",
    "collection_synced": false,
    "next_actions": [
      "Open token page: https://www.discogs.com/settings/developers"
    ],
    "can_skip_optional_setup": true
  }
}
```

## Example: Discogs Ready, No Optional Provider Ready

```json
{
  "schema_version": 2,
  "core_service": {
    "service_id": "discogs",
    "required": true,
    "configured": true,
    "readiness": "ready"
  },
  "providers": [
    {
      "provider_id": "spotify",
      "optional": true,
      "readiness": "unavailable",
      "degraded_reasons": ["addon_unavailable"],
      "can_skip_setup": true,
      "can_retry_setup": true
    }
  ],
  "next_actions": [
    "Install optional addon dependencies for this provider."
  ],
  "summary": {
    "required_services_configured": true,
    "optional_provider_count": 1,
    "ready_provider_count": 0,
    "degraded_mode": true,
    "onboarding_state": "core_ready_optional_pending",
    "collection_synced": true,
    "next_actions": [
      "Install optional addon dependencies for this provider."
    ],
    "can_skip_optional_setup": true
  }
}
```

## Example: Spotify Ready

```json
{
  "schema_version": 2,
  "core_service": {
    "service_id": "discogs",
    "required": true,
    "configured": true,
    "readiness": "ready"
  },
  "providers": [
    {
      "provider_id": "spotify",
      "optional": true,
      "readiness": "ready",
      "auth_state": "authenticated",
      "supported_capabilities": [
        "playback",
        "device_selection",
        "catalog_matching"
      ]
    }
  ],
  "next_actions": [],
  "summary": {
    "required_services_configured": true,
    "optional_provider_count": 1,
    "ready_provider_count": 1,
    "degraded_mode": false,
    "onboarding_state": "ready",
    "collection_synced": true,
    "next_actions": [],
    "can_skip_optional_setup": true
  }
}
```

## Example: Optional Provider Disabled/Unavailable

```json
{
  "providers": [
    {
      "provider_id": "youtube_music",
      "enabled": false,
      "readiness": "unavailable",
      "degraded_reasons": ["disabled", "backend_not_installed"],
      "next_actions": [
        "Set DP_ENABLE_EXPERIMENTAL_YOUTUBE_MUSIC=1 to enable provider scaffolding."
      ]
    }
  ]
}
```

## Canonical API Example Payloads

Canonical multi-scenario payloads live in:

- `docs/api/provider_readiness_examples.json`

The file includes these scenarios:

- `missing_discogs_token`
- `discogs_configured_needs_initial_sync`
- `discogs_ready_optional_skipped`
- `spotify_ready`
- `experimental_youtube_music_disabled`
- `provider_unavailable`
- `provider_unauthenticated`
- `degraded_mode_optional_pending`

Contract tests assert this JSON file matches generated fixture contracts in `tests/provider_readiness_examples.py`.

## Versioning and Deprecation Policy

- `provider_readiness` is additive-first and intended to be stable for API, CLI, web, GTK, and future mobile clients.
- `schema_version` increments only for intentional contract evolution that may require client adaptation.
- New fields may be added without a schema bump when existing fields and semantics are preserved.
- Existing keys in the current contract shape are treated as stability commitments.
- Legacy Spotify-shaped fields (`spotify`, `spotify_capability`, `spotify_*`) remain available for backward compatibility during migration.
- Deprecation should follow this path:
  - introduce replacement fields and fixtures first
  - update adapters/tests to consume replacement fields
  - document deprecation window before any removal

## Guidance for Future Providers

Future provider integration should expose descriptor metadata through the backend/registry seam:

- `provider_id`: stable machine id used in contracts, tests, and client routing.
- `display_name`: user-facing provider name.
- `auth_required`: `true` for OAuth/service auth providers, `false` for local/no-auth providers.
- `supported_capabilities`: explicit capability list such as `playback`, `catalog_matching`, `browser_playback`.
- `setup_url`: canonical setup/portal page for end users.
- `oauth_guide_url`: OAuth docs link when applicable.
- `next_actions_when_unconfigured`: plain-language user actions when provider is present but not ready.
- `can_skip_setup`: whether onboarding can continue without connecting this provider.
- `can_retry_setup`: whether adapters should expose retry affordances.
- `experimental` and `experimental_flag`: feature-gated scaffolding metadata.

Provider readiness rows are derived from provider capability + descriptor data, so provider-specific UI branching is not required for normal onboarding/status flows.

### Provider Descriptor Pattern

Use this minimal descriptor shape when introducing a future provider scaffold:

```json
{
  "provider_id": "future_provider",
  "display_name": "Future Provider",
  "auth_required": true,
  "supported_capabilities": ["playback", "catalog_matching"],
  "setup_url": "https://provider.example/setup",
  "oauth_guide_url": "https://provider.example/oauth",
  "next_actions_when_unconfigured": [
    "Open provider setup portal.",
    "Complete auth callback flow."
  ],
  "can_skip_setup": true,
  "can_retry_setup": true,
  "experimental": true,
  "experimental_flag": "DP_ENABLE_EXPERIMENTAL_FUTURE_PROVIDER"
}
```

### Readiness/Diagnostics Expectations

Future providers should map cleanly onto these readiness states:

- `ready`: provider can be used for its declared capabilities.
- `degraded`: provider is listed but needs setup/auth/retry.
- `unavailable`: provider is disabled or not installable in the current environment.

And these standard support surfaces:

- `degraded_reasons` populated with machine-readable causes such as `unauthenticated`, `not_configured`, `disabled`, `backend_not_installed`, `addon_unavailable`.
- `next_actions` populated with short user-facing setup or recovery steps.
- `status_message` populated with a concise human-readable status summary.

### Test Harness

Use `tests/test_provider_readiness_fake_harness.py` to validate new descriptors and readiness behavior before adding real SDK/API integrations.
