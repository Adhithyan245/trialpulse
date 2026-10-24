Task T10-fix2: stop false holds on correct "no missing data" claims.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/gate/adapter.py and/or trialpulse/gate/live.py (wherever
the missing-data check result is turned into a GateCheck), tests/test_gate_checks.py.
Nothing else.

Real Gemini reports for P-07 (complete window, 15 of 15 days) are being held. The reviewer
found PulseEval's coverage_claims parser marks BOTH completeness_claimed=True and
gap_acknowledged=True for common phrasings, so evaluate_missing_data fails its
"no gap claimed when complete" logic ("gap claimed but window complete"):
  "Wearable and diary records are complete across the observation window from trial day
   1 to day 15 without missing data periods."
  "Wearable and daily self-report records are complete across all 15 observation days
   with no missing windows."
This is a PulseEval parser limitation (negation not applied to "missing").

Rule to implement for the coverage check: compute cov = coverage_claims(claim.text).
If cov.completeness_claimed and cov.gap_acknowledged both hold, the claim's meaning is
"complete, no gaps": decide it from the data instead of the PulseEval result:
pass when the window is complete (available == expected_observations), fail with
explanation "claims complete data but only A of N days are available; missing: [...]"
when it is not. In the passing case set the explanation to
"complete-data claim matches the data (A of N days); PulseEval parser read 'missing' as a
gap, overridden by rule". In every other case keep using the PulseEval result unchanged.

Tests: add both sentences above as coverage claims for P-07 at day 15 23:00 -> pass;
the same "complete ... with no missing windows" sentence for S03 participant P-06 at day
28 23:00 -> fail. Keep all existing tests passing.

When finished, list the files you changed and stop.
