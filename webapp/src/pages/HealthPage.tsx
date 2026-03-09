import { useEffect, useState } from "react";
import { CollectionHealth, fetchCollectionHealth } from "../api";

function scoreColor(score: number): string {
  if (score >= 80) return "#2a7a2a";
  if (score >= 50) return "#b8860b";
  return "crimson";
}

export function HealthPage() {
  const [health, setHealth] = useState<CollectionHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    fetchCollectionHealth()
      .then((payload) => setHealth(payload.data))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load health data."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "0 2rem 2rem", lineHeight: 1.5 }}>
      <h2>Collection Health</h2>

      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
      {loading ? <p>Loading…</p> : null}

      {!loading && !error && health !== null ? (
        <>
          <div style={{ marginBottom: "1.5rem" }}>
            <span style={{
              display: "inline-block",
              fontSize: "3rem",
              fontWeight: 700,
              color: scoreColor(health.score),
              lineHeight: 1,
            }}>
              {health.score}
            </span>
            <span style={{ fontSize: "1.5rem", color: "#888", marginLeft: "0.25rem" }}>/100</span>
            <p style={{ margin: "0.25rem 0 0", color: "#555", fontSize: "0.9rem" }}>
              {health.total_active} releases
            </p>
          </div>

          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.95rem" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #ddd", textAlign: "left" }}>
                <th style={{ padding: "0.4rem 0.75rem 0.4rem 0" }}>Label</th>
                <th style={{ padding: "0.4rem 0.75rem", textAlign: "right" }}>Gap</th>
                <th style={{ padding: "0.4rem 0.75rem", textAlign: "right" }}>%</th>
                <th style={{ padding: "0.4rem 0.75rem", textAlign: "right" }}>Deduction</th>
              </tr>
            </thead>
            <tbody>
              {health.buckets.map((b) => (
                <tr key={b.name} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "0.4rem 0.75rem 0.4rem 0" }}>{b.label}</td>
                  <td style={{ padding: "0.4rem 0.75rem", textAlign: "right" }}>{b.gap_count}</td>
                  <td style={{ padding: "0.4rem 0.75rem", textAlign: "right", color: "#888" }}>
                    {b.gap_pct.toFixed(1)}%
                  </td>
                  <td style={{ padding: "0.4rem 0.75rem", textAlign: "right", color: b.deduction > 0 ? "crimson" : "#555" }}>
                    {b.deduction > 0 ? `-${b.deduction.toFixed(1)}` : "0"}
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
