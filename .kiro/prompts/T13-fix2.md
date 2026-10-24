Task T13-fix2: restore the old tamper_for_demo call style.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
File you may edit: trialpulse/api/audit.py only.

Result: 119 passed, 1 failed: tests/test_audit.py::test_tamper_breaks_chain_at_entry_three
calls tamper_for_demo(log._conn, entry_id, {...}) with a sqlite3.Connection and now gets
"TypeError: expected str, bytes or os.PathLike object, not Connection" (audit.py ~391).
The task said to keep the existing call style working. Accept all three: an AuditLog
(use its connection and lock), a sqlite3.Connection (use it directly, no lock), or a path
(open, edit, commit, close). Do not change any test. When finished, list the file you
changed and stop.
