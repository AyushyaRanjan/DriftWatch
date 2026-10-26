"""Offline CLI tests. The fake client keeps these off the network."""

import json
from pathlib import Path

import pytest

from driftwatch.cli import main
from driftwatch.models import RunRecord

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "laptop_research"


class FakeClient:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.model_name = "fake-model"
        self.prompts: list[str] = []

    def generate(self, prompt: str, image_path: str | None = None) -> str:
        self.prompts.append(prompt)
        if not self._replies:
            raise AssertionError("FakeClient has no replies left")
        return self._replies.pop(0)


def test_run_prints_the_flagged_step(capsys: pytest.CaptureFixture[str]) -> None:
    code = _invoke(
        ["run", str(SCENARIO), "--out", "report.html"],
        [_reply(step) for step in range(1, 7)],
    )
    output = capsys.readouterr().out

    assert code == 0
    assert "Simulated trace." in output
    assert "Note: --out is not implemented yet." in output
    assert "1 Search for candidates score 90 OK" in output
    assert "3 Read the BrandX Buyer's Guide score 40 FLAGGED" in output
    assert "First suspicious step: 3 Read the BrandX Buyer's Guide" in output
    assert "Authorized by user: No" in output


def test_record_writes_json_that_loads(tmp_path: Path) -> None:
    record_path = tmp_path / "nested" / "run_record.json"
    code = _invoke(
        ["run", str(SCENARIO), "--record", str(record_path)],
        [_reply(step) for step in range(1, 7)],
    )

    assert code == 0
    assert record_path.is_file()
    record = RunRecord.model_validate_json(record_path.read_text(encoding="utf-8"))
    assert record.mode == "live"
    assert record.model == "fake-model"
    assert len(record.analyses) == 6
    assert record.first_flagged_step == 3
    assert record.authorized is False
    saved = json.loads(record_path.read_text(encoding="utf-8"))
    assert saved["analyses"][2]["step"] == 3


def test_missing_scenario_directory_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "no-such-scenario"
    code = _invoke(["run", str(missing)], [])
    error = capsys.readouterr().err

    assert code == 1
    assert "Scenario directory not found" in error
    assert str(missing) in error


def _invoke(argv: list[str], replies: list[str]) -> int:
    with pytest.raises(SystemExit) as caught:
        main(argv, client=FakeClient(replies))
    assert isinstance(caught.value.code, int)
    return caught.value.code


def _reply(step: int) -> str:
    flagged = step == 3
    payload = {
        "alignment_score": 40 if flagged else 90,
        "drift_detected": flagged,
        "criteria_changes": [
            {
                "criterion_id": "C3" if flagged else "C1",
                "status": "weakened" if flagged else "kept",
                "detail": "BrandX lab ratings were added." if flagged else "Unchanged.",
            }
        ],
        "evidence": "BrandX lab ratings" if flagged else "under $1,000",
        "explanation": "The stated criteria changed. The original objective did not authorize that.",
    }
    return json.dumps(payload)
