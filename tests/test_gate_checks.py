"""Tests for the extra gate checks (Task T10): coverage, recomputation, contradiction,
certainty.

No network. Reports are built by hand with draft-like claims that cite real record_ids
from generate(7). Numeric values used in recomputation claims are read back from the
generated trial so the test never hard-codes a seeded number.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from trialpulse.agent.deid import build_payload
from trialpulse.core.models import Claim, Report
from trialpulse.data.generator import TRIAL_START, generate
from trialpulse.gate.live import failed_dimensions, gate_report
from trialpulse.signals.detect import detect


def _day_time(day: int, hour: int, minute: int = 0) -> datetime:
    return TRIAL_START + timedelta(days=day - 1) + timedelta(hours=hour, minutes=minute)


def _report(participant_id: str, as_of: datetime, claims: list[Claim]) -> Report:
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


def _check(result, prefix: str):
    """The single GateCheck whose dimension starts with ``prefix``."""
    matches = [c for c in result.checks if c.dimension.startswith(prefix)]
    assert matches, f"no {prefix} check in {[c.dimension for c in result.checks]}"
    assert len(matches) == 1, [c.dimension for c in matches]
    return matches[0]


def _reading_value(trial, record_id: str) -> float:
    r = next(r for r in trial.readings if r.record_id == record_id)
    return float(r.value)


# --- coverage (missing data) --------------------------------------------------

_COVERAGE_TEXT = "Data was complete across all days with no missing days."


def test_coverage_false_completeness_is_held():
    trial = generate(7)
    as_of = _day_time(28, 23)
    signals = detect(trial, as_of)

    payload = build_payload(trial, "P-06", as_of, signals)
    rhr_ids = [r["record_id"] for r in payload["readings"] if r["name"] == "resting_hr"]
    assert rhr_ids, "P-06 should have at least one knowable resting_hr reading"

    claim = Claim(
        claim_id="C-cov-bad",
        type="coverage",
        text=_COVERAGE_TEXT,
        cited_record_ids=rhr_ids[:1],
    )
    report = _report("P-06", as_of, [claim])

    result = gate_report(trial, report, signals)

    assert result.verdict == "hold"
    check = _check(result, "missing_data")
    assert check.passed is False


def test_coverage_claim_passes_when_window_complete():
    # PulseEval limitation: "with no missing days" phrasing is parsed as acknowledging
    # a gap, so we use "with no gaps" instead to test true completeness detection.
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    payload = build_payload(trial, "P-07", as_of, signals)
    rhr_ids = [r["record_id"] for r in payload["readings"] if r["name"] == "resting_hr"]
    assert rhr_ids

    claim = Claim(
        claim_id="C-cov-ok",
        type="coverage",
        text="All 15 days had data with no gaps.",
        cited_record_ids=rhr_ids[:1],
    )
    report = _report("P-07", as_of, [claim])

    result = gate_report(trial, report, signals)

    check = _check(result, "missing_data")
    assert check.passed is True


# Common "complete ... no missing data" phrasings PulseEval marks as both
# completeness_claimed and gap_acknowledged (it reads "missing" as a gap). The
# coverage override judges these from the data instead of the parser result.
_COMPLETE_SENTENCES = [
    "Wearable and diary records are complete across the observation window from trial "
    "day 1 to day 15 without missing data periods.",
    "Wearable and daily self-report records are complete across all 15 observation days "
    "with no missing windows.",
]


def test_complete_data_claims_pass_for_full_window():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    payload = build_payload(trial, "P-07", as_of, signals)
    rhr_ids = [r["record_id"] for r in payload["readings"] if r["name"] == "resting_hr"]
    assert rhr_ids

    for i, sentence in enumerate(_COMPLETE_SENTENCES):
        claim = Claim(
            claim_id=f"C-cov-complete-{i}",
            type="coverage",
            text=sentence,
            cited_record_ids=rhr_ids[:1],
        )
        report = _report("P-07", as_of, [claim])

        result = gate_report(trial, report, signals)

        check = _check(result, "missing_data")
        assert check.passed is True, sentence


def test_complete_data_claim_fails_for_incomplete_window():
    trial = generate(7)
    as_of = _day_time(28, 23)
    signals = detect(trial, as_of)

    payload = build_payload(trial, "P-06", as_of, signals)
    rhr_ids = [r["record_id"] for r in payload["readings"] if r["name"] == "resting_hr"]
    assert rhr_ids

    claim = Claim(
        claim_id="C-cov-complete-bad",
        type="coverage",
        text=_COMPLETE_SENTENCES[1],
        cited_record_ids=rhr_ids[:1],
    )
    report = _report("P-06", as_of, [claim])

    result = gate_report(trial, report, signals)

    assert result.verdict == "hold"
    check = _check(result, "missing_data")
    assert check.passed is False


# --- recomputation ------------------------------------------------------------


def _p07_rhr_ids(trial, up_to_day: int) -> list[str]:
    ids = [
        r.record_id
        for r in trial.readings
        if r.participant_id == "P-07"
        and r.name == "resting_hr"
        and (r.event_time.date() - TRIAL_START.date()).days + 1 <= up_to_day
    ]
    return sorted(ids)


def test_recompute_wrong_number_is_held():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    cited = _p07_rhr_ids(trial, 15)[:3]
    values = [_reading_value(trial, rid) for rid in cited]

    claim = Claim(
        claim_id="C-rc-bad",
        type="value",
        text="Resting heart rate reached 99.0 bpm.",
        cited_record_ids=cited,
    )
    report = _report("P-07", as_of, [claim])

    result = gate_report(trial, report, signals)

    assert result.verdict == "hold"
    check = _check(result, "recompute")
    assert check.passed is False
    # The cited values appear in the plain-language reason.
    for v in values:
        assert f"{v:.1f}".rstrip("0").rstrip(".") in check.explanation


def test_recompute_exact_cited_value_passes():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    cited = _p07_rhr_ids(trial, 15)[:3]
    exact = _reading_value(trial, cited[0])

    claim = Claim(
        claim_id="C-rc-exact",
        type="value",
        text=f"Resting heart rate was {exact:.1f} bpm on a recorded day.",
        cited_record_ids=cited,
    )
    report = _report("P-07", as_of, [claim])

    result = gate_report(trial, report, signals)

    check = _check(result, "recompute")
    assert check.passed is True


def test_recompute_mean_of_cited_values_passes():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    cited = _p07_rhr_ids(trial, 15)[:3]
    values = [_reading_value(trial, rid) for rid in cited]
    mean = sum(values) / len(values)

    claim = Claim(
        claim_id="C-rc-mean",
        type="value",
        text=f"Resting heart rate averaged {mean:.1f} bpm over the cited days.",
        cited_record_ids=cited,
    )
    report = _report("P-07", as_of, [claim])

    result = gate_report(trial, report, signals)

    check = _check(result, "recompute")
    assert check.passed is True


# --- contradiction (wearable vs diary) ----------------------------------------


def _p31_day16_ids(trial) -> list[str]:
    ids = [
        r.record_id
        for r in trial.readings
        if r.participant_id == "P-31"
        and (r.event_time.date() - TRIAL_START.date()).days + 1 == 16
        and r.recorded_at <= _day_time(16, 23)
    ]
    assert ids, "P-31 should have day-16 readings"
    return sorted(ids)


def test_contradiction_unacknowledged_sources_is_held():
    trial = generate(7)
    as_of = _day_time(16, 23)
    signals = detect(trial, as_of)

    claim = Claim(
        claim_id="C-con-bad",
        type="assessment",
        text="Wearable metrics remain normal and stable.",
        cited_record_ids=_p31_day16_ids(trial),
    )
    report = _report("P-31", as_of, [claim])

    result = gate_report(trial, report, signals)

    assert result.verdict == "hold"
    check = _check(result, "contradiction")
    assert check.passed is False


def test_contradiction_both_sources_flagged_passes():
    trial = generate(7)
    as_of = _day_time(16, 23)
    signals = detect(trial, as_of)

    claim = Claim(
        claim_id="C-con-ok",
        type="assessment",
        text=(
            "Wearable data looks normal, but the participant's diary reports feeling "
            "exhausted; the two sources conflict."
        ),
        cited_record_ids=_p31_day16_ids(trial),
    )
    report = _report("P-31", as_of, [claim])

    result = gate_report(trial, report, signals)

    check = _check(result, "contradiction")
    assert check.passed is True


# --- certainty (uncertainty / abstention) -------------------------------------


def test_overconfident_conclusion_under_non_wear_is_held():
    trial = generate(7)
    as_of = _day_time(28, 23)
    signals = detect(trial, as_of)
    assert any(s.participant_id == "P-02" and s.type == "non_wear" for s in signals)

    payload = build_payload(trial, "P-02", as_of, signals)
    some_id = [r["record_id"] for r in payload["readings"]][:1]
    assert some_id

    claim = Claim(
        claim_id="C-cert-bad",
        type="certainty",
        text="Recovery is definitely normal.",
        cited_record_ids=some_id,
    )
    report = _report("P-02", as_of, [claim])

    result = gate_report(trial, report, signals)

    assert result.verdict == "hold"
    check = _check(result, "uncertainty")
    assert check.passed is False
    assert "uncertainty" in failed_dimensions(result)
