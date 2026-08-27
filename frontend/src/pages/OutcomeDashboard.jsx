import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { CheckCircle, Copy, Users, Eye, ThumbsUp, ThumbsDown, Clock, Github } from 'lucide-react';
import { triggerEvaluation, getOutcome, getProofs, getCandidateRoster } from '../api';

const DECISION_STYLES = {
    advancing: { label: 'Advancing to Interview', icon: ThumbsUp, className: 'bg-green-100 text-green-800' },
    rejected: { label: 'Rejected', icon: ThumbsDown, className: 'bg-red-100 text-red-800' },
};

export default function OutcomeDashboard() {
    const { outcomeId } = useParams();
    const navigate = useNavigate();
    const [outcome, setOutcome] = useState(null);
    const [roster, setRoster] = useState([]);
    const [loading, setLoading] = useState(true);
    const [scoring, setScoring] = useState(false);
    const [copied, setCopied] = useState(false);

    const load = useCallback(async () => {
        const [outcomeData, proofsData, rosterData] = await Promise.all([
            getOutcome(outcomeId),
            getProofs(outcomeId),
            getCandidateRoster(outcomeId),
        ]);
        setOutcome(outcomeData);
        setRoster(rosterData);

        // No manual "run evaluation" step — score anyone who applied and
        // isn't scored yet, transparently, so the roster is always current.
        const needsScoring = proofsData.length > 0 && rosterData.some((r) => !r.has_score);
        if (needsScoring) {
            setScoring(true);
            try {
                await triggerEvaluation({
                    request_id: Math.random().toString(36).substring(7),
                    outcome: outcomeData,
                    proofs: proofsData,
                    options: { anonymize: false },
                });
                setRoster(await getCandidateRoster(outcomeId));
            } catch (error) {
                console.error("Scoring failed", error);
            } finally {
                setScoring(false);
            }
        }
        return proofsData;
    }, [outcomeId]);

    useEffect(() => {
        load().finally(() => setLoading(false));
    }, [load]);

    const candidateLink = `${window.location.origin}/submit-proof/${outcomeId}`;

    const handleCopyLink = () => {
        navigator.clipboard.writeText(candidateLink);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (loading) return <div className="p-8 text-center">Loading dashboard...</div>;
    if (!outcome) return <div className="p-8 text-center">Outcome not found.</div>;

    return (
        <div className="max-w-5xl mx-auto space-y-8">
            {/* Header */}
            <div className="bg-white shadow-sm rounded-xl p-8 border border-gray-100">
                <h1 className="text-3xl font-bold text-gray-900">{outcome.title}</h1>
                <p className="text-gray-500 mt-1">{outcome.description}</p>
                <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                    <span className="flex items-center gap-1"><CheckCircle className="w-4 h-4" /> {outcome.tasks.length} Tasks</span>
                    <span className="flex items-center gap-1"><Users className="w-4 h-4" /> {roster.length} Candidates</span>
                </div>
            </div>

            {/* Candidate Roster */}
            <div className="bg-white shadow-sm rounded-xl border border-gray-100 overflow-hidden">
                <div className="px-8 py-5 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                    <h3 className="text-lg font-bold text-gray-900">Candidates ({roster.length})</h3>
                    {scoring && (
                        <span className="flex items-center gap-2 text-sm text-indigo-600">
                            <div className="animate-spin rounded-full h-4 w-4 border-2 border-indigo-500 border-t-transparent" />
                            Scoring...
                        </span>
                    )}
                </div>

                {roster.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-gray-500 text-sm mb-3">No candidates yet. Share the apply link above.</p>
                        <button onClick={handleCopyLink} className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-500">
                            <Copy className="w-4 h-4" /> Copy link
                        </button>
                    </div>
                ) : (
                    <ul className="divide-y divide-gray-200">
                        {roster.map((c) => {
                            const decisionStyle = c.decision ? DECISION_STYLES[c.decision] : null;
                            const DecisionIcon = decisionStyle?.icon;
                            return (
                                <li key={c.candidate_id} className="px-8 py-5 flex items-center justify-between gap-4">
                                    <div className="min-w-0">
                                        <p className="text-sm font-semibold text-gray-900 truncate">{c.full_name || c.candidate_id}</p>
                                        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
                                            <span className="truncate">{c.candidate_id}</span>
                                            {c.github_username && (
                                                <span className="flex items-center gap-1">
                                                    <Github className="w-3 h-3" /> @{c.github_username}
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {decisionStyle ? (
                                        <span className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${decisionStyle.className}`}>
                                            <DecisionIcon className="h-3.5 w-3.5" />
                                            {decisionStyle.label}
                                        </span>
                                    ) : c.has_score ? (
                                        <Link
                                            to={`/dashboard/${outcomeId}/candidate/${encodeURIComponent(c.candidate_id)}`}
                                            className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm"
                                        >
                                            <Eye className="w-4 h-4" /> View
                                        </Link>
                                    ) : (
                                        <span className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
                                            <Clock className="w-3.5 h-3.5" /> Scoring...
                                        </span>
                                    )}
                                </li>
                            );
                        })}
                    </ul>
                )}
            </div>
        </div>
    );
}
