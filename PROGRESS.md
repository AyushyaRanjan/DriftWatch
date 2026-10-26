# Progress

## Phases

- [x] Phase 0: scaffold
- [x] Phase 1: gemma smoke test
- [x] Phase 2: models and scenario
- [x] Phase 3: detector
- [x] Phase 4: cli and live run
- [x] Phase 5: report and replay
- [ ] Phase 6: readme and ci
- [ ] Phase 7: github push and verification
- [ ] Phase 8: optional vision

## Current state

Phase 5 is done. `driftwatch replay` renders a saved run as one self-contained HTML file and labels it REPLAY. `examples/report.html` was produced from `examples/run_record.json` without another API call. Page text is HTML-escaped. Offline tests pass. The live test stays skipped unless `RUN_LIVE=1`. No `.env` file is tracked.

## Next step

Phase 6: readme and ci.

## Known issues

The Phase 1 smoke script still uses json.loads on the raw reply, which failed when Gemma wrapped JSON in a markdown fence. The detector strips those fences before parsing.

## Last agent and date

Cursor Grok 4.7, 2026-10-26
