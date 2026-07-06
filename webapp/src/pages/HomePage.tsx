import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  CollectorInsightsPayload,
  fetchCollectorInsights,
  getJson,
  ProviderReadinessContract,
  SyncSummary,
  syncCollection,
  syncWantlist,
} from "../api";

type StatusPayload = {
  release_count_total: number;
  release_count_active: number;
  mapped_count: number;
  unmatched_count: number;
  wantlist_count: number;
  last_sync_time: string | null;
  market_value_last_updated: string | null;
  spotify_capability?: {
    addon_available: boolean;
    configured: boolean;
    action_label: string;
  };
  provider_readiness?: ProviderReadinessContract;
};

type SyncState = "idle" | "syncing" | "done" | "error";

function formatSyncSummary(label: "Collection" | "Wantlist", summary: SyncSummary): string {
  return (
    `${label} sync complete: fetched ${summary.fetched_count}, ` +
    `upserted ${summary.upserted_count}, deactivated ${summary.deactivated_count}.`
  );
}

function readinessNextActions(readiness: ProviderReadinessContract): string[] {
  if (readiness.summary.next_actions.length > 0) {
    return readiness.summary.next_actions;
  }
  return readiness.next_actions;
}

export function HomePage() {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [insights, setInsights] = useState<CollectorInsightsPayload | null>(null);
  const [error, setError] = useState<string>("");
  const [collectionSync, setCollectionSync] = useState<SyncState>("idle");
  const [collectionMsg, setCollectionMsg] = useState("");
  const [wantlistSync, setWantlistSync] = useState<SyncState>("idle");
  const [wantlistMsg, setWantlistMsg] = useState("");

  function loadStatus() {
    return Promise.all([
      getJson<StatusPayload>("/status"),
      fetchCollectorInsights({ gems_limit: 3, queue_limit: 5 }),
    ])
      .then(([statusPayload, insightsPayload]) => {
        setStatus(statusPayload.data);
        setInsights(insightsPayload.data);
        setError("");
        return statusPayload.data;
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unknown API error.");
        throw err;
      });
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getJson<StatusPayload>("/status"),
      fetchCollectorInsights({ gems_limit: 3, queue_limit: 5 }),
    ])
      .then(([statusPayload, insightsPayload]) => {
        if (cancelled) return;
        setStatus(statusPayload.data);
        setInsights(insightsPayload.data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unknown API error.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleSyncCollection() {
    setCollectionSync("syncing");
    setCollectionMsg("");
    syncCollection()
      .then((payload) => {
        const summary = payload.data;
        if (!summary) {
          throw new Error("Collection sync completed without a summary.");
        }
        setCollectionSync("done");
        setCollectionMsg(formatSyncSummary("Collection", summary));
        void loadStatus().catch(() => undefined);
      })
      .catch((err: unknown) => {
        setCollectionSync("error");
        setCollectionMsg(err instanceof Error ? err.message : "Sync failed.");
      });
  }

  function handleSyncWantlist() {
    setWantlistSync("syncing");
    setWantlistMsg("");
    syncWantlist()
      .then((payload) => {
        const summary = payload.data;
        if (!summary) {
          throw new Error("Wantlist sync completed without a summary.");
        }
        setWantlistSync("done");
        setWantlistMsg(formatSyncSummary("Wantlist", summary));
        void loadStatus().catch(() => undefined);
      })
      .catch((err: unknown) => {
        setWantlistSync("error");
        setWantlistMsg(err instanceof Error ? err.message : "Sync failed.");
      });
  }

  return (
    <main className="app-page">
      <header className="app-page__header">
        <div>
          <h1 className="app-page__title">Spinner for Discogs</h1>
          <p className="app-page__subtitle">
            Your records, your market. Browse your collection, spin something to play, and keep
            wantlist and value context close.
          </p>
        </div>
      </header>
      {error ? <p className="app-message app-message--error">{error}</p> : null}
      {!error && !status ? (
        <p className="app-message app-message--subtle">Loading status…</p>
      ) : null}
      {status ? (
        <section className="app-stat-grid">
          <article className="app-surface app-stat-card">
            <p className="app-stat-card__label">Total releases</p>
            <p className="app-stat-card__value">{status.release_count_total}</p>
          </article>
          <article className="app-surface app-stat-card">
            <p className="app-stat-card__label">Active releases</p>
            <p className="app-stat-card__value">{status.release_count_active}</p>
          </article>
          <article className="app-surface app-stat-card">
            <p className="app-stat-card__label">Mapped releases</p>
            <p className="app-stat-card__value">{status.mapped_count}</p>
          </article>
          <article className="app-surface app-stat-card">
            <p className="app-stat-card__label">Unmatched releases</p>
            <p className="app-stat-card__value">{status.unmatched_count}</p>
          </article>
          <article className="app-surface app-stat-card">
            <p className="app-stat-card__label">Wantlist entries</p>
            <p className="app-stat-card__value">{status.wantlist_count ?? 0}</p>
            <p className="app-stat-card__meta">
              {status.last_sync_time ? `Last synced ${status.last_sync_time}` : "Not yet synced."}
            </p>
          </article>
          {status.spotify_capability ? (
            <article className="app-surface app-stat-card">
              <p className="app-stat-card__label">Spotify</p>
              <p className="app-stat-card__value" style={{ fontSize: "1.2rem" }}>
                {status.spotify_capability.action_label}
              </p>
              <p className="app-stat-card__meta">
                {status.spotify_capability.addon_available
                  ? "Addon installed"
                  : "Addon unavailable"}
              </p>
            </article>
          ) : null}
          {status.provider_readiness ? (
            <article className="app-surface app-stat-card">
              <p className="app-stat-card__label">Provider Readiness</p>
              <p className="app-stat-card__value" style={{ fontSize: "1.2rem" }}>
                {status.provider_readiness.summary.onboarding_state}
              </p>
              <p className="app-stat-card__meta">
                Optional ready {status.provider_readiness.summary.ready_provider_count}/
                {status.provider_readiness.summary.optional_provider_count}
              </p>
            </article>
          ) : null}
        </section>
      ) : null}
      {status?.provider_readiness ? (
        <section className="app-surface app-card" style={{ marginTop: "1.25rem" }}>
          <h2 className="app-stack-label" style={{ marginBottom: "0.5rem" }}>
            Setup Guidance
          </h2>
          {!status.provider_readiness.summary.required_services_configured ? (
            <div style={{ marginBottom: "1rem" }}>
              <p className="app-message app-message--error" style={{ marginBottom: "0.75rem" }}>
                Discogs setup is required before you can browse your collection.
              </p>
              <Link
                to="/setup"
                className="app-button app-button--primary"
                style={{ display: "inline-block" }}
              >
                Go to Setup
              </Link>
            </div>
          ) : (
            <p className="app-message app-message--subtle" style={{ marginBottom: "0.75rem" }}>
              Discogs required setup is complete.
            </p>
          )}
          {status.provider_readiness.summary.degraded_mode ? (
            <p className="app-message app-message--subtle" style={{ marginBottom: "0.75rem" }}>
              Degraded mode: collection browsing still works without optional playback providers.
            </p>
          ) : null}
          <ul className="app-list">
            {status.provider_readiness.providers.map((provider) => (
              <li key={provider.provider_id}>
                <strong>{provider.display_name}</strong>: {provider.readiness} —{" "}
                {provider.status_message}
              </li>
            ))}
          </ul>
          {readinessNextActions(status.provider_readiness).length > 0 ? (
            <>
              <h3 className="app-stack-label" style={{ marginBottom: "0.4rem", marginTop: "1rem" }}>
                Next Actions
              </h3>
              <ul className="app-list">
                {readinessNextActions(status.provider_readiness).map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </>
          ) : null}
        </section>
      ) : null}
      {insights ? (
        <section className="app-surface app-card" style={{ marginTop: "1.25rem" }}>
          <h2 className="app-stack-label" style={{ marginBottom: "0.5rem" }}>
            Collector Insights
          </h2>
          <p className="app-message app-message--subtle" style={{ marginBottom: "0.75rem" }}>
            Health {insights.summary.health_score}/100 · Hidden gems{" "}
            {insights.summary.hidden_gems_count} · Value queue{" "}
            {insights.summary.refresh_queue_count}
          </p>
          {insights.highlights.length > 0 ? (
            <ul className="app-list">
              {insights.highlights.map((item) => (
                <li key={`${item.kind}-${item.title}`}>
                  <strong>{item.title}</strong>: {item.message}
                </li>
              ))}
            </ul>
          ) : (
            <p className="app-message app-message--subtle">
              No urgent insights right now. Try a fresh sync or value refresh.
            </p>
          )}
          {insights.daily_use_actions.length > 0 ? (
            <>
              <h3 className="app-stack-label" style={{ marginBottom: "0.4rem", marginTop: "1rem" }}>
                Daily Use Actions
              </h3>
              <ul className="app-list">
                {insights.daily_use_actions.slice(0, 4).map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </>
          ) : null}
        </section>
      ) : null}

      <div className="app-inline-actions" style={{ marginTop: "1.5rem" }}>
        <button
          type="button"
          className="app-button app-button--primary"
          onClick={handleSyncCollection}
          disabled={collectionSync === "syncing"}
        >
          {collectionSync === "syncing" ? "Syncing…" : "Sync Collection"}
        </button>
        <button
          type="button"
          className="app-button"
          onClick={handleSyncWantlist}
          disabled={wantlistSync === "syncing"}
        >
          {wantlistSync === "syncing" ? "Syncing…" : "Sync Wantlist"}
        </button>
      </div>
      {collectionMsg ? (
        <p
          className={`app-message ${collectionSync === "error" ? "app-message--error" : "app-message--success"}`}
        >
          {collectionMsg}
        </p>
      ) : null}
      {wantlistMsg ? (
        <p
          className={`app-message ${wantlistSync === "error" ? "app-message--error" : "app-message--success"}`}
        >
          {wantlistMsg}
        </p>
      ) : null}
    </main>
  );
}
