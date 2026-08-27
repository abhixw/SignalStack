from app.constants import JobRole


def _outcome_payload(outcome_id, job_role=None):
    return {
        "id": outcome_id,
        "title": "Some role",
        "description": "test",
        "tasks": [{"task_id": "t1", "title": "Do the thing", "success_criteria": {}}],
        "rubric": {"t1": 1.0},
        "job_role": job_role,
    }


def test_get_job_roles_returns_the_fixed_list(client):
    resp = client.get("/job-roles")
    assert resp.status_code == 200
    assert resp.json() == list(JobRole.ALL)


def test_create_outcome_accepts_a_valid_job_role(client, recruiter_headers):
    resp = client.post("/outcomes", headers=recruiter_headers, json=_outcome_payload("jr-1", JobRole.BACKEND))
    assert resp.status_code == 200
    assert resp.json()["job_role"] == JobRole.BACKEND


def test_create_outcome_rejects_an_invalid_job_role(client, recruiter_headers):
    resp = client.post("/outcomes", headers=recruiter_headers, json=_outcome_payload("jr-2", "Astronaut"))
    assert resp.status_code == 400


def test_create_outcome_allows_no_job_role(client, recruiter_headers):
    resp = client.post("/outcomes", headers=recruiter_headers, json=_outcome_payload("jr-3", None))
    assert resp.status_code == 200
    assert resp.json()["job_role"] is None


def test_update_outcome_rejects_an_invalid_job_role(client, recruiter_headers):
    client.post("/outcomes", headers=recruiter_headers, json=_outcome_payload("jr-4", JobRole.BACKEND))
    resp = client.put("/outcomes/jr-4", headers=recruiter_headers, json=_outcome_payload("jr-4", "Astronaut"))
    assert resp.status_code == 400


def test_candidate_jobs_filters_by_job_role(client, recruiter_headers):
    client.post("/outcomes", headers=recruiter_headers, json=_outcome_payload("jr-backend", JobRole.BACKEND))
    client.post("/outcomes", headers=recruiter_headers, json=_outcome_payload("jr-frontend", JobRole.FRONTEND))

    backend_only = client.get(f"/candidate/jobs?job_role={JobRole.BACKEND}").json()
    ids = {o["id"] for o in backend_only}
    assert "jr-backend" in ids
    assert "jr-frontend" not in ids


def test_candidate_jobs_without_filter_returns_all_roles(client, recruiter_headers):
    client.post("/outcomes", headers=recruiter_headers, json=_outcome_payload("jr-a", JobRole.BACKEND))
    client.post("/outcomes", headers=recruiter_headers, json=_outcome_payload("jr-b", JobRole.FRONTEND))

    all_jobs = client.get("/candidate/jobs").json()
    ids = {o["id"] for o in all_jobs}
    assert "jr-a" in ids
    assert "jr-b" in ids


def test_public_outcomes_endpoint_also_filters_by_job_role(client, recruiter_headers):
    client.post("/outcomes", headers=recruiter_headers, json=_outcome_payload("jr-x", JobRole.DATA_ML))
    client.post("/outcomes", headers=recruiter_headers, json=_outcome_payload("jr-y", JobRole.DEVOPS))

    resp = client.get(f"/outcomes?job_role={JobRole.DATA_ML}")
    ids = {o["id"] for o in resp.json()}
    assert "jr-x" in ids
    assert "jr-y" not in ids
