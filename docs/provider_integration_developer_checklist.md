# Provider Integration Developer Checklist

## Goal

Add future provider scaffolding safely without live credentials, while keeping setup/status/API/web/GTK/CLI aligned to `provider_readiness`.

## 1) Add a Future Provider Scaffold

1. Register provider metadata in `src/discogs_player/integrations/provider_registry.py`:
   - backend spec entry
   - display name
   - docs URL
   - optional experimental feature flag
2. Add descriptor metadata in `_PROVIDER_DESCRIPTORS`:
   - `auth_required`
   - `supported_capabilities`
   - `setup_url`
   - `oauth_guide_url` if applicable
   - `next_actions_when_unconfigured`
   - `can_skip_setup`
   - `can_retry_setup`
3. Ensure capability detection exposes a stable provider row via `get_capabilities()`.

## 2) Test Readiness States Without Live Credentials

Use the fake harness:

- `tests/test_provider_readiness_fake_harness.py`

This harness validates:

- ready
- unavailable
- disabled
- installed but not configured
- unauthenticated
- limited capability
- browser-only playback
- no-auth-required
- experimental behind a feature flag

Run:

```bash
venv/bin/python -m pytest -q \
  tests/test_provider_readiness.py \
  tests/test_provider_readiness_fake_harness.py \
  tests/test_provider_registry.py \
  tests/test_provider_readiness_contract_examples.py
```

## 3) Decide Provider Surface State

Use these contract semantics:

- `ready`
  - provider is configured for declared capabilities
  - `degraded_reasons` is empty
- `degraded`
  - provider exists but needs setup/auth/retry
  - examples: `unauthenticated`, `not_configured`
- `unavailable`
  - provider cannot be used in current environment
  - examples: `disabled`, `backend_not_installed`, `addon_unavailable`
- optional setup skipped
  - represented by contract summary (`can_skip_optional_setup`) and optional provider counts
  - onboarding can still proceed when required services are configured

## 4) Verify Adapter Convergence

Run:

```bash
venv/bin/python -m pytest -q \
  tests/test_setup_report.py \
  tests/test_api_setup.py \
  tests/test_api_service.py \
  tests/test_cli_exit_codes.py \
  tests/test_setup_wizard.py \
  tests/test_first_run_onboarding.py
npm --prefix webapp run build
```

Confirm:

- setup/status/diagnostics/providers CLI emit `provider_readiness`
- web onboarding uses `provider_readiness.summary` and `next_actions`
- GTK setup wizard consumes readiness summary and degraded guidance

