import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserPlus, Mail, Lock, User, AlertCircle, Loader2, CheckCircle, Eye, EyeOff } from 'lucide-react';
import logoImage from '../assets/logo.png';
import '../styles/auth.css';

const GoogleIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" />
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
);

const Register = () => {
    const [formData, setFormData] = useState({ name: '', email: '', password: '', confirmPassword: '' });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);
    const [passwordStrength, setPasswordStrength] = useState(0);
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    const { loginWithGoogle } = useAuth();
    const navigate = useNavigate();

    const calcStrength = (pwd) => {
        let s = 0;
        if (pwd.length >= 8) s += 25;
        if (pwd.length >= 12) s += 25;
        if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) s += 25;
        if (/\d/.test(pwd)) s += 25;
        return s;
    };

    const strengthClass = passwordStrength < 50 ? 'weak' : passwordStrength < 75 ? 'medium' : 'strong';
    const strengthText = passwordStrength < 50 ? 'Weak password' : passwordStrength < 75 ? 'Medium password' : 'Strong password';

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
        if (name === 'password') setPasswordStrength(calcStrength(value));
    };

    // ── Email Registration ─────────────────────────────────────────────
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (!formData.name.trim() || formData.name.trim().length < 2) {
            setError('Name must be at least 2 characters.'); return;
        }
        if (formData.password.length < 8) {
            setError('Password must be at least 8 characters.'); return;
        }
        if (!/[A-Z]/.test(formData.password)) {
            setError('Password must contain at least 1 uppercase letter.'); return;
        }
        if (!/\d/.test(formData.password)) {
            setError('Password must contain at least 1 number.'); return;
        }
        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match.'); return;
        }

        setLoading(true);
        try {
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const res = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.name.trim(),
                    email: formData.email,
                    password: formData.password,
                }),
            });
            const data = await res.json();

            if (!res.ok) {
                const detail = data.detail || 'Registration failed.';
                if (res.status === 429) setError('Too many attempts. Please try again later.');
                else if (detail.includes('already registered') || detail.includes('already exists')) {
                    setError('This email is already registered. Please login.');
                } else {
                    setError(detail);
                }
                return;
            }

            // Success → redirect to OTP verification page
            navigate('/verify-email', {
                state: { email: formData.email, name: formData.name.trim() },
            });

        } catch (err) {
            setError(err.message === 'Failed to fetch'
                ? 'Cannot connect to server. Try again later.'
                : 'Registration failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    // ── Google OAuth (same as login — creates account if new) ──────────
    const handleGoogleRegister = async () => {
        setError('');
        setGoogleLoading(true);
        try {
            await loginWithGoogle();
        } catch (err) {
            setError(err.message || 'Google sign-up failed. Try again.');
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
                    <h1 className="auth-title">Create your account</h1>
                    <p className="auth-subtitle">Join Purity Prop AI</p>
                </div>

                {/* Error */}
                {error && (
                    <div className="error-message">
                        <AlertCircle size={18} /><span>{error}</span>
                    </div>
                )}

                {/* Google Button */}
                <button id="google-signup-btn" type="button" className="google-btn"
                    onClick={handleGoogleRegister} disabled={isDisabled}>
                    {googleLoading ? <Loader2 size={20} className="spinner" /> : <GoogleIcon />}
                    {googleLoading ? 'Connecting...' : 'Continue with Google'}
                </button>

                {/* Divider */}
                <div className="auth-divider">
                    <span className="divider-line" />
                    <span className="divider-text">or register with email</span>
                    <span className="divider-line" />
                </div>

                {/* Form */}
                <form className="auth-form" onSubmit={handleSubmit}>
                    {/* Name */}
                    <div className="form-group">
                        <label htmlFor="name" className="form-label"><User size={18} />Full Name</label>
                        <input id="name" name="name" type="text" value={formData.name}
                            onChange={handleChange} placeholder="Enter your full name"
                            className="form-input" required disabled={isDisabled} autoComplete="name" />
                    </div>

                    {/* Email */}
                    <div className="form-group">
                        <label htmlFor="email" className="form-label"><Mail size={18} />Email Address</label>
                        <input id="email" name="email" type="email" value={formData.email}
                            onChange={handleChange} placeholder="your.email@example.com"
                            className="form-input" required disabled={isDisabled} autoComplete="email" />
                    </div>

                    {/* Password */}
                    <div className="form-group">
                        <label htmlFor="password" className="form-label"><Lock size={18} />Password</label>
                        <div className="input-wrapper">
                            <input id="password" name="password"
                                type={showPassword ? 'text' : 'password'}
                                value={formData.password} onChange={handleChange}
                                placeholder="Min 8 chars, 1 uppercase, 1 number"
                                className="form-input" required disabled={isDisabled}
                                autoComplete="new-password" />
                            <button type="button" className="password-toggle"
                                onClick={() => setShowPassword(!showPassword)} tabIndex={-1}>
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                        {formData.password && (
                            <div className="password-strength">
                                <div className="strength-bar">
                                    <div className={`strength-fill ${strengthClass}`} />
                                </div>
                                <span className={`strength-text ${strengthClass}`}>{strengthText}</span>
                            </div>
                        )}
                    </div>

                    {/* Confirm Password */}
                    <div className="form-group">
                        <label htmlFor="confirmPassword" className="form-label"><CheckCircle size={18} />Confirm Password</label>
                        <div className="input-wrapper">
                            <input id="confirmPassword" name="confirmPassword"
                                type={showConfirm ? 'text' : 'password'}
                                value={formData.confirmPassword} onChange={handleChange}
                                placeholder="Re-enter your password"
                                className="form-input" required disabled={isDisabled}
                                autoComplete="new-password" />
                            <button type="button" className="password-toggle"
                                onClick={() => setShowConfirm(!showConfirm)} tabIndex={-1}>
                                {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                    </div>

                    {/* Submit */}
                    <button id="register-submit-btn" type="submit" className="auth-button" disabled={isDisabled}>
                        {loading ? <><Loader2 size={20} className="spinner" />Creating account...</>
                            : <><UserPlus size={20} />Create Account</>}
                    </button>
                </form>

                <div className="auth-footer">
                    <p className="auth-footer-text">
                        Already have an account?{' '}
                        <Link to="/login" className="auth-link">Sign in here</Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Register;
