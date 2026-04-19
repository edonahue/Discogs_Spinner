import { useEffect, useRef, useState } from "react";
import { fetchTracklist, Track } from "../api";

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
  const backdropRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
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
  }, [releaseId]);

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
          <p className="app-message app-message--subtle">
            No tracklist cached — run{" "}
            <code style={{ background: "#f0f0f0", padding: "0 0.3rem", borderRadius: "3px" }}>
              dplayer tracks refresh
            </code>{" "}
            to populate it.
          </p>
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
