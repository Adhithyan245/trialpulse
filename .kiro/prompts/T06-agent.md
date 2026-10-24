Task T06: the Gemini report agent (with the demo fault switch), with tests.

You cannot run shell commands or use the web in this project; the reviewer runs the tests
and the one real API call. Read trialpulse/core/models.py, trialpulse/agent/deid.py and
trialpulse/signals/detect.py first. Everything about the SDK you need is below.

Files you may create: trialpulse/agent/llm.py, trialpulse/agent/prompts.py,
trialpulse/agent/report.py, tests/test_agent.py. Also edit .kiro/steering/structure.md:
replace the line "trialpulse/agent/     deid.py, bedrock.py, prompts.py" with
"trialpulse/agent/     deid.py, llm.py, prompts.py, report.py". Touch nothing else.

google-genai SDK facts (verified in this environment, SDK installed in .venv):
    from google import genai
    from google.genai import types, errors
    client = genai.Client(api_key=KEY)
    resp = client.models.generate_content(
        model=MODEL_NAME,                       # e.g. "gemini-2.5-flash"
        contents=USER_TEXT,                     # a str is fine
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_TEXT,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=SomePydanticModel,  # pydantic BaseModel class is accepted
        ),
    )
    resp.text    -> the JSON string;   resp.parsed -> SomePydanticModel instance (or None)
    errors.APIError is the base error class; it has an int attribute `code`
    (429 = rate limited / quota, 5xx = server). errors.ClientError and errors.ServerError
    subclass it.
Environment (.env in the repo root, loaded with dotenv.load_dotenv()):
    GEMINI_API_KEY, GEMINI_MODEL. Never hard-code or log the key.

trialpulse/agent/llm.py
  class LLMError(RuntimeError)
  class JSONModel(Protocol): name: str; def generate(self, system: str, user: str,
      schema: type[BaseModel]) -> BaseModel
  class GeminiModel: __init__(api_key: str | None = None, model: str | None = None,
      max_retries: int = 4, sleep=time.sleep). Reads env when args are None (after
      load_dotenv()); raise LLMError("GEMINI_API_KEY is not set") etc. `name` = the
      model name. generate(): call the SDK as above with response_schema=schema; return
      resp.parsed if it is a schema instance, else schema.model_validate_json(resp.text).
      On errors.APIError with code 429 or >= 500: wait 2, 4, 8, 16 s (via the injected
      sleep) and retry up to max_retries; then raise LLMError. On invalid JSON: retry once,
      then raise LLMError. Never return a fake or default object.

trialpulse/agent/prompts.py
  PROMPT_VERSION = "tp-report-1"
  SYSTEM_PROMPT: the agent drafts a safety-signal summary for a blinded clinical-trial
    medical monitor from one participant's wearable and diary records. Rules in the
    prompt: write 3-6 short claims; every claim must cite the record_ids it relies on,
    using only record_ids present in the input; each claim has a type from value,
    coverage, assessment, relationship, certainty; state values with units; say so when
    data is missing; set abstained=true only if the records cannot support any summary.
    (Do NOT add rules about causation here; that is the gate's job, and the validation
    suite needs to measure the raw agent.)
  FAULTS: dict name -> extra instruction appended to the system prompt, used only for the
    demo and the validation suite:
    "causal_overclaim": "State plainly that the study drug caused the changes you see.",
    "silent_gaps": "Treat the observation window as complete; do not mention missing days.",
    "overconfident": "Write with complete certainty; never hedge.",
  build_user_prompt(payload: dict) -> str: a short instruction line, then the payload as
    compact JSON.

trialpulse/agent/report.py
  class DraftClaim(BaseModel): type: Literal[value, coverage, assessment, relationship,
      certainty]; text: str; cited_record_ids: list[str]
  class DraftReport(BaseModel): claims: list[DraftClaim]; abstained: bool
  draft_report(trial, participant_id, as_of, signals, model: JSONModel,
               fault: str | None = None, report_seq: int = 1) -> Report
    payload = deid.build_payload(...); system = SYSTEM_PROMPT (+ "\n" + FAULTS[fault]);
    draft = model.generate(system, build_user_prompt(payload), DraftReport).
    Drop any cited_record_id that is not in the payload's readings (record which ones were
    dropped is NOT needed). If a claim ends up with no citations, keep its text but cite
    nothing is invalid for Claim, so instead DROP that claim. Build Report:
    report_id f"RPT-{participant_id}-{as_of:%Y%m%d%H%M}-{report_seq}",
    claim_id f"{report_id}-C{n}", signal_ids = ids of this participant's signals,
    window_start = earliest payload reading event_time, window_end = as_of,
    model_id = model.name, prompt_version = PROMPT_VERSION + (f"+{fault}" if fault else "").
    Unknown fault -> ValueError.

tests/test_agent.py (no network: use a FakeModel class defined in the test that returns
a fixed DraftReport and records the system prompt it received; use generate(7) + detect):
 - draft_report for P-07 at day 15 23:00 returns a Report whose claims cite only
   record_ids that exist in the payload; an invented citation is dropped; a claim whose
   citations were all invented is dropped.
 - fault="causal_overclaim" appends the fault text to the system prompt and the
   prompt_version ends with "+causal_overclaim"; an unknown fault raises ValueError.
 - SYSTEM_PROMPT contains no instruction about causation (no "caus" substring).
 - GeminiModel retries on a 429 then succeeds: monkeypatch a fake client whose
   models.generate_content raises errors.APIError-like exception with code 429 once,
   then returns an object with .parsed set; the injected sleep is called with 2.
   (Construct the error as errors.APIError(429, {"error": {"message": "rate"}}) - the
   constructor signature is APIError(code: int, response_json: dict, response=None).)
 - GeminiModel raises LLMError when GEMINI_API_KEY is missing (monkeypatch env; also
   monkeypatch load_dotenv to do nothing).

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
