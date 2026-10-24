Task T09-fix: finish the gate; one spec error.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/gate/adapter.py, trialpulse/gate/live.py,
tests/test_gate.py. Nothing else. Your previous run on T09 ended before you reported back;
read the three files and the task in .kiro/prompts/T09-gate-causal.md and finish anything
incomplete.

Spec error (mine): AgentTrace.tools_called is REQUIRED, not defaulted. Pass
tools_called=[] (and memories_used=[]) explicitly when building the trace. All 5 tests in
tests/test_gate.py currently fail with "tools_called Field required" at adapter.py:110.

Do not weaken any test. When finished, list the files you changed and stop.
