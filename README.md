# TrialPulse

The AI drafts. Deterministic checks verify. Humans decide.

TrialPulse brings wearable data into decentralized clinical trials. An AI agent drafts
safety-signal reports from participants' wearable readings and diaries for a blinded
medical monitor. Every claim is checked by PulseEval before a human signs, and when the
evidence behind a claim is missing, the system asks the right participant the right
question and redrafts from the reply.

Live demo: https://trialpulse-n8gd.onrender.com
(free hosting: the first visit after a quiet period can take up to a minute to wake the server)

Hackachusetts 2026 · Biotech & healthcare (challenges H1 and H5)

## Why

AI is starting to draft drug-safety narratives, and that saves monitors real time. But an
AI can confidently claim a drug caused harm when the underlying readings do not support it.
TrialPulse puts a deterministic reliability gate between the draft and the human, so an
unsupported claim is caught and sent back for evidence instead of reaching the monitor.

## What we measured

Measured with PulseEval checks (commit db4e475) on synthetic data; numbers come from the
recorded runs in data/derived/validation.

| Metric | Value |
| --- | --- |
| Raw AI drafts held (no gate corrections applied) | 11 of 12 |
| Clean drafts (no injected fault) held | 5 of 6 |
| Fault drafts held | 6 of 6 |
| Passed after the evidence loop | 9 |
| Still held after the loop | 3 |
| Unsafe reports reaching the monitor | 0 |
| Raw unchecked drafts that would reach the monitor | 12 |
| Mean rounds | 2.25 |
| Evidence requests | 19 |
| Replies | 12 |
| Model used | gemini-3.5-flash-lite |

### Raw failures by check

| Check | Failures |
| --- | --- |
| uncertainty | 6 |
| negative_control | 4 |
| causal_restraint | 3 |
| missing_data | 2 |
| contradiction | 2 |
| recompute | 1 |

## How it works

1. Signals: per-participant personal split-conformal bands, multi-signal drift detection,
   non-wear detection, and diary conflict detection flag candidate safety signals.
2. The flagged signals become a de-identified, blinded payload.
3. Gemini drafts claims, each citing the record_ids behind it.
4. The gate runs PulseEval temporal consistency, evidence grounding, missing data,
   contradiction, uncertainty, and causal restraint, plus TrialPulse's own number
   recomputation and blind-safe negative-control check.
5. Evidence loop: rules choose which request to send; replies come back as timestamped
   records; the agent redrafts and the draft is re-gated.
6. The medical monitor signs the report with a reason.
7. The signed report is written to a hash-chained audit log.

## The five scenes

1. The trial, alive: 3D Massachusetts with one beacon per participant pulsing at their
   resting heart rate, amber when outside the personal band.
2. The checkpoint: a tunnel of seven rings, one per PulseEval check, where failed claim
   cards stop and show a plain-language reason.
   Try to fool the checkpoint: type your own claim about a participant (for example 'The study drug caused P-07's HRV drop') and the same deterministic checks judge it instantly, with no AI call.
3. Sign and seal: the monitor signs and the report becomes a block on a linked chain; a
   tamper button breaks the chain from that block on.
4. How this was verified: per claim, the cited readings, the recomputed number next to the
   AI's number, and the pre-drug comparison.
5. Proof it works: the validation scorecard, the FDA credibility panel, and the trial
   finder on real data.

## Real Massachusetts data

- Recruiting trials: 3131 (ClinicalTrials.gov)
- Wearable-measurable trials: 446 (ClinicalTrials.gov)
- Top cities: Boston 2622, Springfield 84 (ClinicalTrials.gov)
- Environmental-justice block groups: 2604 (MassGIS)
- Heart-failure 30-day readmissions above expected: 35 of 51 hospitals with a ratio
  (READM-30-HF-HRRP) (CMS)

Sources: ClinicalTrials.gov, MassGIS, CDC PLACES, CMS, US Census Bureau.

## Run it

- `make demo` runs the demo in replay mode with no API key.
- `make test` runs the test suite.
- `make docker` builds and runs the container.

Live mode needs `GEMINI_API_KEY`, `GEMINI_MODEL`, and `GEMINI_FALLBACK_MODELS` in a `.env`
file, plus `TP_LIVE_MODE=1`.

Render: deploy with the `render.yaml` blueprint.

## Built with Kiro

TrialPulse was built with a spec-driven workflow in Kiro. Steering files in
`.kiro/steering` hold the product, tech, design, structure, and guardrail rules that apply
to every task. Each task has its own prompt file in `.kiro/prompts` (50 prompt files), and
every task was reviewed with tests before commit.

## Honest limits

- Participants are synthetic and labelled "Synthetic data" on every screen.
- Participant replies in the evidence loop are simulated and labelled as simulated.
- PulseEval is our own MIT-licensed library, built before the event
  (github.com/Adhithyan245/PulseEval, pinned commit db4e475) and used here as a dependency.
- The demo runs on the free Gemini tier.
- The FDA AI-credibility guidance referenced is a draft.
- TrialPulse is not a medical device, and no clinical decisions are made by the software.

## License

MIT.
