"""GitHub state persistence engine using official GitHub Contents REST API."""

import base64
import json
import logging
from typing import Any, Dict, Optional, Tuple
import httpx

from app.config import get_settings
from app.models import DailyState, DraftStatus, PublicationStatus

logger = logging.getLogger(__name__)


class GitHubStateConflictError(Exception):
    """Raised when an optimistic concurrency conflict (409) occurs in GitHub state."""
    pass


class GitHubStateError(Exception):
    """Raised when GitHub state read or write operations fail."""
    pass


class GitHubStateManager:
    """Manages reading and writing daily automation state on a dedicated branch."""

    def __init__(self, token: Optional[str] = None, repository: Optional[str] = None, branch: Optional[str] = None):
        settings = get_settings()
        self.token = token or settings.github_token
        self.repository = repository or settings.github_repository
        self.branch = branch or settings.github_state_branch
        self.base_url = "https://api.github.com"

    def _get_headers(self) -> Dict[str, str]:
        if not self.token:
            raise GitHubStateError("GITHUB_TOKEN is missing. Cannot access GitHub repository.")
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Groq-LinkedIn-Automation/1.0"
        }

    def read_file(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Read a file from the state branch.
        Returns (decoded_content, sha). If file does not exist (404), returns (None, None).
        """
        settings = get_settings()
        if not self.repository:
            raise GitHubStateError("GITHUB_REPOSITORY is missing. Cannot access GitHub state.")

        url = f"{self.base_url}/repos/{self.repository}/contents/{file_path}"
        params = {"ref": self.branch}

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, headers=self._get_headers(), params=params)

                if resp.status_code == 404:
                    return None, None
                elif resp.status_code == 200:
                    data = resp.json()
                    sha = data.get("sha")
                    raw_content = data.get("content", "")
                    encoding = data.get("encoding", "base64")
                    if encoding == "base64":
                        decoded = base64.b64decode(raw_content).decode("utf-8")
                    else:
                        decoded = raw_content
                    return decoded, sha
                else:
                    redacted_body = settings.redact(resp.text)
                    raise GitHubStateError(f"GitHub API error reading '{file_path}': HTTP {resp.status_code} - {redacted_body}")
        except httpx.RequestError as e:
            redacted_err = settings.redact(str(e))
            raise GitHubStateError(f"Network error reading GitHub state '{file_path}': {redacted_err}") from None

    def write_file(self, file_path: str, content: str, commit_message: str, sha: Optional[str] = None) -> str:
        """
        Write or update a file on the state branch using optimistic concurrency.
        Returns the new commit/blob SHA.
        """
        settings = get_settings()
        if not self.repository:
            raise GitHubStateError("GITHUB_REPOSITORY is missing. Cannot access GitHub state.")

        # Ensure no secrets leaked into content or commit message
        clean_content = settings.redact(content)
        clean_message = settings.redact(commit_message)

        url = f"{self.base_url}/repos/{self.repository}/contents/{file_path}"
        encoded_content = base64.b64encode(clean_content.encode("utf-8")).decode("utf-8")

        payload: Dict[str, Any] = {
            "message": clean_message,
            "content": encoded_content,
            "branch": self.branch,
        }
        if sha:
            payload["sha"] = sha

        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.put(url, headers=self._get_headers(), json=payload)

                if resp.status_code in (200, 201):
                    data = resp.json()
                    new_sha = data.get("content", {}).get("sha", "")
                    return new_sha
                elif resp.status_code == 409:
                    raise GitHubStateConflictError(f"Optimistic concurrency conflict writing '{file_path}'. File was modified concurrently.")
                else:
                    redacted_body = settings.redact(resp.text)
                    raise GitHubStateError(f"GitHub API error writing '{file_path}': HTTP {resp.status_code} - {redacted_body}")
        except httpx.RequestError as e:
            redacted_err = settings.redact(str(e))
            raise GitHubStateError(f"Network error writing GitHub state '{file_path}': {redacted_err}") from None

    def load_daily_state(self, date_str: str) -> Tuple[Optional[DailyState], Optional[str]]:
        """Load DailyState object for a date. Returns (DailyState, sha)."""
        file_path = f"automation_state/{date_str}.json"
        content, sha = self.read_file(file_path)
        if not content:
            return None, None

        try:
            data = json.loads(content)
            state = DailyState(**data)
            return state, sha
        except Exception as e:
            raise GitHubStateError(f"Corrupt daily state JSON in '{file_path}': {e}")

    def save_daily_state(self, state: DailyState, sha: Optional[str] = None) -> str:
        """Persist DailyState object to automation_state/YYYY-MM-DD.json and history."""
        file_path = f"automation_state/{state.date}.json"
        state_json = state.model_dump_json(indent=2)
        commit_msg = f"automation: update daily state for {state.date} [{state.publication_status.value}]"

        new_sha = self.write_file(
            file_path=file_path,
            content=state_json,
            commit_message=commit_msg,
            sha=sha
        )

        # Also write historical snapshot in automation_history/
        history_path = f"automation_history/{state.date}.json"
        _, hist_sha = self.read_file(history_path)
        self.write_file(
            file_path=history_path,
            content=state_json,
            commit_message=f"automation: update history record for {state.date}",
            sha=hist_sha
        )

        return new_sha

    def save_outbox_markdown(self, date_str: str, markdown_content: str) -> str:
        """Save outbox human-readable markdown file."""
        file_path = f"automation_outbox/{date_str}.md"
        _, existing_sha = self.read_file(file_path)
        commit_msg = f"automation: record outbox draft for {date_str}"
        return self.write_file(
            file_path=file_path,
            content=markdown_content,
            commit_message=commit_msg,
            sha=existing_sha
        )

    def list_directory(self, dir_path: str) -> list:
        """List files in a directory on the state branch. Returns list of file metadata items."""
        settings = get_settings()
        if not self.repository:
            raise GitHubStateError("GITHUB_REPOSITORY is missing. Cannot access GitHub state.")

        url = f"{self.base_url}/repos/{self.repository}/contents/{dir_path.strip('/')}"
        params = {"ref": self.branch}

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, headers=self._get_headers(), params=params)
                if resp.status_code == 404:
                    return []
                elif resp.status_code == 200:
                    data = resp.json()
                    return data if isinstance(data, list) else [data]
                else:
                    redacted_body = settings.redact(resp.text)
                    logger.warning("Error listing directory '%s': HTTP %d - %s", dir_path, resp.status_code, redacted_body)
                    return []
        except httpx.RequestError as e:
            logger.warning("Network error listing directory '%s': %s", dir_path, settings.redact(str(e)))
            return []

    def delete_file(self, file_path: str, sha: str, commit_message: str) -> bool:
        """Delete a file on the state branch."""
        settings = get_settings()
        if not self.repository:
            raise GitHubStateError("GITHUB_REPOSITORY is missing. Cannot access GitHub state.")

        url = f"{self.base_url}/repos/{self.repository}/contents/{file_path}"
        payload = {
            "message": settings.redact(commit_message),
            "sha": sha,
            "branch": self.branch
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.request("DELETE", url, headers=self._get_headers(), json=payload)
                if resp.status_code in (200, 204):
                    return True
                elif resp.status_code == 404:
                    return True
                else:
                    redacted_body = settings.redact(resp.text)
                    raise GitHubStateError(f"GitHub API error deleting '{file_path}': HTTP {resp.status_code} - {redacted_body}")
        except httpx.RequestError as e:
            redacted_err = settings.redact(str(e))
            raise GitHubStateError(f"Network error deleting '{file_path}': {redacted_err}") from None

