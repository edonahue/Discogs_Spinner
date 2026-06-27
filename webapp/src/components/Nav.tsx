import { NavLink } from "react-router-dom";

function IconHome() {
  return (
    <svg
      className="app-nav__icon"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M2 6.5L8 2l6 4.5V14a1 1 0 01-1 1H3a1 1 0 01-1-1V6.5z" />
      <path d="M6 15V9h4v6" />
    </svg>
  );
}

function IconCollection() {
  return (
    <svg
      className="app-nav__icon"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="6" />
      <circle cx="8" cy="8" r="1.5" />
      <path d="M8 2a6 6 0 010 12" strokeDasharray="2 2" />
    </svg>
  );
}

function IconWantlist() {
  return (
    <svg
      className="app-nav__icon"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M8 13.5S2 9.5 2 5.5A3.5 3.5 0 018 3.2 3.5 3.5 0 0114 5.5c0 4-6 8-6 8z" />
    </svg>
  );
}

function IconValue() {
  return (
    <svg
      className="app-nav__icon"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M8 1v14M5 4h4.5a2 2 0 010 4H5m0 0h5a2 2 0 010 4H5" />
    </svg>
  );
}

function IconHealth() {
  return (
    <svg
      className="app-nav__icon"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M1 8h3l2-5 3 10 2-5h4" />
    </svg>
  );
}

function IconRecent() {
  return (
    <svg
      className="app-nav__icon"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5v3.5l2.5 1.5" />
    </svg>
  );
}

function IconAnalytics() {
  return (
    <svg
      className="app-nav__icon"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="1" y="10" width="3" height="5" rx="0.5" />
      <rect x="6.5" y="6" width="3" height="9" rx="0.5" />
      <rect x="12" y="2" width="3" height="13" rx="0.5" />
    </svg>
  );
}

function IconSetup() {
  return (
    <svg
      className="app-nav__icon"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="2" />
      <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.42 1.42M11.54 11.54l1.41 1.41M3.05 12.95l1.42-1.42M11.54 4.46l1.41-1.41" />
    </svg>
  );
}

export function Nav() {
  function navClass(isActive: boolean): string {
    return isActive ? "app-nav__link app-nav__link--active" : "app-nav__link";
  }

  return (
    <nav className="app-nav" aria-label="Primary">
      <div className="app-nav__inner">
        <NavLink to="/" end className={({ isActive }) => navClass(isActive)}>
          <IconHome />
          Home
        </NavLink>
        <NavLink to="/collection" className={({ isActive }) => navClass(isActive)}>
          <IconCollection />
          Collection
        </NavLink>
        <NavLink to="/wantlist" className={({ isActive }) => navClass(isActive)}>
          <IconWantlist />
          Wantlist
        </NavLink>
        <NavLink to="/value" className={({ isActive }) => navClass(isActive)}>
          <IconValue />
          Value
        </NavLink>
        <NavLink to="/health" className={({ isActive }) => navClass(isActive)}>
          <IconHealth />
          Health
        </NavLink>
        <NavLink to="/recent" className={({ isActive }) => navClass(isActive)}>
          <IconRecent />
          Recent
        </NavLink>
        <NavLink to="/analytics" className={({ isActive }) => navClass(isActive)}>
          <IconAnalytics />
          Analytics
        </NavLink>
        <NavLink to="/setup" className={({ isActive }) => navClass(isActive)}>
          <IconSetup />
          Setup
        </NavLink>
      </div>
    </nav>
  );
}
