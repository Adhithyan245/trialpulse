"""Command-line entry point for TrialPulse.

Commands:
  signals --day N [--hour H] [--participant P]
  report PARTICIPANT --day N [--hour H] [--fault NAME] [--json]
  generate [--seed S] [--out PATH]
"""

import argparse
import sys
from datetime import datetime, timedelta

from trialpulse.agent.llm import GeminiModel, LLMError
from trialpulse.agent.report import draft_report
from trialpulse.data.generator import TRIAL_START, generate
from trialpulse.signals.detect import detect


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m trialpulse")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # signals command
    signals_parser = subparsers.add_parser(
        "signals", help="Detect signals for a given trial day"
    )
    signals_parser.add_argument("--day", type=int, required=True, help="Trial day")
    signals_parser.add_argument("--hour", type=int, default=23, help="Hour of day (default: 23)")
    signals_parser.add_argument(
        "--participant", type=str, help="Filter to a single participant"
    )

    # report command
    report_parser = subparsers.add_parser("report", help="Draft a report for a participant")
    report_parser.add_argument("participant", help="Participant ID (e.g., P-07)")
    report_parser.add_argument("--day", type=int, required=True, help="Trial day")
    report_parser.add_argument("--hour", type=int, default=23, help="Hour of day (default: 23)")
    report_parser.add_argument("--fault", type=str, help="Fault mode to inject")
    report_parser.add_argument(
        "--json", action="store_true", help="Output full report as JSON"
    )

    # generate command
    generate_parser = subparsers.add_parser("generate", help="Generate a trial")
    generate_parser.add_argument("--seed", type=int, default=7, help="Random seed (default: 7)")
    generate_parser.add_argument(
        "--out", default="data/synthetic/trial.json", help="Output path"
    )

    args = parser.parse_args(argv)

    try:
        if args.command == "signals":
            return _cmd_signals(args)
        elif args.command == "report":
            return _cmd_report(args)
        elif args.command == "generate":
            return _cmd_generate(args)
    except LLMError as e:
        print(f"error: {e.args[0]}", file=sys.stderr)
        return 2

    return 0


def _cmd_signals(args) -> int:
    trial = generate()
    as_of = TRIAL_START + timedelta(days=args.day - 1, hours=args.hour)
    signals = detect(trial, as_of)

    if args.participant:
        signals = [s for s in signals if s.participant_id == args.participant]

    for sig in signals:
        z_str = f"{sig.z_score:.2f}" if sig.z_score is not None else "-"
        print(
            f"{sig.participant_id}  {sig.type}  {sig.metric}  "
            f"start={_trial_day(sig.window_start)}  z={z_str}  cites={len(sig.record_ids)}"
        )

    return 0


def _cmd_report(args) -> int:
    trial = generate()
    as_of = TRIAL_START + timedelta(days=args.day - 1, hours=args.hour)
    signals = detect(trial, as_of)

    model = GeminiModel()
    report = draft_report(
        trial,
        args.participant,
        as_of,
        signals,
        model,
        fault=args.fault,
        report_seq=1,
    )

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print(f"model={model.name} prompt={report.prompt_version}")
        for claim in report.claims:
            print(f"[{claim.type}] {claim.text}  ({len(claim.cited_record_ids)} cites)")

    return 0


def _cmd_generate(args) -> int:
    data = generate(seed=args.seed)
    from trialpulse.data.generator import write_json

    write_json(data, args.out)
    print(args.out)
    return 0


def _trial_day(dt: datetime) -> int:
    """Convert datetime to trial day (1-indexed)."""
    return (dt.date() - TRIAL_START.date()).days + 1


if __name__ == "__main__":
    sys.exit(main())
