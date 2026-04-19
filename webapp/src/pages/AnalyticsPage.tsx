import { useEffect, useState } from "react";
import { CollectionAnalytics, fetchAnalytics } from "../api";

const thStyle: React.CSSProperties = {
  padding: "0.4rem 0.75rem 0.4rem 0",
  textAlign: "left",
};
const tdStyle: React.CSSProperties = {
  padding: "0.35rem 0.75rem 0.35rem 0",
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
      <h3 className="app-page__section-title">{title}</h3>
      {rows.length === 0 ? (
        <p className="app-message app-message--subtle">No data.</p>
      ) : (
        <div className="app-table-wrap">
          <table className="app-table app-table--compact responsive-stack app-rank-table">
          <thead>
            <tr>
              <th style={thStyle}>Rank</th>
              <th style={thStyle}>Name</th>
              <th style={{ ...thStyle, textAlign: "right", paddingRight: 0 }}>Releases</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={String(row[labelKey])}>
                <td data-label="Rank" style={{ ...tdStyle, color: "#aaa", width: "2rem" }}>{i + 1}</td>
                <td data-label="Name" style={tdStyle}>{String(row[labelKey])}</td>
                <td data-label="Releases" style={tdRight}>{row.count}</td>
              </tr>
            ))}
          </tbody>
          </table>
        </div>
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
      <h3 className="app-page__section-title">{title}</h3>
      {rows.length === 0 ? (
        <p className="app-message app-message--subtle">No data.</p>
      ) : (
        <div className="app-table-wrap">
          <table className="app-table app-table--compact responsive-stack app-rank-table">
          <thead>
            <tr>
              <th style={thStyle}>Year</th>
              <th style={{ ...thStyle, textAlign: "right", paddingRight: 0 }}>Releases</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.year}>
                <td data-label="Year" style={tdStyle}>{row.year}</td>
                <td data-label="Releases" style={tdRight}>{row.count}</td>
              </tr>
            ))}
          </tbody>
          </table>
        </div>
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
    <main className="app-page">
      <header className="app-page__header">
        <div>
          <h1 className="app-page__title">Collection Analytics</h1>
          <p className="app-page__subtitle">
            Analytics stays aggregate-only, but the dense ranking tables now stack cleanly instead of clipping at smaller desktop widths.
          </p>
        </div>
      </header>

      {error ? <p className="app-message app-message--error">{error}</p> : null}
      {loading ? <p className="app-message app-message--subtle">Loading analytics…</p> : null}

      {!loading && !error && data !== null ? (
        <>
          <section className="app-stat-grid" style={{ marginBottom: "1rem" }}>
            <article className="app-surface app-stat-card">
              <p className="app-stat-card__label">Active releases</p>
              <p className="app-stat-card__value">{data.release_count_active}</p>
            </article>
            <article className="app-surface app-stat-card">
              <p className="app-stat-card__label">Mapped</p>
              <p className="app-stat-card__value" style={{ color: "var(--success)" }}>{data.mapped_count}</p>
            </article>
            <article className="app-surface app-stat-card">
              <p className="app-stat-card__label">Unmatched</p>
              <p className="app-stat-card__value" style={{ color: "#b8860b" }}>{data.unmatched_count}</p>
            </article>
            {data.release_count_active > 0 ? (
              <article className="app-surface app-stat-card">
                <p className="app-stat-card__label">Mapping rate</p>
                <p className="app-stat-card__value">
                  {Math.round((data.mapped_count / data.release_count_active) * 100)}%
                </p>
              </article>
            ) : null}
          </section>

          <section className="app-card-grid">
            <div className="app-surface app-card">
              <RankTable title="Top Genres" rows={data.top_genres} labelKey="genre" />
            </div>
            <div className="app-surface app-card">
              <RankTable title="Top Styles" rows={data.top_styles} labelKey="style" />
            </div>
            <div className="app-surface app-card">
              <RankTable title="Top Artists" rows={data.top_artists} labelKey="artist" />
            </div>
            <div className="app-surface app-card">
              <YearTable title="By Release Year" rows={data.by_release_year} />
            </div>
            <div className="app-surface app-card">
              <YearTable title="Acquisition Timeline" rows={data.acquisition_timeline} />
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}
