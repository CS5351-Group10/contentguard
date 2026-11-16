"""Gate 7 (review-memo presence) tests — deterministic, offline.

Verifies the memo-enforcement gap: per docs/review-memo.md every PR needs an RM memo
posted by a NON-author reviewer before merge, but no gate enforced it (2026-11-15 PR #2
review incident; issue #4). These tests cover every row of issue #4's edge-case table,
including the three negative cases, plus the fetch helpers added to scripts/pr_files.py
and the multi-page pagination path.

No requirement-registry ID applies (governance infrastructure; issue #4 "Fit criteria
covered: n/a"). Source: docs/review-memo.md rule 1 + issue #4.

No network: urllib.request.urlopen is monkeypatched in every test that touches fetching.
"""

import io
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import pr_files
from check_review_memo import find_memo

AUTHOR = "alice"
REVIEWER = "bob"

FULL_MEMO = (
    "## RM-004 — PR #8\n"
    "- Reviewer(s): bob\n"
    "- Spec alignment: ...\n"
    "- Verdict: APPROVE\n"
)


# ---------------------------------------------------------------------------
# find_memo — pure detection logic (issue #4 edge-case table)
# ---------------------------------------------------------------------------


def test_memo_detected_non_author() -> None:
    """Verifies issue #4: non-author + RM number + Verdict line -> memo detected."""
    entries = [(REVIEWER, FULL_MEMO)]
    assert find_memo(entries, AUTHOR) == FULL_MEMO


def test_author_self_memo_rejected() -> None:
    """Verifies issue #4 (negative): a full memo-shaped entry by the PR AUTHOR is rejected.

    Mirrors the PR #2 incident: the author's own RM-002 skeleton comment contains
    `Verdict: APPROVE` but its author is the PR author, so it must not count.
    """
    entries = [(AUTHOR, FULL_MEMO)]
    assert find_memo(entries, AUTHOR) is None


def test_missing_verdict_rejected() -> None:
    """Verifies issue #4 (negative): an RM number without a Verdict line is rejected."""
    body = "## RM-004 — PR #8\n- Reviewer(s): bob\n- Spec alignment: ...\n"
    entries = [(REVIEWER, body)]
    assert find_memo(entries, AUTHOR) is None


def test_missing_rm_rejected() -> None:
    """Verifies issue #4 (negative): a Verdict line without an RM number is rejected."""
    body = "- Reviewer(s): bob\n- Verdict: APPROVE\n"
    entries = [(REVIEWER, body)]
    assert find_memo(entries, AUTHOR) is None


def test_case_insensitive_match() -> None:
    """Verifies issue #4: lowercase variants (`rm-004`, `verdict: approve`) are accepted."""
    body = "rm-004\nverdict: approve\n"
    entries = [(REVIEWER, body)]
    assert find_memo(entries, AUTHOR) == body


def test_verdict_requires_enum_value() -> None:
    """Verifies issue #4: `Verdict:` must be one of APPROVE / CHANGES REQUIRED / REJECT.

    Negative: a verdict-like line with an arbitrary value does not count.
    """
    body = "RM-004\nVerdict: looks fine to me\n"
    entries = [(REVIEWER, body)]
    assert find_memo(entries, AUTHOR) is None


def test_multiple_memos_first_valid_wins() -> None:
    """Verifies issue #4: with several entries the first VALID memo is returned.

    Earlier invalid entries (author-posted, then RM-only) are skipped before the valid
    non-author memo is found.
    """
    invalid_author = (AUTHOR, "RM-001\nVerdict: APPROVE\n")
    invalid_no_verdict = (REVIEWER, "RM-002\njust a note\n")
    valid = (REVIEWER, "RM-004\nVerdict: CHANGES REQUIRED\n")
    entries = [invalid_author, invalid_no_verdict, valid]
    assert find_memo(entries, AUTHOR) == valid[1]


def test_memo_accepts_changes_required_and_reject_verdicts() -> None:
    """Verifies issue #4: any valid Verdict enum value counts as a memo (state of review
    does not matter; branch protection still requires an approving review to merge)."""
    for verdict in ("APPROVE", "CHANGES REQUIRED", "REJECT", "approve"):
        body = f"RM-004\nVerdict: {verdict}\n"
        assert find_memo([(REVIEWER, body)], AUTHOR) == body


# ---------------------------------------------------------------------------
# Fetch helpers + pagination (scripts/pr_files.py)
# ---------------------------------------------------------------------------


def _http_error(code: int, url: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url=url,
        code=code,
        msg="error",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,  # type: ignore[arg-type]
    )


def test_pull_reviews_fetches_review_bodies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies issue #4: pull_reviews() returns review dicts from the reviews endpoint."""
    payload = b'[{"user": {"login": "bob"}, "body": "RM-004\\nVerdict: APPROVE"}]'
    seen: list[str] = []

    def fake_urlopen(req: object, *_args: object, **_kwargs: object) -> io.BytesIO:
        seen.append(getattr(req, "full_url", ""))
        return io.BytesIO(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    reviews = pr_files.pull_reviews("o/r", 8, "")
    assert reviews[0]["user"]["login"] == "bob"
    assert any(url.endswith("/pulls/8/reviews?per_page=100&page=1") for url in seen)


def test_issue_comments_fetches_comment_bodies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies issue #4: issue_comments() reads the issue-comments endpoint.

    Negative-x: this endpoint lives under /issues/, so it needs the `issues: read`
    workflow permission (not `pull-requests: read`) — otherwise 403.
    """
    payload = b'[{"user": {"login": "bob"}, "body": "RM-004\\nVerdict: APPROVE"}]'
    seen: list[str] = []

    def fake_urlopen(req: object, *_args: object, **_kwargs: object) -> io.BytesIO:
        seen.append(getattr(req, "full_url", ""))
        return io.BytesIO(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    comments = pr_files.issue_comments("o/r", 8, "")
    assert comments[0]["body"].startswith("RM-004")
    assert any(url.endswith("/issues/8/comments?per_page=100&page=1") for url in seen)


def test_pagination_merges_multiple_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies issue #4: paginated fetch merges >100 items across pages.

    Page 1 returns 100 items (full page -> fetch page 2); page 2 returns 1 item (short
    page -> stop). The merged list must contain all 101, in order.
    """
    page1 = b"[" + b",".join(b'{"filename": "f%d"}' % i for i in range(100)) + b"]"
    page2 = b'[{"filename": "last"}]'
    responses = [page1, page2]
    calls: list[str] = []

    def fake_urlopen(req: object, *_args: object, **_kwargs: object) -> io.BytesIO:
        calls.append(getattr(req, "full_url", ""))
        return io.BytesIO(responses[len(calls) - 1])

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    files = pr_files.changed_files("o/r", 8, "")
    assert len(files) == 101
    assert files[0] == "f0"
    assert files[-1] == "last"
    assert len(calls) == 2


def test_pull_reviews_raises_actionable_error_on_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies issue #4: fetch helpers reuse the actionable-401 error style (same as
    changed_files) instead of a raw HTTPError traceback."""

    def fake_urlopen(req: object, *_args: object, **_kwargs: object) -> io.BytesIO:
        raise _http_error(401, getattr(req, "full_url", ""))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError) as excinfo:
        pr_files.pull_reviews("o/r", 8, "")
    message = str(excinfo.value)
    assert "401" in message
    assert "GITHUB_TOKEN" in message


def test_pull_reviews_raises_actionable_error_on_403(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies issue #4: a 403 (e.g. missing `issues: read` permission) surfaces as an
    actionable RuntimeError, not a bare traceback."""

    def fake_urlopen(req: object, *_args: object, **_kwargs: object) -> io.BytesIO:
        raise _http_error(403, getattr(req, "full_url", ""))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError) as excinfo:
        pr_files.issue_comments("o/r", 8, "")
    assert "403" in str(excinfo.value)
