from pydantic import BaseModel
from typing import List, Dict
from .task import Task

class OutcomeCreate(BaseModel):
    id: str
    title: str
    description: str
    tasks: List[Task]
    rubric: Dict[str, float]
