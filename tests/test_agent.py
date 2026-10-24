"""Tests for the report agent (Task T06). No network calls."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from trialpulse.agent import deid, llm
from trialpulse.agent.llm import GeminiModel, LLMError
from trialpulse.agent.prompts import FAULTS, SYSTEM_PROMPT
from trialpulse.agent.report import DraftClaim, DraftReport, draft_report
from trialpulse.data.generator import TRIAL_START, generate
from trialpulse.signals.detect import detect


def _day_time(day: int, hour: int, minute: int = 0) -> datetime:
    return TRIAL_START + timedelta(days=day - 1) + timedelta(hours=hour, minutes=minute)


class FakeModel:
    """A JSONModel stand-in that returns a fixed DraftReport and records the
    system prompt it was asked with."""

    name = "fake-model-1"

    def __init__(self, draft: DraftReport) -> None:
        self._draft = draft
        self.last_system: str | None = None
        self.last_user: str | None = None

    def generate(self, system: str, user: str, schema):
        self.last_system = system
        self.last_user = user
        return self._draft


def _p07_setup():
    trial = generate(7)
    as_of = _day_time(15, 23)
    signals = detect(trial, as_of)
    payload = deid.build_payload(trial, "P-07", as_of, signals)
    real_ids = [r["record_id"] for r in payload["readings"]]
    assert real_ids, "expected readings for P-07"
    return trial, as_of, signals, real_ids


def test_draft_report_citations_filtered_and_claims_dropped():
    trial, as_of, signals, real_ids = _p07_setup()
    r0, r1 = real_ids[0], real_ids[1]

    draft = DraftReport(
        claims=[
            # Mix of a real and an invented citation: the invented one is dropped.
            DraftClaim(type="value", text="RHR elevated", cited_record_ids=[r0, "FAKE-1"]),
            DraftClaim(type="coverage", text="good wear", cited_record_ids=[r1]),
            # All citations invented: this whole claim is dropped.
            DraftClaim(type="assessment", text="made up", cited_record_ids=["FAKE-2", "FAKE-3"]),
        ],
        abstained=False,
    )
    model = FakeModel(draft)

    report = draft_report(trial, "P-07", as_of, signals, model)

    # Only two claims survive; the all-invented one is dropped.
    assert len(report.claims) == 2
    # Every surviving citation exists in the payload; invented ones are gone.
    all_cited = {rid for c in report.claims for rid in c.cited_record_ids}
    assert all_cited <= set(real_ids)
    assert "FAKE-1" not in all_cited
    assert report.claims[0].cited_record_ids == [r0]
    assert report.claims[1].cited_record_ids == [r1]
    # Claim ids are renumbered against surviving claims.
    assert report.claims[0].claim_id.endswith("-C1")
    assert report.claims[1].claim_id.endswith("-C2")
    assert report.participant_id == "P-07"
    assert report.window_end == as_of


def test_fault_appends_to_system_prompt_and_version():
    trial, as_of, signals, real_ids = _p07_setup()
    draft = DraftReport(
        claims=[DraftClaim(type="value", text="x", cited_record_ids=[real_ids[0]])],
        abstained=False,
    )
    model = FakeModel(draft)

    report = draft_report(trial, "P-07", as_of, signals, model, fault="causal_overclaim")

    assert model.last_system is not None
    assert model.last_system.endswith(FAULTS["causal_overclaim"])
    assert FAULTS["causal_overclaim"] in model.last_system
    assert report.prompt_version.endswith("+causal_overclaim")


def test_unknown_fault_raises():
    trial, as_of, signals, real_ids = _p07_setup()
    draft = DraftReport(
        claims=[DraftClaim(type="value", text="x", cited_record_ids=[real_ids[0]])],
        abstained=False,
    )
    model = FakeModel(draft)
    with pytest.raises(ValueError):
        draft_report(trial, "P-07", as_of, signals, model, fault="nope")


def test_system_prompt_has_no_causation_rule():
    assert "caus" not in SYSTEM_PROMPT.lower()


class _FakeResp:
    def __init__(self, parsed=None, text: str = "") -> None:
        self.parsed = parsed
        self.text = text


def test_gemini_retries_on_429_then_succeeds(monkeypatch):
    from google.genai import errors

    sleeps: list[float] = []

    good = DraftReport(claims=[], abstained=True)

    class _FakeModels:
        def __init__(self) -> None:
            self.calls = 0

        def generate_content(self, model, contents, config):
            self.calls += 1
            if self.calls == 1:
                raise errors.APIError(429, {"error": {"message": "rate"}})
            return _FakeResp(parsed=good)

    class _FakeClient:
        def __init__(self) -> None:
            self.models = _FakeModels()

    gm = GeminiModel(api_key="k", models=["m"], sleep=lambda s: sleeps.append(s))
    gm._client = _FakeClient()

    result = gm.generate("sys", "usr", DraftReport)
    assert result is good
    assert sleeps == [2]


def test_gemini_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(llm, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "m")
    with pytest.raises(LLMError):
        GeminiModel()


class _OneModel:
    """A fake ``client.models`` for a single named model whose behaviour is a
    callable: it either raises or returns a ``_FakeResp``."""

    def __init__(self, behaviours: dict) -> None:
        self._behaviours = behaviours
        self.calls: list[str] = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        return self._behaviours[model]()


def _make_client(behaviours: dict):
    class _Client:
        def __init__(self) -> None:
            self.models = _OneModel(behaviours)

    return _Client()


def test_gemini_falls_back_to_next_model_on_503(monkeypatch):
    from google.genai import errors

    sleeps: list[float] = []
    good = DraftReport(claims=[], abstained=True)

    def a_behaviour():
        raise errors.APIError(503, {"error": {"message": "high demand"}})

    def b_behaviour():
        return _FakeResp(parsed=good)

    client = _make_client({"a": a_behaviour, "b": b_behaviour})

    gm = GeminiModel(api_key="k", models=["a", "b"], sleep=lambda s: sleeps.append(s))
    gm._client = client

    # Before any call, name is the primary.
    assert gm.name == "a"

    result = gm.generate("sys", "usr", DraftReport)
    assert result is good
    assert gm.name == "b"
    # "a" retried with back-off 2 then 4, then moved on; "b" succeeded.
    assert sleeps == [2, 4]


def test_gemini_all_models_fail_lists_both(monkeypatch):
    from google.genai import errors

    sleeps: list[float] = []

    def a_behaviour():
        raise errors.APIError(503, {"error": {"message": "high demand"}})

    def b_behaviour():
        raise errors.APIError(504, {"error": {"message": "deadline"}})

    client = _make_client({"a": a_behaviour, "b": b_behaviour})

    gm = GeminiModel(api_key="k", models=["a", "b"], sleep=lambda s: sleeps.append(s))
    gm._client = client

    with pytest.raises(LLMError) as excinfo:
        gm.generate("sys", "usr", DraftReport)
    msg = str(excinfo.value)
    assert "a" in msg
    assert "b" in msg


def test_gemini_404_moves_on_without_sleeping(monkeypatch):
    from google.genai import errors

    sleeps: list[float] = []
    good = DraftReport(claims=[], abstained=True)

    def a_behaviour():
        raise errors.APIError(404, {"error": {"message": "no longer available"}})

    def b_behaviour():
        return _FakeResp(parsed=good)

    client = _make_client({"a": a_behaviour, "b": b_behaviour})

    gm = GeminiModel(api_key="k", models=["a", "b"], sleep=lambda s: sleeps.append(s))
    gm._client = client

    result = gm.generate("sys", "usr", DraftReport)
    assert result is good
    assert gm.name == "b"
    assert sleeps == []
