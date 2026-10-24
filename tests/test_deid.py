"""Tests for the de-identified agent payload (Task T05)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from trialpulse.agent.deid import ALLOWED_READING_FIELDS, build_payload, scrub_text
from trialpulse.data.generator import TRIAL_START, generate
from trialpulse.signals.detect import detect


def _day_time(day: int, hour: int, minute: int = 0) -> datetime:
    return TRIAL_START + timedelta(days=day - 1) + timedelta(hours=hour, minutes=minute)


def test_payload_hides_blinding_and_location():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)
    payload = build_payload(trial, "P-07", as_of, signals)
    dumped = json.dumps(payload)
    for forbidden in (
        "arm",
        "site_id",
        "home_county",
        "Boston",
        "Worcester",
        "Springfield",
        "Suffolk",
        "Hampden",
    ):
        assert forbidden not in dumped, f"payload leaked {forbidden!r}"


def test_readings_only_allowed_fields():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)
    payload = build_payload(trial, "P-07", as_of, signals)
    assert payload["readings"], "expected some readings"
    for reading in payload["readings"]:
        assert set(reading.keys()) == set(ALLOWED_READING_FIELDS)


def test_as_of_semantics_for_late_sync_participant():
    trial = generate(7)
    as_of = _day_time(21, 8)
    signals = detect(trial, as_of)
    payload = build_payload(trial, "P-15", as_of, signals)

    as_of_iso = as_of.isoformat()
    for reading in payload["readings"]:
        assert reading["recorded_at"] <= as_of_iso

    # P-15's day-20 wearable readings are recorded two days later (day 22), so
    # none of the day-20 07:00 wearable rows may appear at day 21 08:00.
    day20_morning_iso = _day_time(20, 7).isoformat()
    assert not any(
        reading["event_time"] == day20_morning_iso for reading in payload["readings"]
    )

    # Pre-dose readings (trial days 1-7) do appear.
    predose_dates = {_day_time(d, 0).date().isoformat() for d in range(1, 8)}
    seen_predose = {
        reading["event_time"][:10]
        for reading in payload["readings"]
        if reading["event_time"][:10] in predose_dates
    }
    assert seen_predose, "expected pre-dose readings to be present"


def test_only_this_participants_signals_and_drift_present():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)
    payload = build_payload(trial, "P-07", as_of, signals)

    assert payload["signals"], "expected some signals for P-07"
    for sig in payload["signals"]:
        assert sig["participant_id"] == "P-07"

    types = {sig["type"] for sig in payload["signals"]}
    assert "drift" in types, "expected P-07 drift signals"


def test_scrub_text():
    out = scrub_text(
        "call 617-555-0199 or mail jane.doe@example.com, born 05/17/1990"
    )
    assert out == "call [phone] or mail [email], born [date]"


def test_unknown_participant_raises():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)
    try:
        build_payload(trial, "P-99", as_of, signals)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown participant_id")
