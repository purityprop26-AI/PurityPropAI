import axios from 'axios';
import { supabase } from '../lib/supabase';

// Use environment variable for API URL
const API_URL = (import.meta.env.VITE_API_URL || '').trim();

// Create axios instance with base configuration
const apiClient = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add request interceptor to include Supabase auth token
apiClient.interceptors.request.use(
    async (config) => {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
            config.headers.Authorization = `Bearer ${session.access_token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

export default apiClient;
