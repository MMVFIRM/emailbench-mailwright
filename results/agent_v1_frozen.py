"""Mailwright: a plan -> act -> verify agent framework for typed email/productivity APIs.

Every component can be switched off for ablations:
  clock      inject the environment clock ("now") so relative dates resolve correctly
  grounding  preflight reads (identity, folders, to-do lists, labels) injected as context with their ids
  manual     operating manual: API semantics, scope defaults, write policies, capability honesty
  autopage   tool wrapper that transparently fetches every page of list results
  compact    compact, lossless-for-task result rendering (so large lists fit in context)
  plan       requirement checklist extracted before acting
  verify     independent completion check after the executor stops; gaps are fed back
The executor gets the same 46 tools and the same 15-iteration budget as the paper baseline.
"""
from __future__ import annotations

import json
import re
import time

from emailbench.tools import call_tool, tool_schemas

MANUAL = """## Operating rules
Scope
- "My emails" / "my inbox" means the Inbox folder unless the user says otherwise. "Emails I sent" means Sent Items. Never move or modify items in Sent Items unless explicitly asked.
- Automated/system senders are non-human accounts (e.g. names or addresses containing system, alerts, tickets/ticketing, platform, no-reply, notifications). Identify them by listing distinct senders, not by keyword search.
- Relative dates ("today", "tomorrow", "this week", "last 3 days", "older than 7 days") are computed from the current time given below. A week runs Monday-Sunday. All times are UTC unless the user says otherwise; always state times with "UTC".

Retrieval
- messages_list returns every matching message (paging is automatic); use OData filters, e.g. isRead eq false, importance eq 'high', from/emailAddress/address eq 'x@y.com', receivedDateTime ge 2001-10-08T10:00:00Z, hasAttachments eq true, flag/flagStatus eq 'flagged', categories/any(c:c eq 'Label'). Pass folderId (e.g. 'inbox') to scope.
- List results only include a body preview; call messages_get when the answer depends on body content (numbers, dates, requests).
- contacts_search matches names/emails/company/department/title only; to match other fields (phone numbers, etc.) use contacts_list and inspect.
- For counting, grouping, percentages or "most/least" questions, retrieve the complete set first, then compute carefully; show the counts you used.

Actions
- The user has already authorized the actions they asked for: perform them directly. Do not ask for confirmation and do not stop halfway.
- To answer, reply or forward regarding a specific email, use messages_reply / messages_replyAll / messages_forward on that message id (not messages_send).
- Resolve people and senders to their exact email addresses (from messages or contacts) before using them as recipients, attendees or filter criteria.
- Use ids returned by earlier calls (folder ids from folders_create, list ids from todo_lists, etc.). Use messages_batchMove for several messages.
- Patches REPLACE list fields: when adding attendees or categories, send the full list (existing + new).
- There is no contact-update tool: to change a contact, create the corrected contact (keep its other fields) and delete the old one.
- Datetimes are ISO 8601 UTC like 2001-10-16T14:00:00. All-day events: start at 00:00 of the day, end at 00:00 of the next day, isAllDay=true.
- When steps of a multi-step request overlap, apply them in the order given; an item handled by an earlier step is not touched by later steps. Honor every exclusion.
- Do not repeat an action that already succeeded.

Capabilities
- Tools exist for mail, folders, inbox filters, calendar, contacts, to-do lists, mailbox settings and the current user. There are NO tools for boards/planner/kanban, contact groups or the organization directory. If a request needs one of those, say plainly that it is not available; never substitute a different object (e.g. do not create a to-do task instead of a board card) unless the user asked for that. Still complete every other part of the request.

Final answer
- Answer every part of the request with specific data (names, subjects, counts, dates/times in UTC, percentages to one decimal). Use a table or list for multiple items.
- For actions, report exactly what was done (counts per destination, created items, recipients). Never claim an action you did not perform, and never invent data."""

PLAN_PROMPT = """You turn an email/calendar assistant request into a precise checklist before any tools are used.
Current time: {now} (UTC).
Return JSON: {{"requirements": ["..."], "report": ["what the final answer must state"], "constraints": ["ordering, exclusions, scope limits"], "unavailable": ["parts needing boards/planner, contact groups or directory, if any"]}}.
Each requirement must be atomic and checkable (one action or one fact to report). Resolve relative dates to absolute UTC dates. Do not invent facts about the mailbox."""

VERIFY_PROMPT = """You are a strict completion auditor for an email/calendar assistant.
Given the user request, a requirement checklist, the full log of tool calls with results, and the assistant's final answer, decide whether the request is fully and correctly done.
Check: every requested action actually succeeded in the log (right target ids, right parameters, right order, exclusions honored); every question is answered with data supported by tool results; nothing was fabricated; no unrequested side effects; the final answer reports what was done.
Current time: {now} (UTC).
Return JSON: {{"complete": true|false, "gaps": ["specific missing/incorrect item and how to fix it"], "answer_fixes": ["problems in the final answer text"]}}.
Only list real, specific gaps. If the only problems are in the answer text, set complete=false and list them under answer_fixes."""

MSG_KEEP = ("id", "subject", "receivedDateTime", "isRead", "importance", "hasAttachments", "conversationId", "categories")


class FrameworkAgent:
    name = "framework"

    def __init__(self, llm, clock=True, grounding=True, manual=True, autopage=True, compact=True, plan=True,
                 verify=True, max_iterations=15, max_verify_rounds=2, max_result_chars=24000, verifier_llm=None):
        self.llm, self.vllm = llm, verifier_llm or llm
        self.opt = dict(clock=clock, grounding=grounding, manual=manual, autopage=autopage, compact=compact, plan=plan, verify=verify)
        self.max_iter, self.max_verify, self.max_chars = max_iterations, max_verify_rounds, max_result_chars

    # ------------------------------------------------------------------ tool layer
    def _folder_names(self, api):
        return {f["id"]: f["displayName"] for f in api.s["folders"]}

    def _compact_msg(self, m, fnames):
        d = {k: m[k] for k in MSG_KEEP if k in m}
        fe = m["from"]["emailAddress"]
        d["from"] = f"{fe.get('name', '')} <{fe['address']}>"
        d["to"] = [r["emailAddress"]["address"] for r in m.get("toRecipients", [])]
        if m.get("ccRecipients"):
            d["cc"] = [r["emailAddress"]["address"] for r in m["ccRecipients"]]
        d["folder"] = fnames.get(m.get("parentFolderId"), m.get("parentFolderId"))
        if m.get("flag", {}).get("flagStatus") == "flagged":
            d["flagged"] = True
        if "bodyPreview" in m:
            d["preview"] = m["bodyPreview"]
        if "body" in m:
            d["body"] = m["body"]
            d["attachments"] = [a["name"] for a in m.get("attachments", [])]
        if not d.get("categories"):
            d.pop("categories", None)
        return d

    def _exec(self, api, name, args):
        """Returns (text_for_model, ok, n_api_calls)."""
        n = 1
        if isinstance(args, str):
            try:
                args = json.loads(args or "{}")
            except json.JSONDecodeError:
                pass
        if self.opt["autopage"] and isinstance(args, dict):
            if name == "messages_list":
                args = dict(args)
                args["top"] = 100
                args.setdefault("skip", 0)
                txt, ok, raw = call_tool(api, name, args, 10 ** 9)
                while ok and raw.get("nextSkip") is not None and len(raw["value"]) < 500:
                    args["skip"] = raw["nextSkip"]
                    _, ok2, more = call_tool(api, name, args, 10 ** 9)
                    n += 1
                    if not ok2:
                        break
                    raw["value"].extend(more["value"])
                    raw["nextSkip"] = more.get("nextSkip")
                raw.pop("nextSkip", None)
                return self._render(api, name, raw, ok), ok, n
            if name in ("calendar_list", "messages_search", "contacts_list"):
                args = dict(args)
                args["top"] = 100
        txt, ok, raw = call_tool(api, name, args, 10 ** 9)
        return self._render(api, name, raw, ok), ok, n

    def _render(self, api, name, raw, ok):
        if ok and self.opt["compact"] and isinstance(raw, dict):
            fn = self._folder_names(api)
            if name in ("messages_list", "messages_search") and "value" in raw:
                raw = dict(raw, value=[self._compact_msg(m, fn) for m in raw["value"]])
            elif name == "messages_get":
                raw = self._compact_msg(raw, fn)
            elif name in ("calendar_list", "calendar_get"):
                evs = raw.get("value", [raw]) if "value" in raw else [raw]
                out = []
                for e in evs:
                    out.append(dict(id=e["id"], subject=e["subject"], start=e["start"]["dateTime"], end=e["end"]["dateTime"],
                                    isAllDay=e["isAllDay"], location=e["location"]["displayName"],
                                    organizer=e["organizer"]["emailAddress"]["address"],
                                    attendees=[f"{a['emailAddress']['address']} ({a['status']['response']})" for a in e["attendees"]],
                                    myResponse=e["responseStatus"]["response"], body=e.get("body", "")))
                raw = dict(value=out, totalCount=raw.get("totalCount", len(out))) if "value" in raw else out[0]
        txt = json.dumps(raw, default=str, separators=(",", ":") if self.opt["compact"] else (", ", ": "))
        if len(txt) > self.max_chars:
            txt = txt[:self.max_chars] + "...[truncated: narrow the query with a filter]"
        return txt

    # ------------------------------------------------------------------ context
    def _now(self, api):
        return api.s["reference_time"]

    def _grounding(self, api):
        me = api.getCurrentUser()
        folders = api.folders_list()["value"]
        lists = api.todo_lists()["value"]
        labels = api.settings_getLabels()["value"]
        fl = "\n".join(f"  - {f['displayName']} (id {f['id']}, parent {f.get('parentFolderId') or '-'}, {f['totalItemCount']} items, {f['unreadItemCount']} unread)" for f in folders)
        tl = "\n".join(f"  - {l['displayName']} (id {l['id']})" for l in lists)
        return (f"## Mailbox context (live)\nUser: {me['displayName']} <{me['mail']}>, {me['jobTitle']}, {me['department']}.\n"
                f"Folders:\n{fl}\nTo-do lists:\n{tl}\nCategory labels: {', '.join(l['displayName'] for l in labels)}"), 4

    def _system(self, api, grounding_text):
        parts = ["You are an executive assistant operating the user's mailbox, calendar, contacts, to-do lists and settings through tools. You complete requests end to end."]
        if self.opt["clock"]:
            now = self._now(api)
            dow = time.strftime("%A", time.strptime(now[:10], "%Y-%m-%d"))
            parts.append(f"Current time: {now} ({dow}), UTC.")
        if grounding_text:
            parts.append(grounding_text)
        if self.opt["manual"]:
            parts.append(MANUAL)
        else:
            parts.append("Use the tools to gather data or perform actions, then give a clear, complete answer with specific data. Never make up information.")
        return "\n\n".join(parts)

    def _json_call(self, llm, prompt, content):
        try:
            _, txt, _ = llm.respond(prompt, [dict(role="user", content=content)], max_output_tokens=2048, json_mode=True)
            m = re.search(r"\{.*\}", txt, re.S)
            return json.loads(m.group(0)) if m else {}
        except Exception:
            return {}

    # ------------------------------------------------------------------ main loop
    def run(self, query, api):
        t0 = time.time()
        now = self._now(api) if self.opt["clock"] else "unknown"
        gtext, pre_calls = self._grounding(api) if self.opt["grounding"] else ("", 0)
        system = self._system(api, gtext)
        plan = None
        if self.opt["plan"]:
            plan = self._json_call(self.llm, PLAN_PROMPT.format(now=now), query)
        user = query
        if plan:
            user += "\n\n[Checklist prepared for this request - satisfy every item]\n" + json.dumps(plan, indent=1)
        items = [dict(role="user", content=user)]
        tools = tool_schemas()
        trace, api_calls, answer, it, verify_rounds, verdicts = [], pre_calls, None, 0, 0, []
        while it < self.max_iter:
            it += 1
            out, text, calls = self.llm.respond(system, items, tools=tools)
            items.extend(out)
            if calls:
                for c in calls:
                    try:
                        args = json.loads(c.get("arguments") or "{}")
                    except Exception:
                        args = c.get("arguments")
                    res, ok, n = self._exec(api, c["name"], args)
                    api_calls += n
                    trace.append(dict(iteration=it, name=c["name"], args=args, result=res, ok=ok))
                    items.append(dict(type="function_call_output", call_id=c["call_id"], output=res))
                continue
            answer = text
            if not self.opt["verify"] or verify_rounds >= self.max_verify or it >= self.max_iter:
                break
            verify_rounds += 1
            v = self._verify(query, plan, trace, answer, now)
            verdicts.append(v)
            if v.get("complete", True) or not (v.get("gaps") or v.get("answer_fixes")):
                break
            fb = "An independent check of your work found problems:\n" + "\n".join(f"- {g}" for g in (v.get("gaps") or []) + (v.get("answer_fixes") or []))
            fb += "\nIf a point is valid, fix it now (do not redo actions that already succeeded). If a point is wrong, ignore it. Then give the complete final answer again."
            items.append(dict(role="user", content=fb))
            answer = None
        if answer is None:
            answer = "[max iterations reached]"
        return dict(answer=answer, trace=trace, iterations=it, latency=time.time() - t0,
                    extra=dict(api_calls=api_calls, plan=plan, verdicts=verdicts, verify_rounds=verify_rounds))

    def _verify(self, query, plan, trace, answer, now):
        log = "\n".join(f"{i+1}. {t['name']}({json.dumps(t['args'], default=str)[:400]}) -> {'OK' if t['ok'] else 'ERROR'} {t['result'][:900]}"
                        for i, t in enumerate(trace)) or "(no tool calls)"
        content = (f"## Request\n{query}\n\n## Checklist\n{json.dumps(plan, indent=1) if plan else '(none)'}\n\n## Tool log\n{log}\n\n"
                   f"## Final answer\n{answer}")
        return self._json_call(self.vllm, VERIFY_PROMPT.format(now=now), content)
