import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  fetchCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
} from "../api/auth.js";

const AuthContext = createContext(null);

// "Keep me signed in" (remember_me) controls two things together:
//   1. the backend issues a 7-day token instead of a 1-hour one
//   2. the frontend persists that token in localStorage (survives closing
//      the browser) instead of sessionStorage (cleared when the tab closes)
const STORAGE_KEY = "newspulse_token";

function readStoredToken() {
  return (
    localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem(STORAGE_KEY) || null
  );
}

function storeToken(token, rememberMe) {
  // Always clear both first so switching accounts/tabs never leaves a
  // stale token sitting in the other storage.
  localStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem(STORAGE_KEY);
  (rememberMe ? localStorage : sessionStorage).setItem(STORAGE_KEY, token);
}

function clearStoredToken() {
  localStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem(STORAGE_KEY);
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  // Starts true: on first load we don't yet know if a stored token is
  // valid, so ProtectedRoute must wait rather than bounce to /login.
  const [isLoading, setIsLoading] = useState(true);

  // On mount, try to resume a session from a previously stored token.
  useEffect(() => {
    const stored = readStoredToken();
    if (!stored) {
      setIsLoading(false);
      return;
    }

    fetchCurrentUser(stored)
      .then((currentUser) => {
        setToken(stored);
        setUser(currentUser);
      })
      .catch(() => {
        // Token expired or invalid — silently drop it, land on /login.
        clearStoredToken();
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = async ({ email, password, rememberMe }) => {
    const data = await loginUser({ email, password, rememberMe });
    storeToken(data.access_token, rememberMe);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const register = async ({ fullName, email, password }) => {
    const data = await registerUser({ fullName, email, password });
    // Registering also signs the user in immediately (backend returns a token).
    storeToken(data.access_token, false);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    const currentToken = token;
    clearStoredToken();
    setToken(null);
    setUser(null);
    if (currentToken) {
      // Best-effort — JWTs are stateless so there's nothing critical
      // riding on this call succeeding.
      logoutUser(currentToken).catch(() => {});
    }
  };

  const value = useMemo(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(token && user),
      isLoading,
      login,
      register,
      logout,
    }),
    [user, token, isLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
