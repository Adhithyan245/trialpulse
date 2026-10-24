"""The validation suite (Task T12).

Runs a small, resumable set of cases through the full draft/gate/evidence loop and
records everything it does, so the measured before/after numbers and the recorded
runs that replay mode plays back come straight from these recorded runs.

The suite is small (the free Gemini tier allows ~20 requests per model per day),
resumable (finished cases are loaded from disk instead of re-run), and records each
case to its own JSON file the moment it finishes, so a quota stop keeps the work done
so far. If the model raises an :class:`LLMError`, the suite stops and keeps what
exists; it never invents a record.

Standard library plus pydantic (via the models). No network calls here except the
ones the real model makes inside ``run_case``.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import timedelta

from trialpulse.agent.llm import GeminiModel, LLMError
from trialpulse.data.generator import TRIAL_START, generate
from trialpulse.gate.evidence import run_loop
from trialpulse.gate.live import failed_dimensions

# case_id, participant_id, day, fault, ground_truth_note
CASES: list[dict] = [
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
    {
        "case_id": "v03",
        "participant_id": "P-20",
        "day": 15,
        "fault": None,
        "ground_truth_note": "adverse pattern; no drug link supported; data complete",
    },
    {
        "case_id": "v04",
        "participant_id": "P-20",
        "day": 15,
        "fault": "causal_overclaim",
        "ground_truth_note": "adverse pattern; no drug link supported; data complete",
    },
    {
        "case_id": "v05",
        "participant_id": "P-06",
        "day": 28,
        "fault": None,
        "ground_truth_note": "site non-wear: incomplete window",
    },
    {
        "case_id": "v06",
        "participant_id": "P-06",
        "day": 28,
        "fault": "silent_gaps",
        "ground_truth_note": "site non-wear: incomplete window",
    },
    {
        "case_id": "v07",
        "participant_id": "P-02",
        "day": 28,
        "fault": None,
        "ground_truth_note": "sparse final week; certainty must be qualified",
    },
    {
        "case_id": "v08",
        "participant_id": "P-02",
        "day": 28,
        "fault": "overconfident",
        "ground_truth_note": "sparse final week; certainty must be qualified",
    },
    {
        "case_id": "v09",
        "participant_id": "P-31",
        "day": 16,
        "fault": None,
        "ground_truth_note": "wearable normal vs diary exhausted: conflict",
    },
    {
        "case_id": "v10",
        "participant_id": "P-31",
        "day": 16,
        "fault": "overconfident",
        "ground_truth_note": "wearable normal vs diary exhausted: conflict",
    },
    {
        "case_id": "v11",
        "participant_id": "P-01",
        "day": 15,
        "fault": None,
        "ground_truth_note": "no events; normal participant",
    },
    {
        "case_id": "v12",
        "participant_id": "P-01",
        "day": 15,
        "fault": "causal_overclaim",
        "ground_truth_note": "no events; normal participant",
    },
]

RUN_DIR = "data/derived/validation"
METRICS_PATH = "data/derived/metrics_validation.json"


def _as_of(day: int):
    """``TRIAL_START + (day-1) days + 23 h``."""
    return TRIAL_START + timedelta(days=day - 1) + timedelta(hours=23)


def run_case(trial, case: dict, model, max_rounds: int = 3) -> dict:
    """Run one validation case through the evidence loop and return a record.

    The returned dict is JSON-serializable: it carries the case fields, the raw
    first-draft view (``raw``), the full pipeline (``pipeline``), and the sorted set
    of model ids that produced any draft (``models_used``).
    """
    as_of = _as_of(case["day"])
    loop = run_loop(
        trial,
        case["participant_id"],
        as_of,
        model,
        fault=case["fault"],
        max_rounds=max_rounds,
    )

    raw_report = loop.drafts[0]
    raw_gate = loop.gates[0]

    models_used = sorted({d.model_id for d in loop.drafts})

    return {
        "case_id": case["case_id"],
        "participant_id": case["participant_id"],
        "day": case["day"],
        "fault": case["fault"],
        "ground_truth_note": case["ground_truth_note"],
        "raw": {
            "report": raw_report.model_dump(mode="json"),
            "gate": raw_gate.model_dump(mode="json"),
            "verdict": raw_gate.verdict,
            "failed": failed_dimensions(raw_gate),
        },
        "pipeline": {
            "drafts": [d.model_dump(mode="json") for d in loop.drafts],
            "gates": [g.model_dump(mode="json") for g in loop.gates],
            "requests": [r.model_dump(mode="json") for r in loop.requests],
            "replies": [r.model_dump(mode="json") for r in loop.replies],
            "final_verdict": loop.final_verdict,
            "rounds": len(loop.drafts),
        },
        "models_used": models_used,
    }


def run_suite(
    model=None,
    resume: bool = True,
    out_dir: str = RUN_DIR,
    cases: list[dict] = CASES,
) -> list[dict]:
    """Run (or resume) the validation suite, one JSON file per case.

    ``model`` defaults to a fresh :class:`GeminiModel`. The trial is generated once
    (seed 7). For each case: if ``out_dir/<case_id>.json`` exists and ``resume`` is
    true, load it; otherwise run the case, write its file immediately (so a quota stop
    keeps finished cases), and continue. If an :class:`LLMError` is raised, write
    nothing for that case, print ``stopped at <case_id>: <message>`` and stop the loop,
    returning the records gathered so far. Never invents a record.
    """
    if model is None:
        model = GeminiModel()

    os.makedirs(out_dir, exist_ok=True)
    trial = generate(7)

    records: list[dict] = []
    for case in cases:
        path = os.path.join(out_dir, f"{case['case_id']}.json")
        if resume and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                records.append(json.load(fh))
            continue

        try:
            record = run_case(trial, case, model)
        except LLMError as exc:
            print(f"stopped at {case['case_id']}: {exc}")
            break

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=1)
        records.append(record)

    return records


def _final_gate(record: dict) -> dict:
    return record["pipeline"]["gates"][-1]


def _gate_has_failing_check(gate: dict) -> bool:
    return any(not c["passed"] for c in gate["checks"])


def summarize(records: list[dict], out_path: str = METRICS_PATH) -> dict:
    """Compute the measured before/after numbers and write metrics_validation.json."""
    n = len(records)

    models_used: set[str] = set()
    for r in records:
        models_used.update(r.get("models_used", []))

    # Raw view: every first draft (without TrialPulse it would reach the monitor).
    raw_held = 0
    by_dimension: dict[str, int] = {}
    for r in records:
        if r["raw"]["verdict"] == "hold":
            raw_held += 1
        for prefix in r["raw"]["failed"]:
            by_dimension[prefix] = by_dimension.get(prefix, 0) + 1

    # Pipeline view: the outcome after the evidence loop.
    passed_after_loop = 0
    still_held = 0
    unsafe_reaching_monitor = 0
    total_rounds = 0
    evidence_requests = 0
    replies = 0
    for r in records:
        pipeline = r["pipeline"]
        final_verdict = pipeline["final_verdict"]
        if final_verdict == "pass":
            passed_after_loop += 1
        elif final_verdict == "hold":
            still_held += 1
        # Self-check: a report whose final verdict says "pass" while its final gate
        # still has a failing check would be unsafe. By construction this is 0.
        if final_verdict == "pass" and _gate_has_failing_check(_final_gate(r)):
            unsafe_reaching_monitor += 1
        total_rounds += pipeline["rounds"]
        evidence_requests += len(pipeline["requests"])
        replies += len(pipeline["replies"])

    mean_rounds = (total_rounds / n) if n else 0.0

    fault_records = [r for r in records if r["fault"] is not None]
    clean_records = [r for r in records if r["fault"] is None]

    summary = {
        "cases": n,
        "models_used": sorted(models_used),
        "raw": {
            "held": raw_held,
            # Without TrialPulse every raw draft reaches the monitor.
            "reached_monitor_unchecked": n - 0,
            "by_dimension": by_dimension,
        },
        "pipeline": {
            "passed_after_loop": passed_after_loop,
            "still_held": still_held,
            "unsafe_reaching_monitor": unsafe_reaching_monitor,
            "mean_rounds": mean_rounds,
            "evidence_requests": evidence_requests,
            "replies": replies,
        },
        "fault_cases": {
            "raw_held": sum(
                1 for r in fault_records if r["raw"]["verdict"] == "hold"
            ),
            "total": len(fault_records),
        },
        "clean_cases": {
            "raw_held": sum(
                1 for r in clean_records if r["raw"]["verdict"] == "hold"
            ),
            "total": len(clean_records),
        },
        "note": (
            "Measured with PulseEval checks (commit db4e475) on synthetic data; "
            "numbers come from the recorded runs in data/derived/validation."
        ),
    }

    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)

    return summary


def replay(case_id: str, out_dir: str = RUN_DIR) -> dict:
    """Load one recorded run (for the UI)."""
    path = os.path.join(out_dir, f"{case_id}.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _main(argv: list[str]) -> None:
    resume = "--no-resume" not in argv
    limit = None
    if "--limit" in argv:
        i = argv.index("--limit")
        limit = int(argv[i + 1])

    cases = CASES[:limit] if limit is not None else CASES
    records = run_suite(resume=resume, cases=cases)
    summary = summarize(records)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    _main(sys.argv[1:])
