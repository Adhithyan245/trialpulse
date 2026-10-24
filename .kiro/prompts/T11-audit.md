Task T11: the tamper-evident audit log with e-signatures. With tests.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Read trialpulse/core/models.py (AuditEntry, Report, GateResult, EvidenceRequest) and
trialpulse/gate/evidence.py (LoopResult) first. stdlib only (sqlite3, hashlib, json).

Files you may create: trialpulse/api/__init__.py, trialpulse/api/audit.py,
tests/test_audit.py. Nothing else.

trialpulse/api/audit.py
  GENESIS = "0" * 64
  canonical(entry_without_hash: dict) -> str: json.dumps(sort_keys=True,
    separators=(",", ":"), default=str).
  compute_hash(prev_hash, fields) = sha256((prev_hash + canonical(fields)).encode()).hexdigest()
    where fields = entry_id, ts (ISO string), actor_role, action, report_id, details_json,
    prev_hash.
  class AuditLog:
    __init__(path: str = "data/derived/audit.sqlite3"); creates parent folders and the
      table audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, entry_id TEXT UNIQUE, ts TEXT,
      actor_role TEXT, action TEXT, report_id TEXT, details_json TEXT, prev_hash TEXT,
      entry_hash TEXT). ":memory:" must work too.
    append(actor_role, action, report_id, details: dict, ts: datetime) -> AuditEntry:
      prev_hash = last entry_hash or GENESIS; entry_id f"AUD-{seq:05d}" (next seq);
      details_json = json.dumps(details, sort_keys=True, default=str); compute the hash;
      INSERT; return the AuditEntry model. The class exposes NO update or delete method.
    entries(report_id: str | None = None) -> list[AuditEntry] in seq order.
    verify() -> dict {"ok": bool, "checked": n, "first_bad_entry_id": str | None,
      "reason": str | None}: recompute every hash in order; also check each prev_hash
      equals the previous entry_hash (GENESIS for the first).
  record_loop(log, loop: LoopResult, ts: datetime) -> list[AuditEntry]: for each round i,
    append "drafted" (actor system; details: report_id, model_id, prompt_version,
    n_claims), then "gated" (details: verdict, failed dimensions, pulseeval_commit), then
    for each request created in that round "evidence_requested" (details: request_id,
    kind, failed_dimension, question_text) and for each answered request with a reply
    "evidence_received" (details: request_id, reply_record_id). Use ts + i seconds so the
    order is stable. Map requests to rounds by their sent_at (requests sent between draft
    i and draft i+1 belong to round i).
  sign(log, report: Report, actor_role: "monitor" | "safety_reviewer", signer: str,
       decision: "approved" | "rejected" | "redraft_requested", reason: str,
       ts: datetime) -> AuditEntry: e-signature entry; details = {"signer", "reason",
       "meaning": f"{signer} {decision} report {report.report_id}", "report_hash":
       sha256 of report.model_dump_json()}. reason must be non-empty (ValueError).
  tamper_for_demo(path_or_conn, entry_id, new_details: dict) -> None: a clearly named
    helper that edits details_json of one row directly with SQL, simulating someone
    editing the database behind the application's back. Module docstring says it exists
    only for the tamper demonstration.

tests/test_audit.py (":memory:" or tmp_path; build a small LoopResult by hand or with a
fake model as in tests/test_evidence.py; no network):
 - append 5 entries -> verify ok, checked 5; prev_hash chaining correct.
 - tamper_for_demo on entry 3 -> verify not ok, first_bad_entry_id is entry 3's id.
 - a file-backed log survives reopening and still verifies.
 - record_loop for a 2-draft loop produces actions in order:
   drafted, gated, evidence_requested..., evidence_received..., drafted, gated.
 - sign with an empty reason raises ValueError; a valid sign appends an "approved" entry
   whose details include report_hash and meaning.
 - AuditLog has no attribute named update, delete, or remove.

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
