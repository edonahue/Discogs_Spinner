import { useEffect, useRef, useState } from "react";
import { fetchTracklist, refreshTracklist, Track } from "../api";

interface Props {
  releaseId: number;
  releaseTitle: string;
  releaseArtist: string;
  onClose: () => void;
}

export function TracklistModal({ releaseId, releaseTitle, releaseArtist, onClose }: Props) {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [hasCached, setHasCached] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const backdropRef = useRef<HTMLDivElement>(null);

  function loadTracklist() {
    setLoading(true);
    setError("");
    fetchTracklist(releaseId)
      .then((payload) => {
        const d = payload.data;
        setTracks(d?.tracks ?? []);
        setHasCached(d?.has_cached_tracklist ?? false);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load tracklist.")
      )
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadTracklist();
  }, [releaseId]);

  function handleRefresh() {
    setRefreshing(true);
    setError("");
    refreshTracklist(releaseId)
      .then((payload) => {
        const d = payload.data;
        setTracks(d?.tracks ?? []);
        setHasCached(d?.has_cached_tracklist ?? false);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to refresh tracklist.")
      )
      .finally(() => setRefreshing(false));
  }

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === backdropRef.current) onClose();
  }

  const audioTracks = tracks.filter((t) => t.type_ !== "heading");

  return (
    <div
      ref={backdropRef}
      onClick={handleBackdropClick}
      className="app-modal"
    >
      <div className="app-modal__panel">
        <div className="app-modal__header">
          <div>
            <strong style={{ fontSize: "1.05rem" }}>{releaseArtist}</strong>
            <div className="app-muted" style={{ marginTop: "0.1rem" }}>{releaseTitle}</div>
          </div>
          <button
            onClick={onClose}
            className="app-button app-button--ghost app-modal__close"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {error ? <p className="app-message app-message--error">{error}</p> : null}
        {loading ? <p className="app-message app-message--subtle">Loading…</p> : null}

        {!loading && !error && !hasCached ? (
          <div className="app-message app-message--subtle" style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
            <span>Tracklist not yet loaded.</span>
            <button
              type="button"
              className="app-button app-button--ghost"
              onClick={handleRefresh}
              disabled={refreshing}
              style={{ padding: "0.25rem 0.65rem", fontSize: "0.85rem" }}
            >
              {refreshing ? "Refreshing…" : "Refresh Tracklist"}
            </button>
          </div>
        ) : null}

        {!loading && !error && hasCached && audioTracks.length === 0 ? (
          <p className="app-message app-message--subtle">No audio tracks found.</p>
        ) : null}

        {!loading && !error && audioTracks.length > 0 ? (
          <div className="app-table-wrap">
            <table className="app-table app-table--compact responsive-stack">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Title</th>
                  <th className="is-right">Duration</th>
                </tr>
              </thead>
              <tbody>
                {audioTracks.map((track, i) => (
                  <tr key={i}>
                    <td data-label="Track">{track.position || String(i + 1)}</td>
                    <td data-label="Title">{track.title}</td>
                    <td data-label="Duration" className="is-right">{track.duration || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  );
}
