Task T14-polish: make the checkpoint read as a tunnel the claims travel through.

You cannot run shell commands or use the web in this project; the reviewer builds it and
checks it in a browser. Files you may edit: web/src/scenes/Scene2Checkpoint.tsx and files
in web/src/scenes/checkpoint/. Nothing else. No new dependencies.

What the reviewer saw at 1440x900 (real data, case v02):
 a. The 7 rings are circles in a wrapping 3-column grid, so there is no tunnel; at a
    narrower width they wrap to 2 columns and the participant column overlaps them.
 b. The claim card is rendered below all the rings instead of moving through them.
 c. "Held: 9 claims stopped" is visible during the intro, before anything has moved.
 d. The pulse strip shows the shaded band but no line. The API data is fine: hrv_rmssd has
    15 points (values ~51-89), band lo 62.9 / hi 89.1. The y scale must be the min/max of
    all values AND the band, with 10% padding; draw the band, then the line, then dots.
 e. There is no right column (monitor's desk area) at desktop width.

Required layout:
 - Page grid: at >= 1280px, three columns `grid-cols-[260px_minmax(0,1fr)_320px]` with
   gap-6; at 1024-1279px, two columns (participant | checkpoint) and the desk spans below;
   under 1024px, one column. Every grid child gets min-w-0.
 - The tunnel: ONE horizontal row of 7 equal columns (CSS grid, repeat(7, minmax(0,1fr)))
   that never wraps at >= 1024px. Each ring is a tall vertical gate (rounded-full capsule,
   ~56px wide, ~200px tall, 2px border in the line token), label under it, plain sentence
   in a tooltip (title) and sr-only text. A thin horizontal track line runs through the
   vertical middle of all gates.
 - Claim travel: the active claim is a compact token (claim number "C3" + a 1-line
   truncated text) absolutely positioned on the track; its left position animates from
   before ring 1 to each ring in turn (use motion `animate={{ left: ... }}` with
   percentages of the tunnel width). On a passing ring the gate border flashes pass and a
   small tick stays under that gate for this claim; on a failing ring the token stops
   inside the gate, the gate border turns held, and the token turns held-soft with held
   text. Rings with no check for the claim stay dimmed while the token passes.
 - Below the tunnel, a "Current claim" panel: full claim text, cited record ids in mono,
   and a row of 7 small status chips (one per ring: pass / held / n/a) for this claim;
   when held, the reason (first sentence, 160 chars) and a Details disclosure.
 - Under each gate, a short list of claim chips ("C1", "C3") for claims stopped there in
   this draft, so after the travel step the picture shows where each claim was caught.
 - Left of the tunnel: a vertical queue of claim chips waiting to travel; claims that
   passed every ring collect at the right end ("cleared").
 - The draft verdict pill appears only at the verdict step.
 - Monitor's desk lives in the right column at >= 1280px.
Keep all behavior from T14 (sequence, inbox, desk, signing, keyboard, reduced motion).
When finished, list the files you changed and stop.
