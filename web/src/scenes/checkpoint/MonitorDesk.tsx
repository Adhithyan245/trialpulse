import { useState } from "react";
import { useRole } from "../../role";
import { sign } from "../../api";
import type { Claim } from "../../types";

interface MonitorDeskProps {
  claims: Claim[];
  reportId: string;
  verdict: "pass" | "hold";
  rounds: number;
}

export function MonitorDesk({ claims, reportId, verdict, rounds }: MonitorDeskProps) {
  const { role } = useRole();
  const [reason, setReason] = useState("");
  const [decision, setDecision] = useState<string | null>(null);
  const [sealed, setSealed] = useState<{ entryId: string; hash: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const canSign = role === "monitor" || role === "safety_reviewer";

  const handleSign = async (selectedDecision: string) => {
    if (!reason.trim()) {
      setError("Reason is required");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await sign({
        report_id: reportId,
        decision: selectedDecision,
        reason: reason.trim(),
        signer: "Demo monitor",
      });

      setDecision(selectedDecision);
      setSealed({
        entryId: result.entry_id,
        hash: result.entry_hash.slice(0, 12),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  if (verdict === "hold") {
    return (
      <div className="rounded-lg border border-line bg-card p-4">
        <h3 className="text-lg font-semibold text-text mb-3">Monitor's desk</h3>
        <div className="text-sm text-muted">
          Still held after {rounds} round{rounds !== 1 ? "s" : ""}: never sent to
          the monitor as approved
        </div>
      </div>
    );
  }

  if (sealed) {
    return (
      <div className="rounded-lg border border-pass bg-pass-soft p-4">
        <h3 className="text-lg font-semibold text-pass mb-3">Signed</h3>
        <div className="space-y-2">
          <div className="text-sm text-text">
            Decision: <span className="font-medium">{decision}</span>
          </div>
          <div className="font-mono text-sm text-muted tabular-nums">
            Sealed as {sealed.entryId} · {sealed.hash}…
          </div>
          <a
            href="#/seal"
            className="inline-block text-sm text-accent hover:underline focus:underline"
          >
            See it on the chain
          </a>
        </div>
      </div>
    );
  }

  if (!canSign) {
    return (
      <div className="rounded-lg border border-line bg-card p-4">
        <h3 className="text-lg font-semibold text-text mb-3">Monitor's desk</h3>
        <div className="space-y-3">
          <div className="space-y-2">
            <div className="text-sm font-medium text-text">Final claims</div>
            {claims.map((claim) => (
              <div
                key={claim.claim_id}
                className="text-sm text-text border-l-2 border-accent pl-3"
              >
                {claim.text}
              </div>
            ))}
          </div>
          <div className="text-sm text-muted italic">
            Only the medical monitor or safety reviewer can sign.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-line bg-card p-4">
      <h3 className="text-lg font-semibold text-text mb-3">Monitor's desk</h3>
      <div className="space-y-4">
        <div className="space-y-2">
          <div className="text-sm font-medium text-text">Final claims</div>
          {claims.map((claim) => (
            <div
              key={claim.claim_id}
              className="text-sm text-text border-l-2 border-accent pl-3"
            >
              {claim.text}
            </div>
          ))}
        </div>

        <div className="space-y-2">
          <label htmlFor="sign-reason" className="block text-sm font-medium text-text">
            Reason <span className="text-held">*</span>
          </label>
          <textarea
            id="sign-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="w-full rounded border border-line bg-surface px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
            placeholder="Enter your reason for this decision..."
            disabled={loading}
          />
        </div>

        {error && (
          <div className="rounded border border-held bg-held-soft px-3 py-2 text-sm text-held">
            {error}
          </div>
        )}

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => handleSign("approved")}
            disabled={loading}
            className="rounded bg-pass px-4 py-2 text-sm font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-pass focus:ring-offset-2 disabled:opacity-50"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => handleSign("rejected")}
            disabled={loading}
            className="rounded bg-held px-4 py-2 text-sm font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-held focus:ring-offset-2 disabled:opacity-50"
          >
            Reject
          </button>
          <button
            type="button"
            onClick={() => handleSign("redraft_requested")}
            disabled={loading}
            className="rounded border border-line bg-card px-4 py-2 text-sm font-medium text-text hover:bg-surface focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 disabled:opacity-50"
          >
            Request redraft
          </button>
        </div>
      </div>
    </div>
  );
}
