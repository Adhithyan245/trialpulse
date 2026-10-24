// The seven checkpoint rings (Scene 2) and how PulseEval gate dimensions map to
// them. A gate check dimension is of the form "<base>:<suffix>", where <base>
// is one of the PulseEval evaluator names below and <suffix> is either a claim
// id or the report id (for report-level checks).

import type { GateResult } from "./types";

export interface Ring {
  id: string;
  label: string;
  dims: string[];
  plain: string;
}

export const RINGS: Ring[] = [
  {
    id: "time",
    label: "Time",
    dims: ["temporal_consistency"],
    plain: "Only uses data that existed at report time",
  },
  {
    id: "evidence",
    label: "Evidence",
    dims: ["evidence_grounding"],
    plain: "Cites the right records",
  },
  {
    id: "numbers",
    label: "Numbers",
    dims: ["recompute"],
    plain: "Every number matches the records",
  },
  {
    id: "coverage",
    label: "Coverage",
    dims: ["missing_data"],
    plain: "Is honest about missing days",
  },
  {
    id: "conflict",
    label: "Conflict",
    dims: ["contradiction"],
    plain: "Names wearable vs diary conflicts",
  },
  {
    id: "certainty",
    label: "Certainty",
    dims: ["uncertainty"],
    plain: "Sounds as sure as the data allows",
  },
  {
    id: "causation",
    label: "Causation",
    dims: ["causal_restraint", "negative_control"],
    plain: "Never blames the drug without support",
  },
];

// The evaluator base name of a dimension (the part before the first ":").
function dimensionBase(dimension: string): string {
  const idx = dimension.indexOf(":");
  return idx === -1 ? dimension : dimension.slice(0, idx);
}

// The ring id that a gate dimension belongs to (null if unmapped).
export function ringForDimension(dimension: string): string | null {
  const base = dimensionBase(dimension);
  for (const ring of RINGS) {
    if (ring.dims.includes(base)) {
      return ring.id;
    }
  }
  return null;
}

// The claim id (the part after the first ":") carried by a dimension, or null
// when a dimension has no suffix.
export function claimIdOf(dimension: string): string | null {
  const idx = dimension.indexOf(":");
  return idx === -1 ? null : dimension.slice(idx + 1);
}

// Every gate check whose dimension suffix is the given claim id.
export function checksForClaim(gate: GateResult, claimId: string) {
  return gate.checks.filter((c) => claimIdOf(c.dimension) === claimId);
}

// Report-level checks: those whose suffix is the report id.
export function reportLevelChecks(gate: GateResult) {
  return gate.checks.filter((c) => claimIdOf(c.dimension) === gate.report_id);
}
