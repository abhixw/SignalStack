RUBRIC_OUTCOME_PAYLOAD = {
    "id": "rubric-leak-outcome",
    "title": "Rubric Leak Check",
    "description": "d",
    "tasks": [{"task_id": "t1", "title": "Task One", "success_criteria": {"outcome": "must be visible to candidates"}}],
    "rubric": {"technical_depth": 0.7, "completeness": 0.3},
}


def test_public_outcome_list_hides_rubric_but_keeps_success_criteria(client, recruiter_headers):
    client.post("/outcomes", json=RUBRIC_OUTCOME_PAYLOAD, headers=recruiter_headers)

    resp = client.get("/outcomes")
    assert resp.status_code == 200
    outcome = next(o for o in resp.json() if o["id"] == "rubric-leak-outcome")
    assert outcome["rubric"] == {}
    assert outcome["tasks"][0]["success_criteria"] == {"outcome": "must be visible to candidates"}


def test_public_single_outcome_hides_rubric(client, recruiter_headers):
    client.post("/outcomes", json=RUBRIC_OUTCOME_PAYLOAD, headers=recruiter_headers)

    resp = client.get("/outcomes/rubric-leak-outcome")
    assert resp.status_code == 200
    assert resp.json()["rubric"] == {}


def test_candidate_jobs_hides_rubric(client, recruiter_headers):
    client.post("/outcomes", json=RUBRIC_OUTCOME_PAYLOAD, headers=recruiter_headers)

    resp = client.get("/candidate/jobs")
    assert resp.status_code == 200
    outcome = next(o for o in resp.json() if o["id"] == "rubric-leak-outcome")
    assert outcome["rubric"] == {}


def test_owner_update_response_still_returns_real_rubric(client, recruiter_headers):
    # include_rubric=True only for the authenticated owner confirming their own write.
    client.post("/outcomes", json=RUBRIC_OUTCOME_PAYLOAD, headers=recruiter_headers)
    resp = client.put("/outcomes/rubric-leak-outcome", json=RUBRIC_OUTCOME_PAYLOAD, headers=recruiter_headers)
    assert resp.status_code == 200
    assert resp.json()["rubric"] == {"technical_depth": 0.7, "completeness": 0.3}


def test_cors_rejects_disallowed_origin(client):
    resp = client.options(
        "/outcomes",
        headers={
            "Origin": "https://evil-site.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers.keys()}


def test_cors_allows_configured_dev_origin(client):
    resp = client.options(
        "/outcomes",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_never_wildcards_with_credentials():
    from app.config.config import config
    assert "*" not in config.CORS_ORIGINS


async def _boom(*args, **kwargs):
    raise RuntimeError("super secret internal detail: /etc/passwd db-password=hunter2")


def test_unhandled_exception_returns_generic_body_not_traceback(client, monkeypatch):
    from app.services import crud

    monkeypatch.setattr(crud, "get_outcomes", _boom)

    resp = client.get("/outcomes")
    assert resp.status_code == 500
    body = resp.json()
    assert "request_id" in body
    # The raw exception message must never leak in production; in dev mode it's
    # shown for debuggability but must still not have leaked in the 500 above
    # from a genuinely secret-looking path — assert the response is JSON-shaped
    # with a bounded, structured body rather than a raw stack trace string.
    assert isinstance(body.get("detail"), str)
    assert "Traceback" not in body["detail"]


def test_unhandled_exception_production_mode_hides_details(client, monkeypatch):
    from app.services import crud
    from app.config import config as config_module

    monkeypatch.setattr(crud, "get_outcomes", _boom)
    monkeypatch.setattr(config_module.config, "IS_PRODUCTION", True)

    resp = client.get("/outcomes")
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "Internal server error"
    assert "secret" not in body["detail"]


def test_invalid_outcome_payload_returns_422_not_500(client, recruiter_headers):
    resp = client.post("/outcomes", json={"id": "bad", "title": "t"}, headers=recruiter_headers)
    assert resp.status_code == 422


def test_page_size_is_capped(client):
    resp = client.get("/outcomes?page=1&page_size=99999")
    assert resp.status_code == 422  # exceeds the max page_size bound


def test_github_url_validation_rejects_non_github_host(client, candidate_a_headers):
    # Guards against the repo-preview endpoint being used to probe arbitrary hosts.
    resp = client.get("/plugin/repo-preview", params={"repo_url": "http://169.254.169.254/latest/meta-data/"}, headers=candidate_a_headers)
    assert resp.status_code == 400


def test_repo_preview_requires_auth(client):
    resp = client.get("/plugin/repo-preview", params={"repo_url": "https://github.com/octocat/Hello-World"})
    assert resp.status_code == 401


def test_public_job_page_hides_non_public_outcome(client, recruiter_headers, db):
    client.post("/outcomes", json={
        "id": "seo-private-outcome",
        "title": "Secret Role",
        "description": "d",
        "tasks": [],
        "rubric": {},
    }, headers=recruiter_headers)

    client.portal.call(
        db.outcomes.update_one,
        {"_id": "seo-private-outcome"},
        {"$set": {"is_public": False}},
    )

    resp = client.get("/jobs/seo-private-outcome/secret-role", follow_redirects=False)
    assert resp.status_code == 404


def test_sitemap_only_lists_public_outcomes(client, recruiter_headers, db):
    client.post("/outcomes", json={
        "id": "seo-sitemap-outcome",
        "title": "Sitemap Role",
        "description": "d",
        "tasks": [],
        "rubric": {},
    }, headers=recruiter_headers)

    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "seo-sitemap-outcome" in resp.text

    client.portal.call(
        db.outcomes.update_one,
        {"_id": "seo-sitemap-outcome"},
        {"$set": {"is_public": False}},
    )

    resp2 = client.get("/sitemap.xml")
    assert "seo-sitemap-outcome" not in resp2.text


def test_duplicate_registration_does_not_leak_mongo_error(client):
    payload = {"email": "dup-mongo@example.com", "password": "password123", "role": "recruiter"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 400
    assert "E11000" not in resp.json()["detail"]


def test_invalid_object_id_in_token_subject_is_401_not_500(client):
    import jwt
    import datetime
    from app.config.config import config

    token = jwt.encode(
        {"sub": "not-a-valid-object-id", "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)},
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM,
    )
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
