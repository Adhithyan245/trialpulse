import { useState } from "react";
import { StatusPill } from "./StatusPill";
import { RINGS, checksForClaim, reportLevelChecks, ringForDimension } from "../checks";
import { tryIt } from "../api";
import type { Report, GateResult, TryItResponse } from "../types";

interface Scenario {
  id: string;
  label: string;
  participantId: string;
  day: number;
}

const SCENARIOS: Scenario[] = [
  {
    id: "p07-15",
    label: "P-07 · day 15 (changed after dosing)",
    participantId: "P-07",
    day: 15,
  },
  {
    id: "p20-15",
    label: "P-20 · day 15 (changed after dosing)",
    participantId: "P-20",
    day: 15,
  },
  {
    id: "p06-28",
    label: "P-06 · day 28 (Springfield, missing days)",
    participantId: "P-06",
    day: 28,
  },
  {
    id: "p31-16",
    label: "P-31 · day 16 (diary says exhausted)",
    participantId: "P-31",
    day: 16,
  },
];

const EXAMPLES = [
  "The study drug caused P-07's HRV drop.",
  "HRV fell to 51.6 ms on day 12.",
  "Data was complete across all days.",
  "The participant is definitely fine.",
  "HRV dropped after the study drug started; the cause is not established.",
];

const MAX_CHARS = 600;

export function TryIt() {
  const [scenario, setScenario] = useState<Scenario>(SCENARIOS[0]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TryItResponse | null>(null);

  const handleSubmit = async () => {
    if (!text.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await tryIt({
        participant_id: scenario.participantId,
        day: scenario.day,
        text: text.trim(),
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && e.ctrlKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const charsRemaining = MAX_CHARS - text.length;

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Try to fool the checkpoint</h2>
        <p className="mt-2 text-sm text-muted">
          Write a claim about a participant the way an AI might. The same
          deterministic checks judge it instantly; no AI is involved.
        </p>
      </div>

      {/* Scenario picker */}
      <div>
        <label className="mb-2 block text-sm font-medium text-text">
          Scenario
        </label>
        <div className="flex flex-wrap gap-2">
          {SCENARIOS.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setScenario(s)}
              className={`rounded border px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 ${
                scenario.id === s.id
                  ? "border-accent bg-accent text-white"
                  : "border-line bg-card text-text hover:border-accent"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Textarea and examples */}
      <div>
        <label htmlFor="claim-text" className="mb-2 block text-sm font-medium text-text">
          Your claim
        </label>
        <textarea
          id="claim-text"
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, MAX_CHARS))}
          onKeyDown={handleKeyDown}
          placeholder="Type a claim here..."
          maxLength={MAX_CHARS}
          rows={4}
          className="w-full rounded border border-line bg-card px-3 py-2 text-sm text-text placeholder-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <div className="mt-1 flex items-center justify-between text-xs text-muted">
          <span>Ctrl+Enter to submit</span>
          <span className={charsRemaining < 50 ? "text-watch" : ""}>
            {charsRemaining} characters remaining
          </span>
        </div>

        {/* Example chips */}
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((example, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setText(example)}
              className="rounded border border-line bg-card px-3 py-1.5 text-xs text-text hover:border-accent focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* Submit button */}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={!text.trim() || loading}
        className="rounded bg-accent px-6 py-2 text-sm font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Checking…" : "Check it"}
      </button>

      {/* Error */}
      {error && (
        <div className="rounded border border-held bg-held-soft p-4 text-held">
          <p className="text-sm font-medium">Error</p>
          <p className="mt-1 text-sm">{error}</p>
        </div>
      )}

      {/* Result */}
      {result && <TryItResult result={result} />}
    </section>
  );
}

interface TryItResultProps {
  result: TryItResponse;
}

function TryItResult({ result }: TryItResultProps) {
  const { report, gate, negative_control } = result;

  // Count failed claims
  const failedClaimIds = new Set<string>();
  for (const claim of report.claims) {
    const claimChecks = checksForClaim(gate, claim.claim_id);
    if (claimChecks.some((c) => !c.passed)) {
      failedClaimIds.add(claim.claim_id);
    }
  }

  const overallStatus = gate.verdict === "pass" ? "pass" : "held";
  const overallLabel =
    gate.verdict === "pass"
      ? "Passed every check"
      : `Held: ${failedClaimIds.size} of ${report.claims.length} claims stopped`;

  return (
    <div className="space-y-6 rounded-lg border border-line bg-card p-6">
      {/* Overall status */}
      <div>
        <StatusPill status={overallStatus} label={overallLabel} />
      </div>

      {/* Claims */}
      <div className="space-y-6">
        {report.claims.map((claim) => (
          <ClaimResult key={claim.claim_id} claim={claim} gate={gate} />
        ))}
      </div>

      {/* Report-level checks */}
      {reportLevelChecks(gate).length > 0 && (
        <div className="space-y-2 border-t border-line pt-4">
          <h3 className="text-sm font-medium text-text">Report-level checks</h3>
          {reportLevelChecks(gate).map((check, i) => (
            <ReportCheckResult key={i} check={check} />
          ))}
        </div>
      )}

      {/* Negative control */}
      {negative_control && (
        <div className="border-t border-line pt-4 text-sm">
          <NegativeControlSummary control={negative_control} />
        </div>
      )}
    </div>
  );
}

interface ClaimResultProps {
  claim: Report["claims"][0];
  gate: GateResult;
}

function ClaimResult({ claim, gate }: ClaimResultProps) {
  const claimChecks = checksForClaim(gate, claim.claim_id);

  return (
    <div className="space-y-3 rounded border border-line bg-surface p-4">
      {/* Claim text */}
      <p className="text-sm text-text">{claim.text}</p>

      {/* Record IDs */}
      {claim.cited_record_ids.length > 0 && (
        <div className="text-xs text-muted">
          <span className="font-medium">Cited records:</span>{" "}
          <span className="font-mono">{claim.cited_record_ids.join(", ")}</span>
        </div>
      )}

      {/* Ring chips */}
      <div className="flex flex-wrap gap-2">
        {RINGS.map((ring) => {
          const ringChecks = claimChecks.filter(
            (c) => ringForDimension(c.dimension) === ring.id
          );
          if (ringChecks.length === 0) {
            return (
              <RingChip key={ring.id} label={ring.label} status="n-a" />
            );
          }
          const allPassed = ringChecks.every((c) => c.passed);
          return (
            <RingChip
              key={ring.id}
              label={ring.label}
              status={allPassed ? "pass" : "held"}
              checks={ringChecks}
            />
          );
        })}
      </div>
    </div>
  );
}

interface RingChipProps {
  label: string;
  status: "pass" | "held" | "n-a";
  checks?: GateResult["checks"];
}

function RingChip({ label, status, checks }: RingChipProps) {
  const [expanded, setExpanded] = useState(false);

  const bgClass =
    status === "pass"
      ? "bg-pass-soft text-pass"
      : status === "held"
        ? "bg-held-soft text-held"
        : "bg-muted/20 text-muted";

  const failedChecks = checks?.filter((c) => !c.passed) || [];

  return (
    <div className="inline-block">
      <button
        type="button"
        onClick={() => failedChecks.length > 0 && setExpanded(!expanded)}
        className={`rounded-full px-3 py-1 text-xs font-medium ${bgClass} ${
          failedChecks.length > 0
            ? "cursor-pointer hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
            : "cursor-default"
        }`}
        disabled={failedChecks.length === 0}
      >
        {label}
      </button>

      {expanded && failedChecks.length > 0 && (
        <div className="mt-2 rounded border border-line bg-card p-3 text-xs text-text">
          {failedChecks.map((check, i) => {
            const firstSentence = check.explanation.split(/[.!?]/, 1)[0];
            const truncated =
              firstSentence.length > 160
                ? firstSentence.slice(0, 160) + "…"
                : firstSentence;
            return (
              <div key={i} className="space-y-1">
                <p>{truncated}</p>
                <details className="text-muted">
                  <summary className="cursor-pointer hover:text-text">
                    Details
                  </summary>
                  <p className="mt-1">{check.explanation}</p>
                </details>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface ReportCheckResultProps {
  check: GateResult["checks"][0];
}

function ReportCheckResult({ check }: ReportCheckResultProps) {
  const ring = RINGS.find((r) => ringForDimension(check.dimension) === r.id);
  const label = ring?.label || check.dimension.split(":")[0];
  const status = check.passed ? "pass" : "held";

  return (
    <div className="flex items-start gap-2 text-sm">
      <RingChip label={label} status={status} checks={[check]} />
      {!check.passed && (
        <p className="flex-1 text-xs text-muted">{check.explanation}</p>
      )}
    </div>
  );
}

interface NegativeControlSummaryProps {
  control: TryItResponse["negative_control"];
}

function NegativeControlSummary({ control }: NegativeControlSummaryProps) {
  if (!control) return null;

  const predosePct = control.predose_pct?.toFixed(1) || "N/A";
  const postPct = control.post_pct?.toFixed(1) || "N/A";
  const n = control.post_count || 0;
  const total = control.total_participants || 0;
  const supported = control.drug_link_supported ? "supported" : "not supported";

  return (
    <p className="text-muted">
      <span className="font-medium">Controls:</span> pre-dose {predosePct}%,
      after the change {postPct}%, {n} of {total} participants; drug link{" "}
      {supported}.
    </p>
  );
}
