"""Self-contained HTML timeline for a simulated run."""

from html import escape

from driftwatch.models import CriteriaChange, Objective, RunRecord, Step, StepAnalysis

_NOTICE = "The agent trace is simulated for demonstration."
_AUTH = (
    "Was this change authorized by the user? No. "
    "The original objective contains no such change."
)
_NO_DRIFT = "No drift was found."
_FIRST_LABEL = "FIRST SUSPICIOUS CHANGE"


def render_report(record: RunRecord) -> str:
    """Return one complete HTML document. Every dynamic string is escaped."""
    analyses = {item.step: item for item in record.analyses}
    steps = list(record.trace.steps)
    first = record.first_flagged_step
    badge = "REPLAY" if record.mode == "replay" else "LIVE"
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>DriftWatch</title>",
        "<style>",
        _CSS,
        "</style>",
        "</head>",
        "<body>",
        "<header>",
        '<p class="brand">DriftWatch</p>',
        f'<p class="model">{_e(record.model)}</p>',
        f'<p class="badge">{badge}</p>',
        "</header>",
        f'<p class="notice">{_NOTICE}</p>',
        "<section>",
        "<h2>Original objective</h2>",
        f"<p>{_e(record.objective.goal)}</p>",
        "<ul>",
        *[_criterion_item(item.id, item.text) for item in record.objective.criteria],
        "</ul>",
        "</section>",
        '<ol class="timeline">',
        *[
            _timeline_node(step, analyses.get(step.step), first)
            for step in steps
        ],
        "</ol>",
        f'<p class="banner">{_e(_banner(record, steps))}</p>',
        *[_card(step, analyses.get(step.step), record.objective) for step in steps],
    ]
    if first is not None:
        parts.append(f'<section class="authorization"><p>{_AUTH}</p></section>')
    parts.extend(["</body>", "</html>"])
    return "\n".join(parts) + "\n"


def _timeline_node(step: Step, analysis: StepAnalysis | None, first: int | None) -> str:
    flagged = analysis is not None and analysis.flagged
    is_first = first is not None and step.step == first
    if is_first:
        kind = "first"
    elif flagged:
        kind = "flagged"
    else:
        kind = "ok"
    score = "" if analysis is None else str(analysis.alignment_score)
    label = f'<p class="eyebrow">{_FIRST_LABEL}</p>' if is_first else ""
    return "\n".join(
        [
            f'<li class="node {kind}">',
            label,
            f'<p class="step-num">{step.step}</p>',
            f'<p class="node-title">{_e(_short_title(step.title))}</p>',
            f'<p class="score">{_e(score)}</p>',
            f'<p class="change">{_e(_change_line(analysis))}</p>',
            "</li>",
        ]
    )


def _card(step: Step, analysis: StepAnalysis | None, objective: Objective) -> str:
    if analysis is None:
        score = "n/a"
        status = "OK"
        evidence = ""
        explanation = ""
        reasons: list[str] = []
        changes: list[CriteriaChange] = []
    else:
        score = str(analysis.alignment_score)
        status = "FLAGGED" if analysis.flagged else "OK"
        evidence = analysis.evidence
        explanation = analysis.explanation
        reasons = list(analysis.flag_reasons)
        changes = list(analysis.criteria_changes)
    reason_text = ", ".join(reasons) if reasons else "None"
    return "\n".join(
        [
            "<details>",
            "<summary>"
            f"Step {step.step}: {_e(step.title)} · score {_e(score)} · {status}"
            "</summary>",
            "<dl>",
            "<dt>Stated plan</dt>",
            f"<dd>{_e(step.stated_plan)}</dd>",
            "<dt>Page text the agent saw</dt>",
            f"<dd>{_e(step.observation)}</dd>",
            "<dt>Evidence</dt>",
            f"<dd><blockquote>{_e(evidence)}</blockquote></dd>",
            "<dt>Explanation</dt>",
            f"<dd>{_e(explanation)}</dd>",
            "</dl>",
            _criteria_table(objective, changes),
            "<p><strong>Flag reasons</strong> " + _e(reason_text) + "</p>",
            "</details>",
        ]
    )


def _criteria_table(objective: Objective, changes: list[CriteriaChange]) -> str:
    grouped: dict[str, list[CriteriaChange]] = {}
    for change in changes:
        grouped.setdefault(change.criterion_id, []).append(change)
    rows: list[str] = []
    seen: set[str] = set()
    for criterion in objective.criteria:
        seen.add(criterion.id)
        matches = grouped.get(criterion.id, [])
        if not matches:
            rows.append(_row(criterion.id, criterion.text, "not reported", ""))
            continue
        for change in matches:
            rows.append(_row(criterion.id, criterion.text, change.status, change.detail))
    for change in changes:
        if change.criterion_id in seen:
            continue
        rows.append(_row(change.criterion_id, "Added criterion", change.status, change.detail))
    return "\n".join(
        [
            "<table>",
            "<thead><tr><th>Criterion</th><th>Original</th><th>Status</th><th>Detail</th></tr></thead>",
            "<tbody>",
            *rows,
            "</tbody>",
            "</table>",
        ]
    )


def _row(criterion_id: str, original: str, status: str, detail: str) -> str:
    return (
        "<tr>"
        f"<td>{_e(criterion_id)}</td>"
        f"<td>{_e(original)}</td>"
        f"<td>{_e(status)}</td>"
        f"<td>{_e(detail)}</td>"
        "</tr>"
    )


def _criterion_item(criterion_id: str, text: str) -> str:
    return f"<li>{_e(criterion_id)}: {_e(text)}</li>"


def _banner(record: RunRecord, steps: list[Step]) -> str:
    if record.first_flagged_step is None:
        return _NO_DRIFT
    titles = {step.step: step.title for step in steps}
    title = titles.get(record.first_flagged_step, "")
    if title:
        return f"Step {record.first_flagged_step} first drifted: {title}."
    return f"Step {record.first_flagged_step} first drifted."


def _change_line(analysis: StepAnalysis | None) -> str:
    if analysis is None or not analysis.criteria_changes:
        return "criteria kept"
    changed = [
        f"{change.criterion_id} {change.status}"
        for change in analysis.criteria_changes
        if change.status != "kept"
    ]
    if not changed:
        return "criteria kept"
    return ", ".join(changed)


def _short_title(title: str, limit: int = 42) -> str:
    collapsed = " ".join(title.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def _e(value: object) -> str:
    return escape(str(value), quote=True)


_CSS = """
:root {
  color-scheme: light dark;
  --bg: #f6f4ef;
  --ink: #1c1915;
  --muted: #5c564c;
  --card: #fffdf8;
  --line: #ddd6c8;
  --ok: #1f7a45;
  --ok-bg: #e7f6ec;
  --amber: #9a6700;
  --amber-bg: #fff4d6;
  --red: #9f1d1d;
  --red-bg: #fde8e6;
  --badge: #1c1915;
  --badge-ink: #fffdf8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161411;
    --ink: #f3efe6;
    --muted: #c3bbae;
    --card: #221f1b;
    --line: #3c362e;
    --ok: #8ed7a8;
    --ok-bg: #163224;
    --amber: #f0c14a;
    --amber-bg: #3a2d10;
    --red: #ffb4ab;
    --red-bg: #4a1c1c;
    --badge: #f3efe6;
    --badge-ink: #161411;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 1.25rem;
  background: var(--bg);
  color: var(--ink);
  font-family: "Segoe UI", system-ui, sans-serif;
  line-height: 1.45;
}
header, .notice, section, .banner, details, .timeline {
  max-width: 58rem;
  margin-left: auto;
  margin-right: auto;
}
header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.75rem 1.25rem;
}
.brand { font-size: 1.6rem; font-weight: 700; margin: 0; }
.model { margin: 0; color: var(--muted); overflow-wrap: anywhere; }
.badge {
  margin: 0;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  background: var(--badge);
  color: var(--badge-ink);
  font-size: 0.8rem;
  letter-spacing: 0.06em;
}
.notice, .banner, .authorization {
  padding: 0.75rem 1rem;
  border: 1px solid var(--line);
  border-radius: 0.6rem;
  background: var(--card);
}
.notice { font-weight: 600; }
.timeline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0;
  list-style: none;
}
.node {
  flex: 1 1 9rem;
  min-width: 0;
  padding: 0.7rem;
  border: 2px solid var(--line);
  border-radius: 0.7rem;
  background: var(--card);
}
.node.ok { border-color: var(--ok); background: var(--ok-bg); }
.node.flagged { border-color: var(--amber); background: var(--amber-bg); }
.node.first {
  flex-basis: 12rem;
  border-width: 3px;
  border-color: var(--red);
  background: var(--red-bg);
}
.eyebrow { margin: 0 0 0.35rem; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.03em; }
.step-num { margin: 0; font-size: 1.4rem; font-weight: 700; }
.node-title, .score, .change { margin: 0.2rem 0 0; overflow-wrap: anywhere; }
.change { color: var(--muted); font-size: 0.85rem; }
details {
  margin-top: 0.75rem;
  border: 1px solid var(--line);
  border-radius: 0.6rem;
  background: var(--card);
  padding: 0.4rem 0.8rem 0.8rem;
}
summary { cursor: pointer; font-weight: 600; }
table { width: 100%; border-collapse: collapse; }
th, td {
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid var(--line);
  padding: 0.4rem;
  overflow-wrap: anywhere;
}
blockquote { margin: 0; }
@media (max-width: 640px) {
  body { padding: 0.8rem; }
  .node { flex-basis: 100%; }
  table, thead, tbody, tr, th, td { display: block; }
  thead { display: none; }
}
"""
