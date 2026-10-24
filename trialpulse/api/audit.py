"""Tamper-evident audit log with e-signatures (Task T11).

Every event in the trial pipeline is appended to a hash-chained SQLite log: each
entry's hash covers the previous entry's hash plus its own canonical fields, so any
later edit to an earlier row breaks the chain from that point on. The log is
append-only by design: :class:`AuditLog` exposes no update, delete or remove method.

``tamper_for_demo`` exists ONLY for the tamper demonstration in the interface: it
edits a row directly with SQL, simulating someone editing the database behind the
application's back so the UI can show ``verify()`` catching it. Nothing in the normal
application flow may call it.

Standard library only: sqlite3, hashlib, json, threading.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime

from trialpulse.core.models import AuditEntry, Report
from trialpulse.gate.evidence import LoopResult

GENESIS = "0" * 64


def canonical(entry_without_hash: dict) -> str:
    """Deterministic JSON for hashing: sorted keys, no whitespace, str fallback."""
    return json.dumps(
        entry_without_hash, sort_keys=True, separators=(",", ":"), default=str
    )


def compute_hash(prev_hash: str, fields: dict) -> str:
    """sha256 over the previous hash concatenated with the canonical fields."""
    return hashlib.sha256((prev_hash + canonical(fields)).encode()).hexdigest()


def _hash_fields(entry: dict) -> dict:
    """The exact subset of fields covered by an entry's hash, in a fixed shape."""
    return {
        "entry_id": entry["entry_id"],
        "ts": entry["ts"],
        "actor_role": entry["actor_role"],
        "action": entry["action"],
        "report_id": entry["report_id"],
        "details_json": entry["details_json"],
        "prev_hash": entry["prev_hash"],
    }


class AuditLog:
    """An append-only, hash-chained audit log backed by SQLite.
    
    Thread-safe: all reads and writes are guarded by a threading.Lock.
    The SQLite connection is opened with check_same_thread=False to allow
    use from FastAPI's worker thread pool.
    """

    def __init__(self, path: str = "data/derived/audit.sqlite3") -> None:
        self.path = path
        if path != ":memory:":
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT UNIQUE,
                    ts TEXT,
                    actor_role TEXT,
                    action TEXT,
                    report_id TEXT,
                    details_json TEXT,
                    prev_hash TEXT,
                    entry_hash TEXT
                )
                """
            )
            self._conn.commit()

    def _last(self) -> sqlite3.Row | None:
        """Fetch the last entry. Caller must hold self._lock."""
        cur = self._conn.execute(
            "SELECT * FROM audit ORDER BY seq DESC LIMIT 1"
        )
        return cur.fetchone()

    def append(
        self,
        actor_role: str,
        action: str,
        report_id: str,
        details: dict,
        ts: datetime,
    ) -> AuditEntry:
        with self._lock:
            last = self._last()
            prev_hash = last["entry_hash"] if last is not None else GENESIS
            next_seq = (last["seq"] + 1) if last is not None else 1
            entry_id = f"AUD-{next_seq:05d}"
            ts_str = ts.isoformat()
            details_json = json.dumps(details, sort_keys=True, default=str)

            fields = {
                "entry_id": entry_id,
                "ts": ts_str,
                "actor_role": actor_role,
                "action": action,
                "report_id": report_id,
                "details_json": details_json,
                "prev_hash": prev_hash,
            }
            entry_hash = compute_hash(prev_hash, fields)

            self._conn.execute(
                """
                INSERT INTO audit(
                    entry_id, ts, actor_role, action, report_id,
                    details_json, prev_hash, entry_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    ts_str,
                    actor_role,
                    action,
                    report_id,
                    details_json,
                    prev_hash,
                    entry_hash,
                ),
            )
            self._conn.commit()

            return AuditEntry(
                entry_id=entry_id,
                ts=ts,
                actor_role=actor_role,
                action=action,
                report_id=report_id,
                details_json=details_json,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )

    def entries(self, report_id: str | None = None) -> list[AuditEntry]:
        with self._lock:
            if report_id is None:
                cur = self._conn.execute("SELECT * FROM audit ORDER BY seq ASC")
            else:
                cur = self._conn.execute(
                    "SELECT * FROM audit WHERE report_id = ? ORDER BY seq ASC",
                    (report_id,),
                )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> AuditEntry:
        return AuditEntry(
            entry_id=row["entry_id"],
            ts=datetime.fromisoformat(row["ts"]),
            actor_role=row["actor_role"],
            action=row["action"],
            report_id=row["report_id"],
            details_json=row["details_json"],
            prev_hash=row["prev_hash"],
            entry_hash=row["entry_hash"],
        )

    def verify(self) -> dict:
        """Recompute every hash in order and check the prev_hash chaining."""
        with self._lock:
            cur = self._conn.execute("SELECT * FROM audit ORDER BY seq ASC")
            rows = cur.fetchall()

            expected_prev = GENESIS
            checked = 0
            for row in rows:
                checked += 1
                if row["prev_hash"] != expected_prev:
                    return {
                        "ok": False,
                        "checked": checked,
                        "first_bad_entry_id": row["entry_id"],
                        "reason": "prev_hash does not match the previous entry's hash",
                    }
                fields = {
                    "entry_id": row["entry_id"],
                    "ts": row["ts"],
                    "actor_role": row["actor_role"],
                    "action": row["action"],
                    "report_id": row["report_id"],
                    "details_json": row["details_json"],
                    "prev_hash": row["prev_hash"],
                }
                recomputed = compute_hash(row["prev_hash"], fields)
                if recomputed != row["entry_hash"]:
                    return {
                        "ok": False,
                        "checked": checked,
                        "first_bad_entry_id": row["entry_id"],
                        "reason": "entry_hash does not match the recomputed hash",
                    }
                expected_prev = row["entry_hash"]

            return {
                "ok": True,
                "checked": checked,
                "first_bad_entry_id": None,
                "reason": None,
            }

    def reset(self) -> None:
        """Drop and recreate the audit table, clearing all entries.
        
        Thread-safe: acquires the lock before dropping the table.
        Used for the demo reset feature.
        """
        with self._lock:
            self._conn.execute("DROP TABLE IF EXISTS audit")
            self._conn.execute(
                """
                CREATE TABLE audit(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT UNIQUE,
                    ts TEXT,
                    actor_role TEXT,
                    action TEXT,
                    report_id TEXT,
                    details_json TEXT,
                    prev_hash TEXT,
                    entry_hash TEXT
                )
                """
            )
            self._conn.commit()


def record_loop(log: AuditLog, loop: LoopResult, ts: datetime) -> list[AuditEntry]:
    """Record a full evidence loop as audit entries, in a stable order.

    For each round i: a ``drafted`` entry, a ``gated`` entry, then one
    ``evidence_requested`` per request created in that round and one
    ``evidence_received`` per answered request with a reply. Requests are mapped to
    rounds by their ``sent_at``: a request sent between draft i and draft i+1 belongs
    to round i. Each round's entries use ``ts + i seconds`` so ordering is stable.
    """
    from datetime import timedelta

    drafts = loop.drafts
    gates = loop.gates
    n_rounds = len(drafts)

    # Build the sorted boundaries between consecutive drafts.
    draft_times = [d.as_of for d in drafts]

    # reply_record_id set, so evidence_received can be matched.
    reply_ids = {r.record_id for r in loop.replies}

    def round_for(sent_at: datetime) -> int:
        """Round index i for a request sent between draft i and draft i+1.

        A request is created during the loop iteration that produces the *next*
        draft, so its ``sent_at`` coincides with that next draft's ``as_of`` and is
        strictly later than the draft it belongs to. We therefore take the largest
        index whose draft time is strictly before ``sent_at``; if none qualifies
        (ties at the very first draft from midnight clamping) we fall back to 0.
        """
        idx = 0
        found = False
        for i, dt in enumerate(draft_times):
            if dt < sent_at:
                idx = i
                found = True
            else:
                break
        if not found:
            return 0
        return idx

    # Group requests by round.
    requests_by_round: dict[int, list] = {i: [] for i in range(n_rounds)}
    for req in loop.requests:
        requests_by_round[round_for(req.sent_at)].append(req)

    out: list[AuditEntry] = []
    for i in range(n_rounds):
        round_ts = ts + timedelta(seconds=i)
        report = drafts[i]
        gate = gates[i]

        out.append(
            log.append(
                actor_role="system",
                action="drafted",
                report_id=report.report_id,
                details={
                    "report_id": report.report_id,
                    "model_id": report.model_id,
                    "prompt_version": report.prompt_version,
                    "n_claims": len(report.claims),
                },
                ts=round_ts,
            )
        )

        failed = [c.dimension for c in gate.checks if not c.passed]
        out.append(
            log.append(
                actor_role="system",
                action="gated",
                report_id=report.report_id,
                details={
                    "verdict": gate.verdict,
                    "failed_dimensions": failed,
                    "pulseeval_commit": gate.pulseeval_commit,
                },
                ts=round_ts,
            )
        )

        round_requests = requests_by_round[i]
        for req in round_requests:
            out.append(
                log.append(
                    actor_role="system",
                    action="evidence_requested",
                    report_id=report.report_id,
                    details={
                        "request_id": req.request_id,
                        "kind": req.kind,
                        "failed_dimension": req.failed_dimension,
                        "question_text": req.question_text,
                    },
                    ts=round_ts,
                )
            )
        for req in round_requests:
            if req.reply_record_id is not None and req.reply_record_id in reply_ids:
                out.append(
                    log.append(
                        actor_role="system",
                        action="evidence_received",
                        report_id=report.report_id,
                        details={
                            "request_id": req.request_id,
                            "reply_record_id": req.reply_record_id,
                        },
                        ts=round_ts,
                    )
                )

    return out


def sign(
    log: AuditLog,
    report: Report,
    actor_role: str,
    signer: str,
    decision: str,
    reason: str,
    ts: datetime,
) -> AuditEntry:
    """Append an e-signature entry for a human decision on a report.

    ``decision`` is used directly as the entry action (approved / rejected /
    redraft_requested). ``reason`` must be non-empty.
    """
    if not reason or not reason.strip():
        raise ValueError("an e-signature reason must be non-empty")

    report_hash = hashlib.sha256(report.model_dump_json().encode()).hexdigest()
    details = {
        "signer": signer,
        "reason": reason,
        "meaning": f"{signer} {decision} report {report.report_id}",
        "report_hash": report_hash,
    }
    return log.append(
        actor_role=actor_role,
        action=decision,
        report_id=report.report_id,
        details=details,
        ts=ts,
    )


def tamper_for_demo(path_or_conn_or_log: str | sqlite3.Connection | AuditLog, entry_id: str, new_details: dict) -> None:
    """Edit one row's details_json directly with SQL, behind the log's back.

    This exists ONLY for the tamper demonstration: it bypasses the append-only API
    so the interface can show ``verify()`` detecting the break. Do not call it from
    normal application code.
    
    Accepts three types:
    - An AuditLog instance: uses its connection and lock for thread safety.
    - A sqlite3.Connection: uses it directly without acquiring a lock.
    - A file path (string): opens, edits, commits, and closes.
    """
    own_conn = False
    lock = None
    
    if isinstance(path_or_conn_or_log, AuditLog):
        conn = path_or_conn_or_log._conn
        lock = path_or_conn_or_log._lock
    elif isinstance(path_or_conn_or_log, sqlite3.Connection):
        conn = path_or_conn_or_log
        lock = None
    else:
        conn = sqlite3.connect(path_or_conn_or_log)
        own_conn = True
        lock = None

    try:
        if lock:
            lock.acquire()
        new_json = json.dumps(new_details, sort_keys=True, default=str)
        conn.execute(
            "UPDATE audit SET details_json = ? WHERE entry_id = ?",
            (new_json, entry_id),
        )
        conn.commit()
    finally:
        if lock:
            lock.release()
        if own_conn:
            conn.close()
