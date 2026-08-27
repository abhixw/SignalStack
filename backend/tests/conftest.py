import os
import sys

import pytest

# ENVIRONMENT=test forces config.MONGODB_ACTIVE_DATABASE to MONGODB_TEST_DATABASE
# regardless of what MONGODB_DATABASE is set to — a test run can never write into
# the real database even if this file is misconfigured. Must be set before
# `app.main` (and therefore `app.config.config`) is imported.
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ["MONGODB_TEST_DATABASE"] = "signaxai_test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-do-not-use-in-production-0123456789abcdef"
os.environ["DEMO_MODE"] = "false"
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("GITHUB_TOKEN", "")
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
# Force-blank (not setdefault): a real GITHUB_OAUTH_CLIENT_ID/SECRET in the
# developer's own .env must never leak into the test run — tests that need
# "configured" explicitly monkeypatch these back on a per-test basis.
os.environ["GITHUB_OAUTH_CLIENT_ID"] = ""
os.environ["GITHUB_OAUTH_CLIENT_SECRET"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import database as db_module  # noqa: E402
from app.config.config import config  # noqa: E402
from app.main import app  # noqa: E402
from app.services import crud  # noqa: E402
from app.services.auth import hash_password  # noqa: E402

assert config.MONGODB_ACTIVE_DATABASE == "signaxai_test", (
    "Refusing to run tests — active database is not the test database."
)


@pytest.fixture(scope="session")
def client():
    """One TestClient for the whole session. Using it as a context manager
    runs the app's real FastAPI `lifespan` (connect_to_mongo/close_mongo_connection)
    on the SAME event loop TestClient uses for every request — required because
    PyMongo's AsyncMongoClient is bound to the loop it was created on and errors
    if used from a different one (verified empirically before writing this)."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


async def _truncate_all():
    db = db_module.get_database()
    for name in await db.list_collection_names():
        await db[name].delete_many({})


@pytest.fixture(autouse=True)
def _clean_collections(client):
    """Truncate all collections before each test, run on the app's own loop
    via the TestClient portal (see note on `client` above)."""
    client.portal.call(_truncate_all)
    yield


@pytest.fixture()
def db():
    """Direct Mongo access for tests that need to manipulate state the API
    doesn't expose (e.g. flipping `is_public` on an outcome). Any operations
    on it must be run via `client.portal.call(...)`, not awaited directly —
    see test_security.py for the pattern."""
    return db_module.get_database()


def register_and_login(client, email, password="testpass123", role="candidate", full_name=None):
    if role == "candidate":
        # Candidate self-registration now requires proving ownership of a real
        # GitHub account (POST /auth/register/candidate/start), which there's
        # no way to drive in tests — so test candidates are created directly,
        # same rationale as _connect_github/_promote_to_admin below.
        client.portal.call(
            crud.create_user, db_module.get_database(), email, hash_password(password), role, full_name,
        )
    else:
        client.post("/auth/register", json={
            "email": email, "password": password, "role": role, "full_name": full_name,
        })
    resp = client.post("/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def recruiter_headers(client):
    return register_and_login(client, "recruiter@example.com", role="recruiter")


@pytest.fixture()
def other_recruiter_headers(client):
    return register_and_login(client, "recruiter2@example.com", role="recruiter")


async def _connect_github(email: str, github_username: str, github_id: int):
    db = db_module.get_database()
    await db.users.update_one(
        {"email": email},
        {"$set": {"github_username": github_username, "github_id": github_id}},
    )


@pytest.fixture()
def candidate_a_headers(client):
    headers = register_and_login(client, "candidate-a@example.com", role="candidate")
    # "octocat" matches the repo owner used by every existing proof-submission
    # test fixture/payload (github.com/octocat/...) — connected via direct DB
    # write since there's no way to drive real GitHub OAuth in tests.
    client.portal.call(_connect_github, "candidate-a@example.com", "octocat", 900001)
    return headers


@pytest.fixture()
def candidate_b_headers(client):
    headers = register_and_login(client, "candidate-b@example.com", role="candidate")
    client.portal.call(_connect_github, "candidate-b@example.com", "octocat", 900002)
    return headers


@pytest.fixture()
def candidate_no_github_headers(client):
    """A candidate who has registered but NOT connected GitHub — for testing
    that proof submission is blocked until they do."""
    return register_and_login(client, "candidate-no-github@example.com", role="candidate")


async def _promote_to_admin(email: str):
    db = db_module.get_database()
    await db.users.update_one({"email": email}, {"$set": {"role": "admin"}})


@pytest.fixture()
def admin_headers(client):
    headers = register_and_login(client, "admin@example.com", role="candidate")  # role forced down by API
    # Promote directly in the DB — mirrors scripts/promote_admin.py, since admin
    # accounts are intentionally not reachable through the public API.
    client.portal.call(_promote_to_admin, "admin@example.com")
    resp = client.post("/auth/login", json={"email": "admin@example.com", "password": "testpass123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
