/**
 * AuthContext — Custom JWT Authentication State Management
 *
 * Token lifecycle:
 *   - Set on login / register / Google sign-in
 *   - Persisted in localStorage (pp_token, pp_user)
 *   - Restored on page refresh (with JWT expiry check)
 *   - Cleared on logout (+ backend JWT revocation)
 *   - Interceptor reads cached value — zero I/O
 */

import React, { createContext, useState, useContext, useEffect } from "react";
import axios from "axios";

const API_URL = (import.meta.env.VITE_API_URL || "").trim();

// Axios instance for backend API calls
export const api = axios.create({
  baseURL: API_URL,
  timeout: 60000,  // 60s — Supabase DB cold-start can take 5-10s on free tier
});


// FIX [HIGH-F2]: Module-level token ref — updated by auth state listener.
// Interceptor reads this ref without any network call.
// Using a ref (not closure) so interceptor always gets the latest value.
const _tokenRef = { current: null };

// Set up the request interceptor ONCE at module level (not inside React lifecycle).
// This avoids multiple interceptors stacking up on re-renders.
api.interceptors.request.use((config) => {
  // Zero I/O — reads from module-level ref updated by onAuthStateChange
  if (_tokenRef.current) {
    config.headers.Authorization = `Bearer ${_tokenRef.current}`;
  }
  return config;
});

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);


  // ── Local token persistence helpers ─────────────────────────────────
  const STORAGE_TOKEN_KEY = 'pp_token';
  const STORAGE_USER_KEY = 'pp_user';

  const persistSession = (accessToken, userObj) => {
    try {
      localStorage.setItem(STORAGE_TOKEN_KEY, accessToken);
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(userObj));
    } catch { /* quota exceeded etc — ignore */ }
  };

  const clearPersistedSession = () => {
    try {
      localStorage.removeItem(STORAGE_TOKEN_KEY);
      localStorage.removeItem(STORAGE_USER_KEY);
    } catch { /* ignore */ }
  };

  /** Check if a JWT is still valid (not expired) */
  const isTokenValid = (accessToken) => {
    try {
      const parts = accessToken.split('.');
      if (parts.length !== 3) return false;
      const payload = JSON.parse(atob(parts[1]));
      const exp = payload?.exp;
      if (!exp) return false;
      return exp > Math.floor(Date.now() / 1000);
    } catch {
      return false;
    }
  };

  // ── Restore session from localStorage on mount ──────────────────────
  useEffect(() => {
    const restoreSession = () => {
      try {
        const savedToken = localStorage.getItem(STORAGE_TOKEN_KEY);
        const savedUser = localStorage.getItem(STORAGE_USER_KEY);

        if (savedToken && savedUser && isTokenValid(savedToken)) {
          const userObj = JSON.parse(savedUser);
          _tokenRef.current = savedToken;
          setToken(savedToken);
          setUser(userObj);
        } else {
          // Token expired or missing — clear stale data
          clearPersistedSession();
        }
      } catch {
        clearPersistedSession();
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, []);


  const login = async (email, password) => {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (res.ok && data.access_token) {
      const userObj = {
        id: data.user.user_id,
        email: data.user.email,
        name: data.user.name,
        picture: data.user.picture,
        provider: data.user.provider,
        is_verified: data.user.is_verified,
      };
      _tokenRef.current = data.access_token;
      setToken(data.access_token);
      setUser(userObj);
      persistSession(data.access_token, userObj);
      return data.user;
    }
    const err = new Error(data.detail || 'Login failed');
    err.response = { status: res.status, data };
    throw err;
  };


  const register = async (name, email, password) => {
    // Register via custom backend (not Supabase)
    const res = await fetch(`${API_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json();

    if (!res.ok) {
      const detail = data.detail || 'Registration failed.';
      const err = new Error(detail);
      err.response = { status: res.status, data: { detail } };
      throw err;
    }

    // If auto-verified, store token + user immediately
    if (data.auto_verified && data.access_token) {
      const userObj = {
        id: data.user.user_id,
        email: data.user.email,
        name: data.user.name,
        picture: data.user.picture,
        provider: data.user.provider,
        is_verified: data.user.is_verified,
      };
      _tokenRef.current = data.access_token;
      setToken(data.access_token);
      setUser(userObj);
      persistSession(data.access_token, userObj);
    }

    return data;
  };

  /** Google OAuth — uses native Google Identity Services SDK (no Supabase) */
  const loginWithGoogle = () => {
    return new Promise((resolve, reject) => {
      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      if (!clientId) {
        reject(new Error('Google Client ID not configured.'));
        return;
      }

      // Wait for Google SDK to load
      const tryInit = () => {
        if (!window.google?.accounts?.id) {
          setTimeout(tryInit, 200);
          return;
        }

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (response) => {
            try {
              // Send Google ID token to our backend for verification + JWT
              const res = await fetch(`${API_URL}/auth/google`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id_token: response.credential }),
              });
              const data = await res.json();

              if (!res.ok) {
                reject(new Error(data.detail || 'Google authentication failed.'));
                return;
              }

              // Store custom JWT and user profile
              const userObj = {
                id: data.user.user_id,
                email: data.user.email,
                name: data.user.name,
                picture: data.user.picture,
                provider: data.user.provider,
                is_verified: data.user.is_verified,
              };
              _tokenRef.current = data.access_token;
              setToken(data.access_token);
              setUser(userObj);
              persistSession(data.access_token, userObj);
              resolve(data.user);
            } catch (err) {
              reject(err);
            }
          },
          auto_select: false,
          ux_mode: 'popup',
        });

        // Trigger the Google Sign-In popup
        window.google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            // Fallback: use the full Google Sign-In button flow
            window.google.accounts.id.renderButton(
              document.createElement('div'),
              { type: 'standard', theme: 'outline', size: 'large' }
            );
            // Try popup again with explicit user gesture
            window.google.accounts.oauth2.initCodeClient({
              client_id: clientId,
              scope: 'email profile',
              ux_mode: 'popup',
              callback: () => { },
            });
          }
        });
      };

      tryInit();
    });
  };

  /**
   * loginWithToken — called after OTP verification succeeds.
   * Stores the custom JWT from /auth/verify-email in the context.
   */
  const loginWithToken = async (accessToken, userProfile) => {
    const userObj = {
      id: userProfile.user_id,
      email: userProfile.email,
      name: userProfile.name,
      picture: userProfile.picture,
      provider: userProfile.provider,
      is_verified: userProfile.is_verified,
    };
    _tokenRef.current = accessToken;
    setToken(accessToken);
    setUser(userObj);
    persistSession(accessToken, userObj);
  };

  const logout = async () => {
    // Revoke Google token if available
    try {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.disableAutoSelect();
      }
    } catch { /* ignore */ }

    // Call backend logout to revoke JWT
    try {
      if (_tokenRef.current) {
        await fetch(`${API_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${_tokenRef.current}`,
            'Content-Type': 'application/json',
          },
        });
      }
    } catch { /* ignore logout errors */ }

    _tokenRef.current = null;
    setUser(null);
    setToken(null);
    clearPersistedSession();
  };


  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      login,
      register,
      logout,
      loginWithGoogle,
      loginWithToken,
      isAuthenticated: !!user,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

