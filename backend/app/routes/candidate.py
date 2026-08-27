import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.asynchronous.database import AsyncDatabase
from typing import List, Optional
import app.schemas as schemas
from app.config.database import get_db
from app.services import codeforces, crud, dsa_signals, leetcode
from app.services.errors import UpstreamServiceError
from app.deps.auth import require_roles
from app.constants import UserRole

router = APIRouter(tags=["Candidate"])


def _coding_profiles_response(profiles: dict) -> dict:
    return {
        "codeforces_handle": profiles.get("codeforces_handle"),
        "leetcode_username": profiles.get("leetcode_username"),
        "codeforces_stats": profiles.get("codeforces_stats"),
        "leetcode_stats": profiles.get("leetcode_stats"),
        "dsa_proficiency": profiles.get("dsa_proficiency", 0.0),
        "leetcode_fetch_failed": profiles.get("leetcode_fetch_failed", False),
        "updated_at": profiles.get("updated_at"),
    }


async def _refetch_coding_profiles(codeforces_handle: str | None, leetcode_username: str | None) -> dict:
    """Raises HTTPException(400) if a codeforces_handle is set but doesn't
    exist — Codeforces has a real API with a real "not found" contract, so a
    typo is caught immediately. LeetCode has no such contract (unofficial,
    best-effort) — a failed fetch there is stored as "couldn't verify right
    now" rather than rejecting the whole request."""
    codeforces_info = None
    codeforces_counts = None
    if codeforces_handle:
        try:
            codeforces_info = codeforces.fetch_user_info(codeforces_handle)
            codeforces_counts = codeforces.fetch_solved_problem_counts(codeforces_handle)
        except UpstreamServiceError as e:
            if e.error_type == "NOT_FOUND":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Codeforces handle not found.")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not reach Codeforces. Try again shortly.")

    leetcode_stats = None
    leetcode_fetch_failed = False
    if leetcode_username:
        leetcode_stats = leetcode.fetch_user_stats(leetcode_username)
        leetcode_fetch_failed = leetcode_stats is None

    codeforces_score = dsa_signals.score_codeforces(codeforces_info, codeforces_counts)
    leetcode_score = dsa_signals.score_leetcode(leetcode_stats)

    return {
        "codeforces_handle": codeforces_handle,
        "leetcode_username": leetcode_username,
        "codeforces_stats": {"info": codeforces_info, "solved": codeforces_counts} if codeforces_handle else None,
        "leetcode_stats": leetcode_stats,
        "leetcode_fetch_failed": leetcode_fetch_failed,
        "dsa_proficiency": dsa_signals.combine(codeforces_score, leetcode_score),
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
    }


@router.get("/candidate/jobs", response_model=List[schemas.OutcomeCreate])
async def get_candidate_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    job_role: Optional[str] = None,
    db: AsyncDatabase = Depends(get_db),
):
    """List available job postings (Outcomes), optionally filtered to one
    job_role (see app.constants.JobRole). Public — candidates browse before
    logging in."""
    outcomes = await crud.get_outcomes(db, offset=(page - 1) * page_size, limit=page_size, job_role=job_role)
    return [
        schemas.OutcomeCreate(
            id=o["_id"],
            title=o["title"],
            description=o["description"],
            tasks=[schemas.Task(**t) for t in o["tasks"]],
            job_role=o.get("job_role"),
            # Scoring weights are never shown to candidates — see schemas/outcome.py.
        ) for o in outcomes
    ]


@router.get("/candidate/my-applications")
async def get_candidate_applications(
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.CANDIDATE)),
):
    """Get all jobs the AUTHENTICATED candidate has applied for. Identity comes from the JWT —
    never from a client-supplied id — so one candidate can never read another's applications."""
    candidate_user_id = str(current_user["_id"])
    proofs = await crud.get_proofs_for_candidate(db, candidate_user_id)

    results = []
    for proof in proofs:
        outcome = await crud.get_outcome(db, proof["outcome_id"])
        evaluation = await crud.get_evaluation_by_job_id(db, proof["outcome_id"])

        # The raw score is never sent to a candidate — only whichever decision
        # the recruiter has explicitly made (see POST /evaluations/{job_id}/decision).
        # No decision yet is "Under Review" (already scored) or "Pending" (not
        # evaluated at all), never a number either way.
        eval_body = (evaluation or {}).get("evaluation", {})
        was_scored = current_user["email"] in eval_body.get("candidate_scores", {})
        decision = eval_body.get("candidate_decisions", {}).get(current_user["email"])

        if decision == "advancing":
            status_label = "Advancing to Interview"
        elif decision == "rejected":
            status_label = "Rejected"
        elif was_scored:
            status_label = "Under Review"
        else:
            status_label = "Pending"

        results.append({
            "job_id": proof["outcome_id"],
            "job_title": outcome["title"] if outcome else "Unknown",
            "applied_at": proof["created_at"],
            "status": status_label,
        })

    return results


@router.get("/candidate/coding-profiles")
async def get_coding_profiles(
    current_user: dict = Depends(require_roles(UserRole.CANDIDATE)),
):
    """The authenticated candidate's own stored Codeforces/LeetCode handles +
    the most recently fetched stats. Self-reported — no ownership
    verification exists for either platform (unlike GitHub)."""
    return _coding_profiles_response(current_user.get("coding_profiles") or {})


@router.patch("/candidate/coding-profiles")
async def update_coding_profiles(
    payload: schemas.CodingProfilesUpdate,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.CANDIDATE)),
):
    """Sets and immediately fetches+caches stats for whichever handle(s) are
    provided. None = leave that field unchanged; "" = clear it; a real value
    replaces it and triggers a fresh fetch — stats are cached here, not
    re-fetched live at evaluation time (see POST .../refresh to update them
    later without changing the handles)."""
    existing = current_user.get("coding_profiles") or {}

    codeforces_handle = existing.get("codeforces_handle")
    if payload.codeforces_handle is not None:
        codeforces_handle = payload.codeforces_handle.strip() or None

    leetcode_username = existing.get("leetcode_username")
    if payload.leetcode_username is not None:
        leetcode_username = payload.leetcode_username.strip() or None

    profiles = await _refetch_coding_profiles(codeforces_handle, leetcode_username)
    await crud.update_candidate_coding_profiles(db, current_user["_id"], profiles)
    return _coding_profiles_response(profiles)


@router.post("/candidate/coding-profiles/refresh")
async def refresh_coding_profiles(
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.CANDIDATE)),
):
    """Re-fetches stats for whichever handles are already stored — for
    updating a score after solving more problems, without re-typing handles."""
    existing = current_user.get("coding_profiles") or {}
    profiles = await _refetch_coding_profiles(existing.get("codeforces_handle"), existing.get("leetcode_username"))
    await crud.update_candidate_coding_profiles(db, current_user["_id"], profiles)
    return _coding_profiles_response(profiles)
