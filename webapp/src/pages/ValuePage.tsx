import { useEffect, useState } from "react";
import { fetchValueDashboard, fetchValueQueue, postJson, ValueDashboard, ValueRefreshQueue } from "../api";

export function ValuePage() {
  const [dashboard, setDashboard] = useState<ValueDashboard | null>(null);
  const [queue, setQueue] = useState<ValueRefreshQueue | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState("");

  function loadDashboard() {
    setLoading(true);
    setError("");
    Promise.all([
      fetchValueDashboard({ top_limit: 10 }),
      fetchValueQueue({ limit: 25, stale_days: 30 }),
    ])
      .then(([dashPayload, queuePayload]) => {
        setDashboard(dashPayload.data);
        setQueue(queuePayload.data);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load value dashboard."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  function handleRefresh() {
    setRefreshing(true);
    setRefreshMsg("");
    postJson<unknown>("/value/refresh", { from_missing: false, limit: 50, stale_days: 7 })
      .then(() => {
        setRefreshMsg("Refresh started. Reloading data…");
        setTimeout(() => {
          setRefreshMsg("");
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
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "0 2rem 2rem", lineHeight: 1.5 }}>
      <h2>Collection Value</h2>

      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {dashboard?.last_updated ? (
          <span style={{ color: "#555", fontSize: "0.9rem" }}>
            Last updated: {dashboard.last_updated}
          </span>
        ) : null}
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{ padding: "0.4rem 1rem" }}
        >
          {refreshing ? "Refreshing…" : "Refresh Values"}
        </button>
      </div>

      {refreshMsg ? (
        <p style={{ color: refreshMsg.includes("failed") || refreshMsg.includes("Failed") ? "crimson" : "#2a7a2a" }}>
          {refreshMsg}
        </p>
      ) : null}

      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
      {loading ? <p>Loading…</p> : null}

      {!loading && !error && !hasData ? (
        <p style={{ color: "#555" }}>Run a value refresh to see market prices.</p>
      ) : null}

      {hasData ? (
        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.95rem" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #ddd", textAlign: "left" }}>
              <th style={{ padding: "0.4rem 0.75rem 0.4rem 0" }}>Artist</th>
              <th style={{ padding: "0.4rem 0.75rem" }}>Title</th>
              <th style={{ padding: "0.4rem 0.75rem", textAlign: "right" }}>Median</th>
              <th style={{ padding: "0.4rem 0.75rem", textAlign: "right" }}>High</th>
              <th style={{ padding: "0.4rem 0.75rem" }}>Currency</th>
            </tr>
          </thead>
          <tbody>
            {dashboard.top_releases.map((r) => (
              <tr key={r.discogs_release_id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "0.4rem 0.75rem 0.4rem 0" }}>{r.artist}</td>
                <td style={{ padding: "0.4rem 0.75rem" }}>{r.title}</td>
                <td style={{ padding: "0.4rem 0.75rem", textAlign: "right", color: "#2a7a2a", fontWeight: 500 }}>
                  {r.price_median != null ? r.price_median.toFixed(2) : "—"}
                </td>
                <td style={{ padding: "0.4rem 0.75rem", textAlign: "right" }}>
                  {r.price_high != null ? r.price_high.toFixed(2) : "—"}
                </td>
                <td style={{ padding: "0.4rem 0.75rem", color: "#888" }}>{r.currency}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}

      <h3 style={{ marginTop: "2rem" }}>Refresh Queue</h3>
      {queue !== null && queue.total_candidates === 0 ? (
        <p style={{ color: "#555" }}>All prices are up to date.</p>
      ) : null}
      {queue !== null && queue.total_candidates > 0 ? (
        <>
          <div style={{ display: "flex", gap: "1.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.9rem", color: "#555" }}>
              Missing: <strong>{queue.missing_count}</strong>
            </span>
            <span style={{ fontSize: "0.9rem", color: "#555" }}>
              Unpriced: <strong>{queue.unpriced_count}</strong>
            </span>
            <span style={{ fontSize: "0.9rem", color: "#555" }}>
              Stale (&gt;{queue.stale_days}d): <strong>{queue.stale_count}</strong>
            </span>
          </div>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.9rem" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #ddd", textAlign: "left" }}>
                <th style={{ padding: "0.3rem 0.75rem 0.3rem 0" }}>Artist</th>
                <th style={{ padding: "0.3rem 0.75rem" }}>Title</th>
                <th style={{ padding: "0.3rem 0.75rem" }}>Reason</th>
                <th style={{ padding: "0.3rem 0.75rem", textAlign: "right" }}>Median</th>
              </tr>
            </thead>
            <tbody>
              {queue.queue.map((item) => (
                <tr key={item.discogs_release_id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "0.3rem 0.75rem 0.3rem 0" }}>{item.artist}</td>
                  <td style={{ padding: "0.3rem 0.75rem" }}>{item.title}</td>
                  <td style={{ padding: "0.3rem 0.75rem" }}>
                    <span style={{
                      fontSize: "0.8rem",
                      padding: "0.1rem 0.4rem",
                      borderRadius: "3px",
                      background: item.market_need_reason === "missing" ? "#fde8e8"
                        : item.market_need_reason === "unpriced" ? "#fdf3e0"
                        : "#e8f0fe",
                      color: item.market_need_reason === "missing" ? "crimson"
                        : item.market_need_reason === "unpriced" ? "#b8860b"
                        : "#1a56a0",
                    }}>
                      {item.market_need_reason}
                    </span>
                  </td>
                  <td style={{ padding: "0.3rem 0.75rem", textAlign: "right", color: "#888" }}>
                    {item.market_median != null ? item.market_median.toFixed(2) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}
    </main>
  );
}
