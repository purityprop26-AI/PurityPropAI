import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, AlertCircle, CheckCircle, Loader2, ArrowLeft, KeyRound } from 'lucide-react';
import logoImage from '../assets/logo.png';
import '../styles/auth.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ForgotPassword = () => {
    const [email, setEmail] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!email) { setError('Please enter your email address.'); return; }
        setError('');
        setLoading(true);

        try {
            const res = await fetch(`${API_URL}/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            const data = await res.json();

            if (!res.ok) {
                if (res.status === 429) setError('Too many requests. Please wait a few minutes.');
                else setError(data.detail || 'Something went wrong. Try again.');
                return;
            }

            // Always show success (server uses generic message for security)
            setSuccess(true);

        } catch {
            setError('Cannot connect to server. Try again later.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card verify-card">
                {/* Logo */}
                <div className="auth-logo">
                    <img src={logoImage} alt="PurityProp AI" className="auth-logo-image" />
                    <span className="auth-logo-text">PurityProp</span>
                </div>

                {/* Icon */}
                <div className="verify-icon-wrapper">
                    <div className="verify-icon-ring" style={{ background: 'rgba(251,191,36,0.1)', borderColor: 'rgba(251,191,36,0.3)' }}>
                        <KeyRound size={32} style={{ color: '#FBBF24' }} />
                    </div>
                </div>

                {/* Header */}
                <div className="auth-header">
                    <h1 className="auth-title">Forgot password?</h1>
                    <p className="auth-subtitle">
                        {success
                            ? 'Check your inbox for the reset code.'
                            : "Enter your email and we'll send you a reset code."
                        }
                    </p>
                </div>

                {/* Error */}
                {error && (
                    <div className="error-message">
                        <AlertCircle size={18} /><span>{error}</span>
                    </div>
                )}

                {/* Success state */}
                {success ? (
                    <div className="reset-success-box">
                        <div className="reset-success-icon">
                            <CheckCircle size={28} />
                        </div>
                        <p className="reset-success-text">
                            We've sent a 6-digit code to <strong>{email}</strong>.
                            Check your spam folder if it doesn't arrive within a minute.
                        </p>
                        <button
                            id="goto-reset-btn"
                            type="button"
                            className="auth-button"
                            onClick={() => navigate('/reset-password', { state: { email } })}
                        >
                            <KeyRound size={18} /> Enter Reset Code
                        </button>
                    </div>
                ) : (
                    <form className="auth-form" onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label htmlFor="reset-email" className="form-label">
                                <Mail size={18} />Email Address
                            </label>
                            <input
                                id="reset-email"
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="your.email@example.com"
                                className="form-input"
                                required
                                disabled={loading}
                                autoComplete="email"
                                autoFocus
                            />
                        </div>

                        <button
                            id="forgot-submit-btn"
                            type="submit"
                            className="auth-button"
                            disabled={loading}
                        >
                            {loading
                                ? <><Loader2 size={20} className="spinner" />Sending code...</>
                                : <><Mail size={20} />Send Reset Code</>
                            }
                        </button>
                    </form>
                )}

                {/* Back */}
                <div className="auth-footer" style={{ marginTop: '1.25rem' }}>
                    <Link to="/login" className="auth-link back-link">
                        <ArrowLeft size={16} /> Back to Sign In
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default ForgotPassword;
