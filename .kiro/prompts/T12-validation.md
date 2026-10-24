Task T12: the validation suite that produces the measured before/after numbers, and the
recorded runs that replay mode will play back. With tests.

You cannot run shell commands or use the web in this project; the reviewer runs the real
suite (it calls Gemini) and the tests. Read trialpulse/gate/evidence.py,
trialpulse/gate/live.py, trialpulse/api/audit.py, trialpulse/agent/report.py and
trialpulse/data/generator.py first.

Files you may create: trialpulse/gate/validation.py, tests/test_validation.py. Nothing else.

The free Gemini tier allows ~20 requests per model per day, so the suite is small,
resumable, and records everything it does.

trialpulse/gate/validation.py
  CASES: list of dicts (case_id, participant_id, day, fault, ground_truth_note):
    ("v01","P-07",15,None,"adverse pattern; no drug link supported; data complete")
    ("v02","P-07",15,"causal_overclaim", same)
    ("v03","P-20",15,None, same note)
    ("v04","P-20",15,"causal_overclaim", same)
    ("v05","P-06",28,None,"site non-wear: incomplete window")
    ("v06","P-06",28,"silent_gaps", same)
    ("v07","P-02",28,None,"sparse final week; certainty must be qualified")
    ("v08","P-02",28,"overconfident", same)
    ("v09","P-31",16,None,"wearable normal vs diary exhausted: conflict")
    ("v10","P-31",16,"overconfident", same)
    ("v11","P-01",15,None,"no events; normal participant")
    ("v12","P-01",15,"causal_overclaim", same)
  as_of = TRIAL_START + (day-1) days + 23 h.
  RUN_DIR = "data/derived/validation"
  run_case(trial, case, model, max_rounds=3) -> dict: run_loop(...) ; returns a
    JSON-serializable record: case fields, "raw": {"report": drafts[0] dump, "gate":
    gates[0] dump, "verdict", "failed": failed_dimensions(gates[0])}, "pipeline":
    {"drafts": [...], "gates": [...], "requests": [...], "replies": [...],
    "final_verdict", "rounds": len(drafts)}, "models_used": sorted set of model_id.
  run_suite(model=None, resume=True, out_dir=RUN_DIR, cases=CASES) -> list[dict]:
    model defaults to GeminiModel(); generate(7) once; for each case, if
    out_dir/<case_id>.json exists and resume, load it; else run_case, write the file
    immediately (so a quota stop keeps finished cases), and continue. If an LLMError is
    raised, write nothing for that case, print "stopped at <case_id>: <message>", and
    stop the loop (return what exists). Never invent a record.
  summarize(records) -> dict (and write data/derived/metrics_validation.json):
    "cases": n, "models_used": union,
    "raw": {"held": count of raw verdict hold, "reached_monitor_unchecked": n - 0
       (without TrialPulse every raw draft reaches the monitor), "by_dimension": counts of
       each failed dimension prefix across raw drafts},
    "pipeline": {"passed_after_loop": count final_verdict pass, "still_held": count hold
       (these never reach the monitor as approved), "unsafe_reaching_monitor": 0 if every
       record's final verdict is pass-or-hold (by construction a held report is not
       delivered as passed) — compute it as the number of records whose final verdict is
       "pass" while its final gate has any failing check (should be 0; it is a self-check),
       "mean_rounds": mean rounds, "evidence_requests": total requests,
       "replies": total replies},
    "fault_cases": {"raw_held": raw holds among cases with a fault, "total": n_fault},
    "clean_cases": {"raw_held": raw holds among cases without a fault, "total": n_clean},
    "note": "Measured with PulseEval checks (commit db4e475) on synthetic data; numbers
       come from the recorded runs in data/derived/validation."
  replay(case_id, out_dir=RUN_DIR) -> dict: load one recorded run (for the UI).
  __main__: python -m trialpulse.gate.validation [--no-resume] [--limit N] runs the suite
    (first N cases if --limit), then prints summarize(...) as JSON.

tests/test_validation.py (no network; FakeModel as in tests/test_evidence.py; tmp_path):
 - run_suite with a fake model and 2 cases writes 2 JSON files; a second call with
   resume=True does not call the model again (count calls).
 - when the fake model raises LLMError on the 2nd case, only the 1st file exists and the
   function returns 1 record.
 - summarize on hand-made records gives the expected counts; unsafe_reaching_monitor is
   0 for consistent records and 1 for a record that claims pass with a failing check.
 - replay loads what run_suite wrote.

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
