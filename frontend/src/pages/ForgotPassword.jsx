import { useState } from "react";
import { Link } from "react-router-dom";
import AuthLayout from "../components/auth/AuthLayout.jsx";
import { forgotPassword } from "../api/auth.js";
import { ApiError } from "../api/client.js";
import "../styles/forms.css";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await forgotPassword({ email });
      setSubmitted(true);
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
      title="Reset your password"
      subtitle="Enter your work email and we'll send you a link to reset your password."
      footer={
        <>
          Remembered it after all? <Link to="/login">Back to sign in</Link>
        </>
      }
    >
      {submitted ? (
        <div className="form-success-box">
          If an account exists for <strong>{email}</strong>, a reset link has
          been sent. Check your inbox.
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          {error && <div className="form-banner form-banner--error">{error}</div>}

          <div className="form-field">
            <label htmlFor="email">Work email</label>
            <input
              id="email"
              name="email"
              type="email"
              placeholder="you@vizagsteel.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <p className="form-field__hint">
              We'll email a link to reset your password.
            </p>
          </div>

          <button type="submit" className="btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
