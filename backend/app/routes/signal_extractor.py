from fastapi import APIRouter, Depends, HTTPException
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError
from typing import List
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.pipeline.signal_extractor import SignalExtractor
from app.deps.auth import get_current_user, require_roles
from app.constants import UserRole
from app.services.errors import UpstreamServiceError

_ALREADY_APPLIED_MESSAGE = "You have already applied to this outcome."

router = APIRouter(tags=["Signal Extractor"])


@router.post("/proofs", response_model=schemas.ProofCreate)
async def submit_proof(
    proof: schemas.ProofCreate,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.CANDIDATE)),
):
    if proof.job_id:
        outcome = await crud.get_outcome(db, proof.job_id)
        if not outcome:
            raise HTTPException(status_code=404, detail="Outcome not found")

    # A candidate must have a GitHub account verified via OAuth before they can
    # submit any proof, and the submitted repo must belong to THAT verified
    # account — otherwise anyone could submit someone else's public repo.
    github_username = current_user.get("github_username")
    if not github_username:
        raise HTTPException(
            status_code=403,
            detail="Connect your GitHub account before submitting a proof.",
        )

    repo_url = proof.payload.get("repo_url", "")
    extractor = SignalExtractor()
    try:
        owner, _ = extractor.github._normalize_repo_url(repo_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")

    if owner.lower() != github_username.lower():
        raise HTTPException(
            status_code=403,
            detail=f"This repository does not belong to your verified GitHub account (@{github_username}).",
        )

    # Identity is derived from the authenticated JWT, never trusted from the request body.
    proof.candidate_id = current_user["email"]
    candidate_user_id = str(current_user["_id"])

    existing = await crud.get_proof_for_candidate_outcome(db, proof.job_id, candidate_user_id)
    if existing:
        raise HTTPException(status_code=409, detail=_ALREADY_APPLIED_MESSAGE)

    try:
        result = await crud.create_proof(db, proof, candidate_user_id=candidate_user_id)
    except DuplicateKeyError:
        # Race: two submissions for the same outcome landed concurrently — the
        # unique index is the real guard, the check above is just the common case.
        raise HTTPException(status_code=409, detail=_ALREADY_APPLIED_MESSAGE)

    await crud.create_audit_log(db, "proof", proof.job_id, "submitted", {"candidate_user_id": candidate_user_id, "type": proof.type})
    return schemas.ProofCreate(
        job_id=result["outcome_id"],
        candidate_id=result["candidate_id"],
        type=result["type"],
        payload=result["payload"],
    )


@router.get("/proofs/{job_id}", response_model=List[schemas.ProofCreate])
async def get_proofs(
    job_id: str,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN)),
):
    # Recruiters may only see proofs for outcomes they own; admins see everything.
    outcome = await crud.get_outcome(db, job_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    owner_id = outcome.get("owner_id")
    if current_user["role"] != UserRole.ADMIN and owner_id and owner_id != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="You do not own this outcome")

    proofs = await crud.get_proofs(db, job_id)
    return [schemas.ProofCreate(
        job_id=p["outcome_id"],
        candidate_id=p["candidate_id"],
        type=p["type"],
        payload=p["payload"]
    ) for p in proofs]


@router.get("/plugin/repo-preview")
async def get_repo_preview(repo_url: str, current_user: dict = Depends(get_current_user)):
    if not repo_url or "github.com" not in repo_url:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    extractor = SignalExtractor()
    try:
        files, default_branch = extractor.github.get_recursive_tree_or_raise(repo_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    except UpstreamServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())

    if not files:
        return {"name": repo_url.rstrip('/').split('/')[-1], "files": [], "readme": ""}

    readme_content = ""
    readme_file = next((f for f in files if f.lower().startswith('readme')), None)
    if readme_file:
        readme_content = extractor.github.get_file_content(repo_url, readme_file)

    return {
        "name": repo_url.rstrip('/').split('/')[-1],
        "files": files[:10],
        "readme": readme_content[:500] + "..." if len(readme_content) > 500 else readme_content
    }
