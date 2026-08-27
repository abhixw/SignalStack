import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Github, FileCode, Folder, CheckCircle, ShieldCheck, AlertTriangle, Code2 } from 'lucide-react';
import { getOutcome, submitProof, getRepoPreview, startGithubConnect, getCandidateApplications, getCodingProfiles, updateCodingProfiles } from '../api';
import { useAuth } from '../context/AuthContext';

// Optional — saved straight to the candidate's account (not tied to this
// specific application), so DSA-focused tasks on ANY outcome can score
// against it, same as the GitHub connection above. Pick one platform at a
// time; whichever one isn't touched here keeps whatever was saved before.
function CodingProfileSection() {
    const [platform, setPlatform] = useState('codeforces');
    const [handle, setHandle] = useState('');
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        getCodingProfiles()
            .then(setProfile)
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    const currentHandle = platform === 'codeforces' ? profile?.codeforces_handle : profile?.leetcode_username;

    const handleSave = async (e) => {
        e.preventDefault();
        if (!handle.trim()) return;
        setError('');
        setSaving(true);
        try {
            const data = await updateCodingProfiles(
                platform === 'codeforces' ? { codeforcesHandle: handle.trim() } : { leetcodeUsername: handle.trim() }
            );
            setProfile(data);
            setHandle('');
        } catch (err) {
            setError(err.message || 'Could not save this handle.');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return null;

    return (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-1">
                <Code2 className="h-4 w-4 text-indigo-600" />
                <h4 className="text-sm font-semibold text-gray-900">Coding platform profile (optional)</h4>
            </div>
            <p className="text-xs text-gray-500 mb-3">
                Link Codeforces or LeetCode so DSA-focused tasks — on this outcome or any other — can score against your real problem-solving activity. Self-reported; there's no ownership verification like there is for GitHub.
            </p>

            <div className="flex gap-2">
                <select
                    value={platform}
                    onChange={(e) => { setPlatform(e.target.value); setHandle(''); setError(''); }}
                    className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm py-2 px-2 border bg-white"
                >
                    <option value="codeforces">Codeforces</option>
                    <option value="leetcode">LeetCode</option>
                </select>
                <input
                    type="text"
                    placeholder={currentHandle || (platform === 'codeforces' ? 'Your Codeforces handle' : 'Your LeetCode username')}
                    value={handle}
                    onChange={(e) => setHandle(e.target.value)}
                    className="flex-1 min-w-0 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm py-2 px-3 border"
                />
                <button
                    type="button"
                    onClick={handleSave}
                    disabled={saving || !handle.trim()}
                    className="px-4 py-2 rounded-md text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                >
                    {saving ? 'Saving...' : 'Save'}
                </button>
            </div>

            {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

            {currentHandle && (
                <p className="mt-2 text-xs text-green-700">
                    Connected as <strong>{currentHandle}</strong> on {platform === 'codeforces' ? 'Codeforces' : 'LeetCode'}.
                    {platform === 'leetcode' && profile?.leetcode_fetch_failed && ' (Couldn\'t fetch stats just now — this platform has no official API, try saving again shortly.)'}
                </p>
            )}
        </div>
    );
}

// Extracts the owner from a github.com/{owner}/{repo} URL — mirrors the
// backend's ownership check (app/routes/signal_extractor.py) so the candidate
// gets an inline warning before submitting, not just a 403 after.
function repoOwnerFromUrl(url) {
    try {
        const parsed = new URL(url.includes('://') ? url : `https://${url}`);
        if (!/(^|\.)github\.com$/.test(parsed.hostname)) return null;
        const parts = parsed.pathname.split('/').filter(Boolean);
        return parts.length >= 2 ? parts[0] : null;
    } catch {
        return null;
    }
}

export default function ProofSubmit() {
    const { outcomeId } = useParams();
    const { user } = useAuth();
    const [outcome, setOutcome] = useState(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [connecting, setConnecting] = useState(false);
    const [alreadyApplied, setAlreadyApplied] = useState(false);

    const [formData, setFormData] = useState({
        repo_url: '',
        context: ''
    });

    // Mock Live Preview State
    const [preview, setPreview] = useState(null);

    useEffect(() => {
        async function loadOutcome() {
            try {
                const [data, applications] = await Promise.all([
                    getOutcome(outcomeId),
                    getCandidateApplications().catch(() => []),
                ]);
                setOutcome(data);
                setAlreadyApplied(applications.some((a) => a.job_id === outcomeId));
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
                // The server derives the real candidate identity from the JWT and
                // ignores this field; it's kept only because the schema requires it.
                candidate_id: 'ignored-derived-from-auth',
                type: 'github',
                payload: {
                    repo_url: formData.repo_url,
                    context: formData.context
                }
            });
            setSubmitted(true);
        } catch (error) {
            if (error.status === 409) {
                setAlreadyApplied(true);
            } else {
                alert(`Error: ${error.message}`);
            }
        } finally {
            setSubmitting(false);
        }
    };

    const handleConnectGithub = async () => {
        setConnecting(true);
        try {
            await startGithubConnect(`/submit-proof/${outcomeId}`);
            // startGithubConnect navigates the browser away on success — this
            // component unmounts, so there's no need to reset `connecting` here.
        } catch (error) {
            alert(`Could not start GitHub connection: ${error.message}`);
            setConnecting(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading...</div>;
    if (!outcome) return <div className="p-8 text-center">Outcome not found.</div>;

    if (!user?.github_username) {
        return (
            <div className="max-w-md mx-auto mt-16 text-center bg-white p-8 rounded-2xl shadow-xl border border-gray-100">
                <div className="mx-auto h-14 w-14 rounded-full bg-gray-900 flex items-center justify-center mb-6">
                    <Github className="h-7 w-7 text-white" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">Connect GitHub to apply</h2>
                <p className="text-sm text-gray-500 mb-6">
                    We only accept proof-of-work repos from a verified GitHub account, so we can confirm the work is actually yours.
                </p>
                <button
                    onClick={handleConnectGithub}
                    disabled={connecting}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 disabled:opacity-50"
                >
                    <Github className="h-4 w-4" />
                    {connecting ? 'Redirecting to GitHub...' : 'Connect GitHub'}
                </button>
            </div>
        );
    }

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

    if (alreadyApplied) {
        return (
            <div className="max-w-2xl mx-auto mt-16 text-center">
                <div className="bg-green-100 rounded-full h-20 w-20 flex items-center justify-center mx-auto mb-6">
                    <CheckCircle className="h-10 w-10 text-green-600" />
                </div>
                <h2 className="text-3xl font-bold text-gray-900 mb-4">Already Applied</h2>
                <p className="text-gray-600 mb-6">
                    You've already submitted a proof for <span className="font-medium">{outcome.title}</span>. Only one application per outcome is allowed.
                </p>
                <Link
                    to="/candidate/applications"
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                >
                    View My Applications
                </Link>
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
                    <div className="mb-6 flex items-center gap-2 p-3 rounded-lg border border-green-100 bg-green-50 text-green-800 text-sm">
                        <ShieldCheck className="h-4 w-4 flex-shrink-0" />
                        Verified as <span className="font-semibold">@{user.github_username}</span> on GitHub
                    </div>

                    <div className="mb-8 p-4 bg-yellow-50 rounded-lg border border-yellow-100 text-yellow-800 text-sm">
                        <strong>Instruction:</strong> Submit proof of work relevant to this outcome.
                        We evaluate code, not resumes.
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-8">
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
                            {formData.repo_url && repoOwnerFromUrl(formData.repo_url) &&
                                repoOwnerFromUrl(formData.repo_url).toLowerCase() !== user.github_username.toLowerCase() && (
                                <p className="mt-2 flex items-center gap-1.5 text-xs text-red-600">
                                    <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
                                    This repo belongs to "{repoOwnerFromUrl(formData.repo_url)}", not your verified account (@{user.github_username}) — submission will be rejected.
                                </p>
                            )}
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

                        <CodingProfileSection />

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
