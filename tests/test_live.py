"""Live Gemma check. Skipped unless RUN_LIVE=1. Does not assert which step is flagged."""

import os
from pathlib import Path

import pytest

from driftwatch.cli import main
from driftwatch.models import RunRecord

pytestmark = pytest.mark.live

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "laptop_research"


@pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="set RUN_LIVE=1 to call Gemma")
def test_live_run_record_has_six_analyses(tmp_path: Path) -> None:
    record_path = tmp_path / "run_record.json"
    with pytest.raises(SystemExit) as caught:
        main(["run", str(SCENARIO), "--record", str(record_path)])
    assert caught.value.code == 0
    record = RunRecord.model_validate_json(record_path.read_text(encoding="utf-8"))
    assert record.mode == "live"
    assert len(record.analyses) == 6
    assert {analysis.step for analysis in record.analyses} == {1, 2, 3, 4, 5, 6}
