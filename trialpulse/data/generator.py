"""Seeded synthetic trial generator.

Produces a deterministic :class:`TrialData` bundle (participants, wearable and
diary readings, and a ground-truth description of the planted events). The same
seed always yields identical output because the only randomness comes from a
single ``numpy.random.default_rng(seed)``.

All participant data is synthetic.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import numpy as np
from pydantic import BaseModel

from trialpulse.core.models import Participant, Reading

TRIAL_START = datetime(2026, 9, 21)  # trial day 1; day d is TRIAL_START + (d-1) days
N_DAYS = 28
DOSE_START_DAY = 8  # days 1-7 are the pre-dose baseline

SITES: dict[str, tuple[str, str]] = {
    "S01": ("Boston", "Suffolk"),
    "S02": ("Worcester", "Worcester"),
    "S03": ("Springfield", "Hampden"),
}

_SITE_ORDER = ["S01", "S02", "S03"]
N_PARTICIPANTS = 40

# Physiological / activity metric metadata: kind and unit.
_METRIC_KIND: dict[str, str] = {
    "resting_hr": "physiological",
    "hrv_rmssd": "physiological",
    "spo2": "physiological",
    "skin_temp": "physiological",
    "respiratory_rate": "physiological",
    "sleep_hours": "sleep",
    "strain": "activity",
    "wear_minutes": "activity",
    "user_calibrating": "context",
}
_METRIC_UNIT: dict[str, str | None] = {
    "resting_hr": "bpm",
    "hrv_rmssd": "ms",
    "spo2": "%",
    "skin_temp": "C",
    "respiratory_rate": "rpm",
    "sleep_hours": "h",
    "strain": None,
    "wear_minutes": "min",
    "user_calibrating": None,
}

# Metrics emitted (in this order) on a normal worn day.
_WORN_METRICS = [
    "resting_hr",
    "hrv_rmssd",
    "spo2",
    "skin_temp",
    "respiratory_rate",
    "sleep_hours",
    "strain",
    "wear_minutes",
    "user_calibrating",
]


class TrialData(BaseModel):
    participants: list[Participant]
    readings: list[Reading]
    ground_truth: dict


def _day_time(day: int, hour: int, minute: int = 0) -> datetime:
    return TRIAL_START + timedelta(days=day - 1) + timedelta(hours=hour, minutes=minute)


def _pid(i: int) -> str:
    """i is 1-based participant number."""
    return f"P-{i:02d}"


def generate(seed: int = 7) -> TrialData:
    rng = np.random.default_rng(seed)

    # --- participants --------------------------------------------------
    participants: list[Participant] = []
    site_of: dict[str, str] = {}
    arm_of: dict[str, str] = {}
    for i in range(1, N_PARTICIPANTS + 1):
        pid = _pid(i)
        site_id = _SITE_ORDER[(i - 1) % 3]
        arm = "A" if (i - 1) % 2 == 0 else "B"
        _, county = SITES[site_id]
        participants.append(
            Participant(
                participant_id=pid,
                site_id=site_id,
                arm=arm,
                enrolled_at=TRIAL_START,
                dose_start_day=DOSE_START_DAY,
                home_county=county,
            )
        )
        site_of[pid] = site_id
        arm_of[pid] = arm

    # --- per-participant baselines (drawn in participant order) --------
    base: dict[str, dict[str, float]] = {}
    fatigue_base: dict[str, int] = {}
    for i in range(1, N_PARTICIPANTS + 1):
        pid = _pid(i)
        base[pid] = {
            "resting_hr": float(rng.normal(60, 6)),
            "hrv_rmssd": float(55.0 * rng.lognormal(0.0, 0.3)),
            "spo2": float(rng.uniform(96.5, 98.5)),
            "skin_temp": float(rng.uniform(33.5, 34.5)),
            "respiratory_rate": float(rng.uniform(13, 16)),
            "sleep_hours": float(rng.uniform(6.5, 8.0)),
            "strain": float(rng.uniform(6, 16)),
        }
        fatigue_base[pid] = int(rng.integers(2, 5))  # 2..4 inclusive

    # --- planted-event bookkeeping -------------------------------------
    adverse_pids = ["P-07", "P-20"]
    late_sync_pid = "P-15"
    diary_conflict_pid = "P-31"
    sparse_pid = "P-02"
    non_wear_site = "S03"

    non_wear_days: list[tuple[str, int]] = []

    readings: list[Reading] = []

    def add(
        pid: str,
        day: int,
        name: str,
        value: float | str,
        event_time: datetime,
        recorded_at: datetime,
        source: str,
        kind: str,
        unit: str | None,
    ) -> None:
        readings.append(
            Reading(
                record_id=f"{pid}-d{day:02d}-{name}",
                kind=kind,
                name=name,
                value=value,
                unit=unit,
                event_time=event_time,
                recorded_at=recorded_at,
                source=source,
                participant_id=pid,
                site_id=site_of[pid],
            )
        )

    # --- daily loop ----------------------------------------------------
    for i in range(1, N_PARTICIPANTS + 1):
        pid = _pid(i)
        b = base[pid]
        for day in range(1, N_DAYS + 1):
            event_time = _day_time(day, 7)
            # recorded_at = event_time + 1..6 whole hours (normal case)
            delay_hours = int(rng.integers(1, 7))  # 1..6
            recorded_at = event_time + timedelta(hours=delay_hours)

            # P-15 late_sync: days 20, 21 recorded_at = event_time + 2 days
            if pid == late_sync_pid and day in (20, 21):
                recorded_at = event_time + timedelta(days=2)

            # ---- site non-wear (S03, days 9..28) ----
            is_non_wear = False
            if site_of[pid] == non_wear_site and 9 <= day <= N_DAYS:
                if rng.random() < 0.30:
                    is_non_wear = True

            # ---- P-02 sparse week (days 22..28) ----
            sparse_mode = None
            if pid == sparse_pid and 22 <= day <= N_DAYS:
                if day in (24, 27):
                    sparse_mode = "normal"
                elif day in (22, 23):
                    sparse_mode = "calibrating_only"
                else:  # 25, 26, 28
                    sparse_mode = "nothing"

            # ---- adverse pattern modifiers (P-07, P-23, days 12..28) ----
            rhr_mod = 0.0
            hrv_mult = 1.0
            temp_mod = 0.0
            rr_mod = 0.0
            if pid in adverse_pids and 12 <= day <= N_DAYS:
                rhr_mod = 8.0
                hrv_mult = 0.75
                temp_mod = 0.6
                rr_mod = 1.5

            # ---- draw daily noise for every participant/day (keeps RNG
            #      stream deterministic regardless of which rows are emitted) ----
            n_rhr = float(rng.normal(0, 2))
            n_hrv = float(rng.normal(0, 0.08))  # 8% sd (relative)
            n_spo2 = float(rng.normal(0, 0.4))
            n_temp = float(rng.normal(0, 0.15))
            n_rr = float(rng.normal(0, 0.4))
            n_sleep = float(rng.normal(0, 0.5))
            n_strain = float(rng.normal(0, 2.0))
            wear_val = int(rng.integers(1250, 1441))  # 1250..1440
            nonwear_val = int(rng.integers(0, 501))  # 0..500
            fatigue_noise = int(rng.integers(-1, 2))  # -1,0,1

            # Decide which wearable rows to emit.
            if sparse_mode == "nothing":
                emit_wearable = False
                emit_calibrating_only = False
                calibrating_value = 0
            elif sparse_mode == "calibrating_only":
                emit_wearable = False
                emit_calibrating_only = True
                calibrating_value = 1
            elif is_non_wear:
                # emit only wear_minutes with value 0..500
                non_wear_days.append((pid, day))
                add(
                    pid, day, "wear_minutes", nonwear_val, event_time, recorded_at,
                    "wearable", _METRIC_KIND["wear_minutes"], _METRIC_UNIT["wear_minutes"],
                )
                emit_wearable = False
                emit_calibrating_only = False
                calibrating_value = 0
            else:
                emit_wearable = True
                emit_calibrating_only = False
                calibrating_value = 0

            if emit_calibrating_only:
                add(
                    pid, day, "user_calibrating", 1.0, event_time, recorded_at,
                    "wearable", _METRIC_KIND["user_calibrating"],
                    _METRIC_UNIT["user_calibrating"],
                )

            if emit_wearable:
                resting_hr = round(b["resting_hr"] + n_rhr + rhr_mod, 1)
                hrv = round(b["hrv_rmssd"] * hrv_mult * (1.0 + n_hrv), 1)
                spo2 = round(min(b["spo2"] + n_spo2, 100.0), 1)
                skin_temp = round(b["skin_temp"] + n_temp + temp_mod, 1)
                resp = round(b["respiratory_rate"] + n_rr + rr_mod, 1)
                sleep = round(b["sleep_hours"] + n_sleep, 1)
                strain = round(min(max(b["strain"] + n_strain, 0.0), 21.0), 1)

                values: dict[str, float] = {
                    "resting_hr": resting_hr,
                    "hrv_rmssd": hrv,
                    "spo2": spo2,
                    "skin_temp": skin_temp,
                    "respiratory_rate": resp,
                    "sleep_hours": sleep,
                    "strain": strain,
                    "wear_minutes": float(wear_val),
                    "user_calibrating": 0.0,
                }
                for name in _WORN_METRICS:
                    add(
                        pid, day, name, values[name], event_time, recorded_at,
                        "wearable", _METRIC_KIND[name], _METRIC_UNIT[name],
                    )

            # ---- diary (every participant every day; unaffected by non-wear) ----
            diary_time = _day_time(day, 20)
            fatigue = fatigue_base[pid] + fatigue_noise
            # event overrides
            if pid in adverse_pids and 12 <= day <= 15:
                fatigue = int(rng.integers(7, 9))  # 7..8
            if pid == diary_conflict_pid and 14 <= day <= 16:
                fatigue = 9
            fatigue = int(min(max(fatigue, 0), 10))
            add(
                pid, day, "fatigue", fatigue, diary_time, diary_time,
                "self_report", "subjective", None,
            )

            # P-31 symptom_note on day 15
            if pid == diary_conflict_pid and day == 15:
                readings.append(
                    Reading(
                        record_id="P-31-d15-symptom_note",
                        kind="subjective",
                        name="symptom_note",
                        value="completely exhausted",
                        unit=None,
                        event_time=diary_time,
                        recorded_at=diary_time,
                        source="self_report",
                        participant_id=pid,
                        site_id=site_of[pid],
                    )
                )

    # --- ground truth --------------------------------------------------
    ground_truth: dict = {
        "seed": seed,
        "events": [
            {
                "type": "adverse_pattern",
                "participant_ids": ["P-07", "P-20"],
                "start_day": 12,
                "end_day": 28,
                "detail": (
                    "resting_hr +8, hrv_rmssd x0.75, skin_temp +0.6, "
                    "respiratory_rate +1.5; fatigue 7-8 on days 12-15"
                ),
            },
            {
                "type": "site_non_wear",
                "site_id": "S03",
                "start_day": 9,
                "end_day": 28,
                "detail": "each S03 participant-day not worn with probability 0.30",
            },
            {
                "type": "late_sync",
                "participant_ids": ["P-15"],
                "start_day": 20,
                "end_day": 21,
                "detail": "recorded_at = event_time + 2 days on days 20 and 21",
            },
            {
                "type": "diary_conflict",
                "participant_ids": ["P-31"],
                "start_day": 14,
                "end_day": 16,
                "detail": (
                    "fatigue 9 on days 14-16 plus a symptom_note "
                    "'completely exhausted' on day 15; wearable normal"
                ),
            },
            {
                "type": "sparse_week",
                "participant_ids": ["P-02"],
                "start_day": 22,
                "end_day": 28,
                "detail": (
                    "days 24 and 27 normal; days 22 and 23 user_calibrating=1 only; "
                    "days 25, 26, 28 emit nothing"
                ),
            },
        ],
        "non_wear_days": [[pid, day] for (pid, day) in non_wear_days],
    }

    return TrialData(
        participants=participants,
        readings=readings,
        ground_truth=ground_truth,
    )


def write_json(data: TrialData, path: str = "data/synthetic/trial.json") -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(data.model_dump_json(indent=1))
