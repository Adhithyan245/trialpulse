Task T18: make the app deployable as one container (Render), with a one-command local run.

You cannot run shell commands or use the web in this project; the reviewer builds the
image and deploys it. Read trialpulse/api/app.py, trialpulse/api/state.py, pyproject.toml,
web/package.json and .gitignore first.

Files you may create or edit: Dockerfile, .dockerignore, render.yaml, Makefile,
.gitignore (one line), web/src/scenes/checkpoint/PulseStrip.tsx (one attribute, see 5).
Nothing else.

1. Dockerfile (multi-stage):
   stage "web": node:22-slim; WORKDIR /app/web; copy web/package.json and
   web/package-lock.json; npm ci; copy web/; npm run build.
   stage "app": python:3.11-slim; apt-get install git (needed for the pulseeval git
   dependency) and clean apt lists; WORKDIR /app; copy pyproject.toml and the trialpulse
   package; pip install --no-cache-dir . ; copy data/raw, data/derived (metrics*.json,
   validation/, trial_locations.json, clock.json) and .kiro is NOT needed; copy
   web/dist from the web stage to /app/web/dist. ENV TP_AUDIT_PATH=/tmp/audit.sqlite3
   (writable on Render's free tier). EXPOSE 8000. CMD: uvicorn trialpulse.api.app:app
   --host 0.0.0.0 --port ${PORT:-8000} (use sh -c so $PORT expands; Render sets PORT).
   The app must work with no GEMINI_API_KEY (replay mode is the default).
2. .dockerignore: .venv, node_modules, web/node_modules, web/dist, .git, .kiro/runs,
   .pytest_cache, __pycache__, *.sqlite3, .env, .claude.
3. render.yaml (Blueprint): one web service, runtime docker, plan free, healthCheckPath
   /api/health, envVars: TP_LIVE_MODE "0" (GEMINI_API_KEY is set by the owner in the
   dashboard only if live mode is wanted; mark it sync: false).
4. Makefile with targets: test (.venv pytest), web (npm ci + build in web/), demo
   (python -m uvicorn trialpulse.api.app:app --port 8000), docker (docker build -t
   trialpulse . && docker run -p 8000:8000 trialpulse). Keep it simple.
5. .gitignore: add "!data/derived/clock.json" right after the
   "!data/derived/trial_locations.json" line (the clock cache must ship).
   In PulseStrip.tsx the <svg> has height="auto", which browsers reject (console error
   "<svg> attribute height: Expected length, 'auto'"): remove the height attribute and
   rely on viewBox + width 100% (add style={{ height: "auto" }} if needed).
When finished, list the files you created or changed and stop.
