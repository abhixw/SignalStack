"""Turns raw Codeforces/LeetCode stats into the single 0.0-1.0 `dsa_proficiency`
signal that Matcher averages alongside the GitHub-derived signals (see
app/pipeline/matcher.py). Kept as pure functions so the normalization
thresholds are easy to see and to unit test in isolation from the network
calls in app/services/codeforces.py / app/services/leetcode.py."""

# Codeforces rating at which "Master" begins — reaching it is treated as a
# full score; nothing above it scores any higher.
_CODEFORCES_MASTER_RATING = 2100

# Distinct solved-problem count (on either platform) treated as a full score.
_SOLVED_PROBLEMS_FOR_FULL_SCORE = 300


def _ratio(value: float, ceiling: float) -> float:
    if not value or value <= 0:
        return 0.0
    return min(value / ceiling, 1.0)


def score_codeforces(user_info: dict | None, solved_counts: dict | None) -> float:
    """Highest of a rating-based score and a solved-count-based score — a
    candidate strong on either measure shouldn't be capped by the other."""
    rating_score = _ratio((user_info or {}).get("rating") or 0, _CODEFORCES_MASTER_RATING)
    solved_score = _ratio((solved_counts or {}).get("total") or 0, _SOLVED_PROBLEMS_FOR_FULL_SCORE)
    return max(rating_score, solved_score)


def score_leetcode(stats: dict | None) -> float:
    solved_all = ((stats or {}).get("solved") or {}).get("all") or 0
    return _ratio(solved_all, _SOLVED_PROBLEMS_FOR_FULL_SCORE)


def combine(codeforces_score: float, leetcode_score: float) -> float:
    """A candidate only using one platform isn't penalized for not using the
    other — take whichever signal is strongest, not an average."""
    return round(max(codeforces_score, leetcode_score), 4)
