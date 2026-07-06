# Contributing to Spinner for Discogs

Thank you for your interest in contributing to Spinner for Discogs! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Architecture Decision Records](#architecture-decision-records)

## Code of Conduct

This project follows the standard open-source code of conduct:
- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different viewpoints and experiences

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Pop!_OS or similar Linux distribution (for full GUI functionality)
- Git

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/edonahue/Discogs_Spinner.git
   cd Discogs_Spinner
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Configure environment variables:**

   See [docs/token_setup.md](docs/token_setup.md) for step-by-step instructions on obtaining these credentials.

   ```bash
   export DISCOGS_TOKEN="your_discogs_personal_token"
   # Optional: Spotify credentials for playback testing
   export SPOTIFY_CLIENT_ID="your_spotify_client_id"
   export SPOTIFY_SECRET="your_spotify_client_secret"
   # Legacy alias also accepted:
   # export SPOTIFY_CLIENT_SECRET="your_spotify_client_secret"
   ```

5. **Run tests to verify setup:**
   ```bash
   pytest
   ```

## Project Structure

```
discogs_player/
├── src/discogs_player/        # Main source code
│   ├── cli/                   # Command-line interface
│   │   ├── commands.py        # CLI command definitions
│   │   └── render.py          # Output formatting
│   ├── core/                  # Core utilities
│   │   ├── paths.py           # XDG path management
│   │   └── settings.py        # Configuration management
│   ├── data/                  # Data layer
│   │   ├── db.py              # Database schema/migrations
│   │   └── repo.py            # Repository queries
│   ├── services/              # External API clients
│   │   ├── discogs_client.py  # Discogs API
│   │   ├── matching.py        # Discogs→Spotify matching
│   │   ├── image_cache.py     # Cover art caching
│   │   └── sync_manager.py    # Sync orchestration
│   ├── integrations/          # Optional integration adapters
│   │   ├── player_backend.py  # Backend interface + shared errors
│   │   ├── null_backend.py    # Fallback backend when addon unavailable
│   │   └── spotify/           # Spotify addon implementation
│   │       ├── backend.py
│   │       ├── spotify_client.py
│   │       └── oauth.py
│   ├── use_cases/             # Business logic
│   │   ├── sync_collection.py
│   │   ├── list_releases.py
│   │   ├── spin_release.py
│   │   ├── play_release.py
│   │   └── ... (43 modules total)
│   ├── ui/                    # GTK4 GUI
│   │   ├── main_window.py     # Main window
│   │   ├── sorting.py         # Sorting logic
│   │   └── widgets/           # UI components
│   └── main.py                # CLI entry point
├── tests/                     # Test suite
├── docs/                      # Documentation
├── scripts/                   # Utility scripts
└── requirements.txt           # Dependencies
```

## Coding Standards

### Python Style

- **PEP 8** compliance is required
- Use **type hints** for all function signatures
- Maximum line length: **100 characters**
- Use **Google-style docstrings**:
  ```python
  def function_name(param1: str, param2: int) -> bool:
      """Short description.
      
      Longer description if needed.
      
      Args:
          param1: Description of param1
          param2: Description of param2
          
      Returns:
          Description of return value
          
      Raises:
          ValueError: When input is invalid
      """
  ```

### Import Order

```python
# 1. Standard library
from __future__ import annotations
import json
from typing import Any

# 2. Third-party
import httpx
from rich.console import Console

# 3. Local application
from discogs_player.data.db import get_connection
```

### Integration Boundary Rules

- Core modules (`core/`, `data/`, `use_cases/`, shared `cli/`/`ui/` flows) must not directly import `integrations/spotify/*`.
- Resolve optional Spotify behavior through `discogs_player.capabilities` and the `PlayerBackend` interface.
- Keep capability-aware UX:
  - Addon missing: show `Enable Spotify (optional)`.
  - Addon installed but unconfigured: show `Connect Spotify`.
- Keep mapping bootstrap imports in core/use-case space:
  - Tool-specific parsing lives in `use_cases/bootstrap_import.py` (for example Discofy JSON).
  - Preserve direct fallback schema support (`discogs_release_id` + `spotify_album_id`) for future portability.
  - Keep conversion helpers thin wrappers around those use-cases (for example `scripts/convert_discofy_bootstrap.py`) to avoid parser drift.
- Keep first-time setup/auth flows discoverable:
  - `dplayer setup` for overall onboarding status.
  - `dplayer auth spotify-doctor` for Spotify auth diagnostics.
- Keep Spotify matching safety behavior consistent:
  - automated apply paths only persist `confidence >= 0.90` (`SAFE_AUTO_APPLY_THRESHOLD`).
  - `0.72-0.89` candidates stay in review queue (`match audit` report / `match --unmatched` output) unless explicitly overridden.
  - preserve audit resiliency (`429` retry/backoff + resumable JSON report export).

### Error Handling

- Use specific exceptions, avoid bare `except:`
- Provide meaningful error messages
- Use the project's error codes for CLI exit codes

### Naming Conventions

- **Modules**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `lowercase_with_underscores`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Private**: `_leading_underscore`

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/discogs_player --cov-report=term-missing

# Run specific test file
pytest tests/test_spin_release.py

# Run with verbose output
pytest -v
```

### Core vs Plus Test Profiles

Validate both packaging profiles locally before changing integration boundaries:

```bash
# Core profile (no Spotify addon dependency)
pip install .
pytest -q tests/test_cli_exit_codes.py tests/test_play_release.py tests/test_ensure_mapping.py

# Plus profile (Spotify addon enabled)
pip install ".[spotify]"
pytest -q tests/test_spotify_oauth.py tests/test_cli_exit_codes.py tests/test_play_release.py tests/test_ensure_mapping.py
```

CI uses the same split in `.github/workflows/core_plus_ci.yml` and publishes
`discogs_player-core` + `discogs_player-plus` artifacts per OS.

### Spotify Live Smoke Validation

For live desktop verification of Spotify auth/devices/play-open fallback:

```bash
./scripts/spotify_live_smoke.sh
./scripts/spotify_live_smoke.sh --auth
```

### Test Guidelines

- All new features must include tests
- Aim for >80% code coverage
- Use `isolated_xdg` fixture for filesystem isolation
- Mock external API calls
- Test both success and error cases

### Test Example

```python
def test_spin_release_deterministic(isolated_xdg):
    """Test that spin with same seed returns same result."""
    # Setup test data
    conn = get_connection()
    upsert_releases(conn, [test_release_data])
    conn.close()
    
    # Execute
    result1 = run_spin_release(seed=42)
    result2 = run_spin_release(seed=42)
    
    # Assert
    assert result1["discogs_release_id"] == result2["discogs_release_id"]
```

## Submitting Changes

### Before Submitting

1. **Run the test suite:**
   ```bash
   pytest
   ```

2. **Run type checking:**
   ```bash
   mypy src/discogs_player
   ```

3. **Run linting:**
   ```bash
   ruff check .
   ruff format .
   ```

4. **Update documentation** if needed

5. **Add an Architecture Decision Record (ADR)** for significant changes

### Commit Messages

Follow conventional commits:

```
feat: add spin feature to wantlist
test: add coverage for release stats refresh
fix: handle missing discogs token gracefully
docs: update API documentation
refactor: optimize keyboard navigation
```

### Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes with tests
3. Run the full test suite
4. Commit with clear messages
5. Push to your fork
6. Open a Pull Request with:
   - Clear description of changes
   - Link to related issues
   - Test results
   - Any breaking changes noted

## Architecture Decision Records

Significant architectural decisions should be documented in the `docs/adr/` directory. See existing ADRs for format.

When to write an ADR:
- New major features
- Changes to data model
- Changes to API design
- Significant refactoring
- Technology choices

Template:
```markdown
# ADR-XXX: Title

## Status
Proposed / Accepted / Deprecated / Superseded

## Context
What is the issue we're facing?

## Decision
What did we decide?

## Consequences
What are the trade-offs?

## Alternatives Considered
What else did we consider?
```

## Questions?

- Check existing documentation in `docs/`
- Review Architecture Decision Records in `docs/adr/`
- Open an issue for discussion

Thank you for contributing!
