"""De-identification and payload assembly for the blinded AI agent.

The AI drafts safety reports for a BLINDED medical monitor. It must never see
the treatment arm, and it should see no identifying or location detail. It may
only see records that were knowable at the report time (``recorded_at <= as_of``).
"""

from __future__ import annotations

import re
from datetime import datetime

from trialpulse.core.models import Signal
from trialpulse.data.generator import TRIAL_START

# The only Reading fields the agent is allowed to see.
ALLOWED_READING_FIELDS = (
    "record_id",
    "kind",
    "name",
    "value",
    "unit",
    "event_time",
    "recorded_at",
    "source",
)

# Pre-dose baseline days (trial days 1-7) are always visible.
_PREDOSE_DAYS = range(1, 8)

# Order of substitution matters: strip e-mails before phone numbers so the
# digits inside an address are not mistaken for a phone number.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_DATE_RE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b")
# 7+ digits, allowing spaces, dashes, dots, parentheses and a leading +.
_PHONE_RE = re.compile(r"\+?\(?\d[\d\s().\-]{5,}\d")


def scrub_text(text: str) -> str:
    """Redact e-mail addresses, phone numbers and dates from free text.

    E-mails become ``[email]``, phone numbers (7+ digits with optional spaces,
    dashes, dots, parentheses and a leading ``+``) become ``[phone]``, and dates
    written like ``1990-05-17`` or ``05/17/1990`` become ``[date]``. All other
    text is left as is.
    """
    text = _EMAIL_RE.sub("[email]", text)
    text = _DATE_RE.sub("[date]", text)
    text = _PHONE_RE.sub("[phone]", text)
    return text


def _trial_day(when: datetime) -> int:
    """Trial day (1-based) of a datetime (uses its calendar date)."""
    return (when.date() - TRIAL_START.date()).days + 1


def _iso(value):
    """ISO-serialize datetimes; pass through everything else."""
    return value.isoformat() if isinstance(value, datetime) else value


def build_payload(
    trial,
    participant_id: str,
    as_of: datetime,
    signals: list[Signal],
    lookback_days: int = 14,
) -> dict:
    """De-identified, time-correct payload for ``participant_id`` as of ``as_of``.

    Includes this participant's readings that are knowable at ``as_of`` whose
    trial day is within the lookback window ``[as_of_day - lookback_days + 1,
    as_of_day]``, PLUS all pre-dose readings (trial days 1-7) known as of
    ``as_of``. Readings are sorted by ``(event_time, record_id)``, datetimes are
    ISO strings, and ``symptom_note`` values are scrubbed. Arm, site, county,
    enrollment and city details are never included.

    Raises ValueError for an unknown ``participant_id``.
    """
    participant = next(
        (p for p in trial.participants if p.participant_id == participant_id), None
    )
    if participant is None:
        raise ValueError(f"unknown participant_id: {participant_id!r}")

    as_of_day = _trial_day(as_of)
    window_lo = as_of_day - lookback_days + 1

    selected = []
    for r in trial.readings:
        if r.participant_id != participant_id:
            continue
        if r.recorded_at > as_of:
            continue
        rday = _trial_day(r.event_time)
        in_window = window_lo <= rday <= as_of_day
        is_predose = rday in _PREDOSE_DAYS
        if not (in_window or is_predose):
            continue
        selected.append(r)

    selected.sort(key=lambda r: (r.event_time, r.record_id))

    readings = []
    for r in selected:
        row = {}
        for field in ALLOWED_READING_FIELDS:
            val = getattr(r, field)
            if field == "value" and r.name == "symptom_note" and isinstance(val, str):
                val = scrub_text(val)
            row[field] = _iso(val)
        readings.append(row)

    participant_signals = [
        s.model_dump(mode="json") for s in signals if s.participant_id == participant_id
    ]

    return {
        "participant_id": participant_id,
        "as_of": as_of.isoformat(),
        "trial_day": as_of_day,
        "dose_start_day": participant.dose_start_day,
        "readings": readings,
        "signals": participant_signals,
    }
