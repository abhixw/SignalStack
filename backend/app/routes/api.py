from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict

from app.models import models
from app.schemas import schemas
from app.services import crud
from app.config.database import get_db
from app.dependencies import signal_extractor, allocation_engine

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "service": "SignalLayer Backend"}

@router.get("/outcomes", response_model=List[schemas.OutcomeCreate])
def get_outcomes(db: Session = Depends(get_db)):
    outcomes = crud.get_outcomes(db)
    return [
        schemas.OutcomeCreate(
            id=o.id,
            title=o.title,
            description=o.description,
            tasks=[schemas.Task(**t) for t in o.tasks_json],
            rubric=o.rubric_json
        ) for o in outcomes
    ]

@router.post("/outcomes", response_model=schemas.OutcomeCreate)
def create_outcome(outcome: schemas.OutcomeCreate, db: Session = Depends(get_db)):
    existing_outcome = crud.get_outcome(db, outcome.id)
    if existing_outcome:
        raise HTTPException(status_code=400, detail="Outcome already exists")
    result = crud.create_outcome(db, outcome)
    # Audit Log
    crud.create_audit_log(db, "outcome", outcome.id, "created", {"title": outcome.title})
    return result

@router.post("/proofs", response_model=schemas.ProofCreate)
def submit_proof(proof: schemas.ProofCreate, db: Session = Depends(get_db)):
    # Verify outcome exists
    if proof.job_id:
        outcome = crud.get_outcome(db, proof.job_id)
        if not outcome:
            raise HTTPException(status_code=404, detail="Outcome not found")
    result = crud.create_proof(db, proof)
    # Audit Log
    crud.create_audit_log(db, "proof", proof.job_id, "submitted", {"candidate": proof.candidate_id, "type": proof.type})
    return result

@router.get("/outcomes/{outcome_id}", response_model=schemas.OutcomeCreate)
def get_outcome(outcome_id: str, db: Session = Depends(get_db)):
    outcome = crud.get_outcome(db, outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    # Convert tasks_json to list of Task objects
    tasks = [schemas.Task(**t) for t in outcome.tasks_json]
    return schemas.OutcomeCreate(
        id=outcome.id,
        title=outcome.title,
        description=outcome.description,
        tasks=tasks,
        rubric=outcome.rubric_json
    )

@router.get("/proofs/{job_id}", response_model=List[schemas.ProofCreate])
def get_proofs(job_id: str, db: Session = Depends(get_db)):
    proofs = crud.get_proofs(db, job_id)
    return [schemas.ProofCreate(
        job_id=p.outcome_id,
        candidate_id=p.candidate_id,
        type=p.type,
        payload=p.payload_json
    ) for p in proofs]

@router.post("/plugin/evaluate")
def evaluate(request: schemas.EvaluateRequest, db: Session = Depends(get_db)):
    # 1. Extract Signals
    signals_map = {}
    for proof in request.proofs:
        signals = signal_extractor.extract_signals(proof)
        signals_map[proof.candidate_id] = signals
    
    # 2. Evaluate using Allocation Engine
    evaluation = allocation_engine.evaluate(request.outcome, request.proofs, signals_map)
    
    # 3. Store Evaluation (Persist the result)
    crud.create_evaluation(db, evaluation)
    
    # 4. Audit Log
    crud.create_audit_log(db, "evaluation", evaluation.job_id, "completed", {"fit_score": evaluation.fit_score, "candidates": [p.candidate_id for p in request.proofs]})
    
    return {
        "job_id": evaluation.job_id,
        "status": "completed",
        "evaluation": evaluation
    }

@router.get("/evaluations", response_model=List[schemas.EvaluationSummary])
def get_evaluations(db: Session = Depends(get_db)):
    return crud.get_evaluation_summaries(db)

@router.get("/plugin/status/{job_id}")
def get_status(job_id: str, db: Session = Depends(get_db)):
    # For MVP, we just check if evaluation exists
    # In real async system, this would check job queue
    eval_db = db.query(models.Evaluation).filter(models.Evaluation.job_id == job_id).first()
    if eval_db:
        return {"job_id": job_id, "status": "completed", "evaluation": eval_db.evaluation_json}
    return {"job_id": job_id, "status": "pending"}

@router.post("/plugin/feedback")
def submit_feedback(feedback: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    # Store feedback
    crud.create_feedback(db, feedback)
    
    # Trigger Learning Loop (Update Weights)
    changes = []
    if feedback.evaluation_id:
        # Fetch evaluation to see which signals were used
        # Note: Check if evaluation_id is int or str in schema vs model. Model has int. Schema str?
        # In crud.py: evaluation_id=int(feedback.evaluation_id) if feedback.evaluation_id.isdigit() else None
        
        eval_id = int(feedback.evaluation_id) if feedback.evaluation_id and feedback.evaluation_id.isdigit() else None
        
        eval_db = None
        if eval_id:
            eval_db = db.query(models.Evaluation).filter(models.Evaluation.id == eval_id).first()
        
        if not eval_db and feedback.job_id:
             eval_db = db.query(models.Evaluation).filter(models.Evaluation.job_id == feedback.job_id).first()
             
        if eval_db:
            eval_data = eval_db.evaluation_json
            signals_used = eval_data.get("global_signals_used", [])
            
            # Adjust weights based on result
            adjustment = 0.1 if feedback.result == "success" else -0.1
            
            for signal in signals_used:
                # Get current weight (default 1.0 if not found)
                current_weight_obj = db.query(models.SignalWeight).filter(models.SignalWeight.signal_name == signal).first()
                current_weight = current_weight_obj.weight if current_weight_obj else 1.0
                
                new_weight = max(0.1, min(2.0, current_weight + adjustment)) # Clamp between 0.1 and 2.0
                crud.update_signal_weight(db, signal, new_weight)
                changes.append(f"Updated {signal} to {new_weight:.2f}")
    
    if not changes:
        changes.append("No signals found to update")
        
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

@router.post("/plugin/suggest-tasks", response_model=List[schemas.TaskSuggestion])
def suggest_tasks(request: schemas.TaskSuggestionRequest, db: Session = Depends(get_db)):
    tasks = allocation_engine.llm_service.generate_tasks(request.description)
    return [schemas.TaskSuggestion(**t) for t in tasks]

@router.get("/plugin/repo-preview")
def get_repo_preview(repo_url: str):
    if not repo_url or "github.com" not in repo_url:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    
    files, default_branch = signal_extractor.github.get_recursive_tree(repo_url)
    if not files:
        return {"name": "Repository Not Found", "files": [], "readme": ""}
        
    # Fetch README
    readme_content = ""
    readme_file = next((f for f in files if f.lower().startswith('readme')), None)
    if readme_file:
        readme_content = signal_extractor.github.get_file_content(repo_url, readme_file)
        
    return {
        "name": repo_url.rstrip('/').split('/')[-1],
        "files": files[:10], # Limit to top 10 for preview
        "readme": readme_content[:500] + "..." if len(readme_content) > 500 else readme_content
    }
