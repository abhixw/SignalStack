from app.services import leetcode


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data


def test_fetch_user_stats_returns_parsed_fields(monkeypatch):
    def fake_post(url, json, headers, timeout):
        assert url == "https://leetcode.com/graphql"
        assert json["variables"]["username"] == "someuser"
        return _FakeResponse({
            "data": {
                "matchedUser": {
                    "username": "someuser",
                    "submitStatsGlobal": {
                        "acSubmissionNum": [
                            {"difficulty": "All", "count": 150},
                            {"difficulty": "Easy", "count": 80},
                            {"difficulty": "Medium", "count": 60},
                            {"difficulty": "Hard", "count": 10},
                        ]
                    },
                    "profile": {"ranking": 12345},
                }
            }
        })

    monkeypatch.setattr(leetcode.requests, "post", fake_post)
    stats = leetcode.fetch_user_stats("someuser")
    assert stats == {
        "username": "someuser",
        "ranking": 12345,
        "solved": {"easy": 80, "medium": 60, "hard": 10, "all": 150},
    }


def test_fetch_user_stats_unknown_username_returns_none(monkeypatch):
    def fake_post(url, json, headers, timeout):
        return _FakeResponse({"data": {"matchedUser": None}})

    monkeypatch.setattr(leetcode.requests, "post", fake_post)
    assert leetcode.fetch_user_stats("ghost") is None


def test_fetch_user_stats_non_200_returns_none(monkeypatch):
    def fake_post(url, json, headers, timeout):
        return _FakeResponse({}, status_code=429)

    monkeypatch.setattr(leetcode.requests, "post", fake_post)
    assert leetcode.fetch_user_stats("someuser") is None


def test_fetch_user_stats_malformed_response_returns_none(monkeypatch):
    def fake_post(url, json, headers, timeout):
        return _FakeResponse({"unexpected": "shape"})

    monkeypatch.setattr(leetcode.requests, "post", fake_post)
    assert leetcode.fetch_user_stats("someuser") is None


def test_fetch_user_stats_network_error_returns_none(monkeypatch):
    import requests as requests_module

    def fake_post(url, json, headers, timeout):
        raise requests_module.exceptions.ConnectionError("boom")

    monkeypatch.setattr(leetcode.requests, "post", fake_post)
    assert leetcode.fetch_user_stats("someuser") is None
