const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "signalstack_token";

export function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
}

// A plain full-page redirect target (no auth needed) — GitHub's OAuth flow
// ends in a browser redirect, not a fetch, so this isn't called through
// `request()`. Use as <a href={getGithubLoginUrl()}> or window.location.href.
export function getGithubLoginUrl() {
    return `${API_URL}/auth/github/login`;
}

// Unlike login, /auth/github/connect requires the Bearer token — a plain link
// click can't send that header, so this fetches the authorize URL first
// (with auth attached) and the caller navigates the browser there itself.
export async function startGithubConnect(returnTo) {
    const qs = returnTo ? `?return_to=${encodeURIComponent(returnTo)}` : '';
    const { authorize_url } = await request(`/auth/github/connect${qs}`);
    window.location.href = authorize_url;
}

// Candidate sign-up with a password: does NOT create the account. Stashes
// the form details server-side and sends the browser to GitHub to prove the
// claimed username is real — the account is only created once GithubCallback
// completes the email+username confirm and OTP steps (flow=register_verify).
export async function registerCandidateStart({ email, password, fullName, githubUsername }) {
    const { authorize_url } = await request("/auth/register/candidate/start", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name: fullName, github_username: githubUsername }),
    });
    window.location.href = authorize_url;
}

// Fired whenever a request comes back 401 so AuthContext can clear stale state
// and redirect to /login, without every call site needing to handle it.
const AUTH_EXPIRED_EVENT = "signalstack:auth-expired";

async function request(path, options = {}) {
    const token = getToken();
    const headers = { ...(options.headers || {}) };
    if (options.body && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${path}`, { ...options, headers });

    if (response.status === 401) {
        clearToken();
        window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
    }

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = typeof errorData.detail === "string"
            ? errorData.detail
            : errorData.detail?.message || response.statusText || "Request failed";
        const error = new Error(detail);
        error.status = response.status;
        error.body = errorData;
        throw error;
    }

    if (response.status === 204) return null;
    return response.json();
}

export { AUTH_EXPIRED_EVENT };

// ---- Auth ----

export async function registerUser({ email, password, fullName, role }) {
    return request("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name: fullName, role }),
    });
}

export async function loginUser({ email, password }) {
    const data = await request("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    return data;
}

export async function getMe() {
    return request("/auth/me");
}

export async function forgotPassword(email) {
    return request("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
    });
}

export async function resetPassword({ email, otp, newPassword }) {
    return request("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ email, otp, new_password: newPassword }),
    });
}

// Must be called (and succeed) before verifyGithubOtp — no OTP is sent until
// the candidate correctly types both the email AND username connected to
// their GitHub account.
export async function confirmGithubEmail({ pendingToken, email, githubUsername }) {
    return request("/auth/github/confirm-email", {
        method: "POST",
        body: JSON.stringify({ pending_token: pendingToken, email, github_username: githubUsername }),
    });
}

// Completes whichever GitHub flow /auth/github/callback queued (login,
// signup, or connect) — nothing is created/linked/logged-in before this
// succeeds. Response is {access_token} for login/signup, {connected: true}
// for a connect flow (the caller is already authenticated in that case).
export async function verifyGithubOtp({ pendingToken, otp }) {
    return request("/auth/github/verify-otp", {
        method: "POST",
        body: JSON.stringify({ pending_token: pendingToken, otp }),
    });
}

// ---- Outcomes ----

export async function createOutcome(outcome) {
    return request("/outcomes", { method: "POST", body: JSON.stringify(outcome) });
}

export async function getOutcome(outcomeId) {
    return request(`/outcomes/${outcomeId}`);
}

export async function getOutcomes({ page = 1, pageSize = 20 } = {}) {
    return request(`/outcomes?page=${page}&page_size=${pageSize}`);
}

// Recruiter's own outcomes only (admin sees all) — used on the recruiter
// Dashboard so recruiters never click into an outcome they don't own.
export async function getMyOutcomes({ page = 1, pageSize = 20 } = {}) {
    return request(`/outcomes/mine?page=${page}&page_size=${pageSize}`);
}

// One row per applicant — name/GitHub username plus whatever evaluation
// state exists so far (has_score, decision). Powers the outcome dashboard's
// candidate list instead of a raw proof list.
export async function getCandidateRoster(outcomeId) {
    return request(`/outcomes/${outcomeId}/candidates`);
}

// ---- Proofs ----

export async function submitProof(proof) {
    return request("/proofs", { method: "POST", body: JSON.stringify(proof) });
}

export async function getProofs(outcomeId) {
    return request(`/proofs/${outcomeId}`);
}

// ---- Feedback / signal weights ----

export async function submitFeedback(feedback) {
    return request("/plugin/feedback", { method: "POST", body: JSON.stringify(feedback) });
}

export async function getSignalWeights() {
    return request("/admin/signal-weights");
}

// ---- Evaluations ----

export async function getEvaluations({ page = 1, pageSize = 20 } = {}) {
    return request(`/evaluations?page=${page}&page_size=${pageSize}`);
}

export async function triggerEvaluation(payload) {
    return request("/plugin/evaluate", { method: "POST", body: JSON.stringify(payload) });
}

export async function getEvaluation(jobId) {
    const data = await request(`/plugin/status/${jobId}`);
    if (data.status !== "completed" || !data.evaluation) {
        throw new Error("Evaluation not ready or not found");
    }
    return data.evaluation;
}

// The only thing that ever determines what a candidate sees about their
// application (GET /candidate/my-applications) — the raw score never reaches them.
export async function setCandidateDecision(jobId, candidateId, decision) {
    return request(`/evaluations/${jobId}/decision`, {
        method: "POST",
        body: JSON.stringify({ candidate_id: candidateId, decision }),
    });
}

// ---- Task suggestion / repo preview ----

export async function suggestTasks(description) {
    return request("/plugin/suggest-tasks", {
        method: "POST",
        body: JSON.stringify({ description }),
    });
}

export async function getRepoPreview(repoUrl) {
    return request(`/plugin/repo-preview?repo_url=${encodeURIComponent(repoUrl)}`);
}

// ---- Admin ----

export async function getAuditLogs({ page = 1, pageSize = 50 } = {}) {
    return request(`/admin/audit-logs?page=${page}&page_size=${pageSize}`);
}

// ---- Candidate ----

export async function getCandidateJobs({ page = 1, pageSize = 20, jobRole } = {}) {
    const roleParam = jobRole ? `&job_role=${encodeURIComponent(jobRole)}` : '';
    return request(`/candidate/jobs?page=${page}&page_size=${pageSize}${roleParam}`);
}

export async function getCandidateApplications() {
    // Identity comes from the JWT on the backend — no candidate id is ever passed.
    return request("/candidate/my-applications");
}

// ---- Candidate coding profiles (Codeforces / LeetCode — feed the DSA task-matching signal) ----

export async function getCodingProfiles() {
    return request("/candidate/coding-profiles");
}

// undefined = leave that field unchanged; "" = clear it; a value re-fetches
// and re-scores it. See app/routes/candidate.py for the exact semantics.
export async function updateCodingProfiles({ codeforcesHandle, leetcodeUsername } = {}) {
    const body = {};
    if (codeforcesHandle !== undefined) body.codeforces_handle = codeforcesHandle;
    if (leetcodeUsername !== undefined) body.leetcode_username = leetcodeUsername;
    return request("/candidate/coding-profiles", { method: "PATCH", body: JSON.stringify(body) });
}

export async function refreshCodingProfiles() {
    return request("/candidate/coding-profiles/refresh", { method: "POST" });
}
