from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import datetime
from .outcome import OutcomeCreate
from .proof import ProofCreate, Evidence

class EvaluateRequest(BaseModel):
    request_id: str
    outcome: OutcomeCreate
    proofs: List[ProofCreate]
    options: Optional[Dict[str, Any]] = None

class EvaluationTrigger(BaseModel):
    job_id: str

class CandidateDecisionUpdate(BaseModel):
    candidate_id: str
    decision: str  # "advancing" | "rejected" — validated against DECISIONS in routes/evaluator.py

class WorkAllocation(BaseModel):
    task_id: str
    task_title: str
    recommended_candidate: str
    confidence: float
    reasons: List[str]
    evidence: List[Evidence]

class TaskScore(BaseModel):
    task_id: str
    task_title: str
    score: float
    reasons: List[str]

class EvaluationResponse(BaseModel):
    job_id: str
    fit_score: float
    work_allocation: List[WorkAllocation]
    candidate_scores: Dict[str, float] = {}
    # Every candidate's score against every task — not just who "won" each
    # task (that's what work_allocation captures). Keyed by candidate_id.
    candidate_task_scores: Dict[str, List[TaskScore]] = {}
    # Recruiter-set only, via POST /evaluations/{job_id}/decision — "advancing"
    # or "rejected" per candidate_id; absent = no decision made yet. This is
    # the ONLY thing a candidate ever sees about their evaluation (see
    # GET /candidate/my-applications) — never the raw score.
    candidate_decisions: Dict[str, str] = {}
    global_signals_used: List[str]
    risk_flags: List[str]
    human_action_required: bool
    raw_output: Optional[Dict[str, Any]] = None

class EvaluationSummary(BaseModel):
    job_id: str
    outcome_title: str
    fit_score: float
    human_action_required: bool
    risk_flags: List[str]
    created_at: datetime.datetime
