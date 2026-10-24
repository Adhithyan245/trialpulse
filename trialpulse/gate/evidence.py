"""The evidence-seeking loop (Task T10c).

When the reliability gate holds a report, this module decides WHAT evidence would
settle it (rules only, never the model), phrases the request in plain language,
records synthetic replies as new timestamped records, builds redraft feedback,
and re-drafts and re-gates the report.

Rules decide the request kind. The model never chooses a request kind.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel

from trialpulse.agent.prompts import REDRAFT_TEMPLATE
from trialpulse.agent.report import draft_report
from trialpulse.core.models import (
    EvidenceRequest,
    GateResult,
    Reading,
    Report,
    Signal,
)
from trialpulse.gate.live import (
    failed_dimensions,
    gate_report,
    negative_control_summary,
)
from trialpulse.signals.detect import detect

# A failed dimension prefix maps to the request kinds it should trigger.
# "uncertainty" is conditional (only with a non_wear signal); see plan_requests.
RULES: dict[str, list[str]] = {
    "causal_restraint": ["predose_comparison", "symptom_checkin"],
    "negative_control": ["predose_comparison", "symptom_checkin"],
    "missing_data": ["wear_reminder"],
    "uncertainty": ["wear_reminder"],
    "contradiction": ["followup_question"],
    "recompute": [],
    "temporal_consistency": [],
    "evidence_grounding": [],
}

# Plain-language question text per request kind (filled with .format as needed).
QUESTION_TEMPLATES: dict[str, str] = {
    "symptom_checkin": (
        "Since day {start_day}, have you had a fever, a cold, poor sleep or any "
        "other change in how you feel?"
    ),
    "wear_reminder": (
        "We are missing some days of device data. Could you wear the device "
        "tonight and let us know if anything stopped you wearing it?"
    ),
    "followup_question": (
        "Your diary says you feel very tired while your device readings look "
        "normal. Can you tell us more about what has been going on?"
    ),
    "predose_comparison": "Attach the participant's pre-dose comparison to the report.",
    "trial_level_alert": (
        "{n} participants show the same change in {metrics} starting around day "
        "{start_day}. Review at trial level."
    ),
}

# Scripted replies for synthetic participants only, keyed by (participant_id, kind).
SCRIPTED_REPLIES: dict[tuple[str, str], str] = {
    ("P-07", "symptom_checkin"): (
        "I've had a cold since day 11: sore throat, blocked nose, and I slept badly."
    ),
    ("P-20", "symptom_checkin"): "Congestion and poor sleep since about day 11.",
    ("P-31", "followup_question"): (
        "I've been on night shifts all week. I feel wiped out, but no other symptoms."
    ),
}

# Fallback replies by kind when there is no scripted (participant, kind) entry.
_DEFAULT_REPLIES: dict[str, str] = {
    "wear_reminder": "Sorry, my charger broke. I'll wear it again from tonight.",
    "symptom_checkin": "No new symptoms to report.",
    "followup_question": "Nothing else has changed.",
}

# Request kinds that produce a participant reply reading.
_READING_KINDS = ("symptom_checkin", "wear_reminder", "followup_question")


class LoopResult(BaseModel):
    drafts: list[Report]
    gates: list[GateResult]
    requests: list[EvidenceRequest]
    replies: list[Reading]
    final_verdict: str


def _trial_day(when: datetime) -> int:
    from trialpulse.data.generator import TRIAL_START

    return (when.date() - TRIAL_START.date()).days + 1


def _has_non_wear(signals: list[Signal], participant_id: str) -> bool:
    return any(
        s.participant_id == participant_id and s.type == "non_wear" for s in signals
    )


def _participant(trial, participant_id: str):
    return next(
        (p for p in trial.participants if p.participant_id == participant_id), None
    )


def _drift_metrics(signals: list[Signal], participant_id: str) -> list[str]:
    return sorted(
        {
            s.metric
            for s in signals
            if s.participant_id == participant_id and s.type == "drift"
        }
    )


def plan_requests(
    trial,
    report: Report,
    gate_result: GateResult,
    signals: list[Signal],
    now: datetime,
    already_issued: set[str] = frozenset(),
) -> list[EvidenceRequest]:
    """Decide the evidence requests for a held report, from the failing dimensions.

    Rules map each failing dimension prefix to request kinds; kinds are de-duplicated
    per report, and each request's ``failed_dimension`` is the first failing prefix
    that produced that kind. One ``trial_level_alert`` is added when at least two
    participants have drift signals on a common metric as of ``report.as_of`` and this
    report's participant is one of them.

    Kinds already issued for this participant in the loop (``already_issued``) are
    skipped, so the same request is not re-issued across rounds.
    """
    pid = report.participant_id

    # First failing prefix that produced each (participant) kind, in first-seen order.
    kind_order: list[str] = []
    kind_source: dict[str, str] = {}
    for prefix in failed_dimensions(gate_result):
        kinds = RULES.get(prefix, [])
        if prefix == "uncertainty" and not _has_non_wear(signals, pid):
            kinds = []
        for kind in kinds:
            if kind in already_issued:
                continue
            if kind not in kind_source:
                kind_source[kind] = prefix
                kind_order.append(kind)

    # The start day for symptom check-ins and the trial alert: earliest drift window.
    drift_starts = [
        _trial_day(s.window_start)
        for s in signals
        if s.participant_id == pid and s.type == "drift"
    ]
    start_day = min(drift_starts) if drift_starts else _trial_day(report.as_of)

    requests: list[EvidenceRequest] = []
    for kind in kind_order:
        template = QUESTION_TEMPLATES[kind]
        question_text = template.format(start_day=start_day) if "{" in template else template
        requests.append(
            EvidenceRequest(
                request_id=f"REQ-{report.report_id}-{kind}",
                report_id=report.report_id,
                participant_id=pid,
                failed_dimension=kind_source[kind],
                kind=kind,
                question_text=question_text,
                sent_at=now,
                status="open",
            )
        )

    # Trial-level alert: >= 2 participants with drift on a common metric as of as_of,
    # this report's participant being one of them. Skipped if already issued.
    if "trial_level_alert" not in already_issued:
        alert = _trial_level_alert(trial, report, start_day, now)
        if alert is not None:
            requests.append(alert)

    return requests


def _trial_level_alert(
    trial, report: Report, start_day: int, now: datetime
) -> EvidenceRequest | None:
    pid = report.participant_id
    all_signals = detect(trial, report.as_of)

    # metric -> set of participant_ids with a drift signal on that metric.
    by_metric: dict[str, set[str]] = {}
    for s in all_signals:
        if s.type != "drift":
            continue
        by_metric.setdefault(s.metric, set()).add(s.participant_id)

    shared_metrics = sorted(
        m for m, pids in by_metric.items() if len(pids) >= 2 and pid in pids
    )
    if not shared_metrics:
        return None

    # Participants sharing any of these metrics with this participant.
    cohort: set[str] = set()
    for m in shared_metrics:
        cohort |= by_metric[m]
    n = len(cohort)
    metrics_text = ", ".join(shared_metrics)

    return EvidenceRequest(
        request_id=f"REQ-{report.report_id}-trial_level_alert",
        report_id=report.report_id,
        participant_id="TRIAL",
        failed_dimension="trial_level_alert",
        kind="trial_level_alert",
        question_text=QUESTION_TEMPLATES["trial_level_alert"].format(
            n=n, metrics=metrics_text, start_day=start_day
        ),
        sent_at=now,
        status="open",
    )


def _reply_text(participant_id: str, kind: str) -> str:
    scripted = SCRIPTED_REPLIES.get((participant_id, kind))
    if scripted is not None:
        return scripted
    return _DEFAULT_REPLIES[kind]


def answer_requests(
    trial, requests: list[EvidenceRequest], now: datetime
) -> tuple[list[Reading], list[EvidenceRequest]]:
    """Create synthetic replies and mark each request answered.

    For participant requests of a reply-bearing kind, a ``symptom_note`` Reading is
    created and linked to the request. ``predose_comparison`` and ``trial_level_alert``
    get status ``answered`` with no reading.
    """
    replies: list[Reading] = []
    answered: list[EvidenceRequest] = []

    for req in requests:
        if req.kind in _READING_KINDS and req.participant_id != "TRIAL":
            pid = req.participant_id
            participant = _participant(trial, pid)
            site_id = participant.site_id if participant is not None else ""
            text = _reply_text(pid, req.kind)
            record_id = f"{pid}-reply-{req.kind}-{now:%Y%m%d%H%M}"
            reading = Reading(
                record_id=record_id,
                kind="subjective",
                name="symptom_note",
                value=text,
                unit=None,
                event_time=now,
                recorded_at=now,
                source="simulated_reply",
                participant_id=pid,
                site_id=site_id,
            )
            replies.append(reading)
            answered.append(
                req.model_copy(
                    update={"reply_record_id": record_id, "status": "answered"}
                )
            )
        else:
            answered.append(req.model_copy(update={"status": "answered"}))

    return replies, answered


def build_feedback(
    gate_result: GateResult,
    requests: list[EvidenceRequest],
    nc_summary: dict | None,
) -> str:
    """Fill REDRAFT_TEMPLATE with the failing checks, the new evidence, and an
    optional blind-safe pre-dose / trial-wide comparison line."""
    held_lines = [
        f"- {c.explanation}" for c in gate_result.checks if not c.passed
    ]
    held_reasons = "\n".join(held_lines) if held_lines else "- (no reasons recorded)"

    evidence_lines: list[str] = []
    for req in requests:
        if req.reply_record_id is not None:
            evidence_lines.append(f"- [{req.reply_record_id}] {req.question_text}")
    new_evidence = (
        "\n".join(evidence_lines) if evidence_lines else "- (no new evidence)"
    )

    comparison = ""
    if nc_summary is not None:
        p = nc_summary["predose_exceedance_rate"]
        q = nc_summary["postchange_exceedance_rate"]
        trate = nc_summary["trial_drift_rate"]
        comparison = (
            f"Comparison: pre-dose exceedance {p:.0%} versus {q:.0%} after the "
            f"change; a similar pattern appears across {trate:.0%} of the trial."
        )

    return REDRAFT_TEMPLATE.format(
        held_reasons=held_reasons,
        new_evidence=new_evidence,
        comparison=comparison,
    )


def run_loop(
    trial,
    participant_id: str,
    as_of: datetime,
    model,
    fault: str | None = None,
    max_rounds: int = 2,
) -> LoopResult:
    """Draft, gate, and (while held) request evidence, redraft and re-gate.

    The ``fault`` is applied to the first draft only. Returns a LoopResult holding
    every draft and gate, the evidence requests and synthetic replies, and the final
    gate verdict.
    """
    signals = detect(trial, as_of)

    report = draft_report(
        trial, participant_id, as_of, signals, model, fault=fault, report_seq=1
    )
    gate = gate_report(trial, report, signals)

    drafts: list[Report] = [report]
    gates: list[GateResult] = [gate]
    all_requests: list[EvidenceRequest] = []
    all_replies: list[Reading] = []
    issued_kinds: set[str] = set()

    round_num = 1
    while gate.verdict == "hold" and round_num < max_rounds:
        now = as_of + timedelta(minutes=10 * round_num)
        # Never cross midnight: clamp to 23:59 on as_of's calendar day.
        day_end = as_of.replace(hour=23, minute=59, second=0, microsecond=0)
        if now > day_end:
            now = day_end

        requests = plan_requests(
            trial, report, gate, signals, now, already_issued=issued_kinds
        )
        replies, requests = answer_requests(trial, requests, now)
        issued_kinds.update(req.kind for req in requests)
        all_requests.extend(requests)
        all_replies.extend(replies)

        trial = trial.model_copy(update={"readings": trial.readings + replies})

        nc_summary = negative_control_summary(trial, report, signals)
        feedback = build_feedback(gate, requests, nc_summary)

        report = draft_report(
            trial,
            participant_id,
            now,
            signals,
            model,
            fault=None,
            feedback=feedback,
            report_seq=round_num + 1,
        )
        gate = gate_report(trial, report, signals)

        drafts.append(report)
        gates.append(gate)
        round_num += 1

    return LoopResult(
        drafts=drafts,
        gates=gates,
        requests=all_requests,
        replies=all_replies,
        final_verdict=gate.verdict,
    )
