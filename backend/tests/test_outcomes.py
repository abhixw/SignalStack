OUTCOME_PAYLOAD = {
    "id": "outcome-create-1",
    "title": "Data Engineer",
    "description": "Build an ETL pipeline.",
    "tasks": [{"task_id": "t1", "title": "Write pipeline", "success_criteria": {}}],
    "rubric": {"t1": 1.0},
}


def test_create_outcome_requires_recruiter_or_admin(client, candidate_a_headers):
    resp = client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=candidate_a_headers)
    assert resp.status_code == 403


def test_create_outcome_requires_auth(client):
    resp = client.post("/outcomes", json=OUTCOME_PAYLOAD)
    assert resp.status_code == 401


def test_recruiter_can_create_outcome(client, recruiter_headers):
    resp = client.post("/outcomes", json=OUTCOME_PAYLOAD, headers=recruiter_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == "outcome-create-1"


def test_duplicate_outcome_id_rejected(client, recruiter_headers):
    payload = {**OUTCOME_PAYLOAD, "id": "outcome-dup"}
    first = client.post("/outcomes", json=payload, headers=recruiter_headers)
    assert first.status_code == 200
    second = client.post("/outcomes", json=payload, headers=recruiter_headers)
    assert second.status_code == 400


def test_get_outcomes_is_public_no_auth_needed(client, recruiter_headers):
    client.post("/outcomes", json={**OUTCOME_PAYLOAD, "id": "outcome-public-1"}, headers=recruiter_headers)
    resp = client.get("/outcomes")
    assert resp.status_code == 200
    ids = [o["id"] for o in resp.json()]
    assert "outcome-public-1" in ids


def test_get_single_outcome_is_public(client, recruiter_headers):
    client.post("/outcomes", json={**OUTCOME_PAYLOAD, "id": "outcome-public-2"}, headers=recruiter_headers)
    resp = client.get("/outcomes/outcome-public-2")
    assert resp.status_code == 200


def test_get_outcome_404_for_unknown_id(client):
    resp = client.get("/outcomes/does-not-exist-at-all")
    assert resp.status_code == 404


def test_outcomes_list_is_paginated(client, recruiter_headers):
    for i in range(3):
        client.post("/outcomes", json={**OUTCOME_PAYLOAD, "id": f"outcome-page-{i}"}, headers=recruiter_headers)
    resp = client.get("/outcomes?page=1&page_size=2")
    assert resp.status_code == 200
    assert len(resp.json()) <= 2


def test_owner_can_update_own_outcome(client, recruiter_headers):
    client.post("/outcomes", json={**OUTCOME_PAYLOAD, "id": "outcome-update-1"}, headers=recruiter_headers)
    updated = {**OUTCOME_PAYLOAD, "id": "outcome-update-1", "title": "Updated Title"}
    resp = client.put("/outcomes/outcome-update-1", json=updated, headers=recruiter_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


def test_non_owner_recruiter_cannot_update_outcome(client, recruiter_headers, other_recruiter_headers):
    client.post("/outcomes", json={**OUTCOME_PAYLOAD, "id": "outcome-owned-by-r1"}, headers=recruiter_headers)
    updated = {**OUTCOME_PAYLOAD, "id": "outcome-owned-by-r1", "title": "Hijacked"}
    resp = client.put("/outcomes/outcome-owned-by-r1", json=updated, headers=other_recruiter_headers)
    assert resp.status_code == 403


def test_admin_can_update_any_outcome(client, recruiter_headers, admin_headers):
    client.post("/outcomes", json={**OUTCOME_PAYLOAD, "id": "outcome-admin-edit"}, headers=recruiter_headers)
    updated = {**OUTCOME_PAYLOAD, "id": "outcome-admin-edit", "title": "Admin Edited"}
    resp = client.put("/outcomes/outcome-admin-edit", json=updated, headers=admin_headers)
    assert resp.status_code == 200


def test_outcomes_mine_requires_auth(client):
    resp = client.get("/outcomes/mine")
    assert resp.status_code == 401


def test_outcomes_mine_requires_recruiter_or_admin(client, candidate_a_headers):
    resp = client.get("/outcomes/mine", headers=candidate_a_headers)
    assert resp.status_code == 403


def test_outcomes_mine_only_shows_own_outcomes(client, recruiter_headers, other_recruiter_headers):
    client.post("/outcomes", json={**OUTCOME_PAYLOAD, "id": "outcome-mine-r1"}, headers=recruiter_headers)
    client.post("/outcomes", json={**OUTCOME_PAYLOAD, "id": "outcome-mine-r2"}, headers=other_recruiter_headers)

    r1_view = client.get("/outcomes/mine", headers=recruiter_headers).json()
    r2_view = client.get("/outcomes/mine", headers=other_recruiter_headers).json()

    assert any(o["id"] == "outcome-mine-r1" for o in r1_view)
    assert all(o["id"] != "outcome-mine-r2" for o in r1_view)
    assert any(o["id"] == "outcome-mine-r2" for o in r2_view)
    assert all(o["id"] != "outcome-mine-r1" for o in r2_view)


def test_outcomes_mine_includes_real_rubric_for_owner(client, recruiter_headers):
    payload = {**OUTCOME_PAYLOAD, "id": "outcome-mine-rubric", "rubric": {"depth": 0.6, "clarity": 0.4}}
    client.post("/outcomes", json=payload, headers=recruiter_headers)

    resp = client.get("/outcomes/mine", headers=recruiter_headers)
    outcome = next(o for o in resp.json() if o["id"] == "outcome-mine-rubric")
    assert outcome["rubric"] == {"depth": 0.6, "clarity": 0.4}


def test_outcomes_mine_admin_sees_all(client, recruiter_headers, admin_headers):
    client.post("/outcomes", json={**OUTCOME_PAYLOAD, "id": "outcome-mine-visible-to-admin"}, headers=recruiter_headers)
    resp = client.get("/outcomes/mine", headers=admin_headers)
    assert any(o["id"] == "outcome-mine-visible-to-admin" for o in resp.json())
