# Gate 19 run notes (Claude Sonnet 5.5 as model under test and as judge)
- 30 runs as fresh subagents, all valid; no word-cap or budget violations; no retries.
- Judge used the required `criterion_id` key (alias count 0); no edits to judge_results.json.
- Judge is the same model as the runner (the gate prefers a different family; none available here). Pilot: 5 questions x 3 repeats.
- PASS=false solely because of final_output_omission_noninferior (lrpe_pcr 3 groups vs v0.3 1; max extra allowed 1).
