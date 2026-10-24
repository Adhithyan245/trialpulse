import { motion } from "motion/react";
import type { EvidenceRequest, Reading } from "../../types";
import { RINGS } from "../../checks";

const KIND_LABELS: Record<string, string> = {
  symptom_checkin: "Symptom check-in",
  wear_reminder: "Wear reminder",
  followup_question: "Follow-up question",
  predose_comparison: "Pre-dose comparison attached",
  trial_level_alert: "Trial-level alert",
};

interface EvidenceInboxProps {
  requests: EvidenceRequest[];
  replies: Reading[];
  step?: "requesting" | "received" | "desk";
}

export function EvidenceInbox({ requests, replies, step = "desk" }: EvidenceInboxProps) {
  if (requests.length === 0) {
    return null;
  }

  const replyMap = new Map(replies.map((r) => [r.record_id, r]));

  // Find the ring label for a failed dimension
  const getRingLabel = (dimension: string): string => {
    // Extract base dimension (before the colon)
    const base = dimension.includes(":") ? dimension.split(":")[0] : dimension;
    const ring = RINGS.find((r) => r.dims.includes(base));
    return ring ? ring.label : dimension;
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-text">Evidence requests</h3>
      <div className="space-y-2">
        {requests.map((req, index) => {
          const reply = req.reply_record_id
            ? replyMap.get(req.reply_record_id)
            : null;

          const showRequest = step === "received" || step === "desk";
          const showReply = (step === "received" || step === "desk") && reply;

          return (
            <motion.div
              key={req.request_id}
              className="rounded-lg border border-line bg-card p-3 text-sm"
              initial={step === "requesting" ? { x: 50, opacity: 0 } : false}
              animate={{ x: 0, opacity: 1 }}
              transition={{
                duration: 0.4,
                delay: step === "requesting" ? index * 0.6 : 0,
              }}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-medium text-accent">
                    {KIND_LABELS[req.kind] || req.kind}
                  </div>
                  {step === "requesting" && (
                    <div className="text-xs text-muted">
                      triggered by {getRingLabel(req.failed_dimension)}
                    </div>
                  )}
                </div>
                {showRequest && (
                  <div className="text-text">{req.question_text}</div>
                )}
                {showReply && (
                  <motion.div
                    className="border-t border-line pt-2 space-y-1"
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: 0.2 }}
                  >
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center rounded-full border border-line px-2 py-0.5 text-xs text-muted">
                        Simulated reply
                      </span>
                      <span className="font-mono text-xs text-muted tabular-nums">
                        {reply.record_id}
                      </span>
                    </div>
                    <div className="text-muted">{reply.value}</div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
