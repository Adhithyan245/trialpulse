Task T17-polish: visual fixes the reviewer found in the browser (Scenes 1, 2 and 5).

You cannot run shell commands or use the web in this project; the reviewer builds and
checks it in a browser. Files you may edit: web/src/scenes/Scene1Trial.tsx,
web/src/scenes/trial/*, web/src/scenes/Scene5Proof.tsx, web/src/scenes/Scene2Checkpoint.tsx,
web/src/scenes/checkpoint/PulseStrip.tsx. Nothing else. TypeScript strict (no unused).

Scene 1 (trial map):
 a. Participants of a site are drawn on top of each other: each cluster looks like one dot.
    Offsets must be applied in SCREEN pixels after projecting the site anchor: ring 1 has
    6 dots at radius 12 px, ring 2 has 12 dots at radius 24 px, ring 3 the rest at 36 px
    (angle evenly spaced, starting at -90deg). Dot radius 4.5 px. Scale the whole map so
    Massachusetts fills the map card (fitExtent with 16 px padding).
 b. Site labels and county names are tiny: site label 12px semibold text color, county
    names 10px muted, placed so they do not overlap dots (site label to the right of its
    outer ring).
 c. County borders are nearly invisible on the dark theme: stroke with the muted token at
    55% opacity, 1px, fill card.
 d. Remove the extra "Synthetic data" banner inside the scene (the Shell already shows the
    ribbon at the top).
Scene 5 (proof):
 e. The "Raw failures by dimension" bars render solid black: Recharts SVG fill does not
    resolve Tailwind class names. Read the CSS variable values at runtime
    (getComputedStyle(document.documentElement).getPropertyValue("--accent").trim(), and
    the text/line/muted tokens for axes and labels; re-read when the theme changes via a
    MutationObserver on <html data-theme> and a matchMedia listener) and pass real color
    strings.
 f. "Causation" appears twice because causal_restraint and negative_control both map to
    the Causation ring: aggregate counts by ring (sum), so each ring appears once, in RINGS
    order, skipping rings with 0.
 g. The stat cards overflow and are clipped on the right: use a wrapping grid
    (grid-cols-2 sm:grid-cols-3 lg:grid-cols-4, gap-4) with min-w-0 cards; numbers in
    tabular-nums mono at a size that fits.
Scene 2 (checkpoint):
 h. Under 1024px the page is still ~35 px wider than the window at one step; find any
    fixed min-width or non-wrapping row in the checkpoint files and fix it (min-w-0,
    flex-wrap, break-words for long ids).
 i. The pulse-strip card is much taller than its chart: the card must size to its content.
When finished, list the files you changed and stop.
