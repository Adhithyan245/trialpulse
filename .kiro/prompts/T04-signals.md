Task T04: personal baselines, calibrated bands and signal detection, with tests.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Read trialpulse/core/models.py and trialpulse/data/generator.py first. numpy + stdlib only.

Files you may create: trialpulse/signals/__init__.py, trialpulse/signals/baseline.py,
trialpulse/signals/detect.py, tests/test_signals.py. Do not touch any other file.

Core rule (temporal correctness): every function that takes `as_of` may only use readings
with recorded_at <= as_of. Never use a reading recorded later, even if its event_time is
earlier. Trial day of a reading = (event_time.date() - TRIAL_START.date()).days + 1.

baseline.py
  MONITORED = {"resting_hr": "up", "hrv_rmssd": "down", "skin_temp": "up",
               "respiratory_rate": "up"}   # direction that counts as a deviation
  ALPHA = 0.05
  personal_baseline(readings, participant_id, metric) -> (median, mad): from that
    participant's pre-dose days (trial days 1-7) only. mad = median absolute deviation,
    with a floor of 1e-6 relative to the median scale (avoid division by zero).
  conformal_q(trial, metric, alpha=ALPHA) -> float: split-conformal threshold on
    normalized scores pooled across ALL participants' pre-dose days:
    score = |x - median_p| / mad_p. With n scores, q = the ceil((n + 1) * (1 - alpha))-th
    smallest score (1-based; if that index exceeds n, return the largest score).
  personal_bands(trial) -> dict[participant_id][metric] = {"median", "lo", "hi", "q"}
    where lo = median - q * mad, hi = median + q * mad.
  Module docstring: explain in 3-4 lines that the band is a split-conformal 95% band on
  MAD-normalized scores, calibrated on pre-dose days, so a normal day falls inside it with
  probability >= 95% under exchangeability.

detect.py
  detect(trial, as_of: datetime) -> list[Signal]  (sorted by participant_id, type, metric)
  1. Drift (multi-signal rule): for each participant, look at trial days after day 7 whose
     readings are known as of as_of. A day "deviates" on a metric when the value is
     outside the band in that metric's direction (above hi for "up", below lo for
     "down"). Flag drift when, on 2 consecutive trial days, at least 2 of the 4 monitored
     metrics deviate on both days. For each metric that deviates on both of those days,
     emit one Signal(type="drift", metric=<metric>, window_start = start of the change
     estimated by a one-sided CUSUM on that metric's normalized scores over days 8..now
     (k = 0.5, h = 4.0; the change start is the day after the CUSUM was last at 0 before
     crossing h; if it never crosses, use the first of the two consecutive days),
     window_end = 07:00 on the last deviating day, z_score = signed normalized score of
     the latest known reading, record_ids = record_ids of the deviating readings in
     the window). signal_id = f"SIG-{participant_id}-drift-{metric}".
  2. Non-wear: over the 7 trial days ending at as_of's trial day, count days where the
     participant has no resting_hr reading known as of as_of, or wear_minutes < 600, or
     user_calibrating == 1. If >= 2 such days, emit Signal(type="non_wear",
     metric="wear_minutes", z_score=None, window over those 7 days, record_ids = the
     wear_minutes / user_calibrating readings of those days that exist).
     signal_id = f"SIG-{participant_id}-non_wear".
  3. Diary conflict: if the participant has fatigue >= 8 on >= 2 of the last 3 trial
     days (known as of as_of) and no drift signal, emit Signal(type="diary_conflict",
     metric="fatigue", z_score=None, record_ids = those fatigue readings plus any
     symptom_note in the window). signal_id = f"SIG-{participant_id}-diary_conflict".

tests/test_signals.py (use generate(7)):
 - conformal_q follows the formula on a hand-made tiny case (write a fake trial with a
   few readings, or test a helper that takes a list of scores; expose
   conformal_threshold(scores, alpha) in baseline.py for this).
 - at as_of = day 15 23:00: P-07 and P-20 each have >= 2 drift signals; no other
   participant has a drift signal.
 - at as_of = day 15 23:00: no drift signal exists for P-07 when as_of = day 11 23:00
   (before the change).
 - at as_of = day 28 23:00: at least 5 of the S03 participants have a non_wear signal;
   P-02 has a non_wear signal.
 - at as_of = day 16 23:00: P-31 has a diary_conflict signal and no drift signal.
 - temporal: at as_of = day 21 08:00, no signal for P-15 cites a record whose
   recorded_at is later than as_of (P-15's day-20 rows are recorded on day 22).
 - every signal's record_ids exist in the trial and were recorded at or before as_of.

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
