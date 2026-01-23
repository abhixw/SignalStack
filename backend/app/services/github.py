import requests
import base64
from typing import List, Dict
from app.config.config import config

class GitHubService:
    def __init__(self):
        self.token = config.GITHUB_TOKEN
        self.headers = {"Authorization": f"token {self.token}"} if self.token else {}
        self.api_base = "https://api.github.com"

    def _normalize_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Extract owner and repo from various GitHub URL formats."""
        # Remove trailing slashes and .git suffix
        url = repo_url.rstrip('/').rstrip('.git')
        parts = url.split('/')
        owner, repo = parts[-2], parts[-1]
        return owner, repo

    def get_repo_content(self, repo_url: str, path: str = "") -> List[Dict]:
        # Extract owner/repo from URL
        try:
            owner, repo = self._normalize_repo_url(repo_url)
        except:
            return []

        url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []

    def get_file_content(self, repo_url: str, file_path: str) -> str:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/contents/{file_path}"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                content = response.json().get("content", "")
                return base64.b64decode(content).decode('utf-8')
        except Exception as e:
            print(f"Error fetching file {file_path}: {e}")
        return ""

    def get_recursive_tree(self, repo_url: str) -> tuple[List[str], str]:
        # Get default branch sha first
        default_branch = "main"
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            repo_info = requests.get(f"{self.api_base}/repos/{owner}/{repo}", headers=self.headers).json()
            default_branch = repo_info.get("default_branch", "main")
            
            tree_url = f"{self.api_base}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
            response = requests.get(tree_url, headers=self.headers)
            if response.status_code == 200:
                return [item['path'] for item in response.json().get('tree', [])], default_branch
        except:
            pass
        return [], default_branch

    def get_commit_history(self, repo_url: str, limit: int = 50) -> List[Dict]:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/commits?per_page={limit}"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
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
        except Exception as e:
            print(f"Error fetching commits: {e}")
        return []
