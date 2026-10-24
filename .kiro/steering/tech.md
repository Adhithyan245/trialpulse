# Stack (do not add to it without asking)
Python 3.11, pydantic v2, pandas, numpy, pyarrow, FastAPI, uvicorn, google-genai, python-dotenv,
pytest, sqlite3 (stdlib)
pulseeval @ git+https://github.com/Adhithyan245/PulseEval@db4e475
Frontend: React + Vite + TypeScript, Tailwind, Recharts, motion, lucide-react, d3-geo,
three, @react-three/fiber, @react-three/drei. No state library.

LLM: Google Gemini via the google-genai SDK (from google import genai), structured JSON output.
Model from env GEMINI_MODEL, optional fallbacks in GEMINI_FALLBACK_MODELS (comma-separated). Key from env GEMINI_API_KEY (loaded from .env). Never hard-code either.
If the call fails, raise. Never return a fake or simulated response.

PulseEval: use pulseeval.timeline.Record and MemberTimeline, pulseeval.agent.AgentTrace,
pulseeval.scenarios (NumericCase, AssessmentCase, RelationshipCase) and
pulseeval.evaluation.* evaluators. Do not modify or copy PulseEval code.
Python environment: .venv in the repo root. Run tests with: .venv\Scripts\python -m pytest -q
Deploy: one container, FastAPI serves web/dist, Render.
