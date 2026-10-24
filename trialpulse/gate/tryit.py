"""Backend for "Try to fool the checkpoint": gate a claim a judge types, instantly.

A judge picks one of the four :data:`EXAMPLES` scenarios and types a short claim about
that participant. We turn the typed text into a :class:`Report` with rule-labelled
claims and real citations (never the model), run the same reliability gate the AI drafts
go through, and return the verdict. No LLM call is made.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from trialpulse.core.models import Claim, Reading, Report
from trialpulse.data.generator import TRIAL_START
from trialpulse.gate.adapter import CAUSAL_CUE
from trialpulse.gate.live import gate_report, negative_control_summary
from trialpulse.gate.negative_control import links_to_drug
from trialpulse.signals.baseline import trial_day
from trialpulse.signals.detect import detect

# The four scenarios the UI offers.
EXAMPLES: list[dict] = [
    {"participant_id": "P-07", "day": 15, "label": "P-07, day 15 (adverse pattern)"},
    {"participant_id": "P-20", "day": 15, "label": "P-20, day 15 (adverse pattern)"},
    {"participant_id": "P-06", "day": 28, "label": "P-06, day 28 (normal)"},
    {"participant_id": "P-31", "day": 16, "label": "P-31, day 16 (diary conflict)"},
]

# Lowercase word-prefix -> metric. Longer phrases are listed (and checked) first so
# that e.g. "heart rate variab" wins over "heart rate".
METRIC_WORDS: list[tuple[str, str]] = [
    ("heart rate variab", "hrv_rmssd"),
    ("hrv", "hrv_rmssd"),
    ("rmssd", "hrv_rmssd"),
    ("resting heart", "resting_hr"),
    ("rhr", "resting_hr"),
    ("heart rate", "resting_hr"),
    ("pulse", "resting_hr"),
    ("skin temp", "skin_temp"),
    ("temperature", "skin_temp"),
    ("respirat", "respiratory_rate"),
    ("breath", "respiratory_rate"),
    ("sleep", "sleep_hours"),
    ("spo2", "spo2"),
    ("oxygen", "spo2"),
    ("fatigue", "fatigue"),
    ("tired", "fatigue"),
    ("exhaust", "fatigue"),
    ("wear", "wear_minutes"),
    ("worn", "wear_minutes"),
    ("device", "wear_minutes"),
]

# Wording that marks a relationship (association) claim, beyond the causal cue.
_ASSOCIATION_RE = re.compile(
    r"\b(?:associated|related|linked|correlat)", re.IGNORECASE
)

# Coverage wording.
_COVERAGE_RE = re.compile(
    r"\b(?:complete|missing|gap|every day|all days|no data|coverage)\b",
    re.IGNORECASE,
)

# A number followed by a unit (value claim).
_VALUE_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:bpm|ms|%|C|rpm|h|min)\b"
)

# "day N" inside a sentence.
_DAY_RE = re.compile(r"\bday\s+(\d+)\b", re.IGNORECASE)

MAX_TEXT = 600
MIN_TEXT = 8
MAX_CLAIMS = 5


def _as_of(day: int) -> datetime:
    """The clock instant for a trial ``day``: that day at 23:00."""
    return TRIAL_START + timedelta(days=day - 1) + timedelta(hours=23)


def _split_sentences(text: str) -> list[str]:
    """Split ``text`` into sentences on . ! ? (followed by space or end)."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _metrics_in(sentence: str) -> list[str]:
    """Metrics named in ``sentence`` (word-prefix, longer phrases first), de-duplicated."""
    lower = sentence.lower()
    found: list[str] = []
    for word, metric in METRIC_WORDS:
        if word in lower and metric not in found:
            found.append(metric)
    return found


def _claim_type(sentence: str) -> str:
    """Rule-label the claim type for one sentence."""
    if CAUSAL_CUE.search(sentence) or _ASSOCIATION_RE.search(sentence):
        return "relationship"
    if _COVERAGE_RE.search(sentence):
        return "coverage"
    if _VALUE_RE.search(sentence):
        return "value"
    return "assessment"


def _known_readings(
    trial, participant_id: str, metric: str, as_of: datetime
) -> list[Reading]:
    """This participant's readings of ``metric`` knowable at ``as_of``, by event_time."""
    rs = [
        r
        for r in trial.readings
        if r.participant_id == participant_id
        and r.name == metric
        and r.recorded_at <= as_of
    ]
    rs.sort(key=lambda r: (r.event_time, r.record_id))
    return rs


def _cite_metric(
    trial, participant_id: str, metric: str, day: int, as_of: datetime
) -> list[str]:
    """Record ids to cite for one metric, following the task's citation rules."""
    known = _known_readings(trial, participant_id, metric, as_of)
    if not known:
        return []

    as_of_day = (as_of.date() - TRIAL_START.date()).days + 1
    if day is not None:
        selected = [r for r in known if trial_day(r.event_time) == day]
    else:
        window = range(as_of_day - 3, as_of_day + 1)
        selected = [r for r in known if trial_day(r.event_time) in window]

    if not selected:
        # Fall back to the most recent known reading of this metric.
        selected = [known[-1]]

    return [r.record_id for r in selected]


def build_report(trial, participant_id: str, day: int, text: str) -> Report:
    """Turn a typed ``text`` into a rule-labelled :class:`Report` for the gate."""
    text = text.strip()
    if len(text) > MAX_TEXT:
        raise ValueError(f"text is too long: {len(text)} > {MAX_TEXT} characters")
    if len(text) < MIN_TEXT:
        raise ValueError(f"text is too short: {len(text)} < {MIN_TEXT} characters")

    as_of = _as_of(day)
    sentences = _split_sentences(text)[:MAX_CLAIMS]

    report_id = f"TRY-{participant_id}-d{day}"
    claims: list[Claim] = []
    for idx, sentence in enumerate(sentences, start=1):
        metrics = _metrics_in(sentence)
        if not metrics:
            metrics = ["resting_hr"]

        day_match = _DAY_RE.search(sentence)
        named_day = int(day_match.group(1)) if day_match else None

        cited: list[str] = []
        for metric in metrics:
            for rid in _cite_metric(trial, participant_id, metric, named_day, as_of):
                if rid not in cited:
                    cited.append(rid)

        # An uncited claim is invalid: fall back to the participant's most recent
        # known resting_hr reading so every claim cites something real and knowable.
        if not cited:
            rhr = _known_readings(trial, participant_id, "resting_hr", as_of)
            if rhr:
                cited.append(rhr[-1].record_id)

        claims.append(
            Claim(
                claim_id=f"{report_id}-C{idx}",
                type=_claim_type(sentence),
                text=sentence,
                cited_record_ids=cited,
            )
        )

    signals = detect(trial, as_of)
    signal_ids = [s.signal_id for s in signals if s.participant_id == participant_id]

    return Report(
        report_id=report_id,
        participant_id=participant_id,
        signal_ids=signal_ids,
        as_of=as_of,
        window_start=TRIAL_START,
        window_end=as_of,
        claims=claims,
        abstained=False,
        model_id="typed by you",
        prompt_version="try-it",
    )


def run(trial, participant_id: str, day: int, text: str) -> dict:
    """Gate a typed claim and return the report, gate result and negative control."""
    known_pids = {p.participant_id for p in trial.participants}
    if participant_id not in known_pids:
        raise ValueError(f"unknown participant: {participant_id!r}")
    if not 1 <= day <= 28:
        raise ValueError(f"day out of range: {day} (expected 1..28)")

    report = build_report(trial, participant_id, day, text)
    signals = detect(trial, report.as_of)

    gate = gate_report(trial, report, signals)

    if any(links_to_drug(c) for c in report.claims):
        nc = negative_control_summary(trial, report, signals)
    else:
        nc = None

    return {
        "report": report.model_dump(mode="json"),
        "gate": gate.model_dump(mode="json"),
        "negative_control": nc,
    }
