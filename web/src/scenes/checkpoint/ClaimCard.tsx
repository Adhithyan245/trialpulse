import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { Claim } from "../../types";

interface ClaimCardProps {
  claim: Claim;
  status?: "normal" | "stopped";
  reason?: string;
  fullExplanation?: string;
}

export function ClaimCard({
  claim,
  status = "normal",
  reason,
  fullExplanation,
}: ClaimCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [textExpanded, setTextExpanded] = useState(false);

  const isLongText = claim.text.length > 150;
  const displayText = textExpanded || !isLongText
    ? claim.text
    : claim.text.slice(0, 150) + "...";

  const shortReason = reason && reason.length > 160
    ? reason.slice(0, 160) + "..."
    : reason;

  return (
    <div
      className={`rounded-lg border p-3 shadow-sm transition-colors ${
        status === "stopped"
          ? "border-held bg-held-soft"
          : "border-line bg-card"
      }`}
    >
      <div className="space-y-2">
        <div className="text-sm">
          {displayText}
          {isLongText && (
            <button
              type="button"
              onClick={() => setTextExpanded(!textExpanded)}
              className="ml-2 text-accent hover:underline focus:underline"
            >
              {textExpanded ? "Less" : "More"}
            </button>
          )}
        </div>

        {claim.cited_record_ids.length > 0 && (
          <div className="text-xs text-muted font-mono tabular-nums">
            {claim.cited_record_ids.length} record
            {claim.cited_record_ids.length !== 1 ? "s" : ""} cited
          </div>
        )}

        {status === "stopped" && reason && (
          <div className="border-t border-held pt-2 mt-2">
            <div className="text-sm text-held font-medium">
              {shortReason}
            </div>
            {fullExplanation && fullExplanation !== reason && (
              <button
                type="button"
                onClick={() => setExpanded(!expanded)}
                className="mt-1 inline-flex items-center gap-1 text-xs text-held hover:underline focus:underline"
              >
                {expanded ? (
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
            )}
            {expanded && fullExplanation && (
              <div className="mt-2 text-xs text-held whitespace-pre-wrap">
                {fullExplanation}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
