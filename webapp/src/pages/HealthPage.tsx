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
    <main className="app-page">
      <header className="app-page__header">
        <div>
          <h1 className="app-page__title">Collection Health</h1>
        </div>
      </header>

      {error ? <p className="app-message app-message--error">{error}</p> : null}
      {loading ? <p className="app-message app-message--subtle">Loading collection health…</p> : null}

      {!loading && !error && health !== null ? (
        <>
          <section className="app-surface app-stat-card" style={{ marginBottom: "1rem" }}>
            <p className="app-stat-card__label">Health score</p>
            <p className="app-stat-card__value" style={{ color: scoreColor(health.score) }}>
              {health.score}
              <span style={{ fontSize: "1rem", color: "var(--muted)", marginLeft: "0.35rem" }}>/100</span>
            </p>
            <p className="app-stat-card__meta">{health.total_active} releases</p>
          </section>

          <section className="app-surface app-table-shell">
            <div className="app-table-wrap">
              <table className="app-table responsive-stack">
                <thead>
                  <tr>
                    <th>Label</th>
                    <th className="is-right">Gap</th>
                    <th className="is-right">Percent</th>
                    <th className="is-right">Deduction</th>
                  </tr>
                </thead>
                <tbody>
                  {health.buckets.map((bucket) => (
                    <tr key={bucket.name}>
                      <td data-label="Label">{bucket.label}</td>
                      <td data-label="Gap" className="is-right">{bucket.gap_count}</td>
                      <td data-label="Percent" className="is-right">{bucket.gap_pct.toFixed(1)}%</td>
                      <td
                        data-label="Deduction"
                        className="is-right"
                        style={{ color: bucket.deduction > 0 ? "var(--danger)" : "var(--muted)" }}
                      >
                        {bucket.deduction > 0 ? `-${bucket.deduction.toFixed(1)}` : "0"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}
