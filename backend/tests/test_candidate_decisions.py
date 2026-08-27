OUTCOME_PAYLOAD = {
    "id": "decision-test-outcome",
    "title": "Backend Role",
    "description": "Build an API.",
    "tasks": [{"task_id": "t1", "title": "Implement API", "success_criteria": {}}],
    "rubric": {"t1": 1.0},
}

PROOF_PAYLOAD = {
    "job_id": "decision-test-outcome",
    "candidate_id": "spoofed@attacker.com",
    "type": "github",
    "payload": {"repo_url": "https://github.com/octocat/Hello-World"},
}


def _create_outcome_and_evaluate(client, recruiter_headers, candidate_a_headers, candidate_email):
    client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=recruiter_headers)
    client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    resp = client.post("/plugin/evaluate", headers=recruiter_headers, json={
        "request_id": "req-1",
        "outcome": OUTCOME_PAYLOAD,
        "proofs": [{"job_id": "decision-test-outcome", "candidate_id": candidate_email, "type": "github",
                    "payload": {"repo_url": "https://github.com/octocat/Hello-World"}}],
    })
    assert resp.status_code == 200, resp.text


def test_evaluation_response_never_contains_a_raw_score_field_visible_to_candidates(client, recruiter_headers, candidate_a_headers):
    candidate_email = client.get("/auth/me", headers=candidate_a_headers).json()["email"]
    _create_outcome_and_evaluate(client, recruiter_headers, candidate_a_headers, candidate_email)

    apps = client.get("/candidate/my-applications", headers=candidate_a_headers).json()
    assert len(apps) == 1
    assert "score" not in apps[0]
    assert apps[0]["status"] == "Under Review"


def test_recruiter_can_set_candidate_decision_and_candidate_sees_it(client, recruiter_headers, candidate_a_headers):
    candidate_email = client.get("/auth/me", headers=candidate_a_headers).json()["email"]
    _create_outcome_and_evaluate(client, recruiter_headers, candidate_a_headers, candidate_email)

    resp = client.post(
        "/evaluations/decision-test-outcome/decision",
        headers=recruiter_headers,
        json={"candidate_id": candidate_email, "decision": "advancing"},
    )
    assert resp.status_code == 200
    assert resp.json()["candidate_decisions"][candidate_email] == "advancing"

    apps = client.get("/candidate/my-applications", headers=candidate_a_headers).json()
    assert apps[0]["status"] == "Advancing to Interview"
    assert "score" not in apps[0]


def test_recruiter_can_reject_a_candidate(client, recruiter_headers, candidate_a_headers):
    candidate_email = client.get("/auth/me", headers=candidate_a_headers).json()["email"]
    _create_outcome_and_evaluate(client, recruiter_headers, candidate_a_headers, candidate_email)

    client.post(
        "/evaluations/decision-test-outcome/decision",
        headers=recruiter_headers,
        json={"candidate_id": candidate_email, "decision": "rejected"},
    )
    apps = client.get("/candidate/my-applications", headers=candidate_a_headers).json()
    assert apps[0]["status"] == "Rejected"


def test_decision_endpoint_rejects_invalid_decision_value(client, recruiter_headers, candidate_a_headers):
    candidate_email = client.get("/auth/me", headers=candidate_a_headers).json()["email"]
    _create_outcome_and_evaluate(client, recruiter_headers, candidate_a_headers, candidate_email)

    resp = client.post(
        "/evaluations/decision-test-outcome/decision",
        headers=recruiter_headers,
        json={"candidate_id": candidate_email, "decision": "maybe"},
    )
    assert resp.status_code == 400


def test_decision_endpoint_rejects_unknown_candidate(client, recruiter_headers, candidate_a_headers):
    candidate_email = client.get("/auth/me", headers=candidate_a_headers).json()["email"]
    _create_outcome_and_evaluate(client, recruiter_headers, candidate_a_headers, candidate_email)

    resp = client.post(
        "/evaluations/decision-test-outcome/decision",
        headers=recruiter_headers,
        json={"candidate_id": "not-a-real-applicant@example.com", "decision": "advancing"},
    )
    assert resp.status_code == 404


def test_decision_endpoint_requires_owning_the_outcome(client, recruiter_headers, other_recruiter_headers, candidate_a_headers):
    candidate_email = client.get("/auth/me", headers=candidate_a_headers).json()["email"]
    _create_outcome_and_evaluate(client, recruiter_headers, candidate_a_headers, candidate_email)

    resp = client.post(
        "/evaluations/decision-test-outcome/decision",
        headers=other_recruiter_headers,
        json={"candidate_id": candidate_email, "decision": "advancing"},
    )
    assert resp.status_code == 403


def test_decision_endpoint_requires_recruiter_role(client, candidate_a_headers):
    resp = client.post(
        "/evaluations/decision-test-outcome/decision",
        headers=candidate_a_headers,
        json={"candidate_id": "someone@example.com", "decision": "advancing"},
    )
    assert resp.status_code == 403


def test_decision_survives_candidate_email_containing_dots(client, recruiter_headers, candidate_a_headers):
    """The real regression this guards: candidate_id is an email, so it
    contains "." — a naive `$set` on a dotted Mongo path built from it would
    silently write to the wrong nested field instead of storing the decision."""
    candidate_email = client.get("/auth/me", headers=candidate_a_headers).json()["email"]
    assert "." in candidate_email  # sanity: the fixture email really has a dot in it
    _create_outcome_and_evaluate(client, recruiter_headers, candidate_a_headers, candidate_email)

    client.post(
        "/evaluations/decision-test-outcome/decision",
        headers=recruiter_headers,
        json={"candidate_id": candidate_email, "decision": "advancing"},
    )
    status_resp = client.get("/plugin/status/decision-test-outcome", headers=recruiter_headers)
    decisions = status_resp.json()["evaluation"]["candidate_decisions"]
    assert decisions == {candidate_email: "advancing"}
