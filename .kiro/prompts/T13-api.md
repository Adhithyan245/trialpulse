Task T13: the FastAPI backend the front end uses (replay mode by default). With tests.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Read trialpulse/data/generator.py, trialpulse/data/trials.py, trialpulse/signals/detect.py,
trialpulse/signals/baseline.py, trialpulse/gate/evidence.py, trialpulse/gate/validation.py,
trialpulse/gate/negative_control.py and trialpulse/api/audit.py first.

Files you may create: trialpulse/api/app.py, trialpulse/api/state.py, tests/test_api.py.
Nothing else. FastAPI + stdlib only (fastapi.testclient works; httpx is installed).

Roles come from the request header "X-Role": "monitor" (default), "coordinator",
"safety_reviewer". The treatment arm is returned ONLY for safety_reviewer; every other
response is blinded (no "arm" key anywhere).

trialpulse/api/state.py: a lazily built, cached AppState (functools.lru_cache):
  trial = generate(7); bands = personal_bands(trial); public metrics from
  data/derived/metrics_public.json if present else build_public_metrics();
  validation metrics from data/derived/metrics_validation.json if present else None;
  clock = precomputed per trial day 1..28 (as_of = day 23:00): for each participant
  {participant_id, site_id, resting_hr (latest known that day or None), worn (bool: has a
  resting_hr reading that day), drift (bool: any drift signal as of that day), non_wear
  (bool), diary_conflict (bool)}; audit = AuditLog(path from env TP_AUDIT_PATH, default
  data/derived/audit.sqlite3). On first build, if the audit log is empty, seed it by
  calling record_loop for every recorded validation run (LoopResult.model_validate on the
  record's pipeline part: drafts, gates, requests, replies, final_verdict), using each
  run's first draft as_of as ts.

trialpulse/api/app.py: app = FastAPI(title="TrialPulse"). All routes under /api:
  GET  /api/health -> {"ok": true, "mode": "replay" | "live"} (live when env
       TP_LIVE_MODE == "1").
  GET  /api/trial -> {"days": 28, "dose_start_day": 8, "sites": [{site_id, city,
       county}], "participants": [{participant_id, site_id} (+ "arm" for
       safety_reviewer)], "synthetic": true}
  GET  /api/clock -> {"days": [{"day": d, "participants": [...]}]} (the precomputed clock)
  GET  /api/signals?day=N -> detect(trial, as_of(N)) dumped
  GET  /api/participants/{pid}/series?day=N -> {"participant_id", "day", "metrics":
       {metric: [{"day", "value", "record_id", "recorded_at"}]} for readings known as of
       day N 23:00, "bands": bands[pid], "diary": [...fatigue and symptom_note rows]};
       404 for an unknown pid.
  GET  /api/runs -> [{case_id, participant_id, day, fault, raw_verdict, final_verdict,
       rounds, models_used}] from data/derived/validation/*.json (sorted by case_id)
  GET  /api/runs/{case_id} -> the recorded run (validation.replay); 404 if missing.
       Responses include "recorded": true so the UI can label "Recorded run".
  GET  /api/negative-control/{case_id} -> negative_control_summary for the recorded run's
       final draft (blind-safe; never the participant's arm)
  GET  /api/metrics -> {"public": ..., "validation": ...}
  POST /api/live/report {participant_id, day, fault|null} -> only when live mode, else
       409 {"detail": "live mode is off; showing recorded runs"}; runs run_loop with
       GeminiModel(); on LLMError returns 503 with the message (never a fake result).
  GET  /api/audit?report_id= -> entries;  GET /api/audit/verify -> verify()
  POST /api/audit/sign {report_id, decision, reason, signer} -> uses the X-Role
       (monitor or safety_reviewer only, else 403) and the latest draft with that
       report_id found in the recorded runs (404 if none); returns the new entry.
  POST /api/audit/tamper {entry_id} -> tamper_for_demo on that entry (demo only; returns
       the verify() result afterwards).
  If the folder web/dist exists, mount it at "/" with StaticFiles(html=True) AFTER the
  API routes. Add CORSMiddleware allowing http://localhost:5173.

tests/test_api.py (TestClient; set TP_AUDIT_PATH to a tmp file via monkeypatch before
importing/clearing the cached state; write 1-2 small fake validation records into a tmp
validation folder and point the state at it via an env var TP_VALIDATION_DIR that state.py
honors; no network):
 - /api/health ok and mode "replay" by default.
 - /api/trial has 40 participants and no "arm" for monitor; has "arm" for safety_reviewer.
 - /api/clock has 28 days; on day 15, P-07 has drift true; on day 9, P-07 drift false.
 - /api/participants/P-07/series?day=15 returns resting_hr points and bands; unknown
   pid -> 404; P-15 series at day 21 contains no day-20 point (late sync) — use day 21 and
   check no point with day 20 for resting_hr.
 - /api/runs lists the fake records; /api/runs/missing -> 404.
 - POST /api/live/report in replay mode -> 409.
 - sign as monitor appends an approved entry; as coordinator -> 403; empty reason -> 422
   or 400; tamper then verify -> ok false.
 - no response body for role monitor contains the substring "\"arm\"".

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
