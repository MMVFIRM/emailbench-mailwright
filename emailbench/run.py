"""Benchmark runner.

python -m emailbench.run --agent baseline --model gpt-6-luna --split dev --workers 8 --out results/x
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .api import EmailBenchAPI
from .grader import grade
from .llm import LLM, load_env
from .scenarios import get


def make_agent(kind, model, effort, **kw):
    llm = LLM(model, reasoning_effort=effort)
    if kind == "baseline":
        from .baseline import BaselineAgent
        return BaselineAgent(llm), llm
    if kind.startswith("framework"):
        from framework.agent import FrameworkAgent
        return FrameworkAgent(llm, **kw), llm
    raise ValueError(kind)


def run_one(sc, kind, model, effort, judge_model, judge_effort, agent_kw):
    agent, llm = make_agent(kind, model, effort, **agent_kw)
    judge = LLM(judge_model, reasoning_effort=judge_effort, max_output_tokens=2048) if judge_model else None
    api = EmailBenchAPI()
    t0 = time.time()
    try:
        out = agent.run(sc.query, api)
        err = None
    except Exception as e:
        out = dict(answer="", trace=[], iterations=0, latency=time.time() - t0)
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}"
    g = grade(sc, api.snapshot(), out["answer"], out["trace"], judge=judge)
    if err is None and any(x["reason"].startswith("judge error") for x in g["llm"]):
        err = "judge error (rerun with --resume)"
    return dict(id=sc.id, category=sc.category, difficulty=sc.difficulty, split=sc.split, domains=sc.domains,
                query=sc.query, answer=out["answer"], trace=out["trace"], iterations=out.get("iterations"),
                latency=out.get("latency"), calls=len(out["trace"]), call_ok=sum(t["ok"] for t in out["trace"]),
                usage=llm.usage.as_dict(), judge_usage=judge.usage.as_dict() if judge else None, error=err,
                extra=out.get("extra"), **g)


def summarize(recs):
    n = len(recs)
    by = defaultdict(list)
    for r in recs:
        by[r["category"]].append(r)
    tot_in = sum(r["usage"]["input_tokens"] for r in recs)
    tot_out = sum(r["usage"]["output_tokens"] for r in recs)
    return dict(
        n=n, passed=sum(r["passed"] for r in recs), pass_rate=round(100 * sum(r["passed"] for r in recs) / max(n, 1), 1),
        mean_score=round(sum(r["score"] for r in recs) / max(n, 1), 3),
        calls=round(sum(r["calls"] for r in recs) / max(n, 1), 2),
        call_ok=round(100 * sum(r["call_ok"] for r in recs) / max(1, sum(r["calls"] for r in recs)), 1),
        latency=round(sum(r["latency"] or 0 for r in recs) / max(n, 1), 2),
        errors=sum(1 for r in recs if r["error"]), input_tokens=tot_in, output_tokens=tot_out,
        by_category={k: f"{sum(x['passed'] for x in v)}/{len(v)}" for k, v in sorted(by.items())},
    )


def main(argv=None):
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="baseline")
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--effort", default=None, help="reasoning effort (omit = model default)")
    ap.add_argument("--judge", default="gpt-6-luna")
    ap.add_argument("--judge-effort", default=None)
    ap.add_argument("--split", default=None)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--categories", nargs="*")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", required=True)
    ap.add_argument("--agent-kw", default="{}", help="JSON kwargs for the framework agent (ablations)")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args(argv)
    scs = get(split=a.split, ids=a.ids, categories=a.categories)
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "results.jsonl")
    done = {}
    if a.resume and os.path.exists(path):
        for line in open(path):
            r = json.loads(line)
            if not r.get("error"):
                done[r["id"]] = r
    todo = [s for s in scs if s.id not in done]
    kw = json.loads(a.agent_kw)
    json.dump(dict(vars(a), n=len(scs)), open(os.path.join(a.out, "config.json"), "w"), indent=2)
    recs = list(done.values())
    with open(path, "w") as f:
        for r in recs:
            f.write(json.dumps(r, default=str) + "\n")
        with ThreadPoolExecutor(a.workers) as ex:
            futs = {ex.submit(run_one, s, a.agent, a.model, a.effort, a.judge, a.judge_effort, kw): s for s in todo}
            for i, fu in enumerate(as_completed(futs), 1):
                r = fu.result()
                recs.append(r)
                f.write(json.dumps(r, default=str) + "\n")
                f.flush()
                print(f"[{i}/{len(todo)}] {r['id']:8s} {'PASS' if r['passed'] else 'fail'} score={r['score']:.2f} calls={r['calls']} {('ERR ' + r['error'][:80]) if r['error'] else ''}", flush=True)
    s = summarize(recs)
    json.dump(s, open(os.path.join(a.out, "summary.json"), "w"), indent=2)
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
