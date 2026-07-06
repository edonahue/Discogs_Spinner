# Privacy Policy (Project-Level)

Last updated: 2026-02-26

## Scope

This policy applies to the `discogs_player` project and its distributed builds.
It is a local-first application designed to store collection data on the user's
machine.

## Data Processed

The app may process:

- Discogs collection and wantlist metadata retrieved with user-supplied credentials.
- Optional streaming-provider playback/matching metadata (for example Spotify
  device and album identifiers).
- Local settings and cache data stored in app-managed directories.

## Storage Model

- Primary data is stored locally (SQLite + cache files).
- Discogs tokens can come from `DISCOGS_TOKEN`, local `.env` files, or local
  app settings stored on the user's machine.
- Optional provider credentials may use environment variables, local settings,
  or system keyring storage where enabled.
- The project does not intentionally send analytics or telemetry by default.

## Third-Party Services

When users enable integrations, requests are sent directly to third-party APIs
(for example Discogs and optional streaming providers) using user-authorized
credentials.

Those third parties have their own privacy policies and terms.

## Data Sharing

The project does not intentionally sell personal data.

Data may be shared only when users explicitly choose to:

- export local data,
- upload logs/issues,
- or use integrated third-party APIs.

Collection exports redact secret-looking settings such as tokens, passwords,
client secrets, and refresh tokens.

## Data Retention and Deletion

- Users can remove local app data by deleting local database/cache/config files.
- Users are responsible for revoking API credentials in third-party services.

## Security Notes

- Do not commit tokens/secrets to source control.
- Use local secret storage where available.
- Review generated logs before sharing externally.

## Contact

For privacy concerns, open an issue in the repository with minimal sensitive
data.

## Policy Changes

This file may be updated as project scope changes. Material policy changes
should be noted in repository history/changelog notes.
