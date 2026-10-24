Task T10: the rest of the gate checks (coverage, number recomputation, wearable-vs-diary
conflict, certainty). With tests.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Read trialpulse/gate/adapter.py, trialpulse/gate/live.py, tests/test_gate.py,
trialpulse/signals/detect.py and trialpulse/agent/deid.py first. Use the PulseEval API
quoted below; never copy PulseEval code.

Files you may edit: trialpulse/gate/adapter.py, trialpulse/gate/live.py,
tests/test_gate.py. You may create trialpulse/gate/recompute.py and
tests/test_gate_checks.py. Nothing else. Keep every existing test passing.

PulseEval API (installed):
  from pulseeval.scenarios import NumericCase, AssessmentCase
    common fields as for RelationshipCase (case_id, description, timeline, question,
      as_of, target_name, provenance, certainty=None|"direct_answer_supported"|
      "uncertainty_required"|"abstention_required"|"conflict_requires_qualification",
      conclusion_terms: list[str] = [])
    NumericCase: window_start: datetime, expected_value: float, unit: str,
      tolerance: float, expected_record_ids: list[str], expected_observations: int
      (daily observations a complete window would contain; window_start + i days for
      i in range(expected_observations) are the expected days)
    AssessmentCase: window_start: datetime, wearable_record_ids: list[str],
      self_report_record_ids: list[str], wearable_indicates: "good"|"poor"|"mixed",
      self_report_indicates: "good"|"poor"|None, relevant_names: list[str]
  from pulseeval.evaluation.missing_data import evaluate_missing_data      # NumericCase
  from pulseeval.evaluation.contradiction import evaluate_contradiction_handling  # Assessment
  from pulseeval.evaluation.uncertainty import evaluate_uncertainty_abstention  # needs certainty
  from pulseeval.evaluation.text import numbers_with_unit, coverage_claims
    numbers_with_unit(text, unit) -> list[(value: float, polarity)] where polarity is one
      of "negated", "past", "hedged", "affirmed"; matches a number immediately followed
      by the unit, e.g. "61.8 bpm".
    coverage_claims(text) -> object with .completeness_claimed, .gap_acknowledged,
      .available, .total, .missing, .imputation_claimed

New checks (all labels from rules over the data, never from the model):
1. Coverage (missing data), per claim: applies when claim.type == "coverage" or
   coverage_claims(claim.text) shows completeness_claimed or gap_acknowledged or counts.
   NumericCase: target_name "resting_hr" (a worn day = a day with a resting_hr reading),
   window_start = 07:00 on the first trial day of the report window, expected_observations
   = number of trial days from that day through the as_of trial day (inclusive),
   expected_record_ids = the participant's resting_hr readings known as of as_of in that
   window, expected_value = their mean (0.0 if none), unit "bpm", tolerance 1000.0
   (the answer check is not run here). Run evaluate_missing_data.
2. Recomputation, per claim (our own check, in recompute.py): UNITS = {"bpm", "ms", "%",
   "C", "rpm", "h", "min"}. For each unit, take the affirmed numbers in the claim text
   (numbers_with_unit). Each affirmed number must match, within max(0.05, 0.5% of value),
   either one cited reading with that unit or the mean of all cited readings with that
   unit. A number whose unit appears in no cited reading also fails. Return a GateCheck
   with dimension f"recompute:{claim_id}" and an explanation such as
   "AI said 48.0 bpm; cited resting_hr values are 51.2, 52.0, 59.4 (mean 54.2)" on
   failure, "all N numbers match the cited records" on pass. Skip claims with no numbers
   that carry a unit (no check emitted).
3. Contradiction, per report: applies when the participant has a diary_conflict signal
   or (fatigue >= 8 on >= 2 of the last 3 days known as of as_of and no drift signal).
   AssessmentCase with wearable_record_ids = the participant's wearable readings on the
   as_of trial day known as of as_of (if none, the latest day with any), self-report ids =
   the fatigue / symptom_note readings in the last 3 days, wearable_indicates = "poor" if
   any drift signal else "good", self_report_indicates = "poor" if max fatigue >= 8,
   "good" if max fatigue <= 4, else None, relevant_names = all metric names among those
   records. The trace uses the WHOLE report text (claims joined with " ") as final_answer
   and the union of all cited ids. Dimension f"contradiction:{report_id}".
4. Certainty, per report: label rule: "conflict_requires_qualification" if check 3
   applies with an actual conflict; else "uncertainty_required" if the participant has a
   non_wear signal; else not evaluated. conclusion_terms = ["normal", "stable", "safe",
   "no concern", "recovered", "fine"]. Run evaluate_uncertainty_abstention on the whole
   report text. Dimension f"uncertainty:{report_id}".
failed_claims() must keep working for claim-level dimensions; add failed_dimensions(result)
-> list[str] of failing dimension prefixes (e.g. ["causal_restraint", "recompute"]).

tests/test_gate_checks.py (no network; hand-built Reports with real record ids from
generate(7)):
 - S03 participant P-06 at day 28 23:00: coverage claim "Data was complete across all
   days with no missing days." -> missing-data check fails, verdict hold.
 - P-07 at day 15 23:00: the same coverage claim passes the missing-data check (P-07 has
   no gaps).
 - recompute: a claim "Resting heart rate reached 99.0 bpm." citing real P-07 resting_hr
   readings fails with the cited values in the explanation; a claim quoting the exact
   value of a cited reading passes; a claim quoting the mean of the cited values passes.
 - P-31 at day 16 23:00: report "Wearable metrics remain normal and stable." citing
   P-31's day-16 readings -> contradiction check fails (both sources not acknowledged);
   report "Wearable data looks normal, but the participant's diary reports exhaustion;
   the two sources conflict." -> contradiction passes.
 - P-02 at day 28 23:00 (non_wear): "Recovery is definitely normal." -> uncertainty
   check fails.

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
