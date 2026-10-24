Task T10-fix: one test sentence hits a known PulseEval parser limitation.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
File you may edit: tests/test_gate_checks.py only.

Current result: 76 passed, 1 failed: test_coverage_claim_passes_when_window_complete.
The reviewer checked pulseeval.evaluation.text.coverage_claims directly:
  "Data was complete across all days with no missing days." ->
      completeness_claimed=True AND gap_acknowledged=True   (PulseEval limitation: the
      "with no missing days" phrasing is read as acknowledging a gap)
  "Data was complete across all days."   -> completeness_claimed=True only
  "All 15 days had data with no gaps."   -> completeness_claimed=True, available 15/15
Real Gemini coverage sentences parse correctly, so this only affects the test wording.

In test_coverage_claim_passes_when_window_complete (P-07, complete window) use the claim
text "All 15 days had data with no gaps." Keep the S03 failing test's sentence unchanged
(it is expected to fail there anyway). Add a short comment above the passing test naming
the PulseEval limitation. Change nothing else. When finished, list the file you changed
and stop.
