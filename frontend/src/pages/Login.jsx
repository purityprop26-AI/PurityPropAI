import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogIn, Mail, Lock, AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react';
import logoImage from '../assets/logo.png';
import '../styles/auth.css';

// ── Google SVG Icon (no external library needed) ───────────────────────
const GoogleIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" />
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
);

const Login = () => {
    const [formData, setFormData] = useState({ email: '', password: '', rememberMe: false });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    const { login, loginWithGoogle } = useAuth();
    const navigate = useNavigate();

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
    };

    // ── Email + Password submit ────────────────────────────────────────
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (!formData.email || !formData.password) { setError('Please fill in all fields'); return; }
        setLoading(true);
        try {
            await login(formData.email, formData.password);
            navigate('/dashboard');
        } catch (err) {
            const detail = err.response?.data?.detail || err.message || '';
            if (err.response?.status === 401) setError('Invalid email or password.');
            else if (err.response?.status === 403) setError(detail || 'Please verify your email before logging in.');
            else if (err.response?.status === 429) setError(detail || 'Too many attempts. Try again later.');
            else if (err.message === 'Network Error') setError('Cannot connect to server. Try again later.');
            else setError(detail || 'Login failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    // ── Google OAuth ───────────────────────────────────────────────────
    const handleGoogleLogin = async () => {
        setError('');
        setGoogleLoading(true);
        try {
            await loginWithGoogle();
            // Supabase OAuth redirects — no navigate() needed
        } catch (err) {
            setError(err.message || 'Google sign-in failed. Try again.');
            setGoogleLoading(false);
        }
    };

    const isDisabled = loading || googleLoading;

    return (
        <div className="auth-container">
            <div className="auth-card">
                {/* Logo */}
                <div className="auth-logo">
                    <img src={logoImage} alt="Purity Prop AI" className="auth-logo-image" />
                    <span className="auth-logo-text">PurityProp</span>
                </div>

                {/* Header */}
                <div className="auth-header">
                    <h1 className="auth-title">Welcome back</h1>
                    <p className="auth-subtitle">Sign in to your account</p>
                </div>

                {/* Error */}
                {error && (
                    <div className="error-message">
                        <AlertCircle size={18} />
                        <span>{error}</span>
                    </div>
                )}

                {/* ── Google Button ─────────────────────────────────── */}
                <button
                    id="google-signin-btn"
                    type="button"
                    className="google-btn"
                    onClick={handleGoogleLogin}
                    disabled={isDisabled}
                >
                    {googleLoading ? <Loader2 size={20} className="spinner" /> : <GoogleIcon />}
                    {googleLoading ? 'Connecting...' : 'Continue with Google'}
                </button>

                {/* ── Divider ───────────────────────────────────────── */}
                <div className="auth-divider">
                    <span className="divider-line" />
                    <span className="divider-text">or sign in with email</span>
                    <span className="divider-line" />
                </div>

                {/* ── Email form ────────────────────────────────────── */}
                <form className="auth-form" onSubmit={handleSubmit}>
                    {/* Email */}
                    <div className="form-group">
                        <label htmlFor="email" className="form-label">
                            <Mail size={18} />Email Address
                        </label>
                        <input
                            id="email" name="email" type="email"
                            value={formData.email} onChange={handleChange}
                            placeholder="your.email@example.com"
                            className="form-input" required disabled={isDisabled}
                            autoComplete="email"
                        />
                    </div>

                    {/* Password */}
                    <div className="form-group">
                        <label htmlFor="password" className="form-label">
                            <Lock size={18} />Password
                        </label>
                        <div className="input-wrapper">
                            <input
                                id="password" name="password"
                                type={showPassword ? 'text' : 'password'}
                                value={formData.password} onChange={handleChange}
                                placeholder="Enter your password"
                                className="form-input" required disabled={isDisabled}
                                autoComplete="current-password"
                            />
                            <button type="button" className="password-toggle"
                                onClick={() => setShowPassword(!showPassword)} tabIndex={-1}>
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                    </div>

                    {/* Remember + Forgot Password row */}
                    <div className="form-row-split">
                        <div className="checkbox-wrapper">
                            <input id="rememberMe" name="rememberMe" type="checkbox"
                                checked={formData.rememberMe} onChange={handleChange}
                                className="checkbox-input" disabled={isDisabled} />
                            <label htmlFor="rememberMe" className="checkbox-label">Remember me</label>
                        </div>
                        <Link to="/forgot-password" className="forgot-link">Forgot password?</Link>
                    </div>

                    {/* Submit */}
                    <button id="email-signin-btn" type="submit" className="auth-button" disabled={isDisabled}>
                        {loading ? <><Loader2 size={20} className="spinner" />Signing in...</>
                            : <><LogIn size={20} />Sign In</>}
                    </button>
                </form>

                {/* Footer */}
                <div className="auth-footer">
                    <p className="auth-footer-text">
                        Don't have an account?{' '}
                        <Link to="/register" className="auth-link">Create one now</Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;
