# EmailBench-R + Mailwright

A from-the-paper reconstruction of **EmailBench** (Singh et al., arXiv:2609.31906) and **Mailwright**, an agent framework built to beat plain tool-calling agents on it.

The official EmailBench artifacts weren't public when this was built, so this is a reconstruction. Its scores aren't directly comparable to the paper's numbers.

Released by MMV Firm (Memento Mori Vivere LLC).

## Results at a glance

| Setup (pre-registered numbers) | Held-out test (147 tasks) | Holdout-2 (85 fresh tasks) |
|---|---|---|
| **Mailwright v2 + gpt-6-luna** | 99.3% on all 150 (post hoc, see below) | **96.5%** |
| Mailwright v1 + gpt-6-luna (2 runs) | 98.3% | 95.3% |
| Plain gpt-6-luna (paper baseline loop) | 86.7% | 84.7% |
| Best other plain model (gpt-6-sol) | 91.2% | not run |

Most of the gain comes from giving the agent the current date and time: a clock-only variant reaches 96.6% on the held-out test. Details, ablations and caveats are below.

## Layout

```
emailbench/
  corpus.py        deterministic Kaminski corpus (Appendix O): 65 messages, 15 events, 15 contacts, 10 tasks, ...
  odata.py         OData $filter/$orderby evaluator used by messages_list / messages_count
  api.py           in-memory API with changelog, snapshot(), mutation logs (sentMessages, deletedIds, movedMessages)
  tools.py         the 46 evaluated tools (Table 34) as JSON-schema function tools + dispatcher
  scenario.py      scenario/assertion types; static checks: return-contains, state-check, exists, sent-message
  gt.py            ground-truth queries; expected answers are computed from the corpus, not hand-typed
  scen_*.py        206 scenarios in the paper's 16-category distribution (Table 2)
  grader.py        hybrid grader: s = 1/2 static + 1/2 LLM, pass iff s >= 0.5 and all critical checks pass;
                   judge prompt, trace truncation (100/200 chars) and parsing per Appendix P
  baseline.py      paper baseline: Appendix M system prompt, ReAct loop, 15 iterations, 8,000-char results
  llm.py           OpenAI Responses-API client (retries on 429) + MockLLM for offline tests
  run.py           parallel runner -> results/<run>/results.jsonl + summary.json
framework/agent.py Mailwright (plan -> act -> verify) with per-component ablation switches
tests/             oracle solvability (all 206), empty-agent-fails, offline framework-loop tests
```

## Quick start

```bash
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env
python -m pytest tests -q                                   # offline: 584 tests
python -m emailbench.run --agent baseline  --model gpt-6-luna --split test --out results/b
python -m emailbench.run --agent framework --model gpt-6-luna --split test --out results/f
python -m emailbench.run --agent framework --model gpt-6-luna --split test --out results/f_noverify \
       --agent-kw '{"verify": false}'
```

## Protocol

- **Dev/test split.** Split by a SHA-256 hash of the scenario id (56 dev / 150 test). The framework was tuned only on dev failures, then frozen (`results/provenance_sha256.txt`) before any test run.
- **Same budget.** Baseline and framework get the same 46 tools, the same 15-iteration executor budget, and the same judge (gpt-6-luna). The framework also makes one planner call and up to two verifier calls. These are reported as extra LLM calls and tokens.
- **Validity checks.** Every scenario ships a reference oracle that passes all of its static assertions. A do-nothing agent fails every scenario except MD-003, where the correct behavior is to do nothing and explain why.

## Deviations from the paper (deliberate)

| Paper | Here | Why |
|---|---|---|
| Message reads frozen to the seed corpus | Reads reflect mutations (`frozen_reads=True` restores the paper behavior) | Paper flags this as a validity defect |
| Calendar helper truncates fractional hours | Exact times | Paper flags this as a fixture defect |
| `return-contains` uses literal substrings despite regex patterns | Case-insensitive regex | Paper flags this as a grading defect |
| 30 scenarios name another persona | All scenarios target the Kaminski persona | Runner ignored `user_id` anyway |
| Board scenarios need tools the adapter lacks | Board scenarios test capability honesty: say it's unavailable, don't fabricate or substitute, and do the doable part | Makes the 10 scenarios gradeable |
| 43 scenarios are LLM-only | Every scenario has at least one static check (285 total) | Less judge dependence |
| Judge = GPT-5 (also an evaluated model) | Judge = gpt-6-luna (also the framework's model) | Same self-evaluation caveat. Static checks decide most outcomes |

## Mailwright components (all switchable via `--agent-kw`)

`clock`, `grounding`, `manual`, `autopage`, `compact`, `plan`, `verify`. These are described in the `framework/agent.py` docstring.

## Mailwright v2

Two switches, both on by default: `allday_dates` shows all-day events with inclusive dates, and `calendar_facts` treats the calendar entry as authoritative for event date, time, and location. Pass `--agent-kw '{"allday_dates":false,"calendar_facts":false}'` to reproduce v1 exactly (frozen copy: `results/agent_v1_frozen.py`).

v2 scored 56/56 on dev and 149/150 on test. Both fixes were derived from test failures, so the test score is post hoc. The one remaining failure (MW-014) is a judge false negative: the static check passed.

## Holdout-2 (fresh held-out test)

`python -m emailbench.run --split holdout2 ...` runs 85 new tasks (`emailbench/scen_holdout2.py`), written after v2 was frozen and hash-locked before any run (`results/provenance_holdout2_sha256.txt`).

Pre-registered results (GPT 6 Luna, one run each): v2 82/85 (96.5%), v1 81/85 (95.3%), plain baseline 72/85 (84.7%).

v1.1 fixes four grading defects found after the runs (MR02 and MP4 answer patterns, IC2 counting a move to Deleted Items as deletion, BO3 made non-critical because it is ill-posed). Applied to all runs alike, and excluding BO3: v2 84/84, v1 84/84, baseline 72/84.
