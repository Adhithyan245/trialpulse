Task T06-fix: model fallback and request timeouts for the Gemini free tier.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/agent/llm.py, tests/test_agent.py,
.kiro/steering/tech.md (one line only, see below). Nothing else.

What the reviewer saw with real calls: the free tier often returns 503 UNAVAILABLE
("high demand") for one model for minutes at a time, while other Flash models answer in
3-4 s; some models hang until a 504 after ~29 s. Today: gemini-3.5-flash 503,
gemini-3.7-flash 504, gemini-3.6-flash OK, gemini-3.5-flash-lite OK,
gemini-3.1-flash-lite OK.

Change GeminiModel:
1. Model list: read GEMINI_MODEL (primary) and optional GEMINI_FALLBACK_MODELS
   (comma-separated). Constructor arg `models: list[str] | None` overrides env.
   `name` must return the model that produced the most recent successful response
   (before any call: the primary).
2. Per model, retry 429/5xx with the injected sleep using back-off (2, 4) only, then move
   on to the next model. Raise LLMError only when every model has failed; the message
   lists each model and its last error code. Non-retryable client errors (4xx other than
   429) skip straight to the next model too (e.g. 404 "no longer available").
3. Create the client with a 45 s request timeout and disable the SDK's own retries, so
   our loop is the only retry policy:
       genai.Client(api_key=key, http_options=types.HttpOptions(
           timeout=45000, retry_options=types.HttpRetryOptions(attempts=1)))
   (timeout is in milliseconds; both classes exist in google.genai.types.)
4. Keep: invalid-JSON retry once per model; never return a fake object.
Tests to add: with a fake client where model "a" always raises APIError(503, {...}) and
model "b" succeeds, generate() returns b's result, name == "b", and sleep was called with
2 then 4; when all models fail, LLMError mentions both model names; a 404 on "a" moves to
"b" without sleeping. Keep the existing tests passing (adapt only constructor calls if
the signature change requires it, keeping their intent).

In .kiro/steering/tech.md replace the line starting "Model name from env GEMINI_MODEL." with:
"Model from env GEMINI_MODEL, optional fallbacks in GEMINI_FALLBACK_MODELS (comma-separated). Key from env GEMINI_API_KEY (loaded from .env). Never hard-code either."

When finished, list the files you changed and stop.
