Task T02: the seeded synthetic trial generator, with tests.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Everything you need is below and in trialpulse/core/models.py (read it first).

Files you may create: trialpulse/data/__init__.py, trialpulse/data/generator.py,
tests/test_generator.py. Do not touch any other file. numpy and the stdlib only.

API (trialpulse/data/generator.py):
  TRIAL_START = datetime(2026, 9, 21)   # trial day 1; day d is TRIAL_START + (d-1) days
  N_DAYS = 28; DOSE_START_DAY = 8        # days 1-7 are the pre-dose baseline
  SITES = {"S01": ("Boston", "Suffolk"), "S02": ("Worcester", "Worcester"),
           "S03": ("Springfield", "Hampden")}
  class TrialData(pydantic BaseModel): participants: list[Participant],
      readings: list[Reading], ground_truth: dict   (JSON-serializable)
  def generate(seed: int = 7) -> TrialData
  def write_json(data: TrialData, path: str = "data/synthetic/trial.json") -> None
      (create parent folders; data.model_dump_json(indent=1))

Participants: 40, ids "P-01".."P-40", assigned round-robin to S01, S02, S03 (so P-01 S01,
P-02 S02, P-03 S03, ...). arm alternates "A","B" (P-01 A, P-02 B, ...). enrolled_at =
TRIAL_START, dose_start_day = 8, home_county from SITES. Use numpy default_rng(seed) only,
so the same seed gives identical output.

Daily wearable rows (one per metric per participant per day, when the device was worn):
  event_time = that day 07:00; recorded_at = event_time + 1..6 hours (random whole hours).
  record_id = f"{participant_id}-d{day:02d}-{name}"; source "wearable"; participant_id, site_id.
  kind: "physiological" for resting_hr, hrv_rmssd, spo2, skin_temp, respiratory_rate;
        "sleep" for sleep_hours; "activity" for strain and wear_minutes;
        "context" for user_calibrating.
  Per-participant baselines: resting_hr N(60, 6) bpm; hrv_rmssd lognormal median 55 ms
  (sigma 0.3); spo2 96.5-98.5 %; skin_temp 33.5-34.5 C; respiratory_rate 13-16 rpm;
  sleep_hours 6.5-8.0 h; strain 6-16. Daily noise: resting_hr +-2 (sd), hrv 8% (sd),
  spo2 0.4, skin_temp 0.15, respiratory_rate 0.4, sleep 0.5, strain 2.0. Round to 1 decimal
  (spo2 1 decimal, strain 1 decimal). wear_minutes on worn days 1250-1440 (int).
  user_calibrating = 0 on normal days. Units: bpm, ms, %, C, rpm, h, None, min, None.

Diary rows: each participant each day, name "fatigue", kind "subjective", source
"self_report", value baseline 2-4 (int, small noise), event_time and recorded_at = that day
20:00, record_id f"{pid}-d{day:02d}-fatigue". unit None.

Planned events (also record each in ground_truth["events"] as a dict with keys
type, participant_ids or site_id, start_day, end_day, detail):
 1. "adverse_pattern" for P-07 (arm A) and P-23 (arm B): from day 12 to day 28,
    resting_hr +8, hrv_rmssd x0.75, skin_temp +0.6, respiratory_rate +1.5; fatigue 7-8 on
    days 12-15. No symptom_note (the cause is unknown to the data on purpose).
 2. "site_non_wear" for S03: from day 9 to 28, each S03 participant-day is not worn with
    probability 0.30. On a not-worn day: emit only wear_minutes with a value 0-500 (int);
    emit no other wearable rows for that day (missing data stays missing). Diary unaffected.
    Store the exact list of (participant_id, day) not-worn pairs in
    ground_truth["non_wear_days"]. Make sure P-07 and P-23 are not S03 participants
    (they are not: P-07 is S01, P-23 is S02).
 3. "late_sync" for P-15: on days 20 and 21, recorded_at = event_time + 2 days.
 4. "diary_conflict" for P-31 (wearable normal): fatigue 9 on days 14-16 plus a
    "symptom_note" row on day 15 with value "completely exhausted" (kind "subjective",
    source "self_report", record_id f"P-31-d15-symptom_note", 20:00).
 5. "sparse_week" for P-02: on days 22-28 only days 24 and 27 have wearable rows; days 22
    and 23 emit only user_calibrating = 1 (kind "context"); days 25, 26, 28 emit nothing.
ground_truth["seed"] = seed.

tests/test_generator.py:
 - generate(7) twice gives identical model_dump_json(); generate(8) differs.
 - 40 participants; site and arm assignment exactly as specified.
 - every record_id is unique; every Reading validates (it is built from the models).
 - P-07 mean resting_hr over days 12-15 > its mean over days 1-7 + 6; same for P-23.
 - no participant other than P-07 and P-23 has a 4-day mean resting_hr more than 6 above
   their own days 1-7 mean (check every 4-day window).
 - for every (pid, day) in ground_truth["non_wear_days"], that day has a wear_minutes row
   with value < 600 and no resting_hr row; S03 has at least 25 such days.
 - P-15 day 20 and 21 rows have recorded_at - event_time == 2 days.
 - P-31 has the symptom_note on day 15 and fatigue 9 on days 14-16.
 - P-02 has resting_hr rows on exactly days 24 and 27 within days 22-28.
 - write_json to a tmp_path file round-trips through TrialData.model_validate_json.

Done when the reviewer's `.venv\Scripts\python -m pytest -q` passes. When finished, list
every file you changed and stop.
