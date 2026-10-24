Task T10c: the evidence-seeking loop. When the gate holds a report, request exactly the
evidence that would settle it, add the replies as new timestamped records, redraft, and
gate again. With tests.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Read trialpulse/core/models.py, trialpulse/agent/report.py, trialpulse/agent/prompts.py,
trialpulse/agent/deid.py, trialpulse/gate/live.py, trialpulse/gate/negative_control.py
and trialpulse/data/generator.py first.

Files you may create: trialpulse/gate/evidence.py, tests/test_evidence.py.
You may edit: trialpulse/agent/report.py (add an optional `feedback: str | None = None`
parameter to draft_report, appended to the system prompt after any fault text) and
trialpulse/agent/prompts.py (add REDRAFT_TEMPLATE). Nothing else. Keep all tests passing.

Rules decide WHAT is requested; the model never chooses a request kind.
trialpulse/gate/evidence.py
  RULES: failed dimension prefix -> request kinds:
    "causal_restraint" -> ["predose_comparison", "symptom_checkin"]
    "negative_control" -> ["predose_comparison", "symptom_checkin"]
    "missing_data"     -> ["wear_reminder"]
    "uncertainty"      -> ["wear_reminder"] only if the participant has a non_wear signal
    "contradiction"    -> ["followup_question"]
    "recompute"        -> [] (no participant request; the redraft feedback asks to fix
                           the numbers)
    "temporal_consistency", "evidence_grounding" -> [] (feedback only)
  Use failed_dimensions(gate_result) from live.py; de-duplicate kinds per report.
  QUESTION_TEMPLATES (plain language, sent to the participant / site):
    symptom_checkin: "Since day {start_day}, have you had a fever, a cold, poor sleep or
      any other change in how you feel?"
    wear_reminder: "We are missing some days of device data. Could you wear the device
      tonight and let us know if anything stopped you wearing it?"
    followup_question: "Your diary says you feel very tired while your device readings
      look normal. Can you tell us more about what has been going on?"
    predose_comparison: "Attach the participant's pre-dose comparison to the report."
    trial_level_alert: "{n} participants show the same change in {metrics} starting around
      day {start_day}. Review at trial level."
  plan_requests(trial, report, gate_result, signals, now) -> list[EvidenceRequest]:
    request_id f"REQ-{report.report_id}-{kind}", failed_dimension = the first failing
    prefix that produced the kind, sent_at = now, status "open". Add one
    trial_level_alert (participant_id "TRIAL") when >= 2 participants have drift signals
    on a common metric as of report.as_of and this report's participant is one of them.
  SCRIPTED_REPLIES: dict[(participant_id, kind)] -> text, for synthetic participants only:
    ("P-07","symptom_checkin"): "I've had a cold since day 11: sore throat, blocked nose,
      and I slept badly."
    ("P-20","symptom_checkin"): "Congestion and poor sleep since about day 11."
    ("P-31","followup_question"): "I've been on night shifts all week. I feel wiped out,
      but no other symptoms."
    default for wear_reminder: "Sorry, my charger broke. I'll wear it again from tonight."
    default for symptom_checkin: "No new symptoms to report."
    default for followup_question: "Nothing else has changed."
  answer_requests(requests, now) -> tuple[list[Reading], list[EvidenceRequest]]: for each
    request of kind symptom_checkin / wear_reminder / followup_question with a participant
    (not "TRIAL"), create Reading(record_id=f"{pid}-reply-{kind}-{now:%Y%m%d%H%M}",
    kind="subjective", name="symptom_note", value=<reply text>, unit=None,
    event_time=now, recorded_at=now, source="simulated_reply", participant_id=pid,
    site_id=<participant's site>) and return the request updated with
    reply_record_id and status "answered". predose_comparison and trial_level_alert get
    status "answered" with no reading. (answer_requests needs the trial to look up the
    site: make the signature answer_requests(trial, requests, now).)
  build_feedback(gate_result, requests, nc_summary: dict | None) -> str: fill
    REDRAFT_TEMPLATE with the failing checks' explanations (one per line), the new
    evidence (each reply text with its record_id), and, if given, a one-line pre-dose /
    trial-wide comparison from negative_control_summary (blind-safe wording; never this
    participant's arm).
  class LoopResult(BaseModel): drafts: list[Report], gates: list[GateResult],
    requests: list[EvidenceRequest], replies: list[Reading], final_verdict: str
  run_loop(trial, participant_id, as_of, model, fault=None, max_rounds=2) -> LoopResult:
    round 1 = signals = detect(trial, as_of); draft_report(..., fault=fault, report_seq=1);
    gate_report. While the verdict is "hold" and rounds < max_rounds:
    now = as_of + 30 minutes * round; requests = plan_requests(...);
    replies, requests = answer_requests(trial, requests, now);
    trial = trial.model_copy(update={"readings": trial.readings + replies});
    feedback = build_feedback(...); redraft with draft_report(trial, pid, now, signals,
    model, fault=None, feedback=feedback, report_seq=round+1) and gate it at that as_of.
    The fault is applied to the first draft only (it simulates the raw agent's mistake).
    final_verdict = the last gate verdict.

prompts.py REDRAFT_TEMPLATE (a str with {held_reasons} and {new_evidence} and
{comparison} placeholders): "Your previous draft was held by the reliability gate for
these reasons:\n{held_reasons}\nNew evidence now available:\n{new_evidence}\n{comparison}\n
Rewrite the report. Every claim must be supported by the cited records. Do not attribute
any change to the study drug; describe timing as an association only. State missing data
and any conflict between the wearable and the diary explicitly."

tests/test_evidence.py (no network; a FakeModel that returns a causal claim on its first
call and, on its second call, a clean claim that cites the reply record id it finds in the
user prompt; generate(7); P-07 at day 15 23:00):
 - run_loop(..., fault="causal_overclaim") ends with final_verdict "pass" after 2 drafts.
 - the requests include symptom_checkin and predose_comparison and a trial_level_alert;
   every request kind is in RULES' values or "trial_level_alert".
 - exactly one reply Reading for P-07 exists, source "simulated_reply", recorded_at later
   than the original as_of, and the request that produced it has status "answered" and
   reply_record_id set.
 - the second system prompt the FakeModel received contains "held by the reliability gate"
   and does not contain the causal_overclaim fault text.
 - plan_requests for a gate result failing only "missing_data" returns only wear_reminder.

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
