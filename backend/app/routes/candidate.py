from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
import app.models as models

router = APIRouter(tags=["Candidate"])

@router.get("/candidate/jobs", response_model=List[schemas.OutcomeCreate])
def get_candidate_jobs(db: Session = Depends(get_db)):
    """List all available job postings (Outcomes)."""
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

@router.get("/candidate/my-applications/{candidate_id}")
def get_candidate_applications(candidate_id: str, db: Session = Depends(get_db)):
    """Get all jobs a candidate has applied for and their status/results."""
    # 1. Get all proofs by this candidate
    proofs = db.query(models.Proof).filter(models.Proof.candidate_id == candidate_id).all()
    
    results = []
    for proof in proofs:
        # Get outcome details
        outcome = crud.get_outcome(db, proof.outcome_id)
        
        # Get evaluation if exists
        evaluation = db.query(models.Evaluation).filter(models.Evaluation.job_id == proof.outcome_id).first()
        
        personal_score = None
        if evaluation:
            eval_data = evaluation.evaluation_json
            candidate_scores = eval_data.get("candidate_scores", {})
            personal_score = candidate_scores.get(candidate_id)
        
        results.append({
            "job_id": proof.outcome_id,
            "job_title": outcome.title if outcome else "Unknown",
            "applied_at": proof.created_at,
            "status": "Evaluated" if personal_score is not None else "Pending",
            "score": personal_score
        })
    
    return results
