import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import OutcomeCreate from './pages/OutcomeCreate';
import ProofSubmit from './pages/ProofSubmit';
import EvaluationView from './pages/EvaluationView';
import ReviewerQueue from './pages/ReviewerQueue';
import OutcomeDashboard from './pages/OutcomeDashboard';
import FeedbackView from './pages/FeedbackView';
import AdminAudit from './pages/AdminAudit';
import CandidatePortal from './pages/CandidatePortal';
import CandidateJobs from './pages/CandidateJobs';
import CandidateApplications from './pages/CandidateApplications';

function NavLinks() {
  const location = useLocation();
  const isCandidate = location.pathname.startsWith('/candidate') || location.pathname.startsWith('/submit-proof');

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

  return (
    <>
      <Link to="/" className={`${location.pathname === '/' ? 'border-indigo-500 text-gray-900' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
        Outcomes
      </Link>
      <Link to="/reviewer" className={`${location.pathname === '/reviewer' ? 'border-indigo-500 text-gray-900' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
        Review Queue
      </Link>
      <Link to="/learning" className={`${location.pathname === '/learning' ? 'border-indigo-500 text-gray-900' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
        System Learning
      </Link>
      <Link to="/admin/audit" className={`${location.pathname === '/admin/audit' ? 'border-indigo-500 text-gray-900' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
        Audit Logs
      </Link>
    </>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
        <nav className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <div className="flex-shrink-0 flex items-center mr-8">
                  <span className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600 tracking-tight">
                    SignalStack
                  </span>
                </div>
                <div className="hidden sm:flex sm:space-x-8 h-full">
                  <NavLinks />
                </div>
              </div>
              <div className="flex items-center">
                <Routes>
                  <Route path="/candidate/*" element={
                    <Link to="/" className="text-sm font-medium text-indigo-600 hover:text-indigo-500 border border-indigo-600 px-4 py-2 rounded-md">
                      Recruiter Dashboard
                    </Link>
                  } />
                  <Route path="*" element={
                    <Link to="/candidate" className="text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-md shadow-sm transition-all hover:scale-105 active:scale-95">
                      Candidate Portal
                    </Link>
                  } />
                </Routes>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto py-8 sm:px-6 lg:px-8">
          <Routes>
            {/* Recruiter Routes */}
            <Route path="/" element={<Dashboard />} />
            <Route path="/create-outcome" element={<OutcomeCreate />} />
            <Route path="/dashboard/:outcomeId" element={<OutcomeDashboard />} />
            <Route path="/evaluation/:jobId" element={<EvaluationView />} />
            <Route path="/reviewer" element={<ReviewerQueue />} />
            <Route path="/learning" element={<FeedbackView />} />
            <Route path="/admin/audit" element={<AdminAudit />} />

            {/* Candidate Routes */}
            <Route path="/candidate" element={<CandidatePortal />} />
            <Route path="/candidate/jobs" element={<CandidateJobs />} />
            <Route path="/candidate/applications" element={<CandidateApplications />} />
            <Route path="/submit-proof/:outcomeId" element={<ProofSubmit />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
