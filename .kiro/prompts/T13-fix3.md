Task T13-fix3: the server hangs on first load. Build state once, at startup, and cache it.

You cannot run shell commands or use the web in this project; the reviewer runs the tests
and the server. Files you may edit: trialpulse/api/state.py, trialpulse/api/app.py,
tests/test_api.py (adapt only if a test needs the new startup behavior). Nothing else.

What the reviewer measured: building AppState takes ~30 s (precomputing 28 days of
detect() for the clock + seeding the audit log). On first page load the browser fires
/api/trial, /api/clock and /api/metrics at once; all three threads enter the
functools.lru_cache builder at the same time (lru_cache does not lock), each builds its own
state and seeds the same audit SQLite file, and the requests were still pending after
2+ minutes. On a free host that sleeps when idle this would hang every judge's first visit.

Fix:
 1. Guard the state builder with a module-level threading.Lock so it runs exactly once;
    other callers wait for it and then get the same object.
 2. Build the state at application startup (FastAPI lifespan), so the first request does
    not pay for it. /api/health must answer immediately even while building, with
    {"ok": true, "mode": ..., "ready": bool}.
 3. Cache the precomputed clock to data/derived/clock.json (the trial is deterministic,
    seed 7); on startup load it if present and its "seed" and "n_days" match, else
    compute and write it. Expose a CLI: python -m trialpulse.api.state --build-cache.
 4. Seed the audit log only when the table is empty, inside the AuditLog's lock, once.
Tests: the existing API tests must keep passing (they use tmp paths; make sure the clock
cache path can be overridden with env TP_CLOCK_CACHE so tests do not write into
data/derived). Add a test that two threads calling the state getter at once build it once
(count builds with a monkeypatched builder).
When finished, list the files you changed and stop.
