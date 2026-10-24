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
