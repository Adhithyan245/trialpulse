Task T04-fix: two numerical bugs found in review.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/signals/baseline.py, trialpulse/signals/detect.py,
tests/test_signals.py. Nothing else. Keep all existing tests passing and keep their intent.

Bug 1: skin_temp is rounded to 0.1 C, so many participants have identical pre-dose values
and MAD = 0. The relative 1e-6 floor then makes normalized scores explode (reviewer saw
conformal_q("skin_temp") = 2906.98 and z_score = 17441.86). Fix: scale MAD to a standard
deviation estimate (sigma = 1.4826 * MAD) and floor it per metric at a physiologically
meaningful minimum: MIN_SIGMA = {"resting_hr": 1.0, "hrv_rmssd": 2.0, "skin_temp": 0.1,
"respiratory_rate": 0.3}. Use sigma everywhere the code used mad (scores, bands, CUSUM).
personal_baseline should return (median, sigma); update the docstring and the bands dict
key "mad" -> "sigma" if present. Add a test: for every monitored metric, conformal_q is
between 1.5 and 6.0 on generate(7), and every drift signal's |z_score| < 50.

Bug 2: the CUSUM change start is too early (P-07 hrv_rmssd change estimated at trial day 9;
the true change is day 12). With sigma-scaled scores this should improve. Also change the
CUSUM to use the signed score in the deviation direction (positive = deviating) with
k = 0.5 and h = 4.0 as before. Add a test: at as_of = day 15 23:00, every drift signal for
P-07 and P-20 has window_start trial day between 11 and 13 inclusive.

When finished, list the files you changed and stop.
