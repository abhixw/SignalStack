import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Share2, Play, CheckCircle, Copy, Users } from 'lucide-react';
import { triggerEvaluation, getOutcome, getProofs } from '../api';

export default function OutcomeDashboard() {
    const { outcomeId } = useParams();
    const navigate = useNavigate();
    const [outcome, setOutcome] = useState(null);
    const [proofs, setProofs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [evaluating, setEvaluating] = useState(false);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        async function loadData() {
            try {
                const [outcomeData, proofsData] = await Promise.all([
                    getOutcome(outcomeId),
                    getProofs(outcomeId)
                ]);
                setOutcome(outcomeData);
                setProofs(proofsData);
            } catch (error) {
                console.error("Failed to load dashboard data", error);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, [outcomeId]);

    const candidateLink = `${window.location.origin}/submit-proof/${outcomeId}`;

    const handleCopyLink = () => {
        navigator.clipboard.writeText(candidateLink);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleEvaluate = async () => {
        setEvaluating(true);
        try {
            if (proofs.length === 0) {
                alert("No proofs submitted yet. Please submit proofs via the candidate link.");
                setEvaluating(false);
                return;
            }

            const payload = {
                request_id: Math.random().toString(36).substring(7),
                outcome: outcome,
                proofs: proofs,
                options: { anonymize: false }
            };

            const result = await triggerEvaluation(payload);
            navigate(`/evaluation/${result.job_id}`, { state: { result } });
        } catch (error) {
            console.error("Evaluation failed", error);
            alert("Evaluation failed. Ensure proofs have been submitted.");
        } finally {
            setEvaluating(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading dashboard...</div>;
    if (!outcome) return <div className="p-8 text-center">Outcome not found.</div>;

    return (
        <div className="max-w-5xl mx-auto space-y-8">
            {/* Header */}
            <div className="bg-white shadow-sm rounded-xl p-8 border border-gray-100 flex justify-between items-start">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">{outcome.title}</h1>
                    <p className="text-gray-500 mt-1">{outcome.description}</p>
                    <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                        <span className="flex items-center gap-1"><CheckCircle className="w-4 h-4" /> {outcome.tasks.length} Tasks</span>
                        <span className="flex items-center gap-1"><Users className="w-4 h-4" /> {proofs.length} Candidates</span>
                    </div>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={handleEvaluate}
                        disabled={evaluating || proofs.length === 0}
                        className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {evaluating ? 'Evaluating...' : (
                            <>
                                <Play className="w-5 h-5 mr-2" />
                                Run Evaluation
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Submitted Proofs List */}
            <div className="bg-white shadow-sm rounded-xl p-8 border border-gray-100">
                <h3 className="text-lg font-bold text-gray-900 mb-4">Submitted Proofs ({proofs.length})</h3>
                {proofs.length === 0 ? (
                    <div className="text-center py-8 bg-gray-50 rounded-lg border border-dashed border-gray-300">
                        <p className="text-gray-500 text-sm">No proofs submitted yet. Share the invite link above.</p>
                    </div>
                ) : (
                    <ul className="divide-y divide-gray-200">
                        {proofs.map((proof) => (
                            <li key={proof.candidate_id} className="py-4 flex justify-between items-center">
                                <div>
                                    <p className="text-sm font-medium text-gray-900">{proof.candidate_id}</p>
                                    <p className="text-xs text-gray-500 font-mono">{proof.type} • {new Date().toLocaleDateString()}</p>
                                </div>
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                    Ready
                                </span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}
