import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Github, FileCode, Folder, CheckCircle } from 'lucide-react';
import { getOutcome, submitProof, getRepoPreview } from '../api';

export default function ProofSubmit() {
    const { outcomeId } = useParams();
    const [outcome, setOutcome] = useState(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    const [formData, setFormData] = useState({
        candidate_id: '',
        repo_url: '',
        context: ''
    });

    // Mock Live Preview State
    const [preview, setPreview] = useState(null);

    useEffect(() => {
        async function loadOutcome() {
            try {
                const data = await getOutcome(outcomeId);
                setOutcome(data);

                // Pre-fill candidate ID from URL if present
                const params = new URLSearchParams(window.location.search);
                const cid = params.get('candidateId');
                if (cid) {
                    setFormData(prev => ({ ...prev, candidate_id: cid }));
                }
            } catch (error) {
                console.error("Failed to load outcome", error);
            } finally {
                setLoading(false);
            }
        }
        loadOutcome();
    }, [outcomeId]);

    // Simulate fetching repo details when URL is entered
    // Fetch repo details when URL is entered
    useEffect(() => {
        const fetchPreview = async () => {
            if (formData.repo_url.includes('github.com')) {
                try {
                    const data = await getRepoPreview(formData.repo_url);
                    setPreview(data);
                } catch (error) {
                    console.error("Failed to fetch preview", error);
                    setPreview(null);
                }
            } else {
                setPreview(null);
            }
        };

        const timeoutId = setTimeout(fetchPreview, 1000); // Debounce 1s
        return () => clearTimeout(timeoutId);
    }, [formData.repo_url]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await submitProof({
                job_id: outcomeId,
                candidate_id: formData.candidate_id || `cand_${Math.random().toString(36).substr(2, 5)}`,
                type: 'github',
                payload: {
                    repo_url: formData.repo_url,
                    context: formData.context
                }
            });
            setSubmitted(true);
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading...</div>;
    if (!outcome) return <div className="p-8 text-center">Outcome not found.</div>;

    if (submitted) {
        return (
            <div className="max-w-2xl mx-auto mt-16 text-center">
                <div className="bg-green-100 rounded-full h-20 w-20 flex items-center justify-center mx-auto mb-6">
                    <CheckCircle className="h-10 w-10 text-green-600" />
                </div>
                <h2 className="text-3xl font-bold text-gray-900 mb-4">Proof Submitted</h2>
                <p className="text-gray-600">
                    Your work has been received and is being processed by SignalLayer.
                    You will be notified if you are selected for an interview.
                </p>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto py-12 px-4">
            <div className="bg-white shadow-xl rounded-2xl overflow-hidden border border-gray-100">
                <div className="bg-indigo-600 px-8 py-10 text-white">
                    <h1 className="text-3xl font-bold">{outcome.title}</h1>
                    <p className="mt-2 text-indigo-100 opacity-90">{outcome.description}</p>
                </div>

                <div className="p-8">
                    <div className="mb-8 p-4 bg-yellow-50 rounded-lg border border-yellow-100 text-yellow-800 text-sm">
                        <strong>Instruction:</strong> Submit proof of work relevant to this outcome.
                        We evaluate code, not resumes.
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-8">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Candidate ID / Email</label>
                            <input
                                type="text"
                                required
                                placeholder="e.g. jane.doe@example.com"
                                value={formData.candidate_id}
                                onChange={(e) => setFormData({ ...formData, candidate_id: e.target.value })}
                                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3 border"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">GitHub Repository URL <span className="text-red-500">*</span></label>
                            <div className="mt-1 flex rounded-md shadow-sm">
                                <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-500 sm:text-sm">
                                    <Github className="h-4 w-4" />
                                </span>
                                <input
                                    type="url"
                                    required
                                    placeholder="https://github.com/username/repo"
                                    value={formData.repo_url}
                                    onChange={(e) => setFormData({ ...formData, repo_url: e.target.value })}
                                    className="flex-1 min-w-0 block w-full px-3 py-3 rounded-none rounded-r-md focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm border-gray-300 border"
                                />
                            </div>
                        </div>

                        {preview && (
                            <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 animate-fade-in">
                                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Live Preview</h4>
                                <div className="flex items-center gap-3 mb-3">
                                    <Folder className="h-5 w-5 text-indigo-500" />
                                    <span className="font-medium text-gray-900">{preview.name}</span>
                                </div>
                                <div className="space-y-1 pl-8 border-l-2 border-gray-200 ml-2.5">
                                    {preview.files.map((file, i) => (
                                        <div key={i} className="flex items-center gap-2 text-sm text-gray-600">
                                            <FileCode className="h-3 w-3 text-gray-400" />
                                            {file}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Additional Context (Optional)</label>
                            <textarea
                                rows={3}
                                placeholder="Any specific notes about your implementation..."
                                value={formData.context}
                                onChange={(e) => setFormData({ ...formData, context: e.target.value })}
                                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3 border"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                        >
                            {submitting ? 'Submitting Proof...' : 'Submit Proof'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
