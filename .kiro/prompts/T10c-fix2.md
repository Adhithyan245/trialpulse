Task T10c-fix2: two rule-labelling bugs seen in a real Gemini run of the loop.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/gate/adapter.py, trialpulse/gate/evidence.py,
tests/test_gate.py, tests/test_evidence.py. Nothing else. Keep all tests passing.

1. Outcome selection in relationship_case. A redraft claim linking rising fatigue with
   physiological changes, citing wearable readings plus the participant's reply
   (name "symptom_note"), was labelled outcome_name = "symptom_note", observed_direction
   "none", so PulseEval failed it with "association stated but the records show no
   pattern". New rule for outcome_name: the most common cited metric among MONITORED
   (trialpulse.signals.baseline) metrics; if none is cited, "fatigue" if a fatigue reading
   is cited; otherwise the most common cited wearable metric. Never "symptom_note".
   observed_direction for "fatigue": "positive" if the participant has fatigue >= 7 on
   >= 2 of the 4 trial days ending at as_of (known as of as_of), else "none".
   Exclude "symptom_note" from confounder_names. Add tests for both rules.

2. Redraft time crosses midnight. run_loop used now = as_of + 30 min * round, so with
   as_of = day 15 23:00, round 2 ran at day 16 00:00; the coverage check then expected 16
   days and flagged day 16 as missing. Use now = as_of + 10 minutes * round, and never
   later than 23:59 on as_of's calendar day (clamp). Add a test that every draft in a
   3-round loop has as_of on the same calendar date as the original as_of.

When finished, list the files you changed and stop.
