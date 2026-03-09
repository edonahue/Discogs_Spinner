import { useEffect, useState } from "react";
import { getJson, syncCollection, syncWantlist } from "../api";

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

export function HomePage() {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [error, setError] = useState<string>("");
  const [collectionSync, setCollectionSync] = useState<SyncState>("idle");
  const [collectionMsg, setCollectionMsg] = useState("");
  const [wantlistSync, setWantlistSync] = useState<SyncState>("idle");
  const [wantlistMsg, setWantlistMsg] = useState("");

  function loadStatus() {
    getJson<StatusPayload>("/status")
      .then((payload) => setStatus(payload.data))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Unknown API error."));
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
      .then(() => {
        setCollectionSync("done");
        setCollectionMsg("Collection sync started.");
        setTimeout(() => {
          setCollectionSync("idle");
          setCollectionMsg("");
          loadStatus();
        }, 3000);
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
      .then(() => {
        setWantlistSync("done");
        setWantlistMsg("Wantlist sync started.");
        setTimeout(() => {
          setWantlistSync("idle");
          setWantlistMsg("");
          loadStatus();
        }, 3000);
      })
      .catch((err: unknown) => {
        setWantlistSync("error");
        setWantlistMsg(err instanceof Error ? err.message : "Sync failed.");
      });
  }

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "0 2rem 2rem", lineHeight: 1.5 }}>
      <h1>Discogs Spinner</h1>
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
      {!error && !status ? <p>Loading status...</p> : null}
      {status ? (
        <section>
          <p>Total releases: {status.release_count_total}</p>
          <p>Active releases: {status.release_count_active}</p>
          <p>Mapped releases: {status.mapped_count}</p>
          <p>Unmatched releases: {status.unmatched_count}</p>
          {status.last_sync_time
            ? <p>Last synced: {status.last_sync_time}</p>
            : <p>Not yet synced.</p>}
          {status.wantlist_count != null
            ? <p>Wantlist entries: {status.wantlist_count}</p>
            : null}
          {status.spotify_capability ? (
            <p>
              Spotify: {status.spotify_capability.action_label}
              {" ("}
              {status.spotify_capability.addon_available ? "addon installed" : "addon unavailable"}
              {")"}
            </p>
          ) : null}
        </section>
      ) : null}

      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", marginTop: "1.5rem", flexWrap: "wrap" }}>
        <button
          onClick={handleSyncCollection}
          disabled={collectionSync === "syncing"}
          style={{ padding: "0.4rem 1rem" }}
        >
          {collectionSync === "syncing" ? "Syncing…" : "Sync Collection"}
        </button>
        <button
          onClick={handleSyncWantlist}
          disabled={wantlistSync === "syncing"}
          style={{ padding: "0.4rem 1rem" }}
        >
          {wantlistSync === "syncing" ? "Syncing…" : "Sync Wantlist"}
        </button>
      </div>
      {collectionMsg ? (
        <p style={{ color: collectionSync === "error" ? "crimson" : "#2a7a2a", marginTop: "0.5rem" }}>
          {collectionMsg}
        </p>
      ) : null}
      {wantlistMsg ? (
        <p style={{ color: wantlistSync === "error" ? "crimson" : "#2a7a2a", marginTop: "0.5rem" }}>
          {wantlistMsg}
        </p>
      ) : null}
    </main>
  );
}
