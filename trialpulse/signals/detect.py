"""Signal detection over a trial, temporally correct as of a given instant.

Every function respects as-of semantics: only readings with recorded_at <= as_of
are visible. Drift uses the personal conformal bands from :mod:`baseline`; non-wear
and diary conflict are counting rules over recent trial days.
"""

from __future__ import annotations

from datetime import datetime

from trialpulse.core.models import Reading, Signal
from trialpulse.data.generator import TRIAL_START, _day_time
from trialpulse.signals.baseline import MONITORED, personal_baseline, personal_bands, trial_day

DOSE_START_DAY = 8  # drift is only assessed on trial days after day 7


def _known(readings: list[Reading], as_of: datetime) -> list[Reading]:
    """Readings the system could know at as_of (recorded_at <= as_of)."""
    return [r for r in readings if r.recorded_at <= as_of]


def _signed_score(value: float, median: float, sigma: float, direction: str) -> float:
    """Signed normalized score; positive means deviation in the monitored direction."""
    if direction == "up":
        return (value - median) / sigma
    return (median - value) / sigma


def _deviates(value: float, band: dict[str, float], direction: str) -> bool:
    if direction == "up":
        return value > band["hi"]
    return value < band["lo"]


def _day_metric_values(
    readings: list[Reading], participant_id: str
) -> dict[int, dict[str, Reading]]:
    """Map trial_day -> metric name -> the Reading (numeric, monitored metric)."""
    out: dict[int, dict[str, Reading]] = {}
    for r in readings:
        if r.participant_id != participant_id or r.name not in MONITORED:
            continue
        if not isinstance(r.value, (int, float)):
            continue
        out.setdefault(trial_day(r.event_time), {})[r.name] = r
    return out


def _run_start_day(
    scores_by_day: dict[int, float], last_deviating_day: int
) -> int:
    """Earliest day of the unbroken run ending at ``last_deviating_day``.

    Walk backwards over trial days > 7 that have a known reading, extending the
    run while the signed score is > 1.0. A day with no known reading ends the run.
    """
    start = last_deviating_day
    d = last_deviating_day - 1
    while d > 7 and d in scores_by_day and scores_by_day[d] > 1.0:
        start = d
        d -= 1
    return start


def _detect_drift(
    readings: list[Reading],
    participant_id: str,
    as_of: datetime,
    bands: dict[str, dict[str, float]],
    sigmas: dict[str, float],
) -> list[Signal]:
    day_metrics = _day_metric_values(readings, participant_id)
    as_of_day = (as_of.date() - TRIAL_START.date()).days + 1
    post_days = sorted(d for d in day_metrics if d > 7 and d <= as_of_day)

    # Per-day deviation flags for each monitored metric.
    deviates_on: dict[int, set[str]] = {}
    for d in post_days:
        flags: set[str] = set()
        for metric, direction in MONITORED.items():
            rec = day_metrics[d].get(metric)
            if rec is None:
                continue
            if _deviates(float(rec.value), bands[metric], direction):
                flags.add(metric)
        deviates_on[d] = flags

    # Find 2 consecutive trial days where >=2 of the 4 metrics deviate on both days.
    chosen: tuple[int, int] | None = None
    for d1, d2 in zip(post_days, post_days[1:]):
        if d2 != d1 + 1:
            continue
        both = deviates_on[d1] & deviates_on[d2]
        if len(both) >= 2:
            chosen = (d1, d2)  # keep scanning to prefer the latest pair
    if chosen is None:
        return []

    d1, d2 = chosen
    both = deviates_on[d1] & deviates_on[d2]

    signals: list[Signal] = []
    for metric in sorted(both):
        direction = MONITORED[metric]
        median = bands[metric]["median"]
        sigma = sigmas[metric]

        # Signed normalized scores over trial days > 7 up to as_of_day.
        scores_by_day: dict[int, float] = {}
        for d in sorted(x for x in day_metrics if 7 < x <= as_of_day):
            rec = day_metrics[d].get(metric)
            if rec is None:
                continue
            scores_by_day[d] = _signed_score(float(rec.value), median, sigma, direction)

        # Last deviating day in the chosen pair's window (>7, <= d2).
        last_deviating_day = d2
        for d in sorted(x for x in day_metrics if 7 < x <= d2):
            rec = day_metrics[d].get(metric)
            if rec is None:
                continue
            if _deviates(float(rec.value), bands[metric], direction):
                last_deviating_day = d

        window_start_day = _run_start_day(scores_by_day, last_deviating_day)

        window_start = _day_time(window_start_day, 7)
        window_end = _day_time(d2, 7)

        # record_ids of the deviating readings in the window [window_start_day, d2].
        record_ids: list[str] = []
        for d in sorted(x for x in day_metrics if window_start_day <= x <= d2):
            rec = day_metrics[d].get(metric)
            if rec is None:
                continue
            if _deviates(float(rec.value), bands[metric], direction):
                record_ids.append(rec.record_id)

        # z_score = signed normalized score of the latest known reading of this metric.
        latest_rec: Reading | None = None
        for d in sorted(x for x in day_metrics if x <= as_of_day):
            rec = day_metrics[d].get(metric)
            if rec is not None:
                latest_rec = rec
        z = (
            _signed_score(float(latest_rec.value), median, sigma, direction)
            if latest_rec is not None
            else 0.0
        )

        signals.append(
            Signal(
                signal_id=f"SIG-{participant_id}-drift-{metric}",
                participant_id=participant_id,
                type="drift",
                metric=metric,
                window_start=window_start,
                window_end=window_end,
                z_score=z,
                record_ids=record_ids,
            )
        )
    return signals


def _detect_non_wear(
    readings: list[Reading], participant_id: str, as_of: datetime
) -> list[Signal]:
    as_of_day = (as_of.date() - TRIAL_START.date()).days + 1
    window_days = [d for d in range(as_of_day - 6, as_of_day + 1) if d >= 1]
    if not window_days:
        return []

    # Index this participant's known readings by (trial_day, metric).
    by_day: dict[int, dict[str, Reading]] = {}
    for r in readings:
        if r.participant_id != participant_id:
            continue
        by_day.setdefault(trial_day(r.event_time), {})[r.name] = r

    bad_days: list[int] = []
    record_ids: list[str] = []
    for d in window_days:
        day = by_day.get(d, {})
        rhr = day.get("resting_hr")
        wear = day.get("wear_minutes")
        calib = day.get("user_calibrating")

        is_bad = False
        if rhr is None:
            is_bad = True
        if wear is not None and isinstance(wear.value, (int, float)) and float(wear.value) < 600:
            is_bad = True
        if calib is not None and isinstance(calib.value, (int, float)) and int(calib.value) == 1:
            is_bad = True

        if is_bad:
            bad_days.append(d)
            if wear is not None:
                record_ids.append(wear.record_id)
            if calib is not None and isinstance(calib.value, (int, float)) and int(calib.value) == 1:
                record_ids.append(calib.record_id)

    if len(bad_days) < 2:
        return []

    window_start = _day_time(window_days[0], 7)
    window_end = _day_time(window_days[-1], 7)
    return [
        Signal(
            signal_id=f"SIG-{participant_id}-non_wear",
            participant_id=participant_id,
            type="non_wear",
            metric="wear_minutes",
            window_start=window_start,
            window_end=window_end,
            z_score=None,
            record_ids=record_ids,
        )
    ]


def _detect_diary_conflict(
    readings: list[Reading], participant_id: str, as_of: datetime, has_drift: bool
) -> list[Signal]:
    if has_drift:
        return []
    as_of_day = (as_of.date() - TRIAL_START.date()).days + 1
    last3 = [d for d in range(as_of_day - 2, as_of_day + 1) if d >= 1]
    if not last3:
        return []

    fatigue_by_day: dict[int, Reading] = {}
    note_by_day: dict[int, Reading] = {}
    for r in readings:
        if r.participant_id != participant_id:
            continue
        d = trial_day(r.event_time)
        if d not in last3:
            continue
        if r.name == "fatigue" and isinstance(r.value, (int, float)):
            fatigue_by_day[d] = r
        elif r.name == "symptom_note":
            note_by_day[d] = r

    high_days = [d for d in last3 if d in fatigue_by_day and float(fatigue_by_day[d].value) >= 8]
    if len(high_days) < 2:
        return []

    record_ids = [fatigue_by_day[d].record_id for d in sorted(high_days)]
    record_ids += [note_by_day[d].record_id for d in sorted(note_by_day)]

    window_start = _day_time(last3[0], 20)
    window_end = _day_time(last3[-1], 20)
    return [
        Signal(
            signal_id=f"SIG-{participant_id}-diary_conflict",
            participant_id=participant_id,
            type="diary_conflict",
            metric="fatigue",
            window_start=window_start,
            window_end=window_end,
            z_score=None,
            record_ids=record_ids,
        )
    ]


def detect(trial, as_of: datetime) -> list[Signal]:
    """Detect drift, non-wear and diary-conflict signals as of ``as_of``.

    Sorted by (participant_id, type, metric).
    """
    bands = personal_bands(trial)
    known = _known(list(trial.readings), as_of)
    known_by_pid: dict[str, list[Reading]] = {}
    for r in known:
        known_by_pid.setdefault(r.participant_id, []).append(r)

    signals: list[Signal] = []
    for p in trial.participants:
        pid = p.participant_id
        rs = known_by_pid.get(pid, [])
        sigmas = {
            metric: personal_baseline(trial, pid, metric)[1] for metric in MONITORED
        }
        drift = _detect_drift(rs, pid, as_of, bands[pid], sigmas)
        non_wear = _detect_non_wear(rs, pid, as_of)
        diary = _detect_diary_conflict(rs, pid, as_of, has_drift=bool(drift))
        signals.extend(drift)
        signals.extend(non_wear)
        signals.extend(diary)

    signals.sort(key=lambda s: (s.participant_id, s.type, s.metric))
    return signals
