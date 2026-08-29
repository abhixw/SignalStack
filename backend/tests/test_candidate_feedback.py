OUTCOME_PAYLOAD = {
    "id": "feedback-test-outcome",
    "title": "Backend Role",
    "description": "Build an API.",
    "tasks": [{"task_id": "t1", "title": "Implement API", "success_criteria": {}}],
    "rubric": {"t1": 1.0},
}

PROOF_PAYLOAD = {
    "job_id": "feedback-test-outcome",
    "candidate_id": "spoofed@attacker.com",
    "type": "github",
    "payload": {"repo_url": "https://github.com/octocat/Hello-World"},
}


def _evaluate(client, recruiter_headers, candidate_emails):
    proofs = [
        {"job_id": "feedback-test-outcome", "candidate_id": email, "type": "github",
         "payload": {"repo_url": "https://github.com/octocat/Hello-World"}}
        for email in candidate_emails
    ]
    resp = client.post("/plugin/evaluate", headers=recruiter_headers, json={
        "request_id": "req-1", "outcome": OUTCOME_PAYLOAD, "proofs": proofs,
    })
    assert resp.status_code == 200, resp.text


def _setup(client, recruiter_headers, candidate_a_headers):
    client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=recruiter_headers)
    client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    _evaluate(client, recruiter_headers, ["candidate-a@example.com"])


def test_suggest_feedback_returns_a_draft_without_persisting_anything(client, recruiter_headers, candidate_a_headers):
    _setup(client, recruiter_headers, candidate_a_headers)

    resp = client.post(
        "/evaluations/feedback-test-outcome/feedback/suggest",
        headers=recruiter_headers,
        json={"candidate_id": "candidate-a@example.com", "decision": "advancing"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["feedback"], str)
    assert len(resp.json()["feedback"]) > 0

    # Nothing persisted yet — no decision, no feedback stored.
    roster = client.get("/outcomes/feedback-test-outcome/candidates", headers=recruiter_headers).json()
    assert roster[0]["decision"] is None


def test_suggest_feedback_requires_owning_the_outcome(client, recruiter_headers, other_recruiter_headers, candidate_a_headers):
    _setup(client, recruiter_headers, candidate_a_headers)
    resp = client.post(
        "/evaluations/feedback-test-outcome/feedback/suggest",
        headers=other_recruiter_headers,
        json={"candidate_id": "candidate-a@example.com", "decision": "advancing"},
    )
    assert resp.status_code == 403


def test_suggest_feedback_rejects_unknown_candidate(client, recruiter_headers, candidate_a_headers):
    _setup(client, recruiter_headers, candidate_a_headers)
    resp = client.post(
        "/evaluations/feedback-test-outcome/feedback/suggest",
        headers=recruiter_headers,
        json={"candidate_id": "nobody@example.com", "decision": "advancing"},
    )
    assert resp.status_code == 404


def test_suggest_feedback_rejects_invalid_decision(client, recruiter_headers, candidate_a_headers):
    _setup(client, recruiter_headers, candidate_a_headers)
    resp = client.post(
        "/evaluations/feedback-test-outcome/feedback/suggest",
        headers=recruiter_headers,
        json={"candidate_id": "candidate-a@example.com", "decision": "maybe"},
    )
    assert resp.status_code == 400


def test_decision_with_feedback_is_visible_to_the_candidate(client, recruiter_headers, candidate_a_headers):
    _setup(client, recruiter_headers, candidate_a_headers)

    resp = client.post(
        "/evaluations/feedback-test-outcome/decision",
        headers=recruiter_headers,
        json={"candidate_id": "candidate-a@example.com", "decision": "advancing", "feedback": "Great work on the API layer!"},
    )
    assert resp.status_code == 200
    assert resp.json()["candidate_feedback"]["candidate-a@example.com"] == "Great work on the API layer!"

    apps = client.get("/candidate/my-applications", headers=candidate_a_headers).json()
    assert apps[0]["status"] == "Advancing to Interview"
    assert apps[0]["feedback"] == "Great work on the API layer!"


def test_decision_without_feedback_leaves_feedback_null(client, recruiter_headers, candidate_a_headers):
    _setup(client, recruiter_headers, candidate_a_headers)
    client.post(
        "/evaluations/feedback-test-outcome/decision",
        headers=recruiter_headers,
        json={"candidate_id": "candidate-a@example.com", "decision": "rejected"},
    )
    apps = client.get("/candidate/my-applications", headers=candidate_a_headers).json()
    assert apps[0]["feedback"] is None


def test_feedback_survives_reevaluation_same_as_decisions(client, recruiter_headers, candidate_a_headers, candidate_b_headers):
    _setup(client, recruiter_headers, candidate_a_headers)
    client.post(
        "/evaluations/feedback-test-outcome/decision",
        headers=recruiter_headers,
        json={"candidate_id": "candidate-a@example.com", "decision": "advancing", "feedback": "Solid submission."},
    )

    client.post("/proofs", json={**PROOF_PAYLOAD, "candidate_id": "irrelevant"}, headers=candidate_b_headers)
    _evaluate(client, recruiter_headers, ["candidate-a@example.com", "candidate-b@example.com"])

    apps = client.get("/candidate/my-applications", headers=candidate_a_headers).json()
    assert apps[0]["feedback"] == "Solid submission."
