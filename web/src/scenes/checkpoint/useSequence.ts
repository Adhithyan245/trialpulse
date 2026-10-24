import { useState, useEffect, useCallback, useRef } from "react";
import type { RunPipeline } from "../../types";

export type SequenceStep =
  | { type: "intro"; draftIndex: number }
  | { type: "travel"; draftIndex: number; claimIndex: number; ringIndex: number }
  | { type: "verdict"; draftIndex: number }
  | { type: "requesting"; draftIndex: number }
  | { type: "received"; draftIndex: number }
  | { type: "desk" };

export interface SequenceState {
  step: SequenceStep;
  isPlaying: boolean;
  speed: 1 | 2;
  play: () => void;
  pause: () => void;
  next: () => void;
  restart: () => void;
  toggleSpeed: () => void;
}

interface UseSequenceOptions {
  pipeline: RunPipeline;
  reducedMotion: boolean;
}

/**
 * Requests that belong to round `i` (the evidence prompted by draft `i`).
 *
 * A request's sent_at is EQUAL to the next draft's as_of in recorded runs
 * (the loop sends the request and redrafts at the same instant), so the
 * correct half-open rule is:
 *
 *   draft_i.as_of < sent_at <= draft_{i+1}.as_of
 *
 * For the last draft there is no next as_of, so any request after as_of counts:
 *
 *   sent_at > draft_i.as_of
 */
export function requestsForRound(
  pipeline: RunPipeline,
  i: number
): RunPipeline["requests"] {
  const draft = pipeline.drafts[i];
  if (!draft) return [];
  const draftAsOf = new Date(draft.as_of).getTime();
  const nextDraft = pipeline.drafts[i + 1];
  const nextAsOf = nextDraft ? new Date(nextDraft.as_of).getTime() : null;

  return pipeline.requests.filter((req) => {
    const sentAt = new Date(req.sent_at).getTime();
    if (sentAt <= draftAsOf) return false;
    if (nextAsOf !== null) return sentAt <= nextAsOf;
    return true;
  });
}

export function useSequence({
  pipeline,
  reducedMotion,
}: UseSequenceOptions): SequenceState {
  const [step, setStep] = useState<SequenceStep>({
    type: "intro",
    draftIndex: 0,
  });
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<1 | 2>(1);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const getNextStep = useCallback(
    (current: SequenceStep): SequenceStep | null => {
      const numDrafts = pipeline.drafts.length;

      switch (current.type) {
        case "intro": {
          // Move to first claim travel
          const draft = pipeline.drafts[current.draftIndex];
          if (draft.claims.length === 0) {
            return { type: "verdict", draftIndex: current.draftIndex };
          }
          return {
            type: "travel",
            draftIndex: current.draftIndex,
            claimIndex: 0,
            ringIndex: 0,
          };
        }

        case "travel": {
          const draft = pipeline.drafts[current.draftIndex];
          const numRings = 7; // RINGS.length

          // Next ring for this claim
          if (current.ringIndex < numRings - 1) {
            return {
              type: "travel",
              draftIndex: current.draftIndex,
              claimIndex: current.claimIndex,
              ringIndex: current.ringIndex + 1,
            };
          }

          // Next claim
          if (current.claimIndex < draft.claims.length - 1) {
            return {
              type: "travel",
              draftIndex: current.draftIndex,
              claimIndex: current.claimIndex + 1,
              ringIndex: 0,
            };
          }

          // All claims done, move to verdict
          return { type: "verdict", draftIndex: current.draftIndex };
        }

        case "verdict": {
          const gate = pipeline.gates[current.draftIndex];

          // If held, show evidence steps (requesting and received)
          if (gate.verdict === "hold") {
            const requestsInRange = requestsForRound(
              pipeline,
              current.draftIndex
            );

            if (requestsInRange.length > 0) {
              return { type: "requesting", draftIndex: current.draftIndex };
            }
          }

          // Move to next draft or desk
          if (current.draftIndex < numDrafts - 1) {
            return { type: "intro", draftIndex: current.draftIndex + 1 };
          }

          return { type: "desk" };
        }

        case "requesting": {
          // After showing requests, show replies
          return { type: "received", draftIndex: current.draftIndex };
        }

        case "received": {
          // After showing replies, move to next draft or desk
          if (current.draftIndex < numDrafts - 1) {
            return { type: "intro", draftIndex: current.draftIndex + 1 };
          }
          return { type: "desk" };
        }

        case "desk": {
          // Final step
          return null;
        }
      }
    },
    [pipeline]
  );

  const advance = useCallback(() => {
    const next = getNextStep(step);
    if (next) {
      setStep(next);
    } else {
      setIsPlaying(false);
      clearTimer();
    }
  }, [step, getNextStep, clearTimer]);

  const next = useCallback(() => {
    setIsPlaying(false);
    clearTimer();
    advance();
  }, [advance, clearTimer]);

  const restart = useCallback(() => {
    setIsPlaying(false);
    clearTimer();
    setStep({ type: "intro", draftIndex: 0 });
  }, [clearTimer]);

  const play = useCallback(() => {
    setIsPlaying(true);
  }, []);

  const pause = useCallback(() => {
    setIsPlaying(false);
    clearTimer();
  }, [clearTimer]);

  const toggleSpeed = useCallback(() => {
    setSpeed((s) => (s === 1 ? 2 : 1));
  }, []);

  // Auto-advance when playing
  useEffect(() => {
    if (!isPlaying) return;

    const delay = reducedMotion 
      ? 10 
      : step.type === "travel" 
        ? (700 / speed) 
        : step.type === "requesting" || step.type === "received"
          ? (2000 / speed)
          : (1500 / speed);

    timerRef.current = setTimeout(() => {
      advance();
    }, delay);

    return clearTimer;
  }, [isPlaying, step, speed, reducedMotion, advance, clearTimer]);

  // Keyboard controls
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      if (e.key === " ") {
        e.preventDefault();
        if (isPlaying) {
          pause();
        } else {
          play();
        }
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        next();
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isPlaying, play, pause, next]);

  return {
    step,
    isPlaying,
    speed,
    play,
    pause,
    next,
    restart,
    toggleSpeed,
  };
}
