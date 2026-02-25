# ADR-003: API-First Local Service for Web + Desktop Shell

## Status
Accepted

## Context

The app needs to evolve from CLI/GTK-only usage into:

1. Cross-platform desktop delivery (Windows, macOS, Debian Linux)
2. A web application interface
3. Continued support for optional Spotify integration

The existing layered architecture and use-case modules should remain reusable.

## Decision

We adopt an API-first local-service architecture:

1. Keep `use_cases/` as the source of business logic.
2. Add a new FastAPI service layer (`discogs_player_api`) exposing stable `/api/v1/*` contracts.
3. Build web UI (`webapp/`) against that API.
4. Wrap the web UI in a desktop shell (`desktop_shell/`) for native distribution.
5. Keep Spotify capability-gated and optional for all interfaces.

## Consequences

### Pros

- Preserves current core/use-case investment
- Enables web and desktop parity through shared HTTP contracts
- Keeps CLI support intact for SSH-first users
- Supports no-Spotify deployments cleanly

### Cons

- Introduces API contract/versioning maintenance
- Adds frontend/toolchain complexity (TypeScript + shell runtime)
- Requires stronger cross-interface parity tests

## Implementation Notes

- API responses use a standard envelope:
  - `ok`
  - `data`
  - `error`
  - `meta`
- Error codes are normalized for clients (`invalid_request`, `auth_error`, etc.).
- Route handlers remain thin adapters around existing use cases.

## References

- `src/discogs_player_api/`
- `src/discogs_player/api_main.py`
- `webapp/`
- `desktop_shell/`
