Task T05: the de-identified, time-correct payload the AI agent will receive, with tests.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Read trialpulse/core/models.py, trialpulse/data/generator.py and
trialpulse/signals/detect.py first. stdlib + pydantic only.

Files you may create: trialpulse/agent/__init__.py, trialpulse/agent/deid.py,
tests/test_deid.py. Do not touch any other file.

Why: the AI drafts safety reports for a BLINDED medical monitor. It must never see the
treatment arm, and it should see no identifying or location detail. It may only see
records that were knowable at the report time.

trialpulse/agent/deid.py:
  ALLOWED_READING_FIELDS = ("record_id", "kind", "name", "value", "unit", "event_time",
                            "recorded_at", "source")
  scrub_text(text: str) -> str: replace e-mail addresses with "[email]", phone numbers
    (7+ digits with optional spaces, dashes, dots, parentheses, leading +) with "[phone]",
    and dates written like 1990-05-17 or 05/17/1990 with "[date]". Leave other text as is.
  build_payload(trial, participant_id: str, as_of: datetime, signals: list[Signal],
                lookback_days: int = 14) -> dict:
    {
      "participant_id": participant_id,
      "as_of": as_of.isoformat(),
      "trial_day": <trial day of as_of>,
      "dose_start_day": <participant.dose_start_day>,
      "readings": [ {field: value for field in ALLOWED_READING_FIELDS} ... ],
      "signals": [ signal.model_dump(mode="json") for signals of this participant ],
    }
    readings = this participant's readings with recorded_at <= as_of and trial day in
    [as_of trial day - lookback_days + 1, as_of trial day] PLUS all pre-dose readings
    (days 1-7) known as of as_of, sorted by (event_time, record_id), datetimes as ISO
    strings, symptom_note values passed through scrub_text. Never include arm,
    site_id, home_county, enrolled_at, or any site city name.
    Raise ValueError for an unknown participant_id.

tests/test_deid.py (use generate(7) and detect from trialpulse.signals.detect):
 - the JSON dump of build_payload(..., "P-07", day 15 23:00, signals) contains none of:
   "arm", "site_id", "home_county", "Boston", "Worcester", "Springfield", "Suffolk",
   "Hampden".
 - every reading in the payload has exactly ALLOWED_READING_FIELDS as keys.
 - every reading has recorded_at <= as_of; for P-15 at day 21 08:00, no day-20 reading
   appears (they are recorded on day 22), and pre-dose readings do appear.
 - only P-07's signals are included, and P-07's drift signals are present.
 - scrub_text: "call 617-555-0199 or mail jane.doe@example.com, born 05/17/1990" becomes
   "call [phone] or mail [email], born [date]".
 - unknown participant raises ValueError.

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
