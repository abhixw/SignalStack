from fastapi import APIRouter, Depends, HTTPException
from typing import List
import app.schemas as schemas
from app.pipeline.task_decomposer import TaskDecomposer
from app.deps.auth import require_roles
from app.constants import UserRole
from app.services.errors import UpstreamServiceError

router = APIRouter(tags=["Task Decomposer"])


@router.post("/plugin/suggest-tasks", response_model=List[schemas.TaskSuggestion])
def suggest_tasks(
    request: schemas.TaskSuggestionRequest,
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    decomposer = TaskDecomposer()
    try:
        return decomposer.split(request.description)
    except UpstreamServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
