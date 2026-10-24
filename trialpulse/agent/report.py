"""Draft a safety-signal :class:`Report` from one participant's records.

The agent proposes claims; this module keeps only the citations that actually
exist in the de-identified payload, drops claims that cannot be cited, and
stamps the result as a :class:`trialpulse.core.models.Report`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from trialpulse.agent import deid
from trialpulse.agent.llm import JSONModel
from trialpulse.agent.prompts import FAULTS, PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from trialpulse.core.models import Claim, Report, Signal


class DraftClaim(BaseModel):
    type: Literal["value", "coverage", "assessment", "relationship", "certainty"]
    text: str
    cited_record_ids: list[str]


class DraftReport(BaseModel):
    claims: list[DraftClaim]
    abstained: bool


def draft_report(
    trial,
    participant_id: str,
    as_of: datetime,
    signals: list[Signal],
    model: JSONModel,
    fault: str | None = None,
    report_seq: int = 1,
) -> Report:
    """Draft a :class:`Report` for ``participant_id`` as of ``as_of``.

    ``fault`` (when given) appends a degrading instruction to the system prompt
    and is recorded in the prompt version. An unknown fault raises ValueError.
    """
    if fault is not None and fault not in FAULTS:
        raise ValueError(f"unknown fault: {fault!r}")

    payload = deid.build_payload(trial, participant_id, as_of, signals)

    system = SYSTEM_PROMPT
    if fault is not None:
        system = SYSTEM_PROMPT + "\n" + FAULTS[fault]

    draft = model.generate(system, build_user_prompt(payload), DraftReport)

    valid_ids = {r["record_id"] for r in payload["readings"]}

    report_id = f"RPT-{participant_id}-{as_of:%Y%m%d%H%M}-{report_seq}"

    claims: list[Claim] = []
    for dc in draft.claims:
        kept = [rid for rid in dc.cited_record_ids if rid in valid_ids]
        if not kept:
            # A claim with no valid citations cannot be a valid Claim; drop it.
            continue
        n = len(claims) + 1
        claims.append(
            Claim(
                claim_id=f"{report_id}-C{n}",
                type=dc.type,
                text=dc.text,
                cited_record_ids=kept,
            )
        )

    reading_times = [
        datetime.fromisoformat(r["event_time"]) for r in payload["readings"]
    ]
    window_start = min(reading_times) if reading_times else as_of

    signal_ids = [s.signal_id for s in signals if s.participant_id == participant_id]

    prompt_version = PROMPT_VERSION + (f"+{fault}" if fault else "")

    return Report(
        report_id=report_id,
        participant_id=participant_id,
        signal_ids=signal_ids,
        as_of=as_of,
        window_start=window_start,
        window_end=as_of,
        claims=claims,
        abstained=draft.abstained,
        model_id=model.name,
        prompt_version=prompt_version,
    )
