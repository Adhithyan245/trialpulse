Task T10b: the negative-control check for claims that link a change to the study drug.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Read trialpulse/gate/adapter.py, trialpulse/gate/live.py, trialpulse/signals/baseline.py
and trialpulse/signals/detect.py first.

Files you may create: trialpulse/gate/negative_control.py, tests/test_negative_control.py.
You may edit trialpulse/gate/live.py to add the check. Nothing else. Keep all tests passing.

Idea: before a report may link a change to the study drug at all (causal OR association
wording), compare the change against two controls that need no unblinding of the
participant: (1) the participant's own pre-dose days, (2) the rest of the trial, split by
arm in aggregate only. If the pattern is just as common in both arms, a drug link is not
supported. The monitor is blinded, so explanations must never state this participant's arm.

trialpulse/gate/negative_control.py
  DRUG_TERMS: reuse EXPOSURE_TERMS from adapter.py.
  links_to_drug(claim) -> bool: claim text mentions an exposure term (word-prefix,
    case-insensitive) AND an outcome term (OUTCOME_TERMS from adapter.py).
  compare(trial, participant_id, as_of, signals) -> dict (JSON-serializable):
    "metrics": the participant's drift metrics as of as_of;
    "predose_exceedance_rate": over the participant's pre-dose days (1-7) known as of
       as_of, the fraction of (day, metric) pairs for those metrics outside the personal
       band in the deviation direction (use personal_bands from baseline.py);
    "postchange_exceedance_rate": the same fraction over the drift window days;
    "differs_from_predose": postchange > predose + 0.5;
    "trial_drift_rate": participants with any drift signal / all participants (as of
       as_of, use detect(trial, as_of) once);
    "arm_rates": {"A": rate, "B": rate} drift-signal rate per arm in aggregate;
    "arm_difference": abs(rate_A - rate_B);
    "drug_link_supported": differs_from_predose and arm_difference >= 0.10
       (the same pattern at the same rate in both arms does not support a drug link).
  check(trial, report, claim, signals) -> GateCheck | None: None unless
    links_to_drug(claim). Dimension f"negative_control:{claim.claim_id}". passed =
    drug_link_supported. Explanation (blind-safe, no arm of this participant):
    "Pre-dose exceedance {p:.0%}, after the change {q:.0%}; the same pattern appears in
    {n} of {N} participants, at {a:.0%} and {b:.0%} in the two treatment groups. A link to
    the study drug is {'supported' if ok else 'not supported'} by these controls."

live.py: run check() for every claim, append the GateCheck when not None; a failure makes
the verdict "hold" like any other check. Export `negative_control_summary(trial, report,
signals)` returning compare(...) for the UI.

tests/test_negative_control.py (generate(7), detect, as_of day 15 23:00):
 - P-07: differs_from_predose is True; arm_rates A and B are equal (P-07 arm A and P-20
   arm B each drift, one of 20 per arm), so drug_link_supported is False.
 - a claim "HRV dropped after the study drug started." citing P-07 readings -> check
   fails; the explanation contains "not supported" and does not contain " arm A" or
   " arm B".
 - a claim "HRV fell to 51.6 ms on day 12." -> check() returns None (no drug link).
 - in gate_report, a report whose only claim is the drug-linked HRV claim -> verdict hold
   with a failing negative_control dimension.

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
