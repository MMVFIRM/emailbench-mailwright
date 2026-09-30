"""Paper baseline: ReAct-style tool-calling loop with the Appendix M system prompt."""
from __future__ import annotations

import json
import time

from .tools import call_tool, tool_schemas

PAPER_SYSTEM_PROMPT = """You are an AI assistant that manages Microsoft Outlook. You have access to tools for managing emails, calendar, contacts, folders, rules, todo lists, and settings.

When the user asks you to do something:
1. Think about which tools you need to call
2. Call the appropriate tools to gather data or perform actions
3. Provide a clear, complete answer based on the tool results

Guidelines:
- For read queries: call the relevant list/search/get tools, then summarize the results clearly
- For write actions: call the appropriate create/update/delete/send tools
- For multi-step tasks: break them down and execute each step
- Always provide specific data (counts, names, dates) from tool results -- never make up information
- When listing items, include key details (subjects, senders, dates, etc.)"""

MAX_ITER_SENTINEL = "[max iterations reached]"


class BaselineAgent:
    name = "baseline"

    def __init__(self, llm, max_iterations=15, max_result_chars=8000):
        self.llm, self.max_iter, self.max_chars = llm, max_iterations, max_result_chars

    def run(self, query, api):
        t0 = time.time()
        tools = tool_schemas()
        items = [dict(role="user", content=query)]
        trace, answer, it = [], None, 0
        for it in range(1, self.max_iter + 1):
            out, text, calls = self.llm.respond(PAPER_SYSTEM_PROMPT, items, tools=tools)
            items.extend(out)
            if not calls:
                answer = text
                break
            for c in calls:
                res, ok, _ = call_tool(api, c["name"], c.get("arguments") or "{}", self.max_chars)
                try:
                    args = json.loads(c.get("arguments") or "{}")
                except Exception:
                    args = c.get("arguments")
                trace.append(dict(iteration=it, name=c["name"], args=args, result=res, ok=ok))
                items.append(dict(type="function_call_output", call_id=c["call_id"], output=res))
        if answer is None:
            answer = MAX_ITER_SENTINEL
        return dict(answer=answer, trace=trace, iterations=it, latency=time.time() - t0)
