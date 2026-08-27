from app.services import dsa_signals


def test_score_codeforces_uses_rating_when_stronger_than_solved_count():
    score = dsa_signals.score_codeforces({"rating": 2100}, {"total": 10})
    assert score == 1.0  # 2100/2100 rating ratio beats 10/300 solved ratio


def test_score_codeforces_uses_solved_count_when_stronger_than_rating():
    score = dsa_signals.score_codeforces({"rating": 0}, {"total": 300})
    assert score == 1.0


def test_score_codeforces_partial_rating():
    score = dsa_signals.score_codeforces({"rating": 1050}, {"total": 0})
    assert abs(score - 0.5) < 1e-6  # 1050/2100


def test_score_codeforces_handles_missing_data():
    assert dsa_signals.score_codeforces(None, None) == 0.0
    assert dsa_signals.score_codeforces({}, {}) == 0.0


def test_score_leetcode_full_score_at_threshold():
    assert dsa_signals.score_leetcode({"solved": {"all": 300}}) == 1.0
    assert dsa_signals.score_leetcode({"solved": {"all": 600}}) == 1.0  # capped, not >1


def test_score_leetcode_partial():
    score = dsa_signals.score_leetcode({"solved": {"all": 150}})
    assert abs(score - 0.5) < 1e-6


def test_score_leetcode_handles_missing_data():
    assert dsa_signals.score_leetcode(None) == 0.0
    assert dsa_signals.score_leetcode({}) == 0.0


def test_combine_takes_the_stronger_platform_not_the_average():
    assert dsa_signals.combine(1.0, 0.0) == 1.0
    assert dsa_signals.combine(0.0, 1.0) == 1.0
    assert dsa_signals.combine(0.3, 0.7) == 0.7


def test_combine_zero_when_neither_platform_set():
    assert dsa_signals.combine(0.0, 0.0) == 0.0
