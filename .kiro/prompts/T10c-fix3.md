Task T10c-fix3: redraft wording and the participant reply as evidence.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/agent/prompts.py, trialpulse/gate/adapter.py,
tests/test_gate.py, tests/test_evidence.py. Nothing else. Keep all tests passing.

Seen in a real run (P-07, causal_overclaim first draft, 3 rounds):
1. The final redraft said "An association was observed between the timing of dose start
   on day 8 and subsequent physiological shifts". The negative-control check correctly
   holds this: the controls show the same pattern at the same rate in both treatment
   groups. The cause is REDRAFT_TEMPLATE, which says "describe timing as an association
   only" and so invites a drug association. Replace that sentence with: "Do not link any
   change to the study drug or to dosing, not even as an association or a timing
   coincidence: the pre-dose and trial-wide comparison does not support a drug link.
   Describe what changed, when, and what other explanation the new evidence offers."
   Keep the other instructions. Update any test that asserts on the old wording.
2. Draft 2 was held by evidence_grounding: "Irrelevant records cited:
   ['P-07-reply-symptom_checkin-...']". The participant's reply (name "symptom_note") is
   legitimate evidence: it is the competing explanation (a cold). The previous fix
   excluded "symptom_note" from confounder_names, which also removed it from the case's
   relevant names. Put "symptom_note" back into confounder_names when a symptom_note
   reading is cited (it must still never be the outcome_name). Update the test that
   asserted it is excluded, so it now asserts it is a confounder and not the outcome.
   Add a test: a relationship claim citing P-07 HRV readings plus a reply symptom_note
   passes evidence_grounding.

When finished, list the files you changed and stop.
