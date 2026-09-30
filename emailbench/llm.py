"""Thin OpenAI Responses-API client with retries, usage accounting and a mock for offline tests."""
from __future__ import annotations

import json
import os
import random
import re
import threading
import time
from dataclasses import dataclass, field


def load_env(path=".env"):
    for p in (path, os.path.join(os.path.dirname(__file__), "..", ".env")):
        if os.path.exists(p):
            for line in open(p):
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v)


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    calls: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, u):
        if u is None:
            return
        with self.lock:
            self.calls += 1
            self.input_tokens += getattr(u, "input_tokens", 0) or 0
            self.output_tokens += getattr(u, "output_tokens", 0) or 0
            d = getattr(u, "output_tokens_details", None)
            self.reasoning_tokens += (getattr(d, "reasoning_tokens", 0) or 0) if d else 0

    def as_dict(self):
        return dict(calls=self.calls, input_tokens=self.input_tokens, output_tokens=self.output_tokens,
                    reasoning_tokens=self.reasoning_tokens)


class LLM:
    """Responses API wrapper. `respond` returns (output_items, text, function_calls)."""

    def __init__(self, model, reasoning_effort=None, max_output_tokens=4096, timeout=180):
        load_env()
        from openai import OpenAI
        self.client = OpenAI(timeout=timeout, max_retries=0)
        self.model, self.effort, self.max_out = model, reasoning_effort, max_output_tokens
        self.usage = Usage()

    def respond(self, instructions, input_items, tools=None, max_output_tokens=None, json_mode=False):
        kw = dict(model=self.model, instructions=instructions, input=input_items, store=False,
                  max_output_tokens=max_output_tokens or self.max_out)
        if tools:
            kw["tools"] = tools
        if self.effort:
            kw["reasoning"] = {"effort": self.effort}
            kw["include"] = ["reasoning.encrypted_content"]
        if json_mode:
            kw["text"] = {"format": {"type": "json_object"}}
        last = None
        for attempt in range(25):
            try:
                r = self.client.responses.create(**kw)
                self.usage.add(r.usage)
                items = [o.model_dump(exclude_none=True) for o in r.output]
                for it in items:  # strip SDK-only keys that the API rejects on replay
                    for k in ("async_", "caller", "namespace", "parsed_arguments"):
                        it.pop(k, None)
                calls = [it for it in items if it.get("type") == "function_call"]
                return items, (r.output_text or ""), calls
            except Exception as e:  # rate limits / transient
                last = e
                msg = str(e)
                is_rate = "429" in msg or "rate limit" in msg.lower()
                if not is_rate and ("400" in msg or "invalid_request" in msg):
                    raise
                m = re.search(r"try again in ([0-9.]+)(ms|s)", msg)
                wait = (float(m.group(1)) / (1000 if m.group(2) == "ms" else 1)) if m else min(30, 2 ** min(attempt, 5))
                time.sleep(wait + 1.0 + random.random() * 3)
        raise last


class MockLLM:
    """Deterministic scripted LLM for offline tests: `script` is a list of responses; each is either
    a string (final text) or a list of (tool_name, args) calls."""

    def __init__(self, script):
        self.script, self.i, self.usage = list(script), 0, Usage()
        self.model = "mock"

    def respond(self, instructions, input_items, tools=None, max_output_tokens=None, json_mode=False):
        step = self.script[self.i] if self.i < len(self.script) else "done"
        self.i += 1
        if callable(step):
            step = step(instructions, input_items)
        if isinstance(step, str):
            return [dict(type="message", role="assistant", content=[dict(type="output_text", text=step)])], step, []
        items = []
        for j, (name, args) in enumerate(step):
            items.append(dict(type="function_call", name=name, arguments=json.dumps(args), call_id=f"c{self.i}_{j}"))
        return items, "", items
