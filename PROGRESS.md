# Progress

## Phases

- [x] Phase 0: scaffold
- [x] Phase 1: gemma smoke test
- [ ] Phase 2: models and scenario
- [ ] Phase 3: detector
- [ ] Phase 4: cli and live run
- [ ] Phase 5: report and replay
- [ ] Phase 6: readme and ci
- [ ] Phase 7: github push and verification
- [ ] Phase 8: optional vision

## Current state

Phase 1 is done. The package installs, `driftwatch` prints `0.1.0`, and offline client tests pass. `scripts/smoke_gemma.py` called `gemma-4-26b-a4b-it` and got a real reply. Temperature 0, JSON mode, and system instructions were accepted. The raw reply did not parse as JSON. D2 and D5 are accepted. No `.env` file is tracked.

## Next step

Phase 2: models and scenario.

## Known issues

The Phase 1 smoke prompt asked for only a JSON object. Gemma wrapped the object in a markdown json code fence, so json.loads on the raw reply failed.

## Last agent and date

Cursor Grok 4.7, 2026-10-26
