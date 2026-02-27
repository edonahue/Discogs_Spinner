# ADR-001: Layered Architecture with Shared Use Cases

## Status
Accepted

## Context
We need to design an architecture that supports both CLI and GUI interfaces without duplicating business logic. The CLI must be fully functional over SSH, and the GUI should be a thin layer on top.

## Decision
We will use a layered architecture:

1. **Core Layer** (`core/`): Paths, settings, runtime configuration
2. **Data Layer** (`data/`): SQLite schema, migrations, repository queries
3. **Service Layer** (`services/`): Core API/data services (Discogs, image cache, sync orchestration)
4. **Integration Layer** (`integrations/`): Optional addon adapters (Spotify backend + null backend)
5. **Use Case Layer** (`use_cases/`): Business operations (sync, list, spin, match, play, etc.)
6. **Interface Layer** (`cli/`, `ui/`): Thin adapters that call use cases

**Key Rule**: No API calls in UI or CLI modules.
**Optional Integration Rule**: Core/use-case code does not import Spotify modules directly; it uses `capabilities` + `PlayerBackend`.
**Bootstrap Mapping Rule**: External mapping imports stay in use-case/core modules (e.g. `bootstrap import`), with a tool-specific parser plus a direct schema fallback.
**Matching Safety Rule**: Automated matching persists only high-confidence mappings (`>=0.90`), with lower-confidence candidates queued for review via audit/report flows.

## Consequences

**Pros:**
- Business logic is written once and shared
- CLI can be tested independently of GUI
- Easy to add new interfaces (e.g., web API)
- Clear separation of concerns
- Testable at each layer

**Cons:**
- More initial setup than monolithic approach
- Need to maintain layer boundaries
- Requires discipline to avoid "leaky" abstractions

## Implementation

- 43 use case modules implementing all features
- CLI uses Typer for commands, Rich for output
- GUI uses GTK4/libadwaita via PyGObject
- Both call the same use case functions

## References
- `src/discogs_player/use_cases/` - 43 modules
- `src/discogs_player/cli/commands.py` - CLI interface
- `src/discogs_player/ui/main_window.py` - GUI interface
