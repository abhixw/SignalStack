from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.pipeline.outcome import OutcomePipeline

router = APIRouter(tags=["Outcome"])

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
    pipeline = OutcomePipeline(db)
    existing_outcome = pipeline.get_outcome(outcome.id)
    if existing_outcome:
        raise HTTPException(status_code=400, detail="Outcome already exists")
    result = pipeline.create_outcome(outcome)
    # Audit Log
    crud.create_audit_log(db, "outcome", outcome.id, "created", {"title": outcome.title})
    return result

@router.get("/outcomes/{outcome_id}", response_model=schemas.OutcomeCreate)
def get_outcome(outcome_id: str, db: Session = Depends(get_db)):
    pipeline = OutcomePipeline(db)
    outcome = pipeline.get_outcome(outcome_id)
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
