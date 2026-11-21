"""ContentGuard service interface (ADR-001; REQ-FUN-001/003/004).

The API validates and coordinates requests.  It never decides moderation outcomes;
all consequential transitions remain owned by the deterministic policy engine.
"""

__all__: list[str] = []
