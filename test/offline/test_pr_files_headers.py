"""Gate-helper hardening tests for scripts/pr_files.py (deterministic, offline).

Verifies: TD-3 (gate helper hardening); supports REQ-INV-005 enforcement (gate 4
needs PR context) and gate 1 (TD-2). The 401 defect: an empty GITHUB_TOKEN made
_headers() emit a malformed `Authorization: Bearer ` header, so the GitHub API
answered 401 and gates 1/4 died with a traceback before gate 4/6 could run.

No network: urllib.request.urlopen is monkeypatched in every test.
"""

import io
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import pr_files


def test_headers_omit_authorization_when_token_empty() -> None:
    """Verifies: TD-3 (gate helper hardening); supports REQ-INV-005 enforcement.

    Negative test: an empty token must NOT produce an `Authorization` header, so the
    request is anonymous (200) instead of malformed (401).
    """
    headers = pr_files._headers("")
    assert "Authorization" not in headers
    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["X-GitHub-Api-Version"] == "2022-11-28"


def test_headers_omit_authorization_when_token_whitespace() -> None:
    """Verifies: TD-3 (gate helper hardening); supports REQ-INV-005 enforcement.

    Negative test: a whitespace-only token must also be treated as absent.
    """
    assert "Authorization" not in pr_files._headers("   ")


def test_headers_include_bearer_when_token_present() -> None:
    """Verifies: TD-3 (gate helper hardening); supports REQ-INV-005 enforcement.

    Regression guard: a real token must still be sent as `Bearer <token>`.
    """
    headers = pr_files._headers("abc123")
    assert headers["Authorization"] == "Bearer abc123"


def test_changed_files_raises_actionable_error_on_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies: TD-3 (gate helper hardening); supports REQ-INV-005 enforcement.

    Negative test: a 401 from the API must surface as a clear, actionable RuntimeError
    (naming GITHUB_TOKEN and the gate wiring), not a raw HTTPError traceback.
    """

    def fake_urlopen(*_args: object, **_kwargs: object) -> io.BytesIO:
        raise urllib.error.HTTPError(
            url="https://api.github.com/repos/o/r/pulls/1/files",
            code=401,
            msg="Unauthorized",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,  # type: ignore[arg-type]
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError) as excinfo:
        pr_files.changed_files("o/r", 1, "")
    message = str(excinfo.value)
    assert "401" in message
    assert "GITHUB_TOKEN" in message


def test_changed_files_returns_filenames_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies: TD-3 (gate helper hardening); supports REQ-INV-005 enforcement.

    Regression guard: a successful (anonymous) response still yields the file list.
    """
    payload = b'[{"filename": "src/a.py"}, {"filename": "docs/b.md"}]'

    def fake_urlopen(*_args: object, **_kwargs: object) -> io.BytesIO:
        return io.BytesIO(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert pr_files.changed_files("o/r", 1, "") == ["src/a.py", "docs/b.md"]
