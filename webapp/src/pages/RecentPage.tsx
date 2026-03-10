import { useEffect, useState } from "react";
import { fetchRecentReleases, Release } from "../api";

const pillStyle: React.CSSProperties = {
  display: "inline-block",
  background: "#f0f0f0",
  borderRadius: "4px",
  padding: "0 0.4rem",
  fontSize: "0.75rem",
  marginRight: "0.25rem",
  color: "#555",
};

const DAYS_OPTIONS = [7, 14, 30, 90];

export function RecentPage() {
  const [releases, setReleases] = useState<Release[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    fetchRecentReleases({ days, limit: 50 })
      .then((payload) => {
        if (!cancelled) setReleases(payload.data?.releases ?? []);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load recent releases.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [days]);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "0 2rem 2rem", lineHeight: 1.5 }}>
      <h2>Recently Added</h2>

      <div style={{ marginBottom: "1rem" }}>
        <label style={{ fontSize: "0.9rem", marginRight: "0.5rem" }}>Last:</label>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          style={{ padding: "0.3rem 0.5rem", fontSize: "0.9rem" }}
        >
          {DAYS_OPTIONS.map((d) => (
            <option key={d} value={d}>
              {d} days
            </option>
          ))}
        </select>
      </div>

      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
      {loading ? <p>Loading…</p> : null}
      {!loading && !error && releases.length === 0 ? (
        <p style={{ color: "#888" }}>No releases added in the last {days} days.</p>
      ) : null}

      <ul style={{ listStyle: "none", padding: 0 }}>
        {releases.map((r) => (
          <li key={r.discogs_release_id} style={{ padding: "0.5rem 0", borderBottom: "1px solid #eee" }}>
            <div>
              <strong>{r.artist}</strong> — {r.title}
              {r.year ? (
                <span style={{ color: "#888", marginLeft: "0.5rem" }}>({r.year})</span>
              ) : null}
            </div>
            {r.genres.length > 0 || r.styles.length > 0 ? (
              <div style={{ marginTop: "0.2rem" }}>
                {[...r.genres, ...r.styles].slice(0, 3).map((tag) => (
                  <span key={tag} style={pillStyle}>
                    {tag}
                  </span>
                ))}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </main>
  );
}
