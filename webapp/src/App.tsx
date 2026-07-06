import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { getJson, ProviderReadinessContract } from "./api";

const isTauri = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

async function checkTauriUpdate(): Promise<string | null> {
  if (!isTauri) return null;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const version = await invoke<string | null>("check_update");
    return version ?? null;
  } catch {
    return null;
  }
}
import { Footer } from "./components/Footer";
import { Nav } from "./components/Nav";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { CollectionPage } from "./pages/CollectionPage";
import { HealthPage } from "./pages/HealthPage";
import { HomePage } from "./pages/HomePage";
import { RecentPage } from "./pages/RecentPage";
import { SetupPage } from "./pages/SetupPage";
import { ValuePage } from "./pages/ValuePage";
import { WantlistPage } from "./pages/WantlistPage";

type SetupPayload = {
  onboarding_stage: string;
  provider_readiness?: ProviderReadinessContract;
};

function UpdateBanner() {
  const [updateVersion, setUpdateVersion] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    checkTauriUpdate().then(setUpdateVersion);
  }, []);

  if (!updateVersion || dismissed) return null;

  return (
    <div className="app-update-banner">
      <span>Version {updateVersion} is available.</span>
      <a
        href="https://github.com/edonahue/Discogs_Spinner/releases/latest"
        target="_blank"
        rel="noreferrer"
        className="app-link"
      >
        Download
      </a>
      <button
        type="button"
        className="app-button app-button--ghost app-update-banner__dismiss"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss update notification"
      >
        ×
      </button>
    </div>
  );
}

function AppRoutes() {
  const navigate = useNavigate();
  const location = useLocation();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    // Retry the setup check to handle the Tauri startup race: the FastAPI
    // sidecar is spawned in the background and the webview loads immediately,
    // so the first request often fires before the API is ready.
    const MAX_ATTEMPTS = 4;
    const RETRY_DELAY_MS = 1000;

    function checkSetup(attemptsLeft: number): Promise<void> {
      return getJson<SetupPayload>("/setup")
        .then((payload) => {
          const readinessSummary = payload.data?.provider_readiness?.summary;
          const onboardingStage =
            readinessSummary?.onboarding_state ?? payload.data?.onboarding_stage;
          const requiredConfigured = readinessSummary?.required_services_configured;
          if (
            onboardingStage === "needs_required_setup" ||
            onboardingStage === "needs_discogs_token" ||
            requiredConfigured === false
          ) {
            navigate("/setup", { replace: true });
          }
        })
        .catch(() => {
          if (attemptsLeft > 1) {
            return new Promise<void>((resolve) => {
              setTimeout(() => {
                resolve(checkSetup(attemptsLeft - 1));
              }, RETRY_DELAY_MS);
            });
          }
          // All retries exhausted — API unreachable; let routes render normally.
        });
    }

    checkSetup(MAX_ATTEMPTS).finally(() => {
      setChecked(true);
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!checked) {
    return (
      <main className="app-page">
        <p className="app-message app-message--subtle">Loading…</p>
      </main>
    );
  }

  const showNav = location.pathname !== "/setup";

  return (
    <div className="app-shell">
      {showNav ? <Nav /> : null}
      <UpdateBanner />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/setup" element={<SetupPage />} />
        <Route path="/collection" element={<CollectionPage />} />
        <Route path="/wantlist" element={<WantlistPage />} />
        <Route path="/value" element={<ValuePage />} />
        <Route path="/health" element={<HealthPage />} />
        <Route path="/recent" element={<RecentPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Footer />
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
