import { motion } from "motion/react";
import { Check, X } from "lucide-react";
import { RINGS, ringForDimension, checksForClaim } from "../../checks";
import type { GateResult, Claim } from "../../types";
import type { SequenceStep } from "./useSequence";

interface RingTunnelProps {
  draft: { claims: Claim[]; report_id: string };
  gate: GateResult;
  step: SequenceStep;
  reducedMotion: boolean;
}

// Claim ids look like "RPT-P-07-202610052300-1-C1"; show only the trailing
// "C1" on chips (full id stays in the title attribute) so rows do not overflow.
function shortClaimLabel(claimId: string): string {
  const parts = claimId.split("-");
  return parts[parts.length - 1] || claimId;
}

export function RingTunnel({ draft, gate, step, reducedMotion }: RingTunnelProps) {
  // Determine which claim is currently traveling
  const travelingClaimIndex = step.type === "travel" ? step.claimIndex : -1;
  const travelingRingIndex = step.type === "travel" ? step.ringIndex : -1;
  const travelingClaim = travelingClaimIndex >= 0 ? draft.claims[travelingClaimIndex] : null;

  // Find which claims stopped at each gate
  const claimsStoppedAtRing: Record<string, string[]> = {};
  if (step.type === "verdict" || step.type === "requesting" || step.type === "received" || step.type === "desk") {
    for (const claim of draft.claims) {
      const claimChecks = checksForClaim(gate, claim.claim_id);
      const failedCheck = claimChecks.find((c) => !c.passed);
      if (failedCheck) {
        const ringId = ringForDimension(failedCheck.dimension);
        if (ringId) {
          if (!claimsStoppedAtRing[ringId]) claimsStoppedAtRing[ringId] = [];
          claimsStoppedAtRing[ringId].push(claim.claim_id);
        }
      }
    }
  }

  // Calculate claim position on the track
  const getClaimPosition = (): string => {
    if (step.type !== "travel") return "0%";
    // Position percentages: before first gate, then centered on each gate 1-7
    // Gates are at roughly: 7%, 21%, 35%, 50%, 64%, 78%, 93%
    const positions = ["0%", "7%", "21%", "35%", "50%", "64%", "78%", "93%"];
    return positions[travelingRingIndex + 1] || "0%";
  };

  // Determine if claim is stopped
  const isClaimStopped = (() => {
    if (!travelingClaim) return false;
    const claimChecks = checksForClaim(gate, travelingClaim.claim_id);
    const failedCheck = claimChecks.find((c) => !c.passed);
    if (!failedCheck) return false;
    
    const failedRingId = ringForDimension(failedCheck.dimension);
    const failedRingIndex = RINGS.findIndex((r) => r.id === failedRingId);
    return failedRingIndex === travelingRingIndex;
  })();

  // Queue: claims waiting to travel
  const queueClaims = (() => {
    if (step.type === "intro") {
      // At intro, show all claims from this draft
      return draft.claims;
    }
    if (step.type === "travel") {
      // During travel, show next few claims (up to 3)
      return draft.claims.slice(travelingClaimIndex + 1, travelingClaimIndex + 4);
    }
    return [];
  })();

  // Cleared: claims that passed all checks
  const clearedClaims = (() => {
    if (step.type === "intro") return [];
    
    const cleared: Claim[] = [];
    const maxClaimIndex = step.type === "travel" ? travelingClaimIndex - 1 : draft.claims.length - 1;
    
    for (let i = 0; i <= maxClaimIndex; i++) {
      const claim = draft.claims[i];
      const claimChecks = checksForClaim(gate, claim.claim_id);
      const hasFailed = claimChecks.some((c) => !c.passed);
      if (!hasFailed) {
        cleared.push(claim);
      }
    }
    return cleared;
  })();

  // Check status for each ring and traveling claim
  const getRingStatus = (ringId: string, ringIndex: number): "pass" | "held" | "neutral" => {
    if (!travelingClaim || step.type !== "travel") return "neutral";
    
    const claimChecks = checksForClaim(gate, travelingClaim.claim_id);
    const checkForRing = claimChecks.find((c) => ringForDimension(c.dimension) === ringId);
    
    if (!checkForRing) return "neutral"; // n/a for this claim
    
    if (ringIndex < travelingRingIndex) {
      return checkForRing.passed ? "pass" : "held";
    } else if (ringIndex === travelingRingIndex) {
      return checkForRing.passed ? "pass" : "held";
    }
    
    return "neutral";
  };

  return (
    <div className="space-y-4">
      {/* Queue and Cleared indicators */}
      <div className="flex items-center justify-between text-xs text-muted">
        <div className="flex items-center gap-2">
          <span>Queue:</span>
          <div className="flex flex-wrap gap-1">
            {queueClaims.map((claim) => (
              <div
                key={claim.claim_id}
                title={claim.claim_id}
                className="rounded border border-line bg-card px-2 py-0.5 font-mono"
              >
                {shortClaimLabel(claim.claim_id)}
              </div>
            ))}
            {queueClaims.length === 0 && <span className="text-muted">—</span>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span>Cleared:</span>
          <div className="flex flex-wrap gap-1">
            {clearedClaims.map((claim) => (
              <div
                key={claim.claim_id}
                title={claim.claim_id}
                className="rounded border border-pass bg-pass-soft px-2 py-0.5 font-mono text-pass"
              >
                {shortClaimLabel(claim.claim_id)}
              </div>
            ))}
            {clearedClaims.length === 0 && <span className="text-muted">—</span>}
          </div>
        </div>
      </div>

      {/* The tunnel with gates and track */}
      <div className="relative">
        {/* Horizontal track line - only on desktop */}
        <div 
          className="absolute left-0 right-0 h-0.5 bg-line hidden lg:block"
          style={{ top: "100px" }}
        />

        {/* Gates in horizontal row at >= 1024px, stacked below */}
        <div className="grid grid-cols-3 gap-4 lg:gap-2 lg:grid-cols-7">
          {RINGS.map((ring, ringIndex) => {
            const status = getRingStatus(ring.id, ringIndex);
            const stoppedClaims = claimsStoppedAtRing[ring.id] || [];
            
            let borderColor = "border-line";
            if (status === "pass") borderColor = "border-pass";
            if (status === "held") borderColor = "border-held";

            return (
              <div key={ring.id} className="flex flex-col items-center">
                {/* Gate visual - tall vertical capsule */}
                <div
                  className={`relative flex items-center justify-center rounded-full border-2 transition-colors ${borderColor}`}
                  style={{ width: "56px", height: "200px" }}
                  title={ring.plain}
                >
                  {status === "pass" && (
                    <Check className="h-5 w-5 text-pass" aria-hidden="true" />
                  )}
                  {status === "held" && (
                    <X className="h-5 w-5 text-held" aria-hidden="true" />
                  )}
                  <span className="sr-only">{ring.plain}</span>
                </div>

                {/* Gate label */}
                <div className="mt-2 text-center">
                  <div className="text-sm font-medium text-text">{ring.label}</div>
                </div>

                {/* Stopped claims under this gate */}
                {stoppedClaims.length > 0 && (
                  <div className="mt-2 flex flex-wrap justify-center gap-1">
                    {stoppedClaims.map((claimId) => (
                      <div
                        key={claimId}
                        title={claimId}
                        className="rounded border border-held bg-held-soft px-2 py-0.5 text-xs font-mono text-held"
                      >
                        {shortClaimLabel(claimId)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Traveling claim token - only on desktop */}
        {travelingClaim && step.type === "travel" && (
          <motion.div
            className={`absolute hidden lg:flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium shadow-md ${
              isClaimStopped
                ? "border-held bg-held-soft text-held"
                : "border-line bg-card text-text"
            }`}
            style={{
              top: "88px",
              left: "0",
              maxWidth: "200px",
            }}
            animate={{ left: getClaimPosition() }}
            transition={{
              duration: reducedMotion ? 0 : 0.6,
              ease: "easeInOut",
            }}
          >
            <span className="font-mono">{travelingClaim.claim_id}</span>
            <span className="truncate">
              {travelingClaim.text.slice(0, 30)}
              {travelingClaim.text.length > 30 ? "..." : ""}
            </span>
          </motion.div>
        )}
      </div>
    </div>
  );
}
