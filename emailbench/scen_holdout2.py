"""Holdout-2 (v1.1): 85 new scenarios written after Mailwright v2 was frozen, before any agent was run on them.

Same mailbox, same tools, same grader.
v1.1 (post-run, applied to all agents equally): H2-MR02 and H2-MP4 answer patterns widened to accept correct
phrasings; H2-IC2 counts a move to Deleted Items as deletion; H2-BO3 email check made non-critical (ill-posed). Category counts are the paper's distribution scaled by ~0.41.
"""
from __future__ import annotations

from . import gt
from .scenario import (Scenario, ans, ans_not, attendee_addrs, event, ex, folder_by_name, in_folder, msg, new_events,
                       no_mutations, not_mutated, rub, sent, st, task, tasks_titled)
from .scen_ops import HONEST

AUTO = {"system@enrononline.com", "legal-tickets@enron.com", "alerts@gasbank.enron.com"}


def _resp(s, eid):
    e = event(s, eid)
    return e and e["responseStatus"]["response"]


def _moved_to(s, ids_, fname, parent=None):
    return all(in_folder(s, i, fname, parent) for i in ids_)


def _only_in(s, ids_, fname):
    f = folder_by_name(s, fname)
    return f is not None and {m["id"] for m in s["messages"] if m["parentFolderId"] == f["id"]} <= set(ids_)


def _mkmove(api, name, ids_):
    fid = api.folders_create(name)["id"]
    if ids_:
        api.messages_batchMove(ids_, fid)
    return fid


def holdout2():
    S = []
    add = S.append
    M = ["messages"]

    # ---------------------------------------------------------------- messages-read (16)
    col = [m for m in gt.inbox() if gt.sender(m).endswith("@enron.com") and gt.sender(m) not in AUTO]
    add(Scenario("H2-MR01", "messages-read", 2, M, "How many emails in my inbox came from Enron colleagues (enron.com addresses), not counting automated accounts?",
                 [ans(rf"\b{len(col)}\b")], [rub(f"{len(col)} inbox emails from human @enron.com senders (excludes legal-tickets@enron.com, alerts@gasbank.enron.com, EnronOnline and Dynegy).")],
                 oracle=lambda api: f"{len(col)}"))
    lu = max(gt.by_sender("lu"), key=lambda m: m["receivedDateTime"])
    add(Scenario("H2-MR02", "messages-read", 1, M, "What's the most recent email from Zimin Lu about, and when did it arrive?",
                 [ans(r"weather|heating.degree|HDD", r"(october|oct\.?) 15|2001-10-15|10/15|today")],
                 [rub(f"{lu['id']} '{lu['subject']}' at {lu['receivedDateTime']} (Oct 15, 04:00 UTC): v2 HDD pricing model, backtest error 7.4% -> 4.1%.")],
                 oracle=lambda api: f"{lu['subject']} on October 15 04:00 UTC"))
    wk = [m for m in gt.inbox() if m["receivedDateTime"][:10] in ("2001-10-13", "2001-10-14") and not m["isRead"]]
    add(Scenario("H2-MR03", "messages-read", 2, M, "How many unread emails did I get over the weekend (Saturday Oct 13 and Sunday Oct 14, UTC)?",
                 [ans(rf"\b{len(wk)}\b")], [rub(f"{len(wk)}: {', '.join(gt.ids(wk))}.")], oracle=lambda api: f"{len(wk)}"))
    cnt = gt.sender_counts()
    two = sorted(a for a, c in cnt.items() if c == 2)
    add(Scenario("H2-MR04", "messages-read", 2, M, "Which senders (including automated ones) have emailed me exactly twice?",
                 [ans(r"enrononline", r"legal", r"gasbank", r"rebecca|mark")], [rub("Exactly: " + ", ".join(gt.NAME[a] for a in two) + ".")],
                 oracle=lambda api: ", ".join(gt.NAME[a] for a in two)))
    add(Scenario("H2-MR05", "messages-read", 1, M, "What mean reversion speed did Stinson Gibner estimate for the gas storage model?",
                 [ans(r"2\.3")], [rub("2.3 per year (msg-002).")], oracle=lambda api: "2.3 per year"))
    hi = gt.high()
    add(Scenario("H2-MR06", "messages-read", 1, M, "How many of my inbox emails are marked high importance, and how many of those are still unread?",
                 [ans(rf"\b{len(hi)}\b", rf"\b{len(gt.unread(hi))}\b")], [rub(f"{len(hi)} high-importance, {len(gt.unread(hi))} unread.")],
                 oracle=lambda api: f"{len(hi)} high, {len(gt.unread(hi))} unread"))
    add(Scenario("H2-MR07", "messages-read", 1, M, "Find the email about bandwidth trading. Who sent it and what do they need from me?",
                 [ans(r"kitchen", r"pricing methodology|pricing")], [rub("Louise Kitchen (msg-031): launching bandwidth trading next month; wants research to provide a pricing methodology for bandwidth swaps.")],
                 oracle=lambda api: "Louise Kitchen needs a pricing methodology for bandwidth swaps"))
    pct = 100 * len(gt.unread()) / len(gt.inbox())
    add(Scenario("H2-MR08", "messages-read", 1, M, "What percentage of my inbox is unread? Give one decimal place.",
                 [ans(rf"{pct:.1f}\s?%|{int(pct)}\s?%")], [rub(f"{len(gt.unread())}/{len(gt.inbox())} = {pct:.1f}%.")], oracle=lambda api: f"{pct:.1f}%"))
    w72 = [m for m in gt.within_hours(72) if gt.sender(m) in ("kenneth.lay@enron.com", "jeff.skilling@enron.com")]
    add(Scenario("H2-MR09", "messages-read", 2, M, "Which emails have I received from Kenneth Lay or Jeff Skilling in the last 72 hours?",
                 [ans(r"board presentation", r"raptor hedge", r"headcount", r"all-employee", r"offsite", r"board meeting prep")],
                 [rub(f"{len(w72)} emails: " + "; ".join(f"{m['id']} {m['subject']}" for m in w72) + ". Excludes 'Re: Research group headcount' (74h ago) and older.", "completeness")],
                 oracle=lambda api: "; ".join(m["subject"] for m in w72)))
    add(Scenario("H2-MR10", "messages-read", 1, M, "Which of my sent emails had an attachment, and who received it?",
                 [ans(r"raptor valuation assumptions|raptor_assumptions", r"taylor")], [rub("Only msg-047 'Raptor valuation assumptions' to Mark Taylor with raptor_assumptions.xls.")],
                 oracle=lambda api: "Raptor valuation assumptions (raptor_assumptions.xls) to Mark Taylor"))
    beck = gt.by_sender("beck")
    old = min(beck, key=lambda m: m["receivedDateTime"])
    add(Scenario("H2-MR11", "messages-read", 2, M, "How many emails has Sally Beck sent me, and what is the oldest one about?",
                 [ans(rf"\b{len(beck)}\b|four", r"inventory|audit")], [rub(f"{len(beck)} emails; oldest {old['id']} '{old['subject']}': internal audit needs an inventory of pricing models by end of month.")],
                 oracle=lambda api: f"{len(beck)}; oldest: {old['subject']} (model inventory)"))
    add(Scenario("H2-MR12", "messages-read", 1, M, "What did Rebecca Mark ask for in her follow-up on the joint venture term sheet?",
                 [ans(r"valuation appendix", r"24")], [rub("msg-030: Dynegy board meets Oct 24; wants my comments on the valuation appendix before then.")],
                 oracle=lambda api: "Comments on the valuation appendix before October 24"))
    un = gt.unread()
    hu, nu = len([m for m in un if m["importance"] == "high"]), len([m for m in un if m["importance"] == "normal"])
    add(Scenario("H2-MR13", "messages-read", 2, M, "Group my unread inbox emails by importance level and count each group.",
                 [ans(rf"high\W+(\w+\W+){{0,3}}{hu}\b|{hu}\W+(\w+\W+){{0,3}}high", rf"normal\W+(\w+\W+){{0,3}}{nu}\b|{nu}\W+(\w+\W+){{0,3}}normal")],
                 [rub(f"High {hu}, normal {nu}, low 0 (total {len(un)}).")], oracle=lambda api: f"high: {hu}, normal: {nu}, low: 0"))
    rc = [m for m in gt.inbox() if "Research" in m["categories"]]
    add(Scenario("H2-MR14", "messages-read", 1, M, "Which emails in my inbox have the 'Research' category? List their subjects.",
                 [ans(r"Monte Carlo simulation parameters", r"Weather derivatives pricing model v2", r"Credit model calibration")],
                 [rub(f"{len(rc)}: " + "; ".join(f"{m['id']} {m['subject']}" for m in rc) + ".", "completeness")],
                 oracle=lambda api: "; ".join(m["subject"] for m in rc)))
    hum = {gt.sender(m) for m in gt.inbox() if gt.sender(m) not in AUTO}
    add(Scenario("H2-MR15", "messages-read", 2, M, "How many different people (not automated accounts) have emailed me, and who sent the most recent email?",
                 [ans(rf"\b{len(hum)}\b|twelve", r"skilling")], [rub(f"{len(hum)} distinct human senders; most recent is Jeff Skilling (msg-001, 2 hours ago).")],
                 oracle=lambda api: f"{len(hum)}; Jeff Skilling"))
    nov = [m for m in gt.inbox() if "november" in (m["subject"] + m["body"]).lower()]
    add(Scenario("H2-MR16", "messages-read", 2, M, "Which emails in my inbox mention November?",
                 [ans(r"EOL-88213|trade confirmation", r"california", r"offsite", r"fall planning")],
                 [rub(f"{len(nov)}: " + "; ".join(f"{m['id']} {m['subject']}" for m in nov) + ".", "completeness")],
                 oracle=lambda api: "; ".join(m["subject"] for m in nov)))

    # ---------------------------------------------------------------- orchestration (7)
    add(Scenario("H2-OR1", "orchestration", 3, ["messages", "settings", "calendar"], "Set my automatic reply for the Energy Risk Conference days naming Zimin Lu as my backup, and email Zimin to let him know he's covering.",
                 [st(lambda s: s["settings"]["vacationResponder"]["enabled"] and (s["settings"]["vacationResponder"]["startDateTime"] or "").startswith("2001-10-22") and (s["settings"]["vacationResponder"]["endDateTime"] or "")[:10] in ("2001-10-23", "2001-10-24") and "lu" in s["settings"]["vacationResponder"]["message"].lower(), "vacation Oct 22-23 naming Lu"),
                  sent(lambda m: "zimin.lu@enron.com" in m["to"], "email to Lu")],
                 [rub("Out-of-office Oct 22 through Oct 23 naming Zimin Lu; email sent to Lu.", "action-taken")],
                 oracle=lambda api: (api.settings_setVacationResponder(True, "Zimin Lu is covering.", "2001-10-22T00:00:00", "2001-10-24T00:00:00"), api.messages_send("Covering", "You're covering Oct 22-23.", ["zimin.lu@enron.com"]), "Done.")[2]))
    wea = [m["id"] for m in gt.inbox() if "weather" in (m["subject"] + m["body"]).lower()]
    add(Scenario("H2-OR2", "orchestration", 3, ["folders", "messages", "todo"], "Create a folder 'Weather', move every inbox email that mentions 'weather' into it, and add a task 'Review weather model v2' to my Research Items list due October 19.",
                 [st(lambda s: _moved_to(s, wea, "Weather") and _only_in(s, wea, "Weather"), f"{wea} moved"),
                  ex(lambda s: any((t["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-19") for t in tasks_titled(s, "weather model", list_name="Research Items")), "task")],
                 [rub(f"Moved {len(wea)} emails ({', '.join(wea)}), created the Research Items task due Oct 19.", "action-taken")],
                 oracle=lambda api: (_mkmove(api, "Weather", wea), api.todo_createTask("list-2", "Review weather model v2", dueDateTime="2001-10-19T17:00:00"), "Done.")[2]))
    add(Scenario("H2-OR3", "orchestration", 3, ["messages", "todo"], "For each email from Mark Taylor that mentions a deadline, create a task in my Project Raptor Backlog due on that deadline.",
                 [st(lambda s: len([t for t in s["todoTasks"] if t["listId"] == "list-3" and not t["id"].startswith("task-0") and (t["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-18")]) >= 2, "two new Raptor tasks due Oct 18")],
                 [rub("Two Taylor emails have deadlines: msg-022 (valuation memo for Andersen by Oct 18) and msg-035 (answers to 12 Andersen questions by Oct 18). Two tasks due Oct 18 in Project Raptor Backlog.", "action-taken")],
                 oracle=lambda api: (api.todo_createTask("list-3", "Valuation memo for Andersen", dueDateTime="2001-10-18T17:00:00"), api.todo_createTask("list-3", "Answer Andersen's 12 questions", dueDateTime="2001-10-18T17:00:00"), "Done.")[2]))
    add(Scenario("H2-OR4", "orchestration", 2, ["messages", "todo"], "Reply to Stinson Gibner's 'Re: Monte Carlo simulation parameters' email agreeing to keep 50,000 paths, and add a task 'Finalize Monte Carlo setup' to Research Items due October 17.",
                 [sent(lambda m: m["inReplyTo"] == "msg-017", "reply to msg-017"),
                  ex(lambda s: any((t["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-17") for t in tasks_titled(s, "monte carlo setup", list_name="Research Items")), "task")],
                 [rub("Reply to msg-017 agreeing to 50,000 paths; task created.", "action-taken")],
                 oracle=lambda api: (api.messages_reply("msg-017", "Agreed, keep 50,000 paths."), api.todo_createTask("list-2", "Finalize Monte Carlo setup", dueDateTime="2001-10-17T17:00:00"), "Done.")[2]))
    add(Scenario("H2-OR5", "orchestration", 3, ["calendar", "messages"], "Decline every meeting organized by someone from Dynegy, and email each of those organizers that Sally Beck will follow up.",
                 [st(lambda s: _resp(s, "evt-008") == "declined" and _resp(s, "evt-014") == "declined", "008 & 014 declined"),
                  sent(lambda m: "rebecca.mark@dynegy.com" in m["to"], "email Mark"), sent(lambda m: "tim.belden@dynegy.com" in m["to"], "email Belden"),
                  st(lambda s: all(_resp(s, e) != "declined" for e in ("evt-011", "evt-013")), "others untouched")],
                 [rub("Declined Dynegy Partnership Review (Rebecca Mark) and Dynegy Credit Review (Tim Belden); emailed both that Sally Beck will follow up.", "action-taken")],
                 oracle=lambda api: ([api.calendar_decline(e) for e in ("evt-008", "evt-014")], [api.messages_send("Follow-up", "Sally Beck will follow up.", [a]) for a in ("rebecca.mark@dynegy.com", "tim.belden@dynegy.com")], "Done.")[2]))
    rap = [m["id"] for m in gt.inbox() if m["conversationId"] == "conv-raptor"]
    add(Scenario("H2-OR6", "orchestration", 2, ["messages", "folders"], "Archive every email in the Raptor SPE conversation thread and flag the one from Jeff Skilling.",
                 [st(lambda s: all(msg(s, i)["parentFolderId"] == "folder-archive" for i in rap), f"{rap} archived"),
                  st(lambda s: msg(s, "msg-015")["flag"].get("flagStatus") == "flagged", "015 flagged")],
                 [rub(f"Archived the thread ({', '.join(rap)}); flagged msg-015.", "action-taken")],
                 oracle=lambda api: (api.messages_batchMove(rap, "archive"), api.messages_update("msg-015", {"flag": {"flagStatus": "flagged"}}), "Done.")[2]))
    lay = gt.by_sender("lay")
    add(Scenario("H2-OR7", "orchestration", 3, ["todo", "messages"], "Create a to-do list called 'Q4 Board' with one task per email from Kenneth Lay (use the email subject as the task title), then mark all of Lay's emails as read.",
                 [st(lambda s: all(tasks_titled(s, m["subject"][:14], list_name="Q4 Board") for m in lay), "task per Lay email"),
                  st(lambda s: all(msg(s, m["id"])["isRead"] for m in lay), "all read")],
                 [rub("List 'Q4 Board' with 3 tasks (All-employee meeting follow-up, Quarterly strategy offsite, Board meeting prep); msg-006/026/036 read.", "action-taken")],
                 oracle=lambda api: _or7(api, lay)))

    # ---------------------------------------------------------------- cross-domain (6)
    add(Scenario("H2-XD1", "cross-domain", 2, ["calendar", "messages"], "Which people organize meetings on my calendar but have never received an email from me?",
                 [ans(r"\bnone\b|no one|nobody|every organizer|all (of )?(the )?organizers"), st(no_mutations, "no changes")],
                 [rub("None: every other organizer (Skilling, Lavorato, Beck, Kean, Rebecca Mark, Kitchen, Taylor, Belden, Shapiro) appears as a recipient of at least one sent email.")],
                 oracle=lambda api: "None - every organizer has received an email from you."))
    add(Scenario("H2-XD2", "cross-domain", 2, ["calendar", "messages"], "Which attendees of the Project Raptor Deep Dive have emailed me about Raptor?",
                 [ans(r"taylor", r"skilling"), ans_not(r"gibner has emailed|gibner \(", critical=False)],
                 [rub("Mark Taylor (3 Raptor emails) and Jeff Skilling (1). Stinson Gibner attends but has sent no Raptor email.")],
                 oracle=lambda api: "Mark Taylor and Jeff Skilling"))
    add(Scenario("H2-XD3", "cross-domain", 2, ["calendar", "todo"], "How many calendar events and how many open to-do tasks do I have on October 16?",
                 [ans(r"\b3\b|three", r"\b2\b|two")], [rub("3 events (FERC Compliance Review, Dynegy Partnership Review, 1:1 with Kitchen); 2 open tasks due (Review VaR model backtest, Raptor hedge MTM recalculation).")],
                 oracle=lambda api: "3 events and 2 open tasks"))
    ppl = set()
    for e in gt.EVENTS:
        if "2001-10-15" <= e["start"]["dateTime"][:10] <= "2001-10-20":
            ppl |= set(gt.attendees(e)) | {e["organizer"]["emailAddress"]["address"]}
    senders = {gt.sender(m) for m in gt.inbox()}
    cts = {c["emailAddresses"][0]["address"] for c in gt.CONTACTS}
    xs = sorted(ppl & senders & cts)
    add(Scenario("H2-XD4", "cross-domain", 3, ["contacts", "messages", "calendar"], "Which of my contacts have both emailed me and are in at least one of my meetings between October 15 and October 20?",
                 [ans(*[rf"\b{gt.NAME[a].split()[-1]}\b" for a in xs])],
                 [rub(f"{len(xs)}: " + ", ".join(gt.NAME[a] for a in xs) + ". Not Kenneth Lay (no meeting).")],
                 oracle=lambda api: ", ".join(gt.NAME[a] for a in xs)))
    add(Scenario("H2-XD5", "cross-domain", 3, ["todo", "calendar"], "Between October 15 and October 26, do I have any open to-do tasks due on a day with no calendar events (all-day events count as events)?",
                 [ans(r"weather derivatives paper")], [rub("Only 'Weather derivatives paper draft' (due Oct 26; no events that day). Every other open task due in the window falls on a day with events (Oct 22 has the all-day conference).")],
                 oracle=lambda api: "Weather derivatives paper draft (Oct 26)"))
    add(Scenario("H2-XD6", "cross-domain", 2, ["calendar", "contacts"], "For each meeting on October 17, list the attendees and say whether each one is in my contacts.",
                 [ans(r"raptor deep dive", r"taylor", r"skilling", r"gibner")],
                 [rub("Oct 17: Focus Time (no attendees) and Project Raptor Deep Dive (Mark Taylor organizer, Jeff Skilling, Stinson Gibner) - all three are contacts.")],
                 oracle=lambda api: "Focus Time: none. Raptor Deep Dive: Taylor, Skilling, Gibner - all contacts"))

    # ---------------------------------------------------------------- messages-write (6)
    add(Scenario("H2-MW1", "messages-write", 1, M, "Reply to Zimin Lu's spread option question recommending the two-factor Monte Carlo approach.",
                 [sent(lambda m: m["inReplyTo"] == "msg-033" and "monte carlo" in m["body"].lower(), "reply to 033")], [rub("Reply to msg-033 recommending two-factor Monte Carlo.", "action-taken")],
                 oracle=lambda api: (api.messages_reply("msg-033", "Use the two-factor Monte Carlo."), "Replied.")[1]))
    add(Scenario("H2-MW2", "messages-write", 1, M, "Forward Tim Belden's credit exposure question to Sally Beck and ask her to pull the latest numbers.",
                 [sent(lambda m: m["kind"] == "forward" and m["inReplyTo"] == "msg-025" and "sally.beck@enron.com" in m["to"], "forward 025 to Beck")],
                 [rub("Forwarded msg-025 to Beck with the request.", "action-taken")],
                 oracle=lambda api: (api.messages_forward("msg-025", ["sally.beck@enron.com"], "Please pull the latest numbers."), "Forwarded.")[1]))
    bk = gt.ids(gt.by_sender("beck"))
    add(Scenario("H2-MW3", "messages-write", 1, M, "Mark every email from Sally Beck as read.",
                 [st(lambda s: all(msg(s, i)["isRead"] for i in bk), "all Beck read")], [rub(f"All {len(bk)} Beck emails read.", "action-taken")],
                 oracle=lambda api: ([api.messages_update(i, {"isRead": True}) for i in bk], "Done.")[1]))
    fl = [m["id"] for m in gt.MSGS if m["flag"]["flagStatus"] == "flagged"]
    add(Scenario("H2-MW4", "messages-write", 1, M, "Clear the flag on all of my flagged emails.",
                 [st(lambda s: all(msg(s, i)["flag"].get("flagStatus") != "flagged" for i in fl), "all unflagged")], [rub(f"Unflagged {', '.join(fl)}.", "action-taken")],
                 oracle=lambda api: ([api.messages_update(i, {"flag": {"flagStatus": "notFlagged"}}) for i in fl], "Done.")[1]))
    add(Scenario("H2-MW5", "messages-write", 1, M, "Email Richard Shapiro and Steven Kean with the subject 'California price caps' asking for a 15-minute call this week, and cc Tim Belden.",
                 [sent(lambda m: {"richard.shapiro@enron.com", "steven.kean@enron.com"} <= set(m["to"]) and "tim.belden@dynegy.com" in m["cc"] and "california price caps" in m["subject"].lower(), "email correct")],
                 [rub("Shapiro and Kean in To, Belden in Cc, subject 'California price caps', asks for a 15-minute call.", "action-taken")],
                 oracle=lambda api: (api.messages_send("California price caps", "Could we do a 15-minute call this week?", ["richard.shapiro@enron.com", "steven.kean@enron.com"], ["tim.belden@dynegy.com"]), "Sent.")[1]))
    add(Scenario("H2-MW6", "messages-write", 2, M, "Reply all to Rebecca Mark's follow-up on the term sheet saying my comments will arrive by October 23.",
                 [sent(lambda m: m["kind"] == "replyAll" and m["inReplyTo"] == "msg-030" and "tim.belden@dynegy.com" in m["to"] + m["cc"], "replyAll 030 incl. Belden")],
                 [rub("Reply-all to msg-030 (Mark + Belden) saying comments by Oct 23.", "action-taken")],
                 oracle=lambda api: (api.messages_replyAll("msg-030", "Comments will arrive by October 23."), "Done.")[1]))

    # ---------------------------------------------------------------- calendar-read (5)
    CAL = ["calendar"]
    add(Scenario("H2-CR1", "calendar-read", 2, CAL, "How many events do I have on Wednesday October 17, and how much total time do they take?",
                 [ans(r"\b2\b|two", r"\b5\b ?(hours|h)|five hours")], [rub("2 events: Focus Time 09:00-12:00 (3h) and Project Raptor Deep Dive 14:00-16:00 (2h); 5 hours total.")],
                 oracle=lambda api: "2 events, 5 hours"))
    add(Scenario("H2-CR2", "calendar-read", 2, CAL, "What's my first meeting tomorrow, and where is it?",
                 [ans(r"FERC Compliance", r"Dynegy Partnership", r"11:00|11 ?am")],
                 [rub("Oct 16 starts at 11:00 UTC with two overlapping meetings: FERC Compliance Review (EB 47C1) and Dynegy Partnership Review (Dynegy HQ / dial-in). Mentioning both is required.")],
                 oracle=lambda api: "At 11:00 UTC: FERC Compliance Review (EB 47C1) and Dynegy Partnership Review (Dynegy HQ / dial-in)"))
    add(Scenario("H2-CR3", "calendar-read", 1, CAL, "Which meetings have I tentatively accepted?",
                 [ans(r"gas volatility")], [rub("Only Gas Volatility Sync (Oct 15 17:00-17:45).")], oracle=lambda api: "Gas Volatility Sync"))
    bm = [e for e in gt.EVENTS if "2001-10-12" <= e["start"]["dateTime"][:10] <= "2001-10-20" and ("sally.beck@enron.com" in gt.attendees(e) or e["organizer"]["emailAddress"]["address"] == "sally.beck@enron.com")]
    add(Scenario("H2-CR4", "calendar-read", 2, CAL, "How many meetings between October 12 and October 20 include Sally Beck (as attendee or organizer)? Name them.",
                 [ans(rf"\b{len(bm)}\b|four", r"retrospective", r"risk committee", r"all-hands", r"credit review")],
                 [rub(f"{len(bm)}: " + ", ".join(e['subject'] for e in bm) + ".")], oracle=lambda api: f"{len(bm)}: " + ", ".join(e['subject'] for e in bm)))
    add(Scenario("H2-CR5", "calendar-read", 2, CAL, "What's the longest meeting on my calendar from October 15 to 19, not counting Focus Time?",
                 [ans(r"raptor deep dive")], [rub("Project Raptor Deep Dive, 2 hours (Oct 17 14:00-16:00).")], oracle=lambda api: "Project Raptor Deep Dive (2 hours)"))

    # ---------------------------------------------------------------- calendar-write (5)
    add(Scenario("H2-CW1", "calendar-write", 1, CAL, "Schedule 'Credit model validation' on October 19 from 10:00 to 11:30 UTC in EB 1972 with Stinson Gibner and Sally Beck.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-19T10:00:00Z" and e["end"]["dateTime"] == "2001-10-19T11:30:00Z" and {"stinson.gibner@enron.com", "sally.beck@enron.com"} <= attendee_addrs(e) and "1972" in e["location"]["displayName"] for e in new_events(s)), "event")],
                 [rub("Event created with time, location and attendees.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Credit model validation", "2001-10-19T10:00:00", "2001-10-19T11:30:00", "EB 1972", ["stinson.gibner@enron.com", "sally.beck@enron.com"]), "Done.")[1]))
    add(Scenario("H2-CW2", "calendar-write", 2, CAL, "Move today's Gas Volatility Sync 30 minutes earlier.",
                 [st(lambda s: event(s, "evt-006")["start"]["dateTime"] == "2001-10-15T16:30:00Z" and event(s, "evt-006")["end"]["dateTime"] == "2001-10-15T17:15:00Z", "16:30-17:15")],
                 [rub("evt-006 now 16:30-17:15 UTC (same 45-minute length).", "action-taken")],
                 oracle=lambda api: (api.calendar_update("evt-006", {"start": "2001-10-15T16:30:00", "end": "2001-10-15T17:15:00"}), "Moved.")[1]))
    add(Scenario("H2-CW3", "calendar-write", 1, CAL, "Rename my 'Focus Time' event to 'Focus: FERC analysis'.",
                 [st(lambda s: event(s, "evt-010")["subject"] == "Focus: FERC analysis", "renamed")], [rub("evt-010 renamed.", "action-taken")],
                 oracle=lambda api: (api.calendar_update("evt-010", {"subject": "Focus: FERC analysis"}), "Renamed.")[1]))
    add(Scenario("H2-CW4", "calendar-write", 2, CAL, "Remove Tim Belden from the Dynegy Partnership Review but keep everyone else on it.",
                 [st(lambda s: "tim.belden@dynegy.com" not in attendee_addrs(event(s, "evt-008")) and "louise.kitchen@enron.com" in attendee_addrs(event(s, "evt-008")), "Belden removed, Kitchen kept")],
                 [rub("evt-008 attendees: Rebecca Mark and Louise Kitchen remain; Belden removed.", "action-taken")],
                 oracle=lambda api: (api.calendar_update("evt-008", {"attendees": ["rebecca.mark@dynegy.com", "louise.kitchen@enron.com"]}), "Removed.")[1]))
    add(Scenario("H2-CW5", "calendar-write", 2, CAL, "Book a 45-minute 'Andersen follow-up' with Mark Taylor starting right when the Project Raptor Deep Dive ends.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-17T16:00:00Z" and e["end"]["dateTime"] == "2001-10-17T16:45:00Z" and "mark.taylor@enron.com" in attendee_addrs(e) for e in new_events(s)), "Oct 17 16:00-16:45")],
                 [rub("Oct 17 16:00-16:45 UTC with Taylor.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Andersen follow-up", "2001-10-17T16:00:00", "2001-10-17T16:45:00", attendees=["mark.taylor@enron.com"]), "Booked.")[1]))

    # ---------------------------------------------------------------- boards (4)
    for sid, d, text, extra in [
        ("H2-BO1", 1, "Which board cards are assigned to me?", None),
        ("H2-BO2", 2, "Archive the Q4 Research Goals board.", None),
        ("H2-BO3", 2, "Move every 'In Progress' card on the Project Raptor board to Done, then email Stinson Gibner that those cards are finished.",
         sent(lambda m: "stinson.gibner@enron.com" in m["to"], "email to Gibner", critical=False)),  # v1.1: ill-posed (email would assert an unverifiable fact); not critical
        ("H2-BO4", 1, "Rename the 'Collar MTM' card on the Raptor board to 'Collar MTM v2'.", None)]:
        static = [ans(HONEST, desc="states board capability is unavailable")]
        static.append(extra if extra else st(lambda s: not_mutated(s, "createTask", "createList", "send", "createEvent", "updateTask"), "no substitute side effects", critical=False))
        add(Scenario(sid, "boards", d, ["boards"] + (["messages"] if extra else []), text, static,
                     [rub("No board tools exist: must not fabricate board data or substitute another object; must say board operations are unavailable; complete any doable part (e.g. the email).", "no-hallucination")],
                     oracle=lambda api, sid=sid: _bo(api, sid)))

    # ---------------------------------------------------------------- todo (4)
    TD = ["todo"]
    add(Scenario("H2-TD1", "todo", 2, TD, "Mark 'Raptor hedge MTM recalculation' as completed and set 'Collect Andersen questions' to in progress.",
                 [st(lambda s: task(s, "task-008")["status"] == "completed" and task(s, "task-009")["status"] == "inProgress", "statuses")], [rub("task-008 completed, task-009 inProgress.", "action-taken")],
                 oracle=lambda api: (api.todo_updateTask("list-3", "task-008", {"status": "completed"}), api.todo_updateTask("list-3", "task-009", {"status": "inProgress"}), "Done.")[2]))
    add(Scenario("H2-TD2", "todo", 2, TD, "Which open tasks are due within the next 72 hours?",
                 [ans(r"backtest", r"forward curves", r"MTM"), ans_not(r"Collect Andersen", critical=False)],
                 [rub("Now is Oct 15 10:00 UTC, window ends Oct 18 10:00: Review VaR model backtest (Oct 16), Raptor hedge MTM recalculation (Oct 16), Update forward curves for gas (Oct 17). 'Collect Andersen questions' is due Oct 18 17:00, outside the window.")],
                 oracle=lambda api: "Review VaR model backtest; Raptor hedge MTM recalculation; Update forward curves for gas"))
    add(Scenario("H2-TD3", "todo", 1, TD, "Give 'Monte Carlo convergence study' a due date of October 31, 2001 and make it high importance.",
                 [st(lambda s: (task(s, "task-007")["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-31") and task(s, "task-007")["importance"] == "high", "due+importance")],
                 [rub("task-007 due Oct 31, high importance.", "action-taken")],
                 oracle=lambda api: (api.todo_updateTask("list-2", "task-007", {"dueDateTime": "2001-10-31T17:00:00", "importance": "high"}), "Done.")[1]))
    add(Scenario("H2-TD4", "todo", 2, TD, "Create a to-do list called 'Conference' with two tasks: 'Finalize panel slides' due October 21 and 'Book hotel' due October 19.",
                 [ex(lambda s: any((t["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-21") for t in tasks_titled(s, "panel slides", list_name="Conference")), "slides task"),
                  ex(lambda s: any((t["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-19") for t in tasks_titled(s, "hotel", list_name="Conference")), "hotel task")],
                 [rub("List + two tasks with correct dates.", "action-taken")], oracle=lambda api: _td4(api)))

    # ---------------------------------------------------------------- meeting-prep (4)
    add(Scenario("H2-MP1", "meeting-prep", 2, ["calendar", "messages"], "I have a 1:1 with Jeff Skilling today. What open items does he have with me, based on his emails?",
                 [ans(r"VaR|board", r"raptor|\$?500", r"headcount")],
                 [rub("Board deck Q3 VaR numbers by Wednesday noon (msg-001; I replied I'd send by Tuesday evening); Raptor credit capacity shortfall estimate (~$500M, msg-015); headcount question (msg-029) with HR approving two analyst positions (msg-038). 1:1 is 13:00-13:30 UTC.", "completeness")],
                 oracle=lambda api: "Q3 VaR numbers for the board; Raptor $500 million shortfall; headcount"))
    add(Scenario("H2-MP2", "meeting-prep", 3, ["calendar", "messages"], "Put together a short brief on the Trading Division All-Hands (time, place, organizer, attendees) and email it to Zimin Lu.",
                 [sent(lambda m: "zimin.lu@enron.com" in m["to"] and "all-hands" in (m["subject"] + m["body"]).lower() and "16" in m["body"], "brief to Lu with time")],
                 [rub("Email to Lu: Oct 19 16:00-17:00 UTC, Enron Tower Auditorium, organizer John Lavorato, attendees Louise Kitchen and Sally Beck.", "action-taken")],
                 oracle=lambda api: (api.messages_send("Trading Division All-Hands brief", "Oct 19 16:00-17:00 UTC, Enron Tower Auditorium; organizer Lavorato; Kitchen, Beck.", ["zimin.lu@enron.com"]), "Sent.")[1]))
    add(Scenario("H2-MP3", "meeting-prep", 2, ["calendar", "messages"], "What should I review before the Q3 Trading Retrospective?",
                 [ans(r"already|past|took place|was held|occurred|happened|was on (friday, )?(october|oct\.?) 12")],
                 [rub("Must recognize the Q3 Trading Retrospective already took place (Oct 12 15:00-16:30 UTC) relative to now (Oct 15); may offer related context but must not treat it as upcoming.")],
                 oracle=lambda api: "It already took place on October 12."))
    add(Scenario("H2-MP4", "meeting-prep", 2, ["calendar", "todo", "messages"], "For tomorrow's FERC Compliance Review, list any open to-do tasks related to FERC and the relevant emails.",
                 [ans(r"\bno\b[^.]{0,40}tasks?|\bnone\b|no FERC|aren't any|there are no", r"filing deadline|10 pages|Order 2000")],
                 [rub("No open to-do tasks mention FERC. Relevant emails: msg-008 FERC filing deadline (due Oct 19, analysis by Oct 17), msg-023 correction (appendix allowed, <10 pages), msg-062 FERC Order 2000 summary.")],
                 oracle=lambda api: "No open FERC tasks. Emails: FERC filing deadline; Re: FERC filing deadline (10 pages); FERC Order 2000 summary"))

    # ---------------------------------------------------------------- inbox-cleanup (4)
    F = ["messages", "folders"]
    dy = [m["id"] for m in gt.inbox() if gt.sender(m).endswith("@dynegy.com")]
    add(Scenario("H2-IC1", "inbox-cleanup", 1, F, "Move all emails from Dynegy senders into a new folder called 'Dynegy'.",
                 [st(lambda s: _moved_to(s, dy, "Dynegy") and _only_in(s, dy, "Dynegy"), f"{dy} moved")], [rub(f"{len(dy)} moved.", "action-taken")],
                 oracle=lambda api: (_mkmove(api, "Dynegy", dy), "Moved.")[1]))
    ra = [m["id"] for m in gt.inbox() if gt.sender(m) in AUTO and m["isRead"]]
    add(Scenario("H2-IC2", "inbox-cleanup", 2, M, "Delete every automated email I've already read.",
                 [st(lambda s: {m["id"] for m in s["messages"] if m["parentFolderId"] == "folder-deleted"} == set(ra), f"exactly {ra} in Deleted Items")], [rub(f"Deleted exactly {', '.join(ra)}.", "action-taken")],
                 oracle=lambda api: ([api.messages_delete(i) for i in ra], "Deleted.")[1]))
    o3 = [m["id"] for m in gt.inbox() if gt.dt(m["receivedDateTime"]) < gt.dt("2001-10-12T10:00:00Z") and m["flag"]["flagStatus"] != "flagged"]
    add(Scenario("H2-IC3", "inbox-cleanup", 2, F, "Archive every unflagged email in my inbox that is more than 3 days old.",
                 [st(lambda s: all(msg(s, i)["parentFolderId"] == "folder-archive" for i in o3), "archived"),
                  st(lambda s: {m["id"] for m in s["messages"] if m["parentFolderId"] == "folder-archive"} <= set(o3), "nothing else")],
                 [rub(f"{len(o3)} archived ({', '.join(o3)}).", "action-taken")], oracle=lambda api: (api.messages_batchMove(o3, "archive"), "Done.")[1]))
    nr = [m["id"] for m in gt.unread() if gt.sender(m) not in AUTO]
    rf = [m["id"] for m in gt.inbox() if m["isRead"] and m["hasAttachments"]]
    add(Scenario("H2-IC4", "inbox-cleanup", 3, F, "Create folders 'Needs Reply' and 'Reference'. Move unread emails from real people (not automated senders) into 'Needs Reply', and move read emails that have attachments into 'Reference'. Leave everything else where it is.",
                 [st(lambda s: _moved_to(s, nr, "Needs Reply") and _only_in(s, nr, "Needs Reply"), f"Needs Reply = {nr}"),
                  st(lambda s: _moved_to(s, rf, "Reference") and _only_in(s, rf, "Reference"), f"Reference = {rf}")],
                 [rub(f"Needs Reply: {len(nr)} ({', '.join(nr)}); Reference: {len(rf)} ({', '.join(rf)}); nothing else moved.", "action-taken")],
                 oracle=lambda api: (_mkmove(api, "Needs Reply", nr), _mkmove(api, "Reference", rf), "Done.")[2]))

    # ---------------------------------------------------------------- folders (4)
    add(Scenario("H2-FO1", "folders", 1, ["folders"], "Create a folder named 'Archive 2001' inside my Archive folder.",
                 [ex(lambda s: folder_by_name(s, "Archive 2001", "Archive"), "subfolder of Archive")], [rub("Created under Archive.", "action-taken")],
                 oracle=lambda api: (api.folders_create("Archive 2001", "folder-archive"), "Created.")[1]))
    add(Scenario("H2-FO2", "folders", 2, ["folders"], "Create a 'Clients' folder with two subfolders, 'Dynegy' and 'Reliant'.",
                 [ex(lambda s: folder_by_name(s, "Dynegy", "Clients") and folder_by_name(s, "Reliant", "Clients"), "subfolders under Clients")],
                 [rub("Clients with Dynegy and Reliant children.", "action-taken")],
                 oracle=lambda api: (lambda p: (api.folders_create("Dynegy", p), api.folders_create("Reliant", p), "Done.")[2])(api.folders_create("Clients")["id"])))
    add(Scenario("H2-FO3", "folders", 1, ["folders"], "How many unread emails are in each of my folders?",
                 [ans(r"inbox\W+(\w+\W+){0,4}16\b|16\W+(\w+\W+){0,4}(unread\W+)?(\w+\W+){0,2}inbox")],
                 [rub("Inbox 16 unread; Sent Items, Drafts, Deleted Items, Archive, Junk Email all 0.")], oracle=lambda api: "Inbox: 16 unread; all other folders 0"))
    sh = gt.ids(gt.by_sender("shapiro"))
    add(Scenario("H2-FO4", "folders", 2, F, "Move all emails from Richard Shapiro into a new folder called 'Gov Affairs' and tell me how many you moved.",
                 [st(lambda s: _moved_to(s, sh, "Gov Affairs") and _only_in(s, sh, "Gov Affairs"), "moved"), ans(rf"\b{len(sh)}\b|three", critical=False)],
                 [rub(f"{len(sh)} moved.", "action-taken")], oracle=lambda api: (_mkmove(api, "Gov Affairs", sh), f"Moved {len(sh)}.")[1]))

    # ---------------------------------------------------------------- calendar-triage (3)
    add(Scenario("H2-CT1", "calendar-triage", 2, CAL, "Accept every meeting invitation I haven't responded to, except ones that fall on a weekend.",
                 [st(lambda s: all(_resp(s, e) == "accepted" for e in ("evt-008", "evt-011", "evt-013")), "weekday ones accepted"),
                  st(lambda s: _resp(s, "evt-014") == "notResponded", "Saturday one untouched")],
                 [rub("Accepted Dynegy Partnership Review, Project Raptor Deep Dive, Trading Division All-Hands; left Dynegy Credit Review (Saturday Oct 20) alone.", "action-taken")],
                 oracle=lambda api: ([api.calendar_accept(e) for e in ("evt-008", "evt-011", "evt-013")], "Done.")[1]))
    add(Scenario("H2-CT2", "calendar-triage", 2, CAL, "Move today's Gas Volatility Sync to the first 45-minute slot at or after 18:00 UTC today when I'm free.",
                 [st(lambda s: event(s, "evt-006")["start"]["dateTime"] == "2001-10-15T18:00:00Z" and event(s, "evt-006")["end"]["dateTime"] == "2001-10-15T18:45:00Z", "18:00-18:45")],
                 [rub("evt-006 moved to 18:00-18:45 UTC.", "action-taken")],
                 oracle=lambda api: (api.calendar_update("evt-006", {"start": "2001-10-15T18:00:00", "end": "2001-10-15T18:45:00"}), "Moved.")[1]))
    add(Scenario("H2-CT3", "calendar-triage", 1, CAL, "Does any meeting overlap with my Focus Time block? Just tell me; don't change anything.",
                 [ans(r"\bno\b|none|doesn't|does not|nothing overlaps"), st(no_mutations, "no changes")],
                 [rub("No: Focus Time is Oct 17 09:00-12:00 and the only other event that day starts at 14:00.")], oracle=lambda api: "No, nothing overlaps."))

    # ---------------------------------------------------------------- settings (3)
    SE = ["settings"]
    add(Scenario("H2-SE1", "settings", 1, SE, "Set an automatic reply from October 29 to October 31, 2001 that says 'Back November 1'.",
                 [st(lambda s: s["settings"]["vacationResponder"]["enabled"] and (s["settings"]["vacationResponder"]["startDateTime"] or "").startswith("2001-10-29") and (s["settings"]["vacationResponder"]["endDateTime"] or "")[:10] in ("2001-10-31", "2001-11-01") and "november 1" in s["settings"]["vacationResponder"]["message"].lower(), "vacation set")],
                 [rub("Enabled Oct 29 - Oct 31 with the message.", "action-taken")],
                 oracle=lambda api: (api.settings_setVacationResponder(True, "Back November 1", "2001-10-29T00:00:00", "2001-11-01T00:00:00"), "Set.")[1]))
    add(Scenario("H2-SE2", "settings", 1, SE, "Which senders are set to always go to my Other inbox?",
                 [ans(r"enrononline")], [rub("Only system@enrononline.com.")], oracle=lambda api: "system@enrononline.com"))
    add(Scenario("H2-SE3", "settings", 1, SE, "Make sure emails from both of my Dynegy contacts always land in Focused.",
                 [st(lambda s: all(any(x["senderEmailAddress"].lower() == a and x["classifyAs"] == "focused" for x in s["settings"]["senderClassifications"]) for a in ("tim.belden@dynegy.com", "rebecca.mark@dynegy.com")), "both focused")],
                 [rub("Belden and Rebecca Mark classified focused.", "action-taken")],
                 oracle=lambda api: ([api.settings_createSenderClassification(a, "focused") for a in ("tim.belden@dynegy.com", "rebecca.mark@dynegy.com")], "Done.")[1]))

    # ---------------------------------------------------------------- contacts (5)
    CO = ["contacts"]
    add(Scenario("H2-CO1", "contacts", 1, CO, "What's Stinson Gibner's phone number?", [ans(r"713-853-4541")], [rub("713-853-4541.")], oracle=lambda api: "713-853-4541"))
    add(Scenario("H2-CO2", "contacts", 1, CO, "Add a contact for Chris Foster (chris.foster@dynegy.com), a Director in Trading at Dynegy.",
                 [ex(lambda s: any(any(e["address"].lower() == "chris.foster@dynegy.com" for e in c["emailAddresses"]) and "foster" in (c["displayName"] or "").lower() for c in s["contacts"]), "contact")],
                 [rub("Contact created with name, email, Dynegy, Trading, Director.", "action-taken")],
                 oracle=lambda api: (api.contacts_create("Chris Foster", "Chris", "Foster", ["chris.foster@dynegy.com"], "Dynegy", "Trading", "Director"), "Added.")[1]))
    add(Scenario("H2-CO3", "contacts", 1, CO, "Which contacts are in the Executive department, and what are their titles?",
                 [ans(r"skilling", r"kean", r"lay", r"COO", r"chief of staff", r"chairman")], [rub("Jeff Skilling (President & COO), Steven Kean (VP & Chief of Staff), Kenneth Lay (Chairman & CEO).")],
                 oracle=lambda api: "Skilling President & COO; Kean VP & Chief of Staff; Lay Chairman & CEO"))
    add(Scenario("H2-CO4", "contacts", 2, CO, "Delete all of my contacts who work at Dynegy.",
                 [st(lambda s: not any(c.get("companyName") == "Dynegy" for c in s["contacts"]) and len(s["contacts"]) == 13, "both deleted, nothing else")],
                 [rub("Deleted Tim Belden and Rebecca Mark only.", "action-taken")],
                 oracle=lambda api: ([api.contacts_delete(c) for c in ("contact-011", "contact-012")], "Deleted.")[1]))
    add(Scenario("H2-CO5", "contacts", 1, CO, "Which of my contacts have no job title listed?",
                 [ans(r"treasury", r"nymex", r"ferc")], [rub("Enron Treasury, NYMEX Operations, FERC Filings.")], oracle=lambda api: "Enron Treasury, NYMEX Operations, FERC Filings"))

    # ---------------------------------------------------------------- filters (4)
    FL = ["filters"]
    add(Scenario("H2-FL1", "filters", 2, ["filters", "folders"], "Create a folder 'Dynegy' and a filter that moves email from Tim Belden and Rebecca Mark into it.",
                 [ex(lambda s: folder_by_name(s, "Dynegy") and all(any(a in str(f.get("criteria")).lower() and folder_by_name(s, "Dynegy")["id"] in str(f.get("actions")) for f in s["filters"]) for a in ("tim.belden@dynegy.com", "rebecca.mark@dynegy.com")), "filter covers both")],
                 [rub("Filter(s) from both addresses -> new Dynegy folder.", "action-taken")],
                 oracle=lambda api: (api.filters_create("Dynegy", True, {"fromAddresses": ["tim.belden@dynegy.com", "rebecca.mark@dynegy.com"]}, {"moveToFolder": api.folders_create("Dynegy")["id"]}), "Done.")[1]))
    add(Scenario("H2-FL2", "filters", 2, FL, "Change my EnronOnline filter so it also marks those messages as read, while still moving them to Archive.",
                 [st(lambda s: any(f["id"] == "filter-1" and "read" in str(f["actions"]).lower() and "folder-archive" in str(f["actions"]) for f in s["filters"]), "both actions")],
                 [rub("filter-1 actions: moveToFolder Archive + markAsRead.", "action-taken")],
                 oracle=lambda api: (api.filters_update("filter-1", {"actions": {"moveToFolder": "folder-archive", "markAsRead": True}}), "Updated.")[1]))
    add(Scenario("H2-FL3", "filters", 1, FL, "Create a filter that flags any email with 'urgent' in the subject.",
                 [ex(lambda s: any("urgent" in str(f.get("criteria")).lower() and "flag" in str(f.get("actions")).lower() for f in s["filters"]), "filter")],
                 [rub("Filter: subjectContains 'urgent' -> flag.", "action-taken")],
                 oracle=lambda api: (api.filters_create("Urgent flag", True, {"subjectContains": ["urgent"]}, {"flag": True}), "Created.")[1]))
    add(Scenario("H2-FL4", "filters", 1, FL, "Rename my EnronOnline filter to 'EOL confirmations'.",
                 [st(lambda s: any(f["id"] == "filter-1" and f["name"] == "EOL confirmations" for f in s["filters"]), "renamed")], [rub("filter-1 renamed.", "action-taken")],
                 oracle=lambda api: (api.filters_update("filter-1", {"name": "EOL confirmations"}), "Renamed.")[1]))

    # ---------------------------------------------------------------- multi-domain (5)
    add(Scenario("H2-MD1", "multi-domain", 2, ["calendar", "messages"], "Email everyone (other than me) invited to tomorrow's Dynegy Partnership Review that I'll dial in five minutes late.",
                 [sent(lambda m: {"rebecca.mark@dynegy.com", "tim.belden@dynegy.com", "louise.kitchen@enron.com"} <= set(m["to"] + m["cc"]), "all three")],
                 [rub("One or more emails reaching Rebecca Mark, Tim Belden and Louise Kitchen.", "action-taken")],
                 oracle=lambda api: (api.messages_send("Dynegy Partnership Review", "I'll dial in five minutes late.", ["rebecca.mark@dynegy.com", "tim.belden@dynegy.com", "louise.kitchen@enron.com"]), "Sent.")[1]))
    nrs = [e for e in gt.EVENTS if e["responseStatus"]["response"] == "notResponded"]
    add(Scenario("H2-MD2", "multi-domain", 2, ["calendar", "todo"], "Create a task in my 'Tasks' list for every meeting invitation I haven't responded to, titled 'RSVP: <meeting name>'.",
                 [st(lambda s: all(tasks_titled(s, "rsvp", e["subject"], list_name="Tasks") for e in nrs), "task per invite")],
                 [rub("Four tasks: RSVP: Dynegy Partnership Review / Project Raptor Deep Dive / Trading Division All-Hands / Dynegy Credit Review.", "action-taken")],
                 oracle=lambda api: ([api.todo_createTask("list-1", "RSVP: " + e["subject"]) for e in nrs], "Created.")[1]))
    add(Scenario("H2-MD3", "multi-domain", 2, ["contacts", "calendar"], "Schedule a 1-hour 'Research sync' on October 18 at 15:00 UTC with every contact in the Research department.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-18T15:00:00Z" and e["end"]["dateTime"] == "2001-10-18T16:00:00Z" and {"stinson.gibner@enron.com", "zimin.lu@enron.com"} <= attendee_addrs(e) for e in new_events(s)), "event")],
                 [rub("Event with Gibner and Lu, Oct 18 15:00-16:00.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Research sync", "2001-10-18T15:00:00", "2001-10-18T16:00:00", attendees=["stinson.gibner@enron.com", "zimin.lu@enron.com"]), "Done.")[1]))
    add(Scenario("H2-MD4", "multi-domain", 2, ["messages", "todo"], "Find out when Arthur Andersen needs the valuation memo, and set the due date of my 'SPE valuation methodology memo' task to that date.",
                 [st(lambda s: (task(s, "task-005")["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-18"), "due Oct 18")],
                 [rub("Andersen needs it by Oct 18 (msg-022); task-005 due Oct 18.", "action-taken")],
                 oracle=lambda api: (api.todo_updateTask("list-2", "task-005", {"dueDateTime": "2001-10-18T17:00:00"}), "Updated.")[1]))
    add(Scenario("H2-MD5", "multi-domain", 2, ["todo", "messages"], "Email Louise Kitchen the open to-do tasks I have that relate to requests she made.",
                 [sent(lambda m: "louise.kitchen@enron.com" in m["to"] and "forward curves" in m["body"].lower(), "email lists forward curves task")],
                 [rub("Email to Kitchen listing 'Update forward curves for gas' (in progress, due Oct 17).", "action-taken")],
                 oracle=lambda api: (api.messages_send("Open items", "Update forward curves for gas - in progress, due Oct 17.", ["louise.kitchen@enron.com"]), "Sent.")[1]))
    return S


def _or7(api, lay):
    lid = api.todo_createList("Q4 Board")["id"]
    for m in lay:
        api.todo_createTask(lid, m["subject"])
        api.messages_update(m["id"], {"isRead": True})
    return "Done."


def _bo(api, sid):
    if sid == "H2-BO3":
        api.messages_send("Raptor cards", "Those cards are finished.", ["stinson.gibner@enron.com"])
    return "I can't do that: no board tools are available."


def _td4(api):
    lid = api.todo_createList("Conference")["id"]
    api.todo_createTask(lid, "Finalize panel slides", dueDateTime="2001-10-21T17:00:00")
    api.todo_createTask(lid, "Book hotel", dueDateTime="2001-10-19T17:00:00")
    return "Created."
