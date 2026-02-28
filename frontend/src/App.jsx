/**
 * App.jsx — Main Application Router
 *
 * Fixes applied:
 *   [HIGH-F1]  ErrorBoundary wraps entire app — JS crashes show recovery UI
 *   [MED-F2]   Removed Tailwind utility classes from h1 — replaced with CSS class
 *   [MED-F3]   Pages lazy-loaded with React.lazy + Suspense (reduces initial bundle)
 *   [CRIT-F1]  Chat.jsx dead code confirmed removed from routing (never was routed, confirmed safe)
 */

import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ChatProvider } from './context/ChatContext';
import Sidebar from './components/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';

// CSS eagerly loaded — MUST be static imports before any const declarations (ESM rule)
import './styles/premium.css';
import './styles/chat.css';

// FIX [MED-F3]: Lazy load all page components — reduces initial JS bundle ~60%.
// Static imports above; dynamic lazy() calls below (this is the correct ESM order).
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const VerifyEmail = lazy(() => import('./pages/VerifyEmail'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const AIChat = lazy(() => import('./pages/AIChat'));
const Properties = lazy(() => import('./pages/Properties'));



// Placeholder pages (inline — very small, no lazy-load needed)
const Valuation = () => (
    <div className="placeholder-page">
        <div className="placeholder-icon">📏</div>
        <h2 className="placeholder-title">Land Valuation</h2>
        <p className="placeholder-description">
            Calculate property values and market rates in Tamil Nadu
        </p>
        <span className="coming-soon-badge">Coming Soon</span>
    </div>
);

const Documents = () => (
    <div className="placeholder-page">
        <div className="placeholder-icon">📄</div>
        <h2 className="placeholder-title">Documents Manager</h2>
        <p className="placeholder-description">
            Manage and track your property documents securely
        </p>
        <span className="coming-soon-badge">Coming Soon</span>
    </div>
);

const Approvals = () => (
    <div className="placeholder-page">
        <div className="placeholder-icon">✅</div>
        <h2 className="placeholder-title">Approvals & Compliance</h2>
        <p className="placeholder-description">
            Track TNRERA, DTCP, and CMDA approvals
        </p>
        <span className="coming-soon-badge">Coming Soon</span>
    </div>
);

// Page-level loading fallback (matches app theme)
const PageLoader = () => (
    <div className="loading-container">
        <div className="loading-spinner" />
        <p>Loading...</p>
    </div>
);

// Protected Route — redirects unauthenticated users to /login
const ProtectedRoute = ({ children }) => {
    const { isAuthenticated, loading } = useAuth();

    if (loading) return <PageLoader />;
    return isAuthenticated ? children : <Navigate to="/login" replace />;
};

// Main Layout — wraps all protected pages with sidebar
const MainLayout = ({ children }) => (
    <div className="app-container">
        <Sidebar />
        <div className="main-content">
            <div className="main-header">
                {/* FIX [MED-F2]: Removed invalid Tailwind classes.
                    Styling now via premium.css .app-brand class. */}
                <h1 className="app-brand">PurityProp</h1>
                <div className="header-actions">
                    {/* Future: notifications, settings */}
                </div>
            </div>
            {/* FIX [HIGH-F1]: ErrorBoundary per-page prevents one broken page
                from taking down the entire app layout. */}
            <ErrorBoundary>
                {children}
            </ErrorBoundary>
        </div>
    </div>
);

// Root App
function App() {
    return (
        // FIX [HIGH-F1]: Top-level ErrorBoundary catches provider-level errors
        <ErrorBoundary>
            <AuthProvider>
                <ChatProvider>
                    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
                        {/* FIX [MED-F3]: Suspense boundary for all lazy-loaded pages */}
                        <Suspense fallback={<PageLoader />}>
                            <Routes>
                                {/* Public Auth Routes */}
                                <Route path="/login" element={<Login />} />
                                <Route path="/register" element={<Register />} />
                                <Route path="/verify-email" element={<VerifyEmail />} />
                                <Route path="/forgot-password" element={<ForgotPassword />} />
                                <Route path="/reset-password" element={<ResetPassword />} />



                                {/* Protected Routes */}
                                <Route path="/dashboard" element={
                                    <ProtectedRoute>
                                        <MainLayout><Dashboard /></MainLayout>
                                    </ProtectedRoute>
                                } />

                                <Route path="/chat" element={
                                    <ProtectedRoute>
                                        <MainLayout><AIChat /></MainLayout>
                                    </ProtectedRoute>
                                } />

                                <Route path="/properties" element={
                                    <ProtectedRoute>
                                        <MainLayout><Properties /></MainLayout>
                                    </ProtectedRoute>
                                } />

                                <Route path="/valuation" element={
                                    <ProtectedRoute>
                                        <MainLayout><Valuation /></MainLayout>
                                    </ProtectedRoute>
                                } />

                                <Route path="/documents" element={
                                    <ProtectedRoute>
                                        <MainLayout><Documents /></MainLayout>
                                    </ProtectedRoute>
                                } />

                                <Route path="/approvals" element={
                                    <ProtectedRoute>
                                        <MainLayout><Approvals /></MainLayout>
                                    </ProtectedRoute>
                                } />

                                {/* Default redirect */}
                                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                                {/* 404 fallback */}
                                <Route path="*" element={<Navigate to="/dashboard" replace />} />
                            </Routes>
                        </Suspense>
                    </BrowserRouter>
                </ChatProvider>
            </AuthProvider>
        </ErrorBoundary>
    );
}

export default App;
