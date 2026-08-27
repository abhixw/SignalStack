import logging
from typing import Optional
from urllib.parse import urlencode

import requests

from app.config.config import config
from app.services.errors import UpstreamServiceError, AUTH_FAILURE, UPSTREAM_SERVICE_ERROR, TIMEOUT

logger = logging.getLogger("signalstack.github_oauth")

_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_TOKEN_URL = "https://github.com/login/oauth/access_token"
_API_BASE = "https://api.github.com"
_TIMEOUT_SECONDS = 10


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": config.GITHUB_OAUTH_CLIENT_ID,
        "redirect_uri": config.GITHUB_OAUTH_REDIRECT_URI,
        "scope": "read:user user:email",
        "state": state,
        "allow_signup": "true",
    }
    return f"{_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> str:
    """Raises UpstreamServiceError on any failure."""
    try:
        resp = requests.post(
            _TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": config.GITHUB_OAUTH_CLIENT_ID,
                "client_secret": config.GITHUB_OAUTH_CLIENT_SECRET,
                "code": code,
                "redirect_uri": config.GITHUB_OAUTH_REDIRECT_URI,
            },
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        raise UpstreamServiceError("github_oauth", TIMEOUT, "GitHub did not respond in time.", retryable=True, status_code=504)
    except requests.exceptions.RequestException as e:
        logger.warning("GitHub OAuth token exchange request failed: %s", e)
        raise UpstreamServiceError("github_oauth", UPSTREAM_SERVICE_ERROR, "Could not reach GitHub.", retryable=True, status_code=502)

    data = resp.json() if resp.content else {}
    token = data.get("access_token")
    if not token:
        logger.warning("GitHub OAuth token exchange did not return a token: %s", data.get("error", "unknown"))
        raise UpstreamServiceError("github_oauth", AUTH_FAILURE, "GitHub authorization failed.", retryable=False)
    return token


def fetch_github_user(access_token: str) -> dict:
    """Returns {id, login, name, avatar_url}. Raises UpstreamServiceError on failure."""
    try:
        resp = requests.get(
            f"{_API_BASE}/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as e:
        logger.warning("GitHub /user request failed: %s", e)
        raise UpstreamServiceError("github_oauth", UPSTREAM_SERVICE_ERROR, "Could not reach GitHub.", retryable=True, status_code=502)

    if resp.status_code != 200:
        raise UpstreamServiceError("github_oauth", AUTH_FAILURE, "Could not verify GitHub identity.", retryable=False)

    data = resp.json()
    return {
        "id": data.get("id"),
        "login": data.get("login"),
        "name": data.get("name"),
        "avatar_url": data.get("avatar_url"),
    }


def fetch_github_primary_email(access_token: str) -> Optional[str]:
    """Best-effort — GitHub only exposes this with the user:email scope, and
    even then a user's email can be private with no public fallback."""
    try:
        resp = requests.get(
            f"{_API_BASE}/user/emails",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            timeout=_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            return None
        emails = resp.json()
        primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
        if primary:
            return primary["email"]
        verified = next((e for e in emails if e.get("verified")), None)
        return verified["email"] if verified else None
    except requests.exceptions.RequestException as e:
        logger.warning("GitHub /user/emails request failed: %s", e)
        return None
