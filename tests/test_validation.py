"""Tests for the validation suite (Task T12). No network calls.

A FakeModel (as in tests/test_evidence.py) stands in for Gemini, so the suite runs
offline. run_suite writes one JSON file per finished case, resumes finished cases
without calling the model again, and stops without a record when the model raises an
LLMError. summarize computes the before/after counts from hand-made records, and
replay loads back what run_suite wrote.
"""

from __future__ import annotations

import json
import re

from trialpulse.agent.llm import LLMError
from trialpulse.agent.report import DraftClaim, DraftReport
from trialpulse.gate import validation


class FakeModel:
    """Returns a drug-linking claim the gate holds on the first call per report, then
    a clean claim citing the reply record id found in the user prompt. Counts calls."""

    name = "fake-validation-model-1"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, system: str, user: str, schema):
        self.calls += 1
        ids = re.findall(r'"record_id":"([^"]+)"', user)

        reply_ids = [rid for rid in ids if "-reply-" in rid]
        if reply_ids:
            return DraftReport(
                claims=[
                    DraftClaim(
                        type="assessment",
                        text="The participant reported a cold with poor sleep.",
                        cited_record_ids=reply_ids,
                    )
                ],
                abstained=False,
            )

        hrv_ids = [rid for rid in ids if rid.endswith("hrv_rmssd")] or ids[:1]
        return DraftReport(
            claims=[
                DraftClaim(
                    type="relationship",
                    text="HRV dropped after the study drug started.",
                    cited_record_ids=hrv_ids,
                )
            ],
            abstained=False,
        )


class FailOnSecondModel:
    """Works on the first case, raises LLMError on the second case's first call."""

    name = "fake-validation-fail-model"

    def __init__(self) -> None:
        self.calls = 0
        self._cases_started = 0

    def generate(self, system: str, user: str, schema):
        self.calls += 1
        ids = re.findall(r'"record_id":"([^"]+)"', user)

        # A fresh report (no reply citation yet) marks the start of a case.
        reply_ids = [rid for rid in ids if "-reply-" in rid]
        if not reply_ids:
            self._cases_started += 1
            if self._cases_started >= 2:
                raise LLMError("quota exhausted")

        if reply_ids:
            return DraftReport(
                claims=[
                    DraftClaim(
                        type="assessment",
                        text="The participant reported a cold.",
                        cited_record_ids=reply_ids,
                    )
                ],
                abstained=False,
            )
        hrv_ids = [rid for rid in ids if rid.endswith("hrv_rmssd")] or ids[:1]
        return DraftReport(
            claims=[
                DraftClaim(
                    type="relationship",
                    text="HRV dropped after the study drug started.",
                    cited_record_ids=hrv_ids,
                )
            ],
            abstained=False,
        )


TWO_CASES = [
    {
        "case_id": "v01",
        "participant_id": "P-07",
        "day": 15,
        "fault": None,
        "ground_truth_note": "adverse pattern; no drug link supported; data complete",
    },
    {
        "case_id": "v02",
        "participant_id": "P-07",
        "day": 15,
        "fault": "causal_overclaim",
        "ground_truth_note": "adverse pattern; no drug link supported; data complete",
    },
]


def test_run_suite_writes_two_files_and_resumes_without_model(tmp_path):
    out_dir = str(tmp_path / "validation")

    model = FakeModel()
    records = validation.run_suite(
        model=model, resume=True, out_dir=out_dir, cases=TWO_CASES
    )
    assert len(records) == 2
    assert (tmp_path / "validation" / "v01.json").exists()
    assert (tmp_path / "validation" / "v02.json").exists()

    calls_after_first = model.calls
    assert calls_after_first > 0

    # A second run with resume=True loads the files and never calls the model again.
    model2 = FakeModel()
    records2 = validation.run_suite(
        model=model2, resume=True, out_dir=out_dir, cases=TWO_CASES
    )
    assert len(records2) == 2
    assert model2.calls == 0


def test_run_suite_stops_on_llm_error_keeping_finished_cases(tmp_path):
    out_dir = str(tmp_path / "validation")

    model = FailOnSecondModel()
    records = validation.run_suite(
        model=model, resume=True, out_dir=out_dir, cases=TWO_CASES
    )

    assert len(records) == 1
    assert (tmp_path / "validation" / "v01.json").exists()
    assert not (tmp_path / "validation" / "v02.json").exists()


def _record(case_id, fault, raw_verdict, raw_failed, final_verdict,
            final_gate_checks, rounds=1, requests=0, replies=0,
            models_used=("m1",)):
    return {
        "case_id": case_id,
        "participant_id": "P-07",
        "day": 15,
        "fault": fault,
        "ground_truth_note": "note",
        "raw": {
            "report": {},
            "gate": {},
            "verdict": raw_verdict,
            "failed": list(raw_failed),
        },
        "pipeline": {
            "drafts": [],
            "gates": [{"checks": final_gate_checks}],
            "requests": [{} for _ in range(requests)],
            "replies": [{} for _ in range(replies)],
            "final_verdict": final_verdict,
            "rounds": rounds,
        },
        "models_used": list(models_used),
    }


def test_summarize_counts_and_self_check(tmp_path):
    out_path = str(tmp_path / "metrics_validation.json")

    records = [
        # clean case, raw passes, final passes, gate all-pass
        _record(
            "v01", None, "pass", [], "pass",
            [{"dimension": "temporal:c", "passed": True, "explanation": "passed"}],
            rounds=1, requests=0, replies=0, models_used=("m1",),
        ),
        # fault case, raw holds (causal), final passes after loop, gate now clean
        _record(
            "v02", "causal_overclaim", "hold", ["causal_restraint", "negative_control"],
            "pass",
            [{"dimension": "evidence_grounding:c", "passed": True, "explanation": "passed"}],
            rounds=2, requests=3, replies=1, models_used=("m1", "m2"),
        ),
        # fault case, raw holds, stays held
        _record(
            "v03", "silent_gaps", "hold", ["missing_data"], "hold",
            [{"dimension": "missing_data:c", "passed": False, "explanation": "gaps"}],
            rounds=3, requests=1, replies=0, models_used=("m1",),
        ),
    ]

    summary = validation.summarize(records, out_path=out_path)

    assert summary["cases"] == 3
    assert summary["models_used"] == ["m1", "m2"]

    assert summary["raw"]["held"] == 2
    assert summary["raw"]["reached_monitor_unchecked"] == 3
    assert summary["raw"]["by_dimension"] == {
        "causal_restraint": 1,
        "negative_control": 1,
        "missing_data": 1,
    }

    assert summary["pipeline"]["passed_after_loop"] == 2
    assert summary["pipeline"]["still_held"] == 1
    assert summary["pipeline"]["unsafe_reaching_monitor"] == 0
    assert summary["pipeline"]["evidence_requests"] == 4
    assert summary["pipeline"]["replies"] == 1
    assert summary["pipeline"]["mean_rounds"] == (1 + 2 + 3) / 3

    assert summary["fault_cases"] == {"raw_held": 2, "total": 2}
    assert summary["clean_cases"] == {"raw_held": 0, "total": 1}

    # The file was written with the same content.
    with open(out_path, encoding="utf-8") as fh:
        on_disk = json.load(fh)
    assert on_disk == summary


def test_summarize_unsafe_reaching_monitor_is_one_for_inconsistent_record(tmp_path):
    out_path = str(tmp_path / "metrics_validation.json")

    # final_verdict says pass, but its final gate still has a failing check.
    records = [
        _record(
            "v01", None, "pass", [], "pass",
            [{"dimension": "recompute:c", "passed": False, "explanation": "mismatch"}],
        ),
    ]
    summary = validation.summarize(records, out_path=out_path)
    assert summary["pipeline"]["unsafe_reaching_monitor"] == 1


def test_replay_loads_what_run_suite_wrote(tmp_path):
    out_dir = str(tmp_path / "validation")

    model = FakeModel()
    validation.run_suite(model=model, resume=True, out_dir=out_dir, cases=TWO_CASES)

    record = validation.replay("v01", out_dir=out_dir)
    assert record["case_id"] == "v01"
    assert "raw" in record
    assert "pipeline" in record
