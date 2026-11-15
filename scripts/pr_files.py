"""Shared helpers for CI gates that need pull-request context (GITHUB_EVENT_PATH)."""

import json
import os
import urllib.request
from pathlib import Path

# Paths whose change makes a PR a "code/prompt change" (gates 1 and 6).
CODE_PREFIXES = ("src/", "test/", "prompts/", "scripts/")


def event_payload() -> dict | None:
    """Load the GitHub Actions event payload, or None outside Actions."""
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path or not Path(path).exists():
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pull_request(event: dict) -> dict | None:
    """Return the pull_request object for PR events, else None."""
    pr = event.get("pull_request")
    return pr if isinstance(pr, dict) else None


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def changed_files(repo: str, number: int, token: str) -> list[str]:
    """List all changed file paths of a pull request (paginated)."""
    base = f"https://api.github.com/repos/{repo}/pulls/{number}/files"
    files: list[str] = []
    page = 1
    while True:
        req = urllib.request.Request(f"{base}?per_page=100&page={page}", headers=_headers(token))
        with urllib.request.urlopen(req) as resp:
            batch = json.load(resp)
        files.extend(str(item["filename"]) for item in batch)
        if len(batch) < 100:
            return files
        page += 1


def changed_code_files(files: list[str]) -> list[str]:
    """Filter the changed paths down to code/prompt paths (gates 1 and 6)."""
    return [f for f in files if f.startswith(CODE_PREFIXES)]
