Task T21: make the landing page and the app shell match the product's quality.

You cannot run shell commands or use the web in this project; the reviewer builds and
checks it in a browser. Read .kiro/steering/design.md, web/src/components/Landing.tsx,
web/src/components/Shell.tsx, web/src/api.ts, web/src/types.ts, web/index.html,
web/src/styles.css, web/tailwind.config.js, data/derived/metrics_validation.json and
data/derived/metrics_public.json first. TypeScript strict (no unused anything).

Files you may create or edit: web/src/components/Landing.tsx, web/src/components/Shell.tsx,
new files under web/src/components/landing/, web/index.html, web/public/favicon.svg,
web/src/scenes/trial/MapView.tsx (only the height fix in 6). Nothing else. No new
dependencies (motion and lucide-react are installed).

1. Hero (two columns >= 1024px, stacked below):
   left: the headline "The AI drafts. Deterministic checks verify. Humans decide.", the
   existing one-sentence description, and three buttons: "Start the demo" (primary, to
   #/checkpoint), "Take the tour" (secondary; dispatches
   window.dispatchEvent(new CustomEvent("tp:start-tour"))), "See the proof" (text link to
   #/proof). Under the buttons a small line: "Synthetic participants · real Massachusetts
   trial data · recorded Gemini runs".
   right: an animated pipeline illustration (inline SVG, ~420x300 viewBox, theme tokens):
   a wearable pulse line -> an "AI draft" card -> a row of 7 small rings (the checkpoint;
   one ring turns held, red) -> a curved arrow looping back to the participant labelled
   "asks for evidence" -> a seal labelled "human signs". A single gentle looping motion
   (the pulse travels left to right, ~6 s loop); static with prefers-reduced-motion.
2. Proof strip right under the hero: four stat tiles with REAL numbers read from
   /api/metrics (validation and public); if a number is missing, hide that tile:
   "<raw.held> of <cases>" raw AI drafts held · "<clean_cases.raw_held> of
   <clean_cases.total>" held even with no injected fault · "<unsafe_reaching_monitor>"
   unsafe reports reached the monitor · "<total_trials>" Massachusetts recruiting trials
   searchable. Big mono numbers, small muted captions, tiles in a wrapping grid.
3. "How it works": five steps in order, each linking to its scene (1 The trial, alive -
   wearables against personal baselines; 2 The checkpoint - every claim through 7
   checks; 3 Sign and seal - human signature on a tamper-evident chain; 4 How this was
   verified - every number recomputed; 5 Proof it works - measured on recorded runs).
   Remove the old three role cards from the landing (roles stay in the Shell).
4. Footer: data sources (ClinicalTrials.gov, MassGIS, CDC PLACES, CMS, US Census Bureau),
   "Reliability checks by PulseEval (MIT)", "Built with Kiro", and a link to
   https://github.com/Adhithyan245/trialpulse.
5. Shell under 768px: a compact top bar (wordmark, current scene name, a menu button with
   aria-expanded) that opens a panel with the five scenes, the role switcher, the mode
   badge and the theme toggle; close it on navigation and on Escape. At >= 768px keep the
   current sidebar. The "Synthetic data" ribbon stays visible in both.
6. In web/src/scenes/trial/MapView.tsx an <svg> has height="auto", which the browser
   rejects ("<svg> attribute height: Expected length, 'auto'"): remove that attribute and
   use style={{ height: "auto" }} with viewBox and width 100%.
7. web/public/favicon.svg: a simple ring with a pulse line through it in the accent teal
   (#0F7C86) on transparent; reference it in index.html. Add to index.html: <meta
   name="description" content="TrialPulse: wearable-powered clinical trials where every
   AI safety report is checked before a human signs.">, og:title "TrialPulse",
   og:description (same text), og:type website, theme-color #0E1A24.
When finished, list every file you created or changed and stop.
