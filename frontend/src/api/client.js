/**
 * Thin fetch wrapper for talking to the FastAPI backend.
 *
 * `apiRequest()` is the shared helper every feature module (auth, search,
 * reports, admin) builds on — it attaches the JSON content-type, the
 * Authorization header when a token is present, and normalizes error
 * handling so callers don't each reimplement it.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_V1 = `${API_BASE_URL}/api/v1`;

/**
 * Thrown when the backend returns a non-2xx response. Carries the
 * `detail` message FastAPI sends so forms can show it directly.
 */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * @param {string} path - path relative to /api/v1, e.g. "/auth/login"
 * @param {object} [options]
 * @param {string} [options.method]
 * @param {object} [options.body] - will be JSON-stringified
 * @param {string|null} [options.token] - if provided, sent as a Bearer token
 */
export async function apiRequest(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_V1}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      "Could not reach the server. Please check your connection and try again.",
      0
    );
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    // No JSON body (e.g. 204) — that's fine.
  }

  if (!response.ok) {
    const message =
      (data && (data.detail || data.message)) ||
      `Request failed with status ${response.status}.`;
    throw new ApiError(
      typeof message === "string" ? message : "Something went wrong. Please try again.",
      response.status
    );
  }

  return data;
}

