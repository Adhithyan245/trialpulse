"""Negative-control check for claims that link a change to the study drug.

Before a report may link a change to the study drug at all (causal *or* association
wording), the change is compared against two controls that need no unblinding of the
participant:

1. the participant's own pre-dose days (trial days 1-7), and
2. the rest of the trial, split by arm in aggregate only.

If the pattern is just as common in both arms, a drug link is not supported. The
monitor is blinded, so explanations never state this participant's arm.
"""

from __future__ import annotations

import re

from trialpulse.core.models import Claim, GateCheck, Report, Signal
from trialpulse.gate.adapter import EXPOSURE_TERMS, OUTCOME_TERMS
from trialpulse.signals.baseline import MONITORED, PREDOSE_DAYS, personal_bands, trial_day
from trialpulse.signals.detect import detect

# Exposure terms that mark a drug link; reuse the gate's exposure vocabulary.
DRUG_TERMS = EXPOSURE_TERMS


def _mentions(text: str, terms: list[str]) -> bool:
    """True if ``text`` mentions any of ``terms`` as a word-prefix, case-insensitive."""
    for term in terms:
        pattern = r"\b" + re.escape(term)
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def links_to_drug(claim: Claim) -> bool:
    """A claim links a change to the study drug if it mentions an exposure term AND an
    outcome term (both word-prefix, case-insensitive)."""
    return _mentions(claim.text, DRUG_TERMS) and _mentions(claim.text, OUTCOME_TERMS)


def _deviates(value: float, band: dict[str, float], direction: str) -> bool:
    if direction == "up":
        return value > band["hi"]
    return value < band["lo"]


def _day_metric_value(trial, participant_id: str, as_of, day: int, metric: str):
    """The numeric value of ``participant_id``'s ``metric`` on trial ``day`` knowable at
    ``as_of``, or None if there is no such reading."""
    for r in trial.readings:
        if r.participant_id != participant_id or r.name != metric:
            continue
        if r.recorded_at > as_of:
            continue
        if trial_day(r.event_time) != day:
            continue
        if not isinstance(r.value, (int, float)):
            continue
        return float(r.value)
    return None


def _exceedance_rate(trial, participant_id, as_of, days, metrics, bands) -> float:
    """Fraction of (day, metric) pairs outside the personal band in the deviation
    direction, over pairs that have a knowable numeric reading."""
    total = 0
    exceed = 0
    for day in days:
        for metric in metrics:
            value = _day_metric_value(trial, participant_id, as_of, day, metric)
            if value is None:
                continue
            total += 1
            if _deviates(value, bands[participant_id][metric], MONITORED[metric]):
                exceed += 1
    if total == 0:
        return 0.0
    return exceed / total


def compare(trial, participant_id: str, as_of, signals: list[Signal]) -> dict:
    """Compare the participant's change against the pre-dose and cross-arm controls.

    Returns a JSON-serializable dict (see module docstring for the controls).
    """
    bands = personal_bands(trial)

    # The participant's drift metrics as of as_of.
    drift_metrics = sorted(
        {
            s.metric
            for s in signals
            if s.participant_id == participant_id and s.type == "drift"
        }
    )

    # Pre-dose days (1-7) knowable as of as_of.
    predose_days = [
        d
        for d in PREDOSE_DAYS
        if any(
            _day_metric_value(trial, participant_id, as_of, d, m) is not None
            for m in drift_metrics
        )
    ]

    # Drift window days: the trial days spanned by this participant's drift signals.
    drift_days: set[int] = set()
    for s in signals:
        if s.participant_id == participant_id and s.type == "drift":
            start = trial_day(s.window_start)
            end = trial_day(s.window_end)
            drift_days.update(range(start, end + 1))
    drift_window_days = sorted(drift_days)

    predose_rate = _exceedance_rate(
        trial, participant_id, as_of, predose_days, drift_metrics, bands
    )
    postchange_rate = _exceedance_rate(
        trial, participant_id, as_of, drift_window_days, drift_metrics, bands
    )
    differs_from_predose = postchange_rate > predose_rate + 0.5

    # Trial-wide drift, split by arm (aggregate only).
    all_signals = detect(trial, as_of)
    drift_pids = {
        s.participant_id for s in all_signals if s.type == "drift"
    }
    participants = trial.participants
    n_total = len(participants)
    trial_drift_rate = len(drift_pids) / n_total if n_total else 0.0

    arm_rates: dict[str, float] = {}
    for arm in ("A", "B"):
        arm_pids = [p.participant_id for p in participants if p.arm == arm]
        drifters = sum(1 for pid in arm_pids if pid in drift_pids)
        arm_rates[arm] = drifters / len(arm_pids) if arm_pids else 0.0
    arm_difference = abs(arm_rates["A"] - arm_rates["B"])

    drug_link_supported = differs_from_predose and arm_difference >= 0.10

    return {
        "metrics": drift_metrics,
        "predose_exceedance_rate": predose_rate,
        "postchange_exceedance_rate": postchange_rate,
        "differs_from_predose": differs_from_predose,
        "trial_drift_rate": trial_drift_rate,
        "arm_rates": arm_rates,
        "arm_difference": arm_difference,
        "drug_link_supported": drug_link_supported,
    }


def check(trial, report: Report, claim: Claim, signals: list[Signal]) -> GateCheck | None:
    """A negative-control GateCheck for a drug-linking claim, or None otherwise.

    The explanation is blind-safe: it never names this participant's arm.
    """
    if not links_to_drug(claim):
        return None

    result = compare(trial, report.participant_id, report.as_of, signals)
    ok = result["drug_link_supported"]

    p = result["predose_exceedance_rate"]
    q = result["postchange_exceedance_rate"]
    a = result["arm_rates"]["A"]
    b = result["arm_rates"]["B"]
    N = len(trial.participants)
    n = round(result["trial_drift_rate"] * N)

    explanation = (
        f"Pre-dose exceedance {p:.0%}, after the change {q:.0%}; the same pattern "
        f"appears in {n} of {N} participants, at {a:.0%} and {b:.0%} in the two "
        f"treatment groups. A link to the study drug is "
        f"{'supported' if ok else 'not supported'} by these controls."
    )

    return GateCheck(
        dimension=f"negative_control:{claim.claim_id}",
        passed=ok,
        explanation=explanation,
    )
