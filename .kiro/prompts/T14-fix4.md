Task T14-fix4: finish the checkpoint scene's sequence and layout.

You cannot run shell commands or use the web in this project; the reviewer checks the
browser. Files you may edit: web/src/scenes/Scene2Checkpoint.tsx and files in
web/src/scenes/checkpoint/. Nothing else.

What the reviewer measured by stepping with Next through case v02:
  step labels seen: Intro, Checking claim 1..5, Draft verdict, Intro, Checking claim
  1..5, Draft verdict, Monitor's desk.
  The evidence step is missing: requests and replies appear in the inbox without their
  own step. Signing works (Approve -> "Sealed as AUD-00086 · a011fdd04a3a…").
Fix:
 1. Between a held draft's "Draft verdict" and the next draft, add two steps:
    "Requesting evidence" (the requests created after that draft appear one by one in the
    inbox, each sliding in from the right, ~600 ms apart, with the ring that triggered it
    named: "triggered by Causation") and "Evidence received" (each reply appears under its
    request with the "Simulated reply" label). Only requests whose sent_at falls between
    this draft's as_of and the next draft's as_of belong to this round; the inbox must be
    empty during draft 1's travel.
 2. The verdict counts claims, not checks: "Held: 3 of 5 claims stopped" (distinct claim
    ids with a failing claim-level check), plus " · 1 report-level check failed" when a
    report-level check failed. Passing: "Passed all checks".
 3. At Intro the queue shows the draft's claim chips ("C1 … C5"); it currently shows "—".
 4. Under 1024px: no horizontal page scroll (the case <select> must be w-full max-w-full,
    the pulse strip container w-full), and the "The checkpoint" heading must not overlap
    the pulse strip (the strip card's height follows its content: remove any fixed
    height; the SVG keeps viewBox 0 0 400 80 and width 100%).
 5. At desktop, the pulse strip card is much taller than its chart; let it size to its
    content.
When finished, list the files you changed and stop.
