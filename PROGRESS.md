# Progress

## Phases

- [x] Phase 0: scaffold
- [x] Phase 1: gemma smoke test
- [x] Phase 2: models and scenario
- [x] Phase 3: detector
- [x] Phase 4: cli and live run
- [x] Phase 5: report and replay
- [x] Phase 6: readme and ci
- [x] Phase 7: github push and verification
- [x] Phase 8: optional vision

## Current state

Phase 8 is done. `driftwatch run --vision` sends the BrandX page screenshot with step 3 only. A live run wrote `examples/run_record_vision.json` and `examples/report_vision.html`. The first flagged step was 3. Offline tests pass. No `.env` file is tracked.

## Next step

Demo video and submission post.

## Known issues

The Phase 1 smoke script still uses json.loads on the raw reply, which failed when Gemma wrapped JSON in a markdown fence. The detector strips those fences before parsing.

## Last agent and date

Cursor Grok 4.7, 2026-10-26
