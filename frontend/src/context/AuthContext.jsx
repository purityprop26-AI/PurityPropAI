import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

// Use environment variable for API URL, fallback to relative path for development
const API_URL = import.meta.env.VITE_API_URL;


const AuthContext = createContext(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(localStorage.getItem('token'));
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check if user is logged in on mount
        if (token) {
            fetchCurrentUser();
        } else {
            setLoading(false);
        }

        // Axios Interceptor for automated token refresh
        const interceptor = axios.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;
                // If 401 Unauthorized and not already retried
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;
                    try {
                        const refreshToken = localStorage.getItem('refresh_token');
                        if (!refreshToken) throw new Error('No refresh token');

                        const res = await axios.post(`${API_URL}/api/auth/refresh`, { refresh_token: refreshToken });
                        const { access_token } = res.data;

                        // Update local storage and state
                        localStorage.setItem('token', access_token);
                        setToken(access_token);

                        // Update header and retry
                        originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
                        return axios(originalRequest);
                    } catch (refreshError) {
                        // Refresh failed (token expired or invalid)
                        logout();
                        return Promise.reject(refreshError);
                    }
                }
                return Promise.reject(error);
            }
        );

        // Cleanup interceptor on unmount
        return () => {
            axios.interceptors.response.eject(interceptor);
        };
    }, []);

    const fetchCurrentUser = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/auth/me`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setUser(response.data);
        } catch (error) {
            // Let the interceptor handle 401s, but if it fails completely:
            if (!localStorage.getItem('token')) {
                logout();
            }
        } finally {
            setLoading(false);
        }
    };

    const login = async (email, password) => {
        const response = await axios.post(`${API_URL}/api/auth/login`, { email, password });
        const { access_token, refresh_token, user: userData } = response.data;

        localStorage.setItem('token', access_token);
        localStorage.setItem('refresh_token', refresh_token);
        setToken(access_token);
        setUser(userData);

        return userData;
    };

    const register = async (name, email, password) => {
        const response = await axios.post(`${API_URL}/api/auth/register`, { name, email, password });
        const { access_token, refresh_token, user: userData } = response.data;

        localStorage.setItem('token', access_token);
        localStorage.setItem('refresh_token', refresh_token);
        setToken(access_token);
        setUser(userData);

        return userData;
    };

    const logout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        setToken(null);
        setUser(null);
    };

    const value = {
        user,
        token,
        loading,
        login,
        register,
        logout,
        isAuthenticated: !!user
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
