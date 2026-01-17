from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import datetime

class Task(BaseModel):
    task_id: str
    title: str
    success_criteria: Dict[str, Any]

class OutcomeCreate(BaseModel):
    id: str
    title: str
    description: str
    tasks: List[Task]
    rubric: Dict[str, float]

class ProofCreate(BaseModel):
    job_id: Optional[str] = None # Optional in schema, but required for submission logic
    candidate_id: str
    type: str
    payload: Dict[str, str]

class EvaluateRequest(BaseModel):
    request_id: str
    outcome: OutcomeCreate
    proofs: List[ProofCreate]
    options: Optional[Dict[str, Any]] = None

class EvaluationTrigger(BaseModel):
    job_id: str

class Evidence(BaseModel):
    type: str
    ref: str
    snippet: str
    source_url: Optional[str] = None

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

class FeedbackCreate(BaseModel):
    job_id: str
    evaluation_id: str
    result: str # success | failure
    metrics: Dict[str, Any]
    notes: Optional[str] = None

class SignalWeightResponse(BaseModel):
    signal_name: str
    weight: float
    task_context: Optional[str] = None

class TaskSuggestionRequest(BaseModel):
    description: str

class TaskSuggestion(BaseModel):
    title: str
    outcome: str
    importance: str

class EvaluationSummary(BaseModel):
    job_id: str
    outcome_title: str
    fit_score: float
    human_action_required: bool
    risk_flags: List[str]
    created_at: datetime.datetime
