"""Built-once, cached application state for the FastAPI backend (Task T13).

The state is generated exactly once, guarded by a module-level lock so that
concurrent callers (the browser fires /api/trial, /api/clock and /api/metrics at
once on first load) all wait for a single build and then share the same object. The
state is normally built at application startup (see the FastAPI lifespan in app.py)
so the first request does not pay the ~30 s build cost.

The state holds: the synthetic trial, personal bands, public/validation metrics, a
precomputed per-day clock, the recorded validation runs, and the audit log (seeded
from the recorded runs the first time its table is empty).

The precomputed clock is cached to ``data/derived/clock.json`` (the trial is
deterministic, seed 7). On startup the cache is loaded when present and its ``seed``
and ``n_days`` match; otherwise it is computed and written.

Environment variables honoured:
  TP_AUDIT_PATH       path to the audit SQLite file (default data/derived/audit.sqlite3)
  TP_VALIDATION_DIR   directory of recorded validation runs (default data/derived/validation)
  TP_CLOCK_CACHE      path to the clock cache JSON (default data/derived/clock.json)

All participant data is synthetic.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

from trialpulse.api.audit import AuditLog, record_loop
from trialpulse.data.generator import (
    N_DAYS,
    TRIAL_START,
    TrialData,
    generate,
)
from trialpulse.data.trials import build_public_metrics
from trialpulse.gate.evidence import LoopResult
from trialpulse.signals.baseline import personal_bands
from trialpulse.signals.detect import detect

DEFAULT_VALIDATION_DIR = "data/derived/validation"
DEFAULT_AUDIT_PATH = "data/derived/audit.sqlite3"
DEFAULT_CLOCK_CACHE = "data/derived/clock.json"
PUBLIC_METRICS_PATH = "data/derived/metrics_public.json"
VALIDATION_METRICS_PATH = "data/derived/metrics_validation.json"

# The deterministic trial seed the demo runs on.
TRIAL_SEED = 7

# Module-level single-build guard. ``_state`` is the shared instance; ``_build_lock``
# ensures the builder runs exactly once even under concurrent first requests.
_state: AppState | None = None
_build_lock = threading.Lock()


def as_of(day: int) -> datetime:
    """The clock instant for a trial ``day``: that day at 23:00."""
    return TRIAL_START + timedelta(days=day - 1) + timedelta(hours=23)


def validation_dir() -> str:
    return os.environ.get("TP_VALIDATION_DIR", DEFAULT_VALIDATION_DIR)


def audit_path() -> str:
    return os.environ.get("TP_AUDIT_PATH", DEFAULT_AUDIT_PATH)


def clock_cache_path() -> str:
    return os.environ.get("TP_CLOCK_CACHE", DEFAULT_CLOCK_CACHE)


@dataclass
class AppState:
    trial: TrialData
    bands: dict
    public_metrics: dict | None
    validation_metrics: dict | None
    clock: dict
    runs: list[dict]
    runs_by_case: dict[str, dict]
    audit: AuditLog


def _load_json(path: str) -> dict | None:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def _load_runs(directory: str) -> list[dict]:
    """Load every ``*.json`` recorded run from ``directory`` sorted by case_id."""
    if not os.path.isdir(directory):
        return []
    records: list[dict] = []
    for name in os.listdir(directory):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as fh:
            records.append(json.load(fh))
    records.sort(key=lambda r: r.get("case_id", ""))
    return records


def _build_clock(trial: TrialData) -> dict:
    """Precompute, for each trial day 1..28, every participant's status as of 23:00.

    drift/non_wear/diary_conflict reflect whether that signal exists for the
    participant as of that day; resting_hr is the latest known value that day (or
    None), worn is whether a resting_hr reading exists that day.
    """
    # Index readings by (participant_id, trial_day) -> {name: Reading}, for speed.
    from trialpulse.signals.baseline import trial_day

    by_pid_day: dict[tuple[str, int], dict[str, object]] = {}
    for r in trial.readings:
        d = trial_day(r.event_time)
        by_pid_day.setdefault((r.participant_id, d), {})[r.name] = r

    participants = trial.participants
    days: list[dict] = []
    for d in range(1, N_DAYS + 1):
        instant = as_of(d)
        signals = detect(trial, instant)
        drift_pids = {s.participant_id for s in signals if s.type == "drift"}
        non_wear_pids = {s.participant_id for s in signals if s.type == "non_wear"}
        conflict_pids = {
            s.participant_id for s in signals if s.type == "diary_conflict"
        }

        rows: list[dict] = []
        for p in participants:
            pid = p.participant_id
            day_readings = by_pid_day.get((pid, d), {})
            rhr_reading = day_readings.get("resting_hr")
            # Only count readings knowable as of the day's instant.
            resting_hr = None
            worn = False
            if (
                rhr_reading is not None
                and rhr_reading.recorded_at <= instant
                and isinstance(rhr_reading.value, (int, float))
            ):
                resting_hr = float(rhr_reading.value)
                worn = True

            rows.append(
                {
                    "participant_id": pid,
                    "site_id": p.site_id,
                    "resting_hr": resting_hr,
                    "worn": worn,
                    "drift": pid in drift_pids,
                    "non_wear": pid in non_wear_pids,
                    "diary_conflict": pid in conflict_pids,
                }
            )
        days.append({"day": d, "participants": rows})

    return {"seed": TRIAL_SEED, "n_days": N_DAYS, "days": days}


def _load_or_build_clock(trial: TrialData) -> dict:
    """Return the precomputed clock, from the on-disk cache when it matches.

    The cache is reused only when its ``seed`` and ``n_days`` match the current
    deterministic trial; otherwise it is recomputed and written. Any error reading
    the cache falls back to recomputing.
    """
    path = clock_cache_path()
    cached = _load_json(path)
    if (
        isinstance(cached, dict)
        and cached.get("seed") == TRIAL_SEED
        and cached.get("n_days") == N_DAYS
        and isinstance(cached.get("days"), list)
    ):
        return cached

    clock = _build_clock(trial)
    _write_clock_cache(path, clock)
    return clock


def _write_clock_cache(path: str, clock: dict) -> None:
    """Write the clock cache, creating the parent directory as needed."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(clock, fh)


def _seed_audit(audit: AuditLog, runs: list[dict]) -> None:
    """Seed an empty audit log from the recorded validation runs.

    For each run, validate its pipeline part into a LoopResult and record the loop
    using the run's first draft ``as_of`` as the timestamp.
    """
    for record in runs:
        pipeline = record.get("pipeline")
        if not pipeline:
            continue
        loop = LoopResult.model_validate(
            {
                "drafts": pipeline["drafts"],
                "gates": pipeline["gates"],
                "requests": pipeline["requests"],
                "replies": pipeline["replies"],
                "final_verdict": pipeline["final_verdict"],
            }
        )
        if not loop.drafts:
            continue
        ts = loop.drafts[0].as_of
        record_loop(audit, loop, ts)


def _build_state() -> AppState:
    """Construct a fresh :class:`AppState`. Callers must serialise via the lock."""
    trial = generate(TRIAL_SEED)
    bands = personal_bands(trial)

    public_metrics = _load_json(PUBLIC_METRICS_PATH)
    if public_metrics is None:
        public_metrics = build_public_metrics()
    validation_metrics = _load_json(VALIDATION_METRICS_PATH)

    clock = _load_or_build_clock(trial)

    runs = _load_runs(validation_dir())
    runs_by_case = {r["case_id"]: r for r in runs}

    # Seed the audit log only when its table is empty, once, inside the log's lock.
    audit = AuditLog(path=audit_path())
    if not audit.entries():
        _seed_audit(audit, runs)

    return AppState(
        trial=trial,
        bands=bands,
        public_metrics=public_metrics,
        validation_metrics=validation_metrics,
        clock=clock,
        runs=runs,
        runs_by_case=runs_by_case,
        audit=audit,
    )


def get_state() -> AppState:
    """Return the shared application state, building it exactly once.

    The build is guarded by a module-level lock: the first caller builds while any
    concurrent callers block on the lock, then all observe the same instance. The
    lock is held only for the duration of the build; once built, subsequent calls
    take the fast path without locking.
    """
    global _state
    if _state is not None:
        return _state
    with _build_lock:
        # Re-check under the lock: another thread may have built it while we waited.
        if _state is None:
            _state = _build_state()
    return _state


def is_ready() -> bool:
    """True once the shared state has been built."""
    return _state is not None


def clear_state() -> None:
    """Clear the cached state (used by tests before changing the environment)."""
    global _state
    with _build_lock:
        _state = None


def build_cache() -> None:
    """Compute and write the clock cache for the deterministic trial.

    Exposed as ``python -m trialpulse.api.state --build-cache`` so the slow clock
    precomputation can be done ahead of time (e.g. at container build) instead of on
    first request.
    """
    trial = generate(TRIAL_SEED)
    clock = _build_clock(trial)
    path = clock_cache_path()
    _write_clock_cache(path, clock)
    print(f"wrote clock cache to {path} (seed={TRIAL_SEED}, n_days={N_DAYS})")


if __name__ == "__main__":
    import sys

    if "--build-cache" in sys.argv[1:]:
        build_cache()
    else:
        print("usage: python -m trialpulse.api.state --build-cache")
        sys.exit(2)
