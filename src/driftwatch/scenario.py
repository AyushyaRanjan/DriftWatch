"""Load one simulated scenario from a directory."""

from pathlib import Path
from typing import TypeVar

from driftwatch.models import Criterion, Objective, Step, Trace

T = TypeVar("T", Objective, Trace)


def load_scenario(directory: str | Path) -> tuple[Objective, Trace]:
    """Return the objective and trace stored in directory.

    Step numbers must be unique and run from 1 through N. Criterion ids on the
    objective, and within each step, must be unique.
    """
    root = Path(directory)
    objective = _read_json(root / "objective.json", Objective)
    trace = _read_json(root / "trace.json", Trace)
    _require_unique_ids(objective.criteria, "objective")
    _require_step_numbers(trace.steps)
    for step in trace.steps:
        _require_unique_ids(step.stated_criteria, f"step {step.step}")
    return objective, trace


def _read_json(path: Path, model: type[T]) -> T:
    if not path.is_file():
        raise ValueError(f"Missing scenario file: {path.name}")
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _require_unique_ids(criteria: list[Criterion], where: str) -> None:
    seen: set[str] = set()
    for criterion in criteria:
        if criterion.id in seen:
            raise ValueError(f"Duplicate criterion id {criterion.id} in {where}")
        seen.add(criterion.id)


def _require_step_numbers(steps: list[Step]) -> None:
    numbers = [step.step for step in steps]
    seen: set[int] = set()
    for number in numbers:
        if number in seen:
            raise ValueError(f"Duplicate step number: {number}")
        seen.add(number)
    expected = list(range(1, len(steps) + 1))
    if sorted(numbers) != expected:
        raise ValueError(
            f"Step numbers must run from 1 to {len(steps)} with no gaps, got {numbers}"
        )
