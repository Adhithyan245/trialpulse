Task T04-fix2: replace the CUSUM change-start estimate with a run-based rule.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/signals/detect.py and tests/test_signals.py (only if a
test asserts CUSUM internals). Nothing else. Do not change baseline.py.

Current result: 45 passed, 1 failed. test_drift_change_window_start_p07_p20_day15 fails:
SIG-P-07-drift-respiratory_rate window_start day=9 (expected 11-13). The reviewer
inspected P-07's direction-signed sigma-normalized respiratory_rate scores for days 8-15:
[3.0, 2.0, 1.7, -0.3, 5.0, 5.7, 4.3, 6.0]. With only 7 baseline days the sigma estimate is
small, so CUSUM accumulates pre-change noise. Do not change that test.

New rule for window_start of a drift signal: starting from the last deviating day and
walking backwards over trial days > 7 with a known reading, extend while the signed score
is > 1.0; window_start = 07:00 on the earliest day of that unbroken run (a day with no
known reading ends the run). Remove the CUSUM code and its k/h constants; update the
docstring to describe the run rule in one or two sentences. Everything else (deviation
test, 2-of-4 metrics on 2 consecutive days, z_score, record_ids) stays the same.

When finished, list the files you changed and stop.
