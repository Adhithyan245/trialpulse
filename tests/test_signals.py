"""Tests for personal baselines, conformal bands and signal detection."""

from __future__ import annotations

from trialpulse.data.generator import _day_time, generate
from trialpulse.signals.baseline import (
    ALPHA,
    MONITORED,
    conformal_q,
    conformal_threshold,
    personal_bands,
)
from trialpulse.signals.detect import detect


# --- helpers --------------------------------------------------------------


def _record_index(trial) -> dict[str, object]:
    return {r.record_id: r for r in trial.readings}


def _signals_for(signals, participant_id, type_=None):
    out = [s for s in signals if s.participant_id == participant_id]
    if type_ is not None:
        out = [s for s in out if s.type == type_]
    return out


# --- conformal_threshold formula -----------------------------------------


def test_conformal_threshold_formula_tiny_case():
    # n = 5 scores. With alpha = 0.05: k = ceil(6 * 0.95) = ceil(5.7) = 6 > 5
    # so the result is the largest score.
    scores = [0.2, 1.0, 0.5, 3.0, 0.1]
    assert conformal_threshold(scores, 0.05) == 3.0

    # n = 9, alpha = 0.1: k = ceil(10 * 0.9) = 9 -> 9th smallest (the max here).
    scores2 = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    assert conformal_threshold(scores2, 0.1) == 0.8

    # n = 19, alpha = 0.05: k = ceil(20 * 0.95) = 19 -> 19th smallest (max).
    scores3 = [float(i) for i in range(19)]
    assert conformal_threshold(scores3, 0.05) == 18.0

    # n = 99, alpha = 0.05: k = ceil(100 * 0.95) = 95 -> 95th smallest (index 94).
    scores4 = [float(i) for i in range(99)]
    assert conformal_threshold(scores4, 0.05) == 94.0

    # empty -> 0.0
    assert conformal_threshold([], 0.05) == 0.0


def test_conformal_q_matches_threshold_on_pooled_scores():
    trial = generate(7)
    from trialpulse.signals.baseline import personal_baseline, PREDOSE_DAYS, trial_day

    metric = "resting_hr"
    scores = []
    for p in trial.participants:
        pid = p.participant_id
        median_p, mad_p = personal_baseline(trial, pid, metric)
        for r in trial.readings:
            if r.participant_id != pid or r.name != metric:
                continue
            if trial_day(r.event_time) in PREDOSE_DAYS:
                scores.append(abs(float(r.value) - median_p) / mad_p)
    expected = conformal_threshold(scores, ALPHA)
    assert conformal_q(trial, metric) == expected


def test_personal_bands_shape():
    trial = generate(7)
    bands = personal_bands(trial)
    for p in trial.participants:
        b = bands[p.participant_id]
        for metric in MONITORED:
            cell = b[metric]
            assert set(cell) == {"median", "lo", "hi", "q"}
            assert cell["lo"] <= cell["median"] <= cell["hi"]


# --- drift ----------------------------------------------------------------


def test_drift_p07_p20_have_signals_day15():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    for pid in ("P-07", "P-20"):
        drifts = _signals_for(signals, pid, "drift")
        assert len(drifts) >= 2, f"{pid} expected >=2 drift signals, got {len(drifts)}"

    # No other participant has a drift signal.
    drift_pids = {s.participant_id for s in signals if s.type == "drift"}
    assert drift_pids == {"P-07", "P-20"}, drift_pids


def test_drift_p07_absent_before_change_day11():
    trial = generate(7)
    as_of = _day_time(11, 23)
    signals = detect(trial, as_of)
    assert _signals_for(signals, "P-07", "drift") == []


# --- non-wear -------------------------------------------------------------


def test_non_wear_s03_and_p02_day28():
    trial = generate(7)
    as_of = _day_time(28, 23)
    signals = detect(trial, as_of)

    s03_pids = {p.participant_id for p in trial.participants if p.site_id == "S03"}
    nonwear_pids = {s.participant_id for s in signals if s.type == "non_wear"}
    assert len(s03_pids & nonwear_pids) >= 5

    assert "P-02" in nonwear_pids


# --- diary conflict -------------------------------------------------------


def test_diary_conflict_p31_day16():
    trial = generate(7)
    as_of = _day_time(16, 23)
    signals = detect(trial, as_of)

    diary = _signals_for(signals, "P-31", "diary_conflict")
    assert len(diary) == 1
    assert _signals_for(signals, "P-31", "drift") == []


# --- temporal correctness -------------------------------------------------


def test_temporal_p15_no_future_records_day21():
    trial = generate(7)
    as_of = _day_time(21, 8)
    signals = detect(trial, as_of)
    index = _record_index(trial)

    for s in _signals_for(signals, "P-15"):
        for rid in s.record_ids:
            rec = index[rid]
            assert rec.recorded_at <= as_of


def test_every_signal_cites_known_existing_records():
    trial = generate(7)
    index = _record_index(trial)
    for as_of in (_day_time(15, 23), _day_time(16, 23), _day_time(28, 23)):
        signals = detect(trial, as_of)
        for s in signals:
            for rid in s.record_ids:
                assert rid in index, f"{rid} not in trial"
                assert index[rid].recorded_at <= as_of



# --- numerical stability (T04-fix) ----------------------------------------


def test_conformal_q_bounded_and_drift_z_scores_sane():
    trial = generate(7)

    # Sigma-scaling keeps the pooled conformal quantile in a sane range for
    # every monitored metric (no MAD=0 blow-ups like conformal_q=2906.98).
    for metric in MONITORED:
        q = conformal_q(trial, metric)
        assert 1.5 < q < 6.0, f"{metric} conformal_q={q} out of range"

    # Across the dosing window, every drift signal's normalized z_score stays
    # well-bounded (previously skin_temp z_score hit 17441.86).
    for day in range(8, 29):
        signals = detect(trial, _day_time(day, 23))
        for s in signals:
            if s.type == "drift":
                assert abs(s.z_score) < 50, f"{s.signal_id} z_score={s.z_score}"


def test_drift_change_window_start_p07_p20_day15():
    from trialpulse.signals.baseline import trial_day

    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)

    for pid in ("P-07", "P-20"):
        drifts = _signals_for(signals, pid, "drift")
        assert drifts, f"{pid} expected drift signals"
        for s in drifts:
            start_day = trial_day(s.window_start)
            assert 11 <= start_day <= 13, f"{s.signal_id} window_start day={start_day}"
