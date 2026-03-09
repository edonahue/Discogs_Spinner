import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { getJson } from "./api";
import { Nav } from "./components/Nav";
import { CollectionPage } from "./pages/CollectionPage";
import { HealthPage } from "./pages/HealthPage";
import { HomePage } from "./pages/HomePage";
import { SetupPage } from "./pages/SetupPage";
import { ValuePage } from "./pages/ValuePage";
import { WantlistPage } from "./pages/WantlistPage";

type SetupPayload = {
  onboarding_stage: string;
};

function AppRoutes() {
  const navigate = useNavigate();
  const location = useLocation();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    getJson<SetupPayload>("/setup")
      .then((payload) => {
        if (payload.data?.onboarding_stage === "needs_discogs_token") {
          navigate("/setup", { replace: true });
        }
      })
      .catch(() => {
        // If API is unreachable, let routes render normally
      })
      .finally(() => {
        setChecked(true);
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!checked) {
    return <p style={{ fontFamily: "system-ui, sans-serif", margin: "2rem" }}>Loading…</p>;
  }

  const showNav = location.pathname !== "/setup";

  return (
    <>
      {showNav ? <Nav /> : null}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/setup" element={<SetupPage />} />
        <Route path="/collection" element={<CollectionPage />} />
        <Route path="/wantlist" element={<WantlistPage />} />
        <Route path="/value" element={<ValuePage />} />
        <Route path="/health" element={<HealthPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
