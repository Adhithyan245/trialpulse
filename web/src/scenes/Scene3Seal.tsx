import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react";
import { audit, auditVerify, resetDemo, tamper } from "../api";
import type { AuditEntry, AuditVerify } from "../types";
import { StatusPill } from "../components/StatusPill";

function formatTimestamp(ts: string): string {
  const date = new Date(ts);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatHash(hash: string): string {
  return hash.slice(0, 6) + "…";
}

function actionLabel(action: string): string {
  const labels: Record<string, string> = {
    drafted: "Drafted",
    gated: "Gated",
    evidence_requested: "Evidence requested",
    evidence_received: "Evidence received",
    approved: "Approved",
    rejected: "Rejected",
    redraft_requested: "Redraft requested",
  };
  return labels[action] || action;
}

function detailsSummary(entry: AuditEntry): string {
  try {
    const details = JSON.parse(entry.details_json);
    if (entry.action === "approved" || entry.action === "rejected" || entry.action === "redraft_requested") {
      const signer = details.signer || "Unknown";
      const reason = details.reason || "";
      return `${signer} ${entry.action} ${entry.report_id}: ${reason}`;
    }
    if (entry.action === "gated") {
      return `Verdict: ${details.verdict || "unknown"}`;
    }
    if (entry.action === "drafted") {
      return `${details.n_claims || 0} claims, model ${details.model_id || "unknown"}`;
    }
    if (entry.action === "evidence_requested") {
      return `Request ${details.request_id || ""}: ${details.kind || ""}`;
    }
    if (entry.action === "evidence_received") {
      return `Reply ${details.reply_record_id || ""}`;
    }
    return "";
  } catch {
    return "";
  }
}

function AuditBlock({
  entry,
  broken,
  onTamper,
}: {
  entry: AuditEntry;
  broken: boolean;
  onTamper: (entryId: string) => void;
}) {
  const [confirmTamper, setConfirmTamper] = useState(false);

  return (
    <div
      className={`relative rounded-lg border p-4 ${
        broken ? "border-held bg-held-soft" : "border-line bg-surface"
      }`}
    >
      <div className="mb-2 flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm text-muted">{entry.entry_id}</span>
            <span className="text-sm font-medium">{actionLabel(entry.action)}</span>
            {broken && (
              <span className="inline-flex items-center gap-1 text-xs text-held">
                <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                chain broken from here
              </span>
            )}
          </div>
          <div className="mt-1 text-sm text-muted">
            {entry.actor_role} · {formatTimestamp(entry.ts)}
          </div>
        </div>
        <div>
          {!confirmTamper ? (
            <button
              type="button"
              onClick={() => setConfirmTamper(true)}
              className="rounded border border-line px-2 py-1 text-xs text-muted hover:bg-surface-hover"
            >
              Tamper
            </button>
          ) : (
            <div className="flex gap-1">
              <button
                type="button"
                onClick={() => {
                  onTamper(entry.entry_id);
                  setConfirmTamper(false);
                }}
                className="rounded border border-held px-2 py-1 text-xs text-held hover:bg-held-soft"
              >
                Confirm
              </button>
              <button
                type="button"
                onClick={() => setConfirmTamper(false)}
                className="rounded border border-line px-2 py-1 text-xs text-muted hover:bg-surface-hover"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="mb-2 text-sm">{detailsSummary(entry)}</div>

      <div className="font-mono text-xs text-muted">
        prev {formatHash(entry.prev_hash)} → hash {formatHash(entry.entry_hash)}
      </div>
    </div>
  );
}

export function Scene3Seal() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [verifyResult, setVerifyResult] = useState<AuditVerify | null>(null);
  const [filterReportId, setFilterReportId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);

  const loadAudit = async (reportIdFilter?: string) => {
    try {
      setLoading(true);
      setError(null);
      const [auditEntries, verify] = await Promise.all([
        audit(reportIdFilter || undefined),
        auditVerify(),
      ]);
      // Newest first
      setEntries([...auditEntries].reverse());
      setVerifyResult(verify);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudit(filterReportId);
  }, [filterReportId]);

  const handleTamper = async (entryId: string) => {
    try {
      const verify = await tamper(entryId);
      setVerifyResult(verify);
      await loadAudit(filterReportId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tamper failed");
    }
  };

  const handleReset = async () => {
    try {
      setResetting(true);
      setError(null);
      const verify = await resetDemo();
      setVerifyResult(verify);
      setFilterReportId("");
      await loadAudit();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setResetting(false);
    }
  };

  if (loading && !resetting) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-6 w-6 animate-spin text-muted" aria-hidden="true" />
        <span className="ml-2 text-muted">Loading audit chain…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-held bg-held-soft p-4 text-held">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" aria-hidden="true" />
          <span className="font-medium">Error</span>
        </div>
        <p className="mt-2">{error}</p>
      </div>
    );
  }

  const brokenFromSeq = verifyResult && !verifyResult.ok ? verifyResult.first_bad_entry_id : null;
  const brokenIndex = brokenFromSeq
    ? entries.findIndex((e) => e.entry_id === brokenFromSeq)
    : -1;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Scene 3: Sign and seal</h1>
        <p className="mt-2 text-muted">
          Every action is a block whose fingerprint includes the one before it, so editing any past entry breaks every fingerprint after it.
        </p>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        {verifyResult && (
          <div>
            {verifyResult.ok ? (
              <StatusPill
                status="pass"
                label={`Chain intact: ${verifyResult.checked} entries checked`}
              />
            ) : (
              <StatusPill
                status="held"
                label={`Chain broken at ${verifyResult.first_bad_entry_id}: ${verifyResult.reason}`}
              />
            )}
          </div>
        )}

        <div className="flex items-center gap-2">
          <label htmlFor="filter-report" className="text-sm text-muted">
            Filter by report:
          </label>
          <input
            id="filter-report"
            type="text"
            value={filterReportId}
            onChange={(e) => setFilterReportId(e.target.value)}
            placeholder="RPT-P-07-v01-1"
            className="rounded border border-line bg-surface px-2 py-1 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>

        <button
          type="button"
          onClick={handleReset}
          disabled={resetting}
          className="ml-auto flex items-center gap-2 rounded bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent/90 disabled:opacity-50"
        >
          {resetting ? (
            <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
          )}
          Reset demo
        </button>
      </div>

      <div className="space-y-3">
        {entries.length === 0 ? (
          <div className="rounded-lg border border-line bg-surface p-8 text-center text-muted">
            {filterReportId ? "No entries for this report ID" : "No audit entries yet"}
          </div>
        ) : (
          entries.map((entry, idx) => {
            const broken = brokenIndex >= 0 && idx >= brokenIndex;
            return (
              <div key={entry.entry_id} className="relative">
                <AuditBlock entry={entry} broken={broken} onTamper={handleTamper} />
                {idx < entries.length - 1 && (
                  <div className="ml-4 h-4 w-0.5 bg-line" aria-hidden="true" />
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
