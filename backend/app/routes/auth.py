import asyncio
import datetime
import hashlib
import secrets

from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

import app.schemas as schemas
from app.config.config import config
from app.config.database import get_db
from app.constants import UserRole
from app.deps.auth import get_current_user
from app.services import crud
from app.services import github_oauth
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.email import send_email
from app.services.errors import UpstreamServiceError
from app.services.mongo_errors import to_http_error

router = APIRouter(prefix="/auth", tags=["Auth"])

_OTP_LENGTH = 6
_GENERIC_FORGOT_PASSWORD_MESSAGE = "If that email is registered, a reset code has been sent."
_INVALID_OTP_MESSAGE = "Invalid or expired code."


def _generate_otp() -> str:
    # secrets, not random — this is a short-lived credential, not just a UI token.
    return "".join(secrets.choice("0123456789") for _ in range(_OTP_LENGTH))


def _hash_otp(otp: str) -> str:
    # sha256, not bcrypt: a 6-digit code's security comes from expiry + the
    # attempt cap below, not from hash cost — bcrypt here would just be slower
    # for no real benefit.
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _as_utc(dt: datetime.datetime) -> datetime.datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)


def _to_user_response(user: dict) -> schemas.UserResponse:
    return schemas.UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        role=user["role"],
        full_name=user.get("full_name"),
        github_username=user.get("github_username"),
        created_at=user["created_at"],
    )


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: schemas.UserRegister, db: AsyncDatabase = Depends(get_db)):
    # Admin accounts are never created through public self-registration.
    role = payload.role if payload.role in UserRole.SELF_REGISTERABLE else UserRole.CANDIDATE

    if role == UserRole.CANDIDATE:
        # Candidate accounts must prove ownership of a real GitHub account —
        # see POST /auth/register/candidate/start. This endpoint only creates
        # recruiter accounts now.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidates must sign up with GitHub. Use the candidate sign-up flow.",
        )

    existing = await crud.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    try:
        user = await crud.create_user(
            db,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=role,
            full_name=payload.full_name,
        )
    except DuplicateKeyError:
        # Race with another request registering the same email between the
        # check above and the insert — the unique index is the real guard.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    except Exception as e:
        raise to_http_error(e)

    return _to_user_response(user)


@router.post("/login", response_model=schemas.Token)
async def login(payload: schemas.UserLogin, db: AsyncDatabase = Depends(get_db)):
    user = await crud.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = create_access_token({"sub": str(user["_id"]), "role": user["role"], "email": user["email"]})
    return schemas.Token(access_token=token)


@router.get("/me", response_model=schemas.UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    return _to_user_response(current_user)


@router.post("/forgot-password", response_model=schemas.MessageResponse)
async def forgot_password(payload: schemas.ForgotPasswordRequest, db: AsyncDatabase = Depends(get_db)):
    """Always returns the same generic message, whether or not the email is
    registered — the response must never be usable to enumerate accounts."""
    user = await crud.get_user_by_email(db, payload.email)
    if not user:
        return schemas.MessageResponse(message=_GENERIC_FORGOT_PASSWORD_MESSAGE)

    existing = await crud.get_latest_password_reset(db, payload.email)
    now = datetime.datetime.now(datetime.timezone.utc)
    if existing and not existing["used"]:
        elapsed = (now - _as_utc(existing["created_at"])).total_seconds()
        if elapsed < config.PASSWORD_RESET_COOLDOWN_SECONDS:
            wait = int(config.PASSWORD_RESET_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {wait}s before requesting another code.",
            )

    otp = _generate_otp()
    expires_at = now + datetime.timedelta(minutes=config.PASSWORD_RESET_OTP_EXPIRE_MINUTES)
    await crud.create_password_reset(db, payload.email, _hash_otp(otp), expires_at)

    subject = "Your Recruvoskill password reset code"
    body = (
        f"Your Recruvoskill password reset code is: {otp}\n\n"
        f"This code expires in {config.PASSWORD_RESET_OTP_EXPIRE_MINUTES} minutes.\n"
        "If you didn't request this, you can safely ignore this email."
    )
    # smtplib is blocking — never call it directly on the event loop.
    await asyncio.to_thread(send_email, payload.email, subject, body)

    return schemas.MessageResponse(message=_GENERIC_FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=schemas.MessageResponse)
async def reset_password(payload: schemas.ResetPasswordRequest, db: AsyncDatabase = Depends(get_db)):
    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_OTP_MESSAGE)

    reset_doc = await crud.get_latest_password_reset(db, payload.email)
    if not reset_doc or reset_doc["used"]:
        raise invalid

    if reset_doc["attempts"] >= config.PASSWORD_RESET_MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Request a new code.")

    now = datetime.datetime.now(datetime.timezone.utc)
    if now > _as_utc(reset_doc["expires_at"]):
        raise invalid

    if _hash_otp(payload.otp) != reset_doc["otp_hash"]:
        await crud.increment_password_reset_attempts(db, reset_doc["_id"])
        raise invalid

    user = await crud.get_user_by_email(db, payload.email)
    if not user:
        raise invalid

    await crud.update_user_password(db, user["_id"], hash_password(payload.new_password))
    await crud.mark_password_reset_used(db, reset_doc["_id"])

    return schemas.MessageResponse(message="Password reset successful. You can now sign in with your new password.")


# ---------------------------------------------------------------------------
# GitHub OAuth — "Continue with GitHub" (login/signup) and "Connect GitHub"
# (link to an already-logged-in account). Both funnel through the same
# /auth/github/callback; the oauth_states doc's user_id tells the callback
# which of the two flows it's completing.
# ---------------------------------------------------------------------------

def _require_github_oauth_configured():
    if not config.GITHUB_OAUTH_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub sign-in is not configured on this server.",
        )


async def _build_authorize_url(db: AsyncDatabase, user_id: Optional[str], return_to: Optional[str]) -> str:
    _require_github_oauth_configured()
    state = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=config.GITHUB_OAUTH_STATE_EXPIRE_MINUTES
    )
    await crud.create_oauth_state(db, state, user_id, expires_at, return_to)
    return github_oauth.build_authorize_url(state)


@router.get("/github/login")
async def github_login(db: AsyncDatabase = Depends(get_db)):
    """Unauthenticated entry point — a plain browser link (no auth header
    needed) that redirects straight to GitHub. Logs in an existing
    GitHub-linked user, or creates a new (GitHub-verified) candidate account."""
    url = await _build_authorize_url(db, user_id=None, return_to=None)
    return RedirectResponse(url=url)


@router.get("/github/connect")
async def github_connect(
    return_to: Optional[str] = None,
    db: AsyncDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Authenticated entry point — links GitHub to the current account. Unlike
    /github/login this returns JSON, not a redirect: this endpoint requires a
    Bearer token, which a plain <a href> browser navigation can't send. The
    frontend calls this via an authenticated fetch, then navigates the browser
    to the returned URL itself (that hop needs no auth — it's just GitHub)."""
    url = await _build_authorize_url(db, user_id=str(current_user["_id"]), return_to=return_to)
    return {"authorize_url": url}


@router.post("/register/candidate/start")
async def register_candidate_start(payload: schemas.CandidateRegisterStart, db: AsyncDatabase = Depends(get_db)):
    """Candidate sign-up no longer creates an account directly — it stashes
    the chosen email/password/full name plus the claimed GitHub username,
    then sends the browser to GitHub. The account is only created once
    /github/callback confirms that GitHub username is real and unclaimed,
    and the candidate has confirmed the matching email + username and OTP
    (see /github/confirm-email, /github/verify-otp, flow="register_verify")."""
    _require_github_oauth_configured()

    existing = await crud.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now + datetime.timedelta(minutes=config.GITHUB_OAUTH_STATE_EXPIRE_MINUTES)

    registration_id = secrets.token_urlsafe(32)
    await crud.create_pending_registration(
        db, registration_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        github_username=payload.github_username.strip().lower(),
        expires_at=expires_at,
    )

    state = secrets.token_urlsafe(32)
    await crud.create_oauth_state(db, state, user_id=None, expires_at=expires_at, registration_id=registration_id)
    return {"authorize_url": github_oauth.build_authorize_url(state)}


def _github_error_redirect(code: str) -> RedirectResponse:
    return RedirectResponse(url=f"{config.FRONTEND_BASE_URL.rstrip('/')}/auth/github/complete?error={code}")


async def _send_github_otp(email: str, github_username: str, otp: str) -> None:
    # Takes an already-generated OTP rather than generating its own — the
    # caller has already hashed and stored it, so the emailed code must be
    # the exact same one or verify-otp can never succeed.
    subject = "Your Recruvoskill verification code"
    body = (
        f"Someone is signing in to Recruvoskill with the GitHub account @{github_username} on this email.\n\n"
        f"Your verification code is: {otp}\n\n"
        f"This code expires in {config.GITHUB_OTP_EXPIRE_MINUTES} minutes.\n"
        "If this wasn't you, do not share this code with anyone."
    )
    await asyncio.to_thread(send_email, email, subject, body)


@router.get("/github/callback")
async def github_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncDatabase = Depends(get_db),
):
    """Identifies the GitHub account, then stops short of completing anything.
    A GitHub OAuth session can already be authenticated in a shared browser —
    proving control of it is not the same as proving the person at the
    keyboard right now is the account owner. So this only ever queues a
    pending record and emails an OTP; POST /auth/github/verify-otp is what
    actually creates/links/logs in."""
    _require_github_oauth_configured()

    if error or not code or not state:
        return _github_error_redirect("github_oauth_failed")

    state_doc = await crud.consume_oauth_state(db, state)
    if not state_doc:
        return _github_error_redirect("github_oauth_failed")  # unknown, expired, or already-used state

    now = datetime.datetime.now(datetime.timezone.utc)
    if now > _as_utc(state_doc["expires_at"]):
        return _github_error_redirect("github_oauth_failed")

    try:
        access_token = github_oauth.exchange_code_for_token(code)
        gh_user = github_oauth.fetch_github_user(access_token)
    except UpstreamServiceError:
        return _github_error_redirect("github_oauth_failed")

    github_id = gh_user.get("id")
    github_username = gh_user.get("login")
    if not github_id or not github_username:
        return _github_error_redirect("github_oauth_failed")

    return_to = state_doc.get("return_to")
    expires_at = now + datetime.timedelta(minutes=config.GITHUB_OTP_EXPIRE_MINUTES)

    # --- Password-signup verification flow: state carries a pending registration ---
    if state_doc.get("registration_id"):
        pending_reg = await crud.consume_pending_registration(db, state_doc["registration_id"])
        if not pending_reg:
            return _github_error_redirect("github_oauth_failed")

        if github_username.strip().lower() != pending_reg["github_username"]:
            # The GitHub account they actually authorized isn't the one they
            # claimed on the sign-up form — refuse rather than silently using
            # whichever account is logged into GitHub right now.
            return _github_error_redirect("github_username_mismatch")

        existing_link = await crud.get_user_by_github_id(db, github_id)
        if existing_link:
            return _github_error_redirect("github_already_linked")

        pending_token = secrets.token_urlsafe(32)
        await crud.create_github_pending(
            db, pending_token, flow="register_verify", expires_at=expires_at,
            email=pending_reg["email"], full_name=pending_reg.get("full_name"),
            github_id=github_id, github_username=github_username,
            password_hash=pending_reg["hashed_password"],
        )
        dest = f"{config.FRONTEND_BASE_URL.rstrip('/')}/auth/github/complete?pending={pending_token}&flow=register_verify"
        return RedirectResponse(url=dest)

    # --- Connect flow: state carries the already-logged-in user's id ---
    if state_doc.get("user_id"):
        existing_link = await crud.get_user_by_github_id(db, github_id)
        if existing_link and str(existing_link["_id"]) != state_doc["user_id"]:
            # This GitHub account is already linked to a DIFFERENT Recruvoskill
            # account — refuse rather than letting two accounts share one
            # verified identity.
            return _github_error_redirect("github_already_linked")

        current_user = await crud.get_user_by_id(db, state_doc["user_id"])
        if not current_user:
            return _github_error_redirect("github_oauth_failed")

        # No OTP is sent yet — the candidate must first correctly type the
        # email connected to their account (checked against `email` below via
        # POST /auth/github/confirm-email) before any code goes out.
        pending_token = secrets.token_urlsafe(32)
        await crud.create_github_pending(
            db, pending_token, flow="connect", expires_at=expires_at,
            email=current_user["email"], user_id=state_doc["user_id"],
            github_id=github_id, github_username=github_username, return_to=return_to,
        )
        dest = f"{config.FRONTEND_BASE_URL.rstrip('/')}/auth/github/complete?pending={pending_token}&flow=connect"
        if return_to:
            dest += f"&return_to={quote(return_to, safe='')}"
        return RedirectResponse(url=dest)

    # --- Login/signup flow: no user_id on the state ---
    user = await crud.get_user_by_github_id(db, github_id)
    if user:
        if user["role"] != UserRole.CANDIDATE:
            # "Continue with GitHub" signs in candidates only. A recruiter/admin
            # who has a linked GitHub account (via /auth/github/connect) still
            # can't use it as a login shortcut — email + password only.
            return _github_error_redirect("github_login_candidates_only")
        pending_token = secrets.token_urlsafe(32)
        await crud.create_github_pending(
            db, pending_token, flow="login", expires_at=expires_at,
            email=user["email"], user_id=str(user["_id"]),
            github_username=github_username, return_to=return_to,
        )
    else:
        email = github_oauth.fetch_github_primary_email(access_token)
        if not email:
            # No real, verified email available from GitHub — we can't send an
            # OTP to an address the candidate doesn't control, and every other
            # part of this app (password reset, notifications) needs a real
            # email anyway. Ask them to make one available on GitHub and retry
            # rather than silently creating an unreachable noreply account.
            return _github_error_redirect("github_email_required")

        existing_by_email = await crud.get_user_by_email(db, email)
        if existing_by_email:
            # An account with this email already exists via password signup.
            # Do NOT silently take it over just because GitHub reports the same
            # email — that would let anyone with control of a GitHub account
            # hijack an unrelated password-based account. They must log in
            # normally and use "Connect GitHub" instead.
            return _github_error_redirect("email_already_registered")

        pending_token = secrets.token_urlsafe(32)
        await crud.create_github_pending(
            db, pending_token, flow="signup", expires_at=expires_at,
            email=email, full_name=gh_user.get("name"),
            github_id=github_id, github_username=github_username, return_to=return_to,
        )

    dest = f"{config.FRONTEND_BASE_URL.rstrip('/')}/auth/github/complete?pending={pending_token}&flow={'login' if user else 'signup'}"
    if return_to:
        dest += f"&return_to={quote(return_to, safe='')}"
    return RedirectResponse(url=dest)


@router.post("/github/confirm-email", response_model=schemas.MessageResponse)
async def github_confirm_email(payload: schemas.GithubEmailConfirmRequest, db: AsyncDatabase = Depends(get_db)):
    """The gate before any OTP is ever sent: the candidate must correctly type
    both the email AND the username connected to their GitHub account. This is
    what actually stops someone using an already-authenticated GitHub session
    (e.g. a shared, unlocked laptop) that isn't really theirs — they'd need to
    also know both of those details, not just click through GitHub's prompt."""
    invalid_email = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="That doesn't match the email and username connected to your GitHub account.",
    )

    pending = await crud.get_github_pending(db, payload.pending_token)
    if not pending or pending["used"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_OTP_MESSAGE)

    if pending.get("email_confirmed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already confirmed.")

    if pending["email_attempts"] >= config.GITHUB_EMAIL_CONFIRM_MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Start over with GitHub sign-in.")

    now = datetime.datetime.now(datetime.timezone.utc)
    if now > _as_utc(pending["expires_at"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_OTP_MESSAGE)

    email_matches = payload.email.strip().lower() == pending["email"].strip().lower()
    username_matches = payload.github_username.strip().lower() == (pending.get("github_username") or "").strip().lower()
    if not email_matches or not username_matches:
        await crud.increment_github_pending_email_attempts(db, pending["_id"])
        raise invalid_email

    otp = _generate_otp()
    expires_at = now + datetime.timedelta(minutes=config.GITHUB_OTP_EXPIRE_MINUTES)
    await crud.confirm_github_pending_email(db, pending["_id"], _hash_otp(otp), expires_at)
    await _send_github_otp(pending["email"], pending["github_username"], otp)
    return schemas.MessageResponse(message="Verification code sent.")


@router.post("/github/verify-otp", response_model=schemas.GithubOtpVerifyResponse)
async def github_verify_otp(payload: schemas.GithubOtpVerifyRequest, db: AsyncDatabase = Depends(get_db)):
    """Completes whichever GitHub flow /github/callback queued — nothing is
    created/linked/logged-in before this succeeds."""
    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_OTP_MESSAGE)

    pending = await crud.get_github_pending(db, payload.pending_token)
    if not pending or pending["used"]:
        raise invalid

    if not pending.get("email_confirmed"):
        raise invalid

    if pending["attempts"] >= config.GITHUB_OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Start over with GitHub sign-in.")

    now = datetime.datetime.now(datetime.timezone.utc)
    if now > _as_utc(pending["expires_at"]):
        raise invalid

    if _hash_otp(payload.otp) != pending["otp_hash"]:
        await crud.increment_github_pending_attempts(db, pending["_id"])
        raise invalid

    flow = pending["flow"]

    if flow == "connect":
        # Re-check "already linked elsewhere" — someone could have linked this
        # exact GitHub account during the window the OTP was pending.
        existing_link = await crud.get_user_by_github_id(db, pending["github_id"])
        if existing_link and str(existing_link["_id"]) != pending["user_id"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That GitHub account is already connected to a different account.")
        connecting_user = await crud.get_user_by_id(db, pending["user_id"])
        if not connecting_user:
            raise invalid
        try:
            await crud.link_github_to_user(db, connecting_user["_id"], pending["github_id"], pending["github_username"])
        except DuplicateKeyError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That GitHub account is already connected to a different account.")
        await crud.mark_github_pending_used(db, pending["_id"])
        return schemas.GithubOtpVerifyResponse(connected=True)

    if flow == "login":
        user = await crud.get_user_by_id(db, pending["user_id"])
        if not user:
            raise invalid
        await crud.mark_github_pending_used(db, pending["_id"])
        token = create_access_token({"sub": str(user["_id"]), "role": user["role"], "email": user["email"]})
        return schemas.GithubOtpVerifyResponse(access_token=token)

    if flow == "signup":
        # Re-check email availability — another registration could have taken
        # it during the window the OTP was pending.
        existing_by_email = await crud.get_user_by_email(db, pending["email"])
        if existing_by_email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email was registered in the meantime.")
        try:
            user = await crud.create_user(
                db,
                email=pending["email"],
                hashed_password=None,
                role=UserRole.CANDIDATE,
                full_name=pending.get("full_name"),
                github_id=pending["github_id"],
                github_username=pending["github_username"],
            )
        except DuplicateKeyError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email or GitHub identity was registered in the meantime.")
        await crud.mark_github_pending_used(db, pending["_id"])
        token = create_access_token({"sub": str(user["_id"]), "role": user["role"], "email": user["email"]})
        return schemas.GithubOtpVerifyResponse(access_token=token)

    if flow == "register_verify":
        # Re-check both email and GitHub identity availability — either could
        # have been taken by another request during the window the OTP was
        # pending.
        existing_by_email = await crud.get_user_by_email(db, pending["email"])
        if existing_by_email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email was registered in the meantime.")
        existing_link = await crud.get_user_by_github_id(db, pending["github_id"])
        if existing_link:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That GitHub account is already connected to a different account.")
        try:
            user = await crud.create_user(
                db,
                email=pending["email"],
                hashed_password=pending["password_hash"],
                role=UserRole.CANDIDATE,
                full_name=pending.get("full_name"),
                github_id=pending["github_id"],
                github_username=pending["github_username"],
            )
        except DuplicateKeyError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email or GitHub identity was registered in the meantime.")
        await crud.mark_github_pending_used(db, pending["_id"])
        token = create_access_token({"sub": str(user["_id"]), "role": user["role"], "email": user["email"]})
        return schemas.GithubOtpVerifyResponse(access_token=token)

    raise invalid
