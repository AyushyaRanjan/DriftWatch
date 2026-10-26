"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from driftwatch.detector import DetectorParseError, analyze_trace
from driftwatch.llm import GemmaClient, LLMClient, LLMError
from driftwatch.models import RunRecord, Trace
from driftwatch.scenario import load_scenario


def main(argv: list[str] | None = None, client: LLMClient | None = None) -> None:
    sys.exit(run(argv, client))


def run(argv: list[str] | None = None, client: LLMClient | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    return _run_scenario(args, client)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="driftwatch")
    subcommands = parser.add_subparsers(dest="command", required=True)
    run_command = subcommands.add_parser("run", help="Audit a simulated scenario")
    run_command.add_argument("scenario", help="Scenario directory")
    run_command.add_argument("--record", type=Path, help="Write the RunRecord JSON here")
    run_command.add_argument("--threshold", type=int, default=60)
    run_command.add_argument("--out", type=Path, help="HTML report path (not implemented yet)")
    return parser


def _run_scenario(args: argparse.Namespace, client: LLMClient | None) -> int:
    scenario = Path(args.scenario)
    if not scenario.is_dir():
        print(f"Scenario directory not found: {scenario}", file=sys.stderr)
        return 1
    if args.out is not None:
        print("Note: --out is not implemented yet.")
    try:
        objective, trace = load_scenario(scenario)
        if client is None:
            client = GemmaClient()
        record = analyze_trace(
            client,
            objective,
            trace,
            _model_name(client),
            threshold=args.threshold,
        )
        if args.record is not None:
            _write_record(args.record, record)
    except (LLMError, DetectorParseError, ValueError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 1
    _print_report(trace, record)
    return 0


def _model_name(client: LLMClient) -> str:
    name = getattr(client, "model_name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    raise ValueError("The model client does not name its model.")


def _write_record(path: Path, record: RunRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _print_report(trace: Trace, record: RunRecord) -> None:
    print("Simulated trace.")
    analyses = {analysis.step: analysis for analysis in record.analyses}
    titles = {step.step: step.title for step in trace.steps}
    for step in trace.steps:
        analysis = analyses[step.step]
        status = "FLAGGED" if analysis.flagged else "OK"
        line = f"{step.step} {step.title} score {analysis.alignment_score} {status}"
        if analysis.flag_reasons:
            line += " " + ", ".join(analysis.flag_reasons)
        print(line)
    if record.first_flagged_step is None:
        print("First suspicious step: none was found")
        return
    title = titles[record.first_flagged_step]
    print(f"First suspicious step: {record.first_flagged_step} {title}")
    print("Authorized by user: No")


if __name__ == "__main__":
    main()
