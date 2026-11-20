"""Structured JSON operational logging (ADR-001; REQ-QUA-002, REQ-SEC-004)."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping


LOGGER = logging.getLogger("contentguard.api")


def log_event(event: str, **fields: object) -> None:
    """Emit one JSON object without raw content, bearer tokens, or credentials."""

    safe: dict[str, object] = {"event": event}
    for key, value in fields.items():
        if key not in {"text", "content", "token", "authorization"}:
            safe[key] = value
    LOGGER.info(json.dumps(safe, sort_keys=True, separators=(",", ":")))


def sanitize_fields(fields: Mapping[str, object]) -> dict[str, object]:
    """Return fields permitted in structured operational logs."""

    return {
        key: value
        for key, value in fields.items()
        if key not in {"text", "content", "token", "authorization"}
    }


__all__ = ["log_event", "sanitize_fields"]
