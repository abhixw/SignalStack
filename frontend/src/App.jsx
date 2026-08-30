import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import OutcomeCreate from './pages/OutcomeCreate';
import ProofSubmit from './pages/ProofSubmit';
import CandidateDecision from './pages/CandidateDecision';
import OutcomeDashboard from './pages/OutcomeDashboard';
import FeedbackView from './pages/FeedbackView';
import AdminAudit from './pages/AdminAudit';
import CandidateJobs from './pages/CandidateJobs';
import CandidateApplications from './pages/CandidateApplications';
import Login from './pages/Login';
import Register from './pages/Register';
import GithubCallback from './pages/GithubCallback';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

function PostLogin() {
    const { user } = useAuth();
    if (!user) return <Navigate to="/login" replace />;
    return <Navigate to={user.role === 'candidate' ? '/candidate/jobs' : '/'} replace />;
}

function NavLinks() {
    const location = useLocation();
    const { user } = useAuth();
    const isCandidate = user?.role === 'candidate';

    if (isCandidate) {
        return (
            <>
                <Link to="/candidate/jobs" className={`${location.pathname === '/candidate/jobs' ? 'border-indigo-500 text-gray-900' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
                    Available Jobs
                </Link>
                <Link to="/candidate/applications" className={`${location.pathname === '/candidate/applications' ? 'border-indigo-500 text-gray-900' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
                    My Applications
                </Link>
            </>
        );
    }

    if (!user) return null;

    return (
        <>
            <Link to="/" className={`${location.pathname === '/' ? 'border-indigo-500 text-gray-900' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
                Outcomes
            </Link>
            {user.role === 'admin' && (
                <>
                    <Link to="/learning" className={`${location.pathname === '/learning' ? 'border-indigo-500 text-gray-900' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
                        System Learning
                    </Link>
                    <Link to="/admin/audit" className={`${location.pathname === '/admin/audit' ? 'border-indigo-500 text-gray-900' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
                        Audit Logs
                    </Link>
                </>
            )}
        </>
    );
}

function AccountControl() {
    const { user, logout } = useAuth();
    if (!user) {
        return (
            <div className="flex items-center gap-3">
                <Link to="/login" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">Sign in</Link>
                <Link to="/register" className="text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-md shadow-sm">Register</Link>
            </div>
        );
    }
    return (
        <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">{user.email} <span className="text-gray-400">({user.role})</span></span>
            <button onClick={logout} className="text-sm font-medium text-gray-600 hover:text-gray-900 border border-gray-300 px-3 py-1.5 rounded-md">
                Log out
            </button>
        </div>
    );
}

function AppShell() {
    return (
        <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
            <nav className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex items-center">
                            <div className="flex-shrink-0 flex items-center mr-8">
                                <span className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600 tracking-tight">
                                    Recruvoskill
                                </span>
                            </div>
                            <div className="hidden sm:flex sm:space-x-8 h-full">
                                <NavLinks />
                            </div>
                        </div>
                        <div className="flex items-center">
                            <AccountControl />
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto py-8 sm:px-6 lg:px-8">
                <Routes>
                    <Route path="/post-login" element={<PostLogin />} />

                    {/* Recruiter Routes */}
                    <Route path="/" element={
                        <ProtectedRoute roles={['recruiter', 'admin']}><Dashboard /></ProtectedRoute>
                    } />
                    <Route path="/create-outcome" element={
                        <ProtectedRoute roles={['recruiter', 'admin']}><OutcomeCreate /></ProtectedRoute>
                    } />
                    <Route path="/dashboard/:outcomeId" element={
                        <ProtectedRoute roles={['recruiter', 'admin']}><OutcomeDashboard /></ProtectedRoute>
                    } />
                    <Route path="/dashboard/:outcomeId/candidate/:candidateEmail" element={
                        <ProtectedRoute roles={['recruiter', 'admin']}><CandidateDecision /></ProtectedRoute>
                    } />
                    <Route path="/learning" element={
                        <ProtectedRoute roles={['admin']}><FeedbackView /></ProtectedRoute>
                    } />
                    <Route path="/admin/audit" element={
                        <ProtectedRoute roles={['admin']}><AdminAudit /></ProtectedRoute>
                    } />

                    {/* Candidate Routes */}
                    <Route path="/candidate" element={<Navigate to="/login" replace />} />
                    <Route path="/candidate/jobs" element={<CandidateJobs />} />
                    <Route path="/candidate/applications" element={
                        <ProtectedRoute roles={['candidate']}><CandidateApplications /></ProtectedRoute>
                    } />
                    <Route path="/submit-proof/:outcomeId" element={
                        <ProtectedRoute roles={['candidate']}><ProofSubmit /></ProtectedRoute>
                    } />
                </Routes>
            </main>
        </div>
    );
}

function App() {
    return (
        <Router>
            <AuthProvider>
                <Routes>
                    {/* Full-screen takeover — no nav bar / content padding from AppShell */}
                    <Route path="/login" element={<Login />} />
                    <Route path="/register" element={<Register />} />
                    <Route path="/auth/github/complete" element={<GithubCallback />} />
                    <Route path="/*" element={<AppShell />} />
                </Routes>
            </AuthProvider>
        </Router>
    );
}

export default App;
