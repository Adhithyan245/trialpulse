import { Play, Pause } from "lucide-react";

interface TrialClockProps {
  currentDay: number;
  totalDays: number;
  doseStartDay: number;
  playing: boolean;
  speed: 1 | 2;
  onDayChange: (day: number) => void;
  onTogglePlay: () => void;
  onToggleSpeed: () => void;
}

export function TrialClock({
  currentDay,
  totalDays,
  doseStartDay,
  playing,
  speed,
  onDayChange,
  onTogglePlay,
  onToggleSpeed,
}: TrialClockProps) {
  const doseStartPercent = ((doseStartDay - 1) / (totalDays - 1)) * 100;

  return (
    <div className="flex flex-col gap-3 p-4 bg-card border border-line rounded">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={onTogglePlay}
            className="p-2 rounded bg-accent text-white hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            aria-label={playing ? "Pause" : "Play"}
          >
            {playing ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
          </button>

          <button
            onClick={onToggleSpeed}
            className="px-3 py-2 rounded bg-surface border border-line text-sm font-mono hover:bg-accent-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            aria-label={`Speed: ${speed}x`}
          >
            {speed}x
          </button>
        </div>

        <div className="font-mono text-sm">
          Day <span className="tabular-nums font-semibold">{currentDay}</span> of{" "}
          <span className="tabular-nums">{totalDays}</span>
        </div>
      </div>

      <div className="relative">
        <input
          type="range"
          min="1"
          max={totalDays}
          value={currentDay}
          onChange={(e) => onDayChange(Number(e.target.value))}
          className="w-full h-2 bg-surface rounded-lg appearance-none cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          style={{
            background: `linear-gradient(to right, var(--accent) 0%, var(--accent) ${((currentDay - 1) / (totalDays - 1)) * 100}%, var(--surface) ${((currentDay - 1) / (totalDays - 1)) * 100}%, var(--surface) 100%)`,
          }}
          aria-label={`Trial day slider, currently day ${currentDay} of ${totalDays}`}
        />

        {/* Dose start marker */}
        <div
          className="absolute top-0 w-0.5 h-2 bg-text"
          style={{
            left: `${doseStartPercent}%`,
            transform: "translateX(-50%)",
          }}
          aria-hidden="true"
        />
        <div
          className="absolute -bottom-5 text-xs text-muted font-mono whitespace-nowrap"
          style={{
            left: `${doseStartPercent}%`,
            transform: "translateX(-50%)",
          }}
        >
          dose start
        </div>
      </div>
    </div>
  );
}
