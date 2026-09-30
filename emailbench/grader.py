"""Hybrid grader: static assertions + LLM-judge rubrics (paper Section 3.3, Appendix P)."""
from __future__ import annotations

import json
import re

JUDGE_SYSTEM = """You are an expert evaluator for an AI email assistant benchmark.
You will be given:
1. The user's original query
2. The agent's final answer
3. A list of tool calls the agent made
4. A rubric describing what to check

Score the agent's answer on a scale of 0.0 to 1.0:
- 1.0 = fully satisfies the rubric
- 0.5 = partially satisfies
- 0.0 = completely fails

Respond with ONLY a JSON object:
{"score": <number>, "reason": "<brief explanation>"}"""


def abbreviate_trace(trace, arg_chars=100, res_chars=200):
    lines = []
    for t in trace:
        a = json.dumps(t["args"], default=str)[:arg_chars]
        r = (t["result"] or "")[:res_chars]
        lines.append(f"  {t['name']}({a}) -> {r}")
    return "\n".join(lines) if lines else "  (none)"


def judge_prompt(query, answer, trace, rubric):
    return (f"## Query\n{query}\n\n## Agent's Answer\n{answer}\n\n## Tool Calls Made\n{abbreviate_trace(trace)}\n"
            f"  (arguments: 100 chars; result: 200 chars)\n\n## Rubric to evaluate\n**{rubric.dimension}**: {rubric.text}\n\n"
            "Respond with ONLY:\n{\"score\": <0.0-1.0>, \"reason\": \"...\"}")


def parse_judge(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return 0.0, "unparseable judge response"
    try:
        d = json.loads(m.group(0))
        return max(0.0, min(1.0, float(d.get("score", 0)))), str(d.get("reason", ""))
    except Exception:
        return 0.0, "unparseable judge response"


def grade(scenario, snapshot, answer, trace, judge=None):
    static = []
    for a in scenario.static:
        try:
            ok = bool(a.fn(snapshot, answer or ""))
        except Exception as e:
            ok = False
        static.append(dict(kind=a.kind, desc=a.desc, passed=ok, critical=a.critical, weight=a.weight))
    llm = []
    for r in scenario.rubrics:
        if judge is None:
            llm.append(dict(dimension=r.dimension, text=r.text, score=None, reason="judge disabled", critical=r.critical))
            continue
        try:
            _, txt, _ = judge.respond(JUDGE_SYSTEM, [dict(role="user", content=judge_prompt(scenario.query, answer, trace, r))],
                                      max_output_tokens=2048)
            sc, why = parse_judge(txt)
        except Exception as e:
            sc, why = 0.0, f"judge error: {e}"
        llm.append(dict(dimension=r.dimension, text=r.text, score=sc, reason=why, critical=r.critical, weight=r.weight))

    s_static = (sum(x["weight"] * x["passed"] for x in static) / sum(x["weight"] for x in static)) if static else None
    scored = [x for x in llm if x["score"] is not None]
    s_llm = (sum(x["weight"] * x["score"] for x in scored) / sum(x["weight"] for x in scored)) if scored else None
    if s_static is not None and s_llm is not None:
        score = 0.5 * s_static + 0.5 * s_llm
    else:
        score = s_static if s_static is not None else (s_llm or 0.0)
    crit_ok = all(x["passed"] for x in static if x["critical"]) and all(x["score"] >= 0.5 for x in scored if x["critical"])
    return dict(score=score, s_static=s_static, s_llm=s_llm, critical_ok=crit_ok, passed=bool(score >= 0.5 and crit_ok),
                static=static, llm=llm)
