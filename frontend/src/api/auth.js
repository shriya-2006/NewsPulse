/**
 * Auth API calls. Each function maps 1:1 to a backend endpoint in
 * app/api/routes/auth.py — components should call these, never fetch()
 * directly, so token attachment and error shaping stay in one place.
 */

import { apiRequest } from "./client.js";

export function registerUser({ fullName, email, password }) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: { full_name: fullName, email, password },
  });
}

export function loginUser({ email, password, rememberMe }) {
  return apiRequest("/auth/login", {
    method: "POST",
    body: { email, password, remember_me: rememberMe },
  });
}

export function forgotPassword({ email }) {
  return apiRequest("/auth/forgot-password", {
    method: "POST",
    body: { email },
  });
}

export function resetPassword({ token, newPassword }) {
  return apiRequest("/auth/reset-password", {
    method: "POST",
    body: { token, new_password: newPassword },
  });
}

export function fetchCurrentUser(token) {
  return apiRequest("/auth/me", { token });
}

export function logoutUser(token) {
  return apiRequest("/auth/logout", { method: "POST", token });
}
