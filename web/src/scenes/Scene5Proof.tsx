import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, Search } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts";
import { metrics, searchTrials } from "../api";
import type { Metrics, PublicMetrics, TrialRow } from "../types";
import { RINGS } from "../checks";

function ValidationScorecard({ validation }: { validation: Metrics["validation"] }) {
  const [colors, setColors] = useState({
    accent: "",
    text: "",
    muted: "",
    line: "",
  });

  useEffect(() => {
    // Read CSS variable values at runtime for Recharts
    const updateColors = () => {
      const root = document.documentElement;
      const style = getComputedStyle(root);
      setColors({
        accent: style.getPropertyValue("--accent").trim(),
        text: style.getPropertyValue("--text").trim(),
        muted: style.getPropertyValue("--muted").trim(),
        line: style.getPropertyValue("--line").trim(),
      });
    };

    updateColors();

    // Watch for theme changes via data-theme attribute
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "attributes" && mutation.attributeName === "data-theme") {
          updateColors();
        }
      }
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    // Watch for theme changes via matchMedia
    const darkModeQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => updateColors();
    darkModeQuery.addEventListener("change", handleChange);

    return () => {
      observer.disconnect();
      darkModeQuery.removeEventListener("change", handleChange);
    };
  }, []);

  if (!validation) {
    return (
      <div className="rounded-lg border border-line bg-surface p-8 text-center text-muted">
        Run the validation suite to see numbers
      </div>
    );
  }

  // Aggregate raw failures by ring instead of dimension
  const ringCounts: Record<string, number> = {};
  for (const [dim, count] of Object.entries(validation.raw.by_dimension)) {
    const ring = RINGS.find((r) => r.dims.includes(dim));
    if (ring) {
      ringCounts[ring.id] = (ringCounts[ring.id] || 0) + count;
    }
  }

  // Build chart data in RINGS order, skipping rings with 0 counts
  const chartData = RINGS.map((ring) => ({
    ring: ring.label,
    failures: ringCounts[ring.id] || 0,
  })).filter((d) => d.failures > 0);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <div className="rounded-lg border border-line bg-surface p-4 min-w-0">
          <div className="text-sm text-muted">Raw AI drafts held</div>
          <div className="mt-1 font-mono text-2xl tabular-nums">
            {validation.raw.held} of {validation.cases}
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-4 min-w-0">
          <div className="text-sm text-muted">Clean cases held</div>
          <div className="mt-1 font-mono text-2xl tabular-nums">
            {validation.clean_cases.raw_held} of {validation.clean_cases.total}
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-4 min-w-0">
          <div className="text-sm text-muted">Passed after evidence loop</div>
          <div className="mt-1 font-mono text-2xl tabular-nums">
            {validation.pipeline.passed_after_loop} of {validation.cases}
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-4 min-w-0">
          <div className="text-sm text-muted">Unsafe reaching monitor</div>
          <div className="mt-1 font-mono text-2xl tabular-nums text-pass">
            {validation.pipeline.unsafe_reaching_monitor}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <div className="rounded-lg border border-line bg-surface p-4 min-w-0">
          <div className="text-sm text-muted">Mean rounds</div>
          <div className="mt-1 font-mono text-2xl tabular-nums">
            {validation.pipeline.mean_rounds.toFixed(2)}
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-4 min-w-0">
          <div className="text-sm text-muted">Evidence requests</div>
          <div className="mt-1 font-mono text-2xl tabular-nums">
            {validation.pipeline.evidence_requests}
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-4 min-w-0">
          <div className="text-sm text-muted">Replies received</div>
          <div className="mt-1 font-mono text-2xl tabular-nums">
            {validation.pipeline.replies}
          </div>
        </div>
      </div>

      <div>
        <h3 className="mb-3 font-medium">Raw failures by ring</h3>
        <div className="rounded-lg border border-line bg-surface p-4">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 20, left: 100, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.line} />
              <XAxis type="number" className="text-xs" tick={{ fill: colors.text }} />
              <YAxis type="category" dataKey="ring" className="text-xs" tick={{ fill: colors.text }} />
              <Bar dataKey="failures" fill={colors.accent} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="text-sm text-muted">
        <p>
          Models: {validation.models_used.join(", ")}. {validation.note}
        </p>
      </div>
    </div>
  );
}

function RegulatoryFit() {
  const guidance = [
    {
      item: "1. Question of interest",
      trialpulse: "Is this safety signal worth the monitor's attention?",
    },
    {
      item: "2. Context of use",
      trialpulse: "Drafts for a blinded medical monitor; a human signs every report",
    },
    {
      item: "3. Model risk",
      trialpulse: "Low influence: every report is gated and signed",
    },
    {
      item: "4. Credibility plan",
      trialpulse: "PulseEval checks, negative controls, validation suite",
    },
    {
      item: "5. Execute",
      trialpulse: "Recorded runs in the repository",
    },
    {
      item: "6. Document",
      trialpulse: "Audit chain (Scene 3), hash-chained e-signatures",
    },
    {
      item: "7. Adequacy",
      trialpulse: "Validation scorecard above",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-line bg-surface p-4">
        <h3 className="mb-3 font-medium">
          FDA draft guidance (January 2025) on AI credibility for regulatory decisions
        </h3>
        <div className="space-y-3 text-sm">
          {guidance.map((row, idx) => (
            <div key={idx} className="grid gap-2 sm:grid-cols-[200px_1fr]">
              <div className="font-medium text-muted">{row.item}</div>
              <div>{row.trialpulse}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="text-sm text-muted">
        <p>
          Also addresses: ICH E6(R3) audit-trail expectations and 21 CFR Part 11 e-signatures (Scene 3).
        </p>
      </div>
    </div>
  );
}

function TrialFinder({ publicMetrics }: { publicMetrics: PublicMetrics | null }) {
  const [query, setQuery] = useState("");
  const [wearableOnly, setWearableOnly] = useState(false);
  const [results, setResults] = useState<TrialRow[]>([]);
  const [total, setTotal] = useState(0);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const doSearch = async () => {
      try {
        setSearching(true);
        setError(null);
        const response = await searchTrials(query, wearableOnly, 50);
        setResults(response.trials);
        setTotal(response.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Search failed");
      } finally {
        setSearching(false);
      }
    };

    const timeoutId = setTimeout(doSearch, 300);
    return () => clearTimeout(timeoutId);
  }, [query, wearableOnly]);

  if (!publicMetrics) {
    return (
      <div className="rounded-lg border border-line bg-surface p-8 text-center text-muted">
        Public metrics not available
      </div>
    );
  }

  const bostonCount = publicMetrics.top_cities.find((c) => c[0] === "Boston")?.[1] || 0;
  const springfieldCount = publicMetrics.top_cities.find((c) => c[0] === "Springfield")?.[1] || 0;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <div className="rounded-lg border border-line bg-surface p-4 min-w-0">
          <div className="text-sm text-muted">Total recruiting trials</div>
          <div className="mt-1 font-mono text-2xl tabular-nums">
            {publicMetrics.total_trials || 0}
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-4 min-w-0">
          <div className="text-sm text-muted">Wearable-measurable</div>
          <div className="mt-1 font-mono text-2xl tabular-nums">
            {publicMetrics.wearable_measurable_trials || 0}
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-4 min-w-0">
          <div className="text-sm text-muted">With MA city</div>
          <div className="mt-1 font-mono text-2xl tabular-nums">
            {publicMetrics.trials_with_ma_city || 0}
          </div>
        </div>
      </div>

      <div className="text-sm text-muted">
        <p>
          Trial access concentrates in Boston: {bostonCount} trials list a Boston site, {springfieldCount} list Springfield.
        </p>
      </div>

      <div className="rounded-lg border border-line bg-surface p-4">
        <div className="mb-4 flex flex-wrap items-center gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by title or condition..."
              className="w-full rounded border border-line bg-surface py-2 pl-10 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={wearableOnly}
              onChange={(e) => setWearableOnly(e.target.checked)}
              className="h-4 w-4 rounded border-line text-accent focus:ring-2 focus:ring-accent"
            />
            <span>Wearable-measurable only</span>
          </label>
        </div>

        {searching && (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-5 w-5 animate-spin text-muted" aria-hidden="true" />
            <span className="ml-2 text-sm text-muted">Searching…</span>
          </div>
        )}

        {error && (
          <div className="rounded border border-held bg-held-soft p-3 text-sm text-held">
            <AlertTriangle className="mr-2 inline h-4 w-4" aria-hidden="true" />
            {error}
          </div>
        )}

        {!searching && !error && (
          <>
            <div className="mb-3 text-sm text-muted">
              {total} trial{total !== 1 ? "s" : ""} found
              {results.length < total && ` (showing first ${results.length})`}
            </div>

            <div className="space-y-3">
              {results.map((trial) => (
                <div key={trial.nct_id} className="rounded border border-line bg-surface p-3">
                  <div className="mb-1 flex items-start justify-between gap-2">
                    <a
                      href={`https://clinicaltrials.gov/study/${trial.nct_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-accent hover:underline"
                    >
                      {trial.title}
                    </a>
                    {trial.wearable_measurable && (
                      <span className="shrink-0 rounded bg-accent/10 px-2 py-0.5 text-xs text-accent">
                        Wearable
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-muted">
                    <span>{trial.phase_label}</span>
                    <span className="mx-2">·</span>
                    <span>{trial.conditions}</span>
                  </div>
                  {trial.cities.length > 0 && (
                    <div className="mt-1 text-xs text-muted">
                      Massachusetts sites: {trial.cities.join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function BeyondTrials({ publicMetrics }: { publicMetrics: PublicMetrics | null }) {
  if (!publicMetrics || !publicMetrics.readmissions) {
    return null;
  }

  const readmissions = publicMetrics.readmissions;

  const aboveExpected = readmissions.heart_failure_above_1;
  const withRatio = readmissions.measures["READM-30-HF-HRRP"]?.with_ratio || 0;

  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <h3 className="mb-3 font-medium">Beyond trials</h3>
      <p className="text-sm">
        {aboveExpected} of {withRatio} Massachusetts hospitals have heart-failure readmissions above the expected rate (CMS).
        The same gate can check AI summaries for post-discharge monitoring.
      </p>
    </div>
  );
}

export function Scene5Proof() {
  const [data, setData] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadMetrics = async () => {
      try {
        setLoading(true);
        setError(null);
        const metricsData = await metrics();
        setData(metricsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load metrics");
      } finally {
        setLoading(false);
      }
    };

    loadMetrics();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-6 w-6 animate-spin text-muted" aria-hidden="true" />
        <span className="ml-2 text-muted">Loading metrics…</span>
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

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Scene 5: Proof it works</h1>
        <p className="mt-2 text-muted">
          Validation scorecard, FDA credibility panel, trial finder with real data.
        </p>
      </div>

      <div className="space-y-8">
        <section>
          <h2 className="mb-4 text-xl font-semibold">Validation scorecard</h2>
          <ValidationScorecard validation={data?.validation || null} />
        </section>

        <section>
          <h2 className="mb-4 text-xl font-semibold">Regulatory fit</h2>
          <RegulatoryFit />
        </section>

        <section>
          <h2 className="mb-4 text-xl font-semibold">Trial finder</h2>
          <TrialFinder publicMetrics={data?.public || null} />
        </section>

        <section>
          <BeyondTrials publicMetrics={data?.public || null} />
        </section>
      </div>
    </div>
  );
}
