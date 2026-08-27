def test_register_creates_recruiter_when_requested(client):
    resp = client.post("/auth/register", json={
        "email": "newuser@example.com", "password": "password123", "role": "recruiter",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "recruiter"
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_rejects_candidate_role(client):
    # Candidates must prove ownership of a real GitHub account instead —
    # see POST /auth/register/candidate/start. This endpoint now only
    # creates recruiter accounts.
    resp = client.post("/auth/register", json={
        "email": "candidate@example.com", "password": "password123", "role": "candidate",
    })
    assert resp.status_code == 400


def test_register_defaults_to_candidate_role_and_is_rejected(client):
    resp = client.post("/auth/register", json={
        "email": "no-role@example.com", "password": "password123",
    })
    assert resp.status_code == 400


def test_register_rejects_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "password123", "role": "recruiter"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400


def test_register_cannot_self_assign_admin(client):
    resp = client.post("/auth/register", json={
        "email": "wannabe-admin@example.com", "password": "password123", "role": "admin",
    })
    assert resp.status_code == 400


def test_register_rejects_short_password(client):
    resp = client.post("/auth/register", json={
        "email": "shortpw@example.com", "password": "short", "role": "recruiter",
    })
    assert resp.status_code == 422


def test_login_success_returns_bearer_token(client):
    client.post("/auth/register", json={"email": "login-ok@example.com", "password": "password123", "role": "recruiter"})
    resp = client.post("/auth/login", json={"email": "login-ok@example.com", "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_invalid_password_returns_401(client):
    client.post("/auth/register", json={"email": "login-bad@example.com", "password": "password123", "role": "recruiter"})
    resp = client.post("/auth/login", json={"email": "login-bad@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client):
    resp = client.post("/auth/login", json={"email": "does-not-exist@example.com", "password": "whatever123"})
    assert resp.status_code == 401


def test_protected_endpoint_without_token_returns_401(client):
    resp = client.get("/admin/audit-logs")
    assert resp.status_code == 401


def test_protected_endpoint_with_garbage_token_returns_401(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer this.is.not.a.jwt"})
    assert resp.status_code == 401


def test_protected_endpoint_with_expired_token_returns_401(client):
    import jwt
    import datetime
    from app.config.config import config

    expired = jwt.encode(
        {"sub": "some-user-id", "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)},
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM,
    )
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


def test_me_returns_current_user(client):
    client.post("/auth/register", json={"email": "me-check@example.com", "password": "password123", "role": "recruiter", "full_name": "Me Check"})
    login = client.post("/auth/login", json={"email": "me-check@example.com", "password": "password123"})
    token = login.json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me-check@example.com"
