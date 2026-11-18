"""Deterministic high-severity pre-filter (REQ-INV-003, REQ-QUA-001).

Literal, case-folded substring matching only — no regex, so there is no ReDoS surface.
Terms come from the pinned snapshot; matching is deterministic and labels are sorted so
the result is reproducible for identical input (QUA-001).
"""

from __future__ import annotations

from .contracts import PrefilterResult


class DeterministicPrefilter:
    """Match a fixed set of literal terms against text, case-insensitively."""

    def __init__(self, terms: tuple[str, ...]) -> None:
        # Normalise once: case-fold and drop empties; sorted for deterministic ordering.
        folded = {t.casefold() for t in terms if t and t.strip()}
        self._terms: tuple[str, ...] = tuple(sorted(folded))

    @property
    def terms(self) -> tuple[str, ...]:
        """The normalised, sorted set of literal terms."""
        return self._terms

    def evaluate(self, text: str) -> PrefilterResult:
        """Return the sorted matched terms and whether a high-severity hit exists."""
        haystack = text.casefold()
        matched = tuple(term for term in self._terms if term in haystack)
        return PrefilterResult(
            labels=matched,
            high_severity=bool(matched),
            matched_terms=matched,
        )


__all__ = ["DeterministicPrefilter"]
