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

class WorkAllocation(BaseModel):
    task_id: str
    task_title: str
    recommended_candidate: str
    confidence: float
    reasons: List[str]
    evidence: List[Evidence]

class EvaluationResponse(BaseModel):
    job_id: str
    fit_score: float
    work_allocation: List[WorkAllocation]
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
