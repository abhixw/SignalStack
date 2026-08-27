import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Github, ShieldCheck, BarChart3, ArrowLeft, Briefcase, UserRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { forgotPassword, resetPassword, getGithubLoginUrl, registerCandidateStart } from '../api';

function GithubContinueButton() {
    return (
        <a
            href={getGithubLoginUrl()}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 shadow-sm transition-colors"
        >
            <Github className="h-4 w-4" />
            Continue with GitHub
        </a>
    );
}

const FEATURES = [
    {
        icon: Github,
        title: 'Proof over resumes',
        description: 'Candidates submit a real GitHub repo, not a PDF.',
    },
    {
        icon: ShieldCheck,
        title: 'Role-based access',
        description: 'Candidates see their own applications; recruiters see only outcomes they own.',
    },
    {
        icon: BarChart3,
        title: 'Transparent scoring',
        description: 'Every score comes with the extracted signals behind it.',
    },
];

function SignInForm({ onSuccess, onForgotPassword }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const { login } = useAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSubmitting(true);
        try {
            await login(email, password);
            onSuccess();
        } catch (err) {
            setError(err.message || 'Login failed');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-5">
            <div>
                <label className="block text-sm font-medium text-gray-900 mb-1.5">Email</label>
                <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                />
            </div>
            <div>
                <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-sm font-medium text-gray-900">Password</label>
                    <button
                        type="button"
                        onClick={onForgotPassword}
                        className="text-xs font-medium text-indigo-600 hover:text-indigo-500"
                    >
                        Forgot password?
                    </button>
                </div>
                <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                />
            </div>

            {error && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-700">{error}</div>
            )}

            <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-colors disabled:opacity-50"
            >
                {submitting ? 'Signing in...' : 'Sign in'}
            </button>
        </form>
    );
}

function SignUpForm({ onSuccess, role }) {
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [githubUsername, setGithubUsername] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const { register } = useAuth();
    const isCandidate = role === 'candidate';

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSubmitting(true);
        try {
            if (isCandidate) {
                // Doesn't create the account directly — stashes these details
                // and sends the browser to GitHub to prove the claimed
                // username is real and belongs to whoever's signing up. The
                // account is only created after that + an email/OTP check on
                // the /auth/github/complete screen.
                await registerCandidateStart({ email, password, fullName, githubUsername });
            } else {
                await register({ email, password, fullName, role });
                onSuccess();
            }
        } catch (err) {
            setError(err.message || 'Registration failed');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-5">
            <div>
                <label className="block text-sm font-medium text-gray-900 mb-1.5">Full name</label>
                <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                />
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-900 mb-1.5">Email</label>
                <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                />
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-900 mb-1.5">Password</label>
                <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                />
                <p className="mt-1.5 text-xs text-gray-500">At least 8 characters.</p>
            </div>

            {isCandidate && (
                <div>
                    <label className="block text-sm font-medium text-gray-900 mb-1.5">GitHub username</label>
                    <input
                        type="text"
                        required
                        value={githubUsername}
                        onChange={(e) => setGithubUsername(e.target.value)}
                        className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                    />
                    <p className="mt-1.5 text-xs text-gray-500">
                        We'll send you to GitHub next to confirm this is really your account.
                    </p>
                </div>
            )}

            {error && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-700">{error}</div>
            )}

            <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-colors disabled:opacity-50"
            >
                {submitting
                    ? (isCandidate ? 'Redirecting to GitHub...' : 'Creating account...')
                    : (isCandidate ? 'Continue to GitHub' : 'Create account')}
            </button>
        </form>
    );
}

function ForgotPasswordForm({ onDone, onBackToSignIn }) {
    const [step, setStep] = useState('request'); // 'request' | 'reset'
    const [email, setEmail] = useState('');
    const [otp, setOtp] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [info, setInfo] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const handleRequestCode = async (e) => {
        e.preventDefault();
        setError('');
        setSubmitting(true);
        try {
            const res = await forgotPassword(email);
            setInfo(res.message);
            setStep('reset');
        } catch (err) {
            setError(err.message || 'Could not send reset code');
        } finally {
            setSubmitting(false);
        }
    };

    const handleResetPassword = async (e) => {
        e.preventDefault();
        setError('');
        setSubmitting(true);
        try {
            await resetPassword({ email, otp, newPassword });
            onDone();
        } catch (err) {
            setError(err.message || 'Could not reset password');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div>
            <button
                type="button"
                onClick={onBackToSignIn}
                className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6"
            >
                <ArrowLeft className="h-4 w-4" />
                Back to sign in
            </button>

            {step === 'request' ? (
                <form onSubmit={handleRequestCode} className="space-y-5">
                    <div>
                        <h2 className="font-serif text-2xl text-gray-900">Reset your password</h2>
                        <p className="mt-2 text-sm text-gray-500">We'll email you a 6-digit code.</p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-900 mb-1.5">Email</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                        />
                    </div>

                    {error && (
                        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-700">{error}</div>
                    )}

                    <button
                        type="submit"
                        disabled={submitting}
                        className="w-full py-3 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-colors disabled:opacity-50"
                    >
                        {submitting ? 'Sending code...' : 'Send reset code'}
                    </button>
                </form>
            ) : (
                <form onSubmit={handleResetPassword} className="space-y-5">
                    <div>
                        <h2 className="font-serif text-2xl text-gray-900">Enter your code</h2>
                        <p className="mt-2 text-sm text-gray-500">{info || `We sent a code to ${email}.`}</p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-900 mb-1.5">6-digit code</label>
                        <input
                            type="text"
                            required
                            inputMode="numeric"
                            pattern="[0-9]{6}"
                            maxLength={6}
                            value={otp}
                            onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm tracking-[0.5em] shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-900 mb-1.5">New password</label>
                        <input
                            type="password"
                            required
                            minLength={8}
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                        />
                        <p className="mt-1.5 text-xs text-gray-500">At least 8 characters.</p>
                    </div>

                    {error && (
                        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-700">{error}</div>
                    )}

                    <button
                        type="submit"
                        disabled={submitting}
                        className="w-full py-3 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-colors disabled:opacity-50"
                    >
                        {submitting ? 'Resetting...' : 'Reset password'}
                    </button>

                    <button
                        type="button"
                        onClick={() => setStep('request')}
                        className="w-full text-center text-sm text-indigo-600 hover:text-indigo-500"
                    >
                        Didn't get a code? Try again
                    </button>
                </form>
            )}
        </div>
    );
}

function RoleSelect({ onSelect }) {
    return (
        <div>
            <h2 className="font-serif text-3xl text-gray-900">Welcome to SignaXAI</h2>
            <p className="mt-2 text-sm text-gray-500 mb-8">Are you hiring, or applying?</p>

            <div className="space-y-4">
                <button
                    type="button"
                    onClick={() => onSelect('candidate')}
                    className="w-full flex items-center gap-4 p-5 rounded-xl border border-gray-200 bg-white hover:border-indigo-500 hover:shadow-md transition-all text-left"
                >
                    <div className="h-11 w-11 shrink-0 rounded-lg bg-indigo-50 flex items-center justify-center">
                        <UserRound className="h-5 w-5 text-indigo-600" />
                    </div>
                    <div>
                        <div className="font-semibold text-gray-900">I'm a Candidate</div>
                        <div className="text-sm text-gray-500">Apply to outcomes with a GitHub repo as proof of work.</div>
                    </div>
                </button>

                <button
                    type="button"
                    onClick={() => onSelect('recruiter')}
                    className="w-full flex items-center gap-4 p-5 rounded-xl border border-gray-200 bg-white hover:border-indigo-500 hover:shadow-md transition-all text-left"
                >
                    <div className="h-11 w-11 shrink-0 rounded-lg bg-indigo-50 flex items-center justify-center">
                        <Briefcase className="h-5 w-5 text-indigo-600" />
                    </div>
                    <div>
                        <div className="font-semibold text-gray-900">I'm a Recruiter</div>
                        <div className="text-sm text-gray-500">Define outcomes and evaluate candidates.</div>
                    </div>
                </button>
            </div>
        </div>
    );
}

export default function AuthPage({ initialTab = 'signin' }) {
    const [tab, setTab] = useState(initialTab);
    const [role, setRole] = useState(null); // null | 'candidate' | 'recruiter' — chosen before signin/signup ever render
    const navigate = useNavigate();

    const goToTab = (nextTab) => {
        // Deliberately NOT navigating to /login or /register here — those are
        // separate <Route>s, each rendering its own <AuthPage> instance, so
        // switching via navigate() would remount this component and reset
        // `role` back to null mid-flow. Tab switching stays client-side state;
        // the URL only matters for how you *arrive* here (initialTab).
        setTab(nextTab);
    };

    const onAuthSuccess = () => {
        // Always resolve through role: honoring a stale `location.state.from`
        // here could send a candidate back to a recruiter-only page they were
        // bounced off of before logging in, which then rejects them again.
        navigate('/post-login', { replace: true });
    };

    return (
        <div className="min-h-screen grid lg:grid-cols-2">
            {/* Left — branding panel */}
            <div className="hidden lg:flex flex-col justify-between p-12 text-white relative overflow-hidden bg-gradient-to-br from-[#0b0f2e] via-[#141a44] to-[#1c1052]">
                <div className="absolute inset-0 opacity-20 pointer-events-none" style={{
                    backgroundImage: 'radial-gradient(circle at 20% 20%, rgba(129,140,248,0.4), transparent 40%), radial-gradient(circle at 80% 70%, rgba(168,85,247,0.35), transparent 45%)',
                }} />

                <div className="relative">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-lg shadow-lg">
                            S
                        </div>
                        <span className="text-xl font-bold tracking-tight">SignaXAI</span>
                    </div>

                    <div className="mt-10 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-xs font-medium text-indigo-100">
                        <Sparkles className="h-3.5 w-3.5" />
                        AI-Native Hiring Platform
                    </div>

                    <h1 className="mt-6 font-serif text-4xl xl:text-5xl leading-tight text-white">
                        Hire on proof,<br />not promises.
                    </h1>

                    <p className="mt-5 max-w-md text-indigo-100/80 leading-relaxed">
                        SignaXAI evaluates real GitHub work — tests, CI/CD, architecture — and shows the evidence behind every score.
                    </p>
                </div>

                <div className="relative space-y-6">
                    {FEATURES.map(({ icon: Icon, title, description }) => (
                        <div key={title} className="flex items-start gap-4">
                            <div className="h-10 w-10 shrink-0 rounded-lg bg-white/10 border border-white/10 flex items-center justify-center">
                                <Icon className="h-5 w-5 text-indigo-200" />
                            </div>
                            <div>
                                <div className="font-semibold text-white">{title}</div>
                                <div className="text-sm text-indigo-100/70">{description}</div>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="relative text-xs text-indigo-100/40">
                    SignaXAI &middot; outcome-based hiring
                </div>
            </div>

            {/* Right — auth form */}
            <div className="flex items-center justify-center p-6 sm:p-12 bg-slate-50">
                <div className="w-full max-w-md">
                    <div className="lg:hidden flex items-center gap-3 mb-8">
                        <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-sm">
                            S
                        </div>
                        <span className="text-lg font-bold tracking-tight text-gray-900">SignaXAI</span>
                    </div>

                    {!role ? (
                        <RoleSelect onSelect={setRole} />
                    ) : (
                        <>
                            {tab !== 'forgot' && (
                                <>
                                    <button
                                        type="button"
                                        onClick={() => setRole(null)}
                                        className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 mb-4"
                                    >
                                        <ArrowLeft className="h-3.5 w-3.5" />
                                        {role === 'candidate' ? 'Candidate' : 'Recruiter'} — change
                                    </button>

                                    <div className="flex rounded-xl bg-gray-100 p-1 mb-8">
                                        <button
                                            type="button"
                                            onClick={() => goToTab('signin')}
                                            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                                                tab === 'signin' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                                            }`}
                                        >
                                            Sign in
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => goToTab('signup')}
                                            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                                                tab === 'signup' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                                            }`}
                                        >
                                            Sign up
                                        </button>
                                    </div>
                                </>
                            )}

                            {tab === 'signin' && (
                                <>
                                    <h2 className="font-serif text-3xl text-gray-900 mb-8">
                                        {role === 'candidate' ? 'Welcome back' : 'Recruiter sign in'}
                                    </h2>
                                    {role === 'candidate' && (
                                        <>
                                            <GithubContinueButton />
                                            <div className="flex items-center gap-3 my-6">
                                                <div className="h-px flex-1 bg-gray-200" />
                                                <span className="text-xs text-gray-400 uppercase tracking-wider">or</span>
                                                <div className="h-px flex-1 bg-gray-200" />
                                            </div>
                                        </>
                                    )}
                                    <SignInForm onSuccess={onAuthSuccess} onForgotPassword={() => setTab('forgot')} />
                                </>
                            )}
                            {tab === 'signup' && (
                                <>
                                    <h2 className="font-serif text-3xl text-gray-900">
                                        {role === 'candidate' ? 'Create your candidate account' : 'Create your recruiter account'}
                                    </h2>
                                    <p className="mt-2 text-sm text-gray-500 mb-8">
                                        {role === 'candidate'
                                            ? 'Submit proof of work and apply to outcomes.'
                                            : 'Define outcomes and evaluate candidates.'}
                                    </p>
                                    {role === 'candidate' && (
                                        <>
                                            <GithubContinueButton />
                                            <div className="flex items-center gap-3 my-6">
                                                <div className="h-px flex-1 bg-gray-200" />
                                                <span className="text-xs text-gray-400 uppercase tracking-wider">or</span>
                                                <div className="h-px flex-1 bg-gray-200" />
                                            </div>
                                        </>
                                    )}
                                    <SignUpForm onSuccess={onAuthSuccess} role={role} />
                                </>
                            )}
                            {tab === 'forgot' && (
                                <ForgotPasswordForm
                                    onDone={() => goToTab('signin')}
                                    onBackToSignIn={() => setTab('signin')}
                                />
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
