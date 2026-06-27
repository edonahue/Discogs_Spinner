import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { postJson } from "../api";

type SetupResponse = {
  onboarding_stage: string;
  discogs: { configured: boolean };
};

// Mirror the GTK setup wizard's auth-vs-network error differentiation so the
// same failure reads the same way across the desktop and web surfaces.
function describeSetupError(err: unknown): string {
  const raw = err instanceof Error ? err.message : "";
  const lower = raw.toLowerCase();
  if (
    lower.includes("token") ||
    lower.includes("auth") ||
    lower.includes("401") ||
    lower.includes("unauthorized")
  ) {
    return "Token rejected — check your token at discogs.com/settings/developers.";
  }
  if (
    lower.includes("network") ||
    lower.includes("connection") ||
    lower.includes("timeout") ||
    lower.includes("failed to fetch") ||
    lower.includes("fetch")
  ) {
    return "Network error — check your internet connection and try again.";
  }
  return raw || "Could not save token. Please try again.";
}

export function SetupPage() {
  const navigate = useNavigate();
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await postJson<SetupResponse>("/setup", { discogs_token: token });
      navigate("/");
    } catch (err: unknown) {
      setError(describeSetupError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="app-page app-page--narrow">
      <section className="app-surface app-card" style={{ marginTop: "2.5rem" }}>
        <h1 className="app-page__title">Welcome to Discogs Spinner</h1>
        <p className="app-page__subtitle" style={{ marginBottom: "1.25rem" }}>
          Discogs setup is required. Playback providers are optional and can be connected later.
        </p>
        <p className="app-page__subtitle" style={{ marginBottom: "1.25rem" }}>
          Enter your Discogs personal access token to continue. You can find it at{" "}
          <a href="https://www.discogs.com/settings/developers" target="_blank" rel="noreferrer">
            discogs.com/settings/developers
          </a>
          .
        </p>
        <form
          onSubmit={(e) => {
            void handleSubmit(e);
          }}
        >
          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="token" className="app-stack-label">
              Discogs Token
            </label>
            <input
              id="token"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="your_personal_access_token"
              required
              className="app-input"
            />
          </div>
          {error ? <p className="app-message app-message--error">{error}</p> : null}
          <button type="submit" disabled={saving} className="app-button app-button--primary">
            {saving ? "Saving…" : "Save Token"}
          </button>
        </form>
      </section>
    </main>
  );
}
