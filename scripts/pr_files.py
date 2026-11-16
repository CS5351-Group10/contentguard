"""Shared helpers for CI gates that need pull-request context (GITHUB_EVENT_PATH)."""

import json
import os
import urllib.error
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
    """Request headers; the Authorization header is sent only for a real token.

    A blank token (GITHUB_TOKEN unset in the CI step) must yield an anonymous
    request, not a malformed ``Authorization: Bearer `` header that the GitHub API
    rejects with 401 (see docs/review-memo.md, gate 1/4 token-plumbing fix).
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token.strip():
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _paginate(base: str, token: str) -> list[dict]:
    """Fetch every page (``per_page=100``) of a list endpoint as a merged list.

    Shared by changed_files / pull_reviews / issue_comments so there is one place
    for API access and one error style. Raises RuntimeError with an actionable
    message on API failure so a gate fails closed with a diagnosis instead of a
    bare traceback.
    """
    items: list[dict] = []
    page = 1
    while True:
        url = f"{base}?per_page=100&page={page}"
        req = urllib.request.Request(url, headers=_headers(token))
        try:
            with urllib.request.urlopen(req) as resp:
                batch = json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise RuntimeError(
                    f"GitHub API returned 401 Unauthorized for {url}. The "
                    "GITHUB_TOKEN for this step is missing or invalid; pass it via "
                    "`env: GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` on the gate step "
                    "in .github/workflows/ci.yml."
                ) from exc
            raise RuntimeError(
                f"GitHub API error {exc.code} for {url}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"GitHub API unreachable for {url}: {exc.reason}"
            ) from exc
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def changed_files(repo: str, number: int, token: str) -> list[str]:
    """List all changed file paths of a pull request (paginated)."""
    base = f"https://api.github.com/repos/{repo}/pulls/{number}/files"
    return [str(item["filename"]) for item in _paginate(base, token)]


def pull_reviews(repo: str, number: int, token: str) -> list[dict]:
    """List all review objects of a pull request (paginated).

    Gate 7 candidates: each review's ``user.login`` + ``body``.
    """
    base = f"https://api.github.com/repos/{repo}/pulls/{number}/reviews"
    return _paginate(base, token)


def issue_comments(repo: str, number: int, token: str) -> list[dict]:
    """List all issue comments of a pull request (paginated).

    Served by the Issues API, so a gate step calling this needs the ``issues: read``
    workflow permission (``pull-requests: read`` alone returns 403 here).
    """
    base = f"https://api.github.com/repos/{repo}/issues/{number}/comments"
    return _paginate(base, token)


def changed_code_files(files: list[str]) -> list[str]:
    """Filter the changed paths down to code/prompt paths (gates 1 and 6)."""
    return [f for f in files if f.startswith(CODE_PREFIXES)]
