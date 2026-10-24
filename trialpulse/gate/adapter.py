"""Adapters that turn TrialPulse objects into PulseEval cases and traces.

The gate labels every claim from rules over the trial data, never from the model.
PulseEval's evaluators then judge the AI's drafted claim against those labels.
"""

from __future__ import annotations

import re
from collections import Counter

from pulseeval.agent import AgentTrace
from pulseeval.evaluation.text import coverage_claims
from pulseeval.scenarios import AssessmentCase, NumericCase, RelationshipCase
from pulseeval.timeline import MemberTimeline, Record

from trialpulse.core.models import WEARABLE_METRICS, Claim, GateCheck, Report, Signal
from trialpulse.data.generator import TRIAL_START, _day_time
from trialpulse.signals.baseline import MONITORED, trial_day

# Conclusion words the certainty check watches for (a confident "all clear").
CERTAINTY_CONCLUSION_TERMS = ["normal", "stable", "safe", "no concern", "recovered", "fine"]

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

    # Outcome name (never "symptom_note"):
    #   1) the most common cited MONITORED (baseline) metric;
    #   2) else "fatigue" if a fatigue reading is cited;
    #   3) else the most common cited wearable metric.
    monitored_cited = [n for n in metric_names if n in MONITORED]
    wearable_cited = [n for n in metric_names if n in WEARABLE_METRICS]
    if monitored_cited:
        outcome_name = Counter(monitored_cited).most_common(1)[0][0]
    elif "fatigue" in metric_names:
        outcome_name = "fatigue"
    elif wearable_cited:
        outcome_name = Counter(wearable_cited).most_common(1)[0][0]
    else:
        outcome_name = "fatigue"

    # Observed direction.
    observed_direction = "none"
    if outcome_name == "fatigue":
        if _fatigue_rising(trial, report.participant_id, report.as_of):
            observed_direction = "positive"
    else:
        # From a drift signal on the outcome metric, if any.
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

    # Other cited metric names plus the exposure. A cited "symptom_note" reply is kept
    # here as a confounder (a competing explanation); it can never be the outcome_name.
    confounders = [
        n
        for n in dict.fromkeys(metric_names)
        if n != outcome_name
    ]
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


def _fatigue_rising(trial, participant_id: str, as_of) -> bool:
    """True if fatigue >= 7 on >= 2 of the 4 trial days ending at ``as_of``.

    Only fatigue readings knowable as of ``as_of`` (recorded_at <= as_of) count.
    """
    as_of_day = _as_of_trial_day(as_of)
    window = range(as_of_day - 3, as_of_day + 1)
    high_days = {
        trial_day(r.event_time)
        for r in trial.readings
        if r.participant_id == participant_id
        and r.name == "fatigue"
        and r.recorded_at <= as_of
        and trial_day(r.event_time) in window
        and isinstance(r.value, (int, float))
        and int(r.value) >= 7
    }
    return len(high_days) >= 2



# --- knowable-reading helpers ----------------------------------------------


def _known_readings(trial, participant_id: str, as_of):
    """This participant's readings knowable at ``as_of`` (recorded_at <= as_of)."""
    return [
        r
        for r in trial.readings
        if r.participant_id == participant_id and r.recorded_at <= as_of
    ]


def _as_of_trial_day(as_of) -> int:
    """Trial day (1-based) that ``as_of`` falls on."""
    return (as_of.date() - TRIAL_START.date()).days + 1


# --- coverage (missing-data) check -----------------------------------------


def coverage_applies(claim: Claim) -> bool:
    """A claim needs the coverage check if it is a coverage claim or talks about coverage."""
    if claim.type == "coverage":
        return True
    c = coverage_claims(claim.text)
    return bool(
        c.completeness_claimed
        or c.gap_acknowledged
        or c.available
        or c.total
        or c.missing
    )


def coverage_case(trial, report: Report, claim: Claim) -> NumericCase:
    """A rule-labelled NumericCase measuring resting_hr day coverage for ``claim``.

    A worn day is a day with a resting_hr reading. The window runs from the first
    trial day of the report window through the as-of trial day (inclusive); the
    answer check is disabled (tolerance 1000.0) because only coverage is judged.
    """
    first_day = trial_day(report.window_start)
    as_of_day = _as_of_trial_day(report.as_of)
    expected_observations = as_of_day - first_day + 1
    window_start = _day_time(first_day, 7)

    known = _known_readings(trial, report.participant_id, report.as_of)
    rhr = [
        r
        for r in known
        if r.name == "resting_hr" and first_day <= trial_day(r.event_time) <= as_of_day
    ]
    rhr.sort(key=lambda r: (r.event_time, r.record_id))
    expected_record_ids = [r.record_id for r in rhr]
    values = [float(r.value) for r in rhr if isinstance(r.value, (int, float))]
    expected_value = sum(values) / len(values) if values else 0.0

    timeline = MemberTimeline(member_id=report.participant_id, records=list(rhr))

    return NumericCase(
        case_id=f"{claim.claim_id}-coverage",
        description="rule-labelled resting_hr coverage check",
        timeline=timeline,
        question="How complete is the resting heart rate record for this window?",
        as_of=report.as_of,
        target_name="resting_hr",
        provenance="TrialPulse gate rules",
        window_start=window_start,
        expected_value=expected_value,
        unit="bpm",
        tolerance=1000.0,
        expected_record_ids=expected_record_ids,
        expected_observations=expected_observations,
    )


def coverage_from_data(trial, report: Report) -> tuple[int, int, list[int]]:
    """Resting_hr day coverage computed from the data for this report's window.

    Returns ``(available, expected_observations, missing_days)`` where a day counts as
    available when it has a knowable resting_hr reading. The window runs from the first
    trial day of the report window through the as-of trial day (inclusive).
    """
    first_day = trial_day(report.window_start)
    as_of_day = _as_of_trial_day(report.as_of)
    expected_observations = as_of_day - first_day + 1

    known = _known_readings(trial, report.participant_id, report.as_of)
    worn_days = {
        trial_day(r.event_time)
        for r in known
        if r.name == "resting_hr" and first_day <= trial_day(r.event_time) <= as_of_day
    }
    available = len(worn_days)
    missing_days = [d for d in range(first_day, as_of_day + 1) if d not in worn_days]
    return available, expected_observations, missing_days


def coverage_override(trial, report: Report, claim: Claim) -> GateCheck | None:
    """Decide a complete-data coverage claim from the data, bypassing PulseEval.

    PulseEval's ``coverage_claims`` parser marks both ``completeness_claimed`` and
    ``gap_acknowledged`` for common "complete ... no missing data" phrasings because it
    reads "missing" as a gap acknowledgement even under negation. When both hold the
    claim means "complete, no gaps", so we judge it against the data instead.

    Returns a GateCheck keyed ``f"missing_data:{claim.claim_id}"`` when the override
    applies, or None when it does not (caller should use the PulseEval result).
    """
    cov = coverage_claims(claim.text)
    if not (cov.completeness_claimed and cov.gap_acknowledged):
        return None

    available, expected, missing_days = coverage_from_data(trial, report)
    if available == expected:
        explanation = (
            f"complete-data claim matches the data ({available} of {expected} days); "
            "PulseEval parser read 'missing' as a gap, overridden by rule"
        )
        passed = True
    else:
        missing = ", ".join(str(d) for d in missing_days)
        explanation = (
            f"claims complete data but only {available} of {expected} days are "
            f"available; missing: [{missing}]"
        )
        passed = False
    return GateCheck(
        dimension=f"missing_data:{claim.claim_id}",
        passed=passed,
        explanation=explanation,
    )


# --- contradiction (wearable vs diary) check -------------------------------

_WEARABLE_SELF = {"fatigue", "symptom_note"}


def _recent_fatigue(known, as_of) -> tuple[list, int | None]:
    """Fatigue readings in the last 3 trial days known as of ``as_of`` and their max value."""
    as_of_day = _as_of_trial_day(as_of)
    last3 = range(as_of_day - 2, as_of_day + 1)
    fatigue = [
        r
        for r in known
        if r.name == "fatigue"
        and trial_day(r.event_time) in last3
        and isinstance(r.value, (int, float))
    ]
    max_fatigue = max((int(r.value) for r in fatigue), default=None)
    return fatigue, max_fatigue


def contradiction_applies(trial, report: Report, signals: list[Signal]) -> bool:
    """Whether the contradiction check applies to this report's participant."""
    pid = report.participant_id
    if any(s.participant_id == pid and s.type == "diary_conflict" for s in signals):
        return True
    has_drift = any(s.participant_id == pid and s.type == "drift" for s in signals)
    if has_drift:
        return False
    known = _known_readings(trial, pid, report.as_of)
    as_of_day = _as_of_trial_day(report.as_of)
    last3 = range(as_of_day - 2, as_of_day + 1)
    high_days = {
        trial_day(r.event_time)
        for r in known
        if r.name == "fatigue"
        and trial_day(r.event_time) in last3
        and isinstance(r.value, (int, float))
        and int(r.value) >= 8
    }
    return len(high_days) >= 2


def contradiction_case(trial, report: Report, signals: list[Signal]) -> AssessmentCase:
    """A rule-labelled AssessmentCase comparing today's wearable data with the diary."""
    pid = report.participant_id
    known = _known_readings(trial, pid, report.as_of)
    as_of_day = _as_of_trial_day(report.as_of)

    # Wearable readings on the as-of trial day; else the latest day with any wearable.
    def _wearable_on(day: int):
        return [
            r
            for r in known
            if r.source == "wearable" and trial_day(r.event_time) == day
        ]

    wearable = _wearable_on(as_of_day)
    if not wearable:
        wearable_days = sorted(
            {trial_day(r.event_time) for r in known if r.source == "wearable"}
        )
        if wearable_days:
            wearable = _wearable_on(wearable_days[-1])
    wearable_ids = [r.record_id for r in wearable]

    _, max_fatigue = _recent_fatigue(known, report.as_of)
    last3 = range(as_of_day - 2, as_of_day + 1)
    self_reports = [
        r
        for r in known
        if r.name in _WEARABLE_SELF and trial_day(r.event_time) in last3
    ]
    self_reports.sort(key=lambda r: (r.event_time, r.record_id))
    self_report_ids = [r.record_id for r in self_reports]

    has_drift = any(s.participant_id == pid and s.type == "drift" for s in signals)
    wearable_indicates = "poor" if has_drift else "good"
    if max_fatigue is not None and max_fatigue >= 8:
        self_report_indicates = "poor"
    elif max_fatigue is not None and max_fatigue <= 4:
        self_report_indicates = "good"
    else:
        self_report_indicates = None

    relevant_names = sorted({r.name for r in wearable} | {r.name for r in self_reports})

    timeline = MemberTimeline(
        member_id=pid, records=list(wearable) + list(self_reports)
    )

    window_start = _day_time(trial_day(report.window_start), 7)
    return AssessmentCase(
        case_id=f"{report.report_id}-contradiction",
        description="rule-labelled wearable-vs-diary check",
        timeline=timeline,
        question="How is the participant doing, given the wearable data and the diary?",
        as_of=report.as_of,
        target_name="recovery",
        provenance="TrialPulse gate rules",
        window_start=window_start,
        wearable_record_ids=wearable_ids,
        self_report_record_ids=self_report_ids,
        wearable_indicates=wearable_indicates,
        self_report_indicates=self_report_indicates,
        relevant_names=relevant_names,
    )


# --- certainty (uncertainty / abstention) check ----------------------------


def certainty_level(trial, report: Report, signals: list[Signal]) -> str | None:
    """The certainty label this report must live up to, or None if not evaluated."""
    if contradiction_applies(trial, report, signals):
        case = contradiction_case(trial, report, signals)
        if case.conflict:
            return "conflict_requires_qualification"
    pid = report.participant_id
    if any(s.participant_id == pid and s.type == "non_wear" for s in signals):
        return "uncertainty_required"
    return None


def certainty_case(trial, report: Report, signals: list[Signal], level: str) -> AssessmentCase:
    """A minimal labelled case carrying ``level`` and the certainty conclusion terms.

    Only the ``certainty`` and ``conclusion_terms`` fields drive the evaluator; the
    rest of the AssessmentCase is structural and never read by it.
    """
    pid = report.participant_id
    window_start = _day_time(trial_day(report.window_start), 7)
    return AssessmentCase(
        case_id=f"{report.report_id}-uncertainty",
        description="rule-labelled certainty check",
        timeline=MemberTimeline(member_id=pid, records=[]),
        question="Is it safe to conclude the participant is fine?",
        as_of=report.as_of,
        target_name="recovery",
        provenance="TrialPulse gate rules",
        window_start=window_start,
        wearable_record_ids=[],
        self_report_record_ids=[],
        wearable_indicates="mixed",
        self_report_indicates=None,
        relevant_names=[],
        certainty=level,
        conclusion_terms=list(CERTAINTY_CONCLUSION_TERMS),
    )


def report_trace(report: Report) -> AgentTrace:
    """A trace over the WHOLE report: all claim texts joined, all cited ids unioned."""
    final_answer = " ".join(c.text for c in report.claims)
    cited: list[str] = []
    for c in report.claims:
        for rid in c.cited_record_ids:
            if rid not in cited:
                cited.append(rid)
    return AgentTrace(
        agent_version=report.model_id,
        agent_config={"prompt_version": report.prompt_version},
        query=f"full report {report.report_id}",
        member_id=report.participant_id,
        as_of=report.as_of,
        time_window=(report.window_start, report.as_of),
        retrieved_context=cited,
        tools_called=[],
        memories_used=[],
        evidence_used=cited,
        final_answer=final_answer,
        abstention=report.abstained,
    )
