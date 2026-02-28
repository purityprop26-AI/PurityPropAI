/**
 * ErrorBoundary — React class component for catching JS runtime errors.
 *
 * FIX [HIGH-F1]: Without this, any unhandled JS error in any child component
 *                causes a full white-screen crash with no user feedback.
 *
 * Catches:
 *   - Component render errors
 *   - Errors in lifecycle methods
 *   - Errors in constructors of child components
 *
 * Does NOT catch:
 *   - Async errors (use .catch() / try-catch for those)
 *   - Event handler errors (use try-catch inside handlers)
 *   - Server-side errors
 */

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
        };
    }

    static getDerivedStateFromError(error) {
        // Update state so next render shows fallback UI
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        // Log to console in dev; in production, send to error tracking service
        console.error('[ErrorBoundary] Caught error:', error, errorInfo);
        this.setState({ errorInfo });
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
    };

    render() {
        if (this.state.hasError) {
            return (
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minHeight: '100vh',
                    background: 'var(--bg-primary, #0f0f13)',
                    color: 'var(--text-primary, #eeeef2)',
                    fontFamily: 'Inter, sans-serif',
                    padding: '2rem',
                    textAlign: 'center',
                    gap: '1.5rem',
                }}>
                    <AlertTriangle size={48} style={{ color: '#f59e0b' }} />

                    <div>
                        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                            Something went wrong
                        </h2>
                        <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.9rem', maxWidth: '400px' }}>
                            An unexpected error occurred. You can try refreshing this section,
                            or reload the full page if the problem persists.
                        </p>
                    </div>

                    {/* Show error detail only in development */}
                    {process.env.NODE_ENV === 'development' && this.state.error && (
                        <pre style={{
                            background: 'rgba(255,0,0,0.08)',
                            border: '1px solid rgba(255,0,0,0.2)',
                            borderRadius: '8px',
                            padding: '1rem',
                            fontSize: '0.75rem',
                            color: '#f87171',
                            maxWidth: '600px',
                            maxHeight: '200px',
                            overflow: 'auto',
                            textAlign: 'left',
                            width: '100%',
                        }}>
                            {this.state.error.toString()}
                            {this.state.errorInfo?.componentStack}
                        </pre>
                    )}

                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <button
                            onClick={this.handleReset}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.75rem 1.5rem',
                                background: 'rgba(255,255,255,0.08)',
                                border: '1px solid rgba(255,255,255,0.15)',
                                borderRadius: '8px',
                                color: 'inherit',
                                cursor: 'pointer',
                                fontSize: '0.9rem',
                                transition: 'all 0.2s ease',
                            }}
                        >
                            <RefreshCw size={16} />
                            Try Again
                        </button>

                        <button
                            onClick={() => window.location.href = '/dashboard'}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.75rem 1.5rem',
                                background: 'rgba(255,255,255,0.04)',
                                border: '1px solid rgba(255,255,255,0.08)',
                                borderRadius: '8px',
                                color: 'rgba(255,255,255,0.6)',
                                cursor: 'pointer',
                                fontSize: '0.9rem',
                            }}
                        >
                            Go to Dashboard
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
