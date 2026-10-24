import { useEffect, useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { negativeControl, participantSeries, run, runs } from "../api";
import type { Claim, GateCheck, RunRecord, RunSummary } from "../types";
import { RINGS, checksForClaim, reportLevelChecks, ringForDimension } from "../checks";
import { StatusPill } from "../components/StatusPill";

interface SeriesData {
  participant_id: string;
  day: number;
  metrics: Record<string, Array<{ day: number; value: number; record_id: string; recorded_at: string }>>;
  bands: Record<string, { lo: number; hi: number }>;
  diary: Array<{ day: number; name: string; value: string; record_id: string; recorded_at: string }>;
}

interface NegativeControlData {
  metrics: string[];
  predose_exceedance_rate: number;
  postchange_exceedance_rate: number;
  differs_from_predose: boolean;
  trial_drift_rate: number;
  arm_rates: { A: number; B: number };
  arm_difference: number;
  drug_link_supported: boolean;
}

function CheckDisclosure({ check, defaultOpen = false }: { check: GateCheck; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const ring = RINGS.find((r) => r.id === ringForDimension(check.dimension));
  const passed = check.passed;

  return (
    <div className={`rounded border ${passed ? "border-pass bg-pass-soft" : "border-held bg-held-soft"}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm"
      >
        <div className="flex items-center gap-2">
          <StatusPill status={passed ? "pass" : "held"} />
          <span className="font-medium">{ring?.label || check.dimension.split(":")[0]}</span>
        </div>
        {open ? (
          <ChevronUp className="h-4 w-4 text-muted" aria-hidden="true" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted" aria-hidden="true" />
        )}
      </button>
      {open && (
        <div className="border-t border-current px-3 py-2 text-sm text-text">
          {check.explanation}
        </div>
      )}
    </div>
  );
}

function ClaimView({
  claim,
  checks,
  series,
}: {
  claim: Claim;
  checks: GateCheck[];
  series: SeriesData;
}) {
  // Find cited records from series data
  const citedRecords: Array<{
    record_id: string;
    metric: string;
    value: string;
    unit: string;
    day: number;
    recorded_at: string;
  }> = [];

  for (const recordId of claim.cited_record_ids) {
    // Check in metrics
    for (const [metricName, points] of Object.entries(series.metrics)) {
      const point = points.find((p) => p.record_id === recordId);
      if (point) {
        citedRecords.push({
          record_id: recordId,
          metric: metricName,
          value: String(point.value),
          unit: metricName === "resting_hr" ? "bpm" : "",
          day: point.day,
          recorded_at: point.recorded_at,
        });
      }
    }
    // Check in diary
    const diaryEntry = series.diary.find((d) => d.record_id === recordId);
    if (diaryEntry) {
      citedRecords.push({
        record_id: recordId,
        metric: diaryEntry.name,
        value: String(diaryEntry.value),
        unit: "",
        day: diaryEntry.day,
        recorded_at: diaryEntry.recorded_at,
      });
    }
  }

  // Group checks by ring
  const checksByRing: Record<string, GateCheck[]> = {};
  for (const check of checks) {
    const ringId = ringForDimension(check.dimension);
    if (ringId) {
      if (!checksByRing[ringId]) {
        checksByRing[ringId] = [];
      }
      checksByRing[ringId].push(check);
    }
  }

  // Check if recompute check exists and extract explanation
  const recomputeCheck = checks.find((c) => c.dimension.startsWith("recompute:"));
  const hasRecompute = !!recomputeCheck;

  return (
    <div className="space-y-4 rounded-lg border border-line bg-surface p-4">
      <div>
        <h4 className="font-medium">Claim</h4>
        <p className="mt-1 text-sm">{claim.text}</p>
      </div>

      {citedRecords.length > 0 && (
        <div>
          <h4 className="mb-2 font-medium">Cited records</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-line">
                <tr className="text-left">
                  <th className="pb-2 pr-4 font-medium">Record ID</th>
                  <th className="pb-2 pr-4 font-medium">Metric</th>
                  <th className="pb-2 pr-4 font-medium">Value</th>
                  <th className="pb-2 pr-4 font-medium">Day</th>
                  <th className="pb-2 font-medium">Recorded at</th>
                </tr>
              </thead>
              <tbody>
                {citedRecords.map((record) => (
                  <tr key={record.record_id} className="border-b border-line last:border-0">
                    <td className="py-2 pr-4 font-mono text-xs">{record.record_id}</td>
                    <td className="py-2 pr-4">{record.metric}</td>
                    <td className="py-2 pr-4 font-mono tabular-nums">
                      {record.value} {record.unit}
                    </td>
                    <td className="py-2 pr-4 font-mono tabular-nums">{record.day}</td>
                    <td className="py-2 font-mono text-xs text-muted">
                      {new Date(record.recorded_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {hasRecompute && recomputeCheck && (
        <div className="rounded border border-accent bg-accent/5 p-3">
          <h4 className="mb-1 font-medium text-accent">Recompute</h4>
          <p className="text-sm">{recomputeCheck.explanation}</p>
        </div>
      )}

      {RINGS.map((ring) => {
        const ringChecks = checksByRing[ring.id];
        if (!ringChecks || ringChecks.length === 0) return null;
        return (
          <div key={ring.id} className="space-y-2">
            <h4 className="text-sm font-medium text-muted">{ring.label}</h4>
            {ringChecks.map((check, idx) => (
              <CheckDisclosure key={idx} check={check} defaultOpen={!check.passed} />
            ))}
          </div>
        );
      })}
    </div>
  );
}

export function Scene4Verified() {
  const [runList, setRunList] = useState<RunSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<string>("");
  const [runData, setRunData] = useState<RunRecord | null>(null);
  const [selectedDraftIndex, setSelectedDraftIndex] = useState(0);
  const [series, setSeries] = useState<SeriesData | null>(null);
  const [controlData, setControlData] = useState<NegativeControlData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadRuns = async () => {
      try {
        const list = await runs();
        setRunList(list);
        if (list.length > 0 && !selectedCase) {
          setSelectedCase(list[1]?.case_id || list[0].case_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load runs");
      } finally {
        setLoading(false);
      }
    };
    loadRuns();
  }, []);

  useEffect(() => {
    if (!selectedCase) return;

    const loadRunData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [data, control] = await Promise.all([
          run(selectedCase),
          negativeControl(selectedCase),
        ]);
        setRunData(data);
        setControlData(control as NegativeControlData);
        setSelectedDraftIndex(0);

        // Load series data for the participant
        const draft = data.pipeline.drafts[0];
        if (draft) {
          const seriesData = (await participantSeries(
            draft.participant_id,
            data.day,
          )) as SeriesData;
          setSeries(seriesData);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load run data");
      } finally {
        setLoading(false);
      }
    };

    loadRunData();
  }, [selectedCase]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-6 w-6 animate-spin text-muted" aria-hidden="true" />
        <span className="ml-2 text-muted">Loading verification data…</span>
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

  if (!runData || !series) {
    return (
      <div className="rounded-lg border border-line bg-surface p-8 text-center text-muted">
        No run data available
      </div>
    );
  }

  const draft = runData.pipeline.drafts[selectedDraftIndex];
  const gate = runData.pipeline.gates[selectedDraftIndex];
  const reportChecks = reportLevelChecks(gate);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Scene 4: How this was verified</h1>
        <p className="mt-2 text-muted">
          For each claim: cited records, recomputed numbers, and gate checks by dimension.
        </p>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label htmlFor="case-picker" className="text-sm text-muted">
            Case:
          </label>
          <select
            id="case-picker"
            value={selectedCase}
            onChange={(e) => setSelectedCase(e.target.value)}
            className="rounded border border-line bg-surface px-2 py-1 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          >
            {runList.map((r) => (
              <option key={r.case_id} value={r.case_id}>
                {r.case_id} (P-{r.participant_id.split("-")[1]}, day {r.day})
              </option>
            ))}
          </select>
        </div>

        {runData.pipeline.drafts.length > 1 && (
          <div className="flex items-center gap-2">
            <label htmlFor="draft-picker" className="text-sm text-muted">
              Draft:
            </label>
            <select
              id="draft-picker"
              value={selectedDraftIndex}
              onChange={(e) => setSelectedDraftIndex(Number(e.target.value))}
              className="rounded border border-line bg-surface px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            >
              {runData.pipeline.drafts.map((_, idx) => (
                <option key={idx} value={idx}>
                  Draft {idx + 1}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="space-y-6">
        <div>
          <h2 className="mb-3 text-lg font-semibold">Claims</h2>
          <div className="space-y-4">
            {draft.claims.map((claim) => {
              const claimChecks = checksForClaim(gate, claim.claim_id);
              return (
                <ClaimView
                  key={claim.claim_id}
                  claim={claim}
                  checks={claimChecks}
                  series={series}
                />
              );
            })}
          </div>
        </div>

        {reportChecks.length > 0 && (
          <div>
            <h2 className="mb-3 text-lg font-semibold">Report-level checks</h2>
            <div className="space-y-2">
              {reportChecks.map((check, idx) => (
                <CheckDisclosure key={idx} check={check} defaultOpen={!check.passed} />
              ))}
            </div>
          </div>
        )}

        {controlData && (
          <div className="rounded-lg border border-line bg-surface p-4">
            <h2 className="mb-3 text-lg font-semibold">Negative controls</h2>
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-muted">Pre-dose exceedance:</span>
                  <span className="ml-2 font-mono tabular-nums">
                    {(controlData.predose_exceedance_rate * 100).toFixed(0)}%
                  </span>
                </div>
                <div>
                  <span className="text-muted">After-change exceedance:</span>
                  <span className="ml-2 font-mono tabular-nums">
                    {(controlData.postchange_exceedance_rate * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              <div>
                <span className="text-muted">Trial-wide drift:</span>
                <span className="ml-2 font-mono tabular-nums">
                  {Math.round(controlData.trial_drift_rate * runData.pipeline.drafts[0].participant_id.length)} participants
                </span>
              </div>

              <div>
                <span className="text-muted">Treatment group rates:</span>
                <span className="ml-2 font-mono tabular-nums">
                  {(controlData.arm_rates.A * 100).toFixed(0)}% and {(controlData.arm_rates.B * 100).toFixed(0)}%
                </span>
                <span className="ml-2 text-muted">(this participant's group is blinded)</span>
              </div>

              <div className="rounded border border-line bg-surface p-2">
                <span className="font-medium">Drug link: </span>
                <span className={controlData.drug_link_supported ? "text-pass" : "text-held"}>
                  {controlData.drug_link_supported ? "Supported" : "Not supported"}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
