Task T08-fix: the CLI test reaches the real Gemini API.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may create or edit: tests/test_cli.py, tests/conftest.py. Nothing else.

Bug: test_report_with_llm_error_exits_2 does monkeypatch.setattr(llm, "GeminiModel", ...),
but trialpulse/__main__.py does `from trialpulse.agent.llm import GeminiModel`, so the
name used by main() is trialpulse.__main__.GeminiModel. The patch had no effect, the test
made a real network call to Gemini, and main returned 0 (reviewer saw "assert 0 == 2").
Fix: patch "trialpulse.__main__.GeminiModel" instead.

Also create tests/conftest.py with an autouse fixture that makes any real Gemini call fail
loudly in tests: monkeypatch google.genai.Client so that constructing it raises
RuntimeError("network disabled in tests"). Existing tests that use fake clients pass their
own client objects and must keep passing; if any existing test constructs a real
genai.Client on purpose, leave that test's behavior unchanged by checking for it first
(read tests/test_agent.py).

When finished, list the files you changed and stop.
