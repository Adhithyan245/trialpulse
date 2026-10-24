Task T14-fix3: the pulse strip draws nothing (every y is NaN) and has a fixed width.

You cannot run shell commands or use the web in this project; the reviewer checks the
browser. File you may edit: web/src/scenes/checkpoint/PulseStrip.tsx, and the place in
Scene2Checkpoint.tsx that passes data into it if the bug is in what is passed. Nothing else.

What the reviewer measured in the browser (case v02, P-07, day 15): the SVG has
width="400" height="80" and no viewBox; its children are
  path d="M 30,NaN L 55.71,NaN L 81.43,NaN ..."  (band)
  path d="M 30 NaN L 55.71 NaN ..."              (line)
  circle cx=30 cy=NaN ...                        (dots)
  rect x=30 width=360 (change window) covering the whole strip.
So x works but every y is NaN. The API response it must read is exactly:
  GET /api/participants/P-07/series?day=15 ->
  {"participant_id":"P-07","day":15,
   "metrics":{"hrv_rmssd":[{"day":1,"value":77.1,"record_id":"P-07-d01-hrv_rmssd",
                            "recorded_at":"2026-09-21T10:00:00"}, ... 15 points],
              "resting_hr":[...], ...},
   "bands":{"hrv_rmssd":{"median":76,"lo":62.87,"hi":89.13,"q":2.46}, ...},
   "diary":[...]}
Find why y is NaN (likely reading the wrong field names, or computing min/max over
undefined) and fix it: y domain = min/max over the point values and band lo/hi, padded
10%; guard against an empty series (render "No readings yet").
Also:
 - Make the strip responsive: viewBox="0 0 400 80", width="100%", height auto
   (preserveAspectRatio="none" is not acceptable for the dots; keep aspect via viewBox).
 - The change window rect must span only from the first drift day (window start of the
   participant's drift: pass it in, or use the first day >= 8 whose value is outside the
   band in the metric's direction; hrv_rmssd deviates downward) to the last day.
 - Draw the dose-start tick at day 8 and label it "dose start".
When finished, list the files you changed and stop.
