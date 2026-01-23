from fastapi import APIRouter, Depends
from typing import List
import app.schemas as schemas
from app.pipeline.task_decomposer import TaskDecomposer

router = APIRouter(tags=["Task Decomposer"])

@router.post("/plugin/suggest-tasks", response_model=List[schemas.TaskSuggestion])
def suggest_tasks(request: schemas.TaskSuggestionRequest):
    decomposer = TaskDecomposer()
    return decomposer.split(request.description)
