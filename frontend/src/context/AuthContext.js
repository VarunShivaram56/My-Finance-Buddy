import { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  AUTH_TOKEN_KEY,
  AUTH_USER_KEY,
  fetchCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
} from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem(AUTH_USER_KEY);
    if (!stored) {
      return null;
    }
    try {
      return JSON.parse(stored);
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem(AUTH_TOKEN_KEY) || "");
  const [loading, setLoading] = useState(Boolean(localStorage.getItem(AUTH_TOKEN_KEY)));

  useEffect(() => {
    const syncUser = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const response = await fetchCurrentUser();
        setUser(response.user);
        localStorage.setItem(AUTH_USER_KEY, JSON.stringify(response.user));
      } catch {
        clearAuthState();
      } finally {
        setLoading(false);
      }
    };

    syncUser();
  }, [token]);

  const clearAuthState = () => {
    setUser(null);
    setToken("");
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    sessionStorage.clear();
  };

  const handleAuthSuccess = (payload) => {
    setUser(payload.user);
    setToken(payload.token);
    localStorage.setItem(AUTH_TOKEN_KEY, payload.token);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(payload.user));
  };

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: Boolean(user && token),
      async login(payload) {
        const response = await loginUser({ user_id: payload.user_id, password: payload.password });
        handleAuthSuccess(response);
        return response;
      },
      async register(payload) {
        const response = await registerUser({ name: payload.name, user_id: payload.user_id, password: payload.password });
        handleAuthSuccess(response);
        return response;
      },
      async logout() {
        try {
          await logoutUser();
        } catch {
          // Ignore logout request failures and still clear local auth state.
        } finally {
          clearAuthState();
        }
      },
      clearAuthState,
    }),
    [loading, token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
