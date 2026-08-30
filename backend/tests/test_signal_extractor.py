from app.pipeline.signal_extractor import SignalExtractor
import app.schemas as schemas


def _proof(repo_url="https://github.com/octocat/Hello-World"):
    return schemas.ProofCreate(job_id="j1", candidate_id="c@example.com", type="github", payload={"repo_url": repo_url})


def test_web_framework_detected_from_requirements_txt(monkeypatch):
    """The actual bug this guards: web_framework was referenced throughout
    Matcher's task_signal_map but never computed anywhere — every "api",
    "restful", "endpoint", "business", "logic", "core" task, and the default
    fallback, was structurally capped near 50% for every candidate regardless
    of repo quality, because this signal was always missing."""
    extractor = SignalExtractor()
    monkeypatch.setattr(extractor.github, "get_recursive_tree", lambda url: (["requirements.txt", "app.py"], "main"))
    monkeypatch.setattr(extractor.github, "get_file_content", lambda url, path: "fastapi\nuvicorn\npydantic\n")

    signals = extractor.extract_signals(_proof())
    assert signals["web_framework"] == 1.0


def test_web_framework_detected_from_package_json(monkeypatch):
    extractor = SignalExtractor()
    monkeypatch.setattr(extractor.github, "get_recursive_tree", lambda url: (["package.json"], "main"))
    monkeypatch.setattr(extractor.github, "get_file_content", lambda url, path: '{"dependencies": {"express": "^4.18.0"}}')

    signals = extractor.extract_signals(_proof())
    assert signals["web_framework"] == 1.0


def test_web_framework_absent_when_no_framework_keyword_found(monkeypatch):
    extractor = SignalExtractor()
    monkeypatch.setattr(extractor.github, "get_recursive_tree", lambda url: (["requirements.txt"], "main"))
    monkeypatch.setattr(extractor.github, "get_file_content", lambda url, path: "requests\nnumpy\n")

    signals = extractor.extract_signals(_proof())
    assert signals["web_framework"] == 0.0
