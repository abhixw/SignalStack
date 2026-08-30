import logging
from typing import Optional

import requests

logger = logging.getLogger("recruvoskill.leetcode")

# LeetCode has no official/documented API. This is the same unauthenticated
# GraphQL endpoint leetcode.com's own frontend calls to render a public
# profile page — found via browser devtools, not a published contract, so it
# can shift or rate-limit without notice. Every caller treats a failure here
# as "unavailable", never as an error to surface loudly.
_GRAPHQL_URL = "https://leetcode.com/graphql"
_TIMEOUT_SECONDS = 10

_PROFILE_QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
    profile {
      ranking
    }
  }
}
"""


def fetch_user_stats(username: str) -> Optional[dict]:
    """Best-effort: returns None on any failure (bad username, endpoint down,
    schema shift) rather than raising — callers should treat that as
    "unavailable right now", not surface it as a hard error."""
    try:
        resp = requests.post(
            _GRAPHQL_URL,
            json={"query": _PROFILE_QUERY, "variables": {"username": username}},
            headers={
                "Content-Type": "application/json",
                # LeetCode's GraphQL endpoint rejects some requests without a
                # same-site-looking Referer.
                "Referer": f"https://leetcode.com/{username}/",
            },
            timeout=_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            logger.warning("LeetCode GraphQL returned status %s", resp.status_code)
            return None

        data = resp.json()
        user = (data.get("data") or {}).get("matchedUser")
        if not user:
            return None

        counts = {"easy": 0, "medium": 0, "hard": 0, "all": 0}
        for entry in (user.get("submitStatsGlobal") or {}).get("acSubmissionNum", []):
            difficulty = (entry.get("difficulty") or "").lower()
            if difficulty in counts:
                counts[difficulty] = entry.get("count", 0)

        return {
            "username": user.get("username"),
            "ranking": (user.get("profile") or {}).get("ranking"),
            "solved": counts,
        }
    except requests.exceptions.RequestException as e:
        logger.warning("LeetCode request failed: %s", e)
        return None
    except (ValueError, KeyError) as e:
        # Malformed/unexpected JSON shape — the endpoint shifted under us.
        logger.warning("LeetCode response was not in the expected shape: %s", e)
        return None
