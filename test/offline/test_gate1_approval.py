"""Gate-1 test-plan-approval tests (deterministic, offline).

Verifies: REQ-GOV-002 / TD-2 — gate 1 (``scripts/check_test_approval.py``) must not accept
the PR-body ``Test-Plan-Approved: #<issue>`` marker alone. For a code/prompt PR it must
resolve the cited issue, find the **earliest** qualifying approval comment (a human
comment that is not the issue author, not the pull-request author and not a bot), and
prove that approval precedes the PR's first implementation commit — compared against the
commit's git **author** date (``commit.commit.author.date``), never the committer date,
with merges skipped and per-commit file lists fetched.

The three historical failures from issue #58 are encoded here as negatives (PR #7: never
signed off; #37: approval after implementation; #11: post-hoc approval), plus the PM
sign-off's technical rules and the two 2026-11-19 amendments:

- A1: an approval by the pull-request author is *self-approval* and fails with its own
  message, distinct from "no approval recorded".
- A2: ``GET /issues/{n}/comments`` and ``GET /pulls/{n}/commits`` are paginated
  (``per_page=100`` + ``Link``); a >30-commit PR or a marker past the first page must not be
  lost, or a legitimate approval becomes a false "post-hoc".
- Bot detection is ``user.type == "Bot"`` or a login ending in ``[bot]``; both timestamps
  are normalised to UTC before comparison.

No network and no conftest: the fetch layer (``_api_json``, ``_pull_commits``,
``_commit_code_files``, ``event_payload``, ``changed_files``) is monkeypatched, same style
as ``test_pr_files_headers.py`` / ``test_gate2_safety.py``. This module uses only the
stdlib so it also runs on the 3.10 dev box (CI is 3.12).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = ROOT / "scripts" / "check_test_approval.py"

ISSUE = 58
PR_NUMBER = 101
REPO = "o/r"
ISSUE_AUTHOR = "creator-xiyuan"
PR_AUTHOR = "creator-xiyuan"
REVIEWER = "swordnew123"
MARKER = f"Test-Plan-Approved: #{ISSUE}"


def _load_gate() -> ModuleType:
    """Load the gate module under test without importing pr_files' network paths."""
    spec = importlib.util.spec_from_file_location("check_test_approval_under_test", GATE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _issue(login: str = ISSUE_AUTHOR) -> dict:
    return {
        "number": ISSUE,
        "user": {"login": login, "type": "User"},
        "pull_request": None,
    }


def _pr_issue(login: str = ISSUE_AUTHOR) -> dict:
    """An /issues/{n} object that resolves to a pull request (what a PR number returns)."""
    obj = _issue(login)
    obj["pull_request"] = {"url": f"https://api.github.com/repos/{REPO}/pulls/{ISSUE}"}
    return obj


def _comment(
    login: str,
    created: str,
    body: str = MARKER,
    *,
    updated: str | None = None,
    ctype: str = "User",
) -> dict:
    return {
        "user": {"login": login, "type": ctype},
        "body": body,
        "created_at": created,
        "updated_at": updated if updated is not None else created,
    }


def _commit(
    sha: str,
    author_date: str,
    *,
    parents: list[str] | None = None,
    committer_date: str | None = None,
    files: list[str] | None = None,
) -> dict:
    """A commit as returned by the pulls/{n}/commits endpoint (files optional there)."""
    return {
        "sha": sha,
        "parents": [{"sha": p} for p in (parents if parents is not None else ["p"])],
        "commit": {
            "author": {"date": author_date},
            "committer": {"date": committer_date if committer_date is not None else author_date},
        },
        "_files": files,
    }


def _event(body: str = MARKER) -> dict:
    return {
        "pull_request": {
            "number": PR_NUMBER,
            "body": body,
            "base": {"repo": {"full_name": REPO}},
            "user": {"login": PR_AUTHOR},
        }
    }


def _run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    event: dict,
    files: list[str],
    issue: dict | None,
    comments: list[dict],
    commits: list[dict],
    commit_files: dict[str, list[str]] | None = None,
) -> tuple[int, str, int]:
    """Drive ``main()`` with a mocked fetch layer; return (exit, output, issue_api_calls)."""
    gate = _load_gate()

    calls = {"issue": 0}

    monkeypatch.setattr(gate, "event_payload", lambda: event)
    monkeypatch.setattr(gate, "changed_files", lambda *a, **k: files)

    def fake_issue_api(repo: str, number: int, token: str) -> dict | None:
        calls["issue"] += 1
        return issue

    monkeypatch.setattr(gate, "_issue_or_none", fake_issue_api, raising=False)
    monkeypatch.setattr(
        gate,
        "_issue_comments",
        lambda repo, number, token: list(comments),
        raising=False,
    )
    monkeypatch.setattr(
        gate,
        "_pull_commits",
        lambda repo, number, token: list(commits),
        raising=False,
    )

    resolved = commit_files if commit_files is not None else {}

    def fake_commit_files(repo: str, sha: str, token: str) -> list[str]:
        if sha not in resolved:
            raise RuntimeError(f"file list unavailable for {sha}")
        return [f for f in resolved[sha] if f.startswith(gate.CODE_PREFIXES)]

    monkeypatch.setattr(gate, "_commit_code_files", fake_commit_files, raising=False)

    exit_code = gate.main()
    return exit_code, capsys.readouterr().out, calls["issue"]


def _code_then_docs(
    commit_date: str = "2026-11-19T08:00:00Z",
) -> tuple[list[dict], dict[str, list[str]]]:
    commits = [_commit("aaa", commit_date)]
    return commits, {"aaa": ["src/contentguard/x.py"]}


def test_approved_before_implementation_passes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — human approval precedes the first code commit ⇒ PASS."""
    commits, files_by_sha = _code_then_docs("2026-11-19T08:00:00Z")
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["scripts/check_test_approval.py"],
        issue=_issue(),
        comments=[_comment(REVIEWER, "2026-11-19T07:25:03Z")],
        commits=commits,
        commit_files=files_by_sha,
    )
    assert exit_code == 0
    assert "PASS" in out
    assert f"#{ISSUE}" in out


def test_no_approval_comment_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — negative (missing): issue exists, no approval ⇒
    "no approval recorded", distinct from "issue not found" (issue #58 / PR #7)."""
    commits, files_by_sha = _code_then_docs()
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py"],
        issue=_issue(),
        comments=[_comment(REVIEWER, "2026-11-19T07:25:03Z", body="Looks fine, no marker yet.")],
        commits=commits,
        commit_files=files_by_sha,
    )
    assert exit_code == 1
    assert "GATE 1 FAIL" in out
    assert "no approval recorded" in out
    assert "issue not found" not in out


def test_approval_after_implementation_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — negative (late): approval after the first code
    commit ⇒ FAIL quoting both timestamps and "post-hoc approval" (issue #58 / PR #37)."""
    commits, files_by_sha = _code_then_docs("2026-11-19T08:00:00Z")
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py"],
        issue=_issue(),
        comments=[_comment(REVIEWER, "2026-11-19T09:30:00Z")],
        commits=commits,
        commit_files=files_by_sha,
    )
    assert exit_code == 1
    assert "post-hoc approval" in out
    assert "2026-11-19T09:30:00Z" in out
    assert "2026-11-19T08:00:00Z" in out


def test_cited_number_is_a_pr_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — negative (fake): the cited number is a pull request
    ⇒ distinct "cited number is a pull request, not an issue" (issue #58)."""
    commits, files_by_sha = _code_then_docs()
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py"],
        issue=_pr_issue(),
        comments=[],
        commits=commits,
        commit_files=files_by_sha,
    )
    assert exit_code == 1
    assert "pull request, not an issue" in out


def test_cited_issue_missing_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — negative (fake): 404 on the cited issue ⇒
    "issue not found", distinct from the other messages (issue #58)."""
    commits, files_by_sha = _code_then_docs()
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py"],
        issue=None,
        comments=[],
        commits=commits,
        commit_files=files_by_sha,
    )
    assert exit_code == 1
    assert "issue not found" in out
    assert "no approval recorded" not in out


def test_docs_only_pr_passes_without_issue_lookup(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — a docs-only PR is an early PASS and makes **no**
    issue API call (regression guard for the current early-pass)."""
    exit_code, out, issue_calls = _run(
        monkeypatch,
        capsys,
        event=_event(body="n/a (docs-only)"),
        files=["docs/team/roster.md", "README.md"],
        issue=_issue(),
        comments=[_comment(REVIEWER, "2026-11-19T07:25:03Z")],
        commits=[],
    )
    assert exit_code == 0
    assert "PASS" in out
    assert issue_calls == 0


def test_push_event_passes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — push context (no PR) ⇒ PASS, unchanged behaviour."""
    gate = _load_gate()
    monkeypatch.setattr(gate, "event_payload", lambda: {"ref": "refs/heads/main"})
    exit_code = gate.main()
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "PASS" in out


def test_merge_commit_skipped(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — a merge commit (two parents) touching code is skipped;
    the first non-merge code commit is the implementation anchor."""
    merge = _commit("m1", "2026-11-19T06:00:00Z", parents=["a", "b"])
    real = _commit("c1", "2026-11-19T08:00:00Z")
    files_by_sha = {
        "m1": ["src/contentguard/x.py"],
        "c1": ["src/contentguard/x.py"],
    }
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py"],
        issue=_issue(),
        comments=[_comment(REVIEWER, "2026-11-19T07:25:03Z")],
        commits=[merge, real],
        commit_files=files_by_sha,
    )
    assert exit_code == 0
    assert "PASS" in out


def test_docs_only_commit_before_real_one_skipped(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — a docs-only commit before the code commit does not
    count as the implementation; the first code-file commit is the anchor."""
    docs = _commit("d1", "2026-11-19T05:00:00Z")
    code = _commit("c1", "2026-11-19T08:00:00Z")
    files_by_sha = {
        "d1": ["docs/team/roster.md"],
        "c1": ["src/contentguard/x.py"],
    }
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py", "docs/team/roster.md"],
        issue=_issue(),
        comments=[_comment(REVIEWER, "2026-11-19T07:25:03Z")],
        commits=[docs, code],
        commit_files=files_by_sha,
    )
    assert exit_code == 0
    assert "PASS" in out


def test_edited_approval_uses_updated_at(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — an edited approval comment uses its ``updated_at``;
    the edit that added the marker after the commit is post-hoc."""
    commits, files_by_sha = _code_then_docs("2026-11-19T08:00:00Z")
    edited = _comment(
        REVIEWER,
        "2026-11-19T07:00:00Z",
        updated="2026-11-19T10:00:00Z",
    )
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py"],
        issue=_issue(),
        comments=[edited],
        commits=commits,
        commit_files=files_by_sha,
    )
    assert exit_code == 1
    assert "post-hoc approval" in out
    assert "2026-11-19T10:00:00Z" in out


def test_bot_comment_ignored(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — a bot approval (user.type == "Bot" or login ending
    "[bot]") is ignored; with no human approval the gate reports "no approval recorded"."""
    commits, files_by_sha = _code_then_docs()
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py"],
        issue=_issue(),
        comments=[
            _comment("ci[bot]", "2026-11-19T07:00:00Z", ctype="Bot"),
            _comment("github-actions", "2026-11-19T07:10:00Z", ctype="Bot"),
        ],
        commits=commits,
        commit_files=files_by_sha,
    )
    assert exit_code == 1
    assert "no approval recorded" in out


def test_self_approval_by_pr_author_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — amendment A1: the only marker comment is by the
    pull-request author ⇒ distinct self-approval message, not "no approval recorded"."""
    author = "implementer"
    commits, files_by_sha = _code_then_docs()
    event = _event()
    event["pull_request"]["user"]["login"] = author
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=event,
        files=["src/contentguard/x.py"],
        issue=_issue(login="reporter"),
        comments=[_comment(author, "2026-11-19T07:25:03Z")],
        commits=commits,
        commit_files=files_by_sha,
    )
    assert exit_code == 1
    assert "approval comment is by the pull-request author" in out
    assert "self-approval does not count" in out
    assert "no approval recorded" not in out


def test_pagination_finds_earliest_comment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — amendment A2: pagination must not lose a valid
    approval or pick a later commit.

    Comments past the first page (a qualifying marker and a later one) are found via the
    paginated ``/comments`` endpoint, and a >30-commit PR whose only code commit is last
    is resolved to that last commit — so a legitimate pre-implementation approval PASSes
    instead of becoming a false "post-hoc".
    """
    first_page = [
        _comment(REVIEWER, "2026-11-19T06:30:00Z", body="context") for _ in range(30)
    ]
    second_page = [
        _comment(REVIEWER, "2026-11-19T07:25:03Z"),
        _comment("other-reviewer", "2026-11-19T09:00:00Z"),
    ]
    comments = first_page + second_page

    commits = [
        _commit(f"c{i:03d}", "2026-11-19T05:00:00Z") for i in range(30)
    ]
    commits.append(_commit("code", "2026-11-19T08:00:00Z"))
    files_by_sha = {c["sha"]: ["docs/x.md"] for c in commits}
    for c in commits:
        files_by_sha[c["sha"]] = ["docs/x.md"]
    files_by_sha["code"] = ["src/contentguard/x.py"]

    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py"],
        issue=_issue(),
        comments=comments,
        commits=commits,
        commit_files=files_by_sha,
    )
    assert exit_code == 0, out
    assert "PASS" in out


def test_fail_closed_when_no_code_commit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — no non-merge code commit exists ⇒ FAIL CLOSED with an
    actionable "GATE 1 FAIL", not a silent pass and not a traceback."""
    commits = [_commit("d1", "2026-11-19T05:00:00Z")]
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py"],
        issue=_issue(),
        comments=[_comment(REVIEWER, "2026-11-19T07:25:03Z")],
        commits=commits,
        commit_files={"d1": ["docs/x.md"]},
    )
    assert exit_code == 1
    assert "GATE 1 FAIL" in out


def test_fail_closed_when_commit_files_unavailable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies: REQ-GOV-002 / TD-2 — a commit file list cannot be fetched ⇒ FAIL CLOSED
    with an actionable "GATE 1 FAIL" rather than guessing."""
    commits = [_commit("c1", "2026-11-19T08:00:00Z")]
    exit_code, out, _ = _run(
        monkeypatch,
        capsys,
        event=_event(),
        files=["src/contentguard/x.py"],
        issue=_issue(),
        comments=[_comment(REVIEWER, "2026-11-19T07:25:03Z")],
        commits=commits,
        commit_files={},
    )
    assert exit_code == 1
    assert "GATE 1 FAIL" in out
