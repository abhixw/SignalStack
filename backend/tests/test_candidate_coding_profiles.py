from app.services import codeforces, leetcode
from app.services.errors import UpstreamServiceError


def _mock_codeforces_ok(monkeypatch, rating=1500, total_solved=50):
    monkeypatch.setattr(codeforces, "fetch_user_info", lambda handle: {
        "handle": handle, "rating": rating, "max_rating": rating, "rank": "expert", "max_rank": "expert",
    })
    monkeypatch.setattr(codeforces, "fetch_solved_problem_counts", lambda handle: {
        "easy": total_solved, "medium": 0, "hard": 0, "unrated": 0, "total": total_solved,
    })


def _mock_codeforces_not_found(monkeypatch):
    def raise_not_found(handle):
        raise UpstreamServiceError("codeforces", "NOT_FOUND", "Codeforces handle not found.", retryable=False, status_code=404)
    monkeypatch.setattr(codeforces, "fetch_user_info", raise_not_found)
    monkeypatch.setattr(codeforces, "fetch_solved_problem_counts", raise_not_found)


def _mock_leetcode_ok(monkeypatch, solved_all=100):
    monkeypatch.setattr(leetcode, "fetch_user_stats", lambda username: {
        "username": username, "ranking": 5000, "solved": {"easy": solved_all, "medium": 0, "hard": 0, "all": solved_all},
    })


def _mock_leetcode_failure(monkeypatch):
    monkeypatch.setattr(leetcode, "fetch_user_stats", lambda username: None)


def test_get_coding_profiles_defaults_when_nothing_set(client, candidate_a_headers):
    resp = client.get("/candidate/coding-profiles", headers=candidate_a_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["codeforces_handle"] is None
    assert body["leetcode_username"] is None
    assert body["dsa_proficiency"] == 0.0


def test_patch_sets_codeforces_handle_and_computes_score(client, monkeypatch, candidate_a_headers):
    _mock_codeforces_ok(monkeypatch, rating=2100, total_solved=10)
    resp = client.patch("/candidate/coding-profiles", headers=candidate_a_headers, json={"codeforces_handle": "someuser"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["codeforces_handle"] == "someuser"
    assert body["dsa_proficiency"] == 1.0  # rating 2100 == full score

    # Persisted — a follow-up GET reflects it too.
    get_resp = client.get("/candidate/coding-profiles", headers=candidate_a_headers)
    assert get_resp.json()["codeforces_handle"] == "someuser"


def test_patch_rejects_unknown_codeforces_handle_and_does_not_persist(client, monkeypatch, candidate_a_headers):
    _mock_codeforces_not_found(monkeypatch)
    resp = client.patch("/candidate/coding-profiles", headers=candidate_a_headers, json={"codeforces_handle": "ghost"})
    assert resp.status_code == 400

    get_resp = client.get("/candidate/coding-profiles", headers=candidate_a_headers)
    assert get_resp.json()["codeforces_handle"] is None


def test_patch_leetcode_fetch_failure_does_not_block_the_request(client, monkeypatch, candidate_a_headers):
    _mock_leetcode_failure(monkeypatch)
    resp = client.patch("/candidate/coding-profiles", headers=candidate_a_headers, json={"leetcode_username": "someone"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["leetcode_username"] == "someone"
    assert body["leetcode_fetch_failed"] is True
    assert body["dsa_proficiency"] == 0.0


def test_patch_empty_string_clears_a_handle(client, monkeypatch, candidate_a_headers):
    _mock_codeforces_ok(monkeypatch)
    client.patch("/candidate/coding-profiles", headers=candidate_a_headers, json={"codeforces_handle": "someuser"})

    resp = client.patch("/candidate/coding-profiles", headers=candidate_a_headers, json={"codeforces_handle": ""})
    assert resp.status_code == 200
    assert resp.json()["codeforces_handle"] is None
    assert resp.json()["dsa_proficiency"] == 0.0


def test_patch_omitted_field_leaves_it_unchanged(client, monkeypatch, candidate_a_headers):
    _mock_codeforces_ok(monkeypatch)
    _mock_leetcode_ok(monkeypatch, solved_all=50)
    client.patch("/candidate/coding-profiles", headers=candidate_a_headers, json={
        "codeforces_handle": "someuser", "leetcode_username": "someone",
    })

    # Only touch leetcode_username this time — codeforces_handle must survive.
    _mock_leetcode_ok(monkeypatch, solved_all=80)
    resp = client.patch("/candidate/coding-profiles", headers=candidate_a_headers, json={"leetcode_username": "someone-else"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["codeforces_handle"] == "someuser"
    assert body["leetcode_username"] == "someone-else"


def test_refresh_uses_stored_handles_without_a_body(client, monkeypatch, candidate_a_headers):
    _mock_codeforces_ok(monkeypatch, rating=1000, total_solved=0)
    client.patch("/candidate/coding-profiles", headers=candidate_a_headers, json={"codeforces_handle": "someuser"})

    _mock_codeforces_ok(monkeypatch, rating=2100, total_solved=0)  # candidate's rating "improved"
    resp = client.post("/candidate/coding-profiles/refresh", headers=candidate_a_headers)
    assert resp.status_code == 200
    assert resp.json()["dsa_proficiency"] == 1.0


def test_coding_profiles_requires_candidate_role(client, recruiter_headers):
    resp = client.get("/candidate/coding-profiles", headers=recruiter_headers)
    assert resp.status_code == 403


def test_dsa_task_score_uses_cached_coding_profile_at_evaluation_time(client, monkeypatch, recruiter_headers, candidate_a_headers):
    _mock_codeforces_ok(monkeypatch, rating=2100, total_solved=0)
    client.patch("/candidate/coding-profiles", headers=candidate_a_headers, json={"codeforces_handle": "someuser"})

    outcome_payload = {
        "id": "dsa-outcome-1",
        "title": "DSA-heavy SDE role",
        "description": "test",
        "tasks": [{"task_id": "t1", "title": "Strong algorithms and data structures", "success_criteria": {}}],
        "rubric": {"t1": 1.0},
    }
    create_resp = client.post("/outcomes", headers=recruiter_headers, json=outcome_payload)
    assert create_resp.status_code == 200, create_resp.text

    proof_payload = {
        "job_id": "dsa-outcome-1",
        "candidate_id": "spoofed@attacker.com",
        "type": "github",
        "payload": {"repo_url": "https://github.com/octocat/Hello-World"},
    }
    proof_resp = client.post("/proofs", headers=candidate_a_headers, json=proof_payload)
    assert proof_resp.status_code == 200, proof_resp.text
    candidate_email = client.get("/auth/me", headers=candidate_a_headers).json()["email"]

    eval_resp = client.post("/plugin/evaluate", headers=recruiter_headers, json={
        "request_id": "req-1",
        "outcome": outcome_payload,
        "proofs": [{"job_id": "dsa-outcome-1", "candidate_id": candidate_email, "type": "github",
                    "payload": {"repo_url": "https://github.com/octocat/Hello-World"}}],
    })
    assert eval_resp.status_code == 200, eval_resp.text
    task_scores = eval_resp.json()["evaluation"]["candidate_task_scores"][candidate_email]
    assert task_scores[0]["score"] == 1.0
