# discogs_player Web App (Scaffold)

This directory is the initial React/TypeScript scaffold for the API-first web client.

## Current scope

- Local-first frontend that targets `http://127.0.0.1:8768/api/v1`
- Minimal status/capabilities dashboard to validate API contracts
- Designed to be wrapped by a desktop shell in later phases

## Development workflow (planned)

```bash
cd webapp
npm install
npm run dev
```

## Environment

Set `VITE_API_BASE_URL` if the API runs on a non-default host.
