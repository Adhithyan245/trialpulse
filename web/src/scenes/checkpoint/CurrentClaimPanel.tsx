import { useState } from "react";
import { ChevronDown, ChevronUp, Check, X, Minus } from "lucide-react";
import { RINGS, ringForDimension, checksForClaim } from "../../checks";
import type { Claim, GateResult } from "../../types";

interface CurrentClaimPanelProps {
  claim: Claim;
  gate: GateResult;
}

export function CurrentClaimPanel({ claim, gate }: CurrentClaimPanelProps) {
  const [detailsExpanded, setDetailsExpanded] = useState(false);

  const claimChecks = checksForClaim(gate, claim.claim_id);
  const failedCheck = claimChecks.find((c) => !c.passed);
  
  // Build status for each ring
  const ringStatuses = RINGS.map((ring) => {
    const checkForRing = claimChecks.find((c) => ringForDimension(c.dimension) === ring.id);
    
    if (!checkForRing) {
      return { ringId: ring.id, label: ring.label, status: "na" as const };
    }
    
    return {
      ringId: ring.id,
      label: ring.label,
      status: checkForRing.passed ? ("pass" as const) : ("held" as const),
      explanation: checkForRing.explanation,
    };
  });

  // Extract first sentence from failed check explanation
  const failedReason = failedCheck
    ? failedCheck.explanation.split(/[.!?]/)[0] + "."
    : null;

  const shortReason = failedReason && failedReason.length > 160
    ? failedReason.slice(0, 160) + "..."
    : failedReason;

  const isStopped = !!failedCheck;

  return (
    <div className={`rounded-lg border p-4 ${isStopped ? "border-held bg-held-soft" : "border-line bg-card"}`}>
      <div className="space-y-3">
        <div>
          <h3 className="text-sm font-semibold text-text mb-2">Current claim</h3>
          <p className="text-sm text-text">{claim.text}</p>
        </div>

        {claim.cited_record_ids.length > 0 && (
          <div className="text-xs text-muted">
            <span className="font-mono tabular-nums">
              {claim.cited_record_ids.length} record
              {claim.cited_record_ids.length !== 1 ? "s" : ""} cited
            </span>
          </div>
        )}

        {/* Status chips for each ring */}
        <div className="flex flex-wrap gap-2">
          {ringStatuses.map((rs) => (
            <div
              key={rs.ringId}
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs ${
                rs.status === "pass"
                  ? "border-pass bg-pass-soft text-pass"
                  : rs.status === "held"
                  ? "border-held bg-held-soft text-held"
                  : "border-line bg-surface text-muted"
              }`}
              title={rs.label}
            >
              {rs.status === "pass" && <Check className="h-3 w-3" />}
              {rs.status === "held" && <X className="h-3 w-3" />}
              {rs.status === "na" && <Minus className="h-3 w-3" />}
              <span>{rs.label}</span>
            </div>
          ))}
        </div>

        {/* Held reason and details */}
        {isStopped && shortReason && (
          <div className="border-t border-held pt-3 space-y-2">
            <div className="text-sm text-held font-medium">
              {shortReason}
            </div>
            {failedCheck && failedCheck.explanation !== shortReason && (
              <>
                <button
                  type="button"
                  onClick={() => setDetailsExpanded(!detailsExpanded)}
                  className="inline-flex items-center gap-1 text-xs text-held hover:underline focus:underline"
                >
                  {detailsExpanded ? (
                    <>
                      <ChevronUp className="h-3 w-3" />
                      Hide details
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-3 w-3" />
                      Details
                    </>
                  )}
                </button>
                {detailsExpanded && (
                  <div className="text-xs text-held whitespace-pre-wrap">
                    {failedCheck.explanation}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
