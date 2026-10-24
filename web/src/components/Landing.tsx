import { useEffect, useState } from "react";
import { metrics } from "../api";
import { useRole } from "../role";
import type { Role, ValidationMetrics } from "../types";

const ROLE_LINES: { id: Role; label: string; line: string }[] = [
  {
    id: "monitor",
    label: "Monitor",
    line: "Review and approve safety-signal reports.",
  },
  {
    id: "coordinator",
    label: "Coordinator",
    line: "Watch device-wear compliance across sites.",
  },
  {
    id: "safety_reviewer",
    label: "Safety reviewer",
    line: "See the unblinded arm and the validation scorecard.",
  },
];

function HeadlineNumbers({ v }: { v: ValidationMetrics }) {
  const stats = [
    { value: v.cases, label: "validation cases" },
    { value: v.raw.held, label: "raw drafts held by the gate" },
    {
      value: v.pipeline.unsafe_reaching_monitor,
      label: "unsafe reports reaching the monitor",
    },
  ];
  return (
    <dl className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
      {stats.map((s) => (
        <div
          key={s.label}
          className="rounded-lg border border-line bg-card p-4"
        >
          <dt className="text-sm text-muted">{s.label}</dt>
          <dd className="mt-1 font-mono text-2xl tabular-nums text-text">
            {s.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function Landing() {
  const { setRole } = useRole();
  const [validation, setValidation] = useState<ValidationMetrics | null>(null);

  useEffect(() => {
    let active = true;
    metrics()
      .then((m) => {
        if (active) setValidation(m.validation);
      })
      .catch(() => {
        // Show no numbers rather than fake ones if the request fails.
        if (active) setValidation(null);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
        The AI drafts. Deterministic checks verify. Humans decide.
      </h1>
      <p className="mt-4 text-lg text-muted">
        TrialPulse watches clinical trial participants through WHOOP-style
        wearables, checks every claim an AI makes about them, and asks for the
        missing evidence before a doctor signs.
      </p>

      <div className="mt-6">
        <a
          href="#/checkpoint"
          className="inline-flex items-center rounded-md bg-accent px-5 py-2.5 font-medium text-white hover:opacity-90"
        >
          Start the demo
        </a>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {ROLE_LINES.map((r) => (
          <button
            key={r.id}
            type="button"
            onClick={() => setRole(r.id)}
            className="rounded-lg border border-line bg-card p-4 text-left hover:border-accent"
          >
            <div className="font-medium text-text">{r.label}</div>
            <div className="mt-1 text-sm text-muted">{r.line}</div>
          </button>
        ))}
      </div>

      {validation && <HeadlineNumbers v={validation} />}
    </div>
  );
}
