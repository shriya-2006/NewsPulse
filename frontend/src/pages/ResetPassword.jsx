import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import AuthLayout from "../components/auth/AuthLayout.jsx";
import { resetPassword } from "../api/auth.js";
import { ApiError } from "../api/client.js";
import "../styles/forms.css";

/**
 * Landing page for the link sent by /auth/forgot-password
 * (…/reset-password?token=...). Not linked from anywhere in the app nav —
 * only reached via that emailed/logged link.
 */
export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [form, setForm] = useState({ newPassword: "", confirmPassword: "" });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!token) {
      setError("This reset link is missing its token. Please request a new one.");
      return;
    }
    if (form.newPassword !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await resetPassword({ token, newPassword: form.newPassword });
      setDone(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="RINL · Visakhapatnam Steel Plant"
      title="Set a new password"
      subtitle="Choose a new password for your account."
      footer={
        <>
          Remembered it after all? <Link to="/login">Back to sign in</Link>
        </>
      }
    >
      {done ? (
        <div className="form-success-box">
          Your password has been reset. Redirecting you to sign in…
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          {error && <div className="form-banner form-banner--error">{error}</div>}

          <div className="form-field">
            <label htmlFor="newPassword">New password</label>
            <input
              id="newPassword"
              name="newPassword"
              type="password"
              placeholder="Create a new password"
              value={form.newPassword}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="confirmPassword">Confirm new password</label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              placeholder="Re-enter your new password"
              value={form.confirmPassword}
              onChange={handleChange}
              required
            />
          </div>

          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Resetting…" : "Reset password"}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
