OUTCOME_PAYLOAD = {
    "id": "authz-outcome",
    "title": "Full Stack Role",
    "description": "Build a full stack app.",
    "tasks": [{"task_id": "t1", "title": "Ship it", "success_criteria": {}}],
    "rubric": {"t1": 1.0},
}

PROOF_PAYLOAD = {
    "job_id": "authz-outcome",
    "candidate_id": "irrelevant",
    "type": "github",
    "payload": {"repo_url": "https://github.com/octocat/Hello-World"},
}


def test_candidate_a_cannot_see_candidate_b_applications(client, recruiter_headers, candidate_a_headers, candidate_b_headers):
    client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=recruiter_headers)
    client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)

    a_apps = client.get("/candidate/my-applications", headers=candidate_a_headers).json()
    b_apps = client.get("/candidate/my-applications", headers=candidate_b_headers).json()

    assert any(a["job_id"] == "authz-outcome" for a in a_apps)
    assert all(a["job_id"] != "authz-outcome" for a in b_apps)


def test_my_applications_requires_candidate_role(client, recruiter_headers):
    resp = client.get("/candidate/my-applications", headers=recruiter_headers)
    assert resp.status_code == 403


def test_candidate_cannot_access_admin_audit_logs(client, candidate_a_headers):
    resp = client.get("/admin/audit-logs", headers=candidate_a_headers)
    assert resp.status_code == 403


def test_candidate_cannot_access_recruiter_evaluate(client, candidate_a_headers):
    payload = {
        "request_id": "r1",
        "outcome": OUTCOME_PAYLOAD,
        "proofs": [],
    }
    resp = client.post("/plugin/evaluate", json=payload, headers=candidate_a_headers)
    assert resp.status_code == 403


def test_recruiter_cannot_access_admin_signal_weights(client, recruiter_headers):
    resp = client.get("/admin/signal-weights", headers=recruiter_headers)
    assert resp.status_code == 403


def test_admin_can_access_audit_logs(client, admin_headers):
    resp = client.get("/admin/audit-logs", headers=admin_headers)
    assert resp.status_code == 200


def test_recruiter_a_cannot_trigger_evaluation_on_recruiter_b_outcome(client, recruiter_headers, other_recruiter_headers):
    outcome = {**OUTCOME_PAYLOAD, "id": "authz-outcome-r1-owned"}
    client.post("/outcomes", json=outcome, headers=recruiter_headers)

    payload = {"request_id": "r1", "outcome": outcome, "proofs": []}
    resp = client.post("/plugin/evaluate", json=payload, headers=other_recruiter_headers)
    assert resp.status_code == 403


def test_evaluations_list_is_scoped_to_owning_recruiter(client, recruiter_headers, other_recruiter_headers):
    outcome = {**OUTCOME_PAYLOAD, "id": "authz-outcome-eval-scope"}
    client.post("/outcomes", json=outcome, headers=recruiter_headers)
    payload = {"request_id": "r1", "outcome": outcome, "proofs": []}
    client.post("/plugin/evaluate", json=payload, headers=recruiter_headers)

    own = client.get("/evaluations", headers=recruiter_headers).json()
    other = client.get("/evaluations", headers=other_recruiter_headers).json()

    assert any(e["job_id"] == "authz-outcome-eval-scope" for e in own)
    assert all(e["job_id"] != "authz-outcome-eval-scope" for e in other)
