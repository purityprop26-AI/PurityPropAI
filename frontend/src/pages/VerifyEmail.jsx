import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, AlertCircle, CheckCircle, Loader2, RefreshCw, Mail } from 'lucide-react';
import logoImage from '../assets/logo.png';
import '../styles/auth.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const OTP_LENGTH = 6;

const VerifyEmail = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { loginWithToken } = useAuth();

    // Email + name from Register.jsx navigation state
    const email = location.state?.email || '';
    const name = location.state?.name || '';

    const [otp, setOtp] = useState(Array(OTP_LENGTH).fill(''));
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const [resending, setResending] = useState(false);
    const [resendCooldown, setResendCooldown] = useState(0);

    // Refs for each digit input — for auto-advance focus
    const inputRefs = useRef([]);

    // Redirect to register if no email in state
    useEffect(() => {
        if (!email) navigate('/register', { replace: true });
    }, [email, navigate]);

    // Countdown timer for resend cooldown
    useEffect(() => {
        if (resendCooldown <= 0) return;
        const timer = setInterval(() => setResendCooldown(c => c - 1), 1000);
        return () => clearInterval(timer);
    }, [resendCooldown]);

    // ── OTP input handling ─────────────────────────────────────────────
    const handleOtpChange = (index, value) => {
        // Allow only single digit
        const digit = value.replace(/\D/g, '').slice(-1);
        const newOtp = [...otp];
        newOtp[index] = digit;
        setOtp(newOtp);

        // Auto-advance to next input
        if (digit && index < OTP_LENGTH - 1) {
            inputRefs.current[index + 1]?.focus();
        }
    };

    const handleOtpKeyDown = (index, e) => {
        if (e.key === 'Backspace' && !otp[index] && index > 0) {
            inputRefs.current[index - 1]?.focus();
        }
        // Allow paste
        if (e.key === 'Enter') handleVerify();
    };

    const handleOtpPaste = (e) => {
        e.preventDefault();
        const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);
        if (pasted.length === OTP_LENGTH) {
            setOtp(pasted.split(''));
            inputRefs.current[OTP_LENGTH - 1]?.focus();
        }
    };

    const otpValue = otp.join('');
    const isComplete = otpValue.length === OTP_LENGTH;

    // ── Verify OTP ─────────────────────────────────────────────────────
    const handleVerify = async () => {
        if (!isComplete) { setError('Please enter the complete 6-digit code.'); return; }
        setError('');
        setLoading(true);

        try {
            const res = await fetch(`${API_URL}/auth/verify-email`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, otp: otpValue }),
            });
            const data = await res.json();

            if (!res.ok) {
                const detail = data.detail || 'Verification failed.';
                if (res.status === 429) setError('Too many attempts. Please request a new code.');
                else setError(detail);
                // Clear OTP on failure
                setOtp(Array(OTP_LENGTH).fill(''));
                inputRefs.current[0]?.focus();
                return;
            }

            // Success — store token and redirect to dashboard
            setSuccess('Email verified! Redirecting...');
            if (data.access_token) {
                await loginWithToken(data.access_token, data.user);
            }
            setTimeout(() => navigate('/dashboard', { replace: true }), 1200);

        } catch (err) {
            setError('Cannot connect to server. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    // ── Resend OTP ─────────────────────────────────────────────────────
    const handleResend = async () => {
        if (resendCooldown > 0) return;
        setError('');
        setResending(true);

        try {
            const res = await fetch(`${API_URL}/auth/resend-otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            const data = await res.json();

            if (!res.ok) {
                if (res.status === 429) {
                    setError('Too many resend requests. Please wait a few minutes.');
                    setResendCooldown(120);  // 2 min cooldown on rate limit
                } else {
                    setError(data.detail || 'Failed to resend. Try again.');
                }
                return;
            }

            setSuccess('A new verification code has been sent to your email.');
            setOtp(Array(OTP_LENGTH).fill(''));
            inputRefs.current[0]?.focus();
            setResendCooldown(60);  // 60s cooldown

        } catch {
            setError('Cannot connect to server. Please try again.');
        } finally {
            setResending(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card verify-card">
                {/* Logo */}
                <div className="auth-logo">
                    <img src={logoImage} alt="Purity Prop AI" className="auth-logo-image" />
                    <span className="auth-logo-text">PurityProp</span>
                </div>

                {/* Icon */}
                <div className="verify-icon-wrapper">
                    <div className="verify-icon-ring">
                        <ShieldCheck size={32} className="verify-icon" />
                    </div>
                </div>

                {/* Header */}
                <div className="auth-header">
                    <h1 className="auth-title">Verify your email</h1>
                    <p className="auth-subtitle">
                        We sent a 6-digit code to{' '}
                        <strong className="verify-email-highlight">{email}</strong>
                    </p>
                </div>

                {/* Alerts */}
                {error && (
                    <div className="error-message">
                        <AlertCircle size={18} /><span>{error}</span>
                    </div>
                )}
                {success && (
                    <div className="success-message">
                        <CheckCircle size={18} /><span>{success}</span>
                    </div>
                )}

                {/* ── OTP Input Grid ──────────────────────────────────── */}
                <div className="otp-grid" role="group" aria-label="OTP input">
                    {otp.map((digit, index) => (
                        <input
                            key={index}
                            id={`otp-digit-${index}`}
                            ref={el => (inputRefs.current[index] = el)}
                            type="text"
                            inputMode="numeric"
                            pattern="\d*"
                            maxLength={2}
                            value={digit}
                            onChange={e => handleOtpChange(index, e.target.value)}
                            onKeyDown={e => handleOtpKeyDown(index, e)}
                            onPaste={handleOtpPaste}
                            className={`otp-input ${digit ? 'otp-filled' : ''}`}
                            disabled={loading || !!success}
                            autoComplete="one-time-code"
                            aria-label={`Digit ${index + 1}`}
                        />
                    ))}
                </div>

                {/* Verify Button */}
                <button
                    id="verify-otp-btn"
                    type="button"
                    className="auth-button"
                    onClick={handleVerify}
                    disabled={!isComplete || loading || !!success}
                >
                    {loading
                        ? <><Loader2 size={20} className="spinner" />Verifying...</>
                        : <><ShieldCheck size={20} />Verify Email</>
                    }
                </button>

                {/* Resend */}
                <div className="resend-wrapper">
                    <p className="resend-text">Didn't receive the code?</p>
                    <button
                        id="resend-otp-btn"
                        type="button"
                        className="resend-btn"
                        onClick={handleResend}
                        disabled={resending || resendCooldown > 0}
                    >
                        {resending
                            ? <><Loader2 size={16} className="spinner" />Sending...</>
                            : resendCooldown > 0
                                ? <><RefreshCw size={16} />Resend in {resendCooldown}s</>
                                : <><Mail size={16} />Resend code</>
                        }
                    </button>
                </div>

                {/* Footer */}
                <div className="auth-footer">
                    <p className="auth-footer-text">
                        Wrong email?{' '}
                        <Link to="/register" className="auth-link">Go back</Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default VerifyEmail;
