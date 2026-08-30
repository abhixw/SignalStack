from typing import List, Dict, Any

class Matcher:
    def __init__(self):
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

            # DSA / competitive-programming tasks — scored from Codeforces/
            # LeetCode (see app/services/dsa_signals.py), not from the repo.
            "dsa": ["dsa_proficiency"],
            "algorithm": ["dsa_proficiency"],
            "algorithms": ["dsa_proficiency"],
            "data structure": ["dsa_proficiency"],
            "data structures": ["dsa_proficiency"],
            "competitive programming": ["dsa_proficiency"],
            "problem solving": ["dsa_proficiency"],
            "leetcode": ["dsa_proficiency"],
            "codeforces": ["dsa_proficiency"],
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

    def calculate_task_score(self, task_title: str, signals: Dict[str, Any]) -> float:
        """Calculate a confidence score for a task based on relevant signals."""
        relevant_signal_names = self._get_task_signals(task_title)
        
        if not relevant_signal_names:
            return signals.get("overall_score", 0.0)
        
        # Average the relevant signals
        signal_values = [signals.get(s, 0.0) for s in relevant_signal_names]
        if signal_values:
            return sum(signal_values) / len(signal_values)
        return 0.0

    # Human-readable label per signal name — used only for the reason text
    # below, never for scoring itself.
    _SIGNAL_LABELS = {
        "tests_present": "tests",
        "migrations_present": "database migrations",
        "deployment_ready": "deployment config (Dockerfile/Procfile)",
        "ci_cd_present": "a CI/CD pipeline",
        "ml_model_present": "trained ML model artifacts",
        "ml_libraries": "ML libraries",
        "web_framework": "a web framework",
        "frontend_present": "frontend templates",
        "static_assets": "static assets (CSS/JS)",
        "nlp_present": "NLP libraries",
        "dsa_proficiency": "Codeforces/LeetCode activity",
    }

    def get_matched_reason(self, task_title: str, signals: Dict[str, Any]) -> List[str]:
        """Explains THIS task's score specifically — only the signals that
        actually fed into calculate_task_score for this task title, split
        into what was found vs. what's missing, so a low score is explained
        (not just silent) and a reason never cites something irrelevant to
        the task it's attached to."""
        relevant_signal_names = self._get_task_signals(task_title)

        found, missing = [], []
        for signal_name in relevant_signal_names:
            label = self._SIGNAL_LABELS.get(signal_name, signal_name)
            value = signals.get(signal_name, 0.0)

            if signal_name == "dsa_proficiency":
                # Graded 0.0-1.0, not binary — describe the strength, not
                # just presence/absence.
                if value >= 0.66:
                    found.append(f"strong {label}")
                elif value >= 0.33:
                    found.append(f"some {label}")
                else:
                    missing.append(label)
            elif value:
                found.append(label)
            else:
                missing.append(label)

        parts = []
        if found:
            parts.append(f"Found: {', '.join(found)}")
        if missing:
            parts.append(f"Missing: {', '.join(missing)}")

        return [". ".join(parts)] if parts else ["No matching signals for this task"]
