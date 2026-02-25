import { useEffect, useState } from "react";

import { getJson } from "./api";

type StatusPayload = {
  release_count_total: number;
  release_count_active: number;
  mapped_count: number;
  unmatched_count: number;
  spotify_capability?: {
    addon_available: boolean;
    configured: boolean;
    action_label: string;
  };
};

export function App() {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    getJson<StatusPayload>("/status")
      .then((payload) => {
        if (!cancelled) {
          setStatus(payload.data);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown API error.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "2rem", lineHeight: 1.5 }}>
      <h1>discogs_player</h1>
      <p>API-first web client scaffold</p>
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
      {!error && !status ? <p>Loading status...</p> : null}
      {status ? (
        <section>
          <p>Total releases: {status.release_count_total}</p>
          <p>Active releases: {status.release_count_active}</p>
          <p>Mapped releases: {status.mapped_count}</p>
          <p>Unmatched releases: {status.unmatched_count}</p>
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
    </main>
  );
}
