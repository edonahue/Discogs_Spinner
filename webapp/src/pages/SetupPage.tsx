import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { postJson } from "../api";

type SetupResponse = {
  onboarding_stage: string;
  discogs: { configured: boolean };
};

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
      setError(err instanceof Error ? err.message : "Failed to save token.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: "480px", margin: "4rem auto", lineHeight: 1.6 }}>
      <h1>Welcome to Discogs Spinner</h1>
      <p>
        Enter your Discogs personal access token to get started. You can find it at{" "}
        <a href="https://www.discogs.com/settings/developers" target="_blank" rel="noreferrer">
          discogs.com/settings/developers
        </a>
        .
      </p>
      <form onSubmit={(e) => { void handleSubmit(e); }}>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="token" style={{ display: "block", marginBottom: "0.25rem", fontWeight: 600 }}>
            Discogs Token
          </label>
          <input
            id="token"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="your_personal_access_token"
            required
            style={{ width: "100%", padding: "0.5rem", fontSize: "1rem", boxSizing: "border-box" }}
          />
        </div>
        {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
        <button
          type="submit"
          disabled={saving}
          style={{ padding: "0.5rem 1.5rem", fontSize: "1rem", cursor: saving ? "not-allowed" : "pointer" }}
        >
          {saving ? "Saving…" : "Save Token"}
        </button>
      </form>
    </main>
  );
}
