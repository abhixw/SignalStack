from pydantic import BaseModel
from typing import List, Dict, Optional
from .task import Task

class OutcomeCreate(BaseModel):
    id: str
    title: str
    description: str
    tasks: List[Task]
    # One of app.constants.JobRole.ALL, or None for an outcome that isn't
    # tagged to a role yet — validated in app/routes/outcome.py, not here,
    # so this schema doesn't need to import app.constants.
    job_role: Optional[str] = None
    # Optional/defaulted: public reads (GET /outcomes, /outcomes/{id}, /candidate/jobs)
    # deliberately omit the real scoring weights, returning {} instead — the
    # rubric is not currently read anywhere in the scoring pipeline, so this is
    # safe to hide from candidates without affecting evaluation.
    rubric: Dict[str, float] = {}
