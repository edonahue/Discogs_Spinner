# ADR-002: SQLite with Incremental Sync and Soft Delete

## Status
Accepted

## Context
We need to store Discogs collection data locally for offline access and fast filtering. The sync should be efficient (not re-downloading everything) and handle items removed from Discogs gracefully.

## Decision
We will use SQLite with:

1. **Incremental Sync**: Only fetch changed/new items
2. **Soft Delete**: Mark items inactive rather than deleting
3. **JSON Columns**: Store arrays (genres, styles) as JSON text
4. **Migration System**: Versioned schema migrations
5. **XDG Paths**: Follow XDG spec for data/config/cache locations

## Schema Design

**Key Tables:**
- `releases` - Core collection data with `is_active` flag
- `wantlist` - Wishlist data
- `spotify_mapping` - Discogs→Spotify links with confidence scores
- `market_prices` - Cached market values
- `*_stats` - Community statistics (have/want counts, ratings)

**Soft Delete Pattern:**
```sql
is_active INTEGER  -- 1 = active, 0 = soft-deleted
last_synced_at TEXT -- When last seen in Discogs
```

**Incremental Sync:**
- Compare Discogs IDs with local DB
- Update existing records
- Insert new records
- Soft-delete missing records

## Consequences

**Pros:**
- Fast local queries
- Offline functionality
- Historical data preservation (soft delete)
- Simple backup (single SQLite file)
- No external database server needed

**Cons:**
- Not designed for multi-user
- Large collections may need optimization
- SQLite limitations (concurrent writes)

## Implementation

- 13 tables total
- 8 schema migrations
- Repository pattern in `data/repo.py`
- Database module in `data/db.py`

## References
- `src/discogs_player/data/db.py` - Schema and migrations
- `src/discogs_player/data/repo.py` - Query patterns
- XDG Base Directory Specification
