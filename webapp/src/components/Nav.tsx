import { NavLink } from "react-router-dom";

const linkStyle: React.CSSProperties = {
  marginRight: "1.5rem",
  textDecoration: "none",
  color: "#555",
  fontWeight: 500,
};

const activeStyle: React.CSSProperties = {
  ...linkStyle,
  color: "#000",
  borderBottom: "2px solid #000",
};

export function Nav() {
  return (
    <nav style={{ padding: "0.75rem 2rem", borderBottom: "1px solid #ddd", marginBottom: "1.5rem" }}>
      <NavLink to="/" end style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
        Home
      </NavLink>
      <NavLink to="/collection" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
        Collection
      </NavLink>
      <NavLink to="/wantlist" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
        Wantlist
      </NavLink>
      <NavLink to="/value" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
        Value
      </NavLink>
    </nav>
  );
}
