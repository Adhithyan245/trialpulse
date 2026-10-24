"""Tests for the evidence-seeking loop (Task T10c). No network calls.

A FakeModel returns a causal (drug-linking) claim on its first call, which the
reliability gate holds, then a clean claim on its second call that cites the reply
record id it finds in the user prompt. The loop requests evidence, records the reply
as a new timestamped record, redrafts and re-gates to a pass.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from trialpulse.agent.report import DraftClaim, DraftReport
from trialpulse.data.generator import TRIAL_START, generate
from trialpulse.gate.adapter import relationship_case, trace_for
from trialpulse.gate.evidence import RULES, plan_requests, run_loop
from trialpulse.core.models import Claim, GateCheck, GateResult, Reading, Report
from trialpulse.signals.detect import detect

from pulseeval.evaluation.grounding import evaluate_evidence_grounding


def _day_time(day: int, hour: int, minute: int = 0) -> datetime:
    return TRIAL_START + timedelta(days=day - 1) + timedelta(hours=hour, minutes=minute)


class FakeModel:
    """First call: a drug-linking claim the gate holds. Second call: a clean claim
    citing the reply record id found in the user prompt."""

    name = "fake-loop-model-1"

    def __init__(self) -> None:
        self.calls = 0
        self.systems: list[str] = []
        self.users: list[str] = []

    def generate(self, system: str, user: str, schema):
        self.calls += 1
        self.systems.append(system)
        self.users.append(user)

        ids = re.findall(r'"record_id":"([^"]+)"', user)

        if self.calls == 1:
            # A drug-linking claim: exposure + outcome wording -> negative control holds.
            hrv_ids = [rid for rid in ids if rid.endswith("hrv_rmssd")] or ids[:1]
            return DraftReport(
                claims=[
                    DraftClaim(
                        type="relationship",
                        text="HRV dropped after the study drug started.",
                        cited_record_ids=hrv_ids,
                    )
                ],
                abstained=False,
            )

        # Second call: a clean claim citing the reply record id.
        reply_ids = [rid for rid in ids if "-reply-" in rid]
        cite = reply_ids if reply_ids else ids[:1]
        return DraftReport(
            claims=[
                DraftClaim(
                    type="assessment",
                    text="The participant reported a cold with a sore throat and poor sleep.",
                    cited_record_ids=cite,
                )
            ],
            abstained=False,
        )


def _report(participant_id: str, as_of: datetime, claims) -> Report:
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


def test_run_loop_holds_then_passes_after_evidence():
    trial = generate(7)
    as_of = _day_time(15, 23)
    model = FakeModel()

    result = run_loop(trial, "P-07", as_of, model, fault="causal_overclaim", max_rounds=2)

    assert len(result.drafts) == 2
    assert result.gates[0].verdict == "hold"
    assert result.final_verdict == "pass"


def test_requests_cover_expected_kinds():
    trial = generate(7)
    as_of = _day_time(15, 23)
    model = FakeModel()

    result = run_loop(trial, "P-07", as_of, model, fault="causal_overclaim", max_rounds=2)

    kinds = {r.kind for r in result.requests}
    assert "symptom_checkin" in kinds
    assert "predose_comparison" in kinds
    assert "trial_level_alert" in kinds

    allowed = {k for kinds_list in RULES.values() for k in kinds_list} | {"trial_level_alert"}
    for req in result.requests:
        assert req.kind in allowed


def test_exactly_one_reply_for_p07_and_request_answered():
    trial = generate(7)
    as_of = _day_time(15, 23)
    model = FakeModel()

    result = run_loop(trial, "P-07", as_of, model, fault="causal_overclaim", max_rounds=2)

    p07_replies = [r for r in result.replies if r.participant_id == "P-07"]
    assert len(p07_replies) == 1
    reply = p07_replies[0]
    assert reply.source == "simulated_reply"
    assert reply.recorded_at > as_of

    checkin = [
        r
        for r in result.requests
        if r.kind == "symptom_checkin" and r.participant_id == "P-07"
    ]
    assert len(checkin) == 1
    assert checkin[0].status == "answered"
    assert checkin[0].reply_record_id == reply.record_id


def test_second_system_prompt_has_feedback_not_fault():
    trial = generate(7)
    as_of = _day_time(15, 23)
    model = FakeModel()

    run_loop(trial, "P-07", as_of, model, fault="causal_overclaim", max_rounds=2)

    assert model.calls == 2
    second_system = model.systems[1]
    assert "held by the reliability gate" in second_system
    # The fault text was applied to the first draft only.
    assert "State plainly that the study drug caused the changes you see." not in second_system


def test_plan_requests_missing_data_only_wear_reminder():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    # P-01 has no drift at day 15, so no trial-level alert is added either.
    report = _report("P-01", as_of, [])
    gate = GateResult(
        report_id=report.report_id,
        verdict="hold",
        checks=[
            GateCheck(
                dimension="missing_data:some-claim",
                passed=False,
                explanation="missing days",
            )
        ],
        pulseeval_commit="db4e475",
    )

    requests = plan_requests(trial, report, gate, signals, as_of)
    assert [r.kind for r in requests] == ["wear_reminder"]



class AlwaysCausalModel:
    """Always returns a drug-linking claim the gate holds, so the report stays held
    across every round."""

    name = "fake-loop-model-causal"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, system: str, user: str, schema):
        self.calls += 1
        ids = re.findall(r'"record_id":"([^"]+)"', user)
        hrv_ids = [rid for rid in ids if rid.endswith("hrv_rmssd")] or ids[:1]
        return DraftReport(
            claims=[
                DraftClaim(
                    type="relationship",
                    text="HRV dropped after the study drug started.",
                    cited_record_ids=hrv_ids,
                )
            ],
            abstained=False,
        )


def test_no_duplicate_requests_across_rounds():
    trial = generate(7)
    as_of = _day_time(15, 23)
    model = AlwaysCausalModel()

    result = run_loop(trial, "P-07", as_of, model, fault="causal_overclaim", max_rounds=3)

    # Three drafts, all held; the loop keeps redrafting until max_rounds.
    assert len(result.drafts) == 3
    assert result.final_verdict == "hold"

    # Exactly one reply Reading despite staying held across rounds.
    assert len(result.replies) == 1

    # Each request kind appears exactly once: no duplicates across rounds.
    kinds = [r.kind for r in result.requests]
    assert len(kinds) == len(set(kinds))



def test_all_drafts_stay_on_as_of_calendar_date():
    """Redraft time uses 10-minute steps clamped to 23:59, so with as_of at
    day 15 23:00 every draft in a 3-round loop stays on the same calendar date."""
    trial = generate(7)
    as_of = _day_time(15, 23)
    model = AlwaysCausalModel()

    result = run_loop(trial, "P-07", as_of, model, fault="causal_overclaim", max_rounds=3)

    assert len(result.drafts) == 3
    for draft in result.drafts:
        assert draft.as_of.date() == as_of.date()


def test_relationship_citing_hrv_plus_reply_symptom_note_grounds():
    """A relationship claim citing P-07 HRV readings plus the participant's reply
    (a symptom_note, the competing cold explanation) passes evidence_grounding: the
    reply is legitimate evidence, kept as a confounder and never the outcome."""
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    # The simulated reply, as the evidence loop would record it, but timestamped within
    # the report window so only grounding (not temporal) is exercised.
    site_id = next(r.site_id for r in trial.readings if r.participant_id == "P-07")
    reply_id = "P-07-reply-symptom_checkin-202501151200"
    reply = Reading(
        record_id=reply_id,
        kind="subjective",
        name="symptom_note",
        value="I think I caught a cold - sore throat and poor sleep.",
        unit=None,
        event_time=_day_time(15, 12),
        recorded_at=_day_time(15, 12),
        source="simulated_reply",
        participant_id="P-07",
        site_id=site_id,
    )
    trial.readings.append(reply)

    claim = Claim(
        claim_id="C-rel-reply",
        type="relationship",
        text=(
            "HRV RMSSD fell over days 13 to 14; the participant separately reported a "
            "cold, which offers an alternative explanation."
        ),
        cited_record_ids=["P-07-d13-hrv_rmssd", "P-07-d14-hrv_rmssd", reply_id],
    )
    report = _report("P-07", as_of, [claim])

    case = relationship_case(trial, report, claim, signals)
    # The reply is a confounder (competing explanation), never the outcome.
    assert "symptom_note" in case.confounder_names
    assert case.outcome_name != "symptom_note"
    assert "symptom_note" in case.relevant_names

    trace = trace_for(report, claim, claim.cited_record_ids)
    grounding = evaluate_evidence_grounding(case, trace)
    assert grounding.passed is True
