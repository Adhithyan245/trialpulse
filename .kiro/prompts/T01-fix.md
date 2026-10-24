Task T01-fix: fix the Reading test helper in tests/test_models.py.

File you may edit: tests/test_models.py only. Do not touch trialpulse/core/models.py.
You cannot run shell commands or use the web in this project; the reviewer runs the tests.

Current result: 3 failed, 14 passed. All 3 failures come from _build_reading, which fills
inherited Record fields with placeholders; `kind` gets "x", which Record rejects.

This is the exact definition of pulseeval.timeline.Record (do not copy it into the project):

    RecordKind = Literal["physiological", "activity", "sleep", "subjective", "context", "goal", "memory"]
    class Record(BaseModel):
        record_id: str
        kind: RecordKind
        name: str
        value: float | str
        unit: str | None = None
        event_time: datetime
        recorded_at: datetime
        source: str          # e.g. "wearable", "self_report"
        confidence: float | None = None

Replace the generic introspection in _build_reading (and remove _placeholder if nothing
else uses it) with explicit, valid values: record_id "r0001", kind "physiological",
value 54.0, unit "bpm", event_time and recorded_at = NOW, source "wearable",
participant_id "P001", site_id "S01", then apply overrides. Keep every existing test's
intent unchanged. When finished, list the file you changed and stop.
