OUTCOME_PAYLOAD = {
    "id": "proof-test-outcome",
    "title": "Backend Role",
    "description": "Build an API.",
    "tasks": [{"task_id": "t1", "title": "Implement API", "success_criteria": {}}],
    "rubric": {"t1": 1.0},
}

PROOF_PAYLOAD = {
    "job_id": "proof-test-outcome",
    "candidate_id": "spoofed@attacker.com",  # must be ignored server-side
    "type": "github",
    "payload": {"repo_url": "https://github.com/octocat/Hello-World"},
}


def _create_outcome(client, recruiter_headers):
    client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=recruiter_headers)


def test_submit_proof_requires_candidate_role(client, recruiter_headers):
    _create_outcome(client, recruiter_headers)
    resp = client.post("/proofs", json=PROOF_PAYLOAD, headers=recruiter_headers)
    assert resp.status_code == 403


def test_submit_proof_requires_auth(client, recruiter_headers):
    _create_outcome(client, recruiter_headers)
    resp = client.post("/proofs", json=PROOF_PAYLOAD)
    assert resp.status_code == 401


def test_submit_proof_ignores_client_supplied_candidate_id(client, recruiter_headers, candidate_a_headers):
    _create_outcome(client, recruiter_headers)
    resp = client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    assert resp.status_code == 200
    # The identity in the response must be the authenticated candidate's email,
    # never the attacker-supplied "spoofed@attacker.com" from the request body.
    assert resp.json()["candidate_id"] == "candidate-a@example.com"


def test_submit_proof_twice_for_same_outcome_is_rejected(client, recruiter_headers, candidate_a_headers):
    _create_outcome(client, recruiter_headers)
    first = client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    assert first.status_code == 200

    second = client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    assert second.status_code == 409
    assert "already applied" in second.json()["detail"].lower()


def test_different_candidates_can_each_apply_once_to_the_same_outcome(client, recruiter_headers, candidate_a_headers, candidate_b_headers):
    _create_outcome(client, recruiter_headers)
    a = client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    b = client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_b_headers)
    assert a.status_code == 200
    assert b.status_code == 200


def test_submit_proof_unknown_outcome_returns_404(client, candidate_a_headers):
    bad_payload = {**PROOF_PAYLOAD, "job_id": "no-such-outcome"}
    resp = client.post("/proofs", json=bad_payload, headers=candidate_a_headers)
    assert resp.status_code == 404


def test_candidate_cannot_view_own_submitted_proof_list_without_recruiter_role(client, recruiter_headers, candidate_a_headers):
    # GET /proofs/{job_id} is a recruiter-facing endpoint over ALL candidates for
    # that outcome — a candidate must not be able to use it to see other candidates.
    _create_outcome(client, recruiter_headers)
    client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    resp = client.get("/proofs/proof-test-outcome", headers=candidate_a_headers)
    assert resp.status_code == 403


def test_owning_recruiter_can_list_proofs(client, recruiter_headers, candidate_a_headers):
    _create_outcome(client, recruiter_headers)
    client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    resp = client.get("/proofs/proof-test-outcome", headers=recruiter_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_non_owning_recruiter_cannot_list_proofs(client, recruiter_headers, other_recruiter_headers, candidate_a_headers):
    _create_outcome(client, recruiter_headers)
    client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    resp = client.get("/proofs/proof-test-outcome", headers=other_recruiter_headers)
    assert resp.status_code == 403


def test_submit_proof_blocked_without_connected_github(client, recruiter_headers, candidate_no_github_headers):
    _create_outcome(client, recruiter_headers)
    resp = client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_no_github_headers)
    assert resp.status_code == 403
    assert "Connect your GitHub" in resp.json()["detail"]


def test_submit_proof_blocked_when_repo_owner_does_not_match_verified_github(client, recruiter_headers, candidate_a_headers):
    # candidate_a is verified as GitHub user "octocat" — a repo under a
    # different owner must be rejected, even though it's a real public repo.
    _create_outcome(client, recruiter_headers)
    mismatched_payload = {**PROOF_PAYLOAD, "payload": {"repo_url": "https://github.com/torvalds/linux"}}
    resp = client.post("/proofs", json=mismatched_payload, headers=candidate_a_headers)
    assert resp.status_code == 403
    assert "does not belong to your verified GitHub account" in resp.json()["detail"]


def test_submit_proof_succeeds_when_repo_owner_matches_verified_github(client, recruiter_headers, candidate_a_headers):
    _create_outcome(client, recruiter_headers)
    resp = client.post("/proofs", json=PROOF_PAYLOAD, headers=candidate_a_headers)
    assert resp.status_code == 200
