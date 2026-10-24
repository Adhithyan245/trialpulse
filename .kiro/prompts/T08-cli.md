Task T08: a small command-line entry point.

You cannot run shell commands or use the web in this project; the reviewer runs it.
Files you may create: trialpulse/__main__.py, tests/test_cli.py. Nothing else. stdlib
argparse only. Read trialpulse/data/generator.py, trialpulse/signals/detect.py,
trialpulse/agent/report.py and trialpulse/agent/llm.py first.

Commands (python -m trialpulse ...):
  signals --day N [--hour H=23] [--participant P]
      generate(7); as_of = TRIAL_START + (N-1) days + H hours; print one line per signal:
      "<participant_id>  <type>  <metric>  start=<trial day>  z=<z or ->  cites=<n>".
  report PARTICIPANT --day N [--hour H=23] [--fault NAME] [--json]
      draft_report with GeminiModel(); print "model=<name> prompt=<version>" and then one
      line per claim "[<type>] <text>  (<n> cites)"; with --json print
      report.model_dump_json(indent=2) instead.
  generate [--seed S=7] [--out data/synthetic/trial.json]   -> write_json, print the path.
Exit code 0 on success; on LLMError print "error: <message>" to stderr and exit 2.
Expose main(argv: list[str] | None = None) -> int so tests can call it.

tests/test_cli.py: main(["signals", "--day", "15"]) returns 0 and prints a line containing
"P-07" and "drift" (use capsys); main(["generate", "--out", <tmp_path file>]) writes the
file; main(["report", "P-07", "--day", "15"]) with GeminiModel monkeypatched to a fake
that raises LLMError returns 2. No network in tests.

When finished, list every file you changed and stop.
