from pydantic import BaseModel
from typing import Dict, Optional, Any

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
