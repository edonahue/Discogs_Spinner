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
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: "8px",
          padding: "1.5rem 2rem",
          maxWidth: "560px",
          width: "90%",
          maxHeight: "80vh",
          overflow: "auto",
          fontFamily: "system-ui, sans-serif",
          boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
          <div>
            <strong style={{ fontSize: "1.05rem" }}>{releaseArtist}</strong>
            <div style={{ color: "#555", marginTop: "0.1rem" }}>{releaseTitle}</div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              fontSize: "1.4rem",
              cursor: "pointer",
              color: "#888",
              lineHeight: 1,
              padding: "0 0 0 1rem",
            }}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
        {loading ? <p>Loading…</p> : null}

        {!loading && !error && !hasCached ? (
          <p style={{ color: "#888", fontSize: "0.9rem" }}>
            No tracklist cached — run{" "}
            <code style={{ background: "#f0f0f0", padding: "0 0.3rem", borderRadius: "3px" }}>
              dplayer tracks refresh
            </code>{" "}
            to populate it.
          </p>
        ) : null}

        {!loading && !error && hasCached && audioTracks.length === 0 ? (
          <p style={{ color: "#888", fontSize: "0.9rem" }}>No audio tracks found.</p>
        ) : null}

        {!loading && !error && audioTracks.length > 0 ? (
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.92rem" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #ddd", textAlign: "left" }}>
                <th style={{ padding: "0.3rem 0.5rem 0.3rem 0", width: "2.5rem", color: "#888" }}>#</th>
                <th style={{ padding: "0.3rem 0.75rem" }}>Title</th>
                <th style={{ padding: "0.3rem 0 0.3rem 0.75rem", textAlign: "right", color: "#888" }}>Duration</th>
              </tr>
            </thead>
            <tbody>
              {audioTracks.map((t, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #f0f0f0" }}>
                  <td style={{ padding: "0.3rem 0.5rem 0.3rem 0", color: "#aaa" }}>
                    {t.position || String(i + 1)}
                  </td>
                  <td style={{ padding: "0.3rem 0.75rem" }}>{t.title}</td>
                  <td style={{ padding: "0.3rem 0 0.3rem 0.75rem", textAlign: "right", color: "#888" }}>
                    {t.duration || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>
    </div>
  );
}
