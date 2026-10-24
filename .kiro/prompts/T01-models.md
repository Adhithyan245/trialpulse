Task T01: the data contracts as pydantic v2 models, with tests.

Files you may create: trialpulse/__init__.py, trialpulse/core/__init__.py,
trialpulse/core/models.py, tests/__init__.py, tests/test_models.py, pyproject.toml
Do not touch any other file. Do not add dependencies beyond the stack in tech.md.

pyproject.toml: project name "trialpulse", version 0.1.0, requires-python >=3.11,
dependencies: pydantic>=2, numpy, pandas, pyarrow, fastapi, uvicorn, google-genai,
python-dotenv, "pulseeval @ git+https://github.com/Adhithyan245/PulseEval@db4e475".
Optional dev: pytest. setuptools build backend; packages found under the repo root
(include trialpulse*). [tool.pytest.ini_options] testpaths = ["tests"].

trialpulse/core/models.py must define exactly these models (pydantic v2, use Literal for
the listed string choices, datetime for times, all fields required unless marked optional):

Reading: subclass of pulseeval.timeline.Record (import it; do not copy it) adding
  participant_id: str, site_id: str.
  Allowed `name` values for wearable rows (WHOOP API v2 daily summaries, one row per
  participant per day): resting_hr (bpm), hrv_rmssd (ms), spo2 (%), skin_temp (C),
  respiratory_rate (rpm), sleep_hours (h), strain (0-21), wear_minutes (min),
  user_calibrating (value 0 or 1). Diary rows: kind="subjective", source="self_report",
  name "fatigue" (value 0-10) or "symptom_note" (value is text).
  Put the allowed names in a module-level frozenset WEARABLE_METRICS and DIARY_METRICS and
  validate `name` against their union.
Participant: participant_id, site_id, arm Literal["A","B"], enrolled_at: datetime,
  dose_start_day: int (trial day the study drug starts), home_county: str.
Signal: signal_id, participant_id, type Literal["drift","non_wear","diary_conflict"],
  metric: str, window_start: datetime, window_end: datetime, z_score: float | None,
  record_ids: list[str].
Claim: claim_id, type Literal["value","coverage","assessment","relationship","certainty"],
  text: str, cited_record_ids: list[str] (must be non-empty: an uncited claim is invalid).
Report: report_id, participant_id, signal_ids: list[str], as_of: datetime,
  window_start: datetime, window_end: datetime, claims: list[Claim], abstained: bool,
  model_id: str, prompt_version: str.
EvidenceRequest: request_id, report_id, participant_id, failed_dimension: str,
  kind Literal["symptom_checkin","wear_reminder","followup_question","predose_comparison",
  "trial_level_alert"], question_text: str, sent_at: datetime,
  reply_record_id: str | None = None, status Literal["open","answered"] = "open".
GateCheck: dimension: str, passed: bool, explanation: str.
GateResult: report_id, verdict Literal["pass","hold"], checks: list[GateCheck],
  pulseeval_commit: str.
AuditEntry: entry_id, ts: datetime, actor_role Literal["system","monitor","coordinator",
  "safety_reviewer"], action Literal["drafted","gated","evidence_requested",
  "evidence_received","approved","rejected","redraft_requested"], report_id: str,
  details_json: str, prev_hash: str, entry_hash: str.

tests/test_models.py (pytest): for every model, a valid instance round-trips through
model_dump_json / model_validate_json unchanged; a Reading with an unknown name is rejected;
a Claim with empty cited_record_ids is rejected; a Reading is an instance of
pulseeval.timeline.Record; invalid Literal values are rejected for Signal.type and
AuditEntry.action.

Done when: `.venv\Scripts\python -m pytest -q` passes.
Out of scope: generator, signals, any other module. When finished, list every file you
changed and stop.
