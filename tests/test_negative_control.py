"""Tests for the negative-control check (Task T10b).

No network. Reports are built by hand with draft-like claims citing real record_ids
from generate(7). The negative control compares a drug-linking claim's change against
the participant's pre-dose days and against the rest of the trial split by arm; a link
is not supported when the same pattern appears at the same rate in both arms.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from trialpulse.core.models import Claim, Report
from trialpulse.data.generator import TRIAL_START, generate
from trialpulse.gate.live import gate_report
from trialpulse.gate.negative_control import check, compare, links_to_drug
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


def _p07_hrv_ids(trial, up_to_day: int) -> list[str]:
    ids = [
        r.record_id
        for r in trial.readings
        if r.participant_id == "P-07"
        and r.name == "hrv_rmssd"
        and (r.event_time.date() - TRIAL_START.date()).days + 1 <= up_to_day
    ]
    assert ids, "P-07 should have knowable hrv_rmssd readings"
    return sorted(ids)


# --- compare() ---------------------------------------------------------------


def test_compare_p07_differs_but_arms_equal():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    result = compare(trial, "P-07", as_of, signals)

    # The change clearly differs from P-07's own pre-dose days.
    assert result["differs_from_predose"] is True

    # One of 20 drifts in each arm (P-07 arm A, P-20 arm B), so the rates are equal.
    assert result["arm_rates"]["A"] == result["arm_rates"]["B"]
    assert result["arm_difference"] == 0.0

    # Same pattern, same rate in both arms -> a drug link is not supported.
    assert result["drug_link_supported"] is False


# --- links_to_drug() ---------------------------------------------------------


def test_links_to_drug_wording():
    linked = Claim(
        claim_id="C-link",
        type="relationship",
        text="HRV dropped after the study drug started.",
        cited_record_ids=["P-07-d12-hrv_rmssd"],
    )
    plain = Claim(
        claim_id="C-plain",
        type="value",
        text="HRV fell to 51.6 ms on day 12.",
        cited_record_ids=["P-07-d12-hrv_rmssd"],
    )
    assert links_to_drug(linked) is True
    assert links_to_drug(plain) is False


# --- check() -----------------------------------------------------------------


def test_check_drug_linked_claim_fails_and_is_blind_safe():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    claim = Claim(
        claim_id="C-nc-bad",
        type="relationship",
        text="HRV dropped after the study drug started.",
        cited_record_ids=_p07_hrv_ids(trial, 15),
    )
    report = _report("P-07", as_of, [claim])

    gc = check(trial, report, claim, signals)
    assert gc is not None
    assert gc.dimension == "negative_control:C-nc-bad"
    assert gc.passed is False
    assert "not supported" in gc.explanation
    # Blind-safe: never names this participant's arm.
    assert " arm A" not in gc.explanation
    assert " arm B" not in gc.explanation


def test_check_plain_value_claim_returns_none():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    claim = Claim(
        claim_id="C-nc-plain",
        type="value",
        text="HRV fell to 51.6 ms on day 12.",
        cited_record_ids=_p07_hrv_ids(trial, 15),
    )
    report = _report("P-07", as_of, [claim])

    assert check(trial, report, claim, signals) is None


# --- integration with gate_report -------------------------------------------


def test_gate_report_holds_on_drug_linked_claim():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    claim = Claim(
        claim_id="C-nc-gate",
        type="relationship",
        text="HRV dropped after the study drug started.",
        cited_record_ids=_p07_hrv_ids(trial, 15),
    )
    report = _report("P-07", as_of, [claim])

    result = gate_report(trial, report, signals)

    assert result.verdict == "hold"
    nc = [c for c in result.checks if c.dimension.startswith("negative_control")]
    assert len(nc) == 1
    assert nc[0].passed is False
