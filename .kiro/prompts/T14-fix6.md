Task T14-fix6: the evidence steps never run, and the cleared row overflows.

You cannot run shell commands or use the web in this project; the reviewer checks the
browser. Files you may edit: web/src/scenes/checkpoint/useSequence.ts,
web/src/scenes/checkpoint/RingTunnel.tsx, web/src/scenes/Scene2Checkpoint.tsx,
web/src/scenes/checkpoint/EvidenceInbox.tsx. Nothing else.

1. Root cause found by the reviewer: in the recorded runs a request's sent_at is EQUAL to
   the next draft's as_of (the loop sends the request and redrafts at the same instant,
   e.g. sent_at "2026-10-05T23:10:00" and draft 2 as_of "2026-10-05T23:10:00").
   useSequence.ts (verdict case, ~line 106-115) keeps a request only when
   sentAt < nextAsOf, so requestsInRange is always empty and the sequence jumps from
   "Draft verdict" straight to the next draft. My task wording ("between") caused this.
   Correct rule everywhere a request is assigned to a round (useSequence.ts and the
   visibleRequests logic in Scene2Checkpoint.tsx / EvidenceInbox.tsx):
       draft_i.as_of < sent_at <= draft_{i+1}.as_of   (for the last draft: sent_at > as_of)
   Put this rule in ONE exported helper (requestsForRound(pipeline, i)) in useSequence.ts
   and use it in all places. The reviewer will step through v02 with Next and expects:
   ... "Draft verdict" (held), "Requesting evidence", "Evidence received", then draft 2.
   The inbox must show 0 replies before "Evidence received" and the reply after it.
2. Overflow under 1024px: the "Cleared" row renders chips with the full claim id
   (e.g. "RPT-P-07-202610052300-1-C1", ~111px each) in a non-wrapping flex row (classes
   "flex gap-1"), pushing the page to 698px wide in a 498px window. Show short labels
   ("C1") on the chips with the full id in title, and add flex-wrap to the queue and
   cleared rows. Do the same anywhere else claim chips are rendered.
When finished, list the files you changed and stop.
