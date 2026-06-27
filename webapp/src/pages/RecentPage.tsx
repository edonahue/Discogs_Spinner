import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchRecentReleases, Release } from "../api";

const pillStyle: React.CSSProperties = {
  display: "inline-flex",
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
    <main className="app-page">
      <header className="app-page__header">
        <div>
          <h1 className="app-page__title">Recently Added</h1>
          <p className="app-page__subtitle">
            Scan recent pickups and jump back into the collection with the selected release focused.
          </p>
        </div>
        <div className="app-inline-actions">
          <label className="app-stack-label" htmlFor="recent-days">
            Last
          </label>
          <select
            id="recent-days"
            className="app-select"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            {DAYS_OPTIONS.map((d) => (
              <option key={d} value={d}>
                {d} days
              </option>
            ))}
          </select>
        </div>
      </header>

      {error ? <p className="app-message app-message--error">{error}</p> : null}
      {loading ? <p className="app-message app-message--subtle">Loading recent releases…</p> : null}
      {!loading && !error && releases.length === 0 ? (
        <p className="app-message app-message--subtle">
          No releases added in the last {days} days.
        </p>
      ) : null}

      <ul className="app-record-list">
        {releases.map((release) => (
          <li key={release.discogs_release_id} className="app-surface app-record">
            <div className="app-record__header">
              <p className="app-record__title">
                <strong>{release.artist}</strong> — {release.title}
                {release.year ? <span className="app-record__year"> ({release.year})</span> : null}
              </p>
              <Link
                className="app-link-button app-link-button--ghost"
                to={`/collection?focus=${release.discogs_release_id}`}
              >
                View in Collection
              </Link>
            </div>
            {release.genres.length > 0 || release.styles.length > 0 ? (
              <div className="app-tag-list" style={{ marginTop: "0.5rem" }}>
                {[...release.genres, ...release.styles].slice(0, 3).map((tag) => (
                  <span key={tag} className="app-tag" style={pillStyle}>
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
