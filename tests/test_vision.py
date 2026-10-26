"""Offline checks for the optional vision flag. No network."""

import json
from pathlib import Path

import pytest

from driftwatch.cli import main

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "laptop_research"
_SENTENCE = "A screenshot of the page the agent saw is attached."


class FakeClient:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.model_name = "fake-model"
        self.image_paths: list[str | None] = []
        self.prompts: list[str] = []

    def generate(self, prompt: str, image_path: str | None = None) -> str:
        self.prompts.append(prompt)
        self.image_paths.append(image_path)
        if not self._replies:
            raise AssertionError("FakeClient has no replies left")
        return self._replies.pop(0)


def test_vision_sends_the_image_only_on_step_three() -> None:
    client = FakeClient([_reply() for _ in range(6)])
    code = _invoke(["run", str(SCENARIO), "--vision"], client)

    assert code == 0
    assert len(client.image_paths) == 6
    assert client.image_paths[2] is not None
    assert Path(client.image_paths[2]).name == "brandx_page.png"
    assert all(path is None for index, path in enumerate(client.image_paths) if index != 2)
    assert _SENTENCE in client.prompts[2]
    assert all(_SENTENCE not in prompt for index, prompt in enumerate(client.prompts) if index != 2)


def test_without_vision_no_image_is_sent() -> None:
    client = FakeClient([_reply() for _ in range(6)])
    code = _invoke(["run", str(SCENARIO)], client)

    assert code == 0
    assert client.image_paths == [None] * 6
    assert all(_SENTENCE not in prompt for prompt in client.prompts)


def test_missing_vision_image_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    scenario = tmp_path / "laptop_research"
    scenario.mkdir()
    client = FakeClient([])
    code = _invoke(["run", str(scenario), "--vision"], client)
    error = capsys.readouterr().err

    assert code == 1
    assert "Vision image not found" in error
    assert "brandx_page.png" in error
    assert client.image_paths == []


def _invoke(argv: list[str], client: FakeClient) -> int:
    with pytest.raises(SystemExit) as caught:
        main(argv, client=client)
    assert isinstance(caught.value.code, int)
    return caught.value.code


def _reply() -> str:
    return json.dumps(
        {
            "alignment_score": 90,
            "drift_detected": False,
            "criteria_changes": [
                {"criterion_id": "C1", "status": "kept", "detail": "Unchanged."}
            ],
            "evidence": "under $1,000",
            "explanation": "The step still follows the original objective. Nothing was changed.",
        }
    )
