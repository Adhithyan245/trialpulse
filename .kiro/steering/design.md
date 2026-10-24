# Interface design (every screen follows this)
Product line on the landing screen: "The AI drafts. Deterministic checks verify. Humans decide."
The interface acts out the product instead of summarizing it in dashboard widgets.

Scenes
1. The trial, alive: 3D Massachusetts (MassGIS county outlines, extruded), one beacon per
   participant pulsing at that participant's resting heart rate. Amber halo when outside the
   personal band. Beacons go hollow/dark when the device is not worn. Trial clock: play and
   scrub, day 1 to 28 in about 60 seconds.
2. The checkpoint: a tunnel of 7 rings, one per PulseEval check. Claim cards fly through.
   A failed card stops inside its ring, turns red, and shows a plain-language reason.
   An evidence request flies from the ring to the participant's beacon; the reply flies back.
3. Sign and seal: the monitor signs with a reason; the report becomes a block on a linked
   chain. A tamper button edits an old block and the chain visibly breaks from there on.
4. How this was verified: per claim, the cited readings, the recomputed number next to the
   AI's number, and the pre-drug comparison.
5. Proof it works: validation scorecard, FDA credibility panel, trial finder (real data).

Rules
- Build each scene in 2D first, wired to real data; upgrade to 3D after. Every 3D scene sits
  in an error boundary that renders the 2D version if WebGL fails. Honor prefers-reduced-motion.
- All 3D shapes are generated in code. No model files.
- Fonts: IBM Plex Sans (UI), IBM Plex Mono (record IDs, timestamps, numbers, tabular-nums).
- Color tokens only (CSS variables, light and dark themes). Ink navigation, light working
  area, one teal accent. Status colors are separate from the accent: pass green, watch amber,
  held red, each always paired with an icon and a text label.
- Charts: personal band as a shaded area behind the line; missing days stay as gaps, never
  interpolated; diary entries as markers.
- A "Synthetic data" ribbon on every screen. Recorded runs are labelled "Recorded run";
  simulated participant replies are labelled "Simulated reply".
- Landing: one-sentence pitch, "Start the demo" button, role buttons (Monitor, Coordinator,
  Safety reviewer). No passwords. 5-step guided tour with Skip.
- Works at laptop and phone widths. Visible keyboard focus everywhere.
