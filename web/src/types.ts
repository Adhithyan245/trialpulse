// TypeScript types mirroring the FastAPI backend (trialpulse/api/app.py).

export type Role = "monitor" | "coordinator" | "safety_reviewer";

export interface Participant {
  participant_id: string;
  site_id: string;
  arm?: "A" | "B"; // only present for the safety_reviewer role
}

export interface Site {
  site_id: string;
  city: string;
  county: string;
}

export interface Trial {
  days: number;
  dose_start_day: number;
  sites: Site[];
  participants: Participant[];
  synthetic: boolean;
}

export interface ClockParticipant {
  participant_id: string;
  site_id: string;
  resting_hr: number | null;
  worn: boolean;
  drift: boolean;
  non_wear: boolean;
  diary_conflict: boolean;
}

export interface ClockDay {
  day: number;
  participants: ClockParticipant[];
}

export interface Clock {
  days: ClockDay[];
}

export type ClaimType =
  | "value"
  | "coverage"
  | "assessment"
  | "relationship"
  | "certainty";

export interface Claim {
  claim_id: string;
  type: ClaimType;
  text: string;
  cited_record_ids: string[];
}

export interface Report {
  report_id: string;
  participant_id: string;
  as_of: string;
  window_start: string;
  window_end: string;
  claims: Claim[];
  abstained: boolean;
  model_id: string;
  prompt_version: string;
}

export interface GateCheck {
  dimension: string;
  passed: boolean;
  explanation: string;
}

export interface GateResult {
  report_id: string;
  verdict: "pass" | "hold";
  checks: GateCheck[];
  pulseeval_commit: string;
}

export type EvidenceKind =
  | "symptom_checkin"
  | "wear_reminder"
  | "followup_question"
  | "predose_comparison"
  | "trial_level_alert";

export interface EvidenceRequest {
  request_id: string;
  report_id: string;
  participant_id: string;
  failed_dimension: string;
  kind: EvidenceKind;
  question_text: string;
  sent_at: string;
  reply_record_id: string | null;
  status: "open" | "answered";
}

export interface Reading {
  record_id: string;
  kind: string;
  name: string;
  value: number | string;
  unit: string | null;
  event_time: string;
  recorded_at: string;
  source: string;
  participant_id: string;
  site_id: string;
}

export interface RunSummary {
  case_id: string;
  participant_id: string;
  day: number;
  fault: string | null;
  raw_verdict: "pass" | "hold";
  final_verdict: "pass" | "hold";
  rounds: number;
  models_used: string[];
}

export interface RunPipeline {
  drafts: Report[];
  gates: GateResult[];
  requests: EvidenceRequest[];
  replies: Reading[];
  final_verdict: "pass" | "hold";
  rounds: number;
}

export interface RunRaw {
  report: Report;
  gate: GateResult;
  verdict: "pass" | "hold";
  failed: string[];
}

export interface RunRecord {
  case_id: string;
  participant_id: string;
  day: number;
  fault: string | null;
  ground_truth_note: string;
  raw: RunRaw;
  pipeline: RunPipeline;
  models_used: string[];
  recorded?: boolean;
}

export interface AuditEntry {
  entry_id: string;
  ts: string;
  actor_role: "system" | "monitor" | "coordinator" | "safety_reviewer";
  action:
    | "drafted"
    | "gated"
    | "evidence_requested"
    | "evidence_received"
    | "approved"
    | "rejected"
    | "redraft_requested";
  report_id: string;
  details_json: string;
  prev_hash: string;
  entry_hash: string;
}

export interface PublicMetrics {
  total_trials: number;
  by_phase: Record<string, number>;
  wearable_measurable_trials: number;
  trials_with_ma_city: number;
  top_cities: Array<[string, number]>;
  ej_block_groups: number;
  ej_municipalities: number;
  trials_in_ej_municipalities: number;
  short_sleep_by_county: Record<string, number>;
  readmissions: {
    hospitals: number;
    measures: Record<string, { with_ratio: number; above_1: number }>;
    heart_failure_above_1: number;
  };
}

export interface Metrics {
  public: PublicMetrics | null;
  validation: ValidationMetrics | null;
}

export interface ValidationMetrics {
  cases: number;
  models_used: string[];
  raw: {
    held: number;
    reached_monitor_unchecked: number;
    by_dimension: Record<string, number>;
  };
  pipeline: {
    passed_after_loop: number;
    still_held: number;
    unsafe_reaching_monitor: number;
    mean_rounds: number;
    evidence_requests: number;
    replies: number;
  };
  fault_cases: { raw_held: number; total: number };
  clean_cases: { raw_held: number; total: number };
  note: string;
}

export interface Health {
  ok: boolean;
  mode: "live" | "replay";
}

export interface AuditVerify {
  ok: boolean;
  checked: number;
  first_bad_entry_id: string | null;
  reason: string | null;
}

export interface TrialRow {
  nct_id: string;
  title: string;
  phase_label: string;
  conditions: string;
  wearable_measurable: boolean;
  cities: string[];
}

export interface TrialsResponse {
  total: number;
  trials: TrialRow[];
}
