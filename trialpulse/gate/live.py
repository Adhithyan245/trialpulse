"""Run the reliability gate over a drafted report and produce a GateResult.

Every claim is checked for temporal consistency. Causal / relationship claims are
additionally checked for causal restraint and evidence grounding. A single failing
check holds the whole report.
"""

from __future__ import annotations

from pulseeval.evaluation.causal import evaluate_causal_restraint
from pulseeval.evaluation.contradiction import evaluate_contradiction_handling
from pulseeval.evaluation.grounding import evaluate_evidence_grounding
from pulseeval.evaluation.missing_data import evaluate_missing_data
from pulseeval.evaluation.temporal import evaluate_temporal_consistency
from pulseeval.evaluation.uncertainty import evaluate_uncertainty_abstention

from trialpulse.core.models import Claim, GateCheck, GateResult, Report, Signal
from trialpulse.gate.adapter import (
    PULSEEVAL_COMMIT,
    certainty_case,
    certainty_level,
    contradiction_applies,
    contradiction_case,
    coverage_applies,
    coverage_case,
    coverage_override,
    is_causal_or_relationship,
    relationship_case,
    report_trace,
    trace_for,
)
from trialpulse.gate.negative_control import check as negative_control_check
from trialpulse.gate.negative_control import compare as _negative_control_compare
from trialpulse.gate.recompute import recompute_check

# Report-level dimension prefixes: their suffix is a report id, not a claim id.
_REPORT_DIMENSIONS = ("contradiction", "uncertainty")


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


def _report_check(result, dimension: str) -> GateCheck:
    """Turn a report-level EvaluationResult into a GateCheck keyed by ``dimension``."""
    explanation = "passed"
    if not result.passed and result.failures:
        explanation = result.failures[0].actual_behavior
    return GateCheck(dimension=dimension, passed=result.passed, explanation=explanation)


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

        # Coverage (missing-data), per claim, only when the claim talks about coverage.
        if coverage_applies(claim):
            override = coverage_override(trial, report, claim)
            if override is not None:
                checks.append(override)
            else:
                cov_case = coverage_case(trial, report, claim)
                cov = evaluate_missing_data(cov_case, trace)
                if cov is not None:
                    checks.append(_check_from_result(cov, claim))

        # Recomputation, per claim, only when the claim states a unit-bearing number.
        rc = recompute_check(claim, _cited_readings(trial, claim))
        if rc is not None:
            checks.append(rc)

        # Negative control, per claim, only when the claim links a change to the drug.
        nc = negative_control_check(trial, report, claim, signals)
        if nc is not None:
            checks.append(nc)

    # Contradiction, per report.
    if contradiction_applies(trial, report, signals):
        con_case = contradiction_case(trial, report, signals)
        con = evaluate_contradiction_handling(con_case, report_trace(report))
        if con is not None:
            checks.append(_report_check(con, f"contradiction:{report.report_id}"))

    # Certainty, per report.
    level = certainty_level(trial, report, signals)
    if level is not None:
        unc_case = certainty_case(trial, report, signals, level)
        unc = evaluate_uncertainty_abstention(unc_case, report_trace(report))
        if unc is not None:
            checks.append(_report_check(unc, f"uncertainty:{report.report_id}"))

    verdict = "hold" if any(not c.passed for c in checks) else "pass"
    return GateResult(
        report_id=report.report_id,
        verdict=verdict,
        checks=checks,
        pulseeval_commit=PULSEEVAL_COMMIT,
    )


def _cited_readings(trial, claim: Claim):
    """The Reading objects a claim cites, in citation order (skipping unknown ids)."""
    by_id = {r.record_id: r for r in trial.readings}
    return [by_id[rid] for rid in claim.cited_record_ids if rid in by_id]


def failed_claims(result: GateResult) -> list[str]:
    """Claim ids that have at least one failing claim-level GateCheck, in first-seen order.

    Each claim-level dimension is ``f"{evaluator}:{claim_id}"``; the claim id is the part
    after the first colon. Report-level dimensions (see ``_REPORT_DIMENSIONS``) are skipped.
    """
    out: list[str] = []
    for check in result.checks:
        if check.passed:
            continue
        prefix = check.dimension.split(":", 1)[0]
        if prefix in _REPORT_DIMENSIONS:
            continue
        claim_id = check.dimension.split(":", 1)[1]
        if claim_id not in out:
            out.append(claim_id)
    return out


def failed_dimensions(result: GateResult) -> list[str]:
    """Distinct dimension prefixes that have at least one failing check, in first-seen order.

    The prefix is the part of a dimension before the first colon, e.g. ``"recompute"`` or
    ``"causal_restraint"``.
    """
    out: list[str] = []
    for check in result.checks:
        if check.passed:
            continue
        prefix = check.dimension.split(":", 1)[0]
        if prefix not in out:
            out.append(prefix)
    return out



def negative_control_summary(trial, report: Report, signals: list[Signal]) -> dict:
    """The negative-control comparison for this report's participant, for the UI."""
    return _negative_control_compare(trial, report.participant_id, report.as_of, signals)
