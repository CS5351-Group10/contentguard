"""Domain and model validation errors for ADR-001, REQ-FUN-005 and REQ-INV-002."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .contracts import DomainErrorCode


@dataclass(frozen=True)
class DomainValidationError:
    """Pure snapshot-validation failure without attempt identity (REQ-FUN-005, REQ-INV-002)."""

    code: DomainErrorCode
    detail: str
    snapshot_id: str
    revision: int


@dataclass(frozen=True)
class ModelValidationError:
    """Pure model-output failure without attempt identity (REQ-SEC-001, REQ-INV-002)."""

    code: Literal["invalid_response"]
    detail: str
