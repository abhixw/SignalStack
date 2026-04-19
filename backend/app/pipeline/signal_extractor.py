from typing import List, Dict, Any, Optional
from app.services.github import GitHubService
import app.schemas as schemas

class SignalExtractor:
    def __init__(self):
        self.github = GitHubService()

    def extract_signals(self, proof: schemas.ProofCreate) -> Dict[str, Any]:
        """Extract raw signals from the proof of work."""
        repo_url = proof.payload.get("repo_url", "")
        if not repo_url or "github.com" not in repo_url:
            return {"valid_repo": 0.0}

        signals = {"valid_repo": 1.0}
        files, _ = self.github.get_recursive_tree(repo_url)
        
        if not files:
             return signals
        # 1. Test Presence
        has_tests = any("test" in f.lower() or "spec" in f.lower() for f in files)
        signals["tests_present"] = 1.0 if has_tests else 0.0

        # 2. Migrations / DB
        has_migrations = any("migration" in f.lower() or "alembic" in f.lower() or ".sql" in f.lower() for f in files)
        signals["migrations_present"] = 1.0 if has_migrations else 0.0
        
        # 3. Docker / Deployment
        has_docker = any("Dockerfile" in f or "docker-compose" in f or "Procfile" in f for f in files)
        signals["deployment_ready"] = 1.0 if has_docker else 0.0

        # 4. CI/CD
        has_ci = any(".github/workflows" in f for f in files)
        signals["ci_cd_present"] = 1.0 if has_ci else 0.0
        
        # ===== ML / AI SIGNALS =====
        # 5. Model Files
        has_model = any(f.endswith(".pkl") or f.endswith(".h5") or f.endswith(".pt") or "models/" in f for f in files)
        signals["ml_model_present"] = 1.0 if has_model else 0.0
        
        # 6. ML Libraries
        ml_keywords = ["scikit", "sklearn", "tensorflow", "pytorch", "keras", "xgboost", "numpy", "pandas"]
        signals["ml_libraries"] = 0.0
        checked_files = 0
        for f in files:
            if "requirements" in f.lower() or "setup.py" in f.lower():
                if checked_files >= 5: break
                content = self.github.get_file_content(repo_url, f)
                checked_files += 1
                if any(kw in content.lower() for kw in ml_keywords):
                    signals["ml_libraries"] = 1.0
                    break
        
        # ... (web_framework is already done) ...
        
        # 8. HTML Templates
        has_templates = any("templates/" in f or f.endswith(".html") for f in files)
        signals["frontend_present"] = 1.0 if has_templates else 0.0
        
        # 9. Static files (CSS, JS)
        has_static = any("static/" in f or f.endswith(".css") or f.endswith(".js") for f in files)
        signals["static_assets"] = 1.0 if has_static else 0.0
        
        # ===== NLP SIGNALS =====
        # 10. NLP Libraries
        nlp_keywords = ["nltk", "spacy", "textblob", "tfidf", "vectorizer", "tokenizer"]
        signals["nlp_present"] = 0.0
        checked_files = 0
        for f in files:
            if f.endswith(".py"):
                if checked_files >= 10: break
                content = self.github.get_file_content(repo_url, f)
                checked_files += 1
                if any(kw in content.lower() for kw in nlp_keywords):
                    signals["nlp_present"] = 1.0
                    break

        # ===== COMMIT HISTORY =====
        commits = self.github.get_commit_history(repo_url)
        signals["commit_count"] = min(len(commits), 50)  # Cap at 50 for normalization
        if commits:
            authors = set(c["author_name"] for c in commits)
            signals["unique_authors"] = len(authors)
            signals["recent_activity_score"] = 1.0
        else:
            signals["unique_authors"] = 0
            signals["recent_activity_score"] = 0.0

        return signals

    def _get_evidence_keywords(self, task_title: str) -> List[str]:
        """Get code keywords to search for based on task title."""
        title_lower = task_title.lower()
        keywords = []
        
        if any(k in title_lower for k in ["ml", "model", "train", "classification"]):
            keywords = ["pickle", "joblib", "fit", "predict", "sklearn", "TfidfVectorizer"]
        elif any(k in title_lower for k in ["api", "restful", "endpoint"]):
            keywords = ["@app.route", "@router", "def predict", "request", "jsonify"]
        elif any(k in title_lower for k in ["database", "schema", "migration"]):
            keywords = ["class ", "Column", "Model", "Table", "ForeignKey"]
        elif any(k in title_lower for k in ["frontend", "component", "layout"]):
            keywords = ["<html", "<form", "<div", "render_template", "template"]
        elif any(k in title_lower for k in ["deploy", "container", "docker"]):
            keywords = ["FROM ", "RUN ", "CMD ", "EXPOSE", "gunicorn"]
        else:
            keywords = ["def ", "class ", "import "]
        
        return keywords

    def extract_evidence(self, repo_url: str, task_title: str) -> List[schemas.Evidence]:
        """Extract relevant code evidence for a task from the repository."""
        evidence = []
        files, default_branch = self.github.get_recursive_tree(repo_url)
        keywords = self._get_evidence_keywords(task_title)
        
        # Priority files based on task type
        priority_files = []
        if any(k in task_title.lower() for k in ["ml", "model", "train"]):
            priority_files = [f for f in files if "model" in f.lower() or f.endswith(".pkl")]
        elif any(k in task_title.lower() for k in ["api", "restful", "endpoint"]):
            priority_files = [f for f in files if "app" in f.lower() or "route" in f.lower()]
        elif any(k in task_title.lower() for k in ["frontend", "template"]):
            priority_files = [f for f in files if f.endswith(".html") or "template" in f.lower()]
        
        # Fallback to common files
        if not priority_files:
            priority_files = [f for f in files if f.endswith(".py") and ("app" in f.lower() or "main" in f.lower())]
        
        # Scan priority files for evidence
        for f in priority_files[:5]:  # Limit to 5 files
            content = self.github.get_file_content(repo_url, f)
            if not content:
                continue
                
            for kw in keywords:
                if kw in content:
                    # Extract a meaningful snippet
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if kw in line:
                            start = max(0, i - 1)
                            end = min(len(lines), i + 4)
                            snippet = "\n".join(lines[start:end])
                            
                            evidence.append(schemas.Evidence(
                                type="code_snippet",
                                ref=f,
                                snippet=snippet[:300],  # Limit snippet length
                                source_url=f"{repo_url}/blob/{default_branch}/{f}#L{i+1}"
                            ))
                            break
                    if evidence:
                        break
            if evidence:
                break
        
        # Fallback evidence if nothing found
        if not evidence and files:
            main_file = next((f for f in files if "app" in f.lower() or "main" in f.lower()), files[0])
            evidence.append(schemas.Evidence(
                type="file_ref",
                ref=main_file,
                snippet=f"Repository contains {len(files)} files. Main entry point: {main_file}",
                source_url=f"{repo_url}/blob/{default_branch}/{main_file}"
            ))
        
        return evidence
