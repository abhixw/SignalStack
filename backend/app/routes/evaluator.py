from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.asynchronous.database import AsyncDatabase
from typing import List
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.pipeline.evaluator import Evaluator
from app.pipeline.signal_extractor import SignalExtractor
from app.deps.auth import require_roles
from app.constants import UserRole
from app.services.errors import UpstreamServiceError
from app.services.llm import GroqLLMService

router = APIRouter(tags=["Evaluator"])

CANDIDATE_DECISIONS = ("advancing", "rejected")


async def _assert_owns_outcome(db: AsyncDatabase, outcome_id: str, current_user: dict) -> dict:
    outcome = await crud.get_outcome(db, outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    owner_id = outcome.get("owner_id")
    if current_user["role"] != UserRole.ADMIN and owner_id and owner_id != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="You do not own this outcome")
    return outcome


@router.post("/plugin/evaluate")
async def evaluate(
    request: schemas.EvaluateRequest,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    outcome_doc = await _assert_owns_outcome(db, request.outcome.id, current_user)

    # Re-evaluating (e.g. a new candidate applied after some others were
    # already decided) must never silently un-decide someone a recruiter
    # already advanced/rejected — carry those forward into the new run.
    previous = await crud.get_evaluation_by_job_id(db, request.outcome.id)
    previous_decisions = (previous or {}).get("evaluation", {}).get("candidate_decisions", {})
    previous_feedback = (previous or {}).get("evaluation", {}).get("candidate_feedback", {})

    # 1. Extract Signals
    signals_map = {}
    extractor = SignalExtractor()
    for proof in request.proofs:
        signals = extractor.extract_signals(proof)

        # candidate_id is the candidate's email (see ProofCreate/submit_proof) —
        # dsa_proficiency is read from whatever Codeforces/LeetCode fetch was
        # cached the last time the candidate updated their coding profiles
        # (POST/PATCH /candidate/coding-profiles), not fetched live here, so an
        # external API being down can never break an evaluation run.
        candidate = await crud.get_user_by_email(db, proof.candidate_id)
        coding_profiles = (candidate or {}).get("coding_profiles") or {}
        signals["dsa_proficiency"] = coding_profiles.get("dsa_proficiency", 0.0)

        signals_map[proof.candidate_id] = signals

    # 2. Evaluate using Allocation Engine
    evaluator = Evaluator()
    evaluation = evaluator.evaluate(request.outcome, request.proofs, signals_map)
    evaluation.candidate_decisions = {**previous_decisions, **evaluation.candidate_decisions}
    evaluation.candidate_feedback = {**previous_feedback, **evaluation.candidate_feedback}

    # 3. Store Evaluation (Persist the result, denormalizing the outcome title)
    await crud.create_evaluation(db, evaluation, outcome_title=outcome_doc.get("title", ""))

    # 4. Audit Log
    await crud.create_audit_log(db, "evaluation", evaluation.job_id, "completed", {"fit_score": evaluation.fit_score, "candidate_count": len(request.proofs)})

    return {
        "job_id": evaluation.job_id,
        "status": "completed",
        "evaluation": evaluation
    }


@router.get("/evaluations", response_model=List[schemas.EvaluationSummary])
async def get_evaluations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    # Recruiters only see evaluations for outcomes they own; admins see all.
    owner_id = None if current_user["role"] == UserRole.ADMIN else str(current_user["_id"])
    return await crud.get_evaluation_summaries(db, owner_id=owner_id, offset=(page - 1) * page_size, limit=page_size)


@router.get("/outcomes/{outcome_id}/candidates")
async def get_candidate_roster(
    outcome_id: str,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    """One row per candidate who applied — name/GitHub username enriched from
    their account, plus whatever evaluation state exists so far. This is what
    the recruiter dashboard lists instead of raw proofs; there's no separate
    "run evaluation" step surfaced here — scoring happens transparently (see
    the frontend) and a candidate's row just reflects whatever's ready."""
    await _assert_owns_outcome(db, outcome_id, current_user)

    proofs = await crud.get_proofs(db, outcome_id)
    evaluation = await crud.get_evaluation_by_job_id(db, outcome_id)
    eval_body = (evaluation or {}).get("evaluation", {})
    candidate_scores = eval_body.get("candidate_scores", {})
    candidate_decisions = eval_body.get("candidate_decisions", {})

    roster = []
    for proof in proofs:
        candidate_email = proof["candidate_id"]
        user = await crud.get_user_by_email(db, candidate_email)
        roster.append({
            "candidate_id": candidate_email,
            "full_name": (user or {}).get("full_name"),
            "github_username": (user or {}).get("github_username"),
            "applied_at": proof["created_at"],
            "has_score": candidate_email in candidate_scores,
            "decision": candidate_decisions.get(candidate_email),
        })
    return roster


@router.post("/evaluations/{job_id}/decision")
async def set_candidate_decision(
    job_id: str,
    payload: schemas.CandidateDecisionUpdate,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    """The only thing that ever determines what a candidate sees about their
    evaluation (see GET /candidate/my-applications) — the raw score is never
    exposed to them, only this decision."""
    await _assert_owns_outcome(db, job_id, current_user)

    if payload.decision not in CANDIDATE_DECISIONS:
        raise HTTPException(status_code=400, detail=f"decision must be one of: {', '.join(CANDIDATE_DECISIONS)}")

    evaluation = await crud.get_evaluation_by_job_id(db, job_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="No evaluation exists for this job yet")
    if payload.candidate_id not in evaluation.get("evaluation", {}).get("candidate_scores", {}):
        raise HTTPException(status_code=404, detail="This candidate has no score in the latest evaluation")

    updated = await crud.set_candidate_decision(db, job_id, payload.candidate_id, payload.decision, payload.feedback)
    await crud.create_audit_log(
        db, "candidate_decision", job_id, "set",
        {"candidate_id": payload.candidate_id, "decision": payload.decision, "has_feedback": payload.feedback is not None},
    )
    return {
        "candidate_decisions": updated["evaluation"]["candidate_decisions"],
        "candidate_feedback": updated["evaluation"]["candidate_feedback"],
    }


@router.post("/evaluations/{job_id}/feedback/suggest")
async def suggest_candidate_feedback(
    job_id: str,
    payload: schemas.FeedbackSuggestionRequest,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    """Drafts feedback text from this candidate's task scores/reasons —
    doesn't persist or send anything. The recruiter reviews/edits it and it's
    only ever actually sent via POST /evaluations/{job_id}/decision."""
    outcome_doc = await _assert_owns_outcome(db, job_id, current_user)

    evaluation = await crud.get_evaluation_by_job_id(db, job_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="No evaluation exists for this job yet")
    eval_body = evaluation["evaluation"]
    task_scores = eval_body.get("candidate_task_scores", {}).get(payload.candidate_id)
    if task_scores is None:
        raise HTTPException(status_code=404, detail="This candidate has no score in the latest evaluation")
    if payload.decision not in CANDIDATE_DECISIONS:
        raise HTTPException(status_code=400, detail=f"decision must be one of: {', '.join(CANDIDATE_DECISIONS)}")

    try:
        feedback = GroqLLMService().generate_candidate_feedback(
            [schemas.TaskScore(**ts) for ts in task_scores], payload.decision, outcome_doc.get("title", ""),
        )
    except UpstreamServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())

    return {"feedback": feedback}


@router.get("/plugin/status/{job_id}")
async def get_status(
    job_id: str,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    await _assert_owns_outcome(db, job_id, current_user)
    eval_doc = await crud.get_evaluation_by_job_id(db, job_id)
    if eval_doc:
        return {"job_id": job_id, "status": "completed", "evaluation": eval_doc["evaluation"]}
    return {"job_id": job_id, "status": "pending"}
