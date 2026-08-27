from fastapi import APIRouter, Depends, Query
from pymongo.asynchronous.database import AsyncDatabase
from typing import List
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.pipeline.feedback import FeedbackLoop
from app.deps.auth import require_roles
from app.constants import UserRole

router = APIRouter(tags=["Feedback"])


@router.post("/plugin/feedback")
async def submit_feedback(
    feedback: schemas.FeedbackCreate,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    await crud.create_feedback(db, feedback)
    loop = FeedbackLoop(db)
    changes = await loop.process_feedback(feedback)
    return {"status": "feedback_recorded", "changes": changes}


@router.get("/admin/signal-weights", response_model=List[schemas.SignalWeightResponse])
async def get_signal_weights(
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN)),
):
    weights = await crud.get_signal_weights(db)
    return [schemas.SignalWeightResponse(
        signal_name=w["signal_name"],
        weight=w["weight"],
        task_context=w.get("task_id")
    ) for w in weights]


@router.get("/admin/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN)),
):
    logs = await crud.get_audit_logs(db, offset=(page - 1) * page_size, limit=page_size)
    return [{"id": str(l["_id"]), "entity_type": l["entity_type"], "entity_id": l["entity_id"], "action": l["action"], "details": l["details"], "created_at": l["created_at"].isoformat()} for l in logs]


@router.get("/admin/feedback")
async def get_feedback_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN)),
):
    feedback = await crud.get_feedback_list(db, offset=(page - 1) * page_size, limit=page_size)
    return [{"id": str(f["_id"]), "job_id": f["job_id"], "result": f["result"], "metrics": f["metrics"], "created_at": f["created_at"].isoformat()} for f in feedback]
