"""Recomputation check: every number the AI states must match the records it cites.

This is TrialPulse's own deterministic check (not a PulseEval evaluator). For each
unit the AI uses, we take the *affirmed* numbers in the claim text and require each
one to reproduce either a single cited reading in that unit or the mean of all cited
readings in that unit, within a small tolerance. A number whose unit is not present
in any cited reading fails: the AI cannot invent a quantity the evidence does not have.
"""

from __future__ import annotations

from pulseeval.evaluation.text import numbers_with_unit

from trialpulse.core.models import Claim, GateCheck

# Units a reading (or a stated number) can carry in TrialPulse.
UNITS = {"bpm", "ms", "%", "C", "rpm", "h", "min"}


def _tolerance(value: float) -> float:
    """Absolute tolerance for one stated number: the larger of 0.05 and 0.5% of value."""
    return max(0.05, abs(value) * 0.005)


def _matches(stated: float, candidates: list[float]) -> bool:
    """True if ``stated`` is within tolerance of any candidate (a reading or their mean)."""
    tol = _tolerance(stated)
    return any(abs(stated - c) <= tol for c in candidates)


def _fmt(value: float) -> str:
    """Trim a float for the explanation (e.g. 54.2, not 54.20000000001)."""
    return f"{value:.1f}".rstrip("0").rstrip(".") if value % 1 else f"{value:.0f}"


def recompute_check(claim: Claim, cited_readings) -> GateCheck | None:
    """Check that every affirmed number in ``claim.text`` reproduces a cited reading.

    ``cited_readings`` are the Reading objects the claim cites (in citation order).
    Returns a GateCheck keyed ``f"recompute:{claim.claim_id}"``, or None when the claim
    states no number that carries a known unit (nothing to recompute).
    """
    # Group the numeric values of cited readings by their unit.
    values_by_unit: dict[str, list[float]] = {}
    for r in cited_readings:
        if r.unit in UNITS and isinstance(r.value, (int, float)):
            values_by_unit.setdefault(r.unit, []).append(float(r.value))

    checked = 0
    failures: list[str] = []
    for unit in UNITS:
        affirmed = [v for v, polarity in numbers_with_unit(claim.text, unit)
                    if polarity == "affirmed"]
        if not affirmed:
            continue
        cited_values = values_by_unit.get(unit, [])
        mean = sum(cited_values) / len(cited_values) if cited_values else None
        candidates = list(cited_values)
        if mean is not None:
            candidates.append(mean)
        for stated in affirmed:
            checked += 1
            if not candidates or not _matches(stated, candidates):
                name = _reading_name(cited_readings, unit)
                if cited_values:
                    vals = ", ".join(_fmt(v) for v in cited_values)
                    failures.append(
                        f"AI said {_fmt(stated)} {unit}; cited {name} values are "
                        f"{vals} (mean {_fmt(mean)})"
                    )
                else:
                    failures.append(
                        f"AI said {_fmt(stated)} {unit}; no cited reading is in {unit}"
                    )

    if checked == 0:
        return None

    passed = not failures
    explanation = (
        f"all {checked} numbers match the cited records"
        if passed
        else "; ".join(failures)
    )
    return GateCheck(
        dimension=f"recompute:{claim.claim_id}",
        passed=passed,
        explanation=explanation,
    )


def _reading_name(cited_readings, unit: str) -> str:
    """The metric name of the first cited reading in ``unit`` (for the explanation)."""
    for r in cited_readings:
        if r.unit == unit:
            return r.name
    return "reading"
