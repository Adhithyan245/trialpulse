"""The FastAPI backend the front end uses (Task T13).

Replay mode by default: the UI plays back the recorded validation runs and the
precomputed trial clock. Live mode (env ``TP_LIVE_MODE == "1"``) additionally lets
``POST /api/live/report`` run the real evidence loop with Gemini.

Roles come from the ``X-Role`` header: ``monitor`` (default), ``coordinator`` or
``safety_reviewer``. The treatment arm is returned ONLY for ``safety_reviewer``;
every other response is blinded.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from trialpulse.agent.llm import GeminiModel, LLMError
from trialpulse.api import state as app_state
from trialpulse.api.audit import sign as audit_sign
from trialpulse.api.audit import tamper_for_demo
from trialpulse.core.models import Report
from trialpulse.data.generator import DOSE_START_DAY, N_DAYS, SITES
from trialpulse.gate.live import negative_control_summary
from trialpulse.signals.baseline import trial_day
from trialpulse.signals.detect import detect

VALID_ROLES = ("monitor", "coordinator", "safety_reviewer")

app = FastAPI(title="TrialPulse")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _role(x_role: str | None) -> str:
    """Resolve the request role; default monitor, unknown roles treated as monitor."""
    if x_role in VALID_ROLES:
        return x_role
    return "monitor"


def _live_mode() -> bool:
    return os.environ.get("TP_LIVE_MODE") == "1"


# --------------------------------------------------------------------------- #
# Trial / clock / signals
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "mode": "live" if _live_mode() else "replay"}


@app.get("/api/trial")
def trial(x_role: str | None = Header(default=None)) -> dict:
    role = _role(x_role)
    st = app_state.get_state()

    sites = [
        {"site_id": sid, "city": city, "county": county}
        for sid, (city, county) in SITES.items()
    ]

    participants = []
    for p in st.trial.participants:
        row = {"participant_id": p.participant_id, "site_id": p.site_id}
        if role == "safety_reviewer":
            row["arm"] = p.arm
        participants.append(row)

    return {
        "days": N_DAYS,
        "dose_start_day": DOSE_START_DAY,
        "sites": sites,
        "participants": participants,
        "synthetic": True,
    }


@app.get("/api/clock")
def clock() -> dict:
    return app_state.get_state().clock


@app.get("/api/signals")
def signals(day: int) -> list[dict]:
    st = app_state.get_state()
    found = detect(st.trial, app_state.as_of(day))
    return [s.model_dump(mode="json") for s in found]


@app.get("/api/participants/{pid}/series")
def participant_series(pid: str, day: int) -> dict:
    st = app_state.get_state()
    if pid not in st.bands:
        raise HTTPException(status_code=404, detail="unknown participant")

    instant = app_state.as_of(day)

    # Numeric wearable readings known as of the instant, grouped by metric.
    metrics: dict[str, list[dict]] = {}
    diary: list[dict] = []
    for r in st.trial.readings:
        if r.participant_id != pid:
            continue
        if r.recorded_at > instant:
            continue
        d = trial_day(r.event_time)
        if r.name in ("fatigue", "symptom_note"):
            diary.append(
                {
                    "day": d,
                    "name": r.name,
                    "value": r.value,
                    "record_id": r.record_id,
                    "recorded_at": r.recorded_at.isoformat(),
                }
            )
            continue
        if not isinstance(r.value, (int, float)):
            continue
        metrics.setdefault(r.name, []).append(
            {
                "day": d,
                "value": float(r.value),
                "record_id": r.record_id,
                "recorded_at": r.recorded_at.isoformat(),
            }
        )

    for points in metrics.values():
        points.sort(key=lambda row: row["day"])
    diary.sort(key=lambda row: (row["day"], row["name"]))

    return {
        "participant_id": pid,
        "day": day,
        "metrics": metrics,
        "bands": st.bands[pid],
        "diary": diary,
    }


# --------------------------------------------------------------------------- #
# Recorded runs
# --------------------------------------------------------------------------- #
def _run_summary(record: dict) -> dict:
    return {
        "case_id": record["case_id"],
        "participant_id": record["participant_id"],
        "day": record["day"],
        "fault": record["fault"],
        "raw_verdict": record["raw"]["verdict"],
        "final_verdict": record["pipeline"]["final_verdict"],
        "rounds": record["pipeline"]["rounds"],
        "models_used": record["models_used"],
    }


@app.get("/api/runs")
def runs() -> list[dict]:
    st = app_state.get_state()
    return [_run_summary(r) for r in st.runs]


@app.get("/api/runs/{case_id}")
def run(case_id: str) -> dict:
    st = app_state.get_state()
    record = st.runs_by_case.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown run")
    out = dict(record)
    out["recorded"] = True
    return out


@app.get("/api/negative-control/{case_id}")
def negative_control(case_id: str) -> dict:
    st = app_state.get_state()
    record = st.runs_by_case.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown run")
    final_draft = Report.model_validate(record["pipeline"]["drafts"][-1])
    signals = detect(st.trial, final_draft.as_of)
    summary = negative_control_summary(st.trial, final_draft, signals)
    summary["recorded"] = True
    return summary


@app.get("/api/metrics")
def metrics() -> dict:
    st = app_state.get_state()
    return {"public": st.public_metrics, "validation": st.validation_metrics}


# --------------------------------------------------------------------------- #
# Live mode
# --------------------------------------------------------------------------- #
@app.post("/api/live/report")
def live_report(body: dict) -> dict:
    if not _live_mode():
        raise HTTPException(
            status_code=409, detail="live mode is off; showing recorded runs"
        )

    from trialpulse.gate.evidence import run_loop

    st = app_state.get_state()
    participant_id = body["participant_id"]
    day = int(body["day"])
    fault = body.get("fault")

    try:
        loop = run_loop(
            st.trial,
            participant_id,
            app_state.as_of(day),
            GeminiModel(),
            fault=fault,
        )
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return loop.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #
@app.get("/api/audit")
def audit_entries(report_id: str | None = None) -> list[dict]:
    st = app_state.get_state()
    entries = st.audit.entries(report_id=report_id)
    return [e.model_dump(mode="json") for e in entries]


@app.get("/api/audit/verify")
def audit_verify() -> dict:
    return app_state.get_state().audit.verify()


def _latest_draft(runs: list[dict], report_id: str) -> Report | None:
    """The latest recorded draft with ``report_id`` across all recorded runs."""
    found: Report | None = None
    for record in runs:
        for draft in record["pipeline"]["drafts"]:
            if draft["report_id"] == report_id:
                found = Report.model_validate(draft)
    return found


@app.post("/api/audit/sign")
def audit_sign_endpoint(
    body: dict, x_role: str | None = Header(default=None)
) -> dict:
    role = _role(x_role)
    if role not in ("monitor", "safety_reviewer"):
        raise HTTPException(status_code=403, detail="role may not sign")

    st = app_state.get_state()
    report_id = body["report_id"]
    decision = body["decision"]
    reason = body.get("reason", "")
    signer = body["signer"]

    report = _latest_draft(st.runs, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="unknown report_id")

    from datetime import datetime

    try:
        entry = audit_sign(
            st.audit,
            report,
            actor_role=role,
            signer=signer,
            decision=decision,
            reason=reason,
            ts=datetime.now(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return entry.model_dump(mode="json")


@app.post("/api/audit/tamper")
def audit_tamper(body: dict) -> dict:
    st = app_state.get_state()
    entry_id = body["entry_id"]
    tamper_for_demo(
        st.audit, entry_id, {"tampered": True, "demo": True}
    )
    return st.audit.verify()


# --------------------------------------------------------------------------- #
# Static front end (mounted last, after the API routes).
# --------------------------------------------------------------------------- #
if os.path.isdir("web/dist"):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory="web/dist", html=True), name="web")
