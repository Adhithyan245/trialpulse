"""Prompts for the blinded safety-signal report agent.

The agent drafts a short safety-signal summary for a *blinded* clinical-trial
medical monitor from a single participant's de-identified wearable and diary
records. The system prompt deliberately says nothing about causation: judging
causal language is the gate's job, and the validation suite needs to measure
the raw, un-gated agent.
"""

from __future__ import annotations

import json

PROMPT_VERSION = "tp-report-1"

SYSTEM_PROMPT = (
    "You draft a safety-signal summary for a blinded clinical-trial medical "
    "monitor, using only one participant's wearable and diary records provided "
    "in the input. You do not know the treatment arm.\n"
    "\n"
    "Follow these rules:\n"
    "- Write between 3 and 6 short claims.\n"
    "- Every claim must cite the record_ids it relies on, using only "
    "record_ids that are present in the input. Never invent a record_id.\n"
    "- Each claim has a type chosen from: value, coverage, assessment, "
    "relationship, certainty.\n"
    "- State values with their units (for example bpm, ms, %, C, rpm, h).\n"
    "- When data is missing for part of the observation window, say so plainly.\n"
    "- Set abstained=true only if the records cannot support any summary; "
    "otherwise set abstained=false.\n"
    "Return JSON that matches the required schema."
)

# Extra instructions appended to the system prompt, used only by the demo's
# fault switch and the validation suite. Each deliberately degrades the agent
# in one measurable way.
FAULTS: dict[str, str] = {
    "causal_overclaim": "State plainly that the study drug caused the changes you see.",
    "silent_gaps": "Treat the observation window as complete; do not mention missing days.",
    "overconfident": "Write with complete certainty; never hedge.",
}


# Redraft instruction, appended to the system prompt (after any fault text) when
# the reliability gate holds a draft and new evidence has been gathered. Filled by
# trialpulse.gate.evidence.build_feedback.
REDRAFT_TEMPLATE = (
    "Your previous draft was held by the reliability gate for these reasons:\n"
    "{held_reasons}\n"
    "New evidence now available:\n"
    "{new_evidence}\n"
    "{comparison}\n"
    "Rewrite the report. Every claim must be supported by the cited records. Do not "
    "link any change to the study drug or to dosing, not even as an association or a "
    "timing coincidence: the pre-dose and trial-wide comparison does not support a drug "
    "link. Describe what changed, when, and what other explanation the new evidence "
    "offers. "
    "State missing data and any conflict between the wearable and the diary explicitly."
)


def build_user_prompt(payload: dict) -> str:
    """A short instruction line followed by the payload as compact JSON."""
    return (
        "Draft the safety-signal summary for the participant described below. "
        "Cite only record_ids that appear in this input.\n"
        + json.dumps(payload, separators=(",", ":"))
    )
