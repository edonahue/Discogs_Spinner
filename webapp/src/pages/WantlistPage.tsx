import { useEffect, useState } from "react";
import { fetchWantlist, Release } from "../api";

const PAGE_SIZE = 25;

type SortKey = "artist_asc" | "artist_desc" | "title_asc" | "year_desc" | "year_asc" | "value_desc";

function sortReleases(releases: Release[], sortKey: SortKey): Release[] {
  return [...releases].sort((a, b) => {
    switch (sortKey) {
      case "artist_asc": return a.artist.localeCompare(b.artist);
      case "artist_desc": return b.artist.localeCompare(a.artist);
      case "title_asc": return a.title.localeCompare(b.title);
      case "year_desc": return (Number(b.year) || 0) - (Number(a.year) || 0);
      case "year_asc": return (Number(a.year) || 0) - (Number(b.year) || 0);
      case "value_desc": return (b.value?.price_median ?? 0) - (a.value?.price_median ?? 0);
    }
  });
}

const pillStyle: React.CSSProperties = {
  display: "inline-block",
  background: "#f0f0f0",
  borderRadius: "4px",
  padding: "0 0.4rem",
  fontSize: "0.75rem",
  marginRight: "0.25rem",
  color: "#555",
};

export function WantlistPage() {
  const [entries, setEntries] = useState<Release[]>([]);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [debouncedYear, setDebouncedYear] = useState("");
  const [genreFilter, setGenreFilter] = useState("");
  const [debouncedGenre, setDebouncedGenre] = useState("");
  const [showValue, setShowValue] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("artist_asc");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const id = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(id);
  }, [query]);

  useEffect(() => {
    const id = setTimeout(() => setDebouncedYear(yearFilter), 300);
    return () => clearTimeout(id);
  }, [yearFilter]);

  useEffect(() => {
    const id = setTimeout(() => setDebouncedGenre(genreFilter), 300);
    return () => clearTimeout(id);
  }, [genreFilter]);

  useEffect(() => {
    setLimit(PAGE_SIZE);
  }, [debouncedQuery, debouncedYear, debouncedGenre, showValue]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    fetchWantlist({
      limit,
      q: debouncedQuery || undefined,
      year: debouncedYear || undefined,
      genres: debouncedGenre ? [debouncedGenre] : undefined,
      withValue: showValue || undefined,
    })
      .then((payload) => {
        if (!cancelled) setEntries(payload.data ?? []);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load wantlist.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [debouncedQuery, debouncedYear, debouncedGenre, showValue, limit]);

  function clearFilters() {
    setQuery("");
    setYearFilter("");
    setGenreFilter("");
    setShowValue(false);
    setSortKey("artist_asc");
    setLimit(PAGE_SIZE);
  }

  const sorted = sortReleases(entries, sortKey);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "0 2rem 2rem", lineHeight: 1.5 }}>
      <h2>Wantlist</h2>

      {/* Filter bar */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center", marginBottom: "0.75rem" }}>
        <input
          type="search"
          placeholder="Search…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ padding: "0.4rem 0.75rem", fontSize: "1rem", width: "220px" }}
        />
        <input
          type="text"
          placeholder="Year"
          value={yearFilter}
          onChange={(e) => setYearFilter(e.target.value)}
          style={{ padding: "0.4rem 0.75rem", fontSize: "1rem", width: "80px" }}
        />
        <input
          type="text"
          placeholder="Genre"
          value={genreFilter}
          onChange={(e) => setGenreFilter(e.target.value)}
          style={{ padding: "0.4rem 0.75rem", fontSize: "1rem", width: "120px" }}
        />
        <label style={{ fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "0.3rem" }}>
          <input type="checkbox" checked={showValue} onChange={(e) => setShowValue(e.target.checked)} />
          Show value
        </label>
        <button onClick={clearFilters} style={{ padding: "0.4rem 0.75rem", fontSize: "0.9rem" }}>
          Clear
        </button>
      </div>

      {/* Sort */}
      <div style={{ marginBottom: "1rem" }}>
        <label style={{ fontSize: "0.9rem", marginRight: "0.5rem" }}>Sort:</label>
        <select
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as SortKey)}
          style={{ padding: "0.3rem 0.5rem", fontSize: "0.9rem" }}
        >
          <option value="artist_asc">Artist A→Z</option>
          <option value="artist_desc">Artist Z→A</option>
          <option value="title_asc">Title A→Z</option>
          <option value="year_desc">Year (newest first)</option>
          <option value="year_asc">Year (oldest first)</option>
          {showValue && <option value="value_desc">Value (high→low)</option>}
        </select>
      </div>

      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
      {loading && entries.length === 0 ? <p>Loading…</p> : null}
      {!loading && !error && entries.length === 0 ? <p>No wantlist entries found.</p> : null}

      <ul style={{ listStyle: "none", padding: 0 }}>
        {sorted.map((e) => (
          <li key={e.discogs_release_id} style={{ padding: "0.5rem 0", borderBottom: "1px solid #eee" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span>
                <strong>{e.artist}</strong> — {e.title}
                {e.year ? <span style={{ color: "#888", marginLeft: "0.5rem" }}>({e.year})</span> : null}
              </span>
              {showValue && e.value?.price_median != null ? (
                <span style={{ color: "#2a7a2a", fontWeight: 500, marginLeft: "1rem", whiteSpace: "nowrap" }}>
                  {e.value.price_median.toFixed(2)} {e.value.currency}
                </span>
              ) : null}
            </div>
            {(e.genres.length > 0 || e.styles.length > 0) ? (
              <div style={{ marginTop: "0.2rem" }}>
                {[...e.genres, ...e.styles].slice(0, 3).map((tag) => (
                  <span key={tag} style={pillStyle}>{tag}</span>
                ))}
              </div>
            ) : null}
          </li>
        ))}
      </ul>

      {entries.length === limit ? (
        <button
          onClick={() => setLimit((l) => l + PAGE_SIZE)}
          style={{ marginTop: "1rem", padding: "0.4rem 1rem" }}
        >
          Load more
        </button>
      ) : null}
    </main>
  );
}
