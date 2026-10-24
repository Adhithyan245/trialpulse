"""Tests for the tamper-evident audit log with e-signatures (Task T11).

No network calls. A small LoopResult is built with a fake model as in
tests/test_evidence.py.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from trialpulse.agent.report import DraftClaim, DraftReport
from trialpulse.api.audit import (
    GENESIS,
    AuditLog,
    record_loop,
    sign,
    tamper_for_demo,
)
from trialpulse.data.generator import TRIAL_START, generate
from trialpulse.gate.evidence import run_loop
from trialpulse.core.models import Report


def _day_time(day: int, hour: int, minute: int = 0) -> datetime:
    return TRIAL_START + timedelta(days=day - 1) + timedelta(hours=hour, minutes=minute)


class FakeModel:
    """First call: a drug-linking claim the gate holds. Second call: a clean claim
    citing the reply record id found in the user prompt."""

    name = "fake-loop-model-1"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, system: str, user: str, schema):
        self.calls += 1
        ids = re.findall(r'"record_id":"([^"]+)"', user)

        if self.calls == 1:
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


def _report(participant_id: str = "P-07") -> Report:
    as_of = _day_time(15, 23)
    return Report(
        report_id=f"RPT-{participant_id}-1",
        participant_id=participant_id,
        signal_ids=[],
        as_of=as_of,
        window_start=TRIAL_START,
        window_end=as_of,
        claims=[],
        abstained=False,
        model_id="test-model",
        prompt_version="test-v1",
    )


def _append_five(log: AuditLog) -> list:
    ts = _day_time(15, 10)
    entries = []
    for i in range(5):
        entries.append(
            log.append(
                actor_role="system",
                action="drafted",
                report_id="RPT-X-1",
                details={"n": i},
                ts=ts + timedelta(seconds=i),
            )
        )
    return entries


def test_append_five_verifies_and_chains():
    log = AuditLog(":memory:")
    entries = _append_five(log)

    result = log.verify()
    assert result["ok"] is True
    assert result["checked"] == 5
    assert result["first_bad_entry_id"] is None

    # prev_hash chaining: first is GENESIS, each subsequent points at the prior hash.
    assert entries[0].prev_hash == GENESIS
    for prev, cur in zip(entries, entries[1:]):
        assert cur.prev_hash == prev.entry_hash


def test_tamper_breaks_chain_at_entry_three():
    log = AuditLog(":memory:")
    entries = _append_five(log)
    target = entries[2]  # entry 3

    tamper_for_demo(log._conn, target.entry_id, {"n": 999})

    result = log.verify()
    assert result["ok"] is False
    assert result["first_bad_entry_id"] == target.entry_id
    assert result["reason"]


def test_file_backed_log_survives_reopen(tmp_path):
    path = str(tmp_path / "audit.sqlite3")

    log = AuditLog(path)
    _append_five(log)
    first = log.verify()
    assert first["ok"] is True
    assert first["checked"] == 5

    reopened = AuditLog(path)
    again = reopened.verify()
    assert again["ok"] is True
    assert again["checked"] == 5
    assert len(reopened.entries()) == 5


def test_record_loop_action_order():
    trial = generate(7)
    as_of = _day_time(15, 23)
    model = FakeModel()
    loop = run_loop(trial, "P-07", as_of, model, fault="causal_overclaim", max_rounds=2)

    assert len(loop.drafts) == 2

    log = AuditLog(":memory:")
    recorded = record_loop(log, loop, _day_time(16, 9))

    actions = [e.action for e in recorded]
    # Round 0: drafted, gated, then evidence_requested..., evidence_received...
    assert actions[0] == "drafted"
    assert actions[1] == "gated"

    # Second draft/gate appears after the first round's evidence entries.
    second_drafted = actions.index("drafted", 2)
    assert actions[second_drafted + 1] == "gated"

    # All evidence_requested in round 0 come before any evidence_received in round 0,
    # and both precede the second drafted entry.
    first_round = actions[2:second_drafted]
    if "evidence_received" in first_round:
        last_req = max(
            i for i, a in enumerate(first_round) if a == "evidence_requested"
        )
        first_recv = min(
            i for i, a in enumerate(first_round) if a == "evidence_received"
        )
        assert last_req < first_recv

    assert log.verify()["ok"] is True


def test_sign_empty_reason_raises():
    log = AuditLog(":memory:")
    report = _report()
    try:
        sign(
            log,
            report,
            actor_role="monitor",
            signer="Dr. Smith",
            decision="approved",
            reason="",
            ts=_day_time(16, 10),
        )
        assert False, "expected ValueError for empty reason"
    except ValueError:
        pass


def test_sign_valid_appends_approved_entry():
    import json

    log = AuditLog(":memory:")
    report = _report()
    entry = sign(
        log,
        report,
        actor_role="monitor",
        signer="Dr. Smith",
        decision="approved",
        reason="Readings and reply support the assessment.",
        ts=_day_time(16, 10),
    )

    assert entry.action == "approved"
    details = json.loads(entry.details_json)
    assert "report_hash" in details
    assert "meaning" in details
    assert report.report_id in details["meaning"]
    assert log.verify()["ok"] is True


def test_log_has_no_mutation_methods():
    log = AuditLog(":memory:")
    assert not hasattr(log, "update")
    assert not hasattr(log, "delete")
    assert not hasattr(log, "remove")
