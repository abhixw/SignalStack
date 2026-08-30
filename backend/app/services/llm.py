import logging
from groq import (
    Groq,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
    GroqError,
)
from typing import List, Dict, Any
import json
from app.config.config import config
from app.services.errors import (
    UpstreamServiceError,
    AUTH_FAILURE,
    RATE_LIMIT,
    TIMEOUT,
    MALFORMED_RESPONSE,
    UPSTREAM_SERVICE_ERROR,
)
import app.schemas as schemas

logger = logging.getLogger("recruvoskill.llm")


def _categorize_groq_error(e: Exception) -> UpstreamServiceError:
    if isinstance(e, AuthenticationError):
        return UpstreamServiceError("groq", AUTH_FAILURE, "AI service authentication failed.", retryable=False)
    if isinstance(e, RateLimitError):
        return UpstreamServiceError("groq", RATE_LIMIT, "AI service rate limit exceeded. Please try again shortly.", retryable=True, status_code=429)
    if isinstance(e, APITimeoutError):
        return UpstreamServiceError("groq", TIMEOUT, "AI service did not respond in time.", retryable=True, status_code=504)
    if isinstance(e, APIConnectionError):
        return UpstreamServiceError("groq", UPSTREAM_SERVICE_ERROR, "Could not reach the AI service.", retryable=True)
    if isinstance(e, (json.JSONDecodeError, KeyError)):
        return UpstreamServiceError("groq", MALFORMED_RESPONSE, "AI service returned an unexpected response.", retryable=True)
    if isinstance(e, GroqError):
        return UpstreamServiceError("groq", UPSTREAM_SERVICE_ERROR, "AI service request failed.", retryable=True)
    return UpstreamServiceError("groq", UPSTREAM_SERVICE_ERROR, "AI service request failed.", retryable=True)


class GroqLLMService:
    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found in environment variables.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)
            # llama3-70b-8192 was decommissioned by Groq (May 2025); gpt-oss-120b is the current closest replacement
            self.model = "openai/gpt-oss-120b"

    def summarize(self, proof: schemas.ProofCreate) -> Dict[str, Any]:
        if not self.client:
            return {"summary": "Groq API Key missing. Using mock summary."}
        
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
            
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                response_format={"type": "json_object"}
            )
            
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            logger.warning("Groq summarize error: %s", e)
            return {"summary": "Error generating summary via Groq."}

    def evaluate_allocation(self, outcome: schemas.OutcomeCreate, enriched_proofs: List[Dict], signals_map: Dict[str, Dict]) -> Dict[str, Any]:
        if not self.client:
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
            
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                response_format={"type": "json_object"}
            )
            
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            logger.warning("Groq evaluate_allocation error: %s", e)
            return None

    def _fallback_feedback(self, task_scores: List["schemas.TaskScore"], decision: str) -> str:
        strong = [ts.task_title for ts in task_scores if ts.score >= 0.66]
        weak = [ts.task_title for ts in task_scores if ts.score < 0.33]
        parts = [
            "Thanks for your submission — we were impressed and would like to move forward to the interview stage."
            if decision == "advancing" else
            "Thank you for your submission. After review, we won't be moving forward with your application at this time."
        ]
        if strong:
            parts.append(f"Particular strengths: {', '.join(strong)}.")
        if weak:
            parts.append(f"Areas that could be stronger: {', '.join(weak)}.")
        return " ".join(parts)

    def generate_candidate_feedback(
        self, task_scores: List["schemas.TaskScore"], decision: str, outcome_title: str
    ) -> str:
        """A draft only — the recruiter reviews/edits it before it's ever sent
        (see POST /evaluations/{job_id}/decision). Never mentions the raw
        percentage scores, only what they qualitatively show."""
        if not self.client:
            logger.warning("GROQ_API_KEY not configured — using template-based feedback fallback.")
            return self._fallback_feedback(task_scores, decision)

        try:
            scores_summary = "\n".join(
                f"- {ts.task_title}: {'strong' if ts.score >= 0.66 else 'moderate' if ts.score >= 0.33 else 'weak'} match. "
                f"Reasons: {'; '.join(ts.reasons) if ts.reasons else 'none recorded'}"
                for ts in task_scores
            )
            decision_context = (
                "The candidate is being ADVANCED to the interview stage."
                if decision == "advancing" else
                "The candidate is being REJECTED at this stage."
            )

            prompt = f"""
            Act as a considerate technical recruiter writing feedback directly to a job candidate.

            Outcome: {outcome_title}
            {decision_context}

            Task-by-task evaluation:
            {scores_summary}

            Write a short (3-5 sentence), specific, professional, honest-but-encouraging feedback
            message for the candidate, referencing concrete strengths and gaps from the evaluation
            above. Do NOT mention percentages, numeric scores, or internal scoring mechanics — speak
            qualitatively (e.g. "your API implementation was solid" not "you scored 80% on API").

            Output strictly valid JSON: {{"feedback": "..."}}
            """

            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                response_format={"type": "json_object"},
            )
            return json.loads(chat_completion.choices[0].message.content)["feedback"]
        except Exception as e:
            categorized = _categorize_groq_error(e)
            logger.warning("LLM feedback generation failed: %s", categorized.to_dict())
            if config.DEMO_MODE:
                return self._fallback_feedback(task_scores, decision)
            raise categorized

    def generate_tasks(self, description: str) -> List[Dict[str, Any]]:
        # Smart Fallback Logic v2 (Principal Engineer Persona)
        def get_fallback_tasks(desc: str):
            logger.info("Using rule-based task fallback for: %s...", desc[:50])
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

        if not self.client:
            logger.warning("GROQ_API_KEY not configured — using rule-based task fallback.")
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
            
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                response_format={"type": "json_object"}
            )
            
            text = chat_completion.choices[0].message.content
            
            # Robust JSON parsing
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != -1:
                text = text[start:end]
            
            return json.loads(text)
        except Exception as e:
            categorized = _categorize_groq_error(e)
            logger.warning("LLM task generation failed: %s", categorized.to_dict())
            if config.DEMO_MODE:
                # Explicit demo/dev mode: degrade to the rule-based generator instead of erroring.
                return get_fallback_tasks(description)
            raise categorized
