Task T15: Scene 1, "The trial, alive" (2D SVG now; the 3D version comes later).

You cannot run shell commands or use the web in this project; the reviewer builds and
checks it in a browser. Read .kiro/steering/design.md, web/src/types.ts, web/src/api.ts,
web/src/styles.css, web/tailwind.config.js, web/src/scenes/checkpoint/PulseStrip.tsx and
trialpulse/api/app.py first. TypeScript is strict (noUnusedLocals / noUnusedParameters).

Files you may create or edit: web/src/scenes/Scene1Trial.tsx and new files under
web/src/scenes/trial/. You may import (not edit) PulseStrip from ../checkpoint/PulseStrip.
Nothing else. No new dependencies (d3-geo and motion are installed).

Data (real API only): GET /api/trial, GET /api/clock (28 days, per participant:
participant_id, site_id, resting_hr|null, worn, drift, non_wear, diary_conflict),
GET /api/participants/{pid}/series?day=N, GET /api/metrics (public.short_sleep_by_county:
county -> % adults sleeping under 7 h). Map outlines: fetch "/ma-counties.geojson"
(served from web/public; a FeatureCollection of the 14 Massachusetts counties, properties
{county, fips}; source: US Census Bureau county boundaries). Credit the source in small
text under the map.

Map (SVG, responsive, viewBox, width 100%):
 - d3-geo geoMercator().fitSize to the counties; draw county paths (fill card, stroke line
   token, 1px); the three site counties (Suffolk, Worcester, Hampden) get a slightly
   stronger stroke and their name label.
 - Site anchors (lon, lat): S01 Boston (-71.06, 42.36), S02 Worcester (-71.80, 42.26),
   S03 Springfield (-72.59, 42.10). Place each site's participants in a tidy cluster
   around its anchor (deterministic: concentric rings of 6, 12 around the anchor, 9px
   apart), with the site name and "n participants" next to the cluster.
 - One dot per participant (r 4). It pulses (scale + opacity) with a period of
   60 / resting_hr seconds for the current day (no reading -> no pulse). States for the
   current day: drift -> watch-colored halo ring; not worn or non_wear -> hollow, dimmed
   dot; diary_conflict -> a small diary tick. Always pair state with a legend entry
   (legend under the map with icon + text). Honor prefers-reduced-motion (no pulsing).
 - Click or Enter on a dot selects the participant (focusable, aria-label
   "P-07, Boston, drift detected").
Trial clock (above the map): Play/Pause, a range slider for day 1..28, "Day 12 of 28",
 a "dose start" marker at day 8 on the slider track; playing advances one day every
 2.1 s (~60 s for the trial); 2x toggle. Default: day 15, paused.
Right panel (stacks under the map below 1024px):
 - Site cards for S01/S02/S03 for the current day: "worn today: 12 of 13", drift count,
   with StatusPill-style chips (pass/watch/held tokens + icons). Real counts from clock.
 - Selected participant (default P-07): id, site, metric tabs (HRV, Resting HR, Skin temp,
   Respiratory rate) showing PulseStrip for that metric up to the current day (fetch
   series for the current day; refetch when the day changes, debounced 250 ms), and a
   context line from public metrics: "Hampden County: 38.4% of adults sleep under 7 hours
   (CDC PLACES 2022)" for the participant's site county.
 - A button "See how the AI's report about P-07 was checked" linking to #/checkpoint.
States: loading text, error text with the server message, nothing invented.
When finished, list every file you created or changed and stop.
