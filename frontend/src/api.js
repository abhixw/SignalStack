const API_URL = "http://localhost:8000";

export async function createOutcome(outcome) {
    const response = await fetch(`${API_URL}/outcomes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(outcome),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to create outcome");
    }
    return response.json();
}

export async function getOutcome(outcomeId) {
    const response = await fetch(`${API_URL}/outcomes/${outcomeId}`);
    if (!response.ok) throw new Error("Failed to fetch outcome");
    return response.json();
}

// Mock function to get all outcomes (since backend doesn't have list endpoint yet)
// In a real app, we would add GET /outcomes
export async function getOutcomes() {
    // For MVP demo, we can just return a list if we had one, or fetch known ones.
    // Since we don't have a list endpoint, we'll mock it or add it to backend.
    // Let's add it to backend for correctness.
    const response = await fetch(`${API_URL}/outcomes`);
    if (!response.ok) return []; // Return empty if endpoint missing
    return response.json();
}

export async function submitProof(proof) {
    const response = await fetch(`${API_URL}/proofs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(proof),
    });
    if (!response.ok) throw new Error("Failed to trigger evaluation");
    return response.json();
}

export async function submitFeedback(feedback) {
    const response = await fetch(`${API_URL}/plugin/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(feedback),
    });
    return response.json();
}

export async function getSignalWeights() {
    const response = await fetch(`${API_URL}/admin/signal-weights`);
    return response.json();
}

export async function getEvaluations() {
    const response = await fetch(`${API_URL}/evaluations`);
    if (!response.ok) throw new Error("Failed to fetch evaluations");
    return response.json();
}

export async function getProofs(outcomeId) {
    const response = await fetch(`${API_URL}/proofs/${outcomeId}`);
    if (!response.ok) throw new Error("Failed to fetch proofs");
    return response.json();
}

export async function triggerEvaluation(payload) {
    const response = await fetch(`${API_URL}/plugin/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("Failed to trigger evaluation");
    return response.json();
}

export async function getEvaluation(jobId) {
    const response = await fetch(`${API_URL}/plugin/status/${jobId}`);
    if (!response.ok) throw new Error("Failed to fetch evaluation");
    if (data.status !== 'completed' || !data.evaluation) {
        throw new Error("Evaluation not ready or not found");
    }
    return data.evaluation;
}

export const suggestTasks = async (description) => {
    const response = await fetch(`${API_URL}/plugin/suggest-tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description })
    });
    if (!response.ok) throw new Error('Failed to suggest tasks');
    return response.json();
};

export const getRepoPreview = async (repoUrl) => {
    const response = await fetch(`${API_URL}/plugin/repo-preview?repo_url=${encodeURIComponent(repoUrl)}`);
    if (!response.ok) throw new Error('Failed to fetch repo preview');
    return response.json();
};

export async function getAuditLogs() {
    const response = await fetch(`${API_URL}/admin/audit-logs`);
    if (!response.ok) throw new Error("Failed to fetch audit logs");
    return response.json();
}

