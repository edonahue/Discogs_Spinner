import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchHiddenGems,
  fetchValueDashboard,
  fetchValueQueue,
  HiddenGemsPayload,
  postJson,
  ValueDashboard,
  ValueRefreshQueue,
} from "../api";
import { usePageVisible } from "../hooks/usePageVisible";

function formatCurrency(value: number | null, currency: string): string {
  if (value == null) return "—";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`;
  }
}

export function ValuePage() {
  const [dashboard, setDashboard] = useState<ValueDashboard | null>(null);
  const [queue, setQueue] = useState<ValueRefreshQueue | null>(null);
  const [gems, setGems] = useState<HiddenGemsPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [gemsError, setGemsError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState("");
  const pageVisible = usePageVisible();

  function loadDashboard(signal?: AbortSignal) {
    setLoading(true);
    setError("");
    setGemsError("");

    Promise.all([
      fetchValueDashboard({ top_limit: 10 }, { signal }),
      fetchValueQueue({ limit: 25, stale_days: 30 }, { signal }),
    ])
      .then(([dashPayload, queuePayload]) => {
        setDashboard(dashPayload.data);
        setQueue(queuePayload.data);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to load value dashboard.");
      })
      .finally(() => {
        if (!signal?.aborted) setLoading(false);
      });

    fetchHiddenGems({ min_median: 25, limit: 10 }, { signal })
      .then((gemsPayload) => {
        setGems(gemsPayload.data);
        setGemsError("");
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setGems(null);
        setGemsError(err instanceof Error ? err.message : "Failed to load hidden gems.");
      });
  }

  useEffect(() => {
    if (!pageVisible) return;
    const controller = new AbortController();
    loadDashboard(controller.signal);
    return () => controller.abort();
  }, [pageVisible]);

  function handleRefresh() {
    setRefreshing(true);
    setRefreshMsg("");
    postJson<unknown>("/value/refresh", { from_missing: false, limit: 50, stale_days: 7 })
      .then(() => {
        setRefreshMsg("Refresh started. Reloading data…");
        setTimeout(() => {
          setRefreshMsg("");
          if (document.hidden) return;
          loadDashboard();
        }, 3000);
      })
      .catch((err: unknown) => {
        setRefreshMsg(err instanceof Error ? err.message : "Refresh failed.");
      })
      .finally(() => setRefreshing(false));
  }

  const hasData = dashboard && dashboard.top_releases.length > 0;

  return (
    <main className="app-page">
      <header className="app-page__header">
        <div>
          <h1 className="app-page__title">Collection Value</h1>
          <p className="app-page__subtitle">
            Review price leaders and refresh candidates, then jump back into the collection with the target release focused.
          </p>
        </div>
        <div className="app-inline-actions">
          {dashboard?.last_updated ? (
            <span className="app-muted">Last updated {dashboard.last_updated}</span>
          ) : null}
          <button
            type="button"
            className="app-button app-button--primary"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing…" : "Refresh Values"}
          </button>
        </div>
      </header>

      {refreshMsg ? (
        <p className={`app-message ${refreshMsg.toLowerCase().includes("fail") ? "app-message--error" : "app-message--success"}`}>
          {refreshMsg}
        </p>
      ) : null}

      {error ? <p className="app-message app-message--error">{error}</p> : null}
      {loading ? <p className="app-message app-message--subtle">Loading market value dashboard…</p> : null}

      {!loading && !error && !hasData ? (
        <p className="app-message app-message--subtle">Run a value refresh to see market prices.</p>
      ) : null}

      {hasData ? (
        <section className="app-surface app-table-shell">
          <h2 className="app-page__section-title">Top Priced Releases</h2>
          <div className="app-table-wrap">
            <table className="app-table responsive-stack">
              <thead>
                <tr>
                  <th>Artist</th>
                  <th>Title</th>
                  <th className="is-right">Median</th>
                  <th className="is-right">High</th>
                  <th>Currency</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.top_releases.map((release) => (
                  <tr key={release.discogs_release_id}>
                    <td data-label="Artist">{release.artist}</td>
                    <td data-label="Title">{release.title}</td>
                    <td data-label="Median" className="is-right">{formatCurrency(release.price_median, release.currency)}</td>
                    <td data-label="High" className="is-right">{formatCurrency(release.price_high, release.currency)}</td>
                    <td data-label="Currency">{release.currency}</td>
                    <td data-label="Action">
                      <Link className="app-link-button app-link-button--ghost" to={`/collection?focus=${release.discogs_release_id}`}>
                        View in Collection
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {gems && gems.gems.length > 0 ? (
        <section className="app-surface app-table-shell" style={{ marginTop: "1rem" }}>
          <div className="app-page__header" style={{ marginBottom: "0.5rem" }}>
            <div>
              <h2 className="app-page__section-title">Hidden Gems</h2>
              <p className="app-page__subtitle">
                Owned releases that are quietly valuable AND hard to find on the Discogs marketplace right now.
              </p>
            </div>
          </div>
          <div className="app-table-wrap">
            <table className="app-table app-table--compact responsive-stack">
              <thead>
                <tr>
                  <th>Artist</th>
                  <th>Title</th>
                  <th>Year</th>
                  <th className="is-right">Median</th>
                  <th className="is-right">For Sale</th>
                  <th>Why</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {gems.gems.map((gem) => (
                  <tr key={gem.discogs_release_id}>
                    <td data-label="Artist">{gem.artist ?? "—"}</td>
                    <td data-label="Title">{gem.title ?? "—"}</td>
                    <td data-label="Year">{gem.year ?? "—"}</td>
                    <td data-label="Median" className="is-right">
                      {formatCurrency(gem.market_median, gem.market_currency ?? "USD")}
                    </td>
                    <td data-label="For Sale" className="is-right">
                      {gem.num_for_sale == null ? "—" : gem.num_for_sale}
                    </td>
                    <td data-label="Why">{gem.reasons.join(" · ") || "—"}</td>
                    <td data-label="Action">
                      <Link
                        className="app-link-button app-link-button--ghost"
                        to={`/collection?focus=${gem.discogs_release_id}`}
                      >
                        View in Collection
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {gemsError ? (
        <p className="app-message app-message--subtle">
          Hidden Gems are temporarily unavailable: {gemsError}
        </p>
      ) : null}

      <section className="app-surface app-table-shell" style={{ marginTop: "1rem" }}>
        <div className="app-page__header" style={{ marginBottom: "1rem" }}>
          <div>
            <h2 className="app-page__section-title">Refresh Queue</h2>
            <p className="app-page__subtitle">
              Releases below can jump back into the collection detail surface for follow-up.
            </p>
          </div>
        </div>

        {queue !== null && queue.total_candidates === 0 ? (
          <p className="app-message app-message--subtle">All prices are up to date.</p>
        ) : null}
        {queue !== null && queue.total_candidates > 0 ? (
          <>
            <div className="app-inline-summary" style={{ marginBottom: "1rem" }}>
              <span className="app-muted">Missing <strong>{queue.missing_count}</strong></span>
              <span className="app-muted">Unpriced <strong>{queue.unpriced_count}</strong></span>
              <span className="app-muted">Stale (&gt;{queue.stale_days}d) <strong>{queue.stale_count}</strong></span>
            </div>
            <div className="app-table-wrap">
              <table className="app-table app-table--compact responsive-stack">
                <thead>
                  <tr>
                    <th>Artist</th>
                    <th>Title</th>
                    <th>Reason</th>
                    <th className="is-right">Median</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {queue.queue.map((item) => (
                    <tr key={item.discogs_release_id}>
                      <td data-label="Artist">{item.artist}</td>
                      <td data-label="Title">{item.title}</td>
                      <td data-label="Reason">{item.market_need_reason}</td>
                      <td data-label="Median" className="is-right">{item.market_median != null ? item.market_median.toFixed(2) : "—"}</td>
                      <td data-label="Action">
                        <Link className="app-link-button app-link-button--ghost" to={`/collection?focus=${item.discogs_release_id}`}>
                          View in Collection
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </section>
    </main>
  );
}
