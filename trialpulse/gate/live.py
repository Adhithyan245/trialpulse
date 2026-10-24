"""Run the reliability gate over a drafted report and produce a GateResult.

Every claim is checked for temporal consistency. Causal / relationship claims are
additionally checked for causal restraint and evidence grounding. A single failing
check holds the whole report.
"""

from __future__ import annotations

from pulseeval.evaluation.causal import evaluate_causal_restraint
from pulseeval.evaluation.grounding import evaluate_evidence_grounding
from pulseeval.evaluation.temporal import evaluate_temporal_consistency

from trialpulse.core.models import Claim, GateCheck, GateResult, Report, Signal
from trialpulse.gate.adapter import (
    PULSEEVAL_COMMIT,
    is_causal_or_relationship,
    relationship_case,
    trace_for,
)


def _check_from_result(result, claim: Claim) -> GateCheck:
    """Turn one EvaluationResult into a GateCheck keyed by evaluator and claim."""
    explanation = "passed"
    if not result.passed and result.failures:
        explanation = result.failures[0].actual_behavior
    return GateCheck(
        dimension=f"{result.evaluator}:{claim.claim_id}",
        passed=result.passed,
        explanation=explanation,
    )


def gate_report(trial, report: Report, signals: list[Signal]) -> GateResult:
    """Evaluate every claim in ``report`` and return a pass/hold GateResult."""
    checks: list[GateCheck] = []

    for claim in report.claims:
        case = relationship_case(trial, report, claim, signals)
        trace = trace_for(report, claim, claim.cited_record_ids)

        temporal = evaluate_temporal_consistency(case, trace)
        checks.append(_check_from_result(temporal, claim))

        if is_causal_or_relationship(claim):
            causal = evaluate_causal_restraint(case, trace)
            if causal is not None:
                checks.append(_check_from_result(causal, claim))
            grounding = evaluate_evidence_grounding(case, trace)
            checks.append(_check_from_result(grounding, claim))

    verdict = "hold" if any(not c.passed for c in checks) else "pass"
    return GateResult(
        report_id=report.report_id,
        verdict=verdict,
        checks=checks,
        pulseeval_commit=PULSEEVAL_COMMIT,
    )


def failed_claims(result: GateResult) -> list[str]:
    """Claim ids that have at least one failing GateCheck, in first-seen order.

    Each failing dimension is ``f"{evaluator}:{claim_id}"``; the claim id is the part
    after the first colon.
    """
    out: list[str] = []
    for check in result.checks:
        if check.passed:
            continue
        claim_id = check.dimension.split(":", 1)[1]
        if claim_id not in out:
            out.append(claim_id)
    return out
