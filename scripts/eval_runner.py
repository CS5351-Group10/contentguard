"""Gate-4 semantic-evaluation replay runner (REQ-INV-005; reports per REQ-QUA-003).

Loads the fixed evaluation corpus (``test/eval/moderation_eval.jsonl``), the human-authored
expectation policy (``test/eval/expectation_policy.yaml``) and a recorded replay artifact
(``{"eval_id":..., "verdict": allow|block|escalate}`` per line). It derives the expected
verdict/severity per row **from the policy** (first match wins), compares against the replay,
computes the approved metrics and prints a per-slice table.

This is replay, not live: CI never calls a model provider (docs/code-governance/
verification-constraints.md §Tier 3). A fork PR has no secret; the gate must still be
deterministic and offline.

Contract highlights (see issue #26):
  - Rules are evaluated in order, **first match wins** — the broad Jigsaw rules overlap.
  - A row matching NO rule is a **hard failure**, always, when the row is actually evaluated.
    There is no "unmatched ⇒ allow" default and no silent skip.
  - ``slice`` is the corpus's own ``selection_stratum``, unchanged.
  - Derived fields are NEVER written back into the corpus.

Metrics (do not invent others):
  - ``agreement`` = share of rows whose disposition equals ``expected_verdict`` (≥ 0.80).
  - ``safety escape`` = a high-severity row the pipeline allowed — hard 0, never averaged.
  - ``false-block`` = share of ``expected_verdict: allow`` rows the pipeline blocked (≤ 0.10),
    reported per slice; the hard per-slice threshold applies only to slices with ≥10 rows.

Exit codes: 0 = pass (or warn-only without ``--strict``); 1 = fail under ``--strict``.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS = ROOT / "test" / "eval" / "moderation_eval.jsonl"
DEFAULT_POLICY = ROOT / "test" / "eval" / "expectation_policy.yaml"

# Approved thresholds (REQ-QUA-003 release target; docs/code-governance/verification-constraints.md
# §Tier 3; issue #26). REQ-QUA-003 is the source of truth for agreement (>= 85%); the registry
# wins over any older drafting here. test_gate4_enforcement keeps this in lockstep with the registry.
AGREEMENT_MIN = 0.85
FALSE_BLOCK_MAX = 0.10
SAFETY_ESCAPE_MAX = 0
MIN_SLICE_DENOMINATOR = 10

REQUIRED_CORPUS_FIELDS = (
    "eval_id",
    "source",
    "source_language",
    "text",
    "label_scheme",
    "labels",
    "selection_stratum",
    "text_sha256",
)

VALID_DISPOSITIONS = frozenset({"allow", "block", "escalate"})
VALID_VERDICTS = frozenset({"allow", "block", "escalate"})
VALID_SEVERITIES = frozenset({"normal", "high"})
WHEN_KEYS = frozenset({"label_scheme", "any_of", "all_zero", "labels"})


class EvalError(Exception):
    """A replay cannot be evaluated: bad corpus, policy, replay, or an uncovered row."""


@dataclass
class Match:
    rule_id: str
    expected_verdict: str
    expected_severity: str


@dataclass
class ScoredRow:
    eval_id: str
    rule_id: str
    expected_verdict: str
    expected_severity: str
    disposition: str
    slice: str

    @property
    def agrees(self) -> bool:
        return self.disposition == self.expected_verdict


@dataclass
class SliceStat:
    total: int = 0
    allow_expected: int = 0
    false_blocks: int = 0

    @property
    def false_block_rate(self) -> float | None:
        if self.allow_expected == 0:
            return None
        return self.false_blocks / self.allow_expected


@dataclass
class Report:
    rows: list[ScoredRow] = field(default_factory=list)
    per_slice: dict[str, SliceStat] = field(default_factory=dict)
    uncovered: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def agreement(self) -> float:
        if not self.rows:
            return 0.0
        return sum(1 for r in self.rows if r.agrees) / len(self.rows)

    @property
    def safety_escapes(self) -> list[ScoredRow]:
        return [
            r
            for r in self.rows
            if r.expected_severity == "high" and r.disposition == "allow"
        ]

    @property
    def false_block_aggregate(self) -> float | None:
        allow = [r for r in self.rows if r.expected_verdict == "allow"]
        if not allow:
            return None
        blocked = [r for r in allow if r.disposition in ("block", "escalate")]
        return len(blocked) / len(allow)

    @property
    def high_positive_count(self) -> int:
        return sum(1 for r in self.rows if r.expected_severity == "high")

    @property
    def ok(self) -> bool:
        return not check_thresholds(self)


# --------------------------------------------------------------------------- loading
def load_corpus(path: Path) -> list[dict[str, Any]]:
    """Load and validate the JSONL corpus. Raises EvalError on schema/hash/duplicate errors."""
    if not path.exists():
        raise EvalError(f"evaluation corpus not found: {path}")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvalError(f"{path}:{lineno}: invalid JSON — {exc}") from exc
            missing = [f for f in REQUIRED_CORPUS_FIELDS if f not in row]
            if missing:
                raise EvalError(f"{path}:{lineno}: missing corpus field(s): {missing}")
            eval_id = str(row["eval_id"])
            if eval_id in seen:
                raise EvalError(f"{path}:{lineno}: duplicate eval_id {eval_id}")
            seen.add(eval_id)
            digest = hashlib.sha256(str(row["text"]).encode("utf-8")).hexdigest()
            if row["text_sha256"] != digest:
                raise EvalError(
                    f"{path}:{lineno}: text_sha256 does not match text for {eval_id}"
                )
            rows.append(row)
    if not rows:
        raise EvalError(f"evaluation corpus is empty: {path}")
    return rows


def load_policy(path: Path) -> dict[str, Any]:
    """Load and validate the human-authored expectation policy (first-match-wins rules).

    Validation (TD-1): parse errors become ``EvalError`` naming the path; every rule has a
    non-empty unique ``id``, ``expected_verdict`` ∈ {allow, block, escalate},
    ``expected_severity`` ∈ {normal, high}, and a non-empty ``when`` mapping whose keys are a
    subset of ``label_scheme``/``any_of``/``all_zero``/``labels`` (at least one present).
    An unknown ``when`` key would otherwise be silently ignored by ``_when_matches`` — the
    bypass this validation closes.
    """
    if not path.exists():
        raise EvalError(f"expectation policy not found: {path}")
    try:
        policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise EvalError(f"{path}: invalid YAML — {exc}") from exc
    if not isinstance(policy, dict):
        raise EvalError(f"{path}: policy is not a mapping")
    if policy.get("match") != "first_match":
        raise EvalError(f"{path}: policy 'match' must be 'first_match'")
    rules = policy.get("rules")
    if not isinstance(rules, list) or not rules:
        raise EvalError(f"{path}: policy has no rules")

    seen_ids: set[str] = set()
    for index, rule in enumerate(rules):
        where = f"{path}: rule #{index + 1}"
        if not isinstance(rule, dict):
            raise EvalError(f"{where}: rule is not a mapping")
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise EvalError(f"{where}: rule id must be a non-empty string")
        if rule_id in seen_ids:
            raise EvalError(f"{where}: duplicate rule id '{rule_id}'")
        seen_ids.add(rule_id)
        where = f"{path}: rule '{rule_id}'"

        verdict = rule.get("expected_verdict")
        if verdict not in VALID_VERDICTS:
            raise EvalError(
                f"{where}: expected_verdict must be one of {sorted(VALID_VERDICTS)}, "
                f"got {verdict!r}"
            )
        severity = rule.get("expected_severity")
        if severity not in VALID_SEVERITIES:
            raise EvalError(
                f"{where}: expected_severity must be one of {sorted(VALID_SEVERITIES)}, "
                f"got {severity!r}"
            )

        when = rule.get("when")
        if not isinstance(when, dict) or not when:
            raise EvalError(
                f"{where}: 'when' must be a non-empty mapping with at least one of "
                f"{sorted(WHEN_KEYS)}"
            )
        unknown = sorted(set(when) - WHEN_KEYS)
        if unknown:
            raise EvalError(
                f"{where}: unknown 'when' key(s) {unknown}; allowed: {sorted(WHEN_KEYS)}"
            )
    return policy


def load_replay(path: Path) -> dict[str, str]:
    """Load a recorded replay artifact into {eval_id: disposition}."""
    if not path.exists():
        raise EvalError(f"replay artifact not found: {path}")
    replay: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvalError(f"{path}:{lineno}: invalid JSON — {exc}") from exc
            eval_id = str(item.get("eval_id", ""))
            verdict = str(item.get("verdict", ""))
            if not eval_id or verdict not in VALID_DISPOSITIONS:
                raise EvalError(
                    f"{path}:{lineno}: each row needs eval_id and verdict in {sorted(VALID_DISPOSITIONS)}"
                )
            if eval_id in replay:
                raise EvalError(f"{path}:{lineno}: duplicate replay eval_id {eval_id}")
            replay[eval_id] = verdict
    if not replay:
        raise EvalError(f"replay artifact is empty: {path}")
    return replay


# --------------------------------------------------------------------------- derivation
def _when_matches(row: dict[str, Any], when: dict[str, Any]) -> bool:
    """Evaluate one policy ``when`` predicate against a corpus row's native labels."""
    scheme = when.get("label_scheme")
    labels = row.get("labels") or {}
    checks: list[bool] = []
    if scheme is not None:
        checks.append(row.get("label_scheme") == scheme)
    if "any_of" in when:
        checks.append(
            any(
                all(labels.get(k) == v for k, v in pattern.items())
                for pattern in when["any_of"]
            )
        )
    if "all_zero" in when:
        checks.append(all(labels.get(k) == 0 for k in when["all_zero"]))
    if "labels" in when:
        checks.append(all(labels.get(k) == v for k, v in when["labels"].items()))
    return all(checks)


def derive_expectation(row: dict[str, Any], policy: dict[str, Any]) -> Match:
    """Derive the expected verdict/severity for a row via first-match-wins policy rules."""
    for rule in policy["rules"]:
        if _when_matches(row, rule.get("when", {})):
            return Match(
                rule_id=str(rule["id"]),
                expected_verdict=str(rule["expected_verdict"]),
                expected_severity=str(rule["expected_severity"]),
            )
    raise EvalError(
        f"no policy rule matched row {row.get('eval_id')} "
        f"(label_scheme={row.get('label_scheme')}, labels={row.get('labels')}); "
        "uncovered data is a hard failure — add a reviewed rule to the policy"
    )


# --------------------------------------------------------------------------- scoring
def score(
    rows: list[dict[str, Any]], policy: dict[str, Any], replay: dict[str, str]
) -> Report:
    """Compare replay dispositions against policy-derived expectations; build a Report."""
    corpus_ids = {str(r["eval_id"]) for r in rows}
    unknown = sorted(set(replay) - corpus_ids)
    if unknown:
        raise EvalError(f"replay references eval_id(s) not in the corpus: {unknown}")

    report = Report()
    for row in rows:
        eval_id = str(row["eval_id"])
        match = derive_expectation(row, policy)
        if eval_id not in replay:
            report.uncovered.append(eval_id)
            continue
        scored = ScoredRow(
            eval_id=eval_id,
            rule_id=match.rule_id,
            expected_verdict=match.expected_verdict,
            expected_severity=match.expected_severity,
            disposition=replay[eval_id],
            slice=str(row["selection_stratum"]),
        )
        report.rows.append(scored)

        stat = report.per_slice.setdefault(scored.slice, SliceStat())
        stat.total += 1
        if scored.expected_verdict == "allow":
            stat.allow_expected += 1
            if scored.disposition in ("block", "escalate"):
                stat.false_blocks += 1
    return report


def check_thresholds(report: Report) -> list[str]:
    """Return ``FAIL:``-prefixed error strings; empty means the replay meets all thresholds."""
    fails: list[str] = []
    if report.uncovered:
        fails.append(
            f"FAIL: {len(report.uncovered)} corpus row(s) have no replay disposition: "
            f"{report.uncovered[:10]}{' …' if len(report.uncovered) > 10 else ''}"
        )
    escapes = report.safety_escapes
    if len(escapes) > SAFETY_ESCAPE_MAX:
        detail = ", ".join(f"{r.eval_id} ({r.slice}, rule {r.rule_id})" for r in escapes[:10])
        fails.append(
            f"FAIL: {len(escapes)} high-severity safety escape(s) (hard threshold 0): {detail}"
        )
    if report.agreement < AGREEMENT_MIN:
        fails.append(
            f"FAIL: verdict agreement {report.agreement:.2%} < {AGREEMENT_MIN:.0%} threshold"
        )
    fb = report.false_block_aggregate
    if fb is not None and fb > FALSE_BLOCK_MAX:
        fails.append(
            f"FAIL: false-block aggregate {fb:.2%} "
            f"> {FALSE_BLOCK_MAX:.0%} threshold"
        )
    for name, stat in sorted(report.per_slice.items()):
        rate = stat.false_block_rate
        if stat.allow_expected >= MIN_SLICE_DENOMINATOR and rate is not None and rate > FALSE_BLOCK_MAX:
            fails.append(
                f"FAIL: false-block rate {rate:.2%} > {FALSE_BLOCK_MAX:.0%} in slice '{name}' "
                f"({stat.false_blocks}/{stat.allow_expected})"
            )
    return fails


# --------------------------------------------------------------------------- reporting
def format_table(report: Report) -> str:
    """Render the per-slice metrics table plus a per-row audit echo of the derivation."""
    lines: list[str] = []
    fb = report.false_block_aggregate
    fb_str = "N/A" if fb is None else f"{fb:.2%}"
    lines.append(
        f"GATE 4 replay: {report.total} rows scored, "
        f"{report.high_positive_count} high-severity positives, "
        f"agreement {report.agreement:.2%}, "
        f"false-block {fb_str}, "
        f"safety escapes {len(report.safety_escapes)}"
    )
    lines.append("")
    header = f"{'slice':<34} {'rows':>4} {'allow-exp':>9} {'false-blk':>9} {'fb-rate':>8} {'hard':>5}"
    lines.append(header)
    lines.append("-" * len(header))
    for name, stat in sorted(report.per_slice.items()):
        rate = stat.false_block_rate
        rate_str = "N/A" if rate is None else f"{rate:.1%}"
        hard = "yes" if stat.allow_expected >= MIN_SLICE_DENOMINATOR else "no"
        lines.append(
            f"{name:<34} {stat.total:>4} {stat.allow_expected:>9} "
            f"{stat.false_blocks:>9} {rate_str:>8} {hard:>5}"
        )
    lines.append("")
    lines.append("Per-row derivation (eval_id / rule / expected / disposition / slice):")
    for row in report.rows:
        marker = "  " if row.agrees else "!!"
        lines.append(
            f"{marker} {row.eval_id} {row.rule_id} "
            f"{row.expected_verdict}/{row.expected_severity} -> {row.disposition} [{row.slice}]"
        )
    return "\n".join(lines)


def _resolve(arg_value: str | None, default: Path) -> Path:
    return Path(arg_value) if arg_value else default


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. See the module docstring for semantics and exit codes."""
    args = list(sys.argv[1:] if argv is None else argv)
    strict = "--strict" in args

    def opt(name: str) -> str | None:
        if name in args:
            idx = args.index(name)
            if idx + 1 < len(args):
                return args[idx + 1]
        return None

    corpus_path = _resolve(opt("--corpus"), DEFAULT_CORPUS)
    policy_path = _resolve(opt("--policy"), DEFAULT_POLICY)
    replay_arg = opt("--replay")

    if not corpus_path.exists():
        message = (
            f"cannot evaluate: evaluation corpus not found ({corpus_path}). "
            "Fix: land the fixed corpus (PR #37) and configure a replay artifact (TD-1)."
        )
        print(f"GATE 4 {'FAIL' if strict else 'WARNING'}: {message}")
        return 1 if strict else 0
    if replay_arg is None:
        message = (
            "cannot evaluate: no replay artifact configured for this prompt version (TD-1). "
            "Pass --replay <path>; the runner never defaults to a fixture."
        )
        print(f"GATE 4 {'FAIL' if strict else 'WARNING'}: {message}")
        return 1 if strict else 0

    try:
        rows = load_corpus(corpus_path)
        policy = load_policy(policy_path)
        replay = load_replay(Path(replay_arg))
        report = score(rows, policy, replay)
    except EvalError as exc:
        print(f"GATE 4 FAIL: {exc}")
        return 1

    print(format_table(report))
    fails = check_thresholds(report)
    if fails:
        for fail in fails:
            print(fail)
        # A high-severity safety escape or an unevaluable row is fatal regardless of
        # --strict: those are zero-tolerance (REQ-INV-005), never averaged and never
        # softened to a warning. Quality thresholds are strict-gated.
        hard = bool(report.safety_escapes) or bool(report.uncovered)
        if strict or hard:
            print("GATE 4 FAIL: replay does not meet the approved thresholds")
            return 1
        print("GATE 4 WARNING: quality thresholds not met (warn-only; --strict to block)")
        return 0
    print("GATE 4 PASS: recorded replay meets the approved thresholds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
