from sqlalchemy.orm import Session
from sqlalchemy import desc
import app.models as models
import app.schemas as schemas
import json

def get_outcome(db: Session, outcome_id: str):
    return db.query(models.Outcome).filter(models.Outcome.id == outcome_id).first()

def get_outcomes(db: Session):
    return db.query(models.Outcome).all()

def create_outcome(db: Session, outcome: schemas.OutcomeCreate):
    # Convert Pydantic models to JSON-serializable dicts
    tasks_data = [t.dict() for t in outcome.tasks]
    
    db_outcome = models.Outcome(
        id=outcome.id,
        title=outcome.title,
        description=outcome.description,
        tasks_json=tasks_data,
        rubric_json=outcome.rubric
    )
    db.add(db_outcome)
    db.commit()
    db.refresh(db_outcome)
    return outcome # Return schema for response

def create_proof(db: Session, proof: schemas.ProofCreate):
    db_proof = models.Proof(
        outcome_id=proof.job_id,
        candidate_id=proof.candidate_id,
        type=proof.type,
        payload_json=proof.payload
    )
    db.add(db_proof)
    db.commit()
    db.refresh(db_proof)
    # Return schema
    return proof

def get_proofs(db: Session, outcome_id: str):
    return db.query(models.Proof).filter(models.Proof.outcome_id == outcome_id).all()

def create_evaluation(db: Session, evaluation: schemas.EvaluationResponse):
    db_eval = models.Evaluation(
        job_id=evaluation.job_id,
        outcome_id=evaluation.job_id,
        evaluation_json=evaluation.dict(),
        fit_score=evaluation.fit_score
    )
    db.add(db_eval)
    db.commit()
    db.refresh(db_eval)
    db.refresh(db_eval)
    return db_eval

def get_evaluations(db: Session):
    return db.query(models.Evaluation).order_by(desc(models.Evaluation.created_at)).all()

def get_evaluation_summaries(db: Session):
    # Join Evaluation and Outcome to get the title
    results = db.query(models.Evaluation, models.Outcome).join(models.Outcome, models.Evaluation.outcome_id == models.Outcome.id).order_by(desc(models.Evaluation.created_at)).all()
    
    summaries = []
    for eval_model, outcome_model in results:
        eval_data = eval_model.evaluation_json
        summaries.append({
            "job_id": eval_model.job_id,
            "outcome_title": outcome_model.title,
            "fit_score": eval_model.fit_score,
            "human_action_required": eval_data.get("human_action_required", True),
            "risk_flags": eval_data.get("risk_flags", []),
            "created_at": eval_model.created_at
        })
    return summaries

def get_signal_weights(db: Session):
    return db.query(models.SignalWeight).all()

def update_signal_weight(db: Session, signal_name: str, weight: float, task_id: str = None):
    # Check if exists
    query = db.query(models.SignalWeight).filter(models.SignalWeight.signal_name == signal_name)
    if task_id:
        query = query.filter(models.SignalWeight.task_id == task_id)
    
    db_weight = query.first()
    if db_weight:
        db_weight.weight = weight
    else:
        db_weight = models.SignalWeight(signal_name=signal_name, weight=weight, task_id=task_id)
        db.add(db_weight)
    db.commit()
    return db_weight

def create_feedback(db: Session, feedback: schemas.FeedbackCreate):
    db_feedback = models.Feedback(
        evaluation_id=int(feedback.evaluation_id) if feedback.evaluation_id.isdigit() else None,
        job_id=feedback.job_id,
        result=feedback.result,
        metrics_json=feedback.metrics
    )
    db.add(db_feedback)
    db.commit()
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

def get_audit_logs(db: Session):
    return db.query(models.AuditLog).order_by(desc(models.AuditLog.created_at)).limit(100).all()

def create_audit_log(db: Session, entity_type: str, entity_id: str, action: str, details: dict = None):
    """Create an audit log entry."""
    db_log = models.AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        details_json=details or {}
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_feedback_list(db: Session):
    """Get all feedback entries for System Learning page."""
    return db.query(models.Feedback).order_by(desc(models.Feedback.created_at)).limit(100).all()
