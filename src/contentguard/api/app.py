"""FastAPI application factory (ADR-001; REQ-FUN-001/003, REQ-SEC-002/003)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from .config import ApiConfig
from .routes import lookup_router, review_router, submissions_router
from .storage import IntakeRepository


def create_app(
    *,
    config: ApiConfig,
    processor: Any,
    lookup_repository: Any | None = None,
    review_repository: Any | None = None,
    review_policy: Any | None = None,
) -> FastAPI:
    """Build the service with explicit ports and no hidden policy authority."""

    app = FastAPI(title="ContentGuard", version="1.0")
    intake_repository = IntakeRepository(config.database_path)
    app.state.api_config = config
    app.state.intake_repository = intake_repository
    app.state.processor = processor
    app.state.lookup_repository = lookup_repository or intake_repository
    app.state.review_repository = review_repository or app.state.lookup_repository
    app.state.review_policy = review_policy
    app.include_router(submissions_router)
    app.include_router(lookup_router)
    app.include_router(review_router)
    return app


__all__ = ["create_app"]
