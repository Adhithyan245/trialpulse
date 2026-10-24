Task T23: backend for "Try to fool the checkpoint": gate a claim a judge types, instantly,
with no LLM call.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Read trialpulse/core/models.py, trialpulse/gate/live.py, trialpulse/gate/negative_control.py,
trialpulse/agent/deid.py, trialpulse/signals/detect.py, trialpulse/api/app.py and
trialpulse/api/state.py first.

Files you may create: trialpulse/gate/tryit.py, tests/test_tryit.py. You may edit
trialpulse/api/app.py to add one route. Nothing else. No new dependencies.

trialpulse/gate/tryit.py
  EXAMPLES = the four scenarios the UI offers: P-07 day 15, P-20 day 15, P-06 day 28,
    P-31 day 16 (expose as a list of dicts {participant_id, day, label}).
  METRIC_WORDS: lowercase word-prefix -> metric: "hrv"/"rmssd"/"heart rate variab" ->
    hrv_rmssd; "resting heart"/"rhr"/"heart rate"/"pulse" -> resting_hr; "skin temp"/
    "temperature" -> skin_temp; "respirat"/"breath" -> respiratory_rate; "sleep" ->
    sleep_hours; "spo2"/"oxygen" -> spo2; "fatigue"/"tired"/"exhaust" -> fatigue;
    "wear"/"worn"/"device" -> wear_minutes. (Check longer phrases first.)
  build_report(trial, participant_id, day, text) -> Report:
    - text is trimmed, at most 600 characters (ValueError beyond), at least 8.
    - split into sentences (on . ! ? followed by space or end); at most 5 claims.
    - claim type per sentence: "relationship" if it matches the adapter's CAUSAL_CUE or
      the words associated/related/linked/correlat; "coverage" if it mentions complete,
      missing, gap, every day, all days, no data, coverage; "value" if it contains a
      number followed by a unit (bpm, ms, %, C, rpm, h, min); otherwise "assessment".
    - citations: as_of = day 23:00. Metrics = those named in the sentence (or resting_hr
      if none). If the sentence names "day N", cite that participant's readings of those
      metrics on day N known as of as_of; otherwise the last 4 trial days up to the as_of
      day. If no reading exists, cite the participant's most recent known reading of that
      metric. Never cite unknown or future records.
    - Report: report_id f"TRY-{participant_id}-d{day}", model_id "typed by you",
      prompt_version "try-it", window_start = TRIAL_START, window_end = as_of,
      abstained False, signal_ids from detect(trial, as_of) for that participant.
  run(trial, participant_id, day, text) -> dict: {"report": report dump,
    "gate": gate_report(...) dump, "negative_control": negative_control_summary(...) if
    any claim links to the drug else null}. Unknown participant or day outside 1..28 ->
    ValueError.
app.py: POST /api/gate/try {participant_id, day, text} -> run(...) using the cached trial
  from state.py; ValueError -> 422 with the message. Works in replay mode (no Gemini).
tests/test_tryit.py:
 - "The study drug caused P-07's HRV drop." for P-07 day 15 -> verdict hold with a failing
   causal_restraint check; the claim cites only P-07 hrv_rmssd readings known as of day 15.
 - "HRV fell to 51.6 ms on day 12." for P-07 day 15 -> the recompute check passes and the
   verdict is pass.
 - "Data was complete across all days." for P-06 day 28 -> a missing_data check fails.
 - text over 600 characters -> ValueError; unknown participant -> ValueError.
 - the API route returns 200 for a valid body and 422 for an empty text (TestClient, using
   the same env/tmp-path setup as tests/test_api.py).
When finished, list every file you changed and stop.
