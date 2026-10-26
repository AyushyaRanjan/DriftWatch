"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from driftwatch.detector import DetectorParseError, analyze_trace
from driftwatch.llm import GemmaClient, LLMClient, LLMError
from driftwatch.models import RunRecord, Trace
from driftwatch.report import render_report
from driftwatch.scenario import load_scenario


def main(argv: list[str] | None = None, client: LLMClient | None = None) -> None:
    sys.exit(run(argv, client))


def run(argv: list[str] | None = None, client: LLMClient | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "replay":
        return _replay(args)
    return _run_scenario(args, client)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="driftwatch")
    subcommands = parser.add_subparsers(dest="command", required=True)
    run_command = subcommands.add_parser("run", help="Audit a simulated scenario")
    run_command.add_argument("scenario", help="Scenario directory")
    run_command.add_argument("--record", type=Path, help="Write the RunRecord JSON here")
    run_command.add_argument("--threshold", type=int, default=60)
    run_command.add_argument("--out", type=Path, help="Write the HTML timeline here")
    run_command.add_argument(
        "--vision",
        action="store_true",
        help="Attach the step 3 page screenshot",
    )
    replay_command = subcommands.add_parser("replay", help="Render a saved run without calling the API")
    replay_command.add_argument("record", type=Path, help="RunRecord JSON")
    replay_command.add_argument("--out", type=Path, required=True, help="HTML report path")
    return parser


def _run_scenario(args: argparse.Namespace, client: LLMClient | None) -> int:
    scenario = Path(args.scenario)
    if not scenario.is_dir():
        print(f"Scenario directory not found: {scenario}", file=sys.stderr)
        return 1
    vision_image: str | None = None
    if args.vision:
        image = scenario / "screenshots" / "brandx_page.png"
        if not image.is_file():
            print(f"Vision image not found: {image}", file=sys.stderr)
            return 1
        vision_image = str(image)
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
            vision_image=vision_image,
        )
        if args.record is not None:
            _write_record(args.record, record)
        if args.out is not None:
            _write_html(args.out, render_report(record))
    except (LLMError, DetectorParseError, ValueError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 1
    _print_report(trace, record)
    if args.out is not None:
        print(f"Wrote report to {args.out}")
    return 0


def _replay(args: argparse.Namespace) -> int:
    path = Path(args.record)
    if not path.is_file():
        print(f"Record file not found: {path}", file=sys.stderr)
        return 1
    try:
        record = RunRecord.model_validate_json(path.read_text(encoding="utf-8"))
        replay = record.model_copy(update={"mode": "replay"})
        _write_html(Path(args.out), render_report(replay))
    except (OSError, ValidationError, ValueError) as exc:
        print(f"Invalid run record: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote replay report to {args.out}")
    return 0


def _model_name(client: LLMClient) -> str:
    name = getattr(client, "model_name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    raise ValueError("The model client does not name its model.")


def _write_record(path: Path, record: RunRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _write_html(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


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
