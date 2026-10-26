# Progress

## Phases

- [x] Phase 0: scaffold
- [x] Phase 1: gemma smoke test
- [x] Phase 2: models and scenario
- [x] Phase 3: detector
- [x] Phase 4: cli and live run
- [ ] Phase 5: report and replay
- [ ] Phase 6: readme and ci
- [ ] Phase 7: github push and verification
- [ ] Phase 8: optional vision

## Current state

Phase 4 is done. `driftwatch run` audits a simulated scenario with Gemma and can write a RunRecord. The live laptop run flagged step 3 first. Steps 1 and 2 were not flagged. `examples/run_record.json` is the untouched output of that run. Offline tests pass. The live test stays skipped unless `RUN_LIVE=1`. No `.env` file is tracked.

## Next step

Phase 5: report and replay.

## Known issues

The Phase 1 smoke script still uses json.loads on the raw reply, which failed when Gemma wrapped JSON in a markdown fence. The detector strips those fences before parsing.

## Last agent and date

Cursor Grok 4.7, 2026-10-26
