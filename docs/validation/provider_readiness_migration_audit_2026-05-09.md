# Provider Readiness Migration Audit (2026-05-09)

## Scope

Audit of setup/status/onboarding/API/web/GTK/CLI migration to the provider-neutral `provider_readiness` contract (`schema_version = 2`) while preserving backward compatibility.

## Remaining Spotify-Shaped Compatibility Fields

These fields are still intentionally emitted for compatibility:

- `setup` payload:
  - `spotify.addon_available`
  - `spotify.configured`
  - `spotify.action_label`
  - `spotify.status_message`
  - `spotify.next_action`
  - `spotify.dashboard_url`
  - `spotify.oauth_guide_url`
  - `spotify.redirect_uri`
- `status` payload:
  - `spotify_capability.addon_available`
  - `spotify_capability.configured`
  - `spotify_capability.action_label`
  - `spotify_capability.status_message`
  - `default_spotify_device`
- data/mapping compatibility:
  - `spotify_album_id` remains available and in active use.

## Intentionally Legacy vs. Migration Targets

Intentionally legacy (keep for now):

- `spotify_*` setup/status blocks for existing CLI/API/web/GTK adapters.
- `dplayer auth spotify*` command family and related diagnostics.
- `spotify_album_id` storage and payload fields.

Migration targets (incremental):

- Prefer `provider_readiness.summary` for onboarding gating.
- Prefer `provider_readiness.providers[*]` for per-provider state and actions.
- Prefer `provider_readiness.next_actions` / `summary.next_actions` for setup guidance.

## Suggested Deprecation Windows

- Window A (now through next minor): additive-only contract expansion, no removals.
- Window B (next 1-2 minors): adapters fully consume provider-neutral contract, legacy fields still emitted.
- Window C (post-adapter convergence + release notes): begin opt-in warnings for legacy-field consumers.
- Removal gate: only after all first-party adapters and documented external consumers are migrated and contract fixtures/tests are updated.

## Future Provider Implementation Checklist

1. Add provider registration metadata (`provider_id`, display name, docs URL, optional experimental flag).
2. Add/extend descriptor metadata:
   - `auth_required`
   - `supported_capabilities`
   - `setup_url`
   - `oauth_guide_url` if applicable
   - `next_actions_when_unconfigured`
   - `can_skip_setup`
   - `can_retry_setup`
3. Ensure capability detection returns stable provider rows.
4. Validate readiness states with fake harness before live SDK/API integration.
5. Keep UI adapters thin; avoid provider-specific business logic in adapter code.

## Future Provider Test Checklist

Run targeted readiness/adapter tests before any live provider rollout:

- `tests/test_provider_readiness.py`
- `tests/test_provider_readiness_fake_harness.py`
- `tests/test_provider_registry.py`
- `tests/test_provider_readiness_contract_examples.py`
- `tests/test_setup_report.py`
- `tests/test_api_setup.py`
- `tests/test_api_service.py`
- `tests/test_cli_exit_codes.py` (including `diagnostics` and `providers`)
- `tests/test_setup_wizard.py`
- `tests/test_first_run_onboarding.py`

Then run:

- `venv/bin/python -m pytest -q --durations=20`
- `npm --prefix webapp run build`

