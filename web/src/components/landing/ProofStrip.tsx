import { useEffect, useState } from "react";
import { metrics } from "../../api";
import type { Metrics } from "../../types";

interface StatTile {
  value: number | string;
  caption: string;
}

interface TileState {
  loaded: boolean;
  data: StatTile | null;
}

export function ProofStrip() {
  const [tiles, setTiles] = useState<TileState[]>([
    { loaded: false, data: null },
    { loaded: false, data: null },
    { loaded: false, data: null },
    { loaded: false, data: null },
  ]);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);
    
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    let active = true;
    metrics()
      .then((m: Metrics) => {
        if (!active) return;

        const newTiles: TileState[] = [];

        // Tile 1: raw drafts held
        if (m.validation?.raw.held !== undefined && m.validation?.cases !== undefined) {
          newTiles.push({
            loaded: true,
            data: {
              value: `${m.validation.raw.held} of ${m.validation.cases}`,
              caption: "raw AI drafts held",
            },
          });
        } else {
          newTiles.push({ loaded: true, data: null });
        }

        // Tile 2: clean cases held
        if (m.validation?.clean_cases.raw_held !== undefined && m.validation?.clean_cases.total !== undefined) {
          newTiles.push({
            loaded: true,
            data: {
              value: `${m.validation.clean_cases.raw_held} of ${m.validation.clean_cases.total}`,
              caption: "held even with no injected fault",
            },
          });
        } else {
          newTiles.push({ loaded: true, data: null });
        }

        // Tile 3: unsafe reaching monitor
        if (m.validation?.pipeline.unsafe_reaching_monitor !== undefined) {
          newTiles.push({
            loaded: true,
            data: {
              value: m.validation.pipeline.unsafe_reaching_monitor.toLocaleString("en-US"),
              caption: "unsafe reports reached the monitor",
            },
          });
        } else {
          newTiles.push({ loaded: true, data: null });
        }

        // Tile 4: total trials
        if (m.public?.total_trials !== undefined) {
          newTiles.push({
            loaded: true,
            data: {
              value: m.public.total_trials.toLocaleString("en-US"),
              caption: "Massachusetts recruiting trials searchable",
            },
          });
        } else {
          newTiles.push({ loaded: true, data: null });
        }

        setTiles(newTiles);
      })
      .catch(() => {
        // If the request fails, mark all as loaded but with no data
        if (active) {
          setTiles([
            { loaded: true, data: null },
            { loaded: true, data: null },
            { loaded: true, data: null },
            { loaded: true, data: null },
          ]);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  // Only render if at least one tile is loaded
  const anyLoaded = tiles.some((t) => t.loaded);
  if (!anyLoaded) {
    return (
      <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((_, i) => (
          <SkeletonTile key={i} prefersReducedMotion={prefersReducedMotion} />
        ))}
      </div>
    );
  }

  return (
    <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {tiles.map((tileState, i) => {
        if (!tileState.loaded) {
          return <SkeletonTile key={i} prefersReducedMotion={prefersReducedMotion} />;
        }
        if (!tileState.data) {
          return null;
        }
        return (
          <div
            key={i}
            className="rounded-lg border border-line bg-card p-4"
          >
            <div className="font-mono text-3xl tabular-nums text-text">
              {tileState.data.value}
            </div>
            <div className="mt-1 text-sm text-muted">{tileState.data.caption}</div>
          </div>
        );
      })}
    </div>
  );
}

function SkeletonTile({ prefersReducedMotion }: { prefersReducedMotion: boolean }) {
  return (
    <div
      className="rounded-lg border border-line bg-card p-4"
      aria-busy={true}
    >
      <div
        className={`h-9 w-24 rounded bg-surface ${
          prefersReducedMotion ? "" : "animate-pulse"
        }`}
      />
      <div
        className={`mt-1 h-4 w-32 rounded bg-surface ${
          prefersReducedMotion ? "" : "animate-pulse"
        }`}
      />
    </div>
  );
}
