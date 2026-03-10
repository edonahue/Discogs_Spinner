import { useEffect, useState } from "react";
import { CollectionAnalytics, fetchAnalytics } from "../api";

const thStyle: React.CSSProperties = {
  padding: "0.4rem 0.75rem 0.4rem 0",
  textAlign: "left",
  borderBottom: "2px solid #ddd",
};
const tdStyle: React.CSSProperties = {
  padding: "0.35rem 0.75rem 0.35rem 0",
  borderBottom: "1px solid #eee",
};
const tdRight: React.CSSProperties = { ...tdStyle, textAlign: "right", paddingRight: 0 };

function RankTable({
  title,
  rows,
  labelKey,
}: {
  title: string;
  rows: { count: number; [key: string]: string | number }[];
  labelKey: string;
}) {
  return (
    <div style={{ marginBottom: "2rem" }}>
      <h3 style={{ marginBottom: "0.5rem", fontSize: "1rem" }}>{title}</h3>
      {rows.length === 0 ? (
        <p style={{ color: "#888", fontSize: "0.9rem" }}>No data.</p>
      ) : (
        <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: "480px", fontSize: "0.92rem" }}>
          <thead>
            <tr>
              <th style={thStyle}>#</th>
              <th style={thStyle}>Name</th>
              <th style={{ ...thStyle, textAlign: "right", paddingRight: 0 }}>Releases</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={String(row[labelKey])}>
                <td style={{ ...tdStyle, color: "#aaa", width: "2rem" }}>{i + 1}</td>
                <td style={tdStyle}>{String(row[labelKey])}</td>
                <td style={tdRight}>{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function YearTable({
  title,
  rows,
}: {
  title: string;
  rows: { year: number; count: number }[];
}) {
  return (
    <div style={{ marginBottom: "2rem" }}>
      <h3 style={{ marginBottom: "0.5rem", fontSize: "1rem" }}>{title}</h3>
      {rows.length === 0 ? (
        <p style={{ color: "#888", fontSize: "0.9rem" }}>No data.</p>
      ) : (
        <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: "320px", fontSize: "0.92rem" }}>
          <thead>
            <tr>
              <th style={thStyle}>Year</th>
              <th style={{ ...thStyle, textAlign: "right", paddingRight: 0 }}>Releases</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.year}>
                <td style={tdStyle}>{row.year}</td>
                <td style={tdRight}>{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function AnalyticsPage() {
  const [data, setData] = useState<CollectionAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    fetchAnalytics({ limit: 10 })
      .then((payload) => setData(payload.data))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load analytics.")
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "0 2rem 2rem", lineHeight: 1.5 }}>
      <h2>Collection Analytics</h2>

      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
      {loading ? <p>Loading…</p> : null}

      {!loading && !error && data !== null ? (
        <>
          <div
            style={{
              display: "flex",
              gap: "2rem",
              marginBottom: "2rem",
              padding: "1rem",
              background: "#f8f8f8",
              borderRadius: "6px",
              fontSize: "0.95rem",
            }}
          >
            <div>
              <div style={{ fontSize: "1.8rem", fontWeight: 700 }}>{data.release_count_active}</div>
              <div style={{ color: "#555" }}>Active releases</div>
            </div>
            <div>
              <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "#2a7a2a" }}>
                {data.mapped_count}
              </div>
              <div style={{ color: "#555" }}>Mapped</div>
            </div>
            <div>
              <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "#b8860b" }}>
                {data.unmatched_count}
              </div>
              <div style={{ color: "#555" }}>Unmatched</div>
            </div>
            {data.release_count_active > 0 ? (
              <div>
                <div style={{ fontSize: "1.8rem", fontWeight: 700 }}>
                  {Math.round((data.mapped_count / data.release_count_active) * 100)}%
                </div>
                <div style={{ color: "#555" }}>Mapping rate</div>
              </div>
            ) : null}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
              gap: "0 3rem",
            }}
          >
            <RankTable title="Top Genres" rows={data.top_genres} labelKey="genre" />
            <RankTable title="Top Styles" rows={data.top_styles} labelKey="style" />
            <RankTable title="Top Artists" rows={data.top_artists} labelKey="artist" />
            <YearTable title="By Release Year" rows={data.by_release_year} />
            <YearTable title="Acquisition Timeline" rows={data.acquisition_timeline} />
          </div>
        </>
      ) : null}
    </main>
  );
}
