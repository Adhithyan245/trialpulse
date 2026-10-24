Task T10c-fix: two problems seen in a real Gemini run of the evidence loop.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/gate/negative_control.py, trialpulse/gate/evidence.py,
tests/test_negative_control.py, tests/test_evidence.py. Nothing else. Keep all tests passing.

1. False drug link on "pre-dose" wording. The redraft "From day 12 to day 15, resting heart
   rate increased compared to a pre-dose baseline range." is held by negative_control,
   because "dose" inside "pre-dose" matches the exposure terms. Referring to the pre-dose
   baseline is a comparison, not a drug link. In links_to_drug, before matching, remove
   these phrases (case-insensitive): "pre-dose", "predose", "pre-dosing", "pre-treatment",
   "pretreatment", "before dosing", "before the dose", "prior to dosing". Then match as
   before. Add tests: that sentence -> links_to_drug False; "Resting heart rate rose after
   the study drug started." -> True; "compared with pre-dose days, HRV fell after dosing
   began" -> True (the second mention still links to dosing).

2. Duplicate requests across rounds. In run_loop, round 2 re-requested symptom_checkin,
   predose_comparison and trial_level_alert for P-07 and produced a second identical reply.
   Track request kinds already issued for the participant in this loop; plan_requests must
   skip kinds already issued (add an `already_issued: set[str] = frozenset()` parameter).
   If a held redraft produces no new requests, still redraft (feedback only) until
   max_rounds. Add a test: with a FakeModel that stays causal for 3 drafts and
   max_rounds=3, exactly one reply Reading exists and each kind appears once in
   result.requests.

When finished, list the files you changed and stop.
