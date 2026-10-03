# Gate 22 - LRPE v0.8 vs control, fresh held-out Harvey LAB tasks (Claude Sonnet 5.5)

Model under test and blind judges: Claude Sonnet 5.5 (subagents). 20 unseen tasks, 40 runs, 4 condition-blind judges. Preregistered in `results/gate22_prereg/` before any run.

## Result: PASS = false, STRONG_EVIDENCE = false
| metric | control | v0.8 | paired delta (95% CI) |
|---|---|---|---|
| criterion pass (macro) | 90.0% | 90.9% | +0.9 pts [-1.6, +2.9] (threshold +5.0) |
| all-pass | 10% | 5% | -5 pts |
| task wins/losses/ties | | | 10 / 6 / 4 |
| tasks with omission failure | 90% | 95% | +1 task (cap 1: ok) |
| central correctness | 100% | 100% | 0 |
| unsafe hallucination | 0 | 0 | 0 |
| citation precision | 1.00 | 1.00 | 0 |
| word-cap compliance | 90% | 100% | - |

Pure-research stratum (n=14): +2.0 pts [+0.4, +3.7]. Stress/reconciliation (n=6): -1.9 pts. Largest loss: H15 (-16.3 pts); largest wins H13 (+8.2), H17 (+7.5).
Failing rules: criterion_pass_gain; word_cap_compliance (two *control* runs over 2000 words, 2213 and 2801, kept as submitted; v0.8 had none). All other preregistered rules pass.

## Honest reading
- Control scored 90.0% here versus 85.5% on Gate 21's tasks, so this batch left less headroom (selection was contract-markup heavy). The v0.7 +3.6 pt gain did not replicate for v0.8 (+0.9) on fresh tasks.
- Failures remain ~all final-output omissions (17 vs 18 tasks), consistent with the word-cap diagnosis; v0.8 used more of the cap (mean 1958 vs 1876 words) but did not convert that into more rubric hits.
- Run integrity: every answer opens with its own task's header; no Gate-20-style contamination found. Judge validation: VALID, 20/20 groups.
- 6 runs were relaunched unchanged after account session-limit 429s killed them (no outputs lost).
