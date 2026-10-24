"""Tests for the "Try to fool the checkpoint" backend (Task T23). No network, no LLM.

The judge picks one of four scenarios and types a short claim; :func:`run` turns the
typed text into a rule-labelled :class:`Report` with real citations and runs the same
reliability gate the AI drafts go through. These tests use the deterministic demo trial
(``generate(7)``). The API-route tests reuse the same env / tmp-path setup as
``tests/test_api.py`` so they never touch the real audit log or recorded runs.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from trialpulse.data.generator import generate
from trialpulse.gate.tryit import MAX_TEXT, build_report, run


def test_causal_overclaim_held_and_cites_only_p07_hrv():
    """A bare "the drug caused the HRV drop" claim is held by causal_restraint, and
    the claim cites only P-07 hrv_rmssd readings knowable as of day 15."""
    trial = generate(7)
    text = "The study drug caused P-07's HRV drop."

    out = run(trial, "P-07", 15, text)

    assert out["gate"]["verdict"] == "hold"

    # A causal_restraint check is present and fails.
    causal = [
        c for c in out["gate"]["checks"]
        if c["dimension"].startswith("causal_restraint")
    ]
    assert causal, [c["dimension"] for c in out["gate"]["checks"]]
    assert any(c["passed"] is False for c in causal)

    # The single claim cites only P-07 hrv_rmssd readings known as of day 15.
    report = out["report"]
    assert len(report["claims"]) == 1
    cited = report["claims"][0]["cited_record_ids"]
    assert cited, "the claim must cite at least one reading"
    by_id = {r.record_id: r for r in trial.readings}
    as_of = build_report(trial, "P-07", 15, text).as_of
    for rid in cited:
        assert rid in by_id, rid
        reading = by_id[rid]
        assert reading.participant_id == "P-07"
        assert reading.name == "hrv_rmssd"
        assert reading.recorded_at <= as_of


def test_recompute_matches_cited_value_passes():
    """A value claim whose number reproduces the cited reading passes recompute and the
    whole verdict is pass."""
    trial = generate(7)
    text = "HRV fell to 51.6 ms on day 12."

    out = run(trial, "P-07", 15, text)

    recompute = [
        c for c in out["gate"]["checks"]
        if c["dimension"].startswith("recompute")
    ]
    assert recompute, [c["dimension"] for c in out["gate"]["checks"]]
    assert all(c["passed"] is True for c in recompute)
    assert out["gate"]["verdict"] == "pass"


def test_missing_data_check_fails_for_false_completeness():
    """A "data complete across all days" claim for P-06 day 28 trips the missing_data
    check (the window is not fully covered)."""
    trial = generate(7)
    text = "Data was complete across all days."

    out = run(trial, "P-06", 28, text)

    missing = [
        c for c in out["gate"]["checks"]
        if c["dimension"].startswith("missing_data")
    ]
    assert missing, [c["dimension"] for c in out["gate"]["checks"]]
    assert any(c["passed"] is False for c in missing)


def test_text_too_long_raises():
    trial = generate(7)
    text = "x" * (MAX_TEXT + 1)
    with pytest.raises(ValueError):
        build_report(trial, "P-07", 15, text)
    with pytest.raises(ValueError):
        run(trial, "P-07", 15, text)


def test_unknown_participant_raises():
    trial = generate(7)
    with pytest.raises(ValueError):
        run(trial, "P-99", 15, "HRV fell on day 12.")


def test_day_out_of_range_raises():
    trial = generate(7)
    with pytest.raises(ValueError):
        run(trial, "P-07", 0, "HRV fell on day 12.")
    with pytest.raises(ValueError):
        run(trial, "P-07", 29, "HRV fell on day 12.")


# --------------------------------------------------------------------------- #
# API route (same env / tmp-path setup as tests/test_api.py)
# --------------------------------------------------------------------------- #
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
        "raw": {"report": report, "gate": gate, "verdict": "pass", "failed": []},
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

    monkeypatch.setenv("TP_AUDIT_PATH", str(tmp_path / "audit.sqlite3"))
    monkeypatch.setenv("TP_VALIDATION_DIR", str(validation_dir))
    monkeypatch.setenv("TP_CLOCK_CACHE", str(tmp_path / "clock.json"))
    monkeypatch.delenv("TP_LIVE_MODE", raising=False)

    from trialpulse.api import state as app_state
    from trialpulse.api.app import app

    app_state.clear_state()
    yield TestClient(app)
    app_state.clear_state()


def test_route_returns_200_for_valid_body(client):
    r = client.post(
        "/api/gate/try",
        json={
            "participant_id": "P-07",
            "day": 15,
            "text": "The study drug caused P-07's HRV drop.",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "report" in body
    assert "gate" in body
    assert "negative_control" in body
    assert body["gate"]["verdict"] in ("pass", "hold")


def test_route_returns_422_for_empty_text(client):
    r = client.post(
        "/api/gate/try",
        json={"participant_id": "P-07", "day": 15, "text": ""},
    )
    assert r.status_code == 422
