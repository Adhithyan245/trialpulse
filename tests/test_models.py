"""Tests for the TrialPulse data contracts.

Every model round-trips through model_dump_json / model_validate_json unchanged.
Validation rules from the task are exercised explicitly.

``Reading`` subclasses ``pulseeval.timeline.Record``; because we must not copy
Record's field definitions, the test builds a Reading by introspecting the
model's required fields and supplying type-appropriate placeholder values for
any inherited field, while setting the fields the task defines explicitly
(name, participant_id, site_id).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import BaseModel

from pulseeval.timeline import Record

from trialpulse.core.models import (
    DIARY_METRICS,
    WEARABLE_METRICS,
    AuditEntry,
    Claim,
    EvidenceRequest,
    GateCheck,
    GateResult,
    Participant,
    Reading,
    Report,
    Signal,
)

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _build_reading(name: str = "resting_hr", **overrides: Any) -> Reading:
    """Construct a valid Reading with explicit, valid values for all Record fields."""
    data: dict[str, Any] = {
        "record_id": "r0001",
        "kind": "physiological",
        "value": 54.0,
        "unit": "bpm",
        "event_time": NOW,
        "recorded_at": NOW,
        "source": "wearable",
        "name": name,
        "participant_id": "P001",
        "site_id": "S01",
    }
    data.update(overrides)
    return Reading(**data)


def _assert_roundtrip(instance: BaseModel) -> None:
    cls = type(instance)
    restored = cls.model_validate_json(instance.model_dump_json())
    assert restored == instance


# --- round-trip for every model ------------------------------------------


def test_reading_roundtrip():
    _assert_roundtrip(_build_reading())


def test_participant_roundtrip():
    p = Participant(
        participant_id="P001",
        site_id="S01",
        arm="A",
        enrolled_at=NOW,
        dose_start_day=7,
        home_county="Middlesex",
    )
    _assert_roundtrip(p)


def test_signal_roundtrip():
    s = Signal(
        signal_id="SIG1",
        participant_id="P001",
        type="drift",
        metric="resting_hr",
        window_start=NOW,
        window_end=NOW,
        z_score=2.5,
        record_ids=["r1", "r2"],
    )
    _assert_roundtrip(s)


def test_signal_roundtrip_null_zscore():
    s = Signal(
        signal_id="SIG2",
        participant_id="P001",
        type="non_wear",
        metric="wear_minutes",
        window_start=NOW,
        window_end=NOW,
        z_score=None,
        record_ids=["r1"],
    )
    _assert_roundtrip(s)


def test_claim_roundtrip():
    c = Claim(claim_id="C1", type="value", text="rhr rose", cited_record_ids=["r1"])
    _assert_roundtrip(c)


def test_report_roundtrip():
    c = Claim(claim_id="C1", type="coverage", text="worn 20/28 days", cited_record_ids=["r1"])
    r = Report(
        report_id="REP1",
        participant_id="P001",
        signal_ids=["SIG1"],
        as_of=NOW,
        window_start=NOW,
        window_end=NOW,
        claims=[c],
        abstained=False,
        model_id="gemini-x",
        prompt_version="v1",
    )
    _assert_roundtrip(r)


def test_evidence_request_roundtrip_defaults():
    e = EvidenceRequest(
        request_id="ER1",
        report_id="REP1",
        participant_id="P001",
        failed_dimension="coverage",
        kind="wear_reminder",
        question_text="Please wear your band.",
        sent_at=NOW,
    )
    assert e.reply_record_id is None
    assert e.status == "open"
    _assert_roundtrip(e)


def test_evidence_request_roundtrip_answered():
    e = EvidenceRequest(
        request_id="ER2",
        report_id="REP1",
        participant_id="P001",
        failed_dimension="assessment",
        kind="symptom_checkin",
        question_text="How is your fatigue?",
        sent_at=NOW,
        reply_record_id="r9",
        status="answered",
    )
    _assert_roundtrip(e)


def test_gate_check_roundtrip():
    g = GateCheck(dimension="value", passed=True, explanation="recomputed matches")
    _assert_roundtrip(g)


def test_gate_result_roundtrip():
    g = GateResult(
        report_id="REP1",
        verdict="pass",
        checks=[GateCheck(dimension="value", passed=True, explanation="ok")],
        pulseeval_commit="db4e475",
    )
    _assert_roundtrip(g)


def test_audit_entry_roundtrip():
    a = AuditEntry(
        entry_id="A1",
        ts=NOW,
        actor_role="monitor",
        action="approved",
        report_id="REP1",
        details_json="{}",
        prev_hash="0" * 64,
        entry_hash="1" * 64,
    )
    _assert_roundtrip(a)


# --- validation rules -----------------------------------------------------


def test_reading_is_record_subclass_and_instance():
    assert issubclass(Reading, Record)
    assert isinstance(_build_reading(), Record)


def test_reading_rejects_unknown_name():
    with pytest.raises(Exception):
        _build_reading(name="unknown_metric")


def test_reading_accepts_all_known_names():
    for name in WEARABLE_METRICS | DIARY_METRICS:
        assert _build_reading(name=name).name == name


def test_claim_rejects_empty_citations():
    with pytest.raises(Exception):
        Claim(claim_id="C9", type="value", text="uncited", cited_record_ids=[])


def test_signal_rejects_invalid_type():
    with pytest.raises(Exception):
        Signal(
            signal_id="SIGX",
            participant_id="P001",
            type="bogus",
            metric="resting_hr",
            window_start=NOW,
            window_end=NOW,
            z_score=None,
            record_ids=["r1"],
        )


def test_audit_entry_rejects_invalid_action():
    with pytest.raises(Exception):
        AuditEntry(
            entry_id="AX",
            ts=NOW,
            actor_role="system",
            action="exploded",
            report_id="REP1",
            details_json="{}",
            prev_hash="0" * 64,
            entry_hash="1" * 64,
        )
