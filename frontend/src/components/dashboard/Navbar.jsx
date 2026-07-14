import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSignOut = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const navLinks = [
    { label: "Search", path: "/dashboard" },
    { label: "Reports", path: "/reports" },
    ...(user?.is_admin ? [{ label: "Admin Dashboard", path: "/admin" }] : []),
  ].filter((link) => link.path !== location.pathname);

  return (
    <header className="dash-navbar">
      <div className="dash-navbar__brand">
        <span className="dash-navbar__mark">NP</span>
        <span className="dash-navbar__title">NewsPulse</span>
      </div>
      <div className="dash-navbar__meta">
        <nav className="dash-navbar__links">
          {navLinks.map((link) => (
            <Link key={link.path} to={link.path} className="dash-navbar__admin-link">
              {link.label}
            </Link>
          ))}
        </nav>
        <span className="dash-navbar__org">
          {user ? user.full_name : "RINL · Visakhapatnam Steel Plant"}
        </span>
        <button type="button" className="dash-navbar__signout" onClick={handleSignOut}>
          Sign out
        </button>
      </div>
    </header>
  );
}
