Architecture
============

discogs_player follows a layered architecture:

1. Core (settings, paths, runtime config)
2. Data (SQLite schema/migrations/repository)
3. Services/Integrations (Discogs, image cache, optional Spotify backend)
4. Use Cases (shared business operations)
5. Interfaces (CLI and GUI adapters)

Key rule:

- No API calls in CLI/UI modules.

Primary references:

- ``docs/adr/001-layered-architecture.md``
- ``docs/adr/002-sqlite-incremental-sync.md``
- ``docs/adr/003-api-first-local-web-and-desktop-shell.md``
- ``PRODUCT_STATE.md``
