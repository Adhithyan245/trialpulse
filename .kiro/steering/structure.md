trialpulse/core/      models.py (the data contracts; change only when asked)
trialpulse/data/      generator.py, trials.py
trialpulse/signals/   baseline.py, detect.py
trialpulse/agent/     deid.py, llm.py, prompts.py, report.py
trialpulse/gate/      adapter.py, live.py, validation.py
trialpulse/api/       app.py, audit.py
trialpulse/__main__.py  CLI
web/src/              views/Monitor.tsx, Compliance.tsx, Scorecard.tsx, TrialFinder.tsx
tests/                one test file per module
data/raw/             portal downloads (read-only)
data/synthetic/, data/derived/   generated, gitignored except metrics files
