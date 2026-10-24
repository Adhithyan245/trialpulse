Task T24: the "Try to fool the checkpoint" panel.

You cannot run shell commands or use the web in this project; the reviewer builds it and
checks it in a browser. Read .kiro/steering/design.md, web/src/api.ts, web/src/types.ts,
web/src/checks.ts, web/src/components/StatusPill.tsx, web/src/scenes/Scene2Checkpoint.tsx
and web/src/components/landing/HowItWorks.tsx first. TypeScript strict (no unused).

Files you may create: web/src/components/TryIt.tsx. You may edit
web/src/scenes/Scene2Checkpoint.tsx (only to render <TryIt /> as a section at the very
bottom of the scene, full width) and web/src/api.ts + web/src/types.ts (add only).
Another task is building the backend at the same time; this is its contract:
  POST /api/gate/try  body {participant_id: string, day: number, text: string}
  200 -> {report: Report, gate: GateResult, negative_control: object | null}
  422 -> {detail: string}
Nothing else.

TryIt panel:
 - Heading "Try to fool the checkpoint", one line: "Write a claim about a participant the
   way an AI might. The same deterministic checks judge it instantly; no AI is involved."
 - Scenario picker (segmented buttons): "P-07 · day 15 (changed after dosing)",
   "P-20 · day 15 (changed after dosing)", "P-06 · day 28 (Springfield, missing days)",
   "P-31 · day 16 (diary says exhausted)".
 - A textarea (max 600 chars, counter) and example chips that fill it:
   "The study drug caused P-07's HRV drop." · "HRV fell to 51.6 ms on day 12." ·
   "Data was complete across all days." · "The participant is definitely fine." ·
   "HRV dropped after the study drug started; the cause is not established."
 - "Check it" button (disabled while empty or loading; Ctrl+Enter submits).
 - Result: overall StatusPill (pass "Passed every check" / held "Held: N of M claims
   stopped"); for each claim: its text, the record ids it was matched to (mono, small),
   and a row of 7 ring chips (RINGS order) pass / held / n-a, using checksForClaim from
   checks.ts; for held rings show the explanation's first sentence (160 chars) with a
   Details disclosure. Report-level checks (suffix = report_id) listed under the claims.
   If negative_control is present, one line: "Controls: pre-dose X%, after the change
   Y%, n of N participants; drug link supported/not supported." (no arm of the
   participant).
 - Errors: show the server's detail text. Loading: "Checking…". Theme tokens only;
   responsive (no horizontal scroll under 1024px); keyboard accessible.
When finished, list every file you created or changed and stop.
