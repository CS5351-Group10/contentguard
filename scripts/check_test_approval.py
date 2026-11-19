"""CI gate 1: no code change merges unless its tests were approved before implementation.

Verifies: REQ-GOV-002 (must) / TD-2. The PR description cites the pre-approved test plan
with the marker ``Test-Plan-Approved: #<issue>``; this gate no longer trusts the marker
alone. For a code/prompt PR it enforces the whole requirement:

1. Resolve the cited number against the issues API. A 404 is *issue not found*; a number
   that resolves to a pull request (GitHub returns a ``pull_request`` key on
   ``/issues/{n}``) is *cited a pull request, not an issue* — distinct messages so an
   author fixes the right thing.
2. Read the issue's comments (paginated) and take the **earliest** qualifying approval
   comment: a body matching the marker whose author is a human — not a bot
   (``user.type == "Bot"`` or a ``[bot]`` login), not the issue author, and not the
   pull-request author. An edited comment (``updated_at != created_at``) uses its
   ``updated_at`` as the effective approval time (a post-hoc edit cannot masquerade as an
   early approval). A marker comment that is *only* by the PR author is reported as
   self-approval, not as "no approval recorded", because the fix differs.
3. Select the first implementation commit from ``GET /pulls/{n}/commits`` (paginated,
   returned order): skip merges (more than one parent); for each remaining commit fetch
   its own file list (``GET /commits/{sha}``) and take the first one whose files include a
   ``CODE_PREFIXES`` path. Earlier docs-only commits do not count.
4. Compare the approval's effective time against that commit's git **author** date
   (``commit.commit.author.date``), never the committer date — a rebase must not turn a
   pre-implementation approval into a post-hoc one. Both sides are normalised to UTC
   before comparison, so ``Z`` and ``+00:00`` compare equal and an offset shifts nothing.

Fail closed: any API or parse problem, a missing commit file list, or no non-merge code
commit produces an actionable ``GATE 1 FAIL: <reason>`` and exit 1 (never a traceback,
never a silent pass, never a marker-only fallback). Docs-only PRs and push events keep
their early pass with no issue lookup. Approval *authority* (which role may sign) is out
of scope; the gate only requires that an independent human approved before implementation.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pr_files import (
    CODE_PREFIXES,
    _headers,
    changed_code_files,
    changed_files,
    event_payload,
    pull_request,
)

MARKER = re.compile(r"Test-Plan-Approved:\s*#(\d+)")
API_ROOT = "https://api.github.com"
# 3.10-compatible UTC singleton (``datetime.UTC`` is 3.11+). CI runs 3.12.
_UTC = timezone.utc  # noqa: UP017


def _json_load(resp: object) -> object:
    """Decode a urlopen response body as JSON."""
    return json.load(resp)  # type: ignore[arg-type]


def _next_link(link_header: str | None) -> str | None:
    """Return the ``rel="next"`` URL from a Link header, or None on the last page."""
    if not link_header:
        return None
    for part in link_header.split(","):
        segments = [s.strip() for s in part.split(";")]
        if any(seg in ('rel="next"', "rel=next") for seg in segments[1:]):
            url = segments[0].strip().strip("<>")
            if url:
                return url
    return None


def _api_paginate(url: str, token: str) -> list[dict]:
    """GET a list endpoint, following ``per_page=100`` + Link pagination.

    Uses the response's Link header when present; falls back to incrementing the page
    parameter while a full page comes back, so a lazy/absent Link header cannot silently
    drop page 2 (mirrors ``pr_files.changed_files``). Returns items in API order.
    """
    sep = "&" if "?" in url else "?"
    page_url: str | None = f"{url}{sep}per_page=100&page=1"
    items: list[dict] = []
    seen: set[str] = set()
    while page_url is not None and page_url not in seen:
        seen.add(page_url)
        req = urllib.request.Request(page_url, headers=_headers(token))
        try:
            with urllib.request.urlopen(req) as resp:
                batch = _json_load(resp)
                link = resp.headers.get("Link") if getattr(resp, "headers", None) else None
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"GitHub API error {exc.code} for {page_url}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"GitHub API unreachable for {page_url}: {exc.reason}"
            ) from exc
        except ValueError as exc:
            raise RuntimeError(
                f"GitHub API returned invalid JSON for {page_url}: {exc}"
            ) from exc
        if not isinstance(batch, list):
            raise RuntimeError(  # noqa: TRY004 — API payload guard; RuntimeError keeps main() fail-closed
                f"GitHub API returned a non-list payload for {page_url}"
            )
        items.extend(batch)
        nxt = _next_link(link) if link is not None else None
        if nxt is not None:
            page_url = nxt
        elif len(batch) < 100:
            page_url = None
        else:
            page_num = int(page_url.rsplit("page=", 1)[1].split("&", 1)[0]) + 1
            page_url = re.sub(r"page=\d+", f"page={page_num}", page_url)
    return items


def _issue_or_none(repo: str, number: int, token: str) -> dict | None:
    """Fetch ``/issues/{n}``; None on 404, otherwise the object (may be a PR).

    A 404 is reported by the caller as "issue not found"; a 200 carrying a
    ``pull_request`` key is a PR number, reported as "cited number is a pull request".
    Other API errors raise RuntimeError (fail closed).
    """
    url = f"{API_ROOT}/repos/{repo}/issues/{number}"
    req = urllib.request.Request(url, headers=_headers(token))
    try:
        with urllib.request.urlopen(req) as resp:
            payload = _json_load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        if exc.code == 401:
            raise RuntimeError(
                f"GitHub API returned 401 Unauthorized for {url}. The GITHUB_TOKEN for "
                "this step is missing or invalid; pass it via "
                "`env: GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` on the gate step."
            ) from exc
        raise RuntimeError(f"GitHub API error {exc.code} for {url}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API unreachable for {url}: {exc.reason}") from exc
    except ValueError as exc:
        raise RuntimeError(f"GitHub API returned invalid JSON for {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(  # noqa: TRY004 — API payload guard; RuntimeError keeps main() fail-closed
            f"GitHub API returned a non-object payload for {url}"
        )
    return payload


def _issue_comments(repo: str, number: int, token: str) -> list[dict]:
    """All comments of an issue, in API order (paginated)."""
    return _api_paginate(f"{API_ROOT}/repos/{repo}/issues/{number}/comments", token)


def _pull_commits(repo: str, number: int, token: str) -> list[dict]:
    """All commits of a PR, in the endpoint's order (paginated)."""
    return _api_paginate(f"{API_ROOT}/repos/{repo}/pulls/{number}/commits", token)


def _is_bot(user: dict) -> bool:
    """A bot account: ``type == "Bot"`` or a login ending in ``[bot]``."""
    login = str(user.get("login", ""))
    return user.get("type") == "Bot" or login.endswith("[bot]")


def _parse_time(value: object) -> datetime:
    """Parse an ISO-8601 timestamp to an aware UTC datetime; raise on a bad value."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing timestamp: {value!r}")
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_UTC)
    return parsed.astimezone(_UTC)


def _qualified_approval(
    comments: list[dict], *, issue_author: str, pr_author: str
) -> tuple[datetime, str] | None:
    """Earliest qualifying approval comment's (effective UTC time, comment author).

    Qualifying means: human (not a bot), not the issue author, not the PR author, body
    matches the marker. Edited comments use ``updated_at`` as the effective time.
    """
    best: tuple[datetime, str] | None = None
    for comment in comments:
        user = comment.get("user") or {}
        login = str(user.get("login", ""))
        body = comment.get("body") or ""
        if MARKER.search(body) is None:
            continue
        if _is_bot(user) or login == issue_author or login == pr_author:
            continue
        created = comment.get("created_at")
        updated = comment.get("updated_at")
        effective = updated if updated not in (None, created) else created
        when = _parse_time(effective)
        if best is None or when < best[0]:
            best = (when, login)
    return best


def _marker_authors(comments: list[dict]) -> set[str]:
    """Logins of every human comment whose body carries the marker (for diagnosis)."""
    authors: set[str] = set()
    for comment in comments:
        user = comment.get("user") or {}
        if MARKER.search(comment.get("body") or "") is None:
            continue
        if _is_bot(user):
            continue
        authors.add(str(user.get("login", "")))
    return authors


def _commit_parents(commit: dict) -> list[dict]:
    parents = commit.get("parents")
    return parents if isinstance(parents, list) else []


def _commit_author_time(commit: dict) -> datetime:
    """A commit's git author date (never committer), normalised to UTC."""
    inner = commit.get("commit") or {}
    author = inner.get("author") or {}
    try:
        return _parse_time(author.get("date"))
    except ValueError as exc:
        raise RuntimeError(
            f"author date unavailable for commit {str(commit.get('sha', '?'))[:7]}: {exc}"
        ) from exc


def _commit_code_files(repo: str, sha: str, token: str) -> list[str]:
    """The code/prompt files changed by one commit (per-commit ``GET /commits/{sha}``).

    Raises RuntimeError when the file list is truncated or unavailable, so the caller
    fails closed instead of guessing that a commit is docs-only.
    """
    url = f"{API_ROOT}/repos/{repo}/commits/{sha}"
    req = urllib.request.Request(url, headers=_headers(token))
    try:
        with urllib.request.urlopen(req) as resp:
            payload = _json_load(resp)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"could not fetch file list for commit {sha[:7]}: "
            f"GitHub API error {exc.code} ({exc.reason})"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"could not fetch file list for commit {sha[:7]}: unreachable ({exc.reason})"
        ) from exc
    except ValueError as exc:
        raise RuntimeError(
            f"could not fetch file list for commit {sha[:7]}: invalid JSON ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(  # noqa: TRY004 — API payload guard; RuntimeError keeps main() fail-closed
            f"commit {sha[:7]} payload is not an object"
        )
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError(f"file list unavailable for commit {sha[:7]}")
    if payload.get("parents") and len(payload["parents"]) > 1:
        return []
    names = [str(item.get("filename", "")) for item in files if isinstance(item, dict)]
    return [n for n in names if n.startswith(CODE_PREFIXES)]


def _first_implementation_commit(
    repo: str, number: int, token: str
) -> tuple[datetime, str] | None:
    """(author time, sha) of the first non-merge commit touching a code path.

    Returns None when no such commit exists. Raises RuntimeError (fail closed) when a
    per-commit file list is unavailable for a non-merge commit.
    """
    for commit in _pull_commits(repo, number, token):
        if len(_commit_parents(commit)) > 1:
            continue
        sha = str(commit.get("sha", ""))
        if not sha:
            raise RuntimeError("a commit in the PR has no sha")
        if _commit_code_files(repo, sha, token):
            return _commit_author_time(commit), sha
    return None


def _fail(reason: str) -> int:
    print(f"GATE 1 FAIL: {reason}")
    return 1


def main() -> int:
    event = event_payload()
    if event is None:
        print("GATE 1 SKIP: no event context (local run)")
        return 0
    pr = pull_request(event)
    if pr is None:
        print("GATE 1 PASS: push event — gate applies to pull requests")
        return 0

    repo = str(pr["base"]["repo"]["full_name"])
    number = int(pr["number"])
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        files = changed_files(repo, number, token)
    except RuntimeError as exc:
        return _fail(f"could not list PR files — {exc}")
    if not changed_code_files(files):
        print("GATE 1 PASS: no code/prompt changes in this PR (docs-only)")
        return 0

    body = pr.get("body") or ""
    match = MARKER.search(body)
    if match is None:
        return _fail(
            "PR changes code but the description has no "
            "'Test-Plan-Approved: #<issue>' marker citing the pre-approved test plan."
        )
    issue_number = int(match.group(1))

    issue_author = ""
    pr_author = str((pr.get("user") or {}).get("login", ""))
    try:
        issue = _issue_or_none(repo, issue_number, token)
        if issue is None:
            return _fail(
                f"issue not found — the cited #{issue_number} does not exist in {repo}"
                " (check the Test-Plan-Approved number)."
            )
        if issue.get("pull_request") is not None:
            return _fail(
                f"cited number is a pull request, not an issue — #{issue_number} is a PR;"
                " cite the test-plan issue opened from the test-plan issue template."
            )
        issue_author = str((issue.get("user") or {}).get("login", ""))
        comments = _issue_comments(repo, issue_number, token)
    except RuntimeError as exc:
        return _fail(str(exc))

    approval = _qualified_approval(
        comments, issue_author=issue_author, pr_author=pr_author
    )
    if approval is None:
        authors = _marker_authors(comments)
        if authors and authors <= ({pr_author} if pr_author else set()):
            return _fail(
                "the approval comment is by the pull-request author "
                "(self-approval does not count) — have someone other than the "
                "implementer sign the test plan on the issue."
            )
        return _fail(
            f"no approval recorded — issue #{issue_number} has no human "
            "'Test-Plan-Approved' comment by someone other than its author and the PR "
            "author. Get the reviewer to sign the plan on the issue."
        )
    approved_at, _approver = approval

    try:
        impl = _first_implementation_commit(repo, number, token)
    except RuntimeError as exc:
        return _fail(str(exc))
    if impl is None:
        return _fail(
            "no non-merge implementation commit found — cannot verify that the test plan"
            " was approved before implementation. A code PR must have at least one "
            "non-merge commit touching a code/prompt path."
        )
    impl_at, impl_sha = impl

    if approved_at > impl_at:
        return _fail(
            "post-hoc approval — the test plan was approved at "
            f"{approved_at.strftime('%Y-%m-%dT%H:%M:%SZ')} but the first implementation "
            f"commit ({impl_sha[:7]}) landed at "
            f"{impl_at.strftime('%Y-%m-%dT%H:%M:%SZ')}. Approval must precede "
            "implementation."
        )

    print(
        f"GATE 1 PASS: test plan #{issue_number} approved at "
        f"{approved_at.strftime('%Y-%m-%dT%H:%M:%SZ')}, before the first implementation "
        f"commit {impl_sha[:7]} at {impl_at.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
