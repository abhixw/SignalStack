from typing import List, Dict, Any
from app.services.github import GitHubService
from app.schemas.schemas import OutcomeCreate, ProofCreate, WorkAllocation, EvaluationResponse, Evidence
import random

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
