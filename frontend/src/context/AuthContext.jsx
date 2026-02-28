/**
 * AuthContext — Supabase Authentication State Management
 *
 * Fix [HIGH-F2]: Axios interceptor no longer calls supabase.auth.getSession()
 *               on every single API request.
 *
 *               OLD (broken): Network call to Supabase GoTrue on EVERY request.
 *               → Adds ~50-200ms per request, causes auth burst traffic.
 *
 *               NEW (fixed): Token stored in module-level ref. Supabase
 *               onAuthStateChange() keeps it fresh automatically (token refresh,
 *               logout, login all update it). Interceptor reads from ref — zero I/O.
 *
 * Token lifecycle:
 *   - Set on login / app mount (checkSession)
 *   - Updated by Supabase's built-in token-refresh mechanism via onAuthStateChange
 *   - Cleared on logout
 *   - Interceptor reads the cached value — no network call
 */

import React, { createContext, useState, useContext, useEffect, useRef } from "react";
import { supabase } from "../lib/supabase";
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


  /** Extract safe user object from Supabase session */
  const extractUser = (session) => ({
    id: session.user.id,
    email: session.user.email,
    name: session.user.user_metadata?.name || session.user.email.split("@")[0],
    created_at: session.user.created_at,
  });

  useEffect(() => {
    // Initial session check
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        _tokenRef.current = session.access_token;
        setToken(session.access_token);
        setUser(extractUser(session));
      }
      setLoading(false);
    }).catch((err) => {
      console.warn("Retrying session fetch - initial attempt failed:", err);
      setLoading(false);
    });

    // Auth state listener — handles login, logout, AND token auto-refresh.
    // This is the ONLY place token is updated — interceptor reads from _tokenRef.
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (session) {
          _tokenRef.current = session.access_token;  // FIX [HIGH-F2]: Keep ref fresh
          setToken(session.access_token);
          setUser(extractUser(session));
        } else {
          _tokenRef.current = null;  // FIX [HIGH-F2]: Clear on logout
          setToken(null);
          setUser(null);
        }
        setLoading(false);
      }
    );

    return () => subscription.unsubscribe();
  }, []);


  const login = async (email, password) => {
    // Try the new /auth/login endpoint first
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (res.ok && data.access_token) {
        // Custom JWT login succeeded — update token ref
        _tokenRef.current = data.access_token;
        setToken(data.access_token);
        setUser({
          id: data.user.user_id,
          email: data.user.email,
          name: data.user.name,
          picture: data.user.picture,
          provider: data.user.provider,
          is_verified: data.user.is_verified,
        });
        return data.user;
      }
      // For unverified / rate-limited, forward HTTP error
      const err = new Error(data.detail || 'Login failed');
      err.response = { status: res.status, data };
      throw err;
    } catch (e) {
      if (e.response) throw e;   // already formatted, re-throw
    }

    // Fallback: legacy Supabase sign-in (for existing users not in user_profiles yet)
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      const err = new Error(error.message);
      err.response = {
        status: error.message.includes('Invalid login') ? 401 : 400,
        data: { detail: error.message.includes('Invalid login') ? 'Invalid email or password' : error.message },
      };
      throw err;
    }
    return { id: data.user.id, email: data.user.email, name: data.user.user_metadata?.name };
  };


  const register = async (name, email, password) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { name } },
    });

    if (error) {
      const err = new Error(error.message);
      const isAlreadyRegistered = error.message.includes("already registered") ||
        error.message.includes("already been registered");
      err.response = {
        status: 400,
        data: { detail: isAlreadyRegistered ? "Email already registered" : error.message },
      };
      throw err;
    }

    return {
      id: data.user.id,
      email: data.user.email,
      name: data.user.user_metadata?.name || name,
    };
  };

  /** Google OAuth — triggers Supabase OAuth redirect flow */
  const loginWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/dashboard`,
        queryParams: { access_type: 'offline', prompt: 'consent' },
      },
    });
    if (error) {
      const err = new Error(error.message);
      throw err;
    }
    // Supabase will redirect — no return value needed
  };

  /**
   * loginWithToken — called after OTP verification succeeds.
   * Stores the custom JWT from /auth/verify-email in the context.
   */
  const loginWithToken = async (accessToken, userProfile) => {
    _tokenRef.current = accessToken;
    setToken(accessToken);
    setUser({
      id: userProfile.user_id,
      email: userProfile.email,
      name: userProfile.name,
      picture: userProfile.picture,
      provider: userProfile.provider,
      is_verified: userProfile.is_verified,
    });
  };

  const logout = async () => {
    await supabase.auth.signOut();
    _tokenRef.current = null;
    setUser(null);
    setToken(null);
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

