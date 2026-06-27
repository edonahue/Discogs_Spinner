import { useEffect, useState } from "react";
import { fetchReleaseDetail, fetchWantlistDetail, ReleaseDetail } from "../api";

type FocusScope = "collection" | "wantlist";

type Props = {
  releaseId: number;
  scope: FocusScope;
  onClear: () => void;
  onOpenTracklist?: (release: ReleaseDetail) => void;
  spinAnimating?: boolean;
};

function formatCurrency(
  value: number | null | undefined,
  currency: string | null | undefined,
): string {
  if (value == null) return "Not priced";
  const normalizedCurrency = (currency || "USD").trim() || "USD";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: normalizedCurrency,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${value.toFixed(2)} ${normalizedCurrency}`;
  }
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "Unknown";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString();
}

function marketSummary(release: ReleaseDetail): string {
  const parts: string[] = [];
  if (release.market_lowest != null) {
    parts.push(`Low ${formatCurrency(release.market_lowest, release.market_currency)}`);
  }
  if (release.market_median != null) {
    parts.push(`Median ${formatCurrency(release.market_median, release.market_currency)}`);
  }
  if (release.market_highest != null) {
    parts.push(`High ${formatCurrency(release.market_highest, release.market_currency)}`);
  }
  return parts.length > 0 ? parts.join(" • ") : "No market value cached yet.";
}

function discogsReleaseUrl(releaseId: number): string {
  return `https://www.discogs.com/release/${releaseId}`;
}

export function FocusedReleaseCard({
  releaseId,
  scope,
  onClear,
  onOpenTracklist,
  spinAnimating,
}: Props) {
  const [release, setRelease] = useState<ReleaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    const request =
      scope === "wantlist"
        ? fetchWantlistDetail(releaseId, { withValue: true })
        : fetchReleaseDetail(releaseId, { withValue: true });

    request
      .then((payload) => {
        if (!cancelled) {
          setRelease(payload.data);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setRelease(null);
          setError(err instanceof Error ? err.message : "Failed to load focused release.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [releaseId, scope]);

  const scopeLabel = scope === "wantlist" ? "Focused Wantlist Detail" : "Focused Collection Detail";

  return (
    <section
      className={`app-surface app-focus-card${spinAnimating ? " app-focus-card--spin-result" : ""}`}
      aria-live="polite"
    >
      <p className="app-focus-card__eyebrow">{scopeLabel}</p>
      {loading ? (
        <p className="app-message app-message--subtle">Loading release #{releaseId}…</p>
      ) : null}
      {error ? <p className="app-message app-message--error">{error}</p> : null}
      {!loading && !error && release ? (
        <div className="app-card-stack">
          <div>
            <h3 className="app-focus-card__title">
              {release.artist} - {release.title}
            </h3>
            <p className="app-focus-card__meta">
              Discogs #{release.discogs_release_id}
              {release.year ? ` • ${release.year}` : ""}
              {release.last_synced_at ? ` • synced ${formatDate(release.last_synced_at)}` : ""}
            </p>
          </div>

          {release.genres.length > 0 || release.styles.length > 0 ? (
            <div className="app-tag-list">
              {[...release.genres, ...release.styles].slice(0, 6).map((tag) => (
                <span key={tag} className="app-tag">
                  {tag}
                </span>
              ))}
            </div>
          ) : null}

          <div className="app-focus-card__grid">
            <div className="app-focus-card__metric">
              <p className="app-focus-card__metric-label">Market</p>
              <p className="app-focus-card__metric-value">{marketSummary(release)}</p>
            </div>
            <div className="app-focus-card__metric">
              <p className="app-focus-card__metric-label">Added</p>
              <p className="app-focus-card__metric-value">{formatDate(release.added_at)}</p>
            </div>
            <div className="app-focus-card__metric">
              <p className="app-focus-card__metric-label">Spotify Mapping</p>
              <p className="app-focus-card__metric-value">
                {release.spotify_album_id ? "Mapped" : "Not mapped"}
              </p>
            </div>
          </div>

          {release.notes ? <p className="app-focus-card__note">{release.notes}</p> : null}

          <div className="app-card-actions">
            {onOpenTracklist ? (
              <button
                type="button"
                className="app-button app-button--primary"
                onClick={() => onOpenTracklist(release)}
              >
                Open Tracklist
              </button>
            ) : null}
            <a
              className="app-link-button app-link-button--ghost"
              href={discogsReleaseUrl(release.discogs_release_id)}
              target="_blank"
              rel="noreferrer"
            >
              Open Discogs
            </a>
            <button type="button" className="app-button app-button--ghost" onClick={onClear}>
              Clear Focus
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
