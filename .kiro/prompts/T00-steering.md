Task T00: create the project's steering files and .gitignore.

Files you may create: .kiro/steering/product.md, .kiro/steering/tech.md,
.kiro/steering/structure.md, .kiro/steering/guardrails.md, .gitignore
Do not create or edit any other file. Write each file's content exactly as given
between its BEGIN and END lines (do not include the BEGIN/END lines themselves).
When finished, list the files you created and stop.

=== BEGIN .kiro/steering/product.md ===
# TrialPulse
Wearable data for decentralized clinical trials. An AI agent drafts safety-signal
reports from participants' wearable readings and diaries; every report passes
through a reliability gate (PulseEval) before a human medical monitor sees it.

Users: medical monitor (reviews and approves reports), site coordinator
(device-wear compliance), trial sponsor (validation scorecard).

Non-negotiables:
- The AI never decides causality. Drug-to-event causality belongs to the investigator.
- Every claim in a report cites record_ids. Uncited claims are invalid.
- All participant data is synthetic and labelled "Synthetic data" on every screen.
- Public numbers (trials, environmental justice areas) come only from files in data/raw.
Non-goals: diagnosis, treatment advice, real patient data, real WHOOP accounts.
=== END .kiro/steering/product.md ===

=== BEGIN .kiro/steering/tech.md ===
# Stack (do not add to it without asking)
Python 3.11, pydantic v2, pandas, numpy, FastAPI, uvicorn, boto3, pytest, sqlite3 (stdlib)
pulseeval @ git+https://github.com/Adhithyan245/PulseEval@db4e475
Frontend: React + Vite + TypeScript, Tailwind, Recharts. No state library.

Bedrock: boto3 client "bedrock-runtime", method converse().
Model ID from env BEDROCK_MODEL_ID. Region from env AWS_REGION. Never hard-code either.
If the call fails, raise. Never return a fake or simulated response.

PulseEval: use pulseeval.timeline.Record, pulseeval.agent.AgentTrace,
pulseeval.scenarios (NumericCase, AssessmentCase, RelationshipCase) and
pulseeval.evaluation.* evaluators. Do not modify or copy PulseEval code.
Deploy: one container, FastAPI serves web/dist, AWS App Runner.
=== END .kiro/steering/tech.md ===

=== BEGIN .kiro/steering/structure.md ===
trialpulse/core/      models.py (the data contracts; change only when asked)
trialpulse/data/      generator.py, trials.py
trialpulse/signals/   baseline.py, detect.py
trialpulse/agent/     deid.py, bedrock.py, prompts.py
trialpulse/gate/      adapter.py, live.py, validation.py
trialpulse/api/       app.py, audit.py
trialpulse/__main__.py  CLI
web/src/              views/Monitor.tsx, Compliance.tsx, Scorecard.tsx, TrialFinder.tsx
tests/                one test file per module
data/raw/             portal downloads (read-only)
data/synthetic/, data/derived/   generated, gitignored except metrics files
=== END .kiro/steering/structure.md ===

=== BEGIN .kiro/steering/guardrails.md ===
# Rules for every task
1. Edit only the files the task lists. If another file must change, stop and ask.
2. No new dependencies, frameworks, services or config files unless the task says so.
3. Never edit an existing test to make it pass. If a test looks wrong, stop and say why.
4. No mocks, stubs, placeholders or simulated responses outside tests/.
5. No numbers in the UI or README that a script in this repo did not compute.
6. Do not rewrite or rename working modules from earlier tasks.
7. If you are unsure an API, field or function exists, say so instead of guessing.
8. Keep changes small. Finish the task, list the files you changed, and stop.
=== END .kiro/steering/guardrails.md ===

=== BEGIN .gitignore ===
__pycache__/
*.pyc
.venv/
.pytest_cache/
node_modules/
web/dist/
data/synthetic/
data/derived/*
!data/derived/metrics*.json
*.sqlite3
.env
.kiro/runs/
=== END .gitignore ===
