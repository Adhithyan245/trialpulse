export function Hero() {
  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-2 lg:gap-12">
      {/* Left column */}
      <div className="flex flex-col justify-center">
        <h1 className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          The AI drafts. Deterministic checks verify. Humans decide.
        </h1>
        <p className="mt-4 text-lg text-muted">
          TrialPulse watches clinical trial participants through WHOOP-style
          wearables, checks every claim an AI makes about them, and asks for the
          missing evidence before a doctor signs.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <a
            href="#/checkpoint"
            className="inline-flex items-center rounded-md bg-accent px-5 py-2.5 font-medium text-white hover:opacity-90"
          >
            Start the demo
          </a>
          <button
            type="button"
            onClick={() =>
              window.dispatchEvent(new CustomEvent("tp:start-tour"))
            }
            className="inline-flex items-center rounded-md border border-line bg-card px-5 py-2.5 font-medium text-text hover:bg-surface"
          >
            Take the tour
          </button>
          <a
            href="#/proof"
            className="inline-flex items-center px-5 py-2.5 font-medium text-accent hover:underline"
          >
            See the proof
          </a>
        </div>

        <p className="mt-3 text-xs text-muted">
          Synthetic participants · real Massachusetts trial data · recorded Gemini runs
        </p>
      </div>

      {/* Right column: animated pipeline */}
      <div className="flex items-center justify-center">
        <PipelineIllustration />
      </div>
    </div>
  );
}

function PipelineIllustration() {
  return (
    <svg
      viewBox="0 0 420 140"
      className="w-full max-w-md"
      role="img"
      aria-label="Pipeline illustration: wearable data flows through AI draft, checkpoint rings, evidence loop, to human signature"
    >
      <defs>
        {/* Pulse animation */}
        <circle id="pulse" r="3" fill="var(--accent)">
          <animate
            attributeName="cx"
            from="20"
            to="100"
            dur="6s"
            repeatCount="indefinite"
          />
        </circle>
      </defs>

      {/* Wearable pulse line */}
      <g>
        <text
          x="10"
          y="50"
          fontSize="11"
          fill="var(--muted)"
          className="font-medium"
        >
          Wearable
        </text>
        <path
          d="M 20 60 L 50 60 L 55 50 L 60 70 L 65 60 L 100 60"
          stroke="var(--accent)"
          strokeWidth="2"
          fill="none"
        />
        <use href="#pulse" y="60">
          <animate
            attributeName="opacity"
            values="0;1;1;0"
            keyTimes="0;0.05;0.95;1"
            dur="6s"
            repeatCount="indefinite"
          />
        </use>
      </g>

      {/* Arrow to AI draft */}
      <path
        d="M 100 60 L 130 60"
        stroke="var(--muted)"
        strokeWidth="1.5"
        markerEnd="url(#arrowhead)"
      />
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="10"
          refX="8"
          refY="3"
          orient="auto"
        >
          <polygon
            points="0 0, 10 3, 0 6"
            fill="var(--muted)"
          />
        </marker>
      </defs>

      {/* AI draft card */}
      <g>
        <rect
          x="130"
          y="45"
          width="70"
          height="30"
          rx="4"
          fill="var(--card)"
          stroke="var(--line)"
          strokeWidth="1.5"
        />
        <text
          x="165"
          y="65"
          fontSize="11"
          fill="var(--text)"
          textAnchor="middle"
          className="font-medium"
        >
          AI draft
        </text>
      </g>

      {/* Arrow to checkpoint */}
      <path
        d="M 200 60 L 230 60"
        stroke="var(--muted)"
        strokeWidth="1.5"
        markerEnd="url(#arrowhead)"
      />

      {/* Checkpoint: 7 rings, one turns red */}
      <g>
        <text
          x="282"
          y="35"
          fontSize="10"
          fill="var(--muted)"
          textAnchor="middle"
        >
          Checkpoint
        </text>
        {[0, 1, 2, 3, 4, 5, 6].map((i) => {
          const cx = 240 + i * 14;
          const isHeld = i === 3;
          return (
            <circle
              key={i}
              cx={cx}
              cy="60"
              r="6"
              fill="none"
              stroke={isHeld ? "var(--held)" : "var(--line)"}
              strokeWidth="1.5"
            />
          );
        })}
      </g>

      {/* Evidence loop arrow (from checkpoint back to participant) */}
      <g>
        <path
          d="M 282 70 C 282 112, 210 116, 120 110 S 60 88, 60 68"
          stroke="var(--watch)"
          strokeWidth="1.5"
          fill="none"
          markerEnd="url(#arrowhead-watch)"
        />
        <defs>
          <marker
            id="arrowhead-watch"
            markerWidth="10"
            markerHeight="10"
            refX="8"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="var(--watch)" />
          </marker>
        </defs>
        <text
          x="165"
          y="128"
          fontSize="10"
          fill="var(--watch)"
          textAnchor="middle"
          className="font-medium"
        >
          asks for evidence
        </text>
      </g>

      {/* Arrow from checkpoint to seal */}
      <path
        d="M 330 60 L 360 60"
        stroke="var(--muted)"
        strokeWidth="1.5"
        markerEnd="url(#arrowhead)"
      />

      {/* Human signs seal */}
      <g>
        <circle
          cx="380"
          cy="60"
          r="18"
          fill="none"
          stroke="var(--pass)"
          strokeWidth="2"
        />
        <path
          d="M 375 60 L 378 63 L 385 56"
          stroke="var(--pass)"
          strokeWidth="2"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <text
          x="380"
          y="90"
          fontSize="10"
          fill="var(--muted)"
          textAnchor="middle"
          className="font-medium"
        >
          Human signs
        </text>
      </g>

      {/* Make static with prefers-reduced-motion */}
      <style>{`
        @media (prefers-reduced-motion: reduce) {
          animate {
            animation-duration: 0.001ms !important;
          }
        }
      `}</style>
    </svg>
  );
}
