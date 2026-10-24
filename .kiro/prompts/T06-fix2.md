Task T06-fix2: treat network failures like server errors in GeminiModel.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/agent/llm.py, tests/test_agent.py. Nothing else.

Seen in a real run: the Gemini server dropped the connection and the SDK raised
httpx.RemoteProtocolError ("Server disconnected without sending a response"), which is not
an errors.APIError, so it escaped GeminiModel and crashed the evidence loop instead of
retrying or falling back to the next model.

Fix: in the per-model call, also catch httpx.TransportError (the base class of
RemoteProtocolError, ConnectError, ReadTimeout and friends; httpx is installed as a
dependency of google-genai, import it inside the function like the SDK imports) and treat
it exactly like a retryable 5xx: back off with the injected sleep (2, 4), then move on to
the next model; record it as code "network" in the final LLMError message.
Add a test: a fake client whose first model raises httpx.RemoteProtocolError("boom")
every time and whose second model succeeds -> generate returns the second model's result
and name is the second model.

When finished, list the files you changed and stop.
