"""REST route modules for the ContentGuard API (ADR-001; REQ-FUN-001/003)."""

from .lookup import router as lookup_router
from .review import router as review_router
from .submissions import router as submissions_router

__all__ = ["lookup_router", "review_router", "submissions_router"]
