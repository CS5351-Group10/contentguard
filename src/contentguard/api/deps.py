"""FastAPI authentication dependency (ADR-001; REQ-SEC-002/003)."""

from __future__ import annotations

import hashlib
from hmac import compare_digest

from fastapi import HTTPException, Request, status

from .models import RequestContext


def require_actor(request: Request) -> RequestContext:
    """Resolve one opaque bearer token to trusted server-side actor context.

    Missing, malformed, and unknown credentials deliberately share one response.
    Client JSON never participates in identity resolution.
    """

    header = request.headers.get("Authorization", "")
    scheme, separator, token = header.partition(" ")
    if not separator or not compare_digest(scheme.lower(), "bearer") or not token.strip():
        raise _unauthorized()
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    actor = request.app.state.api_config.api_tokens.get(digest)
    if actor is None:
        raise _unauthorized()
    return RequestContext(
        actor_id=actor.actor_id,
        actor_type=actor.actor_type,
        scopes=actor.scopes,
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


__all__ = ["require_actor"]
