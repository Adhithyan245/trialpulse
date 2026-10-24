Task T14: Scene 2, "The checkpoint" (2D, animated with `motion`). This is the demo
moment; make it clear, calm and precise.

You cannot run shell commands or use the web in this project; the reviewer builds it and
looks at it in a browser. Read .kiro/steering/design.md, web/src/types.ts, web/src/api.ts,
web/src/checks.ts, web/src/components/*.tsx, web/src/styles.css, web/tailwind.config.js
and trialpulse/api/app.py first.

Files you may create or edit: web/src/scenes/Scene2Checkpoint.tsx and new files under
web/src/scenes/checkpoint/. Nothing else. No new dependencies. Import motion as
`import { motion, AnimatePresence, useReducedMotion } from "motion/react"`.

Data (real API only, never invented): GET /api/runs (list) and GET /api/runs/{case_id}.
A run record has raw (first draft + gate) and pipeline.drafts[i] / pipeline.gates[i]
(drafts[0] is the raw draft), pipeline.requests (with sent_at, kind, question_text,
failed_dimension, reply_record_id), pipeline.replies (Readings with value = reply text,
source "simulated_reply"), pipeline.final_verdict. Gate check dimensions look like
"<prefix>:<claim_id>" (claim-level) or "<prefix>:<report_id>" (report-level).
Real dimension prefixes in the data: temporal_consistency, evidence_grounding, recompute,
missing_data, contradiction, uncertainty, causal_restraint, negative_control. Map them to
rings with RINGS / ringForDimension from checks.ts. Also GET
/api/participants/{pid}/series?day=N for the pulse strip.
Default case: "v02" (P-07, causal_overclaim). A case picker lists all runs as
"v02 · P-07 · day 15 · causal overclaim" (fault null -> "no fault injected").

Layout (desktop >= 1024px, three columns; stacked under that):
 Left, "Participant": participant id, trial day, a small SVG pulse strip of hrv_rmssd for
   days 1..N (line + shaded personal band from series.bands, gaps left as gaps, a vertical
   tick at the dose start day 8 labelled "dose start", the change window shaded), then an
   "Evidence requests" inbox that fills during the loop: each request as a row with its
   kind in plain words ("Symptom check-in", "Wear reminder", "Follow-up question",
   "Pre-dose comparison attached", "Trial-level alert"), the question text, and, once
   answered, the reply text with a "Simulated reply" label and its record id in mono.
 Center, "The checkpoint": seven vertical rings side by side (one per RINGS entry; label,
   and the plain sentence on hover/focus via title + an accessible description). Draft
   claims appear as cards on the left edge and travel through the rings left to right.
   For each claim and ring: if the claim has a failing check for that ring the card stops
   inside that ring, turns held-red (held token), and shows the reason: the first sentence
   of the explanation (cut at 160 chars) plus a "Details" disclosure with the full text;
   if it has a passing check the ring shows a small pass tick as the card passes; if no
   check applies the ring is dimmed for that card ("not applicable"). Report-level checks
   (suffix equals the report_id) appear as a badge at the top of their ring for that
   draft. Above the rings: "Draft k of n · <model_id> · <prompt_version>" and a
   "Recorded run" label. Under the rings: the draft verdict with StatusPill
   ("Held: 3 claims stopped" or "Passed all checks").
 Right, "Monitor's desk": appears when a draft passes. Shows the final claims as a clean
   list, then a reason textbox (required) and three buttons: Approve, Reject, Request
   redraft. On submit, POST /api/audit/sign {report_id: final draft report_id, decision,
   reason, signer: "Demo monitor"} with the current role; show the returned entry_id and
   the first 12 characters of entry_hash in mono ("Sealed as AUD-00031 · 3f9a1c…"), and a
   link "See it on the chain" to #/seal. The coordinator role sees the desk read-only with
   "Only the medical monitor or safety reviewer can sign."; show server errors verbatim.
   If the final verdict is hold, the desk shows "Still held after N rounds: never sent to
   the monitor as approved" instead.

Sequence (a small state machine, steps advance on Play or Next; Restart resets):
 1 intro (participant strip, first draft claims stacked at the left edge)
 2 claims travel through the rings one after another (~700 ms per ring; failures stop)
 3 draft verdict
 4 if held: the evidence requests created after that draft (sent_at between this draft's
   as_of and the next draft's as_of) fly from the failing ring area to the inbox, then
   their replies appear
 5 next draft: repeat 2-4 for every draft in pipeline.drafts
 6 desk
 Controls bar: Play/Pause, Next step, Restart, and a speed toggle (1x / 2x). With
 prefers-reduced-motion, skip travel animations and show each step's end state.
 Keyboard: Space = play/pause, Right arrow = next step.

Quality bar: no layout shift while cards move (fixed ring widths), long claim text wraps
inside cards (max 3 lines collapsed, expand on click), all text from the data, colors only
via the Tailwind token classes, focus visible, works in light and dark themes, and the
"Synthetic data" ribbon from the Shell stays visible. Split into small components under
web/src/scenes/checkpoint/ (PulseStrip, RingTunnel, ClaimCard, EvidenceInbox,
MonitorDesk, useSequence). Handle loading and API errors with a short visible message.

Done when the reviewer's `npm run build` succeeds and the scene works in the browser.
When finished, list every file you created or changed and stop.
