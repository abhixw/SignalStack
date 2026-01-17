import random
from typing import List, Dict, Any
from schemas import OutcomeCreate, ProofCreate, WorkAllocation, EvaluationResponse, Evidence, Task
import crud
import os
import requests
import base64

class GitHubService:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {"Authorization": f"token {self.token}"} if self.token else {}
        self.api_base = "https://api.github.com"

    def _normalize_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Extract owner and repo from various GitHub URL formats."""
        # Remove trailing slashes and .git suffix
        url = repo_url.rstrip('/').rstrip('.git')
        parts = url.split('/')
        owner, repo = parts[-2], parts[-1]
        return owner, repo

    def get_repo_content(self, repo_url: str, path: str = "") -> List[Dict]:
        # Extract owner/repo from URL
        try:
            owner, repo = self._normalize_repo_url(repo_url)
        except:
            return []

        url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []

    def get_file_content(self, repo_url: str, file_path: str) -> str:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/contents/{file_path}"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                content = response.json().get("content", "")
                return base64.b64decode(content).decode('utf-8')
        except Exception as e:
            print(f"Error fetching file {file_path}: {e}")
        return ""

    def get_recursive_tree(self, repo_url: str) -> tuple[List[str], str]:
        # Get default branch sha first
        default_branch = "main"
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            repo_info = requests.get(f"{self.api_base}/repos/{owner}/{repo}", headers=self.headers).json()
            default_branch = repo_info.get("default_branch", "main")
            
            tree_url = f"{self.api_base}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
            response = requests.get(tree_url, headers=self.headers)
            if response.status_code == 200:
                return [item['path'] for item in response.json().get('tree', [])], default_branch
        except:
            pass
        return [], default_branch

    def get_commit_history(self, repo_url: str, limit: int = 50) -> List[Dict]:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/commits?per_page={limit}"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                commits = []
                for item in response.json():
                    commit = item.get("commit", {})
                    author = commit.get("author", {})
                    commits.append({
                        "message": commit.get("message", ""),
                        "author_name": author.get("name", "Unknown"),
                        "date": author.get("date", ""),
                        "sha": item.get("sha", "")
                    })
                return commits
        except Exception as e:
            print(f"Error fetching commits: {e}")
        return []

class SignalExtractor:
    def __init__(self):
        self.github = GitHubService()

    def extract_signals(self, proof: ProofCreate) -> Dict[str, Any]:
        repo_url = proof.payload.get("repo_url", "")
        if not repo_url or "github.com" not in repo_url:
            return {"valid_repo": 0.0}

        signals = {"valid_repo": 1.0}
        files, _ = self.github.get_recursive_tree(repo_url)
        
        # ===== CORE SIGNALS =====
        
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
        
        # 6. ML Libraries (check requirements.txt or setup.py)
        ml_keywords = ["scikit", "sklearn", "tensorflow", "pytorch", "keras", "xgboost", "numpy", "pandas"]
        signals["ml_libraries"] = 0.0
        for f in files:
            if "requirements" in f.lower() or "setup.py" in f.lower():
                content = self.github.get_file_content(repo_url, f)
                if any(kw in content.lower() for kw in ml_keywords):
                    signals["ml_libraries"] = 1.0
                    break
        
        # ===== WEB / API SIGNALS =====
        
        # 7. Flask / FastAPI / Django
        web_keywords = ["flask", "fastapi", "django", "@app.route", "@router"]
        signals["web_framework"] = 0.0
        for f in files:
            if f.endswith(".py"):
                content = self.github.get_file_content(repo_url, f)
                if any(kw in content.lower() for kw in web_keywords):
                    signals["web_framework"] = 1.0
                    break
        
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
        for f in files:
            if f.endswith(".py"):
                content = self.github.get_file_content(repo_url, f)
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

        # ===== CALCULATE OVERALL SCORE =====
        
        # Weight the signals
        weighted_signals = {
            "ml_model_present": 0.2,
            "ml_libraries": 0.15,
            "web_framework": 0.15,
            "nlp_present": 0.1,
            "tests_present": 0.1,
            "deployment_ready": 0.1,
            "frontend_present": 0.1,
            "static_assets": 0.05,
            "ci_cd_present": 0.05
        }
        
        overall_score = sum(signals.get(s, 0) * w for s, w in weighted_signals.items())
        signals["overall_score"] = round(overall_score, 2)

        return signals

class AllocationEngine:
    def __init__(self, db_session=None, llm_service=None):
        self.db = db_session
        self.llm_service = llm_service
        self.github = GitHubService()
        
        # Dynamic task-to-signal mapping based on task title keywords
        self.task_signal_map = {
            # ML Tasks
            "ml": ["ml_model_present", "ml_libraries"],
            "model": ["ml_model_present", "ml_libraries"],
            "train": ["ml_model_present", "ml_libraries"],
            "inference": ["ml_model_present", "web_framework"],
            "classification": ["ml_model_present", "nlp_present"],
            
            # API Tasks
            "api": ["web_framework", "tests_present"],
            "restful": ["web_framework", "tests_present"],
            "endpoint": ["web_framework", "tests_present"],
            
            # Database Tasks
            "database": ["migrations_present", "tests_present"],
            "schema": ["migrations_present", "tests_present"],
            "migration": ["migrations_present"],
            
            # Frontend Tasks
            "component": ["frontend_present", "static_assets"],
            "frontend": ["frontend_present", "static_assets"],
            "layout": ["frontend_present", "static_assets"],
            "ui": ["frontend_present", "static_assets"],
            
            # Deployment Tasks
            "deploy": ["deployment_ready", "ci_cd_present"],
            "container": ["deployment_ready"],
            "docker": ["deployment_ready"],
            "ci/cd": ["ci_cd_present"],
            "pipeline": ["ci_cd_present"],
            
            # Business Logic
            "business": ["web_framework", "tests_present"],
            "logic": ["web_framework", "tests_present"],
            "core": ["web_framework", "tests_present"],
        }
        
        # Evidence file patterns for different task types
        self.evidence_patterns = {
            "ml": ["*.pkl", "models/*", "*model*", "*train*"],
            "api": ["app.py", "main.py", "*routes*", "*views*"],
            "database": ["*schema*", "*model*", "*migration*"],
            "frontend": ["templates/*", "*.html", "static/*"],
            "deploy": ["Dockerfile", "docker-compose*", "Procfile"],
        }

    def _get_task_signals(self, task_title: str) -> List[str]:
        """Dynamically determine which signals are relevant for a task."""
        title_lower = task_title.lower()
        relevant_signals = set()
        
        for keyword, signals in self.task_signal_map.items():
            if keyword in title_lower:
                relevant_signals.update(signals)
        
        # Default to overall capability if no specific match
        if not relevant_signals:
            relevant_signals = {"web_framework", "tests_present"}
        
        return list(relevant_signals)

    def _calculate_task_score(self, task_title: str, signals: Dict[str, Any]) -> float:
        """Calculate a confidence score for a task based on relevant signals."""
        relevant_signal_names = self._get_task_signals(task_title)
        
        if not relevant_signal_names:
            return signals.get("overall_score", 0.0)
        
        # Average the relevant signals
        signal_values = [signals.get(s, 0.0) for s in relevant_signal_names]
        if signal_values:
            return sum(signal_values) / len(signal_values)
        return 0.0

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

    def _extract_evidence(self, repo_url: str, task_title: str) -> List[Evidence]:
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
                            
                            evidence.append(Evidence(
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
            evidence.append(Evidence(
                type="file_ref",
                ref=main_file,
                snippet=f"Repository contains {len(files)} files. Main entry point: {main_file}",
                source_url=f"{repo_url}/blob/{default_branch}/{main_file}"
            ))
        
        return evidence

    def evaluate(self, outcome: OutcomeCreate, proofs: List[ProofCreate], signals_map: Dict[str, Dict]) -> EvaluationResponse:
        allocations = []
        global_signals_used = set()
        
        for task in outcome.tasks:
            best_candidate = None
            best_score = 0.0
            reasons = []
            evidence = []
            
            # Find best candidate based on signals
            for proof in proofs:
                cand_id = proof.candidate_id
                signals = signals_map.get(cand_id, {})
                
                # Calculate task-specific score
                score = self._calculate_task_score(task.title, signals)
                
                # Track which signals we used
                for signal_name in self._get_task_signals(task.title):
                    global_signals_used.add(signal_name)
                
                if score > best_score:
                    best_score = score
                    best_candidate = cand_id
            
            # Generate reasons based on matched signals
            if best_candidate:
                matched_signals = self._get_task_signals(task.title)
                candidate_signals = signals_map.get(best_candidate, {})
                
                # Build human-readable reasons
                reason_parts = []
                if candidate_signals.get("ml_model_present"):
                    reason_parts.append("ML models found")
                if candidate_signals.get("web_framework"):
                    reason_parts.append("Web framework detected")
                if candidate_signals.get("frontend_present"):
                    reason_parts.append("Frontend templates present")
                if candidate_signals.get("deployment_ready"):
                    reason_parts.append("Deployment artifacts found")
                if candidate_signals.get("tests_present"):
                    reason_parts.append("Tests present")
                
                if reason_parts:
                    reasons = [", ".join(reason_parts)]
                else:
                    reasons = [f"Matched on {', '.join(matched_signals)}"]
                
                # Extract evidence
                repo_url = proof.payload.get("repo_url", "")
                if repo_url:
                    evidence = self._extract_evidence(repo_url, task.title)

            allocations.append(WorkAllocation(
                task_id=task.task_id,
                task_title=task.title,
                recommended_candidate=best_candidate or "None",
                confidence=round(best_score, 2),
                reasons=reasons if reasons else ["No matching signals found"],
                evidence=evidence
            ))

        # Calculate overall fit score
        avg_confidence = 0.0
        if allocations:
            avg_confidence = sum(a.confidence for a in allocations) / len(allocations)

        return EvaluationResponse(
            job_id=outcome.id,
            fit_score=round(avg_confidence, 2),
            work_allocation=allocations,
            global_signals_used=list(global_signals_used),
            risk_flags=[],
            human_action_required=True
        )

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiLLMService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("Warning: GEMINI_API_KEY not found in environment variables.")
        else:
            genai.configure(api_key=self.api_key)
            # Use gemini-2.5-flash-lite for best rate limits (10 RPM)
            self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

    def summarize(self, proof: ProofCreate) -> Dict[str, Any]:
        if not self.api_key:
            return {"summary": "Gemini API Key missing. Using mock summary."}
        
        try:
            prompt = f"""
            Analyze the following GitHub repository proof and provide a concise technical summary.
            Repo URL: {proof.payload.get('repo_url')}
            Context: {proof.payload.get('context', 'No context provided')}
            
            Output JSON format:
            {{
                "summary": "Brief summary of the codebase...",
                "tech_stack": ["list", "of", "technologies"],
                "complexity": "Low/Medium/High"
            }}
            """
            response = self.model.generate_content(prompt)
            try:
                import json
                text = response.text.replace('```json', '').replace('```', '').strip()
                return json.loads(text)
            except:
                return {"summary": response.text, "raw": True}
        except Exception as e:
            print(f"Gemini Error: {e}")
            return {"summary": "Error generating summary via Gemini."}

    def evaluate_allocation(self, outcome: OutcomeCreate, enriched_proofs: List[Dict], signals_map: Dict[str, Dict]) -> Dict[str, Any]:
        if not self.api_key:
            return None

        try:
            # Construct Prompt
            candidates_info = []
            for item in enriched_proofs:
                p = item["proof"]
                ctx = item["context"]
                cand_id = p.candidate_id
                signals = signals_map.get(cand_id, {})
                
                candidates_info.append(f"""
                Candidate {cand_id}:
                Repo URL: {ctx['repo_url']}
                Signals: {signals}
                File Structure (Partial): {', '.join(ctx['files'])}
                README Summary: {ctx['readme']}
                Recent Commits: {chr(10).join(ctx.get('commits', []))}
                """)

            prompt = f"""
            Act as an expert technical hiring manager. Evaluate these candidates for the following Outcome.
            
            Outcome: {outcome.title}
            Description: {outcome.description}
            Tasks: {[t.title for t in outcome.tasks]}
            
            Candidates:
            {chr(10).join(candidates_info)}
            
            For each Task, select the best candidate. Provide a confidence score (0.0-1.0) and a concise reason.
            Also cite specific evidence (file names, patterns) if available in the signals.
            
            Output strictly valid JSON with this schema:
            {{
                "allocations": [
                    {{
                        "task_title": "string",
                        "recommended_candidate": "string",
                        "confidence": float,
                        "reason": "string",
                        "evidence_ref": "string"
                    }}
                ]
            }}
            """
            
            response = self.model.generate_content(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            import json
            return json.loads(text)
        except Exception as e:
            print(f"LLM Evaluation Error: {e}")
            return None

    def generate_tasks(self, description: str) -> List[Dict[str, Any]]:
        # Smart Fallback Logic v2 (Principal Engineer Persona)
        def get_fallback_tasks(desc: str):
            print(f"Triggering Smart Fallback v2 for: {desc[:50]}...")
            tasks = []
            desc_lower = desc.lower()
            
            # Pool of High-Quality Tasks
            possible_tasks = []

            # 1. Backend / API
            if any(k in desc_lower for k in ["api", "backend", "fastapi", "flask", "django", "node", "express"]):
                possible_tasks.append({
                    "title": "Design RESTful API Specification", 
                    "outcome": "OpenAPI 3.0 (Swagger) spec defining all endpoints, request/response schemas, and error codes.", 
                    "importance": "High"
                })
                possible_tasks.append({
                    "title": "Implement Core Business Logic", 
                    "outcome": "Service layer implementation with unit tests covering happy/sad paths.", 
                    "importance": "High"
                })

            # 2. Database / Data
            if any(k in desc_lower for k in ["data", "sql", "schema", "db", "postgres", "mongo"]):
                possible_tasks.append({
                    "title": "Design Database Schema & Migrations", 
                    "outcome": "Normalized ERD and Alembic/Flyway migration scripts ensuring data integrity.", 
                    "importance": "High"
                })

            # 3. Frontend / UI
            if any(k in desc_lower for k in ["ui", "frontend", "react", "vue", "angular", "css", "web"]):
                possible_tasks.append({
                    "title": "Build Reusable Component Library", 
                    "outcome": "Set of atomic UI components (Buttons, Inputs, Cards) with consistent styling.", 
                    "importance": "Medium"
                })
                possible_tasks.append({
                    "title": "Implement Responsive Layouts", 
                    "outcome": "Mobile-first CSS/Grid layouts verified on multiple screen sizes.", 
                    "importance": "Medium"
                })

            # 4. Auth / Security
            if any(k in desc_lower for k in ["auth", "login", "security", "jwt", "oauth"]):
                possible_tasks.append({
                    "title": "Implement Secure Authentication", 
                    "outcome": "JWT-based middleware with refresh tokens and BCrypt password hashing.", 
                    "importance": "High"
                })

            # 5. AI / ML (New Category for User's Project)
            if any(k in desc_lower for k in ["ml", "ai", "scikit", "nlp", "classification", "model", "train"]):
                possible_tasks.append({
                    "title": "Train & Evaluate ML Model", 
                    "outcome": "Trained model artifact (.pkl) with >80% F1 score on test set.", 
                    "importance": "High"
                })
                possible_tasks.append({
                    "title": "Implement Inference Pipeline", 
                    "outcome": "API endpoint that accepts raw text and returns prediction with confidence score.", 
                    "importance": "High"
                })

            # 6. Infrastructure / DevOps
            if any(k in desc_lower for k in ["ci", "cd", "docker", "cloud", "deploy", "aws", "render"]):
                possible_tasks.append({
                    "title": "Containerize Application", 
                    "outcome": "Multi-stage Dockerfile optimized for production size and security.", 
                    "importance": "Medium"
                })
                possible_tasks.append({
                    "title": "Setup CI/CD Pipeline", 
                    "outcome": "GitHub Actions workflow for automated linting, testing, and building.", 
                    "importance": "Medium"
                })

            # Default tasks if none matched or too few
            if len(possible_tasks) < 3:
                possible_tasks.append({
                    "title": "System Architecture Design", 
                    "outcome": "High-level design document outlining system components and data flow.", 
                    "importance": "High"
                })
                possible_tasks.append({
                    "title": "Write Comprehensive Unit Tests", 
                    "outcome": "Test suite achieving >80% code coverage.", 
                    "importance": "Medium"
                })

            # Select top 3-5 unique tasks
            seen_titles = set()
            final_tasks = []
            for t in possible_tasks:
                if t["title"] not in seen_titles:
                    final_tasks.append(t)
                    seen_titles.add(t["title"])
                if len(final_tasks) >= 5:
                    break
            
            return final_tasks

        if not self.api_key:
            print("No API Key found, using fallback.")
            return get_fallback_tasks(description)

        try:
            prompt = f"""
            Act as a Principal Engineer and Hiring Manager defining a take-home assignment.
            Decompose the following project description into 3-5 distinct, verifiable technical tasks.
            
            Project Description: "{description}"
            
            ### Guidelines:
            1. **Concrete & Verifiable:** Tasks must result in code or artifacts (e.g., "Implement JWT Auth", not "Research security").
            2. **Proof of Work:** Focus on what the candidate will submit (e.g., "Migration script", "Docker container").
            3. **Testable Outcomes:** Each task must have a clear success criterion.
            
            ### Examples:
            
            **Bad Output (Too Generic):**
            - "Create Backend" (Too vague)
            - "Design Database" (No artifact specified)
            - "Test Application" (Not a specific task)
            
            **Good Output (Specific & Verifiable):**
            - Title: "Implement User Authentication API"
              Outcome: "JWT-based login/register endpoints with BCrypt hashing"
            - Title: "Design Database Schema"
              Outcome: "PostgreSQL ERD and Alembic migration scripts"
            - Title: "Containerize Application"
              Outcome: "Dockerfile and docker-compose.yml that boots the full stack"
            
            ### Output Format:
            Strictly valid JSON array:
            [
                {{
                    "title": "Short Actionable Title",
                    "outcome": "Specific verifiable deliverable",
                    "importance": "High/Medium/Low"
                }}
            ]
            """
            response = self.model.generate_content(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            
            # Robust JSON parsing
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != -1:
                text = text[start:end]
                
            import json
            return json.loads(text)
        except Exception as e:
            print(f"LLM Task Generation Error: {e}")
            if 'response' in locals():
                print(f"Raw Response: {response.text}")
            return get_fallback_tasks(description)

# Initialize
llm_service = GeminiLLMService()
signal_extractor = SignalExtractor()
allocation_engine = AllocationEngine(llm_service=llm_service)
