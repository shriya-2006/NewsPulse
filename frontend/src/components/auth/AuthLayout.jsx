import { Link } from "react-router-dom";
import "./AuthLayout.css";

/**
 * Split-panel shell shared by Login / Register / ForgotPassword.
 * Left: brand + context (what this system does, who it's for).
 * Right: the form itself, passed in as children.
 */
export default function AuthLayout({ eyebrow, title, subtitle, children, footer }) {
  return (
    <div className="auth-shell">
      <aside className="auth-brand">
        <div className="auth-brand__seam" />
        <div className="auth-brand__content">
          <div className="auth-brand__mark">NP</div>
          <h1 className="auth-brand__title">NewsPulse</h1>
          <p className="auth-brand__tagline">
            Enterprise news monitoring &amp; report generation for
            Rashtriya Ispat Nigam Limited, Visakhapatnam Steel Plant.
          </p>
          <ul className="auth-brand__list">
            <li>Track Steel, Coal, Iron Ore &amp; Policy coverage automatically</li>
            <li>Filter by language and edition</li>
            <li>Generate director-ready PDF reports in one click</li>
          </ul>
        </div>
      </aside>

      <main className="auth-form-panel">
        <div className="auth-form-card">
          <Link to="/login" className="auth-form-card__logo">
            NewsPulse
          </Link>
          {eyebrow && <span className="auth-form-card__eyebrow">{eyebrow}</span>}
          <h2 className="auth-form-card__title">{title}</h2>
          {subtitle && <p className="auth-form-card__subtitle">{subtitle}</p>}

          {children}

          {footer && <div className="auth-form-card__footer">{footer}</div>}
        </div>
      </main>
    </div>
  );
}
