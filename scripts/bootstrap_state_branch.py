"""Bootstrap utility to create and initialize the dedicated GitHub state branch."""

import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()


def bootstrap_state_branch() -> int:
    github_token = os.getenv("GITHUB_TOKEN")
    github_repo = os.getenv("GITHUB_REPOSITORY")
    state_branch = os.getenv("GITHUB_STATE_BRANCH", "automation-state")

    if not github_token:
        print("[ERROR] GITHUB_TOKEN environment variable is missing.")
        return 1

    if not github_repo or "/" not in github_repo:
        print("[ERROR] GITHUB_REPOSITORY must be set in 'owner/repo' format.")
        return 1

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Groq-LinkedIn-Automation-Bootstrap/1.0"
    }

    base_url = "https://api.github.com"

    print(f"Connecting to GitHub repository: {github_repo}...")

    with httpx.Client(timeout=20.0) as client:
        # 1. Verify repo access
        repo_resp = client.get(f"{base_url}/repos/{github_repo}", headers=headers)
        if repo_resp.status_code == 401:
            print("[ERROR] GITHUB_TOKEN is invalid or unauthorized.")
            return 1
        elif repo_resp.status_code == 404:
            print(f"[ERROR] Repository '{github_repo}' not found or token lacks access.")
            return 1
        elif repo_resp.status_code != 200:
            print(f"[ERROR] GitHub error: HTTP {repo_resp.status_code}")
            return 1

        repo_data = repo_resp.json()
        default_branch = repo_data.get("default_branch", "main")
        print(f"Repository verified. Default branch is '{default_branch}'.")

        # 2. Check if state branch already exists
        branch_resp = client.get(f"{base_url}/repos/{github_repo}/branches/{state_branch}", headers=headers)
        if branch_resp.status_code == 200:
            branch_data = branch_resp.json()
            latest_sha = branch_data.get("commit", {}).get("sha", "unknown")
            print(f"[SUCCESS] State branch '{state_branch}' already exists! Head commit: {latest_sha[:8]}.")
            return 0
        elif branch_resp.status_code != 404:
            print(f"[ERROR] Error checking branch status: HTTP {branch_resp.status_code} - {branch_resp.text}")
            return 1

        print(f"State branch '{state_branch}' does not exist. Creating from '{default_branch}'...")

        # 3. Get latest SHA of default branch
        ref_resp = client.get(f"{base_url}/repos/{github_repo}/git/ref/heads/{default_branch}", headers=headers)
        if ref_resp.status_code != 200:
            print(f"[ERROR] Failed to fetch ref for default branch '{default_branch}': HTTP {ref_resp.status_code}")
            return 1

        base_sha = ref_resp.json().get("object", {}).get("sha")
        if not base_sha:
            print("[ERROR] Could not extract commit SHA from default branch.")
            return 1

        # 4. Create new branch ref
        create_ref_payload = {
            "ref": f"refs/heads/{state_branch}",
            "sha": base_sha
        }
        create_resp = client.post(f"{base_url}/repos/{github_repo}/git/refs", headers=headers, json=create_ref_payload)
        if create_resp.status_code == 201:
            print(f"[SUCCESS] Successfully created dedicated state branch '{state_branch}' at commit {base_sha[:8]}.")
            print("The state branch is ready for daily automation state and outbox storage.")
            return 0
        elif create_resp.status_code == 403:
            print("[ERROR] Permission denied (403). Ensure your fine-grained GitHub token has 'Contents: Read and write' permission.")
            return 1
        else:
            print(f"[ERROR] Failed to create branch ref: HTTP {create_resp.status_code} - {create_resp.text}")
            return 1


if __name__ == "__main__":
    sys.exit(bootstrap_state_branch())
