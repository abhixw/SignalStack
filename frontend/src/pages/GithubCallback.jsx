import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Github, AlertTriangle, ShieldCheck, Mail } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { confirmGithubEmail, verifyGithubOtp } from '../api';

const ERROR_MESSAGES = {
    github_oauth_failed: "GitHub sign-in didn't complete. Please try again.",
    github_already_linked: 'That GitHub account is already connected to a different Recruvoskill account.',
    email_already_registered: "An account already exists with your GitHub account's email. Sign in with your password instead, then use \"Connect GitHub\" from there.",
    github_email_required: "We couldn't get a usable email from your GitHub account. Make sure you have a verified email on GitHub, then try again.",
    github_login_candidates_only: 'GitHub sign-in is only available for candidate accounts. Sign in with your email and password instead.',
    github_username_mismatch: "The GitHub account you authorized doesn't match the username you entered on the sign-up form. Please start over and use the account that's really yours.",
};

const FLOW_EMAIL_COPY = {
    login: "To confirm it's really you — not just anyone using an already-signed-in browser — type the email and username connected to your GitHub account.",
    signup: 'Type the email and username connected to your GitHub account. We\'ll send a code there to finish creating your account.',
    connect: "Type the email on YOUR Recruvoskill account (not necessarily your GitHub email) and the GitHub username you're connecting — this confirms you're really the one connecting this GitHub account.",
    register_verify: "Type the email you signed up with and the GitHub username you're verifying — this confirms it's really you completing your own sign-up.",
};

const FLOW_OTP_COPY = {
    login: "We've sent a code to that email. Enter it below.",
    signup: "We've sent a code to that email. Enter it below to finish creating your account.",
    connect: "We've sent a code to that email. Enter it below to finish connecting GitHub.",
    register_verify: "We've sent a code to that email. Enter it below to finish creating your account.",
};

export default function GithubCallback() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { loginWithToken, refreshUser } = useAuth();

    const [stage, setStage] = useState('email'); // 'email' | 'otp' | 'error'
    const [error, setError] = useState(null);
    const [email, setEmail] = useState('');
    const [username, setUsername] = useState('');
    const [emailError, setEmailError] = useState('');
    const [otp, setOtp] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [otpError, setOtpError] = useState('');

    const pendingToken = searchParams.get('pending');
    const flow = searchParams.get('flow') || 'login';
    const returnTo = searchParams.get('return_to');
    const errorCode = searchParams.get('error');

    useEffect(() => {
        if (errorCode) {
            setError(ERROR_MESSAGES[errorCode] || 'Something went wrong connecting to GitHub.');
            setStage('error');
        } else if (!pendingToken) {
            setError('Missing GitHub response. Please try again.');
            setStage('error');
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleConfirmEmail = async (e) => {
        e.preventDefault();
        setEmailError('');
        setSubmitting(true);
        try {
            await confirmGithubEmail({ pendingToken, email, githubUsername: username });
            setStage('otp');
        } catch (err) {
            setEmailError(err.message || "That doesn't match the email and username connected to your GitHub account.");
        } finally {
            setSubmitting(false);
        }
    };

    const handleVerify = async (e) => {
        e.preventDefault();
        setOtpError('');
        setSubmitting(true);
        try {
            const result = await verifyGithubOtp({ pendingToken, otp });
            if (result.access_token) {
                await loginWithToken(result.access_token);
            } else if (result.connected) {
                await refreshUser();
            }
            navigate(returnTo || '/post-login', { replace: true });
        } catch (err) {
            setOtpError(err.message || 'Invalid or expired code.');
        } finally {
            setSubmitting(false);
        }
    };

    if (stage === 'error') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
                <div className="max-w-md w-full bg-white p-8 rounded-xl shadow-lg border border-gray-100 text-center">
                    <div className="mx-auto h-12 w-12 rounded-full bg-red-100 flex items-center justify-center mb-4">
                        <AlertTriangle className="h-6 w-6 text-red-600" />
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2">GitHub connection failed</h2>
                    <p className="text-sm text-gray-600 mb-6">{error}</p>
                    <button
                        onClick={() => navigate('/login')}
                        className="w-full py-3 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700"
                    >
                        Back to sign in
                    </button>
                </div>
            </div>
        );
    }

    if (stage === 'email') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
                <div className="max-w-md w-full bg-white p-8 rounded-xl shadow-lg border border-gray-100">
                    <div className="mx-auto h-12 w-12 rounded-full bg-gray-900 flex items-center justify-center mb-4">
                        <Mail className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2 text-center">Confirm your email</h2>
                    <p className="text-sm text-gray-500 mb-6 text-center">{FLOW_EMAIL_COPY[flow] || FLOW_EMAIL_COPY.login}</p>

                    <form onSubmit={handleConfirmEmail} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-900 mb-1.5">Email</label>
                            <input
                                type="email"
                                required
                                autoFocus
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-900 mb-1.5">GitHub username</label>
                            <input
                                type="text"
                                required
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                            />
                        </div>

                        {emailError && (
                            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-700">{emailError}</div>
                        )}

                        <button
                            type="submit"
                            disabled={submitting || !email || !username}
                            className="w-full flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                        >
                            <Mail className="h-4 w-4" />
                            {submitting ? 'Checking...' : 'Send code'}
                        </button>

                        <button
                            type="button"
                            onClick={() => navigate('/login')}
                            className="w-full text-center text-sm text-gray-500 hover:text-gray-700"
                        >
                            Cancel
                        </button>
                    </form>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
            <div className="max-w-md w-full bg-white p-8 rounded-xl shadow-lg border border-gray-100">
                <div className="mx-auto h-12 w-12 rounded-full bg-gray-900 flex items-center justify-center mb-4">
                    <Github className="h-6 w-6 text-white" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2 text-center">Enter your code</h2>
                <p className="text-sm text-gray-500 mb-6 text-center">{FLOW_OTP_COPY[flow] || FLOW_OTP_COPY.login}</p>

                <form onSubmit={handleVerify} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-900 mb-1.5">6-digit code</label>
                        <input
                            type="text"
                            required
                            inputMode="numeric"
                            pattern="[0-9]{6}"
                            maxLength={6}
                            autoFocus
                            value={otp}
                            onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm tracking-[0.5em] text-center shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                        />
                    </div>

                    {otpError && (
                        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-700">{otpError}</div>
                    )}

                    <button
                        type="submit"
                        disabled={submitting || otp.length !== 6}
                        className="w-full flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                    >
                        <ShieldCheck className="h-4 w-4" />
                        {submitting ? 'Verifying...' : 'Verify'}
                    </button>

                    <button
                        type="button"
                        onClick={() => navigate('/login')}
                        className="w-full text-center text-sm text-gray-500 hover:text-gray-700"
                    >
                        Cancel
                    </button>
                </form>
            </div>
        </div>
    );
}
