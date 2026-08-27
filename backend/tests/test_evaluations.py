OUTCOME_PAYLOAD = {
    "id": "eval-outcome-1",
    "title": "ML Engineer",
    "description": "Train and ship a model.",
    "tasks": [{"task_id": "t1", "title": "train model", "success_criteria": {}}],
    "rubric": {"t1": 1.0},
}


def test_authorized_evaluation_succeeds_and_is_persisted(client, recruiter_headers, candidate_a_headers):
    client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=recruiter_headers)
    proof = {
        "job_id": "eval-outcome-1",
        "candidate_id": "ignored",
        "type": "github",
        "payload": {"repo_url": "https://github.com/octocat/Hello-World"},
    }
    client.post("/proofs", json=proof, headers=candidate_a_headers)

    evaluate_payload = {
        "request_id": "req-1",
        "outcome": OUTCOME_PAYLOAD,
        "proofs": [{**proof, "candidate_id": "candidate-a@example.com"}],
    }
    resp = client.post("/plugin/evaluate", json=evaluate_payload, headers=recruiter_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["job_id"] == "eval-outcome-1"

    status_resp = client.get("/plugin/status/eval-outcome-1", headers=recruiter_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "completed"


def test_evaluate_unauthenticated_returns_401(client, recruiter_headers):
    client.post("/outcomes", json={**OUTCOME_PAYLOAD, "id": "eval-outcome-2"}, headers=recruiter_headers)
    payload = {"request_id": "req-2", "outcome": {**OUTCOME_PAYLOAD, "id": "eval-outcome-2"}, "proofs": []}
    resp = client.post("/plugin/evaluate", json=payload)
    assert resp.status_code == 401


def test_evaluate_nonexistent_outcome_returns_404(client, recruiter_headers):
    payload = {
        "request_id": "req-3",
        "outcome": {**OUTCOME_PAYLOAD, "id": "does-not-exist-eval"},
        "proofs": [],
    }
    resp = client.post("/plugin/evaluate", json=payload, headers=recruiter_headers)
    assert resp.status_code == 404


def test_status_check_requires_ownership(client, recruiter_headers, other_recruiter_headers):
    outcome = {**OUTCOME_PAYLOAD, "id": "eval-outcome-status-scope"}
    client.post("/outcomes", json=outcome, headers=recruiter_headers)
    resp = client.get(f"/plugin/status/{outcome['id']}", headers=other_recruiter_headers)
    assert resp.status_code == 403


def test_evaluations_list_requires_recruiter_or_admin(client, candidate_a_headers):
    resp = client.get("/evaluations", headers=candidate_a_headers)
    assert resp.status_code == 403
