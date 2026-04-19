from groq import Groq
from typing import List, Dict, Any
import json
from app.config.config import config
import app.schemas as schemas

class GroqLLMService:
    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        if not self.api_key:
            print("Warning: GROQ_API_KEY not found in environment variables.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)
            # Use llama3-70b-8192 for high quality and speed
            self.model = "llama3-70b-8192"

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
            print(f"Groq Error: {e}")
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

        if not self.client:
            print("No Groq client found, using fallback.")
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
            print(f"LLM Task Generation Error: {e}")
            return get_fallback_tasks(description)
