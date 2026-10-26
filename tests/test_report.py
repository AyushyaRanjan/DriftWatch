"""Offline report and replay tests. These tests must not use the network."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from driftwatch.cli import main
from driftwatch.models import (
    CriteriaChange,
    Criterion,
    Objective,
    RunRecord,
    Step,
    StepAnalysis,
    Trace,
)
from driftwatch.report import render_report

RECORD = Path(__file__).resolve().parents[1] / "examples" / "run_record.json"
_SCRIPT = "<script>alert(1)</script>"


def test_step_three_script_tag_is_escaped_and_markup_stays_local() -> None:
    html = render_report(_load_example())
    lowered = html.lower()

    assert _SCRIPT not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script" not in lowered
    assert "<link" not in lowered
    assert "@import" not in lowered
    assert "src=http" not in lowered
    assert "href=http" not in lowered


def test_first_flagged_step_is_inside_the_first_suspicious_node() -> None:
    html = render_report(_load_example())
    start = html.index("FIRST SUSPICIOUS CHANGE")
    node = html[html.rfind("<li", 0, start) : html.find("</li>", start)]

    assert ">3<" in node
    assert "C3 replaced" in node


def test_clean_record_says_criteria_kept() -> None:
    html = render_report(_record(flagged=False))
    node = html[html.index('<li class="node') : html.index("</li>", html.index('<li class="node'))]

    assert "criteria kept" in node
    assert "replaced" not in node


def test_no_flags_omits_the_authorization_block() -> None:
    html = render_report(_record(flagged=False))

    assert "No drift was found." in html
    assert "Was this change authorized by the user?" not in html
    assert "FIRST SUSPICIOUS CHANGE" not in html


def test_replay_mode_shows_replay_badge() -> None:
    html = render_report(_load_example().model_copy(update={"mode": "replay"}))

    assert "REPLAY" in html


def test_replay_examples_record_succeeds(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "report.html"
    code = _invoke(["replay", str(RECORD), "--out", str(out)])
    html = out.read_text(encoding="utf-8")

    assert code == 0
    assert "REPLAY" in html
    assert "The agent trace is simulated for demonstration." in html
    assert _SCRIPT not in html


def test_missing_or_invalid_record_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = _invoke(["replay", str(tmp_path / "missing.json"), "--out", str(tmp_path / "a.html")])
    missing_error = capsys.readouterr().err
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    invalid = _invoke(["replay", str(bad), "--out", str(tmp_path / "b.html")])
    invalid_error = capsys.readouterr().err

    assert missing == 1
    assert "not found" in missing_error
    assert invalid == 1
    assert "Invalid run record" in invalid_error


def _load_example() -> RunRecord:
    return RunRecord.model_validate_json(RECORD.read_text(encoding="utf-8"))


def _invoke(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as caught:
        main(argv)
    assert isinstance(caught.value.code, int)
    return caught.value.code


def _record(flagged: bool) -> RunRecord:
    step = Step(
        step=1,
        title="Search for candidates",
        action="Search.",
        source="user",
        observation="Look for laptops.",
        stated_plan="Gather three candidates from independent sources.",
        stated_criteria=[Criterion(id="C1", text="Total price stays under $1,000.")],
    )
    return RunRecord(
        model="gemma-4-26b-a4b-it",
        mode="live",
        created_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
        objective=Objective(
            goal="Compare three laptops under $1,000 for a college student and recommend one.",
            criteria=[Criterion(id="C1", text="Total price stays under $1,000.")],
        ),
        trace=Trace(steps=[step]),
        analyses=[
            StepAnalysis(
                step=1,
                alignment_score=90,
                drift_detected=False,
                criteria_changes=[
                    CriteriaChange(criterion_id="C1", status="kept", detail="Unchanged.")
                ],
                evidence="under $1,000",
                explanation="The step still follows the original objective. Nothing was changed.",
                flagged=flagged,
                flag_reasons=["drift_detected"] if flagged else [],
            )
        ],
        first_flagged_step=1 if flagged else None,
        authorized=False if flagged else None,
        threshold=60,
    )
