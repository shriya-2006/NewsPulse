/**
 * Admin dashboard API calls. Mirrors app/api/routes/admin.py.
 */

import { apiRequest } from "./client.js";

export function fetchAdminDashboard(token) {
  return apiRequest("/admin/dashboard", { token });
}

export function fetchAdminUsers(token) {
  return apiRequest("/admin/users", { token });
}
