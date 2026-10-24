Task T13-fix: make the audit log safe to use from FastAPI's worker threads.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/api/audit.py only. Nothing else. Keep all tests passing.

Current result: tests/test_api.py 10 passed, 1 failed (test_tamper_then_verify_fails):
  sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that
  same thread. (raised at audit.py line ~148, in entries())
FastAPI runs sync endpoints in a thread pool, so the cached AuditLog's connection is used
from other threads. Fix: open the connection with sqlite3.connect(path,
check_same_thread=False) and guard every read and write (append, entries, verify) with a
threading.Lock held by the AuditLog instance, so appends stay strictly ordered and the
hash chain cannot interleave. tamper_for_demo, when given a path, opens its own
connection; when given an AuditLog's connection, it must also take that log's lock if it
can find it (accept either an AuditLog instance or a path; keep the existing call style
working).

When finished, list the file you changed and stop.
