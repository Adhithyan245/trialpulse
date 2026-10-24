"""Adapters that turn TrialPulse objects into PulseEval cases and traces.

The gate labels every claim from rules over the trial data, never from the model.
PulseEval's evaluators then judge the AI's drafted claim against those labels.
"""

from __future__ import annotations

import re
from collections import Counter

from pulseeval.agent import AgentTrace
from pulseeval.scenarios import RelationshipCase
from pulseeval.timeline import MemberTimeline, Record

from trialpulse.core.models import Claim, Report, Signal
from trialpulse.data.generator import _day_time
from trialpulse.signals.baseline import MONITORED

# The PulseEval commit this gate is wired against.
PULSEEVAL_COMMIT = "db4e475"

# Case-insensitive causal wording that, in any claim, triggers the causal checks.
CAUSAL_CUE = re.compile(
    r"\b(?:"
    r"cause|caused|causes|causing|"
    r"due to|because of|led to|leads to|"
    r"result of|resulting from|"
    r"triggered|induced|drove|driven by|"
    r"attributable to|effect of"
    r")\b",
    re.IGNORECASE,
)

# Word prefixes the relationship evaluator uses to spot exposure/outcome wording.
EXPOSURE_TERMS = [
    "drug",
    "medication",
    "treatment",
    "dose",
    "dosing",
    "therapy",
    "study drug",
    "intervention",
]
OUTCOME_TERMS = [
    "heart",
    "hrv",
    "rmssd",
    "pulse",
    "temperature",
    "temp",
    "respirat",
    "breath",
    "sleep",
    "fatigue",
    "tired",
    "exhaust",
    "spo2",
    "oxygen",
    "strain",
    "physiolog",
    "change",
    "shift",
    "rise",
    "increase",
    "decrease",
    "drop",
    "elevat",
    "symptom",
    "signal",
    "deviation",
    "pattern",
]


def is_causal_or_relationship(claim: Claim) -> bool:
    """A claim needs the causal checks if it is a relationship claim or uses causal wording."""
    return claim.type == "relationship" or bool(CAUSAL_CUE.search(claim.text))


def timeline_for(trial, participant_id: str, as_of_day_dose: int) -> MemberTimeline:
    """All of ``participant_id``'s readings plus one protocol dose-start record.

    ``as_of_day_dose`` is the participant's dose-start trial day; the protocol record
    marks the study drug starting at 08:00 that day.
    """
    records: list[Record] = [
        r for r in trial.readings if r.participant_id == participant_id
    ]

    dose_time = _day_time(as_of_day_dose, 8)
    records.append(
        Record(
            record_id=f"{participant_id}-protocol-dose_start",
            kind="context",
            name="study_drug",
            value="dose started",
            unit=None,
            event_time=dose_time,
            recorded_at=dose_time,
            source="protocol",
        )
    )
    return MemberTimeline(member_id=participant_id, records=records)


def trace_for(report: Report, claim: Claim, payload_record_ids: list[str]) -> AgentTrace:
    """Represent one drafted claim as an AgentTrace for the PulseEval evaluators."""
    return AgentTrace(
        agent_version=report.model_id,
        agent_config={"prompt_version": report.prompt_version},
        query=f"{claim.type} claim in {report.report_id}",
        member_id=report.participant_id,
        as_of=report.as_of,
        time_window=(report.window_start, report.as_of),
        retrieved_context=payload_record_ids,
        tools_called=[],
        memories_used=[],
        evidence_used=claim.cited_record_ids,
        final_answer=claim.text,
        abstention=report.abstained,
    )


def _cited_readings(trial, claim: Claim):
    """The Reading objects a claim cites, in citation order (skipping unknown ids)."""
    by_id = {r.record_id: r for r in trial.readings}
    return [by_id[rid] for rid in claim.cited_record_ids if rid in by_id]


def relationship_case(
    trial, report: Report, claim: Claim, signals: list[Signal]
) -> RelationshipCase:
    """A rule-labelled RelationshipCase for ``claim``.

    Causal support is always ``association_only``: establishing drug-to-event causality
    is the investigator's call, never the gate's.
    """
    cited = _cited_readings(trial, claim)

    metric_names = [r.name for r in cited]
    if metric_names:
        outcome_name = Counter(metric_names).most_common(1)[0][0]
    else:
        outcome_name = "fatigue"

    # Observed direction comes from a drift signal on the outcome metric, if any.
    observed_direction = "none"
    for s in signals:
        if (
            s.participant_id == report.participant_id
            and s.type == "drift"
            and s.metric == outcome_name
        ):
            direction = MONITORED.get(s.metric)
            if direction == "up":
                observed_direction = "positive"
            elif direction == "down":
                observed_direction = "negative"
            break

    # Other metric names among the cited readings, plus the exposure, are confounders.
    confounders = [n for n in dict.fromkeys(metric_names) if n != outcome_name]
    confounders.append("study_drug")

    unit = cited[0].unit if cited and cited[0].unit is not None else ""

    return RelationshipCase(
        case_id=f"{claim.claim_id}-causal",
        description="rule-labelled causal check",
        timeline=timeline_for(
            trial, report.participant_id, _dose_start_day(trial, report.participant_id)
        ),
        question="Is the change related to the study drug?",
        as_of=report.as_of,
        target_name=outcome_name,
        provenance="TrialPulse gate rules",
        window_start=report.window_start,
        exposure_name="study_drug",
        outcome_name=outcome_name,
        exposure_terms=EXPOSURE_TERMS,
        outcome_terms=OUTCOME_TERMS,
        relationship_record_ids=claim.cited_record_ids,
        observed_direction=observed_direction,
        causal_support="association_only",
        confounder_names=confounders,
        expected_group_means={},
        unit=unit,
        tolerance=0.0,
    )


def _dose_start_day(trial, participant_id: str) -> int:
    """The dose-start trial day for ``participant_id``."""
    participant = next(
        (p for p in trial.participants if p.participant_id == participant_id), None
    )
    if participant is None:
        raise ValueError(f"unknown participant_id: {participant_id!r}")
    return participant.dose_start_day
