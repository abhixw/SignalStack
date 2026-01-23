from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.pipeline.feedback import FeedbackLoop

router = APIRouter(tags=["Feedback"])

@router.post("/plugin/feedback")
def submit_feedback(feedback: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    # Store feedback
    crud.create_feedback(db, feedback)
    
    # Trigger Learning Loop (Update Weights)
    loop = FeedbackLoop(db)
    changes = loop.process_feedback(feedback)
        
    return {"status": "feedback_recorded", "changes": changes}

@router.get("/admin/signal-weights", response_model=List[schemas.SignalWeightResponse])
def get_signal_weights(db: Session = Depends(get_db)):
    weights = crud.get_signal_weights(db)
    return [schemas.SignalWeightResponse(
        signal_name=w.signal_name,
        weight=w.weight,
        task_context=w.task_id
    ) for w in weights]

@router.get("/admin/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    logs = crud.get_audit_logs(db)
    return [{"id": l.id, "entity_type": l.entity_type, "entity_id": l.entity_id, "action": l.action, "details": l.details_json, "created_at": l.created_at.isoformat()} for l in logs]

@router.get("/admin/feedback")
def get_feedback_list(db: Session = Depends(get_db)):
    feedback = crud.get_feedback_list(db)
    return [{"id": f.id, "job_id": f.job_id, "result": f.result, "metrics": f.metrics_json, "created_at": f.created_at.isoformat()} for f in feedback]
