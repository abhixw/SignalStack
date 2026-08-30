import hashlib
import logging
import secrets
import time

import requests

from app.config.config import config
from app.services.errors import UpstreamServiceError, NOT_FOUND, UPSTREAM_SERVICE_ERROR, TIMEOUT

logger = logging.getLogger("recruvoskill.codeforces")

_API_BASE = "https://codeforces.com/api"
_TIMEOUT_SECONDS = 10

# (tier name, inclusive lower bound, exclusive upper bound) on Codeforces
# problem `rating` — Codeforces' own difficulty scale, not a guess.
_DIFFICULTY_TIERS = (
    ("easy", 0, 1200),
    ("medium", 1200, 1900),
    ("hard", 1900, float("inf")),
)


def _sign(method: str, params: dict) -> dict:
    """Per codeforces.com/apiHelp: apiSig = <rand><sha512 hex>, where the
    hashed string is "<rand>/<method>?<sorted params incl. apiKey & time>#<secret>".
    Only called when both CODEFORCES_API_KEY/SECRET are set — anonymous
    requests work too, just at a stricter rate limit."""
    signed_params = dict(params)
    signed_params["apiKey"] = config.CODEFORCES_API_KEY
    signed_params["time"] = str(int(time.time()))

    rand = "".join(secrets.choice("0123456789") for _ in range(6))
    param_str = "&".join(f"{k}={v}" for k, v in sorted(signed_params.items()))
    to_hash = f"{rand}/{method}?{param_str}#{config.CODEFORCES_API_SECRET}"
    api_sig = rand + hashlib.sha512(to_hash.encode("utf-8")).hexdigest()

    signed_params["apiSig"] = api_sig
    return signed_params


def _request(method: str, params: dict) -> list | dict:
    """Raises UpstreamServiceError on failure. Returns the API's `result`."""
    query = _sign(method, params) if config.CODEFORCES_API_CONFIGURED else dict(params)

    try:
        resp = requests.get(f"{_API_BASE}/{method}", params=query, timeout=_TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        raise UpstreamServiceError("codeforces", TIMEOUT, "Codeforces did not respond in time.", retryable=True, status_code=504)
    except requests.exceptions.RequestException as e:
        logger.warning("Codeforces request failed: %s", e)
        raise UpstreamServiceError("codeforces", UPSTREAM_SERVICE_ERROR, "Could not reach Codeforces.", retryable=True, status_code=502)

    data = resp.json() if resp.content else {}
    if data.get("status") != "OK":
        comment = data.get("comment", "") or ""
        if "not found" in comment.lower():
            raise UpstreamServiceError("codeforces", NOT_FOUND, "Codeforces handle not found.", retryable=False, status_code=404)
        logger.warning("Codeforces API returned an error: %s", comment)
        raise UpstreamServiceError("codeforces", UPSTREAM_SERVICE_ERROR, "Codeforces API error.", retryable=True, status_code=502)

    return data["result"]


def fetch_user_info(handle: str) -> dict:
    """Raises UpstreamServiceError (NOT_FOUND) if the handle doesn't exist."""
    result = _request("user.info", {"handles": handle})
    user = result[0]
    return {
        "handle": user.get("handle"),
        "rating": user.get("rating"),
        "max_rating": user.get("maxRating"),
        "rank": user.get("rank"),
        "max_rank": user.get("maxRank"),
    }


def fetch_solved_problem_counts(handle: str) -> dict:
    """Difficulty-tiered distinct solved-problem counts, not raw AC submission
    count — a problem solved after 5 failed attempts still counts once."""
    result = _request("user.status", {"handle": handle, "from": 1, "count": 10000})

    solved: dict[tuple, object] = {}
    for submission in result:
        if submission.get("verdict") != "OK":
            continue
        problem = submission["problem"]
        key = (problem.get("contestId"), problem.get("index"))
        if key not in solved:
            solved[key] = problem.get("rating")

    counts = {"easy": 0, "medium": 0, "hard": 0, "unrated": 0}
    for rating in solved.values():
        if rating is None:
            counts["unrated"] += 1
            continue
        for tier, lo, hi in _DIFFICULTY_TIERS:
            if lo <= rating < hi:
                counts[tier] += 1
                break

    counts["total"] = len(solved)
    return counts
