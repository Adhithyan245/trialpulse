Task T16: Scenes 3, 4 and 5 (sign and seal, how this was verified, proof it works), plus
two small backend endpoints they need.

You cannot run shell commands or use the web in this project; the reviewer runs the
backend tests, builds the web app and checks it in a browser. Read .kiro/steering/design.md,
web/src/types.ts, web/src/api.ts, web/src/checks.ts, web/src/components/*.tsx,
trialpulse/api/app.py, trialpulse/api/state.py, trialpulse/api/audit.py,
trialpulse/data/trials.py and data/derived/metrics_validation.json first.
TypeScript is strict (noUnusedLocals / noUnusedParameters).

Files you may create or edit: web/src/scenes/Scene3Seal.tsx, Scene4Verified.tsx,
Scene5Proof.tsx, new files under web/src/scenes/seal/, web/src/scenes/verified/,
web/src/scenes/proof/, web/src/api.ts and web/src/types.ts (add only), and for the
backend: trialpulse/api/app.py, trialpulse/api/state.py, tests/test_api.py (add only).
Nothing else. No new dependencies (recharts, motion, lucide-react installed).

Backend additions (with tests in tests/test_api.py):
 - POST /api/audit/reset-demo: clears the audit table and re-seeds it from the recorded
   runs exactly like first startup (so one judge's tamper does not break the demo for the
   next). Returns verify(). Implement via a new AuditLog-level helper in state.py that
   drops and recreates the table inside the log's lock (add a method only if needed in
   state.py; do not edit audit.py beyond what the reset needs — if a reset method is
   needed in audit.py you may add ONE method `reset()` there and edit audit.py for that).
 - GET /api/trials?q=&wearable=0|1&limit=50: rows from load_trials() joined with the
   cached locations (load_locations(), never refresh from the network in the API):
   nct_id, title, phase_label, conditions, wearable_measurable, cities (list). q filters
   case-insensitively on title or conditions; wearable=1 keeps wearable-measurable only.
   Also return "total" (matches before the limit).

Scene 3, "Sign and seal" (GET /api/audit, /api/audit/verify, POST tamper, reset-demo):
 - The chain as a vertical list of linked blocks (newest first), each: entry_id, action
   (plain words), actor_role, ts, report_id, a one-line summary of details (for signatures:
   signer, decision and reason), and "prev 3f9a1c… → hash a011fd…" in mono. A connector
   line between blocks.
 - A header with "Verify chain" (shows StatusPill pass "Chain intact: 86 entries checked"
   or held "Chain broken at AUD-00012: <reason>"), a filter by report id, and "Reset demo".
 - Each block has a small "Tamper" button (behind a confirmation inside the page, no
   window.confirm): POST /api/audit/tamper {entry_id}; afterwards re-verify and mark every
   block from the broken one onward with the held token and "chain broken from here".
 - Explain in one sentence at the top: "Every action is a block whose fingerprint includes
   the one before it, so editing any past entry breaks every fingerprint after it."
Scene 4, "How this was verified" (GET /api/runs, /api/runs/{id}, /api/negative-control/{id},
 /api/participants/{pid}/series?day=N):
 - Case picker (default v02) and draft picker (Draft 1 ... n).
 - For each claim of the chosen draft: the claim text; its cited records as a small table
   (record id mono, metric, value + unit, trial day, recorded at) using the series data;
   its checks grouped by ring (RINGS from checks.ts) with pass/held pills and the full
   explanation text in a disclosure; for "recompute" show the explanation prominently
   ("AI said 48.0 bpm; cited records show …").
 - A "Controls" panel from /api/negative-control/{id}: pre-dose exceedance, after-change
   exceedance, "n of N participants", the two treatment-group rates WITHOUT saying which
   group this participant is in, and "drug link supported / not supported".
 - Report-level checks (contradiction, uncertainty) in their own section.
Scene 5, "Proof it works" (GET /api/metrics, /api/trials):
 - Validation scorecard from metrics.validation (only real numbers; if missing, say
   "Run the validation suite to see numbers"): "11 of 12 raw AI drafts were held",
   "5 of 6 drafts without an injected fault were held", "9 of 12 passed after the evidence
   loop", "3 stayed held and never reached the monitor as approved", "0 unsafe reports
   reached the monitor", mean rounds, requests and replies; a Recharts horizontal bar
   chart of raw failures by dimension (labels via RINGS names; axis and text use theme
   tokens); a one-line note with the model names and "Measured with PulseEval on synthetic
   data; recorded runs in the repo".
 - "Regulatory fit" panel: FDA's draft guidance (January 2025) on AI credibility for
   regulatory decisions, as 7 short rows, each mapped to what TrialPulse does:
   1 question of interest (is this safety signal worth the monitor's attention?),
   2 context of use (drafts for a blinded medical monitor; a human signs every report),
   3 model risk (low influence: every report is gated and signed),
   4 credibility plan (PulseEval checks, negative controls, validation suite),
   5 execute (recorded runs), 6 document (audit chain, Scene 3), 7 adequacy (scorecard).
   Label the guidance "draft" explicitly. Also a line naming ICH E6(R3) audit-trail
   expectations and 21 CFR Part 11 e-signatures as what Scene 3 addresses.
 - "Trial finder": a search box + "wearable-measurable only" toggle over GET /api/trials,
   showing title, plain-language phase, conditions, Massachusetts cities; and a stat row
   from metrics.public: total recruiting trials, wearable-measurable trials, trials with a
   Boston site, trials with a Springfield site (from top_cities), and one sentence:
   "Trial access concentrates in Boston: <Boston> trials list a Boston site, <Springfield>
   list Springfield." (numbers from the data).
 - "Beyond trials": from metrics.public.readmissions: "<heart_failure_above_1> of
   <with_ratio for READM-30-HF-HRRP> Massachusetts hospitals have heart-failure
   readmissions above the expected rate (CMS)", and one sentence that the same gate can
   check AI summaries for post-discharge monitoring.
All scenes: loading and error states, theme tokens only, works under 1024px with no
horizontal scroll, keyboard accessible.
When finished, list every file you created or changed and stop.
