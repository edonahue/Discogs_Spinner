import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { fetchWantlist, Release, SyncSummary, syncWantlist } from "../api";
import { FocusedReleaseCard } from "../components/FocusedReleaseCard";
import { usePageVisible } from "../hooks/usePageVisible";

const PAGE_SIZE = 25;

type SortKey = "artist_asc" | "artist_desc" | "title_asc" | "year_desc" | "year_asc" | "value_desc";
type SyncState = "idle" | "syncing" | "done" | "error";

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
  display: "inline-flex",
};

function parseFocusId(raw: string | null): number | null {
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function formatSyncSummary(summary: SyncSummary): string {
  return (
    `Wantlist sync complete: fetched ${summary.fetched_count}, `
    + `upserted ${summary.upserted_count}, deactivated ${summary.deactivated_count}.`
  );
}

export function WantlistPage() {
  const [searchParams, setSearchParams] = useSearchParams();
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
  const [syncState, setSyncState] = useState<SyncState>("idle");
  const [syncMessage, setSyncMessage] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [pendingFocusValidation, setPendingFocusValidation] = useState(false);
  const pageVisible = usePageVisible();
  const focusedReleaseId = parseFocusId(searchParams.get("focus"));

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
    if (!pageVisible) return;
    let cancelled = false;
    const controller = new AbortController();
    const shouldValidateFocus = pendingFocusValidation;
    setLoading(true);
    setError("");
    fetchWantlist({
      limit,
      q: debouncedQuery || undefined,
      year: debouncedYear || undefined,
      genres: debouncedGenre ? [debouncedGenre] : undefined,
      withValue: showValue || undefined,
    }, { signal: controller.signal })
      .then((payload) => {
        if (cancelled) return;
        const nextEntries = payload.data ?? [];
        setEntries(nextEntries);
        if (
          shouldValidateFocus
          && focusedReleaseId != null
          && !nextEntries.some((entry) => entry.discogs_release_id === focusedReleaseId)
        ) {
          clearFocus();
        }
        if (shouldValidateFocus) {
          setPendingFocusValidation(false);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to load wantlist.");
        if (shouldValidateFocus) {
          setPendingFocusValidation(false);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [debouncedQuery, debouncedYear, debouncedGenre, showValue, limit, reloadToken, pageVisible]);

  function clearFilters() {
    setQuery("");
    setYearFilter("");
    setGenreFilter("");
    setShowValue(false);
    setSortKey("artist_asc");
    setLimit(PAGE_SIZE);
  }

  const sorted = sortReleases(entries, sortKey);

  function setFocus(releaseId: number) {
    const next = new URLSearchParams(searchParams);
    next.set("focus", String(releaseId));
    setSearchParams(next, { replace: true });
  }

  function clearFocus() {
    const next = new URLSearchParams(searchParams);
    next.delete("focus");
    setSearchParams(next, { replace: true });
  }

  function handleSyncWantlist() {
    setSyncState("syncing");
    setSyncMessage("");
    syncWantlist()
      .then((payload) => {
        const summary = payload.data;
        if (!summary) {
          throw new Error("Wantlist sync completed without a summary.");
        }
        setSyncState("done");
        setSyncMessage(formatSyncSummary(summary));
        setPendingFocusValidation(true);
        setReloadToken((value) => value + 1);
      })
      .catch((err: unknown) => {
        setSyncState("error");
        setSyncMessage(err instanceof Error ? err.message : "Wantlist sync failed.");
      });
  }

  return (
    <main className="app-page">
      <header className="app-page__header">
        <div>
          <h1 className="app-page__title">Wantlist</h1>
          <p className="app-page__subtitle">
            Keep the browsing view readable at narrower sizes and use the focused detail panel for richer wantlist context without leaving the page.
          </p>
        </div>
      </header>

      {focusedReleaseId ? (
        <FocusedReleaseCard
          releaseId={focusedReleaseId}
          scope="wantlist"
          onClear={clearFocus}
        />
      ) : null}

      <section className="app-surface app-toolbar">
        <div className="app-toolbar__group">
          <div className="app-toolbar__field">
            <input
              className="app-input"
              type="search"
              placeholder="Search artist or title"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="app-toolbar__field app-toolbar__field--compact">
            <input
              className="app-input"
              type="text"
              placeholder="Year"
              value={yearFilter}
              onChange={(e) => setYearFilter(e.target.value)}
            />
          </div>
          <div className="app-toolbar__field">
            <input
              className="app-input"
              type="text"
              placeholder="Genre"
              value={genreFilter}
              onChange={(e) => setGenreFilter(e.target.value)}
            />
          </div>
        </div>
        <div className="app-toolbar__group">
          <label className="app-checkbox">
            <input type="checkbox" checked={showValue} onChange={(e) => setShowValue(e.target.checked)} />
            Show value
          </label>
          <div className="app-toolbar__field">
            <select
              className="app-select"
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
            >
              <option value="artist_asc">Artist A→Z</option>
              <option value="artist_desc">Artist Z→A</option>
              <option value="title_asc">Title A→Z</option>
              <option value="year_desc">Year (newest first)</option>
              <option value="year_asc">Year (oldest first)</option>
              {showValue ? <option value="value_desc">Value (high→low)</option> : null}
            </select>
          </div>
          <button type="button" className="app-button app-button--ghost" onClick={clearFilters}>
            Clear Filters
          </button>
          <button
            type="button"
            className="app-button"
            onClick={handleSyncWantlist}
            disabled={syncState === "syncing"}
          >
            {syncState === "syncing" ? "Syncing…" : "Sync Wantlist"}
          </button>
        </div>
      </section>

      {syncMessage ? (
        <p className={`app-message ${syncState === "error" ? "app-message--error" : "app-message--success"}`}>
          {syncMessage}
        </p>
      ) : null}
      {error ? <p className="app-message app-message--error">{error}</p> : null}
      {loading && entries.length === 0 ? <p className="app-message app-message--subtle">Loading wantlist…</p> : null}
      {!loading && !error && entries.length === 0 ? <p className="app-message app-message--subtle">No wantlist entries found.</p> : null}

      <ul className="app-record-list">
        {sorted.map((entry) => {
          const isFocused = focusedReleaseId === entry.discogs_release_id;
          return (
            <li
              key={entry.discogs_release_id}
              className={`app-surface app-record app-record--interactive${isFocused ? " app-record--focused" : ""}`}
              onClick={() => setFocus(entry.discogs_release_id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setFocus(entry.discogs_release_id);
                }
              }}
              tabIndex={0}
              aria-current={isFocused ? "true" : undefined}
            >
              <div className="app-record__header">
                <p className="app-record__title">
                  <strong>{entry.artist}</strong> — {entry.title}
                  {entry.year ? <span className="app-record__year"> ({entry.year})</span> : null}
                </p>
                {showValue && entry.value?.price_median != null ? (
                  <span className="app-record__price">
                    {entry.value.price_median.toFixed(2)} {entry.value.currency}
                  </span>
                ) : null}
              </div>
              {entry.genres.length > 0 || entry.styles.length > 0 ? (
                <div className="app-tag-list" style={{ marginTop: "0.5rem" }}>
                  {[...entry.genres, ...entry.styles].slice(0, 3).map((tag) => (
                    <span key={tag} className="app-tag" style={pillStyle}>{tag}</span>
                  ))}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>

      {entries.length === limit ? (
        <button
          type="button"
          className="app-button"
          onClick={() => setLimit((l) => l + PAGE_SIZE)}
          style={{ marginTop: "1rem" }}
        >
          Load more
        </button>
      ) : null}
    </main>
  );
}
