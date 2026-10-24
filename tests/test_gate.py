"""Tests for the reliability gate (Task T09): temporal consistency and causal restraint.

No network. Reports are built by hand with draft-like claims that cite real record_ids
from generate(7); the de-identified payload is used only to pick knowable citations.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from trialpulse.agent.deid import build_payload
from trialpulse.core.models import Claim, Report
from trialpulse.data.generator import TRIAL_START, generate
from trialpulse.gate.live import failed_claims, gate_report
from trialpulse.signals.detect import detect


def _day_time(day: int, hour: int, minute: int = 0) -> datetime:
    return TRIAL_START + timedelta(days=day - 1) + timedelta(hours=hour, minutes=minute)


def _report(participant_id: str, as_of: datetime, claims: list[Claim]) -> Report:
    """A hand-built Report carrying the given claims."""
    return Report(
        report_id=f"RPT-{participant_id}-{as_of:%Y%m%d%H%M}-1",
        participant_id=participant_id,
        signal_ids=[],
        as_of=as_of,
        window_start=TRIAL_START,
        window_end=as_of,
        claims=claims,
        abstained=False,
        model_id="test-model",
        prompt_version="test-v1",
    )


def _check(result, prefix: str, claim_id: str):
    """The single GateCheck for ``claim_id`` whose evaluator name starts with ``prefix``."""
    matches = [
        c
        for c in result.checks
        if c.dimension.startswith(prefix) and c.dimension.endswith(f":{claim_id}")
    ]
    assert matches, f"no {prefix} check for {claim_id} in {[c.dimension for c in result.checks]}"
    assert len(matches) == 1
    return matches[0]


def test_asserted_causation_is_held():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    claim = Claim(
        claim_id="C-causal-bad",
        type="relationship",
        text="The study drug caused the physiological shifts observed starting on day 12.",
        cited_record_ids=["P-07-d12-resting_hr", "P-07-d12-skin_temp"],
    )
    report = _report("P-07", as_of, [claim])

    result = gate_report(trial, report, signals)

    assert result.verdict == "hold"
    check = _check(result, "causal_restraint", "C-causal-bad")
    assert check.passed is False


def test_caveated_association_passes_causal_restraint():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    claim = Claim(
        claim_id="C-causal-ok",
        type="relationship",
        text=(
            "HRV RMSSD fell after dosing began; this is an association and the cause "
            "is not established."
        ),
        cited_record_ids=["P-07-d13-hrv_rmssd", "P-07-d14-hrv_rmssd"],
    )
    report = _report("P-07", as_of, [claim])

    result = gate_report(trial, report, signals)

    check = _check(result, "causal_restraint", "C-causal-ok")
    assert check.passed is True


def test_future_recorded_citation_fails_temporal():
    trial = generate(7)
    as_of = _day_time(21, 8)
    signals = detect(trial, as_of)

    # P-15's day-20 wearable row was recorded two days later (late sync): not knowable
    # at day 21 08:00.
    claim = Claim(
        claim_id="C-temporal-bad",
        type="value",
        text="Wear time on day 20 was within the expected range.",
        cited_record_ids=["P-15-d20-wear_minutes"],
    )
    report = _report("P-15", as_of, [claim])

    result = gate_report(trial, report, signals)

    assert result.verdict == "hold"
    check = _check(result, "temporal_consistency", "C-temporal-bad")
    assert check.passed is False


def test_plain_value_claim_with_knowable_citations_passes():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    payload = build_payload(trial, "P-07", as_of, signals)
    knowable_ids = {r["record_id"] for r in payload["readings"]}
    assert "P-07-d10-resting_hr" in knowable_ids

    claim = Claim(
        claim_id="C-value-ok",
        type="value",
        text="Resting heart rate on day 10 was recorded.",
        cited_record_ids=["P-07-d10-resting_hr"],
    )
    report = _report("P-07", as_of, [claim])

    result = gate_report(trial, report, signals)

    assert result.verdict == "pass"
    check = _check(result, "temporal_consistency", "C-value-ok")
    assert check.passed is True


def test_failed_claims_lists_exactly_the_failing_claims():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    bad = Claim(
        claim_id="C-bad",
        type="relationship",
        text="The study drug caused the physiological shifts observed starting on day 12.",
        cited_record_ids=["P-07-d12-resting_hr", "P-07-d12-skin_temp"],
    )
    good = Claim(
        claim_id="C-good",
        type="value",
        text="Resting heart rate on day 10 was recorded.",
        cited_record_ids=["P-07-d10-resting_hr"],
    )
    report = _report("P-07", as_of, [bad, good])

    result = gate_report(trial, report, signals)

    assert result.verdict == "hold"
    assert failed_claims(result) == ["C-bad"]
