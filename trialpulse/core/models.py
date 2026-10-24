"""TrialPulse data contracts (pydantic v2).

The ``Reading`` model subclasses :class:`pulseeval.timeline.Record` directly
(imported, never copied) so that TrialPulse readings are PulseEval records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from pulseeval.timeline import Record

# WHOOP API v2 daily-summary metrics: one row per participant per day.
WEARABLE_METRICS: frozenset[str] = frozenset(
    {
        "resting_hr",       # bpm
        "hrv_rmssd",        # ms
        "spo2",             # %
        "skin_temp",        # C
        "respiratory_rate", # rpm
        "sleep_hours",      # h
        "strain",           # 0-21
        "wear_minutes",     # min
        "user_calibrating", # 0 or 1
    }
)

# Self-reported diary metrics.
DIARY_METRICS: frozenset[str] = frozenset(
    {
        "fatigue",       # 0-10
        "symptom_note",  # free text
    }
)

_ALLOWED_NAMES: frozenset[str] = WEARABLE_METRICS | DIARY_METRICS


class Reading(Record):
    """A single PulseEval record attributed to a participant and site."""

    participant_id: str
    site_id: str

    @field_validator("name")
    @classmethod
    def _name_is_known(cls, v: str) -> str:
        if v not in _ALLOWED_NAMES:
            raise ValueError(f"unknown reading name: {v!r}")
        return v


class Participant(BaseModel):
    participant_id: str
    site_id: str
    arm: Literal["A", "B"]
    enrolled_at: datetime
    dose_start_day: int
    home_county: str


class Signal(BaseModel):
    signal_id: str
    participant_id: str
    type: Literal["drift", "non_wear", "diary_conflict"]
    metric: str
    window_start: datetime
    window_end: datetime
    z_score: float | None
    record_ids: list[str]


class Claim(BaseModel):
    claim_id: str
    type: Literal["value", "coverage", "assessment", "relationship", "certainty"]
    text: str
    cited_record_ids: list[str]

    @field_validator("cited_record_ids")
    @classmethod
    def _must_cite(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("an uncited claim is invalid: cited_record_ids must be non-empty")
        return v


class Report(BaseModel):
    report_id: str
    participant_id: str
    signal_ids: list[str]
    as_of: datetime
    window_start: datetime
    window_end: datetime
    claims: list[Claim]
    abstained: bool
    model_id: str
    prompt_version: str


class EvidenceRequest(BaseModel):
    request_id: str
    report_id: str
    participant_id: str
    failed_dimension: str
    kind: Literal[
        "symptom_checkin",
        "wear_reminder",
        "followup_question",
        "predose_comparison",
        "trial_level_alert",
    ]
    question_text: str
    sent_at: datetime
    reply_record_id: str | None = None
    status: Literal["open", "answered"] = "open"


class GateCheck(BaseModel):
    dimension: str
    passed: bool
    explanation: str


class GateResult(BaseModel):
    report_id: str
    verdict: Literal["pass", "hold"]
    checks: list[GateCheck]
    pulseeval_commit: str


class AuditEntry(BaseModel):
    entry_id: str
    ts: datetime
    actor_role: Literal["system", "monitor", "coordinator", "safety_reviewer"]
    action: Literal[
        "drafted",
        "gated",
        "evidence_requested",
        "evidence_received",
        "approved",
        "rejected",
        "redraft_requested",
    ]
    report_id: str
    details_json: str
    prev_hash: str
    entry_hash: str
