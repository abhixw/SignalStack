import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, User, ThumbsUp, ThumbsDown, CheckCircle, Sparkles } from 'lucide-react';
import { getEvaluation, setCandidateDecision, suggestCandidateFeedback } from '../api';

const DECISION_LABELS = {
    advancing: 'Advancing to Interview',
    rejected: 'Rejected',
};

export default function CandidateDecision() {
    const { outcomeId, candidateEmail: encodedEmail } = useParams();
    const candidateEmail = decodeURIComponent(encodedEmail);
    const navigate = useNavigate();

    const [evaluation, setEvaluation] = useState(null);
    const [loading, setLoading] = useState(true);
    const [deciding, setDeciding] = useState(false);
    const [error, setError] = useState('');
    const [feedback, setFeedback] = useState('');
    const [generating, setGenerating] = useState(null); // null | 'advancing' | 'rejected'

    useEffect(() => {
        getEvaluation(outcomeId)
            .then(setEvaluation)
            .catch((err) => setError(err.message || 'Could not load this evaluation.'))
            .finally(() => setLoading(false));
    }, [outcomeId]);

    const handleGenerate = async (decision) => {
        setGenerating(decision);
        try {
            const result = await suggestCandidateFeedback(outcomeId, candidateEmail, decision);
            setFeedback(result.feedback);
        } catch (err) {
            setError(err.message || 'Could not generate feedback.');
        } finally {
            setGenerating(null);
        }
    };

    const handleDecision = async (decision) => {
        setDeciding(true);
        try {
            await setCandidateDecision(outcomeId, candidateEmail, decision, feedback.trim());
            navigate(`/dashboard/${outcomeId}`);
        } catch (err) {
            setError(err.message || 'Could not record decision.');
            setDeciding(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading...</div>;
    if (error) return <div className="p-8 text-center text-red-600">{error}</div>;
    if (!evaluation) return <div className="p-8 text-center">Evaluation not found.</div>;

    const existingDecision = evaluation.candidate_decisions?.[candidateEmail];

    // Already decided — the recruiter can't reopen this candidate's scoring
    // detail; it's a done deal, same as the roster shows.
    if (existingDecision) {
        return (
            <div className="max-w-lg mx-auto mt-16 text-center bg-white p-8 rounded-2xl shadow-xl border border-gray-100">
                <CheckCircle className="mx-auto h-12 w-12 text-green-500 mb-4" />
                <h2 className="text-xl font-bold text-gray-900 mb-2">Already decided</h2>
                <p className="text-gray-500 mb-6">
                    You marked <span className="font-medium">{candidateEmail}</span> as{' '}
                    <span className="font-semibold">{DECISION_LABELS[existingDecision] || existingDecision}</span>. This can't be reopened.
                </p>
                <Link to={`/dashboard/${outcomeId}`} className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                    Back to candidates
                </Link>
            </div>
        );
    }

    const taskScores = evaluation.candidate_task_scores?.[candidateEmail] || [];
    const overallScore = evaluation.candidate_scores?.[candidateEmail] ?? 0;

    return (
        <div className="max-w-3xl mx-auto space-y-6 pb-12">
            <Link to={`/dashboard/${outcomeId}`} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700">
                <ArrowLeft className="h-4 w-4" /> Back to candidates
            </Link>

            <div className="bg-white shadow-sm rounded-xl p-8 border border-gray-100">
                <div className="flex items-center gap-4 mb-2">
                    <div className="h-12 w-12 rounded-full bg-indigo-100 flex items-center justify-center">
                        <User className="h-6 w-6 text-indigo-600" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">{candidateEmail}</h1>
                    </div>
                    <div className="ml-auto text-right">
                        <div className="text-xs text-gray-500 uppercase font-semibold">Match Score</div>
                        <div className="text-3xl font-bold text-indigo-600">{Math.round(overallScore * 100)}%</div>
                    </div>
                </div>
            </div>

            <div className="bg-white shadow-sm rounded-xl border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                    <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wide">Task-by-Task Scores</h2>
                </div>
                <ul className="divide-y divide-gray-200">
                    {taskScores.map((ts) => {
                        const pct = Math.round(ts.score * 100);
                        const tone = pct >= 66 ? 'bg-green-100 text-green-800' : pct >= 33 ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-600';
                        return (
                            <li key={ts.task_id} className="px-6 py-4 flex items-center justify-between gap-4">
                                <div>
                                    <p className="text-sm font-medium text-gray-900">{ts.task_title}</p>
                                    <p className="text-xs text-gray-500 mt-0.5">{ts.reasons.join('; ')}</p>
                                </div>
                                <span className={`shrink-0 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${tone}`}>
                                    {pct}%
                                </span>
                            </li>
                        );
                    })}
                </ul>
            </div>

            <div className="bg-white shadow-sm rounded-xl p-6 border border-gray-100">
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide mb-1">Feedback to candidate (optional)</h3>
                <p className="text-xs text-gray-500 mb-3">
                    Generate a draft from the task scores above, then edit it — or write your own from scratch. Sent to the candidate alongside your decision below.
                </p>
                <div className="flex gap-2 mb-3">
                    <button
                        type="button"
                        onClick={() => handleGenerate('advancing')}
                        disabled={generating !== null}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50"
                    >
                        <Sparkles className="w-3.5 h-3.5" />
                        {generating === 'advancing' ? 'Drafting...' : 'Draft (advancing)'}
                    </button>
                    <button
                        type="button"
                        onClick={() => handleGenerate('rejected')}
                        disabled={generating !== null}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50"
                    >
                        <Sparkles className="w-3.5 h-3.5" />
                        {generating === 'rejected' ? 'Drafting...' : 'Draft (rejected)'}
                    </button>
                </div>
                <textarea
                    rows={4}
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="Write feedback for the candidate, or generate a draft above..."
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3 border"
                />
            </div>

            <div className="bg-white shadow-sm rounded-xl p-6 border border-gray-100">
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide mb-4">Decision</h3>
                <p className="text-xs text-gray-500 mb-4">This is final — once you decide, you can't reopen this candidate.</p>
                <div className="flex gap-3">
                    <button
                        onClick={() => handleDecision('advancing')}
                        disabled={deciding}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-md text-sm font-semibold text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                    >
                        <ThumbsUp className="w-4 h-4" /> Advance to Interview
                    </button>
                    <button
                        onClick={() => handleDecision('rejected')}
                        disabled={deciding}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-md text-sm font-semibold text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
                    >
                        <ThumbsDown className="w-4 h-4" /> Reject
                    </button>
                </div>
            </div>
        </div>
    );
}
