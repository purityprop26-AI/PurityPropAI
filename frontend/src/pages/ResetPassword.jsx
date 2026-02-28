import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
    Lock, KeyRound, Eye, EyeOff, AlertCircle, CheckCircle,
    Loader2, RefreshCw, ArrowLeft
} from 'lucide-react';
import logoImage from '../assets/logo.png';
import '../styles/auth.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const OTP_LENGTH = 6;

const ResetPassword = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const email = location.state?.email || '';

    const [otp, setOtp] = useState(Array(OTP_LENGTH).fill(''));
    const [newPassword, setNewPwd] = useState('');
    const [confirmPwd, setConfirm] = useState('');
    const [showNew, setShowNew] = useState(false);
    const [showConf, setShowConf] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const [resending, setResending] = useState(false);
    const [resendCooldown, setResendCooldown] = useState(0);

    const inputRefs = useRef([]);

    useEffect(() => {
        if (!email) navigate('/forgot-password', { replace: true });
    }, [email, navigate]);

    useEffect(() => {
        if (resendCooldown <= 0) return;
        const t = setInterval(() => setResendCooldown(c => c - 1), 1000);
        return () => clearInterval(t);
    }, [resendCooldown]);

    // ── OTP input ──────────────────────────────────────────────────────
    const handleOtpChange = (index, value) => {
        const digit = value.replace(/\D/g, '').slice(-1);
        const next = [...otp];
        next[index] = digit;
        setOtp(next);
        if (digit && index < OTP_LENGTH - 1) inputRefs.current[index + 1]?.focus();
    };

    const handleOtpKeyDown = (index, e) => {
        if (e.key === 'Backspace' && !otp[index] && index > 0)
            inputRefs.current[index - 1]?.focus();
    };

    const handlePaste = (e) => {
        e.preventDefault();
        const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);
        if (pasted.length === OTP_LENGTH) {
            setOtp(pasted.split(''));
            inputRefs.current[OTP_LENGTH - 1]?.focus();
        }
    };

    const otpValue = otp.join('');
    const otpDone = otpValue.length === OTP_LENGTH;

    // ── Password strength ──────────────────────────────────────────────
    const strength = (() => {
        let s = 0;
        if (newPassword.length >= 8) s += 25;
        if (newPassword.length >= 12) s += 25;
        if (/[a-z]/.test(newPassword) && /[A-Z]/.test(newPassword)) s += 25;
        if (/\d/.test(newPassword)) s += 25;
        return s;
    })();
    const strengthClass = strength < 50 ? 'weak' : strength < 75 ? 'medium' : 'strong';

    // ── Submit ─────────────────────────────────────────────────────────
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (!otpDone) { setError('Please enter the 6-digit code.'); return; }
        if (newPassword.length < 8) { setError('Password must be at least 8 characters.'); return; }
        if (!/[A-Z]/.test(newPassword)) { setError('Password needs at least 1 uppercase letter.'); return; }
        if (!/\d/.test(newPassword)) { setError('Password needs at least 1 number.'); return; }
        if (newPassword !== confirmPwd) { setError('Passwords do not match.'); return; }

        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/auth/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email,
                    otp: otpValue,
                    new_password: newPassword,
                }),
            });
            const data = await res.json();

            if (!res.ok) {
                if (res.status === 429) setError('Too many attempts. Request a new code.');
                else setError(data.detail || 'Reset failed. Try again.');
                setOtp(Array(OTP_LENGTH).fill(''));
                inputRefs.current[0]?.focus();
                return;
            }

            setSuccess('Password reset successfully! Redirecting to login...');
            setTimeout(() => navigate('/login', { replace: true }), 2000);

        } catch {
            setError('Cannot connect to server. Try again.');
        } finally {
            setLoading(false);
        }
    };

    // ── Resend ─────────────────────────────────────────────────────────
    const handleResend = async () => {
        if (resendCooldown > 0) return;
        setResending(true);
        setError('');
        try {
            const res = await fetch(`${API_URL}/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            if (res.status === 429) {
                setError('Too many requests. Please wait a few minutes.');
                setResendCooldown(120);
                return;
            }
            setOtp(Array(OTP_LENGTH).fill(''));
            inputRefs.current[0]?.focus();
            setResendCooldown(60);
        } catch {
            setError('Unable to resend. Try again.');
        } finally {
            setResending(false);
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
                    <h1 className="auth-title">Reset your password</h1>
                    <p className="auth-subtitle">
                        Enter the 6-digit code sent to{' '}
                        <strong className="verify-email-highlight">{email}</strong>
                    </p>
                </div>

                {/* Alerts */}
                {error && <div className="error-message"><AlertCircle size={18} /><span>{error}</span></div>}
                {success && <div className="success-message"><CheckCircle size={18} /><span>{success}</span></div>}

                <form className="auth-form" onSubmit={handleSubmit}>
                    {/* OTP */}
                    <div className="otp-grid" role="group" aria-label="Reset code input">
                        {otp.map((digit, i) => (
                            <input
                                key={i}
                                id={`reset-otp-${i}`}
                                ref={el => (inputRefs.current[i] = el)}
                                type="text"
                                inputMode="numeric"
                                pattern="\d*"
                                maxLength={2}
                                value={digit}
                                onChange={e => handleOtpChange(i, e.target.value)}
                                onKeyDown={e => handleOtpKeyDown(i, e)}
                                onPaste={handlePaste}
                                className={`otp-input ${digit ? 'otp-filled' : ''}`}
                                style={{ borderColor: digit ? 'rgba(251,191,36,0.5)' : undefined }}
                                disabled={loading || !!success}
                                autoComplete="one-time-code"
                                aria-label={`Digit ${i + 1}`}
                            />
                        ))}
                    </div>

                    {/* New Password */}
                    <div className="form-group">
                        <label htmlFor="new-password" className="form-label">
                            <Lock size={18} />New Password
                        </label>
                        <div className="input-wrapper">
                            <input
                                id="new-password"
                                type={showNew ? 'text' : 'password'}
                                value={newPassword}
                                onChange={e => setNewPwd(e.target.value)}
                                placeholder="Min 8 chars, 1 uppercase, 1 number"
                                className="form-input"
                                required
                                disabled={loading || !!success}
                                autoComplete="new-password"
                            />
                            <button type="button" className="password-toggle"
                                onClick={() => setShowNew(!showNew)} tabIndex={-1}>
                                {showNew ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                        {newPassword && (
                            <div className="password-strength">
                                <div className="strength-bar">
                                    <div className={`strength-fill ${strengthClass}`} />
                                </div>
                                <span className={`strength-text ${strengthClass}`}>
                                    {strength < 50 ? 'Weak' : strength < 75 ? 'Medium' : 'Strong'} password
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Confirm Password */}
                    <div className="form-group">
                        <label htmlFor="confirm-password" className="form-label">
                            <Lock size={18} />Confirm Password
                        </label>
                        <div className="input-wrapper">
                            <input
                                id="confirm-password"
                                type={showConf ? 'text' : 'password'}
                                value={confirmPwd}
                                onChange={e => setConfirm(e.target.value)}
                                placeholder="Re-enter new password"
                                className="form-input"
                                required
                                disabled={loading || !!success}
                                autoComplete="new-password"
                            />
                            <button type="button" className="password-toggle"
                                onClick={() => setShowConf(!showConf)} tabIndex={-1}>
                                {showConf ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                    </div>

                    {/* Submit */}
                    <button
                        id="reset-submit-btn"
                        type="submit"
                        className="auth-button"
                        disabled={!otpDone || loading || !!success}
                    >
                        {loading
                            ? <><Loader2 size={20} className="spinner" />Resetting...</>
                            : <><KeyRound size={20} />Reset Password</>
                        }
                    </button>
                </form>

                {/* Resend */}
                <div className="resend-wrapper">
                    <p className="resend-text">Didn't receive the code?</p>
                    <button id="resend-reset-btn" type="button" className="resend-btn"
                        onClick={handleResend} disabled={resending || resendCooldown > 0}>
                        {resending
                            ? <><Loader2 size={16} className="spinner" />Sending...</>
                            : resendCooldown > 0
                                ? <><RefreshCw size={16} />Resend in {resendCooldown}s</>
                                : <><RefreshCw size={16} />Resend code</>
                        }
                    </button>
                </div>

                {/* Back */}
                <div className="auth-footer">
                    <Link to="/login" className="auth-link back-link">
                        <ArrowLeft size={16} /> Back to Sign In
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default ResetPassword;
