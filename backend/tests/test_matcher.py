from app.pipeline.matcher import Matcher


def test_get_matched_reason_only_cites_signals_relevant_to_the_task():
    """The actual bug this guards: the old implementation checked a fixed
    global list of signals regardless of the task, so an unrelated "positive"
    signal (e.g. deployment_ready) could show up in the reason for a task
    that has nothing to do with deployment."""
    matcher = Matcher()
    # "Design Database Schema" -> ["migrations_present", "tests_present"] only.
    signals = {
        "migrations_present": 0.0,
        "tests_present": 0.0,
        "deployment_ready": 1.0,  # irrelevant to this task, must not appear
        "ml_model_present": 1.0,  # irrelevant to this task, must not appear
    }
    reason = matcher.get_matched_reason("Design Database Schema", signals)[0]
    assert "deployment" not in reason.lower()
    assert "ml model" not in reason.lower()


def test_get_matched_reason_explains_a_zero_score_with_whats_missing():
    matcher = Matcher()
    signals = {"migrations_present": 0.0, "tests_present": 0.0}
    reason = matcher.get_matched_reason("Design Database Schema", signals)[0]
    assert "Missing" in reason
    assert "database migrations" in reason
    assert "tests" in reason
    assert "Found" not in reason


def test_get_matched_reason_explains_a_full_score_with_whats_found():
    matcher = Matcher()
    signals = {"migrations_present": 1.0, "tests_present": 1.0}
    reason = matcher.get_matched_reason("Design Database Schema", signals)[0]
    assert "Found" in reason
    assert "Missing" not in reason


def test_get_matched_reason_splits_partial_score_into_found_and_missing():
    matcher = Matcher()
    signals = {"migrations_present": 1.0, "tests_present": 0.0}
    reason = matcher.get_matched_reason("Design Database Schema", signals)[0]
    assert "Found: database migrations" in reason
    assert "Missing: tests" in reason


def test_get_matched_reason_describes_dsa_proficiency_by_strength_not_presence():
    matcher = Matcher()
    strong = matcher.get_matched_reason("Solve DSA problems", {"dsa_proficiency": 0.9})[0]
    weak = matcher.get_matched_reason("Solve DSA problems", {"dsa_proficiency": 0.1})[0]
    assert "strong" in strong.lower()
    assert "Missing" in weak


def test_calculate_task_score_matches_what_the_reason_describes():
    """The score and its reason must agree — a 0.5 score should show one
    signal found and one missing, not something inconsistent with the number."""
    matcher = Matcher()
    signals = {"migrations_present": 1.0, "tests_present": 0.0}
    score = matcher.calculate_task_score("Design Database Schema", signals)
    reason = matcher.get_matched_reason("Design Database Schema", signals)[0]
    assert score == 0.5
    assert "Found: database migrations" in reason
    assert "Missing: tests" in reason
