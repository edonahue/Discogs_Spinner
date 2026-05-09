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

## Guidance for Future Providers

Future provider integration should expose descriptor metadata through the backend/registry seam:

- `auth_required`
- `supported_capabilities`
- `setup_url`
- `oauth_guide_url` (if applicable)
- `next_actions_when_unconfigured`
- `can_skip_setup`
- `can_retry_setup`

This allows readiness logic to stay provider-neutral while adapters remain thin.
