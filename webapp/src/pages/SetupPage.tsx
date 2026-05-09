import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getJson, postJson, ProviderReadinessContract } from "../api";

type SetupResponse = {
  onboarding_stage: string;
  discogs: { configured: boolean };
  provider_readiness?: ProviderReadinessContract;
};

function setupNextActions(readiness: ProviderReadinessContract): string[] {
  if (readiness.summary.next_actions.length > 0) {
    return readiness.summary.next_actions;
  }
  return readiness.next_actions;
}

export function SetupPage() {
  const navigate = useNavigate();
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [setupState, setSetupState] = useState<SetupResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    getJson<SetupResponse>("/setup")
      .then((payload) => {
        if (!cancelled) setSetupState(payload.data);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

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
      {setupState?.provider_readiness ? (
        <div className="app-message app-message--subtle" style={{ marginBottom: "1rem" }}>
          <div>
            Onboarding state: {setupState.provider_readiness.summary.onboarding_state || setupState.onboarding_stage}
          </div>
          <div>
            Optional providers ready: {setupState.provider_readiness.summary.ready_provider_count}/
            {setupState.provider_readiness.summary.optional_provider_count}
          </div>
          {setupState.provider_readiness.summary.degraded_mode ? (
            <div>Degraded mode is available: collection browsing still works without optional providers.</div>
          ) : null}
          {setupNextActions(setupState.provider_readiness).length > 0 ? (
            <div style={{ marginTop: "0.5rem" }}>
              Next actions: {setupNextActions(setupState.provider_readiness).join(" | ")}
            </div>
          ) : null}
        </div>
      ) : null}
      <form onSubmit={(e) => { void handleSubmit(e); }}>
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
        <button
          type="submit"
          disabled={saving}
          className="app-button app-button--primary"
        >
          {saving ? "Saving…" : "Save Token"}
        </button>
      </form>
      </section>
    </main>
  );
}
