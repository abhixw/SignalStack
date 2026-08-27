import pytest

from app.services import codeforces
from app.services.errors import UpstreamServiceError


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
        self.content = b"1"

    def json(self):
        return self._json_data


def test_fetch_user_info_returns_parsed_fields(monkeypatch):
    def fake_get(url, params, timeout):
        assert url == "https://codeforces.com/api/user.info"
        assert params["handles"] == "someuser"
        return _FakeResponse({
            "status": "OK",
            "result": [{"handle": "someuser", "rating": 1500, "maxRating": 1600, "rank": "expert", "maxRank": "expert"}],
        })

    monkeypatch.setattr(codeforces.requests, "get", fake_get)
    info = codeforces.fetch_user_info("someuser")
    assert info == {"handle": "someuser", "rating": 1500, "max_rating": 1600, "rank": "expert", "max_rank": "expert"}


def test_fetch_user_info_unknown_handle_raises_not_found(monkeypatch):
    def fake_get(url, params, timeout):
        return _FakeResponse({"status": "FAILED", "comment": "handle: User with handle ghost not found"})

    monkeypatch.setattr(codeforces.requests, "get", fake_get)
    with pytest.raises(UpstreamServiceError) as exc_info:
        codeforces.fetch_user_info("ghost")
    assert exc_info.value.error_type == "NOT_FOUND"


def test_fetch_user_info_upstream_error_raises_upstream_service_error(monkeypatch):
    def fake_get(url, params, timeout):
        return _FakeResponse({"status": "FAILED", "comment": "Something else went wrong"})

    monkeypatch.setattr(codeforces.requests, "get", fake_get)
    with pytest.raises(UpstreamServiceError) as exc_info:
        codeforces.fetch_user_info("someuser")
    assert exc_info.value.error_type == "UPSTREAM_SERVICE_ERROR"


def test_fetch_solved_problem_counts_dedupes_and_buckets_by_difficulty(monkeypatch):
    def fake_get(url, params, timeout):
        return _FakeResponse({
            "status": "OK",
            "result": [
                {"verdict": "OK", "problem": {"contestId": 1, "index": "A", "rating": 800}},
                {"verdict": "WRONG_ANSWER", "problem": {"contestId": 1, "index": "A", "rating": 800}},
                {"verdict": "OK", "problem": {"contestId": 1, "index": "A", "rating": 800}},  # duplicate solve, same problem
                {"verdict": "OK", "problem": {"contestId": 2, "index": "B", "rating": 1500}},
                {"verdict": "OK", "problem": {"contestId": 3, "index": "C", "rating": 2200}},
                {"verdict": "OK", "problem": {"contestId": 4, "index": "D", "rating": None}},
            ],
        })

    monkeypatch.setattr(codeforces.requests, "get", fake_get)
    counts = codeforces.fetch_solved_problem_counts("someuser")
    assert counts == {"easy": 1, "medium": 1, "hard": 1, "unrated": 1, "total": 4}


def test_signs_request_when_configured(monkeypatch):
    monkeypatch.setattr(codeforces.config, "CODEFORCES_API_KEY", "fake-key")
    monkeypatch.setattr(codeforces.config, "CODEFORCES_API_SECRET", "fake-secret")

    captured = {}

    def fake_get(url, params, timeout):
        captured.update(params)
        return _FakeResponse({"status": "OK", "result": [{"handle": "someuser"}]})

    monkeypatch.setattr(codeforces.requests, "get", fake_get)
    codeforces.fetch_user_info("someuser")

    assert captured["apiKey"] == "fake-key"
    assert "time" in captured
    assert "apiSig" in captured
    assert len(captured["apiSig"]) == 6 + 128  # 6-digit rand + sha512 hex digest


def test_does_not_sign_request_when_not_configured(monkeypatch):
    monkeypatch.setattr(codeforces.config, "CODEFORCES_API_KEY", None)
    monkeypatch.setattr(codeforces.config, "CODEFORCES_API_SECRET", None)

    captured = {}

    def fake_get(url, params, timeout):
        captured.update(params)
        return _FakeResponse({"status": "OK", "result": [{"handle": "someuser"}]})

    monkeypatch.setattr(codeforces.requests, "get", fake_get)
    codeforces.fetch_user_info("someuser")

    assert "apiKey" not in captured
    assert "apiSig" not in captured
