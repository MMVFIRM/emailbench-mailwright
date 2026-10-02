# Gate 21 results (LRPE v0.7 vs control; Claude Sonnet 5.5 as model under test and judge)
Preregistered in results/gate21_prereg/ (commit before any run). 20 held-out Harvey LAB tasks (analyze-/assess-/compare-; no unused research-named tasks exist). 40 runs, 4 blind judges x 5 groups, merged.

**Outcome: PASS = false** (preregistered +5.0 pt criterion-pass gain missed: observed +3.6 pts, 95% bootstrap CI [+1.2, +6.6]). STRONG_EVIDENCE (CI lower bound > 0) = true. Task wins/losses: 13/2 (5 ties). All other preregistered rules passed (win>=loss, pure-subset non-inferior, omission cap, central, hallucination, citation, budget, word cap). The all-pass rule was replaced pre-run by task_wins_ge_losses because task all-pass was degenerate (0 for both arms) in Gate 20.

Sensitivity (post hoc, not part of the gate): dropping H10 (largest gain, +25.8 pts) gives +2.4 pts, CI [+0.8, +4.1]; leave-one-task-out range +2.4 to +4.1.

Notes:
- Two v0.7 runs (H14, H15) were labelled `blocked` by the model because external fetches were denied, but contain substantive memos; judged as written. Slot 023 (H15) was retried once after a first blocked attempt (retry_log/). 
- Waves were interrupted by account usage limits; failed attempts produced no outputs and were relaunched unchanged.
- Run-integrity check (answer concerns own task docs) found no cross-run contamination.
- Output files from the scorer were named gate20_* internally; renamed to gate21_* here.
- Same-model judge; pilot of 20 tasks; control used more evidence actions on average (23.4 vs 15.2).
