"""Tests for the FastAPI backend (Task T13). No network.

TP_AUDIT_PATH and TP_VALIDATION_DIR are pointed at tmp paths via monkeypatch before
the cached state is (re)built, so the tests never touch the real audit log or the
recorded runs on disk. A couple of small, valid validation records are written into a
tmp folder for the recorded-run and audit-seeding paths.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


def _fake_record(case_id: str, participant_id: str, day: int, fault):
    """A minimal but schema-valid recorded run for one draft/gate round."""
    report_id = f"RPT-{participant_id}-{case_id}-1"
    as_of = "2026-10-05T23:00:00"
    report = {
        "report_id": report_id,
        "participant_id": participant_id,
        "signal_ids": [],
        "as_of": as_of,
        "window_start": "2026-09-21T07:00:00",
        "window_end": as_of,
        "claims": [
            {
                "claim_id": f"{report_id}-C1",
                "type": "value",
                "text": "Resting heart rate was recorded during the window.",
                "cited_record_ids": [f"{participant_id}-d{day:02d}-resting_hr"],
            }
        ],
        "abstained": False,
        "model_id": "fake-model-1",
        "prompt_version": "tp-report-1",
    }
    gate = {
        "report_id": report_id,
        "verdict": "pass",
        "checks": [
            {
                "dimension": f"temporal_consistency:{report_id}-C1",
                "passed": True,
                "explanation": "passed",
            }
        ],
        "pulseeval_commit": "db4e475",
    }
    return {
        "case_id": case_id,
        "participant_id": participant_id,
        "day": day,
        "fault": fault,
        "ground_truth_note": "fake",
        "raw": {
            "report": report,
            "gate": gate,
            "verdict": "pass",
            "failed": [],
        },
        "pipeline": {
            "drafts": [report],
            "gates": [gate],
            "requests": [],
            "replies": [],
            "final_verdict": "pass",
            "rounds": 1,
        },
        "models_used": ["fake-model-1"],
    }


@pytest.fixture()
def client(tmp_path, monkeypatch):
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()
    for rec in (
        _fake_record("v01", "P-07", 15, None),
        _fake_record("v02", "P-20", 15, "causal_overclaim"),
    ):
        with open(validation_dir / f"{rec['case_id']}.json", "w", encoding="utf-8") as fh:
            json.dump(rec, fh)

    audit_file = tmp_path / "audit.sqlite3"
    monkeypatch.setenv("TP_AUDIT_PATH", str(audit_file))
    monkeypatch.setenv("TP_VALIDATION_DIR", str(validation_dir))
    monkeypatch.delenv("TP_LIVE_MODE", raising=False)

    from trialpulse.api import state as app_state
    from trialpulse.api.app import app

    app_state.clear_state()
    yield TestClient(app)
    app_state.clear_state()


def test_health_replay_by_default(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["mode"] == "replay"


def test_trial_blinding(client):
    r_monitor = client.get("/api/trial", headers={"X-Role": "monitor"})
    assert r_monitor.status_code == 200
    body = r_monitor.json()
    assert len(body["participants"]) == 40
    assert all("arm" not in p for p in body["participants"])

    r_safety = client.get("/api/trial", headers={"X-Role": "safety_reviewer"})
    body_safety = r_safety.json()
    assert all("arm" in p for p in body_safety["participants"])


def test_clock_days_and_drift(client):
    r = client.get("/api/clock")
    assert r.status_code == 200
    days = r.json()["days"]
    assert len(days) == 28

    def drift_for(day_index, pid):
        rows = days[day_index - 1]["participants"]
        row = next(p for p in rows if p["participant_id"] == pid)
        return row["drift"]

    assert drift_for(15, "P-07") is True
    assert drift_for(9, "P-07") is False


def test_series_points_bands_and_404(client):
    r = client.get("/api/participants/P-07/series", params={"day": 15})
    assert r.status_code == 200
    body = r.json()
    assert body["metrics"]["resting_hr"]  # non-empty list of points
    assert "resting_hr" in body["bands"]

    r404 = client.get("/api/participants/P-99/series", params={"day": 15})
    assert r404.status_code == 404


def test_series_late_sync_no_day20_point(client):
    r = client.get("/api/participants/P-15/series", params={"day": 21})
    assert r.status_code == 200
    rhr = r.json()["metrics"].get("resting_hr", [])
    assert all(point["day"] != 20 for point in rhr)


def test_runs_list_and_missing(client):
    r = client.get("/api/runs")
    assert r.status_code == 200
    rows = r.json()
    case_ids = [row["case_id"] for row in rows]
    assert case_ids == ["v01", "v02"]

    r404 = client.get("/api/runs/missing")
    assert r404.status_code == 404


def test_run_recorded_flag(client):
    r = client.get("/api/runs/v01")
    assert r.status_code == 200
    assert r.json()["recorded"] is True


def test_live_report_409_in_replay(client):
    r = client.post(
        "/api/live/report",
        json={"participant_id": "P-07", "day": 15, "fault": None},
    )
    assert r.status_code == 409


def test_sign_roles_and_reason(client):
    report_id = "RPT-P-07-v01-1"

    # monitor appends an approved entry.
    r = client.post(
        "/api/audit/sign",
        headers={"X-Role": "monitor"},
        json={
            "report_id": report_id,
            "decision": "approved",
            "reason": "looks complete",
            "signer": "Dr. Monitor",
        },
    )
    assert r.status_code == 200
    assert r.json()["action"] == "approved"

    # coordinator may not sign.
    r403 = client.post(
        "/api/audit/sign",
        headers={"X-Role": "coordinator"},
        json={
            "report_id": report_id,
            "decision": "approved",
            "reason": "x",
            "signer": "Coord",
        },
    )
    assert r403.status_code == 403

    # empty reason is rejected.
    r_empty = client.post(
        "/api/audit/sign",
        headers={"X-Role": "monitor"},
        json={
            "report_id": report_id,
            "decision": "approved",
            "reason": "",
            "signer": "Dr. Monitor",
        },
    )
    assert r_empty.status_code in (400, 422)


def test_tamper_then_verify_fails(client):
    # Seeded audit entries exist; sign one more so there is something to tamper.
    client.post(
        "/api/audit/sign",
        headers={"X-Role": "monitor"},
        json={
            "report_id": "RPT-P-07-v01-1",
            "decision": "approved",
            "reason": "looks complete",
            "signer": "Dr. Monitor",
        },
    )
    entries = client.get("/api/audit").json()
    assert entries
    target = entries[0]["entry_id"]

    r = client.post("/api/audit/tamper", json={"entry_id": target})
    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_no_arm_substring_for_monitor(client):
    paths = [
        ("/api/trial", {"X-Role": "monitor"}, None),
        ("/api/clock", {"X-Role": "monitor"}, None),
        ("/api/runs", {"X-Role": "monitor"}, None),
        ("/api/runs/v01", {"X-Role": "monitor"}, None),
        ("/api/negative-control/v01", {"X-Role": "monitor"}, None),
        ("/api/metrics", {"X-Role": "monitor"}, None),
        ("/api/signals", {"X-Role": "monitor"}, {"day": 15}),
        ("/api/participants/P-07/series", {"X-Role": "monitor"}, {"day": 15}),
    ]
    for path, headers, params in paths:
        r = client.get(path, headers=headers, params=params)
        assert r.status_code == 200, path
        assert '"arm"' not in r.text, path
