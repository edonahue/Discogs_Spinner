import { useEffect, useState } from "react";
import { fetchValueDashboard, postJson, ValueDashboard } from "../api";

export function ValuePage() {
  const [dashboard, setDashboard] = useState<ValueDashboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState("");

  function loadDashboard() {
    setLoading(true);
    setError("");
    fetchValueDashboard({ top_limit: 10 })
      .then((payload) => setDashboard(payload.data))
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
    </main>
  );
}
