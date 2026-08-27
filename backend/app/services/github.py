import logging
import re
import base64
from typing import List, Dict
from urllib.parse import urlparse

import requests

from app.config.config import config
from app.services.errors import (
    UpstreamServiceError,
    AUTH_FAILURE,
    RATE_LIMIT,
    NOT_FOUND,
    TIMEOUT,
    MALFORMED_RESPONSE,
    UPSTREAM_SERVICE_ERROR,
)

logger = logging.getLogger("signalstack.github")

_REQUEST_TIMEOUT_SECONDS = 10
# Only github.com is a valid host — repo_url is user-supplied, so this also
# blocks anyone using this field to make the backend fetch an arbitrary/internal URL.
_ALLOWED_HOSTS = {"github.com", "www.github.com"}
_OWNER_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class GitHubService:
    def __init__(self):
        self.token = config.GITHUB_TOKEN
        self.headers = {
            "Authorization": f"token {self.token}",
            "User-Agent": "SignalStack-Agent/1.0"
        } if self.token else {
            "User-Agent": "SignalStack-Agent/1.0"
        }
        self.api_base = "https://api.github.com"

    def _normalize_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Extract owner and repo from a github.com URL. Raises ValueError for
        anything else (including non-github hosts) — this is also the SSRF guard,
        since every downstream request only ever targets api.github.com."""
        parsed = urlparse(repo_url if "//" in repo_url else f"https://{repo_url}")
        if parsed.hostname not in _ALLOWED_HOSTS:
            raise ValueError(f"Unsupported host: {parsed.hostname}")

        path = parsed.path.rstrip('/')
        if path.endswith('.git'):
            path = path[:-4]

        parts = [p for p in path.split('/') if p]
        if len(parts) < 2:
            raise ValueError("URL does not contain an owner/repo path")

        owner, repo = parts[-2], parts[-1]
        if not (_OWNER_REPO_RE.match(owner) and _OWNER_REPO_RE.match(repo)):
            raise ValueError("Owner/repo contains invalid characters")
        return owner, repo

    def _request(self, url: str) -> requests.Response:
        """Make a GitHub API request, raising a categorized UpstreamServiceError
        on failure rather than swallowing it into an empty/None result."""
        session = requests.Session()
        session.trust_env = False  # avoid local proxy env vars interfering

        def _do(headers) -> requests.Response:
            try:
                return session.get(url, headers=headers, timeout=_REQUEST_TIMEOUT_SECONDS)
            except requests.exceptions.Timeout:
                raise UpstreamServiceError("github", TIMEOUT, "GitHub did not respond in time.", retryable=True, status_code=504)
            except requests.exceptions.RequestException as e:
                logger.warning("GitHub request failed for %s: %s", url, e)
                raise UpstreamServiceError("github", UPSTREAM_SERVICE_ERROR, "Could not reach GitHub.", retryable=True, status_code=502)

        response = _do(self.headers)

        if response.status_code in (401, 403) and self.token:
            # Could be an invalid/rate-limited token — public repos often still work without one.
            logger.info("GitHub request got %s with token; retrying unauthenticated.", response.status_code)
            response = _do({"User-Agent": "SignalStack-Agent/1.0"})

        if response.status_code == 404:
            raise UpstreamServiceError("github", NOT_FOUND, "Repository or resource not found.", retryable=False, status_code=404)
        if response.status_code == 403 and "rate limit" in response.text.lower():
            raise UpstreamServiceError("github", RATE_LIMIT, "GitHub API rate limit exceeded. Please try again later.", retryable=True, status_code=429)
        if response.status_code in (401, 403):
            raise UpstreamServiceError("github", AUTH_FAILURE, "GitHub authentication failed.", retryable=False, status_code=502)
        if response.status_code >= 500:
            raise UpstreamServiceError("github", UPSTREAM_SERVICE_ERROR, "GitHub is currently unavailable.", retryable=True, status_code=502)

        return response

    def get_repo_content(self, repo_url: str, path: str = "") -> List[Dict]:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"
            response = self._request(url)
            return response.json()
        except (ValueError, UpstreamServiceError) as e:
            logger.warning("get_repo_content failed for %s: %s", repo_url, e)
            return []

    def get_file_content(self, repo_url: str, file_path: str) -> str:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/contents/{file_path}"
            response = self._request(url)
            content = response.json().get("content", "")
            return base64.b64decode(content).decode('utf-8')
        except (ValueError, UpstreamServiceError) as e:
            logger.warning("get_file_content failed for %s/%s: %s", repo_url, file_path, e)
            return ""
        except Exception as e:
            logger.warning("get_file_content decode error for %s/%s: %s", repo_url, file_path, e)
            return ""

    def get_recursive_tree(self, repo_url: str) -> tuple[List[str], str]:
        """Tolerant convenience wrapper used throughout the evaluation pipeline —
        one candidate's broken/inaccessible repo should degrade to empty signals,
        not fail the whole batch evaluation. Failures are logged, not silenced."""
        default_branch = "main"
        try:
            owner, repo = self._normalize_repo_url(repo_url)

            repo_response = self._request(f"{self.api_base}/repos/{owner}/{repo}")
            default_branch = repo_response.json().get("default_branch", "main")

            tree_response = self._request(f"{self.api_base}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1")
            return [item['path'] for item in tree_response.json().get('tree', [])], default_branch
        except (ValueError, UpstreamServiceError) as e:
            logger.warning("get_recursive_tree failed for %s: %s", repo_url, e)
            return [], default_branch

    def get_recursive_tree_or_raise(self, repo_url: str) -> tuple[List[str], str]:
        """Same as get_recursive_tree but propagates UpstreamServiceError/ValueError
        for callers (e.g. the repo-preview endpoint) that want to surface the real
        failure reason to the client instead of a generic empty result."""
        owner, repo = self._normalize_repo_url(repo_url)
        repo_response = self._request(f"{self.api_base}/repos/{owner}/{repo}")
        default_branch = repo_response.json().get("default_branch", "main")
        tree_response = self._request(f"{self.api_base}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1")
        try:
            files = [item['path'] for item in tree_response.json().get('tree', [])]
        except (ValueError, KeyError, TypeError) as e:
            raise UpstreamServiceError("github", MALFORMED_RESPONSE, "GitHub returned an unexpected response.", retryable=True, status_code=502) from e
        return files, default_branch

    def get_commit_history(self, repo_url: str, limit: int = 50) -> List[Dict]:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/commits?per_page={limit}"
            response = self._request(url)
            commits = []
            for item in response.json():
                commit = item.get("commit", {})
                author = commit.get("author", {})
                commits.append({
                    "message": commit.get("message", ""),
                    "author_name": author.get("name", "Unknown"),
                    "date": author.get("date", ""),
                    "sha": item.get("sha", "")
                })
            return commits
        except (ValueError, UpstreamServiceError) as e:
            logger.warning("get_commit_history failed for %s: %s", repo_url, e)
            return []
