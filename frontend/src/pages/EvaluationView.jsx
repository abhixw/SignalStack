import React, { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { CheckCircle, AlertTriangle, FileText, User, ArrowRight, XCircle, ThumbsUp, ThumbsDown } from 'lucide-react';
import { submitFeedback, getEvaluation } from '../api';

export default function EvaluationView() {
    const { jobId } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const [evaluation, setEvaluation] = useState(null);
    const [loading, setLoading] = useState(true);
    const [feedbackGiven, setFeedbackGiven] = useState(false);

    const anonymized = location.state?.anonymized || false;

    useEffect(() => {
        if (location.state?.result) {
            setEvaluation(location.state.result.evaluation);
            setLoading(false);
        } else {
            // Fetch from API if not passed in state
            getEvaluation(jobId)
                .then(data => {
                    if (data.status === 'pending') {
                        // Keep loading or show pending state
                        setLoading(true);
                        // Optional: Poll or show message
                    } else if (data.evaluation) {
                        setEvaluation(data.evaluation);
                        setLoading(false);
                    } else {
                        setLoading(false);
                    }
                })
                .catch(err => {
                    console.error("Failed to load evaluation", err);
                    setLoading(false);
                });
        }
    }, [location.state, jobId]);

    const handleAction = async (action) => {
        if (!evaluation) return;

        // Submit feedback/decision
        try {
            await submitFeedback({
                job_id: evaluation.job_id,
                evaluation_id: "eval_123", // Mock ID
                result: action === 'hire' ? 'success' : 'failure',
                metrics: { action_taken: action }
            });
            setFeedbackGiven(true);
            alert(`Action recorded: ${action.toUpperCase()}`);
        } catch (error) {
            console.error("Failed to submit feedback", error);
        }
    };

    if (loading) return (
        <div className="flex flex-col items-center justify-center min-h-[60vh]">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-indigo-500 border-t-transparent mb-4"></div>
            <h2 className="text-xl font-semibold text-gray-900">Evaluating Proofs...</h2>
            <p className="text-gray-500 mt-2">Extracting signals • Allocating tasks • Verifying constraints</p>
            <p className="text-xs text-gray-400 mt-4">This may take up to 30 seconds for deep analysis.</p>
        </div>
    );

    if (!evaluation) return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
            <AlertTriangle className="w-12 h-12 text-yellow-500 mb-4" />
            <h2 className="text-xl font-bold text-gray-900">Evaluation Not Ready</h2>
            <p className="text-gray-500 mt-2 max-w-md">The system is still processing the GitHub signals. Please wait a moment and refresh.</p>
            <button
                onClick={() => window.location.reload()}
                className="mt-6 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
            >
                Refresh Status
            </button>
        </div>
    );

    return (
        <div className="max-w-6xl mx-auto space-y-8 pb-12">
            <div className="bg-white shadow-sm rounded-xl p-8 border border-gray-100">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Evaluation Report</h1>
                        <p className="text-gray-500 mt-1 font-mono text-sm">Job ID: {evaluation.job_id}</p>
                    </div>
                    {evaluation.risk_flags.length > 0 && (
                        <div className="px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800 flex items-center gap-1">
                            <AlertTriangle className="w-4 h-4" /> {evaluation.risk_flags.length} Risks Detected
                        </div>
                    )}
                </div>

                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Candidate Leaderboard</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {Object.entries(evaluation.candidate_scores || {}).map(([candId, score]) => (
                        <div key={candId} className="bg-gray-50 rounded-lg p-4 border border-gray-100 flex flex-col items-center">
                            <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center mb-2">
                                <User className="h-5 w-5 text-indigo-600" />
                            </div>
                            <div className="text-sm font-medium text-gray-900 truncate w-full text-center">{candId}</div>
                            <div className="text-2xl font-bold text-indigo-600 mt-1">{(score * 100).toFixed(0)}%</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* B. Task Allocation Cards (CORE) */}
            <h2 className="text-xl font-bold text-gray-900">Task Allocation</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {evaluation.work_allocation.map((alloc) => (
                    <div key={alloc.task_id} className="bg-white shadow-sm rounded-xl p-6 border border-gray-100 flex flex-col hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-4">
                            <h3 className="text-lg font-bold text-gray-900 leading-tight">{alloc.task_title}</h3>
                            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-bold bg-indigo-50 text-indigo-700">
                                {(alloc.confidence * 100).toFixed(0)}% Match
                            </span>
                        </div>

                        <div className="flex items-center gap-3 mb-6 bg-gray-50 p-3 rounded-lg border border-gray-100">
                            <div className="bg-white p-2 rounded-full shadow-sm">
                                <User className="w-5 h-5 text-indigo-600" />
                            </div>
                            <div>
                                <p className="text-xs text-gray-500 uppercase font-semibold">Recommended</p>
                                <p className="font-medium text-gray-900">
                                    {anonymized ? `Candidate ${alloc.recommended_candidate.substring(0, 4)}...` : alloc.recommended_candidate}
                                </p>
                            </div>
                        </div>

                        <div className="flex-1 space-y-4">
                            <div>
                                <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Why this match?</h4>
                                <ul className="text-sm text-gray-700 space-y-1.5">
                                    {alloc.reasons.map((reason, idx) => (
                                        <li key={idx} className="flex items-start gap-2">
                                            <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                            <span className="leading-snug">{reason}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {alloc.evidence && alloc.evidence.length > 0 && (
                                <div>
                                    <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Evidence</h4>
                                    <div className="space-y-2">
                                        {alloc.evidence.map((ev, idx) => (
                                            <a
                                                key={idx}
                                                href={ev.source_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="block bg-gray-50 p-2.5 rounded border border-gray-200 text-xs hover:bg-indigo-50 hover:border-indigo-200 transition-colors group"
                                            >
                                                <div className="flex justify-between items-center mb-1 text-gray-500 font-mono">
                                                    <span>{ev.ref}</span>
                                                    <FileText className="w-3 h-3 group-hover:text-indigo-600" />
                                                </div>
                                                <div className="text-gray-800 font-mono line-clamp-2 border-l-2 border-gray-300 pl-2">
                                                    {ev.snippet}
                                                </div>
                                            </a>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* C. Signals Used */}
                <div className="lg:col-span-2 bg-white shadow-sm rounded-xl p-8 border border-gray-100">
                    <h3 className="text-lg font-bold text-gray-900 mb-4">System Signals</h3>
                    <div className="flex flex-wrap gap-2">
                        {evaluation.global_signals_used.map((signal) => (
                            <span key={signal} className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800 border border-gray-200">
                                {signal}
                            </span>
                        ))}
                    </div>
                    <p className="mt-4 text-sm text-gray-500">
                        The system analyzed these signals across all submitted proofs to determine the optimal work allocation.
                    </p>
                </div>

                {/* D. Human Actions (MANDATORY) */}
                <div className="bg-white shadow-sm rounded-xl p-8 border border-gray-100 flex flex-col justify-center">
                    <h3 className="text-lg font-bold text-gray-900 mb-6">Human Decision</h3>
                    {feedbackGiven ? (
                        <div className="text-center py-4">
                            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-2" />
                            <p className="font-medium text-gray-900">Decision Recorded</p>
                            <button onClick={() => navigate('/')} className="mt-4 text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                                Return to Dashboard
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            <button
                                onClick={() => handleAction('hire')}
                                className="w-full flex items-center justify-center px-4 py-3 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 shadow-sm"
                            >
                                <ThumbsUp className="w-4 h-4 mr-2" />
                                Advance to Interview
                            </button>
                            <button
                                onClick={() => handleAction('reject')}
                                className="w-full flex items-center justify-center px-4 py-3 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 shadow-sm"
                            >
                                <ThumbsDown className="w-4 h-4 mr-2" />
                                Mark as No Hire
                            </button>
                            <button
                                onClick={() => handleAction('more_proof')}
                                className="w-full flex items-center justify-center px-4 py-3 border border-transparent text-sm font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200"
                            >
                                Request More Proof
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
