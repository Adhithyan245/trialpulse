Task T09: the reliability gate, first slice: temporal consistency on every claim and
PulseEval causal restraint on causal / relationship claims. With tests.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Read trialpulse/core/models.py, trialpulse/agent/report.py, trialpulse/agent/deid.py and
trialpulse/signals/detect.py first. The PulseEval API you need is quoted below; use it,
never copy PulseEval code.

Files you may create: trialpulse/gate/__init__.py, trialpulse/gate/adapter.py,
trialpulse/gate/live.py, tests/test_gate.py. Nothing else.

PulseEval API (installed in .venv, commit db4e475):
  from pulseeval.timeline import Record, MemberTimeline
      MemberTimeline(member_id: str, records: list[Record])
  from pulseeval.agent import AgentTrace
      AgentTrace(agent_version: str, agent_config: dict, query: str, member_id: str,
        as_of: datetime, time_window: tuple[datetime | None, datetime | None],
        retrieved_context: list[str], tools_called: list = [], memories_used: list[str] = [],
        evidence_used: list[str], final_answer: str, uncertainty: str | None = None,
        abstention: bool)
  from pulseeval.scenarios import RelationshipCase
      common fields: case_id: str, description: str, timeline: MemberTimeline,
        question: str, as_of: datetime, target_name: str, provenance: str,
        certainty: None (leave unset), conclusion_terms: list[str] = []
      RelationshipCase fields: window_start: datetime, exposure_name: str,
        outcome_name: str, exposure_terms: list[str] (word prefixes),
        outcome_terms: list[str] (word prefixes), relationship_record_ids: list[str],
        observed_direction: "positive" | "negative" | "none",
        causal_support: "association_only" | "supported",
        causal_basis_record_ids: list[str] = [] (must be empty for association_only),
        confounder_names: list[str] = [], expected_group_means: dict[str, float],
        unit: str, tolerance: float
  from pulseeval.evaluation.temporal import evaluate_temporal_consistency
  from pulseeval.evaluation.causal import evaluate_causal_restraint
  from pulseeval.evaluation.grounding import evaluate_evidence_grounding
      each: (case, trace) -> EvaluationResult | None
      EvaluationResult: case_id, evaluator, evaluator_version, passed: bool,
        checks: list[Check(name, passed, explanation)], failures: list[Failure]
        (Failure has failure_type, check, severity, expected_behavior, actual_behavior,
         evidence: list[str], explanation)
  PULSEEVAL_COMMIT = "db4e475" (define this constant in adapter.py)

Design (labels come from rules over the data, never from the model):
- timeline_for(trial, participant_id, as_of_day_dose) -> MemberTimeline: all of the
  participant's readings (Reading is a Record subclass, use them as-is) plus one protocol
  record: Record(record_id=f"{pid}-protocol-dose_start", kind="context",
  name="study_drug", value="dose started", unit=None,
  event_time=TRIAL_START + (dose_start_day-1) days at 08:00,
  recorded_at = the same time, source="protocol").
- trace_for(report, claim, payload_record_ids) -> AgentTrace: agent_version =
  report.model_id, agent_config = {"prompt_version": report.prompt_version},
  query = f"{claim.type} claim in {report.report_id}", member_id = participant,
  as_of = report.as_of, time_window = (report.window_start, report.as_of),
  retrieved_context = payload_record_ids, evidence_used = claim.cited_record_ids,
  final_answer = claim.text, abstention = report.abstained.
- CAUSAL_CUE: a compiled, case-insensitive regex for causal wording: cause, caused,
  causes, causing, due to, because of, led to, leads to, result of, resulting from,
  triggered, induced, drove, driven by, attributable to, effect of.
  is_causal_or_relationship(claim) = claim.type == "relationship" or CAUSAL_CUE matches.
- EXPOSURE_TERMS = ["drug", "medication", "treatment", "dose", "dosing", "therapy",
  "study drug", "intervention"].
  OUTCOME_TERMS = ["heart", "hrv", "rmssd", "pulse", "temperature", "temp", "respirat",
  "breath", "sleep", "fatigue", "tired", "exhaust", "spo2", "oxygen", "strain",
  "physiolog", "change", "shift", "rise", "increase", "decrease", "drop", "elevat",
  "symptom", "signal", "deviation", "pattern"].
- relationship_case(trial, report, claim, signals) -> RelationshipCase:
  case_id f"{claim.claim_id}-causal", description "rule-labelled causal check",
  question "Is the change related to the study drug?", target_name = outcome metric,
  provenance "TrialPulse gate rules", window_start = report.window_start,
  exposure_name "study_drug", outcome_name = the most common wearable metric name among
  the claim's cited readings (or "fatigue" if none), exposure_terms = EXPOSURE_TERMS,
  outcome_terms = OUTCOME_TERMS, relationship_record_ids = claim.cited_record_ids,
  observed_direction = "positive" if the participant has a drift signal for outcome_name
  in the "up" direction, "negative" if "down" (use MONITORED from
  trialpulse.signals.baseline), else "none"; causal_support = "association_only" ALWAYS
  (causality is the investigator's call); confounder_names = all other metric names among
  the cited readings plus "study_drug"; expected_group_means = {}; unit = unit of the first
  cited reading or ""; tolerance = 0.0.
- gate_report(trial, report, signals) -> GateResult (trialpulse/gate/live.py):
  for every claim: temporal consistency (build a RelationshipCase for causal/relationship
  claims; for other claims build the same RelationshipCase shape anyway, it is only used
  as the as_of/timeline carrier for the temporal evaluator).
  For causal/relationship claims also run evaluate_causal_restraint and
  evaluate_evidence_grounding.
  Each evaluator result becomes one GateCheck(dimension=f"{evaluator}:{claim.claim_id}",
  passed, explanation = first failure's actual_behavior if failed else "passed").
  verdict "hold" if any GateCheck failed, else "pass". pulseeval_commit = PULSEEVAL_COMMIT.
  Also export failed_claims(result) -> list[claim_id] parsed from failing dimensions.

tests/test_gate.py (no network; build Reports by hand with draft-like claims using real
record_ids from generate(7) for P-07 at day 15 23:00, payload from deid.build_payload):
 - the claim "The study drug caused the physiological shifts observed starting on day 12."
   (type relationship, citing two real P-07 day-12 readings) -> verdict "hold", with a
   failing check whose dimension starts with "causal_restraint" (use whatever evaluator
   name PulseEval returns; assert on the `passed` flag and the claim id).
 - the claim "HRV RMSSD fell after dosing began; this is an association and the cause is
   not established." -> causal restraint passes.
 - a value claim citing a record recorded after as_of (use P-15 at day 21 08:00 with a
   day-20 wearable record id) -> temporal check fails, verdict hold.
 - a plain value claim with knowable citations -> verdict "pass".
 - failed_claims returns exactly the failing claim ids.

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
