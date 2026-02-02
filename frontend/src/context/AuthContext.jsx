import React, { createContext, useState, useContext, useEffect } from "react";
import axios from "axios";




const API_URL = import.meta.env.VITE_API_URL;

const api = axios.create({
  baseURL: API_URL,
});


const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};



export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Attach token automatically
    api.interceptors.request.use((config) => {
      const token = localStorage.getItem("token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Refresh-token interceptor
    const interceptor = api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          try {
            const refreshToken = localStorage.getItem("refresh_token");
            if (!refreshToken) throw new Error("No refresh token");

            const res = await api.post("/api/auth/refresh", {
  refresh_token: refreshToken
});


            const { access_token } = res.data;
            localStorage.setItem("token", access_token);
            setToken(access_token);

            originalRequest.headers.Authorization = `Bearer ${access_token}`;
            return api(originalRequest);
          } catch {
            logout();
          }
        }
        return Promise.reject(error);
      }
    );

    if (token) {
      fetchCurrentUser();
    } else {
      setLoading(false);
    }

    return () => api.interceptors.response.eject(interceptor);
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const res = await api.get("/api/auth/me");
      setUser(res.data);
    } catch {
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const res = await api.post("/api/auth/login", { email, password });
    const { access_token, refresh_token, user } = res.data;

    localStorage.setItem("token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    setToken(access_token);
    setUser(user);
    return user;
  };

  const register = async (name, email, password) => {
    const res = await api.post("/api/auth/register", {
      name,
      email,
      password,
    });

    const { access_token, refresh_token, user } = res.data;
    localStorage.setItem("token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    setToken(access_token);
    setUser(user);
    return user;
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
