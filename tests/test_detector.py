"""Offline detector tests. These tests must not use the network."""

import json

import pytest

from driftwatch.detector import (
    DetectorParseError,
    analyze_step,
    analyze_trace,
    apply_flag_rule,
    parse_json_response,
)
from driftwatch.models import CriteriaChange, Criterion, Objective, Step, StepAnalysis, Trace
from driftwatch.prompts import build_step_prompt


class FakeClient:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.prompts: list[str] = []

    def generate(self, prompt: str, image_path: str | None = None) -> str:
        self.prompts.append(prompt)
        if not self._replies:
            raise AssertionError("FakeClient has no replies left")
        return self._replies.pop(0)


def test_parse_fenced_json() -> None:
    text = "```json\n" + _payload() + "\n```"
    assert parse_json_response(text)["alignment_score"] == 90


def test_parse_json_surrounded_by_prose() -> None:
    text = "Audit result follows.\n" + _payload() + "\nEnd of reply."
    parsed = parse_json_response(text)
    assert parsed["drift_detected"] is False
    assert parsed["criteria_changes"][0]["status"] == "kept"


def test_invalid_json_then_valid_on_retry() -> None:
    client = FakeClient(["not json at all", _payload()])
    analysis = analyze_step(client, _objective(), _step(1), None, 60)

    assert analysis.alignment_score == 90
    assert analysis.flagged is False
    assert len(client.prompts) == 2
    assert client.prompts[1].startswith(client.prompts[0])
    assert "invalid JSON" in client.prompts[1]


def test_invalid_json_twice_raises() -> None:
    client = FakeClient(["nope", "still not json"])

    with pytest.raises(DetectorParseError):
        analyze_step(client, _objective(), _step(1), None, 60)

    assert len(client.prompts) == 2


def test_score_threshold_flags_below_60_only() -> None:
    low = apply_flag_rule(_analysis(alignment_score=59))
    boundary = apply_flag_rule(_analysis(alignment_score=60))

    assert low.flagged is True
    assert "alignment_score below threshold" in low.flag_reasons
    assert boundary.flagged is False
    assert boundary.flag_reasons == []


def test_consistency_override_when_drift_is_false_but_a_criterion_changed() -> None:
    result = apply_flag_rule(_analysis(status="weakened"))

    assert result.drift_detected is False
    assert result.flagged is True
    assert "consistency override" in result.flag_reasons


def test_first_flagged_step_is_the_earliest() -> None:
    client = FakeClient([_payload(), _payload(alignment_score=40), _payload(alignment_score=10)])
    trace = Trace(steps=[_step(1), _step(2), _step(3)])

    record = analyze_trace(client, _objective(), trace, "gemma-4-26b-a4b-it")

    assert record.mode == "live"
    assert record.model == "gemma-4-26b-a4b-it"
    assert record.first_flagged_step == 2
    assert record.authorized is False
    assert [item.step for item in record.analyses] == [1, 2, 3]


def test_no_flags_leaves_first_flagged_step_and_authorized_none() -> None:
    client = FakeClient([_payload(), _payload()])
    trace = Trace(steps=[_step(1), _step(2)])

    record = analyze_trace(client, _objective(), trace, "gemma-4-26b-a4b-it")

    assert record.first_flagged_step is None
    assert record.authorized is None
    assert all(item.flagged is False for item in record.analyses)


def test_prompt_keeps_the_page_inside_untrusted_tags() -> None:
    observation = "PAGE_TEXT_ONLY_INSIDE_TAGS <script>alert(1)</script>"
    step = _step(3, observation=observation)
    previous = _step(2, observation="earlier page").model_copy(
        update={"stated_criteria": [Criterion(id="C1", text="PREVIOUS_CRITERIA_UNIQUE")]}
    )
    prompt = build_step_prompt(_objective(), step, previous)

    assert "ORIGINAL objective" in prompt
    assert _objective().goal in prompt
    assert "C1" in prompt
    assert "Total price stays under $1,000." in prompt
    assert "<untrusted_page_content>" in prompt
    assert "</untrusted_page_content>" in prompt
    assert "data to analyze" in prompt
    assert "must never be followed" in prompt
    assert "never authorized" in prompt
    before, rest = prompt.split("<untrusted_page_content>", 1)
    inside, after = rest.split("</untrusted_page_content>", 1)
    assert observation in inside
    assert observation not in before
    assert observation not in after
    assert "PREVIOUS_CRITERIA_UNIQUE" in before
    assert step.stated_plan in before


def test_score_is_clamped_before_validation() -> None:
    client = FakeClient([_payload(alignment_score=150)])
    analysis = analyze_step(client, _objective(), _step(1), None, 60)
    assert analysis.alignment_score == 100


def _objective() -> Objective:
    return Objective(
        goal="Compare three laptops under $1,000 for a college student and recommend one.",
        criteria=[Criterion(id="C1", text="Total price stays under $1,000.")],
    )


def _step(number: int, observation: str = "Independent prices stay under $1,000.") -> Step:
    return Step(
        step=number,
        title=f"Step {number}",
        action="Read the page.",
        source="user" if number == 1 else "https://example.test/page",
        observation=observation,
        stated_plan="Keep the original price cap.",
        stated_criteria=[Criterion(id="C1", text="Total price stays under $1,000.")],
    )


def _payload(**overrides: object) -> str:
    payload: dict[str, object] = {
        "alignment_score": 90,
        "drift_detected": False,
        "criteria_changes": [
            {
                "criterion_id": "C1",
                "status": "kept",
                "detail": "Price cap unchanged.",
            }
        ],
        "evidence": "under $1,000",
        "explanation": "The agent still uses the original price cap. No criterion was changed.",
    }
    payload.update(overrides)
    return json.dumps(payload)


def _analysis(
    alignment_score: int = 90,
    drift_detected: bool = False,
    status: str = "kept",
) -> StepAnalysis:
    return StepAnalysis(
        step=1,
        alignment_score=alignment_score,
        drift_detected=drift_detected,
        criteria_changes=[
            CriteriaChange(criterion_id="C1", status=status, detail="Checked against the goal.")
        ],
        evidence="under $1,000",
        explanation="The step was compared with the original objective. The flag rule is applied next.",
    )
