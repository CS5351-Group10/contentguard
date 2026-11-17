"""Immutable policy snapshot / revision (REQ-FUN-004, REQ-QUA-001).

The snapshot is the enforcement-rule subset pinned to a case. It carries the declared
``rules`` and ``fallback`` (engine behavior follows their declared outcomes) plus a
fixed built-in reason catalog whose **behavior** stays in engine constants — a snapshot
cannot inject a contradictory outcome for ``RULE-HIGH-SEVERITY`` etc., it only supplies
the human-readable reason text for each required built-in id.

``PolicySnapshot.from_dict`` requires exactly the required built-in id set (no missing,
no extra); a missing built-in id raises a :class:`PolicyKernelError` so an emitted
reason id can never be unresolved (REQ-FUN-004).

``SnapshotStore`` (activation / load) is added in the persistence slice.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .contracts import Outcome, Severity, Verdict, digest_of
from .errors import PolicyKernelError

HIGH_SEVERITY_REASON_ID = "RULE-HIGH-SEVERITY"
PREFILTER_HIGH_REASON_ID = "RULE-PREFILTER-HIGH"
HUMAN_REVIEW_REASON_ID = "RULE-HUMAN-REVIEW"

REQUIRED_BUILTIN_REASON_IDS: frozenset[str] = frozenset(
    {
        HIGH_SEVERITY_REASON_ID,
        PREFILTER_HIGH_REASON_ID,
        HUMAN_REVIEW_REASON_ID,
        "FB-ANALYSIS-PROVIDER_UNAVAILABLE",
        "FB-ANALYSIS-TIMEOUT",
        "FB-ANALYSIS-INVALID_RESPONSE",
        "FB-ANALYSIS-GROUNDING_UNAVAILABLE",
        "FB-ANALYSIS-CONTEXT_OVERFLOW",
    }
)


@dataclass(frozen=True)
class RuleCondition:
    """A rule matches when every supplied dimension is satisfied (empty = wildcard)."""

    verdicts: tuple[Verdict, ...] = ()
    severities: tuple[Severity, ...] = ()
    prefilter_labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class PolicyRule:
    """One declared enforcement rule with a stable, resolvable ``rule_id``."""

    rule_id: str
    condition: RuleCondition
    outcome: Outcome
    reason_text: str


@dataclass(frozen=True)
class FallbackRule:
    """The declared fallback applied when no rule matches."""

    fallback_id: str
    outcome: Outcome = Outcome.HOLD
    reason_text: str = "No approved rule matched; held for human review."


@dataclass(frozen=True)
class ReasonEntry:
    """A built-in reason's human-readable text (behavior lives in engine constants)."""

    reason_id: str
    reason_text: str


@dataclass(frozen=True)
class PolicySnapshot:
    """An immutable, digest-addressed enforcement policy snapshot."""

    snapshot_id: str
    revision: int
    rules: tuple[PolicyRule, ...]
    fallback: FallbackRule
    high_severity_terms: tuple[str, ...]
    builtin_reasons: tuple[ReasonEntry, ...]
    digest: str = field(default="")

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise PolicyKernelError("snapshot_id must be non-empty")
        if not isinstance(self.revision, int) or self.revision < 1:
            raise PolicyKernelError("snapshot revision must be an int >= 1")
        seen_rule_ids: set[str] = set()
        for rule in self.rules:
            if rule.rule_id in seen_rule_ids:
                raise PolicyKernelError(f"duplicate rule_id {rule.rule_id!r}")
            seen_rule_ids.add(rule.rule_id)
        builtin_ids = {entry.reason_id for entry in self.builtin_reasons}
        if len(builtin_ids) != len(self.builtin_reasons):
            raise PolicyKernelError("duplicate built-in reason id")
        missing = REQUIRED_BUILTIN_REASON_IDS - builtin_ids
        if missing:
            raise PolicyKernelError(f"snapshot missing required built-in reasons: {sorted(missing)}")
        extra = builtin_ids - REQUIRED_BUILTIN_REASON_IDS
        if extra:
            raise PolicyKernelError(f"snapshot has unexpected built-in reasons: {sorted(extra)}")
        if self.snapshot_id in seen_rule_ids or self.fallback.fallback_id in seen_rule_ids:
            raise PolicyKernelError("rule/fallback ids must not collide with snapshot id")
        # Digest covers the human-readable catalog and every declared rule; behavior
        # constants are not part of it (they cannot be changed by a snapshot).
        computed = digest_of(self._digest_payload())
        if self.digest and self.digest != computed:
            raise PolicyKernelError("snapshot digest does not match its content")
        object.__setattr__(self, "digest", computed)

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "revision": self.revision,
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "condition": {
                        "verdicts": [v.value for v in r.condition.verdicts],
                        "severities": [s.value for s in r.condition.severities],
                        "prefilter_labels": sorted(r.condition.prefilter_labels),
                    },
                    "outcome": r.outcome.value,
                    "reason_text": r.reason_text,
                }
                for r in self.rules
            ],
            "fallback": {
                "fallback_id": self.fallback.fallback_id,
                "outcome": self.fallback.outcome.value,
                "reason_text": self.fallback.reason_text,
            },
            "high_severity_terms": sorted(self.high_severity_terms),
            "builtin_reasons": [
                {"reason_id": e.reason_id, "reason_text": e.reason_text}
                for e in sorted(self.builtin_reasons, key=lambda e: e.reason_id)
            ],
        }

    def reason_text(self, reason_id: str) -> str:
        """Resolve a reason id to its text from this snapshot's catalog (REQ-FUN-004)."""
        for rule in self.rules:
            if rule.rule_id == reason_id:
                return rule.reason_text
        if self.fallback.fallback_id == reason_id:
            return self.fallback.reason_text
        for entry in self.builtin_reasons:
            if entry.reason_id == reason_id:
                return entry.reason_text
        raise PolicyKernelError(f"reason id {reason_id!r} does not resolve in snapshot")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PolicySnapshot:
        """Build a snapshot from the minimal documented mapping (S1 plan §3.3)."""
        try:
            snapshot_id = str(payload["snapshot_id"])
            revision = int(payload["revision"])
            rules = tuple(_rule_from_dict(r) for r in payload["rules"])
            fallback = _fallback_from_dict(payload["fallback"])
            terms = tuple(str(t) for t in payload["high_severity_terms"])
            builtins = tuple(_reason_from_dict(e) for e in payload["builtin_reasons"])
        except KeyError as exc:
            raise PolicyKernelError(f"snapshot payload missing key: {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise PolicyKernelError(f"invalid snapshot payload: {exc}") from exc
        return cls(
            snapshot_id=snapshot_id,
            revision=revision,
            rules=rules,
            fallback=fallback,
            high_severity_terms=terms,
            builtin_reasons=builtins,
        )


def _rule_from_dict(raw: Mapping[str, Any]) -> PolicyRule:
    condition_raw = raw.get("condition", {})
    condition = RuleCondition(
        verdicts=tuple(Verdict(v) for v in condition_raw.get("verdicts", ())),
        severities=tuple(Severity(s) for s in condition_raw.get("severities", ())),
        prefilter_labels=tuple(str(x).casefold() for x in condition_raw.get("prefilter_labels", ())),
    )
    return PolicyRule(
        rule_id=str(raw["rule_id"]),
        condition=condition,
        outcome=Outcome(raw["outcome"]),
        reason_text=str(raw["reason_text"]),
    )


def _fallback_from_dict(raw: Mapping[str, Any]) -> FallbackRule:
    return FallbackRule(
        fallback_id=str(raw["fallback_id"]),
        outcome=Outcome(raw.get("outcome", Outcome.HOLD.value)),
        reason_text=str(
            raw.get("reason_text", "No approved rule matched; held for human review.")
        ),
    )


def _reason_from_dict(raw: Mapping[str, Any]) -> ReasonEntry:
    return ReasonEntry(reason_id=str(raw["reason_id"]), reason_text=str(raw["reason_text"]))


__all__ = [
    "HIGH_SEVERITY_REASON_ID",
    "HUMAN_REVIEW_REASON_ID",
    "PREFILTER_HIGH_REASON_ID",
    "REQUIRED_BUILTIN_REASON_IDS",
    "FallbackRule",
    "PolicyRule",
    "PolicySnapshot",
    "ReasonEntry",
    "RuleCondition",
]
