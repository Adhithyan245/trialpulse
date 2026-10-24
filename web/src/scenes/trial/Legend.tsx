import { CircleDot, CheckSquare } from "lucide-react";

export function Legend() {
  return (
    <div className="flex flex-wrap gap-4 p-3 bg-card border border-line rounded text-sm">
      <div className="flex items-center gap-2">
        <div className="relative">
          <CircleDot className="h-5 w-5 text-accent" />
        </div>
        <span className="text-muted">Pulsing (at resting HR)</span>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative">
          <svg width="20" height="20" viewBox="0 0 20 20">
            <circle
              cx="10"
              cy="10"
              r="5"
              fill="none"
              stroke="var(--watch)"
              strokeWidth="2"
            />
            <circle cx="10" cy="10" r="2.5" fill="var(--accent)" />
          </svg>
        </div>
        <span className="text-muted">Drift detected</span>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative">
          <svg width="20" height="20" viewBox="0 0 20 20">
            <circle
              cx="10"
              cy="10"
              r="2.5"
              fill="none"
              stroke="var(--accent)"
              strokeWidth="1.5"
              opacity="0.4"
            />
          </svg>
        </div>
        <span className="text-muted">Not worn / non-wear</span>
      </div>

      <div className="flex items-center gap-2">
        <CheckSquare className="h-5 w-5 text-text" />
        <span className="text-muted">Diary conflict</span>
      </div>
    </div>
  );
}
