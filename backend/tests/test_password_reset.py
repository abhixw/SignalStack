# Tests can't read real email, and only the OTP's hash is stored in the DB —
# so every test that needs the actual code monkeypatches `send_email` to
# capture the message body it would have sent, then extracts the OTP from it.

def test_forgot_password_unknown_email_returns_generic_message(client):
    resp = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert "sent" in resp.json()["message"].lower()


def test_forgot_password_known_email_sends_otp_and_returns_same_generic_message(client, monkeypatch):
    sent = {}

    def fake_send_email(to_email, subject, body):
        sent["to"] = to_email
        sent["body"] = body
        return True

    monkeypatch.setattr("app.routes.auth.send_email", fake_send_email)

    client.post("/auth/register", json={"email": "resetme@example.com", "password": "originalpass123", "role": "recruiter"})
    resp = client.post("/auth/forgot-password", json={"email": "resetme@example.com"})

    assert resp.status_code == 200
    assert "sent" in resp.json()["message"].lower()
    assert sent["to"] == "resetme@example.com"
    assert "reset code is:" in sent["body"]


def test_forgot_password_cooldown_blocks_immediate_retry(client, monkeypatch):
    monkeypatch.setattr("app.routes.auth.send_email", lambda *a, **k: True)
    client.post("/auth/register", json={"email": "cooldown@example.com", "password": "originalpass123", "role": "recruiter"})
    client.post("/auth/forgot-password", json={"email": "cooldown@example.com"})
    resp = client.post("/auth/forgot-password", json={"email": "cooldown@example.com"})
    assert resp.status_code == 429


def _extract_otp(body: str) -> str:
    line = next(l for l in body.splitlines() if "reset code is:" in l)
    return line.split(":")[-1].strip()


def test_reset_password_with_correct_otp_succeeds_and_old_password_stops_working(client, monkeypatch):
    captured = {}
    monkeypatch.setattr("app.routes.auth.send_email", lambda to, subject, body: captured.update(body=body) or True)

    client.post("/auth/register", json={"email": "flow@example.com", "password": "originalpass123", "role": "recruiter"})
    client.post("/auth/forgot-password", json={"email": "flow@example.com"})
    otp = _extract_otp(captured["body"])

    resp = client.post("/auth/reset-password", json={"email": "flow@example.com", "otp": otp, "new_password": "brandnewpass123"})
    assert resp.status_code == 200

    old_login = client.post("/auth/login", json={"email": "flow@example.com", "password": "originalpass123"})
    assert old_login.status_code == 401

    new_login = client.post("/auth/login", json={"email": "flow@example.com", "password": "brandnewpass123"})
    assert new_login.status_code == 200


def test_reset_password_wrong_otp_rejected(client, monkeypatch):
    monkeypatch.setattr("app.routes.auth.send_email", lambda *a, **k: True)
    client.post("/auth/register", json={"email": "wrongotp@example.com", "password": "originalpass123", "role": "recruiter"})
    client.post("/auth/forgot-password", json={"email": "wrongotp@example.com"})

    resp = client.post("/auth/reset-password", json={"email": "wrongotp@example.com", "otp": "000000", "new_password": "somethingnew123"})
    assert resp.status_code == 400


def test_reset_password_otp_cannot_be_reused(client, monkeypatch):
    captured = {}
    monkeypatch.setattr("app.routes.auth.send_email", lambda to, subject, body: captured.update(body=body) or True)

    client.post("/auth/register", json={"email": "reuse@example.com", "password": "originalpass123", "role": "recruiter"})
    client.post("/auth/forgot-password", json={"email": "reuse@example.com"})
    otp = _extract_otp(captured["body"])

    first = client.post("/auth/reset-password", json={"email": "reuse@example.com", "otp": otp, "new_password": "firstnewpass123"})
    assert first.status_code == 200

    second = client.post("/auth/reset-password", json={"email": "reuse@example.com", "otp": otp, "new_password": "secondnewpass123"})
    assert second.status_code == 400


def test_reset_password_too_many_wrong_attempts_locks_out(client, monkeypatch):
    from app.config.config import config

    monkeypatch.setattr("app.routes.auth.send_email", lambda *a, **k: True)
    monkeypatch.setattr(config, "PASSWORD_RESET_MAX_ATTEMPTS", 2)

    client.post("/auth/register", json={"email": "lockout@example.com", "password": "originalpass123", "role": "recruiter"})
    client.post("/auth/forgot-password", json={"email": "lockout@example.com"})

    for _ in range(2):
        resp = client.post("/auth/reset-password", json={"email": "lockout@example.com", "otp": "000000", "new_password": "x12345678"})
        assert resp.status_code == 400

    resp = client.post("/auth/reset-password", json={"email": "lockout@example.com", "otp": "000000", "new_password": "x12345678"})
    assert resp.status_code == 429


def test_reset_password_unknown_email_returns_generic_invalid(client):
    resp = client.post("/auth/reset-password", json={"email": "never-requested@example.com", "otp": "123456", "new_password": "somethingnew123"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid or expired code."
