"""Personal baselines and split-conformal bands for wearable metrics.

A participant's band for a metric is a split-conformal 95% interval around their
own pre-dose median, measured on sigma-normalized scores score = |x - median_p| / sigma_p,
where sigma_p = 1.4826 * MAD is a robust standard-deviation estimate floored at a
physiologically meaningful minimum per metric. The conformal quantile q is calibrated
by pooling those scores across all participants' pre-dose days, so under exchangeability
a normal (pre-dose-like) day falls inside the band median +/- q*sigma with probability
>= 95%. Only pre-dose days (trial days 1-7) are used, so the calibration is untouched by
on-drug drift.
"""

from __future__ import annotations

import math

import numpy as np

from trialpulse.data.generator import TRIAL_START, TrialData

# Direction that counts as a deviation for each monitored metric.
MONITORED: dict[str, str] = {
    "resting_hr": "up",
    "hrv_rmssd": "down",
    "skin_temp": "up",
    "respiratory_rate": "up",
}

ALPHA = 0.05

PREDOSE_DAYS = range(1, 8)  # trial days 1..7

# MAD -> sigma scale factor for a Gaussian, and a per-metric minimum sigma to
# keep normalized scores well-behaved when the pre-dose values are nearly
# constant (e.g. skin_temp rounded to 0.1 C giving MAD = 0).
_MAD_TO_SIGMA = 1.4826
MIN_SIGMA: dict[str, float] = {
    "resting_hr": 1.0,
    "hrv_rmssd": 2.0,
    "skin_temp": 0.1,
    "respiratory_rate": 0.3,
}


def trial_day(event_time) -> int:
    """Trial day (1-based) of a reading's event_time."""
    return (event_time.date() - TRIAL_START.date()).days + 1


def _predose_values(trial: TrialData, participant_id: str, metric: str) -> list[float]:
    vals: list[float] = []
    for r in trial.readings:
        if r.participant_id != participant_id or r.name != metric:
            continue
        if not isinstance(r.value, (int, float)):
            continue
        if trial_day(r.event_time) in PREDOSE_DAYS:
            vals.append(float(r.value))
    return vals


def personal_baseline(
    readings, participant_id: str, metric: str
) -> tuple[float, float]:
    """Return (median, sigma) from this participant's pre-dose days (1-7) only.

    ``readings`` may be a TrialData or any iterable of Reading. sigma is a robust
    standard-deviation estimate, sigma = 1.4826 * MAD about the median, floored at
    MIN_SIGMA[metric] (defaulting to a small positive value for unknown metrics) so
    division by near-zero spread cannot blow up normalized scores.
    """
    seq = readings.readings if isinstance(readings, TrialData) else readings
    vals: list[float] = []
    for r in seq:
        if r.participant_id != participant_id or r.name != metric:
            continue
        if not isinstance(r.value, (int, float)):
            continue
        if trial_day(r.event_time) in PREDOSE_DAYS:
            vals.append(float(r.value))

    arr = np.asarray(vals, dtype=float)
    median = float(np.median(arr)) if arr.size else 0.0
    mad = float(np.median(np.abs(arr - median))) if arr.size else 0.0
    sigma = _MAD_TO_SIGMA * mad
    floor = MIN_SIGMA.get(metric, 1e-6)
    if sigma < floor:
        sigma = floor
    return median, sigma


def conformal_threshold(scores, alpha: float = ALPHA) -> float:
    """Split-conformal quantile of a list of nonnegative scores.

    With n scores, return the ceil((n + 1) * (1 - alpha))-th smallest score
    (1-based). If that index exceeds n, return the largest score.
    """
    s = sorted(float(x) for x in scores)
    n = len(s)
    if n == 0:
        return 0.0
    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        k = n
    return s[k - 1]


def conformal_q(trial: TrialData, metric: str, alpha: float = ALPHA) -> float:
    """Pooled split-conformal threshold on normalized scores for ``metric``.

    score = |x - median_p| / sigma_p for each pre-dose reading of each participant p.
    """
    participant_ids = [p.participant_id for p in trial.participants]
    baselines: dict[str, tuple[float, float]] = {
        pid: personal_baseline(trial, pid, metric) for pid in participant_ids
    }
    scores: list[float] = []
    for pid in participant_ids:
        median_p, sigma_p = baselines[pid]
        for x in _predose_values(trial, pid, metric):
            scores.append(abs(x - median_p) / sigma_p)
    return conformal_threshold(scores, alpha)


def personal_bands(trial: TrialData) -> dict[str, dict[str, dict[str, float]]]:
    """bands[participant_id][metric] = {median, lo, hi, q} for each monitored metric."""
    q_by_metric: dict[str, float] = {
        metric: conformal_q(trial, metric) for metric in MONITORED
    }
    out: dict[str, dict[str, dict[str, float]]] = {}
    for p in trial.participants:
        pid = p.participant_id
        out[pid] = {}
        for metric in MONITORED:
            median, sigma = personal_baseline(trial, pid, metric)
            q = q_by_metric[metric]
            out[pid][metric] = {
                "median": median,
                "lo": median - q * sigma,
                "hi": median + q * sigma,
                "q": q,
            }
    return out
