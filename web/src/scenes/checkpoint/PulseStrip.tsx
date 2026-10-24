interface Point {
  day: number;
  value: number;
  record_id: string;
  recorded_at: string;
}

// The API's personal bands are keyed median/lo/hi/q (see
// trialpulse.signals.baseline.personal_bands and GET /api/participants/{pid}/series).
interface Band {
  median: number;
  lo: number;
  hi: number;
  q: number;
}

interface PulseStripProps {
  participantId: string;
  currentDay: number;
  doseStartDay: number;
  windowStart: number;
  windowEnd: number;
  metrics: Record<string, Point[]>;
  bands: Record<string, Band>;
}

// hrv_rmssd deviates downward: a reading is "drift" when it falls below the
// band's lower edge. Mirror of trialpulse.signals.baseline.DIRECTIONS.
const DRIFT_DIRECTION = "down" as const;

export function PulseStrip({
  currentDay,
  doseStartDay,
  metrics,
  bands,
}: PulseStripProps) {
  const hrv = metrics.hrv_rmssd ?? [];
  const band = bands.hrv_rmssd;

  if (hrv.length === 0 || !band) {
    return <div className="text-sm text-muted">No readings yet</div>;
  }

  // y domain: min/max over point values and the band edges, padded 10%.
  const values = hrv.map((p) => p.value);
  const dataMin = Math.min(...values, band.lo);
  const dataMax = Math.max(...values, band.hi);
  const span = dataMax - dataMin;
  const yPadding = span > 0 ? span * 0.1 : Math.abs(dataMax) * 0.1 || 1;
  const yMin = dataMin - yPadding;
  const yMax = dataMax + yPadding;

  const width = 400;
  const height = 80;
  const margin = { top: 5, right: 10, bottom: 20, left: 30 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;

  const daySpan = currentDay > 1 ? currentDay - 1 : 1;
  const xScale = (day: number) =>
    margin.left + ((day - 1) / daySpan) * chartWidth;
  const yScale = (value: number) =>
    margin.top + chartHeight - ((value - yMin) / (yMax - yMin)) * chartHeight;

  // Build the line path (gaps for missing days, never interpolated).
  let linePath = "";
  for (let i = 0; i < hrv.length; i++) {
    const point = hrv[i];
    const x = xScale(point.day);
    const y = yScale(point.value);
    if (i === 0 || hrv[i - 1].day !== point.day - 1) {
      linePath += `M ${x} ${y} `;
    } else {
      linePath += `L ${x} ${y} `;
    }
  }

  // Band shading, split on gaps so missing days stay blank.
  function buildBandPath(points: Point[]): string {
    const topLine = points
      .map((p) => `${xScale(p.day)},${yScale(band.hi)}`)
      .join(" L ");
    const bottomLine = points
      .map((p) => `${xScale(p.day)},${yScale(band.lo)}`)
      .reverse()
      .join(" L ");
    return `M ${topLine} L ${bottomLine} Z`;
  }

  const bandSegments: string[] = [];
  let currentSegment: Point[] = [];
  for (const point of hrv) {
    if (
      currentSegment.length === 0 ||
      currentSegment[currentSegment.length - 1].day === point.day - 1
    ) {
      currentSegment.push(point);
    } else {
      bandSegments.push(buildBandPath(currentSegment));
      currentSegment = [point];
    }
  }
  if (currentSegment.length > 0) {
    bandSegments.push(buildBandPath(currentSegment));
  }

  // Change window: from the first drift day (day >= dose start whose value is
  // outside the band in the metric's direction) to the last day present.
  const outside = (value: number) =>
    DRIFT_DIRECTION === "down" ? value < band.lo : value > band.hi;
  const firstDrift = hrv.find((p) => p.day >= doseStartDay && outside(p.value));
  const lastDay = hrv[hrv.length - 1].day;

  const windowRect =
    firstDrift && firstDrift.day <= lastDay
      ? {
          x: xScale(firstDrift.day),
          width: Math.max(0, xScale(lastDay) - xScale(firstDrift.day)),
        }
      : null;

  const doseX = xScale(doseStartDay);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      style={{ display: "block", height: "auto" }}
      className="border border-line rounded bg-card"
      role="img"
      aria-label={`HRV strip for days 1 to ${currentDay}`}
    >
      <defs>
        <pattern
          id="change-window-pattern"
          width="4"
          height="4"
          patternUnits="userSpaceOnUse"
        >
          <rect width="4" height="4" fill="var(--accent-soft)" />
          <path
            d="M0,4 l4,-4 M-1,1 l2,-2 M3,5 l2,-2"
            stroke="var(--accent)"
            strokeWidth="1"
            opacity="0.3"
          />
        </pattern>
      </defs>

      {/* Change window shading (first drift day to last day) */}
      {windowRect && (
        <rect
          x={windowRect.x}
          y={margin.top}
          width={windowRect.width}
          height={chartHeight}
          fill="url(#change-window-pattern)"
          opacity="0.5"
        />
      )}

      {/* Personal band (shaded area) */}
      {bandSegments.map((path, i) => (
        <path key={i} d={path} fill="var(--accent-soft)" opacity="0.3" />
      ))}

      {/* HRV line */}
      <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth="2" />

      {/* Data points (dots) */}
      {hrv.map((point) => (
        <circle
          key={point.record_id}
          cx={xScale(point.day)}
          cy={yScale(point.value)}
          r="3"
          fill="var(--accent)"
        />
      ))}

      {/* Dose start marker */}
      <line
        x1={doseX}
        y1={margin.top}
        x2={doseX}
        y2={height - margin.bottom}
        stroke="var(--text)"
        strokeWidth="1"
        strokeDasharray="3,3"
      />
      <text
        x={doseX}
        y={height - 3}
        textAnchor="middle"
        fontSize="9"
        fill="var(--muted)"
        fontFamily="IBM Plex Mono"
      >
        dose start
      </text>

      {/* X-axis */}
      <line
        x1={margin.left}
        y1={height - margin.bottom}
        x2={width - margin.right}
        y2={height - margin.bottom}
        stroke="var(--line)"
      />

      {/* Day labels */}
      <text
        x={margin.left}
        y={height - 3}
        fontSize="9"
        fill="var(--muted)"
        fontFamily="IBM Plex Mono"
      >
        1
      </text>
      <text
        x={width - margin.right}
        y={height - 3}
        textAnchor="end"
        fontSize="9"
        fill="var(--muted)"
        fontFamily="IBM Plex Mono"
      >
        {currentDay}
      </text>
    </svg>
  );
}
