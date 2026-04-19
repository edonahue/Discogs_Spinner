import { useEffect, useState } from "react";
import { getJson, SyncSummary, syncCollection, syncWantlist } from "../api";

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
};

type SyncState = "idle" | "syncing" | "done" | "error";

function formatSyncSummary(label: "Collection" | "Wantlist", summary: SyncSummary): string {
  return (
    `${label} sync complete: fetched ${summary.fetched_count}, `
    + `upserted ${summary.upserted_count}, deactivated ${summary.deactivated_count}.`
  );
}

export function HomePage() {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [error, setError] = useState<string>("");
  const [collectionSync, setCollectionSync] = useState<SyncState>("idle");
  const [collectionMsg, setCollectionMsg] = useState("");
  const [wantlistSync, setWantlistSync] = useState<SyncState>("idle");
  const [wantlistMsg, setWantlistMsg] = useState("");

  function loadStatus() {
    return getJson<StatusPayload>("/status")
      .then((payload) => {
        setStatus(payload.data);
        setError("");
        return payload.data;
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unknown API error.");
        throw err;
      });
  }

  useEffect(() => {
    let cancelled = false;
    getJson<StatusPayload>("/status")
      .then((payload) => { if (!cancelled) setStatus(payload.data); })
      .catch((err: unknown) => { if (!cancelled) setError(err instanceof Error ? err.message : "Unknown API error."); });
    return () => { cancelled = true; };
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
          <h1 className="app-page__title">Discogs Spinner</h1>
          <p className="app-page__subtitle">
            Desktop collection control without browser tab sprawl. This shell now reflows more predictably when the window narrows.
          </p>
        </div>
      </header>
      {error ? <p className="app-message app-message--error">{error}</p> : null}
      {!error && !status ? <p className="app-message app-message--subtle">Loading status…</p> : null}
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
                {status.spotify_capability.addon_available ? "Addon installed" : "Addon unavailable"}
              </p>
            </article>
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
        <p className={`app-message ${collectionSync === "error" ? "app-message--error" : "app-message--success"}`}>
          {collectionMsg}
        </p>
      ) : null}
      {wantlistMsg ? (
        <p className={`app-message ${wantlistSync === "error" ? "app-message--error" : "app-message--success"}`}>
          {wantlistMsg}
        </p>
      ) : null}
    </main>
  );
}
