import { useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";
import { Play, Pause, SkipForward, RotateCcw } from "lucide-react";
import { run, runs, participantSeries } from "../api";
import { StatusPill } from "../components/StatusPill";
import type { RunRecord, RunSummary, Report, GateResult } from "../types";
import { PulseStrip } from "./checkpoint/PulseStrip";
import { RingTunnel } from "./checkpoint/RingTunnel";
import { CurrentClaimPanel } from "./checkpoint/CurrentClaimPanel";
import { EvidenceInbox } from "./checkpoint/EvidenceInbox";
import { MonitorDesk } from "./checkpoint/MonitorDesk";
import { useSequence, requestsForRound, type SequenceStep } from "./checkpoint/useSequence";
import { checksForClaim, reportLevelChecks } from "../checks";

interface SeriesData {
  participant_id: string;
  day: number;
  metrics: Record<string, Array<{ day: number; value: number; record_id: string; recorded_at: string }>>;
  bands: Record<string, { median: number; lo: number; hi: number; q: number }>;
  diary: Array<{ day: number; name: string; value: string; record_id: string; recorded_at: string }>;
}

// Narrow the parsed series JSON to SeriesData after checking it has the
// required shape. The API client returns `unknown`; throw if the payload is
// missing the fields this scene relies on.
function asSeriesData(value: unknown): SeriesData {
  if (
    typeof value === "object" &&
    value !== null &&
    "metrics" in value &&
    "bands" in value
  ) {
    return value as SeriesData;
  }
  throw new Error("Unexpected participant series payload");
}

export function Scene2Checkpoint() {
  const [runList, setRunList] = useState<RunSummary[] | null>(null);
  const [selectedCase, setSelectedCase] = useState<string>("v02");
  const [runData, setRunData] = useState<RunRecord | null>(null);
  const [seriesData, setSeriesData] = useState<SeriesData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reducedMotion = useReducedMotion();

  // Load run list
  useEffect(() => {
    let active = true;
    runs()
      .then((list) => {
        if (active) setRunList(list);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);

  // Load selected run
  useEffect(() => {
    if (!selectedCase) return;

    let active = true;
    setLoading(true);
    setError(null);

    run(selectedCase)
      .then((data) => {
        if (!active) return;
        setRunData(data);
        return participantSeries(data.participant_id, data.day);
      })
      .then((series) => {
        if (active) {
          setSeriesData(asSeriesData(series));
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedCase]);

  const sequence = useSequence({
    pipeline: runData?.pipeline || {
      drafts: [],
      gates: [],
      requests: [],
      replies: [],
      final_verdict: "hold",
      rounds: 0,
    },
    reducedMotion: !!reducedMotion,
  });

  if (error) {
    return (
      <div className="rounded-lg border border-held bg-held-soft p-4 text-held">
        <p className="font-medium">Error loading checkpoint data</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    );
  }

  if (loading || !runData || !seriesData) {
    return (
      <div className="text-muted">Loading checkpoint...</div>
    );
  }

  const currentDraftIndex = "draftIndex" in sequence.step
    ? sequence.step.draftIndex
    : runData.pipeline.drafts.length - 1;
  const currentDraft = runData.pipeline.drafts[currentDraftIndex];
  const currentGate = runData.pipeline.gates[currentDraftIndex];

  // Determine current draft index for requests and window calculations
  const draftIndex = (() => {
    if (sequence.step.type === "desk") {
      return runData.pipeline.drafts.length - 1;
    }
    if ("draftIndex" in sequence.step) {
      return sequence.step.draftIndex;
    }
    return 0;
  })();
  const visibleRequests = sequence.step.type === "requesting" || sequence.step.type === "received" || sequence.step.type === "desk"
    ? sequence.step.type === "desk"
      ? runData.pipeline.requests // Show all at the desk
      : requestsForRound(runData.pipeline, draftIndex).slice(0, 10)
    : [];

  // Parse window dates from the draft
  // TRIAL_START is 2026-09-21, trial day 1
  const TRIAL_START = new Date("2026-09-21");
  const windowStart = new Date(currentDraft.window_start);
  const windowEnd = new Date(currentDraft.window_end);
  const doseStartDay = 8; // From DOSE_START_DAY

  const windowStartDay = Math.floor(
    (windowStart.getTime() - TRIAL_START.getTime()) / (1000 * 60 * 60 * 24)
  ) + 1;
  const windowEndDay = Math.floor(
    (windowEnd.getTime() - TRIAL_START.getTime()) / (1000 * 60 * 60 * 24)
  ) + 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">The checkpoint</h1>

        {/* Case picker */}
        {runList && runList.length > 0 && (
          <select
            value={selectedCase}
            onChange={(e) => setSelectedCase(e.target.value)}
            className="w-full max-w-full rounded border border-line bg-card px-3 py-2 text-sm focus:border-accent focus:outline-none lg:w-auto"
          >
            {runList.map((r) => (
              <option key={r.case_id} value={r.case_id}>
                {r.case_id} · {r.participant_id} · day {r.day} ·{" "}
                {r.fault || "no fault injected"}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={sequence.isPlaying ? sequence.pause : sequence.play}
          className="inline-flex items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
          aria-label={sequence.isPlaying ? "Pause" : "Play"}
        >
          {sequence.isPlaying ? (
            <>
              <Pause className="h-4 w-4" />
              Pause
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Play
            </>
          )}
        </button>
        <button
          type="button"
          onClick={sequence.next}
          className="inline-flex items-center gap-2 rounded border border-line bg-card px-4 py-2 text-sm font-medium text-text hover:bg-surface focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
          aria-label="Next step"
        >
          <SkipForward className="h-4 w-4" />
          Next
        </button>
        <button
          type="button"
          onClick={sequence.restart}
          className="inline-flex items-center gap-2 rounded border border-line bg-card px-4 py-2 text-sm font-medium text-text hover:bg-surface focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
          aria-label="Restart"
        >
          <RotateCcw className="h-4 w-4" />
          Restart
        </button>
        <button
          type="button"
          onClick={sequence.toggleSpeed}
          className="rounded border border-line bg-card px-3 py-2 text-sm font-medium text-text hover:bg-surface focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
        >
          {sequence.speed}x
        </button>
        <div className="text-sm text-muted">
          {sequence.step.type === "intro" && "Intro"}
          {sequence.step.type === "travel" && `Checking claim ${sequence.step.claimIndex + 1}`}
          {sequence.step.type === "verdict" && "Draft verdict"}
          {sequence.step.type === "requesting" && "Requesting evidence"}
          {sequence.step.type === "received" && "Evidence received"}
          {sequence.step.type === "desk" && "Monitor's desk"}
        </div>
      </div>

      {/* Responsive grid layout */}
      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)] xl:grid-cols-[260px_minmax(0,1fr)_320px]">
        {/* Left: Participant */}
        <div className="space-y-4 min-w-0">
          <div>
            <h2 className="text-lg font-semibold mb-2">Participant</h2>
            <div className="text-sm space-y-1">
              <div>
                <span className="text-muted">ID:</span>{" "}
                <span className="font-mono break-words">{runData.participant_id}</span>
              </div>
              <div>
                <span className="text-muted">Trial day:</span> {runData.day}
              </div>
            </div>
          </div>

          <PulseStrip
            participantId={runData.participant_id}
            currentDay={runData.day}
            doseStartDay={doseStartDay}
            windowStart={Math.max(1, windowStartDay)}
            windowEnd={Math.min(runData.day, windowEndDay)}
            metrics={seriesData.metrics}
            bands={seriesData.bands}
          />

          <EvidenceInbox
            requests={visibleRequests}
            replies={runData.pipeline.replies}
            step={
              sequence.step.type === "requesting"
                ? "requesting"
                : sequence.step.type === "received"
                  ? "received"
                  : sequence.step.type === "desk"
                    ? "desk"
                    : undefined
            }
          />
        </div>

        {/* Center: The checkpoint */}
        <div className="space-y-4 min-w-0 lg:col-span-1 xl:col-span-1">
          <div>
            <h2 className="text-lg font-semibold mb-2">The checkpoint</h2>
            <div className="text-xs text-muted space-y-1">
              <div className="flex flex-wrap items-center gap-x-2">
                <span>Draft {draftIndex + 1} of {runData.pipeline.drafts.length}</span>
                <span>·</span>
                <span className="font-mono break-words">{currentDraft.model_id}</span>
                <span>·</span>
                <span className="font-mono break-words">{currentDraft.prompt_version}</span>
              </div>
              {runData.recorded && (
                <div className="inline-flex items-center rounded-full border border-line px-2 py-0.5 text-muted">
                  Recorded run
                </div>
              )}
            </div>
          </div>

          <CheckpointVisualization
            draft={currentDraft}
            gate={currentGate}
            step={sequence.step}
            reducedMotion={!!reducedMotion}
          />

          {/* Verdict pill - only show at verdict step */}
          {sequence.step.type === "verdict" && (
            <div>
              {currentGate.verdict === "hold" ? (
                <StatusPill
                  status="held"
                  label={(() => {
                    // Count distinct claim IDs with at least one failing check
                    const failedClaimIds = new Set<string>();
                    for (const claim of currentDraft.claims) {
                      const claimChecks = checksForClaim(currentGate, claim.claim_id);
                      if (claimChecks.some((c) => !c.passed)) {
                        failedClaimIds.add(claim.claim_id);
                      }
                    }
                    const claimCount = failedClaimIds.size;
                    const totalClaims = currentDraft.claims.length;
                    
                    // Count report-level checks that failed
                    const reportChecks = reportLevelChecks(currentGate);
                    const failedReportChecks = reportChecks.filter((c) => !c.passed).length;
                    
                    let label = `Held: ${claimCount} of ${totalClaims} claim${claimCount !== 1 ? "s" : ""} stopped`;
                    if (failedReportChecks > 0) {
                      label += ` · ${failedReportChecks} report-level check${failedReportChecks !== 1 ? "s" : ""} failed`;
                    }
                    return label;
                  })()}
                />
              ) : (
                <StatusPill status="pass" label="Passed all checks" />
              )}
            </div>
          )}
        </div>

        {/* Right: Monitor's desk */}
        <div className="min-w-0 lg:col-span-2 xl:col-span-1">
          {sequence.step.type === "desk" && (
            <MonitorDesk
              claims={runData.pipeline.drafts[runData.pipeline.drafts.length - 1].claims}
              reportId={runData.pipeline.drafts[runData.pipeline.drafts.length - 1].report_id}
              verdict={runData.pipeline.final_verdict}
              rounds={runData.pipeline.rounds}
            />
          )}
        </div>
      </div>
    </div>
  );
}

interface CheckpointVisualizationProps {
  draft: Report;
  gate: GateResult;
  step: SequenceStep;
  reducedMotion: boolean;
}

function CheckpointVisualization({
  draft,
  gate,
  step,
  reducedMotion,
}: CheckpointVisualizationProps) {
  return (
    <div className="space-y-4">
      <RingTunnel
        draft={draft}
        gate={gate}
        step={step}
        reducedMotion={reducedMotion}
      />

      {/* Current claim panel - show when traveling or after */}
      {step.type === "travel" && (
        <CurrentClaimPanel
          claim={draft.claims[step.claimIndex]}
          gate={gate}
        />
      )}
    </div>
  );
}
