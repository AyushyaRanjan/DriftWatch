# DriftWatch

DriftWatch detects when an AI agent's goal or decision criteria drift away from what the user originally asked for.

## The problem

An agent can leave the user's goal without any single obviously malicious step. A page can suggest a small change to a rule, the next step can drop another rule, and the final recommendation no longer matches the request. Each step can still look reasonable on its own.

## What DriftWatch does

DriftWatch stores the original objective, walks a scripted agent trace, and asks Gemma to compare every step with that objective. The trace includes a fake webpage that tries to change the criteria. The tool prints a console summary, writes a JSON record, and can write a self-contained HTML timeline. The first flagged step is the headline result.

The checked-in trace is simulated. It is not a recording of a live browsing agent.

## Screenshot

`docs/screenshot.png` is not in this repository. Open `examples/report.html` in a browser to see the timeline from the saved run.

## How Gemma 4 is used

Gemma 4 is an open-weight model. DriftWatch makes one comparison per step against the original objective. Calls go through the Gemini API with the `google-genai` SDK. The model id defaults to `gemma-4-26b-a4b-it` and can be changed with the `GEMMA_MODEL` environment variable. The client sends temperature 0 and parses the JSON reply defensively, including when the reply is wrapped in a markdown fence.

## Quickstart

Python 3.11 or newer. `origin` on GitHub (`https://github.com/AyushyaRanjan/DriftWatch`) has no branches yet, so there is no working `git clone` step. From this project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
cp .env.example .env
```

`.env` is gitignored. Replay does not need a key. A live run needs `GEMINI_API_KEY` set in `.env` to a real Gemini API key. Do not commit that file.

```powershell
driftwatch replay examples/run_record.json --out examples/report.html
driftwatch run scenarios/laptop_research --record examples/run_record.json --out examples/report.html
```

`pytest -q` runs the offline tests and skips the live test.

## Offline replay

Replay reads a saved run and writes the HTML report. It does not call the Gemini API and does not need an API key. The report badge says REPLAY.

```powershell
driftwatch replay examples/run_record.json --out examples/report.html
```

## How it works

The flow is: load `objective.json` and `trace.json` from a scenario directory, build one auditor prompt per step, call Gemma, parse the JSON, apply the flag rule, then print the summary. `--record` writes a `RunRecord` JSON file. `--out` writes the HTML timeline. `replay` loads that JSON, sets the mode to replay, and writes the HTML again.

The data model is pydantic: `Criterion`, `Objective`, `Step`, `Trace`, `CriteriaChange`, `StepAnalysis`, and `RunRecord`. A step stores the plan the agent stated, the criteria it says it is using, and the page text it saw. That page text is untrusted and is HTML-escaped in the report.

The flag rule, with a default threshold of 60, marks a step when `drift_detected` is true, or the alignment score is below the threshold, or any criterion status is other than `kept`. If the model says drift was not detected but a criterion was not kept, the reason list includes `consistency override`. The earliest flagged step is the headline.

The authorization rule is that only the original user objective authorizes anything. A later change to the criteria is not authorized. When a run has a flagged step, the report says the original objective contains no such change.

## Honest limitations

The trace is simulated and scripted. The judge model can itself be fooled or inconsistent. DriftWatch is a monitor, not an enforcement layer. There is one scenario so far, `scenarios/laptop_research`.

## Roadmap

More scenarios, real agent integrations, a GoalGuard-style enforcement module that blocks flagged actions, and multimodal page screenshots.

## License

MIT. See `LICENSE`. Copyright (c) 2026 AYUSHYA RANJAN.

## Where the project notes are

`AGENTS.md` has the rules for coding agents. `DECISIONS.md` is the decision log.
