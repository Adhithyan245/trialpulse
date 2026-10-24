Task T19: the README judges will read first.

You cannot run shell commands or use the web in this project. Read
data/derived/metrics_validation.json, data/derived/metrics_public.json,
.kiro/steering/product.md, .kiro/steering/tech.md, .kiro/steering/design.md, Makefile,
render.yaml and the list of files under trialpulse/ and web/src/scenes/ first.

File you may create: README.md (repo root). Nothing else. Every number in it must come
from those two metrics files (quote them exactly) or be a count you can verify from the
repo. Do not invent numbers, users, partners or results.

Structure (plain, scannable, no emoji):
 1. "TrialPulse" + the line "The AI drafts. Deterministic checks verify. Humans decide."
    + one paragraph: what it is (wearable data for decentralized clinical trials; an AI
    drafts safety reports for a blinded medical monitor; every claim is checked by
    PulseEval before a human signs; when evidence is missing it asks the right participant
    the right question). Then: "Live demo: <LIVE_URL>" exactly as a placeholder line the
    owner will fill, and "Hackachusetts 2026 · Biotech & healthcare (challenges H1 and
    H5)".
 2. "Why": AI is starting to draft drug-safety narratives; it can confidently claim a drug
    caused harm when the data does not support it. Keep it to 3 sentences, no statistics
    that are not in the metrics files.
 3. "What we measured" table from metrics_validation.json: raw AI drafts held, clean (no
    injected fault) drafts held, passed after the evidence loop, still held, unsafe reports
    reaching the monitor, mean rounds, evidence requests, replies; the models used; and the
    note text. Then "Raw failures by check" from by_dimension.
 4. "How it works" as a numbered pipeline: signals (personal split-conformal bands,
    multi-signal drift, non-wear, diary conflict) -> de-identified, blinded payload ->
    Gemini drafts claims with citations -> the gate (PulseEval temporal consistency,
    evidence grounding, missing data, contradiction, uncertainty, causal restraint, plus
    TrialPulse's number recomputation and blind-safe negative-control check) -> evidence
    loop (rules choose the request; replies become timestamped records; redraft; re-gate)
    -> monitor signs -> hash-chained audit log.
 5. "The five scenes" one line each.
 6. "Real Massachusetts data" from metrics_public.json: recruiting trials, wearable-
    measurable trials, top cities (Boston and Springfield counts), environmental-justice
    block groups, heart-failure readmissions above expected (heart_failure_above_1 of the
    READM-30-HF-HRRP with_ratio count). Name the sources: ClinicalTrials.gov, MassGIS,
    CDC PLACES, CMS, US Census Bureau.
 7. "Run it": make demo (replay mode, no API key), make test, make docker; live mode needs
    GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FALLBACK_MODELS in .env and TP_LIVE_MODE=1;
    Render: render.yaml blueprint.
 8. "Built with Kiro": the spec-driven workflow: steering files in .kiro/steering, one
    prompt file per task in .kiro/prompts (count them), every task reviewed with tests
    before commit. Do not claim anything about credits.
 9. "Honest limits": synthetic participants (labelled on every screen); simulated
    participant replies; PulseEval is our own MIT-licensed library built before the event
    (github.com/Adhithyan245/PulseEval, pinned commit db4e475) and used as a dependency;
    the free Gemini tier; the FDA AI-credibility guidance referenced is a draft; not a
    medical device; no clinical decisions are made by the software.
10. License: MIT (note that a LICENSE file should be added by the owner if missing).
When finished, list the file you created and stop.
