import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";

type Step = {
  hash: string;
  title: string;
  body: string;
};

const STEPS: Step[] = [
  {
    hash: "#/trial",
    title: "The trial, alive",
    body:
      "40 synthetic participants across Boston, Worcester and Springfield. Each dot pulses at that person's resting heart rate. Press play: amber halos are changes outside a person's own range; hollow dots are days the device was not worn.",
  },
  {
    hash: "#/checkpoint",
    title: "The checkpoint",
    body:
      "An AI drafted a safety report for P-07 and claimed the study drug caused the change. Press Play: every claim travels through 7 checks. Watch it stop at Causation, then see TrialPulse ask the participant for the missing evidence.",
  },
  {
    hash: "#/seal",
    title: "Sign and seal",
    body:
      "A human signs every report. Each action is a block whose fingerprint includes the one before it. Try Tamper on any block: the chain breaks from that point on.",
  },
  {
    hash: "#/verified",
    title: "How this was verified",
    body:
      "Every number the AI wrote is recomputed from the records it cited, and drug links are tested against pre-dose and trial-wide controls without unblinding the monitor.",
  },
  {
    hash: "#/proof",
    title: "Proof it works",
    body:
      "Measured on 12 recorded Gemini runs. Plus the FDA credibility mapping and a search over 3,131 real Massachusetts trials.",
  },
];

const DONE_KEY = "tp_tour_done";

function markDone(): void {
  try {
    localStorage.setItem(DONE_KEY, "1");
  } catch {
    // ignore
  }
}

function hasStartFlag(): boolean {
  // "?tour=1" in the location search.
  if (typeof window.location.search === "string" && window.location.search.includes("tour=1")) {
    return true;
  }
  // "#/?tour" as a query-like suffix on the hash.
  const hash = window.location.hash || "";
  const qIndex = hash.indexOf("?");
  if (qIndex !== -1 && hash.slice(qIndex + 1).includes("tour")) {
    return true;
  }
  return false;
}

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

export function Tour() {
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [shown, setShown] = useState(false);
  const cardRef = useRef<HTMLDivElement | null>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const reduceMotion = prefersReducedMotion();

  const start = useCallback(() => {
    previousFocus.current = (document.activeElement as HTMLElement) ?? null;
    setIndex(0);
    window.location.hash = STEPS[0].hash;
    setOpen(true);
  }, []);

  const close = useCallback(() => {
    markDone();
    setOpen(false);
    setShown(false);
    const el = previousFocus.current;
    if (el && typeof el.focus === "function") {
      el.focus();
    }
  }, []);

  // Start on the custom event or the URL flag. Never auto-start otherwise.
  useEffect(() => {
    const onStart = () => start();
    window.addEventListener("tp:start-tour", onStart);
    if (hasStartFlag()) {
      start();
    }
    return () => window.removeEventListener("tp:start-tour", onStart);
  }, [start]);

  // Move focus to the card when a step opens and trigger the slide-in.
  useEffect(() => {
    if (open && cardRef.current) {
      cardRef.current.focus();
    }
    if (open) {
      if (reduceMotion) {
        setShown(true);
      } else {
        setShown(false);
        const id = window.requestAnimationFrame(() => setShown(true));
        return () => window.cancelAnimationFrame(id);
      }
    }
    return undefined;
  }, [open, index, reduceMotion]);

  const goTo = useCallback((next: number) => {
    setIndex(next);
    window.location.hash = STEPS[next].hash;
  }, []);

  const onNext = useCallback(() => {
    if (index >= STEPS.length - 1) {
      close();
    } else {
      goTo(index + 1);
    }
  }, [index, goTo, close]);

  const onBack = useCallback(() => {
    if (index > 0) {
      goTo(index - 1);
    }
  }, [index, goTo]);

  const onKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        close();
      }
    },
    [close],
  );

  if (!open) return null;

  const step = STEPS[index];
  const isLast = index === STEPS.length - 1;
  const titleId = "tp-tour-title";

  return (
    <div
      ref={cardRef}
      role="dialog"
      aria-modal="false"
      aria-labelledby={titleId}
      tabIndex={-1}
      onKeyDown={onKeyDown}
      style={
        reduceMotion
          ? undefined
          : {
              opacity: shown ? 1 : 0,
              transform: shown ? "translateY(0)" : "translateY(0.75rem)",
              transition: "opacity 200ms ease, transform 200ms ease",
            }
      }
      className="fixed bottom-4 left-0 right-0 z-50 mx-auto w-[calc(100vw-2rem)] max-w-[360px] rounded-lg border-l-4 border-accent bg-card p-4 shadow-xl sm:left-auto sm:right-4 sm:mx-0"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs text-muted">
          Step {index + 1} of {STEPS.length}
        </span>
        <button
          type="button"
          onClick={close}
          className="text-sm text-muted underline hover:text-text"
        >
          Skip tour
        </button>
      </div>

      <h2 id={titleId} className="mt-2 text-base font-semibold text-text">
        {step.title}
      </h2>
      <p className="mt-1 text-sm text-muted">{step.body}</p>

      <div className="mt-4 flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={onBack}
          disabled={index === 0}
          className="rounded-md border border-line px-3 py-1.5 text-sm text-text disabled:opacity-40"
        >
          Back
        </button>
        <button
          type="button"
          onClick={onNext}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white"
        >
          {isLast ? "Finish" : "Next"}
        </button>
      </div>
    </div>
  );
}
