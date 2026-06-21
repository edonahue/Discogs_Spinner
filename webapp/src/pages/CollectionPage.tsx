import { KeyboardEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  fetchReleases,
  fetchReleaseSummary,
  Release,
  ReleaseCollectionSummary,
  SyncSummary,
  syncCollection,
  spinCollection,
} from "../api";
import { FocusedReleaseCard } from "../components/FocusedReleaseCard";
import { TracklistModal } from "../components/TracklistModal";
import { usePageVisible } from "../hooks/usePageVisible";
import { formatSyncSummary, parseFocusId, PILL_STYLE as pillStyle, SortKey, sortReleases } from "../utils/helpers";

const PAGE_SIZE = 25;

type SyncState = "idle" | "syncing" | "done" | "error";

type TracklistTarget = {
  discogs_release_id: number;
  title: string;
  artist: string;
};

function formatSummaryPrice(summary: ReleaseCollectionSummary | null): string {
  if (!summary || summary.total_median == null || summary.priced_release_count <= 0) {
    return "—";
  }
  if (summary.mixed_currencies) {
    return summary.total_median.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  const currency = (summary.median_currency ?? "").trim().toUpperCase();
  const amount = summary.total_median.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  if (!currency || currency === "USD" || currency === "US$" || currency === "$") {
    return `$${amount}`;
  }
  return `${currency} ${amount}`;
}

function formatLocalDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(parsed);
}

export function CollectionPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [releases, setReleases] = useState<Release[]>([]);
  const [summary, setSummary] = useState<ReleaseCollectionSummary | null>(null);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [debouncedYear, setDebouncedYear] = useState("");
  const [genreFilter, setGenreFilter] = useState("");
  const [debouncedGenre, setDebouncedGenre] = useState("");
  const [unmatchedOnly, setUnmatchedOnly] = useState(false);
  const [showValue, setShowValue] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("artist_asc");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");
  const [syncState, setSyncState] = useState<SyncState>("idle");
  const [syncMessage, setSyncMessage] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [pendingFocusValidation, setPendingFocusValidation] = useState(false);
  const [selectedRelease, setSelectedRelease] = useState<TracklistTarget | null>(null);
  const [spinning, setSpinning] = useState(false);
  const [spinError, setSpinError] = useState("");
  const [spinAnimating, setSpinAnimating] = useState(false);
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
  }, [debouncedQuery, debouncedYear, debouncedGenre, unmatchedOnly, showValue]);

  useEffect(() => {
    if (!pageVisible) return;
    let cancelled = false;
    const controller = new AbortController();
    const shouldValidateFocus = pendingFocusValidation;
    setLoading(true);
    setError("");
    fetchReleases({
      limit,
      q: debouncedQuery || undefined,
      year: debouncedYear || undefined,
      genres: debouncedGenre ? [debouncedGenre] : undefined,
      unmatched: unmatchedOnly || undefined,
      withValue: showValue || undefined,
    }, { signal: controller.signal })
      .then((payload) => {
        if (cancelled) return;
        const nextReleases = payload.data ?? [];
        setReleases(nextReleases);
        if (
          shouldValidateFocus
          && focusedReleaseId != null
          && !nextReleases.some((release) => release.discogs_release_id === focusedReleaseId)
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
        setError(err instanceof Error ? err.message : "Failed to load collection.");
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
  }, [debouncedQuery, debouncedYear, debouncedGenre, unmatchedOnly, showValue, limit, reloadToken, pageVisible]);

  useEffect(() => {
    if (!pageVisible) return;
    let cancelled = false;
    const controller = new AbortController();
    setSummaryLoading(true);
    setSummaryError("");
    fetchReleaseSummary({
      q: debouncedQuery || undefined,
      year: debouncedYear || undefined,
      genres: debouncedGenre ? [debouncedGenre] : undefined,
      unmatched: unmatchedOnly || undefined,
    }, { signal: controller.signal })
      .then((payload) => {
        if (cancelled) return;
        setSummary(payload.data ?? null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof Error && err.name === "AbortError") return;
        setSummaryError(
          err instanceof Error ? err.message : "Failed to load collection summary.",
        );
      })
      .finally(() => {
        if (!cancelled) setSummaryLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [debouncedQuery, debouncedYear, debouncedGenre, unmatchedOnly, reloadToken, pageVisible]);

  function clearFilters() {
    setQuery("");
    setYearFilter("");
    setGenreFilter("");
    setUnmatchedOnly(false);
    setShowValue(false);
    setSortKey("artist_asc");
    setLimit(PAGE_SIZE);
  }

  const sorted = sortReleases(releases, sortKey);

  function openTracklist(target: TracklistTarget) {
    setSelectedRelease(target);
  }

  function clearFocus() {
    const next = new URLSearchParams(searchParams);
    next.delete("focus");
    setSearchParams(next, { replace: true });
  }

  function handleSpin() {
    setSpinning(true);
    setSpinError("");
    spinCollection({
      q: debouncedQuery || undefined,
      year: debouncedYear || undefined,
      genre: debouncedGenre || undefined,
      unmatched: unmatchedOnly || undefined,
    })
      .then((payload) => {
        const id = payload.data?.discogs_release_id;
        if (id) {
          const next = new URLSearchParams(searchParams);
          next.set("focus", String(id));
          setSearchParams(next, { replace: true });
          setSpinAnimating(true);
          setTimeout(() => setSpinAnimating(false), 800);
        }
      })
      .catch((err: unknown) => {
        setSpinError(err instanceof Error ? err.message : "Spin failed.");
      })
      .finally(() => {
        setSpinning(false);
      });
  }

  function handleSyncCollection() {
    setSyncState("syncing");
    setSyncMessage("");
    syncCollection()
      .then((payload) => {
        const summary = payload.data;
        if (!summary) {
          throw new Error("Collection sync completed without a summary.");
        }
        setSyncState("done");
        setSyncMessage(formatSyncSummary(summary));
        setPendingFocusValidation(true);
        setReloadToken((value) => value + 1);
      })
      .catch((err: unknown) => {
        setSyncState("error");
        setSyncMessage(err instanceof Error ? err.message : "Collection sync failed.");
      });
  }

  function handleRowKeyDown(event: KeyboardEvent<HTMLLIElement>, release: Release) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openTracklist({
        discogs_release_id: release.discogs_release_id,
        title: release.title,
        artist: release.artist,
      });
    }
  }

  return (
    <main className="app-page">
      <header className="app-page__header">
        <div>
          <h1 className="app-page__title">Collection</h1>
        </div>
      </header>

      {focusedReleaseId ? (
        <FocusedReleaseCard
          releaseId={focusedReleaseId}
          scope="collection"
          onClear={clearFocus}
          spinAnimating={spinAnimating}
          onOpenTracklist={(release) =>
            openTracklist({
              discogs_release_id: release.discogs_release_id,
              title: release.title,
              artist: release.artist,
            })
          }
        />
      ) : null}

      <section className="app-summary-grid" aria-label="Collection summary">
        <article className="app-surface app-summary-card">
          <p className="app-summary-card__label">LPs</p>
          <p className="app-summary-card__value">
            {summary && summary.format_counts_ready ? summary.lp_count : "—"}
          </p>
          <p className="app-summary-card__meta">
            {summary && summary.format_counts_ready
              ? "Explicit Discogs LP tags"
              : "Run Sync Collection to populate LP/45 format tags"}
          </p>
        </article>
        <article className="app-surface app-summary-card">
          <p className="app-summary-card__label">45s</p>
          <p className="app-summary-card__value">
            {summary && summary.format_counts_ready ? summary.rpm45_count : "—"}
          </p>
          <p className="app-summary-card__meta">
            {summary && summary.format_counts_ready
              ? "Explicit 45 / 45 RPM tags"
              : "Run Sync Collection to populate LP/45 format tags"}
          </p>
        </article>
        <article className="app-surface app-summary-card">
          <p className="app-summary-card__label">Median</p>
          <p className="app-summary-card__value">{formatSummaryPrice(summary)}</p>
          <p className="app-summary-card__meta">
            {summary && summary.priced_release_count > 0
              ? summary.mixed_currencies
                ? `Summed across ${summary.priced_release_count} priced releases with mixed currencies`
                : `Summed across ${summary.priced_release_count} priced releases`
              : "No priced releases in the current result set"}
          </p>
        </article>
        <article className="app-surface app-summary-card">
          <p className="app-summary-card__label">Most Recently Added</p>
          <p className="app-summary-card__value app-summary-card__value--small">
            {formatLocalDateTime(summary?.most_recent_added_at)}
          </p>
          <p className="app-summary-card__meta">
            {summary?.most_recent_release_artist && summary?.most_recent_release_title
              ? `${summary.most_recent_release_artist} — ${summary.most_recent_release_title}`
              : "No added timestamp available"}
          </p>
        </article>
      </section>

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
            <input type="checkbox" checked={unmatchedOnly} onChange={(e) => setUnmatchedOnly(e.target.checked)} />
            Unmatched only
          </label>
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
            className="app-button app-button--primary"
            onClick={handleSpin}
            disabled={spinning}
          >
            {spinning ? <><span className="app-spinner" />Spinning…</> : "Spin"}
          </button>
          <button
            type="button"
            className="app-button"
            onClick={handleSyncCollection}
            disabled={syncState === "syncing"}
          >
            {syncState === "syncing" ? "Syncing…" : "Sync Collection"}
          </button>
        </div>
      </section>

      {syncMessage ? (
        <p className={`app-message ${syncState === "error" ? "app-message--error" : "app-message--success"}`}>
          {syncMessage}
        </p>
      ) : null}
      {spinError ? <p className="app-message app-message--error">{spinError}</p> : null}
      {error ? <p className="app-message app-message--error">{error}</p> : null}
      {summaryError ? <p className="app-message app-message--error">{summaryError}</p> : null}
      {summaryLoading ? (
        <p className="app-message app-message--subtle">Loading collection summary…</p>
      ) : null}
      {loading && releases.length === 0 ? <p className="app-message app-message--subtle">Loading releases…</p> : null}
      {!loading && !error && releases.length === 0 ? <p className="app-message app-message--subtle">No releases found.</p> : null}

      <ul className="app-record-list">
        {sorted.map((release) => {
          const isFocused = focusedReleaseId === release.discogs_release_id;
          return (
            <li
              key={release.discogs_release_id}
              className={`app-surface app-record app-record--interactive${isFocused ? " app-record--focused" : ""}`}
              onClick={() =>
                openTracklist({
                  discogs_release_id: release.discogs_release_id,
                  title: release.title,
                  artist: release.artist,
                })
              }
              onKeyDown={(event) => handleRowKeyDown(event, release)}
              tabIndex={0}
              aria-current={isFocused ? "true" : undefined}
            >
              <div className="app-record__header">
                <p className="app-record__title">
                  <strong>{release.artist}</strong> — {release.title}
                  {release.year ? <span className="app-record__year"> ({release.year})</span> : null}
                </p>
                {showValue && release.value?.price_median != null ? (
                  <span className="app-record__price">
                    {release.value.price_median.toFixed(2)} {release.value.currency}
                  </span>
                ) : null}
              </div>
              {release.genres.length > 0 || release.styles.length > 0 ? (
                <div className="app-tag-list" style={{ marginTop: "0.5rem" }}>
                  {[...release.genres, ...release.styles].slice(0, 3).map((tag) => (
                    <span key={tag} className="app-tag" style={pillStyle}>{tag}</span>
                  ))}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>

      {selectedRelease !== null ? (
        <TracklistModal
          releaseId={selectedRelease.discogs_release_id}
          releaseTitle={selectedRelease.title}
          releaseArtist={selectedRelease.artist}
          onClose={() => setSelectedRelease(null)}
        />
      ) : null}

      {releases.length === limit ? (
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
