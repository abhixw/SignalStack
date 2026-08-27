from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.asynchronous.database import AsyncDatabase
from typing import List, Optional
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.deps.auth import require_roles
from app.constants import JobRole, UserRole

router = APIRouter(tags=["Outcome"])


def _to_schema(o: dict, include_rubric: bool = False) -> schemas.OutcomeCreate:
    # include_rubric=False (the default) hides the real scoring weights — used
    # for every publicly-reachable read. Only pass True for an authenticated
    # owner/admin action that's meant to confirm their own data back to them.
    return schemas.OutcomeCreate(
        id=o["_id"] if "_id" in o else o["id"],
        title=o["title"],
        description=o["description"],
        tasks=[schemas.Task(**t) for t in o["tasks"]],
        rubric=o["rubric"] if include_rubric else {},
        job_role=o.get("job_role"),
    )


def _validate_job_role(job_role: Optional[str]) -> None:
    if job_role is not None and job_role not in JobRole.ALL:
        raise HTTPException(status_code=400, detail=f"Invalid job_role. Must be one of: {', '.join(JobRole.ALL)}")


@router.get("/job-roles", response_model=List[str])
async def get_job_roles():
    # Single source of truth for the fixed list both the recruiter's "create
    # outcome" dropdown and the candidate's "filter jobs" dropdown read from.
    return list(JobRole.ALL)


@router.get("/outcomes", response_model=List[schemas.OutcomeCreate])
async def get_outcomes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    job_role: Optional[str] = None,
    db: AsyncDatabase = Depends(get_db),
):
    # Public, unauthenticated job discovery — deliberately not gated behind auth.
    outcomes = await crud.get_outcomes(db, offset=(page - 1) * page_size, limit=page_size, job_role=job_role)
    return [_to_schema(o) for o in outcomes]


@router.post("/outcomes", response_model=schemas.OutcomeCreate)
async def create_outcome(
    outcome: schemas.OutcomeCreate,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    _validate_job_role(outcome.job_role)
    existing_outcome = await crud.get_outcome(db, outcome.id)
    if existing_outcome:
        raise HTTPException(status_code=400, detail="Outcome already exists")
    await crud.create_outcome(db, outcome, owner_id=str(current_user["_id"]))
    await crud.create_audit_log(db, "outcome", outcome.id, "created", {"title": outcome.title, "owner_id": str(current_user["_id"])})
    return outcome


@router.get("/outcomes/mine", response_model=List[schemas.OutcomeCreate])
async def get_my_outcomes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    """Registered before /outcomes/{outcome_id} so "mine" is never swallowed as
    a path param. Recruiters see only outcomes they own; admins see all —
    same scoping rule already used for GET /evaluations."""
    owner_id = None if current_user["role"] == UserRole.ADMIN else str(current_user["_id"])
    outcomes = await crud.get_outcomes(db, offset=(page - 1) * page_size, limit=page_size, owner_id=owner_id)
    return [_to_schema(o, include_rubric=True) for o in outcomes]


@router.get("/outcomes/{outcome_id}", response_model=schemas.OutcomeCreate)
async def get_outcome(outcome_id: str, db: AsyncDatabase = Depends(get_db)):
    # Public — this is the data source behind the SEO job pages / candidate browsing.
    outcome = await crud.get_outcome(db, outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return _to_schema(outcome)


@router.put("/outcomes/{outcome_id}", response_model=schemas.OutcomeCreate)
async def update_outcome(
    outcome_id: str,
    outcome: schemas.OutcomeCreate,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    _validate_job_role(outcome.job_role)
    existing = await crud.get_outcome(db, outcome_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Outcome not found")
    owner_id = existing.get("owner_id")
    if current_user["role"] != UserRole.ADMIN and owner_id and owner_id != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="You do not own this outcome")

    updated = await crud.update_outcome(db, outcome_id, outcome)
    await crud.create_audit_log(db, "outcome", outcome_id, "updated", {"title": outcome.title})
    return _to_schema(updated, include_rubric=True)
