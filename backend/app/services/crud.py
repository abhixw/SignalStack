import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.asynchronous.database import AsyncDatabase

import app.schemas as schemas
from app.config.database import oid_str


def _doc_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Copy a Mongo document with `_id` renamed/stringified to `id` for API responses."""
    if doc is None:
        return None
    out = dict(doc)
    out["id"] = oid_str(out.pop("_id"))
    return out


def _try_object_id(value: Optional[str]) -> Optional[ObjectId]:
    if not value:
        return None
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


# ---------------------------------------------------------------------------
# Outcomes — _id is the client-supplied string `outcome.id` (preserves the
# original SQL behavior where recruiters choose the id and duplicates 400).
# ---------------------------------------------------------------------------

async def get_outcome(db: AsyncDatabase, outcome_id: str) -> Optional[dict]:
    return await db.outcomes.find_one({"_id": outcome_id})


async def get_outcomes(
    db: AsyncDatabase, offset: int = 0, limit: int = 20,
    owner_id: Optional[str] = None, job_role: Optional[str] = None,
) -> List[dict]:
    query = {}
    if owner_id is not None:
        query["owner_id"] = owner_id
    if job_role is not None:
        query["job_role"] = job_role
    cursor = db.outcomes.find(query).sort("created_at", -1).skip(offset).limit(limit)
    return await cursor.to_list(length=limit)


async def count_outcomes(db: AsyncDatabase) -> int:
    return await db.outcomes.count_documents({})


async def create_outcome(db: AsyncDatabase, outcome: schemas.OutcomeCreate, owner_id: Optional[str] = None) -> dict:
    doc = {
        "_id": outcome.id,
        "title": outcome.title,
        "description": outcome.description,
        "tasks": [t.model_dump() for t in outcome.tasks],
        "rubric": outcome.rubric,
        "job_role": outcome.job_role,
        "owner_id": owner_id,
        "is_public": True,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    await db.outcomes.insert_one(doc)
    return doc


async def update_outcome(db: AsyncDatabase, outcome_id: str, outcome: schemas.OutcomeCreate) -> Optional[dict]:
    update = {
        "title": outcome.title,
        "description": outcome.description,
        "tasks": [t.model_dump() for t in outcome.tasks],
        "rubric": outcome.rubric,
        "job_role": outcome.job_role,
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
    }
    result = await db.outcomes.find_one_and_update(
        {"_id": outcome_id}, {"$set": update}, return_document=True
    )
    return result


# ---------------------------------------------------------------------------
# Proofs — _id is an ObjectId. `outcome_id` and `candidate_user_id` are plain
# string references (application-level integrity, not a Mongo-enforced FK).
# ---------------------------------------------------------------------------

async def create_proof(db: AsyncDatabase, proof: schemas.ProofCreate, candidate_user_id: Optional[str] = None) -> dict:
    doc = {
        "outcome_id": proof.job_id,
        "candidate_id": proof.candidate_id,
        "candidate_user_id": candidate_user_id,
        "type": proof.type,
        "payload": proof.payload,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    result = await db.proofs.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_proofs(db: AsyncDatabase, outcome_id: str) -> List[dict]:
    cursor = db.proofs.find({"outcome_id": outcome_id}).sort("created_at", -1)
    return await cursor.to_list(length=None)


async def get_proofs_for_candidate(db: AsyncDatabase, candidate_user_id: str) -> List[dict]:
    cursor = db.proofs.find({"candidate_user_id": candidate_user_id}).sort("created_at", -1)
    return await cursor.to_list(length=None)


async def get_proof_for_candidate_outcome(db: AsyncDatabase, outcome_id: str, candidate_user_id: str) -> Optional[dict]:
    """Used to block a second application to the same outcome by the same candidate."""
    return await db.proofs.find_one({"outcome_id": outcome_id, "candidate_user_id": candidate_user_id})


# ---------------------------------------------------------------------------
# Evaluations — evaluation_json's contents are embedded directly (this mirrors
# the pre-migration SQL schema, which already stored the whole EvaluationResponse
# as one JSON blob). `outcome_title` is denormalized at write time so listing
# evaluations never needs an application-level join for the common read path.
# ---------------------------------------------------------------------------

async def create_evaluation(db: AsyncDatabase, evaluation: schemas.EvaluationResponse, outcome_title: str = "") -> dict:
    doc = {
        "job_id": evaluation.job_id,
        "outcome_id": evaluation.job_id,
        "outcome_title": outcome_title,
        "evaluation": evaluation.model_dump(),
        "fit_score": evaluation.fit_score,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    result = await db.evaluations.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_evaluation_by_job_id(db: AsyncDatabase, job_id: str) -> Optional[dict]:
    cursor = db.evaluations.find({"job_id": job_id}).sort("created_at", -1).limit(1)
    results = await cursor.to_list(length=1)
    return results[0] if results else None


async def set_candidate_decision(
    db: AsyncDatabase, job_id: str, candidate_id: str, decision: str, feedback: Optional[str] = None
) -> Optional[dict]:
    """Sets on the LATEST evaluation for job_id — re-running an evaluation
    inserts a new doc (see create_evaluation), so a decision always applies to
    whichever run the recruiter is actually looking at.

    candidate_id is an email — it WILL contain ".", so it can never be used as
    a raw `$set` path segment (e.g. f"...candidate_decisions.{candidate_id}"):
    Mongo parses dots in a `$set` PATH as nested-field separators, which would
    silently split "name@example.com" into nested "example"/"com" fields
    instead of one key. Read-modify-write the whole dict instead, the same
    way candidate_scores/candidate_task_scores are safely written elsewhere —
    dots inside a dict VALUE's keys are never path-parsed, only a path
    STRING's dots are."""
    latest = await get_evaluation_by_job_id(db, job_id)
    if not latest:
        return None
    decisions = dict(latest.get("evaluation", {}).get("candidate_decisions") or {})
    decisions[candidate_id] = decision
    update = {"evaluation.candidate_decisions": decisions}

    feedback_map = dict(latest.get("evaluation", {}).get("candidate_feedback") or {})
    if feedback is not None:
        feedback_map[candidate_id] = feedback
        update["evaluation.candidate_feedback"] = feedback_map

    await db.evaluations.update_one({"_id": latest["_id"]}, {"$set": update})

    latest["evaluation"]["candidate_decisions"] = decisions
    latest["evaluation"]["candidate_feedback"] = feedback_map
    return latest


async def get_evaluation_summaries(
    db: AsyncDatabase, owner_id: Optional[str] = None, offset: int = 0, limit: int = 20
) -> List[dict]:
    query: Dict[str, Any] = {}
    if owner_id is not None:
        # Application-level "join": outcomes owned by this recruiter, then
        # evaluations for those outcomes. Simpler and easier to reason about
        # than an aggregation $lookup for this collection's expected size.
        owned_cursor = db.outcomes.find({"owner_id": owner_id}, {"_id": 1})
        owned_ids = [doc["_id"] async for doc in owned_cursor]
        query["outcome_id"] = {"$in": owned_ids}

    cursor = db.evaluations.find(query).sort("created_at", -1).skip(offset).limit(limit)
    docs = await cursor.to_list(length=limit)

    summaries = []
    for d in docs:
        eval_data = d.get("evaluation", {})
        summaries.append({
            "job_id": d["job_id"],
            "outcome_title": d.get("outcome_title", ""),
            "fit_score": d["fit_score"],
            "human_action_required": eval_data.get("human_action_required", True),
            "risk_flags": eval_data.get("risk_flags", []),
            "created_at": d["created_at"],
        })
    return summaries


# ---------------------------------------------------------------------------
# Signal weights
# ---------------------------------------------------------------------------

async def get_signal_weights(db: AsyncDatabase) -> List[dict]:
    return await db.signal_weights.find().to_list(length=None)


async def update_signal_weight(db: AsyncDatabase, signal_name: str, weight: float, task_id: Optional[str] = None) -> dict:
    query = {"signal_name": signal_name, "task_id": task_id}
    update = {
        "$set": {"weight": weight, "updated_at": datetime.datetime.now(datetime.timezone.utc)},
        "$setOnInsert": {"signal_name": signal_name, "task_id": task_id},
    }
    result = await db.signal_weights.find_one_and_update(
        query, update, upsert=True, return_document=True
    )
    return result


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

async def create_feedback(db: AsyncDatabase, feedback: schemas.FeedbackCreate) -> dict:
    doc = {
        "evaluation_id": _try_object_id(feedback.evaluation_id),
        "job_id": feedback.job_id,
        "result": feedback.result,
        "metrics": feedback.metrics,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    result = await db.feedback.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_feedback_list(db: AsyncDatabase, offset: int = 0, limit: int = 100) -> List[dict]:
    cursor = db.feedback.find().sort("created_at", -1).skip(offset).limit(limit)
    return await cursor.to_list(length=limit)


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

async def get_audit_logs(db: AsyncDatabase, offset: int = 0, limit: int = 100) -> List[dict]:
    cursor = db.audit_logs.find().sort("created_at", -1).skip(offset).limit(limit)
    return await cursor.to_list(length=limit)


async def create_audit_log(db: AsyncDatabase, entity_type: str, entity_id: str, action: str, details: Optional[dict] = None) -> dict:
    """`details` must never contain secrets/tokens."""
    doc = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "details": details or {},
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    result = await db.audit_logs.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def get_user_by_email(db: AsyncDatabase, email: str) -> Optional[dict]:
    return await db.users.find_one({"email": email})


async def get_user_by_id(db: AsyncDatabase, user_id: str) -> Optional[dict]:
    oid = _try_object_id(user_id)
    if oid is None:
        return None
    return await db.users.find_one({"_id": oid})


async def create_user(
    db: AsyncDatabase,
    email: str,
    hashed_password: Optional[str],
    role: str,
    full_name: Optional[str],
    github_id: Optional[int] = None,
    github_username: Optional[str] = None,
) -> dict:
    doc = {
        "email": email,
        "hashed_password": hashed_password,  # None for a GitHub-only account
        "role": role,
        "full_name": full_name,
        "github_id": github_id,
        "github_username": github_username,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def update_user_password(db: AsyncDatabase, user_id, hashed_password: str) -> None:
    await db.users.update_one({"_id": user_id}, {"$set": {"hashed_password": hashed_password}})


async def get_user_by_github_id(db: AsyncDatabase, github_id: int) -> Optional[dict]:
    return await db.users.find_one({"github_id": github_id})


async def link_github_to_user(db: AsyncDatabase, user_id, github_id: int, github_username: str) -> None:
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"github_id": github_id, "github_username": github_username}},
    )


async def update_candidate_coding_profiles(db: AsyncDatabase, user_id, coding_profiles: dict) -> None:
    """`coding_profiles` is the whole nested doc — handles, raw stats, and the
    normalized `dsa_proficiency` score Matcher reads at evaluation time (see
    app/services/dsa_signals.py). Self-reported: unlike GitHub, neither
    Codeforces nor LeetCode has an OAuth flow to verify handle ownership."""
    await db.users.update_one({"_id": user_id}, {"$set": {"coding_profiles": coding_profiles}})


# ---------------------------------------------------------------------------
# GitHub OAuth state (CSRF protection + carrying the "connect to this
# already-logged-in user" intent across the redirect to GitHub and back)
# ---------------------------------------------------------------------------

async def create_oauth_state(
    db: AsyncDatabase,
    state: str,
    user_id: Optional[str],
    expires_at,
    return_to: Optional[str] = None,
    registration_id: Optional[str] = None,
) -> dict:
    doc = {
        "state": state,
        "user_id": user_id,  # set only for an authenticated "connect GitHub" flow
        "registration_id": registration_id,  # set only for the password-signup + GitHub-verify flow
        "return_to": return_to,
        "expires_at": expires_at,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    await db.oauth_states.insert_one(doc)
    return doc


async def consume_oauth_state(db: AsyncDatabase, state: str) -> Optional[dict]:
    """Single-use: deletes the state doc as it reads it, so a callback URL
    (or a copy of it) can never be replayed."""
    return await db.oauth_states.find_one_and_delete({"state": state})


# ---------------------------------------------------------------------------
# GitHub OAuth pending-verification (email OTP step-up)
#
# GitHub identifying the user is NOT enough to complete login/signup/link —
# it only proves control of a GitHub session, which may already be
# authenticated in a shared browser. Nothing is created/linked/logged-in
# until the matching email OTP is verified too.
# ---------------------------------------------------------------------------

async def create_github_pending(
    db: AsyncDatabase,
    pending_token: str,
    flow: str,  # "login" | "signup" | "connect" | "register_verify"
    expires_at,
    email: str,
    user_id: Optional[str] = None,          # set for "login" and "connect"
    full_name: Optional[str] = None,        # set for "signup" and "register_verify"
    github_id: Optional[int] = None,
    github_username: Optional[str] = None,
    password_hash: Optional[str] = None,    # set for "register_verify" (chosen at the signup form)
    return_to: Optional[str] = None,
) -> dict:
    """No OTP is generated/sent yet — the candidate must first correctly type
    the email AND username connected to their GitHub account (see
    confirm_github_pending_email) before an OTP is ever issued for it."""
    doc = {
        "pending_token": pending_token,
        "flow": flow,
        "otp_hash": None,
        "expires_at": expires_at,
        "email": email,
        "email_confirmed": False,
        "email_attempts": 0,
        "user_id": user_id,
        "full_name": full_name,
        "github_id": github_id,
        "github_username": github_username,
        "password_hash": password_hash,
        "return_to": return_to,
        "attempts": 0,
        "used": False,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    await db.github_pending.insert_one(doc)
    return doc


async def get_github_pending(db: AsyncDatabase, pending_token: str) -> Optional[dict]:
    return await db.github_pending.find_one({"pending_token": pending_token})


async def increment_github_pending_email_attempts(db: AsyncDatabase, pending_id) -> None:
    await db.github_pending.update_one({"_id": pending_id}, {"$inc": {"email_attempts": 1}})


async def confirm_github_pending_email(db: AsyncDatabase, pending_id, otp_hash: str, expires_at) -> None:
    """Called only once the typed email has been matched against the
    GitHub-resolved one — this is what actually issues the OTP's hash and
    (re)starts its expiry clock from the moment it's genuinely sent."""
    await db.github_pending.update_one(
        {"_id": pending_id},
        {"$set": {"email_confirmed": True, "otp_hash": otp_hash, "expires_at": expires_at}},
    )


async def increment_github_pending_attempts(db: AsyncDatabase, pending_id) -> None:
    await db.github_pending.update_one({"_id": pending_id}, {"$inc": {"attempts": 1}})


async def mark_github_pending_used(db: AsyncDatabase, pending_id) -> None:
    await db.github_pending.update_one({"_id": pending_id}, {"$set": {"used": True}})


# ---------------------------------------------------------------------------
# Pending candidate registration (password signup that requires proving
# ownership of a claimed GitHub username before the account is created)
# ---------------------------------------------------------------------------

async def create_pending_registration(
    db: AsyncDatabase,
    registration_id: str,
    email: str,
    hashed_password: str,
    full_name: Optional[str],
    github_username: str,  # lowercased, as claimed on the signup form
    expires_at,
) -> dict:
    doc = {
        "registration_id": registration_id,
        "email": email,
        "hashed_password": hashed_password,
        "full_name": full_name,
        "github_username": github_username,
        "expires_at": expires_at,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    await db.pending_registrations.insert_one(doc)
    return doc


async def consume_pending_registration(db: AsyncDatabase, registration_id: str) -> Optional[dict]:
    """Single-use: deletes the doc as it reads it, so the OAuth callback URL
    (or a copy of it) can never be replayed to spin up a second account."""
    return await db.pending_registrations.find_one_and_delete({"registration_id": registration_id})


# ---------------------------------------------------------------------------
# Password reset OTPs
# ---------------------------------------------------------------------------

async def create_password_reset(db: AsyncDatabase, email: str, otp_hash: str, expires_at) -> dict:
    doc = {
        "email": email,
        "otp_hash": otp_hash,
        "expires_at": expires_at,
        "used": False,
        "attempts": 0,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }
    result = await db.password_resets.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_latest_password_reset(db: AsyncDatabase, email: str) -> Optional[dict]:
    cursor = db.password_resets.find({"email": email}).sort("created_at", -1).limit(1)
    results = await cursor.to_list(length=1)
    return results[0] if results else None


async def increment_password_reset_attempts(db: AsyncDatabase, reset_id) -> None:
    await db.password_resets.update_one({"_id": reset_id}, {"$inc": {"attempts": 1}})


async def mark_password_reset_used(db: AsyncDatabase, reset_id) -> None:
    await db.password_resets.update_one({"_id": reset_id}, {"$set": {"used": True}})
