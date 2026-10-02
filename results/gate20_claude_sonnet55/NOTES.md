# Gate 20 run notes (Claude Sonnet 5.5 as model under test and judge)
- 40 runs (20 Harvey LAB tasks x control / frozen LRPE-PCR), fresh subagents. Harvey LAB pinned commit f93ae2ac; task documents and sealed rubric criteria are NOT included in this repo.
- First pass: 35 answered; 5 runs ended without a usable answer (4 no file, 1 `blocked` stub) after the harness auto-mode classifier denied document reads (agents had read spill files outside the document dir). With user approval these 5 were re-run once in fresh contexts (one document per call, small outputs); the first-attempt stub is kept in `retry_log/`. All 40 final submissions are status `answered`.
- Word-cap violation kept as submitted: R80E90F81BB86 (2279 > 2000 words).
- Judging: 4 fresh judges, 5 groups each, merged into `judge_results.json` (validated). Judge is the same model family as the runner.
- Derived task all-pass is 0 for both arms (strict all-criteria-pass on ~50 criteria/task never occurs), so the all-pass endpoint is uninformative; criterion pass rate is the usable metric.
- PASS=false, STRONG_EVIDENCE=false.
