"""Tests for the seeded synthetic trial generator."""

from __future__ import annotations

from datetime import timedelta

from trialpulse.core.models import Reading
from trialpulse.data.generator import (
    DOSE_START_DAY,
    N_DAYS,
    N_PARTICIPANTS,
    SITES,
    TRIAL_START,
    TrialData,
    generate,
    write_json,
)

SITE_ORDER = ["S01", "S02", "S03"]


# --- helpers --------------------------------------------------------------


def _readings_by_pid(data: TrialData) -> dict[str, list[Reading]]:
    out: dict[str, list[Reading]] = {}
    for r in data.readings:
        out.setdefault(r.participant_id, []).append(r)
    return out


def _day_of(r: Reading) -> int:
    """Recover the trial day (1-based) from a reading's record_id suffix dNN."""
    # record_id looks like 'P-07-d12-resting_hr'
    token = r.record_id.split("-d", 1)[1]
    return int(token[:2])


def _rhr_by_day(readings: list[Reading]) -> dict[int, float]:
    vals: dict[int, float] = {}
    for r in readings:
        if r.name == "resting_hr":
            vals[_day_of(r)] = float(r.value)
    return vals


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


# --- determinism ----------------------------------------------------------


def test_same_seed_identical():
    a = generate(7).model_dump_json()
    b = generate(7).model_dump_json()
    assert a == b


def test_different_seed_differs():
    assert generate(7).model_dump_json() != generate(8).model_dump_json()


# --- participants ---------------------------------------------------------


def test_forty_participants_sites_and_arms():
    data = generate(7)
    ps = data.participants
    assert len(ps) == N_PARTICIPANTS == 40
    for idx, p in enumerate(ps, start=1):
        assert p.participant_id == f"P-{idx:02d}"
        expected_site = SITE_ORDER[(idx - 1) % 3]
        assert p.site_id == expected_site
        assert p.arm == ("A" if (idx - 1) % 2 == 0 else "B")
        assert p.home_county == SITES[expected_site][1]
        assert p.enrolled_at == TRIAL_START
        assert p.dose_start_day == DOSE_START_DAY

    # The two adverse participants are not on the non-wear site S03.
    by_id = {p.participant_id: p for p in ps}
    assert by_id["P-07"].site_id == "S01"
    assert by_id["P-07"].arm == "A"
    assert by_id["P-20"].site_id == "S02"
    assert by_id["P-20"].arm == "B"


# --- record integrity -----------------------------------------------------


def test_record_ids_unique_and_readings_valid():
    data = generate(7)
    ids = [r.record_id for r in data.readings]
    assert len(ids) == len(set(ids))
    # Every reading is a validated Reading instance.
    for r in data.readings:
        assert isinstance(r, Reading)
        Reading.model_validate(r.model_dump())


# --- adverse pattern ------------------------------------------------------


def test_adverse_participants_rhr_rise():
    data = generate(7)
    by_pid = _readings_by_pid(data)
    for pid in ("P-07", "P-20"):
        rhr = _rhr_by_day(by_pid[pid])
        baseline_days = [rhr[d] for d in range(1, 8) if d in rhr]
        window_days = [rhr[d] for d in range(12, 16) if d in rhr]
        assert baseline_days and window_days
        assert _mean(window_days) > _mean(baseline_days) + 6


def test_no_other_participant_has_elevated_window():
    data = generate(7)
    by_pid = _readings_by_pid(data)
    for pid, readings in by_pid.items():
        if pid in ("P-07", "P-20"):
            continue
        rhr = _rhr_by_day(readings)
        base_days = [rhr[d] for d in range(1, 8) if d in rhr]
        if not base_days:
            continue
        base_mean = _mean(base_days)
        for start in range(1, N_DAYS - 2):  # every 4-day window [start, start+3]
            win = [rhr[d] for d in range(start, start + 4) if d in rhr]
            if len(win) < 3:
                continue
            assert _mean(win) <= base_mean + 6, (pid, start, _mean(win), base_mean)


# --- site non-wear --------------------------------------------------------


def test_non_wear_days_consistent():
    data = generate(7)
    non_wear = data.ground_truth["non_wear_days"]
    # Build a quick index of readings per (pid, day).
    by_key: dict[tuple[str, int], list[Reading]] = {}
    for r in data.readings:
        by_key.setdefault((r.participant_id, _day_of(r)), []).append(r)

    for pid, day in non_wear:
        key = (pid, int(day))
        names = {r.name: r for r in by_key.get(key, [])}
        assert "wear_minutes" in names
        assert float(names["wear_minutes"].value) < 600
        assert "resting_hr" not in names
    # S03 has at least 25 not-worn days.
    s03_pids = {p.participant_id for p in data.participants if p.site_id == "S03"}
    s03_count = sum(1 for pid, _day in non_wear if pid in s03_pids)
    assert s03_count >= 25


# --- late sync ------------------------------------------------------------


def test_late_sync_offset():
    data = generate(7)
    by_pid = _readings_by_pid(data)
    for day in (20, 21):
        rows = [r for r in by_pid["P-15"] if _day_of(r) == day and r.source == "wearable"]
        assert rows
        for r in rows:
            assert r.recorded_at - r.event_time == timedelta(days=2)


# --- diary conflict -------------------------------------------------------


def test_diary_conflict():
    data = generate(7)
    by_pid = _readings_by_pid(data)
    rows = by_pid["P-31"]
    symptom = [r for r in rows if r.name == "symptom_note" and _day_of(r) == 15]
    assert len(symptom) == 1
    assert symptom[0].value == "completely exhausted"
    for day in (14, 15, 16):
        fat = [r for r in rows if r.name == "fatigue" and _day_of(r) == day]
        assert len(fat) == 1
        assert float(fat[0].value) == 9


# --- sparse week ----------------------------------------------------------


def test_sparse_week():
    data = generate(7)
    by_pid = _readings_by_pid(data)
    rhr_days = {
        _day_of(r)
        for r in by_pid["P-02"]
        if r.name == "resting_hr" and 22 <= _day_of(r) <= 28
    }
    assert rhr_days == {24, 27}


# --- write_json round-trip ------------------------------------------------


def test_write_json_roundtrip(tmp_path):
    data = generate(7)
    path = tmp_path / "trial.json"
    write_json(data, str(path))
    assert path.exists()
    restored = TrialData.model_validate_json(path.read_text(encoding="utf-8"))
    assert restored.model_dump_json() == data.model_dump_json()
