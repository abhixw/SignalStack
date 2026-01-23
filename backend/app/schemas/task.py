from pydantic import BaseModel
from typing import Dict, Any

class Task(BaseModel):
    task_id: str
    title: str
    success_criteria: Dict[str, Any]

class TaskSuggestionRequest(BaseModel):
    description: str

class TaskSuggestion(BaseModel):
    title: str
    outcome: str
    importance: str
