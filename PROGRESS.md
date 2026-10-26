# Progress

## Phases

- [x] Phase 0: scaffold
- [x] Phase 1: gemma smoke test
- [x] Phase 2: models and scenario
- [x] Phase 3: detector
- [ ] Phase 4: cli and live run
- [ ] Phase 5: report and replay
- [ ] Phase 6: readme and ci
- [ ] Phase 7: github push and verification
- [ ] Phase 8: optional vision

## Current state

Phase 3 is done. The detector asks an LLM client whether each simulated step still follows the original objective. Page text stays inside untrusted tags. Invalid JSON is retried once. The flag rule marks drift, a score below 60, or any criterion that was not kept. Offline tests pass with a fake client. No `.env` file is tracked.

## Next step

Phase 4: cli and live run.

## Known issues

The Phase 1 smoke script still uses json.loads on the raw reply, which failed when Gemma wrapped JSON in a markdown fence. The detector strips those fences before parsing.

## Last agent and date

Cursor Grok 4.7, 2026-10-26
