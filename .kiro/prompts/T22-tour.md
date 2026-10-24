Task T22: a guided tour across the five scenes.

You cannot run shell commands or use the web in this project; the reviewer builds and
checks it in a browser. Read .kiro/steering/design.md, web/src/App.tsx,
web/src/components/Shell.tsx (read only), web/src/styles.css and web/tailwind.config.js
first. TypeScript strict (no unused anything).

Files you may create or edit: web/src/components/Tour.tsx (new) and web/src/App.tsx (only
to mount <Tour />). Nothing else. Another task is editing Landing.tsx and Shell.tsx at
the same time: do not touch them.

Tour behavior:
 - Starts when window receives the event "tp:start-tour" (the landing page will dispatch
   it), or when the URL hash contains "tour" as a query-like suffix "#/?tour" or when the
   location search has "?tour=1".
 - Five steps; each step navigates (location.hash) to its scene and shows a callout card
   fixed at the bottom-right (bottom-center under 640px), max-width 360px, card token
   background, accent left border, shadow, z-index above the scene:
   1 "#/trial" "The trial, alive" - "40 synthetic participants across Boston, Worcester
     and Springfield. Each dot pulses at that person's resting heart rate. Press play:
     amber halos are changes outside a person's own range; hollow dots are days the device
     was not worn."
   2 "#/checkpoint" "The checkpoint" - "An AI drafted a safety report for P-07 and claimed
     the study drug caused the change. Press Play: every claim travels through 7 checks.
     Watch it stop at Causation, then see TrialPulse ask the participant for the missing
     evidence."
   3 "#/seal" "Sign and seal" - "A human signs every report. Each action is a block whose
     fingerprint includes the one before it. Try Tamper on any block: the chain breaks
     from that point on."
   4 "#/verified" "How this was verified" - "Every number the AI wrote is recomputed from
     the records it cited, and drug links are tested against pre-dose and trial-wide
     controls without unblinding the monitor."
   5 "#/proof" "Proof it works" - "Measured on 12 recorded Gemini runs. Plus the FDA
     credibility mapping and a search over 3,131 real Massachusetts trials."
 - Controls: Back, Next (Finish on the last step), "Skip tour" link, and "Step 2 of 5".
   Keyboard: Escape closes; the card is a dialog with aria-labelledby, focus moves to it
   when a step opens, and returns to the page on close.
 - Remember that the user finished or skipped (localStorage key "tp_tour_done", wrapped in
   try/catch); never auto-start; only start on the event or URL flag.
 - Respect prefers-reduced-motion (no slide-in animation).
When finished, list every file you created or changed and stop.
