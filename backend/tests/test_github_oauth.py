from urllib.parse import urlparse, parse_qs

from conftest import register_and_login


def _configure_oauth(monkeypatch):
    from app.config.config import config
    monkeypatch.setattr(config, "GITHUB_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(config, "GITHUB_OAUTH_CLIENT_SECRET", "test-client-secret")


def _mock_github_identity(monkeypatch, github_id, login, email="octo-user@example.com", name="Octo User"):
    from app.services import github_oauth

    monkeypatch.setattr(github_oauth, "exchange_code_for_token", lambda code: "fake-access-token")
    monkeypatch.setattr(
        github_oauth, "fetch_github_user",
        lambda token: {"id": github_id, "login": login, "name": name, "avatar_url": None},
    )
    monkeypatch.setattr(github_oauth, "fetch_github_primary_email", lambda token: email)


def _query(url: str) -> dict:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def _capture_otp(monkeypatch):
    """Monkeypatch send_email in the auth route module and return a mutable
    dict that gets populated with the last email's body once it's sent."""
    captured = {}

    def fake_send_email(to_email, subject, body):
        captured["to"] = to_email
        captured["body"] = body
        return True

    monkeypatch.setattr("app.routes.auth.send_email", fake_send_email)
    return captured


def _extract_otp(body: str) -> str:
    line = next(l for l in body.splitlines() if "verification code is:" in l)
    return line.split(":")[-1].strip()


def _get_pending(client, monkeypatch, github_id, login, email="octo-user@example.com"):
    """Drives GitHub OAuth through to the pending-record stage (no OTP sent
    yet) and returns (pending_token, dest_query_params)."""
    _mock_github_identity(monkeypatch, github_id=github_id, login=login, email=email)
    login_resp = client.get("/auth/github/login", follow_redirects=False)
    state = _query(login_resp.headers["location"])["state"]
    cb = client.get(f"/auth/github/callback?code=fakecode&state={state}", follow_redirects=False)
    dest = _query(cb.headers["location"])
    return dest.get("pending"), dest


def _get_pending_connect(client, monkeypatch, headers, github_id, login):
    _mock_github_identity(monkeypatch, github_id=github_id, login=login)
    connect_resp = client.get("/auth/github/connect", headers=headers, follow_redirects=False)
    state = _query(connect_resp.json()["authorize_url"])["state"]
    cb = client.get(f"/auth/github/callback?code=fakecode&state={state}", follow_redirects=False)
    dest = _query(cb.headers["location"])
    return dest.get("pending"), dest


def _do_github_login(client, monkeypatch, github_id, login, email="octo-user@example.com"):
    """Full happy path through email confirmation, returning (pending_token, otp, dest)."""
    pending, dest = _get_pending(client, monkeypatch, github_id, login, email)
    captured = _capture_otp(monkeypatch)
    confirm = client.post("/auth/github/confirm-email", json={"pending_token": pending, "email": email, "github_username": login})
    assert confirm.status_code == 200, confirm.text
    return pending, _extract_otp(captured["body"]), dest


def _do_github_connect(client, monkeypatch, headers, github_id, login):
    account_email = client.get("/auth/me", headers=headers).json()["email"]
    pending, dest = _get_pending_connect(client, monkeypatch, headers, github_id, login)
    captured = _capture_otp(monkeypatch)
    confirm = client.post("/auth/github/confirm-email", json={"pending_token": pending, "email": account_email, "github_username": login})
    assert confirm.status_code == 200, confirm.text
    return pending, _extract_otp(captured["body"]), dest


def test_github_login_not_configured_returns_503(client):
    resp = client.get("/auth/github/login", follow_redirects=False)
    assert resp.status_code == 503


def test_github_login_redirects_to_github_when_configured(client, monkeypatch):
    _configure_oauth(monkeypatch)
    resp = client.get("/auth/github/login", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].startswith("https://github.com/login/oauth/authorize")


def test_github_connect_requires_auth(client, monkeypatch):
    _configure_oauth(monkeypatch)
    resp = client.get("/auth/github/connect", follow_redirects=False)
    assert resp.status_code == 401


def test_github_connect_returns_authorize_url_when_authenticated(client, monkeypatch, recruiter_headers):
    _configure_oauth(monkeypatch)
    resp = client.get("/auth/github/connect", headers=recruiter_headers, follow_redirects=False)
    assert resp.status_code == 200
    assert resp.json()["authorize_url"].startswith("https://github.com/login/oauth/authorize")


def test_github_callback_does_not_send_otp_before_email_confirmed(client, monkeypatch):
    """The core ask: after GitHub identifies the account, no OTP goes out and
    nothing is created until the candidate first types the email connected to
    that GitHub account. Merely having an authenticated GitHub session (e.g.
    on a shared/unlocked laptop) must not be enough by itself."""
    _configure_oauth(monkeypatch)
    captured = _capture_otp(monkeypatch)
    pending, dest = _get_pending(client, monkeypatch, github_id=777001, login="notyetreal", email="notyetreal@example.com")

    assert pending is not None
    assert dest["flow"] == "signup"
    assert captured == {}  # no email sent yet

    # OTP verification must also be refused — no OTP was ever issued for this pending record.
    resp = client.post("/auth/github/verify-otp", json={"pending_token": pending, "otp": "000000"})
    assert resp.status_code == 400

    # No account should exist yet.
    login_attempt = client.post("/auth/login", json={"email": "notyetreal@example.com", "password": "irrelevant"})
    assert login_attempt.status_code == 401


def test_github_confirm_email_wrong_email_rejected_and_sends_nothing(client, monkeypatch):
    _configure_oauth(monkeypatch)
    captured = _capture_otp(monkeypatch)
    pending, dest = _get_pending(client, monkeypatch, github_id=777002, login="realghuser", email="real-email@example.com")

    resp = client.post("/auth/github/confirm-email", json={"pending_token": pending, "email": "totally-unrelated@example.com", "github_username": "realghuser"})
    assert resp.status_code == 400
    assert captured == {}  # never sent — wrong email must not trigger an OTP


def test_github_confirm_email_correct_email_sends_otp(client, monkeypatch):
    _configure_oauth(monkeypatch)
    pending, otp, dest = _do_github_login(client, monkeypatch, github_id=777002, login="realghuser", email="real-email@example.com")
    assert otp and len(otp) == 6


def test_github_confirm_email_is_case_insensitive(client, monkeypatch):
    _configure_oauth(monkeypatch)
    pending, dest = _get_pending(client, monkeypatch, github_id=777020, login="caseuser", email="Mixed-Case@Example.com")
    captured = _capture_otp(monkeypatch)
    resp = client.post("/auth/github/confirm-email", json={"pending_token": pending, "email": "mixed-case@example.com", "github_username": "CaseUser"})
    assert resp.status_code == 200
    assert captured.get("to") == "Mixed-Case@Example.com"


def test_github_confirm_email_wrong_username_rejected_even_with_correct_email(client, monkeypatch):
    _configure_oauth(monkeypatch)
    captured = _capture_otp(monkeypatch)
    pending, dest = _get_pending(client, monkeypatch, github_id=777023, login="realusername", email="realusername@example.com")

    resp = client.post("/auth/github/confirm-email", json={"pending_token": pending, "email": "realusername@example.com", "github_username": "wrongusername"})
    assert resp.status_code == 400
    assert captured == {}  # never sent — wrong username must not trigger an OTP, even with the right email


def test_github_confirm_email_lockout_after_too_many_wrong_attempts(client, monkeypatch):
    from app.config.config import config
    _configure_oauth(monkeypatch)
    monkeypatch.setattr(config, "GITHUB_EMAIL_CONFIRM_MAX_ATTEMPTS", 2)
    pending, dest = _get_pending(client, monkeypatch, github_id=777021, login="lockoutemail", email="lockout@example.com")

    for _ in range(2):
        resp = client.post("/auth/github/confirm-email", json={"pending_token": pending, "email": "wrong@example.com", "github_username": "lockoutemail"})
        assert resp.status_code == 400

    resp = client.post("/auth/github/confirm-email", json={"pending_token": pending, "email": "lockout@example.com", "github_username": "lockoutemail"})
    assert resp.status_code == 429


def test_github_confirm_email_cannot_be_reconfirmed(client, monkeypatch):
    _configure_oauth(monkeypatch)
    pending, otp, dest = _do_github_login(client, monkeypatch, github_id=777022, login="reconfirmuser", email="reconfirm@example.com")

    resp = client.post("/auth/github/confirm-email", json={"pending_token": pending, "email": "reconfirm@example.com", "github_username": "reconfirmuser"})
    assert resp.status_code == 400


def test_github_verify_otp_wrong_code_rejected(client, monkeypatch):
    _configure_oauth(monkeypatch)
    pending, otp, dest = _do_github_login(client, monkeypatch, github_id=777003, login="wrongcodeuser")

    resp = client.post("/auth/github/verify-otp", json={"pending_token": pending, "otp": "000000"})
    assert resp.status_code == 400


def test_github_verify_otp_correct_code_creates_account_and_logs_in(client, monkeypatch):
    _configure_oauth(monkeypatch)
    pending, otp, dest = _do_github_login(client, monkeypatch, github_id=777004, login="realuser", email="realuser@example.com")

    resp = client.post("/auth/github/verify-otp", json={"pending_token": pending, "otp": otp})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "realuser@example.com"
    assert body["github_username"] == "realuser"
    assert body["role"] == "candidate"


def test_github_otp_is_single_use(client, monkeypatch):
    _configure_oauth(monkeypatch)
    pending, otp, dest = _do_github_login(client, monkeypatch, github_id=777005, login="singleuse")

    first = client.post("/auth/github/verify-otp", json={"pending_token": pending, "otp": otp})
    assert first.status_code == 200

    second = client.post("/auth/github/verify-otp", json={"pending_token": pending, "otp": otp})
    assert second.status_code == 400


def test_github_otp_lockout_after_too_many_wrong_attempts(client, monkeypatch):
    from app.config.config import config
    _configure_oauth(monkeypatch)
    monkeypatch.setattr(config, "GITHUB_OTP_MAX_ATTEMPTS", 2)
    pending, otp, dest = _do_github_login(client, monkeypatch, github_id=777006, login="lockoutuser")

    for _ in range(2):
        resp = client.post("/auth/github/verify-otp", json={"pending_token": pending, "otp": "000000"})
        assert resp.status_code == 400

    resp = client.post("/auth/github/verify-otp", json={"pending_token": pending, "otp": otp})
    assert resp.status_code == 429


def test_github_login_existing_linked_user_requires_email_and_otp_too(client, monkeypatch):
    _configure_oauth(monkeypatch)
    # First-time signup + verify to create the account.
    pending1, otp1, _ = _do_github_login(client, monkeypatch, github_id=777007, login="returninguser", email="returning@example.com")
    first_login = client.post("/auth/github/verify-otp", json={"pending_token": pending1, "otp": otp1})
    user_id_1 = client.get("/auth/me", headers={"Authorization": f"Bearer {first_login.json()['access_token']}"}).json()["id"]

    # Second login with the same GitHub identity must ALSO require a fresh
    # email confirmation + OTP — it must not skip straight to a token just
    # because the account already exists and is linked.
    pending2, otp2, dest2 = _do_github_login(client, monkeypatch, github_id=777007, login="returninguser", email="returning@example.com")
    assert dest2["flow"] == "login"
    assert pending2 != pending1

    second_login = client.post("/auth/github/verify-otp", json={"pending_token": pending2, "otp": otp2})
    assert second_login.status_code == 200
    user_id_2 = client.get("/auth/me", headers={"Authorization": f"Bearer {second_login.json()['access_token']}"}).json()["id"]
    assert user_id_1 == user_id_2


def test_github_login_rejected_for_recruiter_with_linked_github(client, monkeypatch, recruiter_headers):
    """"Continue with GitHub" is a candidate-only login path — a recruiter who
    has linked GitHub still can't use it as a login shortcut."""
    _configure_oauth(monkeypatch)

    # Recruiter connects GitHub to their existing account.
    pending, otp, _ = _do_github_connect(client, monkeypatch, recruiter_headers, github_id=777013, login="recruiter-gh")
    connect_resp = client.post("/auth/github/verify-otp", json={"pending_token": pending, "otp": otp})
    assert connect_resp.status_code == 200

    # Now try to use "Continue with GitHub" to log in with that same identity.
    captured = _capture_otp(monkeypatch)
    pending2, dest2 = _get_pending(client, monkeypatch, github_id=777013, login="recruiter-gh")

    assert dest2.get("error") == "github_login_candidates_only"
    assert "pending" not in dest2
    assert captured == {}


def test_github_login_still_works_for_candidate_with_linked_github(client, monkeypatch, candidate_a_headers):
    _configure_oauth(monkeypatch)

    # candidate_a_headers fixture already connects GitHub as "octocat" via a
    # direct DB write (not through the OAuth+OTP flow) — that's fine here,
    # this test only cares that the *login* path accepts a candidate.
    pending, dest = _get_pending(client, monkeypatch, github_id=900001, login="octocat")

    assert dest.get("pending") is not None
    assert "error" not in dest


def test_github_oauth_state_is_single_use(client, monkeypatch):
    _configure_oauth(monkeypatch)
    pending, dest = _get_pending(client, monkeypatch, github_id=777008, login="onceonly")
    assert dest.get("pending") is not None

    _mock_github_identity(monkeypatch, github_id=777008, login="onceonly")
    login_resp = client.get("/auth/github/login", follow_redirects=False)
    state = _query(login_resp.headers["location"])["state"]
    client.get(f"/auth/github/callback?code=fakecode&state={state}", follow_redirects=False)

    second = client.get(f"/auth/github/callback?code=fakecode&state={state}", follow_redirects=False)
    assert "error=" in second.headers["location"]


def test_github_connect_flow_requires_email_confirmation_against_account_email_not_github_email(client, monkeypatch, recruiter_headers):
    """This is the actual point of the whole feature: both the email
    confirmation AND the OTP go to the ALREADY-LOGGED-IN account's own email —
    proving the person at the keyboard controls that inbox — not to whatever
    email GitHub reports, and not to anything they type that doesn't match."""
    _configure_oauth(monkeypatch)
    pending, dest = _get_pending_connect(client, monkeypatch, recruiter_headers, github_id=777009, login="linkeduser")
    assert dest["flow"] == "connect"

    # Typing GitHub's (mocked) email instead of the account's real email must fail.
    wrong = client.post("/auth/github/confirm-email", json={"pending_token": pending, "email": "octo-user@example.com", "github_username": "linkeduser"})
    assert wrong.status_code == 400

    me_before = client.get("/auth/me", headers=recruiter_headers)
    assert me_before.json()["github_username"] is None

    account_email = me_before.json()["email"]
    captured = _capture_otp(monkeypatch)
    right = client.post("/auth/github/confirm-email", json={"pending_token": pending, "email": account_email, "github_username": "linkeduser"})
    assert right.status_code == 200
    otp = _extract_otp(captured["body"])

    resp = client.post("/auth/github/verify-otp", json={"pending_token": pending, "otp": otp})
    assert resp.status_code == 200
    assert resp.json()["connected"] is True

    me_after = client.get("/auth/me", headers=recruiter_headers)
    assert me_after.json()["github_username"] == "linkeduser"


def test_github_connect_flow_rejects_github_account_already_linked_elsewhere(client, monkeypatch, recruiter_headers, other_recruiter_headers):
    _configure_oauth(monkeypatch)

    pending1, otp1, _ = _do_github_connect(client, monkeypatch, recruiter_headers, github_id=777010, login="shared-identity")
    r1 = client.post("/auth/github/verify-otp", json={"pending_token": pending1, "otp": otp1})
    assert r1.status_code == 200

    # A second, different account tries to link the SAME GitHub identity.
    # Rejected during the callback itself, before email confirmation / any OTP
    # is even sent — no point going further for a link that's already invalid.
    captured = _capture_otp(monkeypatch)
    pending2, dest2 = _get_pending_connect(client, monkeypatch, other_recruiter_headers, github_id=777010, login="shared-identity")
    assert dest2.get("error") == "github_already_linked"
    assert captured == {}

    me2 = client.get("/auth/me", headers=other_recruiter_headers)
    assert me2.json()["github_username"] is None


def test_github_verify_otp_connect_rejects_reuse_of_github_id_between_pending_creation_and_verification(
    client, monkeypatch, recruiter_headers, other_recruiter_headers
):
    """Both users get as far as receiving an OTP (a legitimate race — neither
    request was invalid when it was made) but only the first verification may
    actually complete the link."""
    _configure_oauth(monkeypatch)

    pending1, otp1, _ = _do_github_connect(client, monkeypatch, recruiter_headers, github_id=777012, login="race-identity")
    pending2, otp2, _ = _do_github_connect(client, monkeypatch, other_recruiter_headers, github_id=777012, login="race-identity")

    r1 = client.post("/auth/github/verify-otp", json={"pending_token": pending1, "otp": otp1})
    assert r1.status_code == 200

    r2 = client.post("/auth/github/verify-otp", json={"pending_token": pending2, "otp": otp2})
    assert r2.status_code == 409

    me2 = client.get("/auth/me", headers=other_recruiter_headers)
    assert me2.json()["github_username"] is None


def test_github_signup_does_not_take_over_existing_password_account(client, monkeypatch):
    _configure_oauth(monkeypatch)
    # Created directly (not via /auth/register, which now requires GitHub
    # verification for candidates) — this test only cares that a GitHub
    # signup with the same email can't silently take the account over.
    register_and_login(client, "victim@example.com", password="originalpass123", role="candidate")

    captured = _capture_otp(monkeypatch)
    pending, dest = _get_pending(client, monkeypatch, github_id=777011, login="attacker-gh", email="victim@example.com")

    assert dest.get("error") == "email_already_registered"
    assert captured == {}

    # The original account must still log in with its original password, unaffected.
    login = client.post("/auth/login", json={"email": "victim@example.com", "password": "originalpass123"})
    assert login.status_code == 200


def test_github_signup_without_available_email_is_rejected_cleanly(client, monkeypatch):
    _configure_oauth(monkeypatch)
    from app.services import github_oauth

    monkeypatch.setattr(github_oauth, "exchange_code_for_token", lambda code: "fake-access-token")
    monkeypatch.setattr(
        github_oauth, "fetch_github_user",
        lambda token: {"id": 777099, "login": "noemailuser", "name": None, "avatar_url": None},
    )
    monkeypatch.setattr(github_oauth, "fetch_github_primary_email", lambda token: None)

    login_resp = client.get("/auth/github/login", follow_redirects=False)
    state = _query(login_resp.headers["location"])["state"]
    cb = client.get(f"/auth/github/callback?code=fakecode&state={state}", follow_redirects=False)
    assert "error=github_email_required" in cb.headers["location"]


def test_verify_otp_with_unknown_pending_token_returns_400(client):
    resp = client.post("/auth/github/verify-otp", json={"pending_token": "does-not-exist", "otp": "123456"})
    assert resp.status_code == 400


def test_confirm_email_with_unknown_pending_token_returns_400(client):
    resp = client.post("/auth/github/confirm-email", json={"pending_token": "does-not-exist", "email": "a@b.com", "github_username": "someone"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Candidate password sign-up that requires proving ownership of the claimed
# GitHub username (POST /auth/register/candidate/start, flow=register_verify)
# ---------------------------------------------------------------------------

def _get_pending_register(client, monkeypatch, github_id, login, email="signup-candidate@example.com",
                           password="password123", full_name="Signup Candidate", claimed_username=None):
    _mock_github_identity(monkeypatch, github_id=github_id, login=login)
    start = client.post("/auth/register/candidate/start", json={
        "email": email, "password": password, "full_name": full_name,
        "github_username": claimed_username if claimed_username is not None else login,
    })
    assert start.status_code == 200, start.text
    state = _query(start.json()["authorize_url"])["state"]
    cb = client.get(f"/auth/github/callback?code=fakecode&state={state}", follow_redirects=False)
    dest = _query(cb.headers["location"])
    return dest.get("pending"), dest


def test_register_candidate_start_not_configured_returns_503(client):
    resp = client.post("/auth/register/candidate/start", json={
        "email": "x@example.com", "password": "password123", "github_username": "someone",
    })
    assert resp.status_code == 503


def test_register_candidate_start_rejects_duplicate_email(client, monkeypatch, recruiter_headers):
    _configure_oauth(monkeypatch)
    account_email = client.get("/auth/me", headers=recruiter_headers).json()["email"]
    resp = client.post("/auth/register/candidate/start", json={
        "email": account_email, "password": "password123", "github_username": "someone",
    })
    assert resp.status_code == 400


def test_register_candidate_flow_happy_path_creates_account_with_password_and_github_linked(client, monkeypatch):
    _configure_oauth(monkeypatch)
    pending, dest = _get_pending_register(
        client, monkeypatch, github_id=778001, login="newcandidate", email="newcandidate@example.com",
    )
    assert dest["flow"] == "register_verify"

    captured = _capture_otp(monkeypatch)
    confirm = client.post("/auth/github/confirm-email", json={
        "pending_token": pending, "email": "newcandidate@example.com", "github_username": "newcandidate",
    })
    assert confirm.status_code == 200, confirm.text
    otp = _extract_otp(captured["body"])

    verify = client.post("/auth/github/verify-otp", json={"pending_token": pending, "otp": otp})
    assert verify.status_code == 200
    token = verify.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "newcandidate@example.com"
    assert body["github_username"] == "newcandidate"
    assert body["role"] == "candidate"

    # The password they chose at sign-up actually works.
    login = client.post("/auth/login", json={"email": "newcandidate@example.com", "password": "password123"})
    assert login.status_code == 200


def test_register_candidate_flow_rejects_claimed_username_that_does_not_match_github(client, monkeypatch):
    _configure_oauth(monkeypatch)
    captured = _capture_otp(monkeypatch)
    pending, dest = _get_pending_register(
        client, monkeypatch, github_id=778002, login="realaccount", email="mismatch@example.com",
        claimed_username="someone-elses-name",
    )
    assert dest.get("error") == "github_username_mismatch"
    assert "pending" not in dest
    assert captured == {}

    # No account should have been created.
    login = client.post("/auth/login", json={"email": "mismatch@example.com", "password": "password123"})
    assert login.status_code == 401


def test_register_candidate_flow_rejects_github_account_already_linked_elsewhere(client, monkeypatch, candidate_a_headers):
    _configure_oauth(monkeypatch)
    # candidate_a_headers is already linked to github_id=900001 (see conftest).
    captured = _capture_otp(monkeypatch)
    pending, dest = _get_pending_register(
        client, monkeypatch, github_id=900001, login="octocat", email="second-signup@example.com",
    )
    assert dest.get("error") == "github_already_linked"
    assert captured == {}

    login = client.post("/auth/login", json={"email": "second-signup@example.com", "password": "password123"})
    assert login.status_code == 401


def test_register_candidate_flow_state_is_single_use(client, monkeypatch):
    _configure_oauth(monkeypatch)
    _mock_github_identity(monkeypatch, github_id=778003, login="onceuser")
    start = client.post("/auth/register/candidate/start", json={
        "email": "onceuser@example.com", "password": "password123", "github_username": "onceuser",
    })
    state = _query(start.json()["authorize_url"])["state"]

    first = client.get(f"/auth/github/callback?code=fakecode&state={state}", follow_redirects=False)
    assert _query(first.headers["location"]).get("pending") is not None

    second = client.get(f"/auth/github/callback?code=fakecode&state={state}", follow_redirects=False)
    assert "error=" in second.headers["location"]
