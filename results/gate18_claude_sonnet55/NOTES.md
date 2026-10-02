# Gate 18 run notes (Claude Sonnet 5.5 as model under test and as judge)
- 45 runs as fresh subagents. Run 033 was launched twice with a malformed prompt (no task given) and stopped immediately; it was then run correctly. No answer was discarded for legal quality.
- `judge_results.original.json` uses `id` for criterion ids; the scorer needs `criterion_id`. `judge_results.json` is identical except for that key rename (450 entries). Scoring the original gives spurious 0.0 issue recall / all-pass.
- Word-cap violations (kept as submitted): R64C0A8680CCA (1347), R831E69BD07E6 (1293), R1199CF705C3F (1336), all control arm P-001.
- Judge is the same model family as the runner; pilot of 5 questions x 3 repeats.
