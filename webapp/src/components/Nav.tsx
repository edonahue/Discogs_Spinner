import { NavLink } from "react-router-dom";

export function Nav() {
  function navClass(isActive: boolean): string {
    return isActive ? "app-nav__link app-nav__link--active" : "app-nav__link";
  }

  return (
    <nav className="app-nav" aria-label="Primary">
      <div className="app-nav__inner">
        <NavLink to="/" end className={({ isActive }) => navClass(isActive)}>
          Home
        </NavLink>
        <NavLink to="/collection" className={({ isActive }) => navClass(isActive)}>
          Collection
        </NavLink>
        <NavLink to="/wantlist" className={({ isActive }) => navClass(isActive)}>
          Wantlist
        </NavLink>
        <NavLink to="/value" className={({ isActive }) => navClass(isActive)}>
          Value
        </NavLink>
        <NavLink to="/health" className={({ isActive }) => navClass(isActive)}>
          Health
        </NavLink>
        <NavLink to="/recent" className={({ isActive }) => navClass(isActive)}>
          Recent
        </NavLink>
        <NavLink to="/analytics" className={({ isActive }) => navClass(isActive)}>
          Analytics
        </NavLink>
        <NavLink to="/setup" className={({ isActive }) => navClass(isActive)}>
          Setup
        </NavLink>
      </div>
    </nav>
  );
}
