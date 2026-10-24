import { useEffect, useState } from "react";
import { participantSeries } from "../../api";
import { PulseStrip } from "../checkpoint/PulseStrip";
import type { Site, PublicMetrics } from "../../types";

interface SeriesData {
  participant_id: string;
  day: number;
  metrics: Record<
    string,
    Array<{
      day: number;
      value: number;
      record_id: string;
      recorded_at: string;
    }>
  >;
  bands: Record<string, { median: number; lo: number; hi: number; q: number }>;
  diary: Array<{
    day: number;
    name: string;
    value: string;
    record_id: string;
    recorded_at: string;
  }>;
}

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

interface ParticipantDetailsProps {
  participantId: string;
  sites: Site[];
  currentDay: number;
  doseStartDay: number;
  publicMetrics: PublicMetrics | null;
}

const METRIC_LABELS: Record<string, string> = {
  hrv_rmssd: "HRV",
  resting_heart_rate: "Resting HR",
  skin_temp_celsius: "Skin temp",
  respiratory_rate: "Respiratory rate",
};

export function ParticipantDetails({
  participantId,
  sites,
  currentDay,
  doseStartDay,
  publicMetrics,
}: ParticipantDetailsProps) {
  const [seriesData, setSeriesData] = useState<SeriesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string>("hrv_rmssd");
  const [lastFetchDay, setLastFetchDay] = useState<number>(currentDay);

  // Debounced fetch when day changes
  useEffect(() => {
    if (currentDay === lastFetchDay) return;

    const timer = setTimeout(() => {
      setLastFetchDay(currentDay);
      setLoading(true);
      setError(null);

      participantSeries(participantId, currentDay)
        .then((data) => {
          setSeriesData(asSeriesData(data));
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    }, 250);

    return () => clearTimeout(timer);
  }, [currentDay, lastFetchDay, participantId]);

  // Initial fetch
  useEffect(() => {
    setLoading(true);
    setError(null);
    setLastFetchDay(currentDay);

    participantSeries(participantId, currentDay)
      .then((data) => {
        setSeriesData(asSeriesData(data));
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [participantId, currentDay]);

  // Find the participant's site
  const site = sites.find((s) =>
    seriesData
      ? s.site_id === seriesData.participant_id.split("-")[0]
      : false
  );

  // Get public health context
  const shortSleepData = publicMetrics?.short_sleep_by_county;
  const countyShortSleep = site && shortSleepData ? shortSleepData[site.county] : null;

  if (loading && !seriesData) {
    return (
      <div className="p-4 bg-card border border-line rounded text-sm text-muted">
        Loading participant data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-card border border-line rounded text-sm text-held">
        {error}
      </div>
    );
  }

  if (!seriesData) {
    return (
      <div className="p-4 bg-card border border-line rounded text-sm text-muted">
        No data available
      </div>
    );
  }

  const availableMetrics = Object.keys(seriesData.metrics).filter(
    (key) => METRIC_LABELS[key]
  );

  return (
    <div className="space-y-4">
      <div className="p-4 bg-card border border-line rounded">
        <div className="font-semibold text-lg mb-1">{participantId}</div>
        {site && (
          <div className="text-sm text-muted">
            {site.city}, {site.county} County
          </div>
        )}
      </div>

      {/* Metric tabs */}
      <div className="flex flex-wrap gap-2">
        {availableMetrics.map((metric) => (
          <button
            key={metric}
            onClick={() => setSelectedMetric(metric)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
              selectedMetric === metric
                ? "bg-accent text-white"
                : "bg-surface text-text hover:bg-accent-soft"
            }`}
          >
            {METRIC_LABELS[metric]}
          </button>
        ))}
      </div>

      {/* Metric chart */}
      <div className="p-4 bg-card border border-line rounded">
        {seriesData.metrics[selectedMetric] &&
        seriesData.bands[selectedMetric] ? (
          <PulseStrip
            participantId={seriesData.participant_id}
            currentDay={currentDay}
            doseStartDay={doseStartDay}
            windowStart={1}
            windowEnd={currentDay}
            metrics={seriesData.metrics}
            bands={seriesData.bands}
          />
        ) : (
          <div className="text-sm text-muted">
            No {METRIC_LABELS[selectedMetric]} data available
          </div>
        )}
      </div>

      {/* Public health context */}
      {countyShortSleep !== null && (
        <div className="p-3 bg-surface border border-line rounded text-sm">
          <div className="text-muted">
            {site?.county} County:{" "}
            <span className="font-mono tabular-nums font-semibold text-text">
              {(countyShortSleep * 100).toFixed(1)}%
            </span>{" "}
            of adults sleep under 7 hours (CDC PLACES 2022)
          </div>
        </div>
      )}

      {/* Link to checkpoint */}
      <a
        href={`#/checkpoint?participant=${participantId}`}
        className="block p-3 bg-accent text-white rounded text-center font-medium hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        See how the AI&rsquo;s report about {participantId} was checked
      </a>
    </div>
  );
}
