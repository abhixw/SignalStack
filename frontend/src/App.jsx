import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import OutcomeCreate from './pages/OutcomeCreate';
import ProofSubmit from './pages/ProofSubmit';
import EvaluationView from './pages/EvaluationView';
import ReviewerQueue from './pages/ReviewerQueue';
import OutcomeDashboard from './pages/OutcomeDashboard';
import FeedbackView from './pages/FeedbackView';
import AdminAudit from './pages/AdminAudit';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
        <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600">
                    SignalLayer
                  </span>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link to="/" className="border-indigo-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                    Outcomes
                  </Link>
                  <Link to="/reviewer" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                    Review Queue
                  </Link>
                  <Link to="/learning" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                    System Learning
                  </Link>
                  <Link to="/admin/audit" className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                    Audit Logs
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/create-outcome" element={<OutcomeCreate />} />
            <Route path="/dashboard/:outcomeId" element={<OutcomeDashboard />} />
            <Route path="/submit-proof/:outcomeId" element={<ProofSubmit />} />
            <Route path="/evaluation/:jobId" element={<EvaluationView />} />
            <Route path="/reviewer" element={<ReviewerQueue />} />
            <Route path="/learning" element={<FeedbackView />} />
            <Route path="/admin/audit" element={<AdminAudit />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
