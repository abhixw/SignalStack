OUTCOME_PAYLOAD = {
    "id": "roster-test-outcome",
    "title": "Backend Role",
    "description": "Build an API.",
    "tasks": [{"task_id": "t1", "title": "Implement API", "success_criteria": {}}],
    "rubric": {"t1": 1.0},
}

PROOF_PAYLOAD = {
    "job_id": "roster-test-outcome",
    "candidate_id": "spoofed@attacker.com",
    "type": "github",
    "payload": {"repo_url": "https://github.com/octocat/Hello-World"},
}


def _evaluate(client, recruiter_headers, candidate_emails):
    proofs = [
        {"job_id": "roster-test-outcome", "candidate_id": email, "type": "github",
         "payload": {"repo_url": "https://github.com/octocat/Hello-World"}}
        for email in candidate_emails
    ]
    resp = client.post("/plugin/evaluate", headers=recruiter_headers, json={
        "request_id": "req-1", "outcome": OUTCOME_PAYLOAD, "proofs": proofs,
    })
    assert resp.status_code == 200, resp.text


def test_roster_lists_applicants_with_name_and_github_username(client, recruiter_headers, candidate_a_headers):
    client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=recruiter_headers)
    client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)

    resp = client.get("/outcomes/roster-test-outcome/candidates", headers=recruiter_headers)
    assert resp.status_code == 200
    roster = resp.json()
    assert len(roster) == 1
    assert roster[0]["candidate_id"] == "candidate-a@example.com"
    assert roster[0]["github_username"] == "octocat"
    assert roster[0]["has_score"] is False
    assert roster[0]["decision"] is None


def test_roster_reflects_score_and_decision_after_evaluation(client, recruiter_headers, candidate_a_headers):
    client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=recruiter_headers)
    client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    _evaluate(client, recruiter_headers, ["candidate-a@example.com"])

    roster = client.get("/outcomes/roster-test-outcome/candidates", headers=recruiter_headers).json()
    assert roster[0]["has_score"] is True
    assert roster[0]["decision"] is None

    client.post("/evaluations/roster-test-outcome/decision", headers=recruiter_headers,
                json={"candidate_id": "candidate-a@example.com", "decision": "advancing"})

    roster = client.get("/outcomes/roster-test-outcome/candidates", headers=recruiter_headers).json()
    assert roster[0]["decision"] == "advancing"


def test_roster_requires_owning_the_outcome(client, recruiter_headers, other_recruiter_headers):
    client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=recruiter_headers)
    resp = client.get("/outcomes/roster-test-outcome/candidates", headers=other_recruiter_headers)
    assert resp.status_code == 403


def test_reevaluating_after_a_new_applicant_does_not_erase_existing_decisions(
    client, recruiter_headers, candidate_a_headers, candidate_b_headers,
):
    """The actual regression this protects against: re-running /plugin/evaluate
    (e.g. because a new candidate applied) inserts a brand-new evaluation doc —
    without carrying decisions forward, a recruiter's earlier Advance/Reject
    would silently vanish the moment anyone else applied."""
    client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=recruiter_headers)
    client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    _evaluate(client, recruiter_headers, ["candidate-a@example.com"])
    client.post("/evaluations/roster-test-outcome/decision", headers=recruiter_headers,
                json={"candidate_id": "candidate-a@example.com", "decision": "advancing"})

    # Candidate B applies later, triggering a fresh evaluation run that now
    # includes both candidates.
    client.post("/proofs", json={**PROOF_PAYLOAD, "candidate_id": "irrelevant"}, headers=candidate_b_headers)
    _evaluate(client, recruiter_headers, ["candidate-a@example.com", "candidate-b@example.com"])

    roster = client.get("/outcomes/roster-test-outcome/candidates", headers=recruiter_headers).json()
    by_id = {r["candidate_id"]: r for r in roster}
    assert by_id["candidate-a@example.com"]["decision"] == "advancing"  # survived the re-run
    assert by_id["candidate-b@example.com"]["decision"] is None
