"""cross-domain (15), multi-domain (12), orchestration (17)."""
from __future__ import annotations

import re
from collections import Counter

from . import gt
from .scenario import (Scenario, ans, ans_not, attendee_addrs, event, ex, folder_by_name, in_folder, msg, new_events,
                       no_mutations, not_mutated, rub, sent, st, task, tasks_titled)


def _people_in(e):
    return set(gt.attendees(e)) | {e["organizer"]["emailAddress"]["address"]}


def _wk(a="2001-10-15", b="2001-10-21"):
    return [e for e in gt.EVENTS if a <= e["start"]["dateTime"][:10] <= b]


def cross_domain():
    S = []
    add = S.append
    cnt = gt.sender_counts()
    mcount = Counter()
    for e in _wk():
        for p in _people_in(e):
            mcount[p] += 1
    key = sorted([a for a in cnt if cnt[a] >= 4 and mcount[a] >= 3], key=lambda a: -cnt[a])
    add(Scenario("XD-001", "cross-domain", 3, ["messages", "calendar"], "Which people have emailed me at least 4 times AND are in at least 3 of my meetings between October 15 and October 21 (as organizer or attendee)?",
                 [ans(*[rf"\b{gt.NAME[a].split()[-1]}\b" for a in key])],
                 [rub("Exactly: " + ", ".join(f"{gt.NAME[a]} ({cnt[a]} emails, {mcount[a]} meetings)" for a in key) + ". Excludes Kean and Taylor (1 meeting each) and system accounts.")],
                 oracle=lambda api: ", ".join(gt.NAME[a] for a in key)))
    add(Scenario("XD-002", "cross-domain", 2, ["contacts", "messages"], "Which of my contacts have never emailed me?",
                 [ans(r"treasury", r"nymex", r"ferc filings|filings@ferc")], [rub("Only the institutional contacts: Enron Treasury, NYMEX Operations, FERC Filings. All 12 person contacts have emailed.")],
                 oracle=lambda api: "Enron Treasury, NYMEX Operations, FERC Filings"))
    days = Counter(e["start"]["dateTime"][:10] for e in gt.EVENTS if not e["isAllDay"])
    busy_days = {d for d, n in days.items() if n > 2}
    due = [t for t in gt.TASKS if t["dueDateTime"] and t["dueDateTime"]["dateTime"][:10] in busy_days and t["status"] != "completed"]
    add(Scenario("XD-003", "cross-domain", 3, ["todo", "calendar"], "Which of my open (not completed) to-do tasks are due on days when I have more than 2 meetings?",
                 [ans(r"backtest", r"MTM"), ans_not(r"Risk Committee slides", critical=False)],
                 [rub(f"Days with >2 meetings: {sorted(busy_days)}. Tasks due those days: " + ", ".join(f"{t['title']} ({t['dueDateTime']['dateTime'][:10]})" for t in due) + ".")],
                 oracle=lambda api: ", ".join(t["title"] for t in due)))
    nr = [e for e in gt.EVENTS if e["responseStatus"]["response"] == "notResponded"]
    orgs = sorted({e["organizer"]["emailAddress"]["address"] for e in nr})
    latest = {o: max([m for m in gt.inbox() if gt.sender(m) == o], key=lambda m: m["receivedDateTime"]) for o in orgs}
    add(Scenario("XD-004", "cross-domain", 2, ["calendar", "messages"], "For each organizer of a meeting I haven't responded to, what's the subject of the most recent email they sent me?",
                 [ans(*[re.escape(" ".join(latest[o]["subject"].split()[:3])) for o in orgs])],
                 [rub("; ".join(f"{gt.NAME[o]} -> '{latest[o]['subject']}'" for o in orgs) + ".")],
                 oracle=lambda api: "; ".join(f"{gt.NAME[o]}: {latest[o]['subject']}" for o in orgs)))
    rec72 = len(gt.within_hours(72))
    sent72 = len(gt.within_hours(72, gt.sent_items()))
    add(Scenario("XD-005", "cross-domain", 2, ["messages"], "In the last 72 hours, how many emails did I receive versus send?",
                 [ans(rf"\b{rec72}\b", rf"\b{sent72}\b")], [rub(f"Received {rec72} (inbox), sent {sent72}, within 72h of 2001-10-15 10:00 UTC.")],
                 oracle=lambda api: f"Received {rec72}, sent {sent72}"))
    oct15 = [m for m in gt.inbox() if m["receivedDateTime"][:10] == "2001-10-15"]
    add(Scenario("XD-006", "cross-domain", 3, ["calendar", "messages"], "What's my busiest day this week (Oct 15-19) by number of meetings, and how many unread emails arrived on that day so far?",
                 [ans(r"(october|oct\.?) 15|10/15|monday|today", rf"\b{len(gt.unread(oct15))}\b")],
                 [rub(f"Oct 15 (4 meetings). Unread arriving Oct 15: {len(gt.unread(oct15))} ({', '.join(gt.ids(gt.unread(oct15)))}).")],
                 oracle=lambda api: f"October 15; {len(gt.unread(oct15))} unread"))
    add(Scenario("XD-007", "cross-domain", 2, ["contacts", "messages", "calendar"], "For each of my Dynegy contacts, list the emails they've sent me and the meetings they're involved in.",
                 [ans(r"belden", r"rebecca", r"Dynegy Partnership", r"Dynegy Credit", r"term sheet")],
                 [rub("Tim Belden: emails Western power price curves, Credit exposure question, Western trading desk intro; meetings Dynegy Partnership Review (attendee), Dynegy Credit Review (organizer). Rebecca Mark: emails Dynegy joint venture term sheet + Re:; meeting Dynegy Partnership Review (organizer).", "completeness")],
                 oracle=lambda api: "Belden: curves, credit exposure, intro; Dynegy Partnership Review, Dynegy Credit Review. Rebecca Mark: term sheet x2; Dynegy Partnership Review"))
    add(Scenario("XD-008", "cross-domain", 2, ["calendar", "messages"], "Who attends my Research Team Standup, and what's the most recent email each of them sent me?",
                 [ans(r"Monte Carlo simulation parameters", r"Weather derivatives pricing model v2", r"Board presentation")],
                 [rub("Gibner -> 'Monte Carlo simulation parameters' (msg-002); Lu -> 'Weather derivatives pricing model v2' (msg-005); Skilling -> 'Board presentation: Q3 risk numbers' (msg-001).")],
                 oracle=lambda api: "Gibner: Monte Carlo simulation parameters; Lu: Weather derivatives pricing model v2; Skilling: Board presentation"))
    add(Scenario("XD-009", "cross-domain", 2, ["todo", "messages"], "Do any of my to-do tasks relate to requests Louise Kitchen made by email?",
                 [ans(r"forward curves")], [rub("Yes: 'Update forward curves for gas' (Tasks, in progress, due Oct 17) matches Kitchen's 'Forward curve update request' (msg-019).")],
                 oracle=lambda api: "Yes: Update forward curves for gas"))
    add(Scenario("XD-010", "cross-domain", 2, ["messages", "contacts"], "Which senders of high-importance emails are in the Executive department in my contacts?",
                 [ans(r"skilling", r"lay", r"kean"), ans_not(r"lavorato", critical=False)],
                 [rub("Jeff Skilling, Kenneth Lay, Steven Kean. (Lavorato is Trading; bots are not contacts.)")],
                 oracle=lambda api: "Skilling, Lay, Kean"))
    rcpt = set()
    for m in gt.sent_items():
        rcpt |= {r["emailAddress"]["address"] for r in m["toRecipients"]}
    wkp = set()
    for e in _wk("2001-10-15", "2001-10-19"):
        wkp |= _people_in(e)
    both = sorted(rcpt & wkp)
    add(Scenario("XD-011", "cross-domain", 3, ["messages", "calendar"], "How many of the people I've sent emails to (as a To recipient) are also in my meetings from October 15 to 19 (as organizer or attendee)? Name them.",
                 [ans(rf"\b{len(both)}\b")], [rub(f"{len(both)}: " + ", ".join(gt.NAME[a] for a in both) + f". Not included: {', '.join(gt.NAME[a] for a in sorted(rcpt - wkp))}.")],
                 oracle=lambda api: f"{len(both)}: " + ", ".join(gt.NAME[a] for a in both)))
    add(Scenario("XD-012", "cross-domain", 3, ["messages", "calendar"], "For the project topics Raptor, FERC, and Dynegy: which topics have unread emails, and what meetings relate to those topics?",
                 [ans(r"raptor", r"dynegy", r"Raptor Deep Dive", r"Dynegy Partnership")],
                 [rub("Raptor has unread (msg-015) -> Project Raptor Kick-off, Project Raptor Deep Dive; Dynegy has unread (msg-018, msg-030) -> Dynegy Partnership Review, Dynegy Credit Review; FERC has no unread emails.")],
                 oracle=lambda api: "Raptor: Kick-off, Raptor Deep Dive; Dynegy: Dynegy Partnership Review, Dynegy Credit Review; FERC none unread"))
    add(Scenario("XD-013", "cross-domain", 2, ["todo", "calendar"], "Are any of my tasks due while I'm at the Energy Risk Conference?",
                 [ans(r"disclosure notes")], [rub("Yes: 'Draft Raptor disclosure notes' due Oct 22 (conference Oct 22-23).")],
                 oracle=lambda api: "Draft Raptor disclosure notes (Oct 22)"))
    add(Scenario("XD-014", "cross-domain", 1, ["contacts"], "Which of my contacts has a Houston (713) phone number but doesn't work at Enron?",
                 [ans(r"rebecca|mark")], [rub("Rebecca Mark (Dynegy, 713-507-6400).")], oracle=lambda api: "Rebecca Mark"))
    per = {}
    for d in range(15, 20):
        ds = f"2001-10-{d:02d}"
        per[ds] = (len([e for e in gt.EVENTS if e["start"]["dateTime"][:10] == ds]), [t["title"] for t in gt.TASKS if t["dueDateTime"] and t["dueDateTime"]["dateTime"][:10] == ds and t["status"] != "completed"])
    add(Scenario("XD-015", "cross-domain", 3, ["calendar", "todo"], "Summarize my week (Oct 15-19): for each day, how many meetings I have and which open tasks are due.",
                 [ans(r"backtest", r"MTM", r"forward curves", r"Andersen", r"SPE")],
                 [rub("; ".join(f"{d}: {n} meetings, due: {', '.join(t) or 'none'}" for d, (n, t) in per.items()) + ".", "completeness")],
                 oracle=lambda api: "; ".join(f"{d}: {n} meetings; {', '.join(t)}" for d, (n, t) in per.items())))
    return S


def multi_domain():
    S = []
    add = S.append
    flagged = [m for m in gt.MSGS if m["flag"]["flagStatus"] == "flagged"]
    add(Scenario("MD-001", "multi-domain", 2, ["messages", "todo"], "Create a task in my 'Tasks' list for each flagged email, using the email subject as the task title.",
                 [st(lambda s: all(tasks_titled(s, m["subject"][:12], list_name="Tasks") for m in flagged), "task per flagged email")],
                 [rub("Three tasks: " + ", ".join(m["subject"] for m in flagged) + ".", "action-taken")],
                 oracle=lambda api: ([api.todo_createTask("list-1", m["subject"]) for m in flagged], "Created 3.")[1]))
    add(Scenario("MD-002", "multi-domain", 2, ["calendar", "messages"], "Send the attendees of today's Risk Committee Meeting a reminder that it starts at 15:00 UTC.",
                 [sent(lambda m: {"sally.beck@enron.com", "jeff.skilling@enron.com", "john.lavorato@enron.com"} <= set(m["to"] + m["cc"]), "one email to all three")],
                 [rub("Reminder sent to Beck, Skilling, Lavorato mentioning 15:00.", "action-taken")],
                 oracle=lambda api: (api.messages_send("Reminder: Risk Committee 15:00 UTC", "Reminder: Risk Committee starts at 15:00 UTC.", ["sally.beck@enron.com", "jeff.skilling@enron.com", "john.lavorato@enron.com"]), "Sent.")[1]))
    add(Scenario("MD-003", "multi-domain", 2, ["messages", "contacts"], "Add a contact for every person who has emailed me but isn't already in my contacts. Skip automated/system senders.",
                 [st(lambda s: not_mutated(s, "createContact"), "no contacts created")],
                 [rub("Correctly determines every human sender is already a contact, so no contacts are added; says so.", "correctness")],
                 oracle=lambda api: "All human senders are already contacts; nothing added."))
    add(Scenario("MD-004", "multi-domain", 2, ["calendar", "todo"], "Block 'Focus: SPE memo' on my calendar on October 18 from 09:00 to 11:00 UTC, and add a task 'Write SPE memo' to my Research Items list due October 18 at 11:00 UTC.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-18T09:00:00Z" and e["end"]["dateTime"] == "2001-10-18T11:00:00Z" for e in new_events(s)), "event"),
                  ex(lambda s: any((t["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-18") for t in tasks_titled(s, "spe memo", list_name="Research Items")), "task")],
                 [rub("Event and task created as specified.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Focus: SPE memo", "2001-10-18T09:00:00", "2001-10-18T11:00:00"), api.todo_createTask("list-2", "Write SPE memo", dueDateTime="2001-10-18T11:00:00"), "Done.")[2]))
    add(Scenario("MD-005", "multi-domain", 2, ["calendar", "messages"], "Add Rebecca Mark to the Dynegy Credit Review and email her the meeting time.",
                 [st(lambda s: {"rebecca.mark@dynegy.com", "sally.beck@enron.com"} <= attendee_addrs(event(s, "evt-014")), "Mark added, Beck kept"),
                  sent(lambda m: "rebecca.mark@dynegy.com" in m["to"] and ("10:00" in m["body"] or "10 am" in m["body"].lower() or "10am" in m["body"].lower()), "email with time")],
                 [rub("evt-014 attendees include Rebecca Mark (existing kept); email says Oct 20 10:00-11:00 UTC.", "action-taken")],
                 oracle=lambda api: (api.calendar_update("evt-014", {"attendees": ["tim.belden@dynegy.com", "sally.beck@enron.com", "rebecca.mark@dynegy.com"]}), api.messages_send("Dynegy Credit Review", "Oct 20, 10:00-11:00 UTC.", ["rebecca.mark@dynegy.com"]), "Done.")[2]))
    add(Scenario("MD-006", "multi-domain", 2, ["messages", "todo"], "Create a to-do list called 'Follow-ups' and add one task for each high-importance email from John Lavorato.",
                 [st(lambda s: len(tasks_titled(s, list_name="Follow-ups")) == 2, "2 tasks in Follow-ups")],
                 [rub("List 'Follow-ups' with 2 tasks: Trading limits breach (msg-013) and Gas volatility spike (msg-027).", "action-taken")],
                 oracle=lambda api: _md6(api)))
    add(Scenario("MD-007", "multi-domain", 2, ["messages", "calendar"], "Schedule a 30-minute meeting tomorrow at 16:00 UTC called 'Monte Carlo paths decision' with everyone (other than me) involved in the Monte Carlo simulation parameters email thread.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-16T16:00:00Z" and e["end"]["dateTime"] == "2001-10-16T16:30:00Z" and {"stinson.gibner@enron.com", "zimin.lu@enron.com"} <= attendee_addrs(e) for e in new_events(s)), "meeting with Gibner and Lu")],
                 [rub("Meeting Oct 16 16:00-16:30 with Gibner (sender) and Lu (cc).", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Monte Carlo paths decision", "2001-10-16T16:00:00", "2001-10-16T16:30:00", attendees=["stinson.gibner@enron.com", "zimin.lu@enron.com"]), "Scheduled.")[1]))
    add(Scenario("MD-008", "multi-domain", 2, ["todo", "messages"], "Email Zimin Lu a list of my open tasks from the Research Items list.",
                 [sent(lambda m: "zimin.lu@enron.com" in m["to"] and all(w in m["body"].lower() for w in ("spe valuation", "weather derivatives paper", "monte carlo convergence")), "email lists 3 tasks")],
                 [rub("Email to Lu listing SPE valuation methodology memo, Weather derivatives paper draft, Monte Carlo convergence study.", "action-taken")],
                 oracle=lambda api: (api.messages_send("Open Research Items", "SPE valuation methodology memo; Weather derivatives paper draft; Monte Carlo convergence study", ["zimin.lu@enron.com"]), "Sent.")[1]))
    add(Scenario("MD-009", "multi-domain", 2, ["calendar", "settings"], "Look up the dates of the Energy Risk Conference on my calendar and set my automatic reply to cover them.",
                 [st(lambda s: s["settings"]["vacationResponder"]["enabled"] and (s["settings"]["vacationResponder"]["startDateTime"] or "").startswith("2001-10-22") and (s["settings"]["vacationResponder"]["endDateTime"] or "")[:10] in ("2001-10-23", "2001-10-24"), "vacation matches conference")],
                 [rub("Vacation responder Oct 22 through Oct 23 (end-of-day or Oct 24 00:00) with a sensible message.", "action-taken")],
                 oracle=lambda api: (api.settings_setVacationResponder(True, "At the Energy Risk Conference.", "2001-10-22T00:00:00", "2001-10-24T00:00:00"), "Set.")[1]))
    add(Scenario("MD-010", "multi-domain", 2, ["calendar", "todo"], "Decline the Dynegy Partnership Review and add a task to my 'Tasks' list to read the JV term sheet, due October 16.",
                 [st(lambda s: event(s, "evt-008")["responseStatus"]["response"] == "declined", "declined"),
                  ex(lambda s: any((t["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-16") for t in tasks_titled(s, "term sheet", list_name="Tasks")), "task")],
                 [rub("Declined evt-008 and created the task.", "action-taken")],
                 oracle=lambda api: (api.calendar_decline("evt-008"), api.todo_createTask("list-1", "Read JV term sheet", dueDateTime="2001-10-16T17:00:00"), "Done.")[2]))
    add(Scenario("MD-011", "multi-domain", 2, ["todo", "messages"], "Send Mark Taylor the list of tasks in my Project Raptor Backlog with their due dates.",
                 [sent(lambda m: "mark.taylor@enron.com" in m["to"] and all(w in m["body"].lower() for w in ("mtm", "andersen", "disclosure")), "email with 3 tasks")],
                 [rub("Email to Taylor listing Raptor hedge MTM recalculation (Oct 16), Collect Andersen questions (Oct 18), Draft Raptor disclosure notes (Oct 22).", "action-taken")],
                 oracle=lambda api: (api.messages_send("Raptor backlog", "MTM recalculation Oct 16; Collect Andersen questions Oct 18; Draft Raptor disclosure notes Oct 22", ["mark.taylor@enron.com"]), "Sent.")[1]))
    add(Scenario("MD-012", "multi-domain", 2, ["messages", "calendar"], "Rebecca Mark mentioned when the Dynegy board meets. Add an all-day calendar event on that date titled 'Dynegy board meeting - JV comments due'.",
                 [ex(lambda s: any(e["isAllDay"] and e["start"]["dateTime"][:10] == "2001-10-24" for e in new_events(s)), "all-day Oct 24")],
                 [rub("All-day event on Oct 24 with that title.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Dynegy board meeting - JV comments due", "2001-10-24T00:00:00", "2001-10-25T00:00:00", isAllDay=True), "Added.")[1]))
    return S


def _md6(api):
    lid = api.todo_createList("Follow-ups")["id"]
    api.todo_createTask(lid, "Trading limits breach - urgent")
    api.todo_createTask(lid, "Gas volatility spike - need model run")
    return "Created."


def orchestration():
    S = []
    add = S.append
    add(Scenario("OR-001", "orchestration", 3, ["messages", "todo", "calendar"], "Handle the FERC filing request: create a task 'FERC price-formation analysis' in my Tasks list due October 17, block 'FERC analysis work' on my calendar October 16 from 16:00 to 18:00 UTC, and reply to Steve Kean's original FERC email confirming the delivery date.",
                 [ex(lambda s: any((t["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-17") for t in tasks_titled(s, "ferc", list_name="Tasks")), "task"),
                  ex(lambda s: any(e["start"]["dateTime"] == "2001-10-16T16:00:00Z" and e["end"]["dateTime"] == "2001-10-16T18:00:00Z" for e in new_events(s)), "event"),
                  sent(lambda m: m["inReplyTo"] == "msg-008", "reply to msg-008")],
                 [rub("All three steps done; reply confirms Oct 17.", "action-taken")],
                 oracle=lambda api: (api.todo_createTask("list-1", "FERC price-formation analysis", dueDateTime="2001-10-17T17:00:00"), api.calendar_create("FERC analysis work", "2001-10-16T16:00:00", "2001-10-16T18:00:00"), api.messages_reply("msg-008", "Confirmed for October 17."), "Done.")[3]))
    au = gt.ids(gt.unread(gt.automated()))
    add(Scenario("OR-002", "orchestration", 2, ["messages", "folders"], "For every unread email from an automated sender: mark it read and move it to Archive. Then tell me how many you processed.",
                 [st(lambda s: all(msg(s, i)["isRead"] and msg(s, i)["parentFolderId"] == "folder-archive" for i in au), "processed"),
                  st(lambda s: {m["id"] for m in s["messages"] if m["parentFolderId"] == "folder-archive"} <= set(au), "nothing else"), ans(rf"\b{len(au)}\b", critical=False)],
                 [rub(f"{len(au)} processed: {', '.join(au)}.", "action-taken")],
                 oracle=lambda api: ([api.messages_update(i, {"isRead": True}) for i in au], api.messages_batchMove(au, "archive"), f"{len(au)} processed.")[2]))
    add(Scenario("OR-003", "orchestration", 2, ["messages", "todo"], "Reply to John Lavorato's gas volatility email saying the results will come by 17:00 UTC, and add a high-importance task 'Send storage model results to Lavorato' to my Tasks list due today at 17:00 UTC.",
                 [sent(lambda m: m["inReplyTo"] == "msg-027", "reply to 027"),
                  ex(lambda s: any(t["importance"] == "high" and (t["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-15T17") for t in tasks_titled(s, "storage model", list_name="Tasks")), "task")],
                 [rub("Reply to msg-027 and high-importance task due 2001-10-15 17:00.", "action-taken")],
                 oracle=lambda api: (api.messages_reply("msg-027", "Results by 17:00 UTC."), api.todo_createTask("list-1", "Send storage model results to Lavorato", dueDateTime="2001-10-15T17:00:00", importance="high"), "Done.")[2]))
    add(Scenario("OR-004", "orchestration", 3, ["messages", "calendar"], "Sally Beck proposed a window for the VaR model review, but I'm at the Energy Risk Conference for part of it. Schedule a 'VaR Model Review kickoff' on the first day of her window after the conference, 10:00-11:00 UTC, with Sally Beck and Stinson Gibner, then reply to her email with the time.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-24T10:00:00Z" and e["end"]["dateTime"] == "2001-10-24T11:00:00Z" and {"sally.beck@enron.com", "stinson.gibner@enron.com"} <= attendee_addrs(e) for e in new_events(s)), "event Oct 24 10:00"),
                  sent(lambda m: m["inReplyTo"] == "msg-021" and "24" in m["body"], "reply to msg-021 with Oct 24")],
                 [rub("Window Oct 22-26, conference Oct 22-23 -> kickoff Oct 24 10:00-11:00 with Beck+Gibner; reply to msg-021 states the time.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("VaR Model Review kickoff", "2001-10-24T10:00:00", "2001-10-24T11:00:00", attendees=["sally.beck@enron.com", "stinson.gibner@enron.com"]), api.messages_reply("msg-021", "Kickoff scheduled October 24 10:00-11:00 UTC."), "Done.")[2]))
    add(Scenario("OR-005", "orchestration", 3, ["todo", "messages", "calendar"], "Andersen needs the Raptor valuation memo. Add a high-importance task 'Raptor valuation memo for Andersen' to the Project Raptor Backlog due on the date Andersen needs it, email Stinson Gibner asking for a draft one day earlier, and accept the Project Raptor Deep Dive.",
                 [ex(lambda s: any(t["importance"] == "high" and (t["dueDateTime"] or {}).get("dateTime", "").startswith("2001-10-18") for t in tasks_titled(s, "valuation memo", list_name="Project Raptor Backlog")), "task due Oct 18"),
                  sent(lambda m: "stinson.gibner@enron.com" in m["to"] and "17" in m["body"], "email Gibner Oct 17"),
                  st(lambda s: event(s, "evt-011")["responseStatus"]["response"] == "accepted", "deep dive accepted")],
                 [rub("Task due Oct 18 (from msg-022), Gibner asked for draft Oct 17, evt-011 accepted.", "action-taken")],
                 oracle=lambda api: (api.todo_createTask("list-3", "Raptor valuation memo for Andersen", dueDateTime="2001-10-18T17:00:00", importance="high"), api.messages_send("Raptor memo draft", "Please send a draft by October 17.", ["stinson.gibner@enron.com"]), api.calendar_accept("evt-011"), "Done.")[3]))
    add(Scenario("OR-006", "orchestration", 2, ["settings", "messages", "calendar"], "Get me ready for the conference: turn on my automatic reply for the conference dates naming Stinson Gibner as my point of contact, and email Stinson to let him know he's covering.",
                 [st(lambda s: s["settings"]["vacationResponder"]["enabled"] and (s["settings"]["vacationResponder"]["startDateTime"] or "").startswith("2001-10-22") and "gibner" in s["settings"]["vacationResponder"]["message"].lower(), "vacation set"),
                  sent(lambda m: "stinson.gibner@enron.com" in m["to"], "email Gibner")],
                 [rub("Vacation Oct 22-23 mentioning Gibner; email to Gibner.", "action-taken")],
                 oracle=lambda api: (api.settings_setVacationResponder(True, "Contact Stinson Gibner.", "2001-10-22T00:00:00", "2001-10-24T00:00:00"), api.messages_send("Covering", "You're covering Oct 22-23.", ["stinson.gibner@enron.com"]), "Done.")[2]))
    xls = [m["id"] for m in gt.inbox() if any(a["name"].endswith(".xls") for a in m["attachments"])]
    add(Scenario("OR-007", "orchestration", 3, ["messages"], "Forward every email in my inbox that has an Excel (.xls) attachment to Zimin Lu.",
                 [st(lambda s: set(xls) <= {m["inReplyTo"] for m in s["sentMessages"] if m["kind"] == "forward" and "zimin.lu@enron.com" in m["to"]}, f"forwarded {xls}")],
                 [rub(f"Forwarded {len(xls)} emails: {', '.join(xls)}.", "action-taken")],
                 oracle=lambda api: ([api.messages_forward(i, ["zimin.lu@enron.com"]) for i in xls], "Forwarded.")[1]))
    add(Scenario("OR-008", "orchestration", 3, ["folders", "messages", "todo"], "Create a folder 'Board Prep', move the board-related emails I received from Kenneth Lay and Jeff Skilling into it, and add a task 'Board risk summary' to my Tasks list due October 17.",
                 [st(lambda s: in_folder(s, "msg-001", "Board Prep") and in_folder(s, "msg-036", "Board Prep"), "001 and 036 moved"),
                  ex(lambda s: tasks_titled(s, "board risk summary", list_name="Tasks"), "task")],
                 [rub("msg-001 (Board presentation) and msg-036 (Board meeting prep) moved; task created due Oct 17.", "action-taken")],
                 oracle=lambda api: (api.messages_batchMove(["msg-001", "msg-036"], api.folders_create("Board Prep")["id"]), api.todo_createTask("list-1", "Board risk summary", dueDateTime="2001-10-17T17:00:00"), "Done.")[2]))
    add(Scenario("OR-009", "orchestration", 3, ["messages", "todo", "folders"], "For each email from Legal Ticketing, create a task in my Tasks list whose title includes the ticket number, then move those emails into a new folder called 'Legal Tickets'.",
                 [ex(lambda s: tasks_titled(s, "LT-4471", list_name="Tasks") and tasks_titled(s, "LT-4480", list_name="Tasks"), "tasks with ticket numbers"),
                  st(lambda s: in_folder(s, "msg-007", "Legal Tickets") and in_folder(s, "msg-024", "Legal Tickets"), "moved")],
                 [rub("Two tasks (LT-4471 NDA review, LT-4480 compliance hold); both emails moved.", "action-taken")],
                 oracle=lambda api: (api.todo_createTask("list-1", "LT-4471 NDA review"), api.todo_createTask("list-1", "LT-4480 compliance hold"), api.messages_batchMove(["msg-007", "msg-024"], api.folders_create("Legal Tickets")["id"]), "Done.")[3]))
    tgt = [m["id"] for m in gt.unread(gt.within_hours(24)) if gt.sender(m) not in {"system@enrononline.com", "legal-tickets@enron.com", "alerts@gasbank.enron.com"}]
    add(Scenario("OR-010", "orchestration", 3, ["messages"], "Reply to every unread email I received in the last 24 hours from a real person (not an automated system) with 'Received - will respond by end of day.'",
                 [st(lambda s: set(tgt) <= {m["inReplyTo"] for m in s["sentMessages"]}, f"replied to {tgt}"),
                  st(lambda s: {m["inReplyTo"] for m in s["sentMessages"]} <= set(tgt), "no extra replies")],
                 [rub(f"Replies to exactly {', '.join(tgt)}.", "action-taken")],
                 oracle=lambda api: ([api.messages_reply(i, "Received - will respond by end of day.") for i in tgt], "Replied.")[1]))
    add(Scenario("OR-011", "orchestration", 2, ["messages", "todo"], "Forward the settlement discrepancies email to Stinson Gibner asking him to check for curve mismatches, and add a task 'Investigate settlement discrepancies' to my Research Items list due October 19.",
                 [sent(lambda m: m["kind"] == "forward" and m["inReplyTo"] == "msg-034" and "stinson.gibner@enron.com" in m["to"], "forward 034"),
                  ex(lambda s: tasks_titled(s, "settlement", list_name="Research Items"), "task")],
                 [rub("Forwarded msg-034 to Gibner and created task in Research Items due Oct 19.", "action-taken")],
                 oracle=lambda api: (api.messages_forward("msg-034", ["stinson.gibner@enron.com"], "Please check curve mismatches."), api.todo_createTask("list-2", "Investigate settlement discrepancies", dueDateTime="2001-10-19T17:00:00"), "Done.")[2]))
    add(Scenario("OR-012", "orchestration", 2, ["calendar", "messages"], "Accept the Gas Volatility Sync and email Zimin Lu the current implied vol figure, asking him to bring the storage model results.",
                 [st(lambda s: event(s, "evt-006")["responseStatus"]["response"] == "accepted", "accepted"),
                  sent(lambda m: "zimin.lu@enron.com" in m["to"] and "85" in m["body"], "email with 85%")],
                 [rub("evt-006 accepted; email to Lu cites 85% implied vol and asks for storage model results.", "action-taken")],
                 oracle=lambda api: (api.calendar_accept("evt-006"), api.messages_send("Gas Volatility Sync", "Implied vol is 85%; please bring storage model results.", ["zimin.lu@enron.com"]), "Done.")[2]))
    add(Scenario("OR-013", "orchestration", 3, ["calendar", "messages", "todo"], "Create a 'Research Weekly Review' meeting on October 19 from 14:00 to 15:00 UTC with Stinson Gibner and Zimin Lu, and send them an agenda email listing my open Research Items tasks.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-19T14:00:00Z" and {"stinson.gibner@enron.com", "zimin.lu@enron.com"} <= attendee_addrs(e) for e in new_events(s)), "meeting"),
                  sent(lambda m: {"stinson.gibner@enron.com", "zimin.lu@enron.com"} <= set(m["to"] + m["cc"]) and all(w in m["body"].lower() for w in ("spe", "weather", "monte carlo")), "agenda email")],
                 [rub("Meeting created and agenda listing the three open Research Items tasks sent to both.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Research Weekly Review", "2001-10-19T14:00:00", "2001-10-19T15:00:00", attendees=["stinson.gibner@enron.com", "zimin.lu@enron.com"]), api.messages_send("Agenda", "SPE valuation methodology memo; Weather derivatives paper draft; Monte Carlo convergence study", ["stinson.gibner@enron.com", "zimin.lu@enron.com"]), "Done.")[2]))
    rap = gt.ids(gt.mentions("raptor", gt.inbox()))
    add(Scenario("OR-014", "orchestration", 2, ["folders", "messages"], "Move all Raptor emails from my inbox into a new 'Raptor' folder, mark them all as read, and tell me how many there were.",
                 [st(lambda s: all(in_folder(s, i, "Raptor") and msg(s, i)["isRead"] for i in rap), "moved + read"), ans(rf"\b{len(rap)}\b|four", critical=False)],
                 [rub(f"{len(rap)} emails ({', '.join(rap)}) moved and read.", "action-taken")],
                 oracle=lambda api: ([api.messages_update(i, {"isRead": True}) for i in rap], api.messages_batchMove(rap, api.folders_create("Raptor")["id"]), f"{len(rap)} emails.")[2]))
    add(Scenario("OR-015", "orchestration", 3, ["messages", "folders"], "Handle the compliance hold: flag the compliance hold ticket email, move it into a new folder 'Compliance', and email Stinson Gibner and Zimin Lu telling them not to delete any research files.",
                 [st(lambda s: in_folder(s, "msg-024", "Compliance") and msg(s, "msg-024")["flag"].get("flagStatus") == "flagged", "flagged+moved"),
                  sent(lambda m: {"stinson.gibner@enron.com", "zimin.lu@enron.com"} <= set(m["to"] + m["cc"]) and "delete" in m["body"].lower(), "email")],
                 [rub("msg-024 flagged and moved to Compliance; email to Gibner and Lu.", "action-taken")],
                 oracle=lambda api: (api.messages_update("msg-024", {"flag": {"flagStatus": "flagged"}}), api.messages_move("msg-024", api.folders_create("Compliance")["id"]), api.messages_send("Compliance hold", "Do not delete any research files.", ["stinson.gibner@enron.com", "zimin.lu@enron.com"]), "Done.")[3]))
    add(Scenario("OR-016", "orchestration", 2, ["todo", "messages"], "Mark my 'Update forward curves for gas' task as completed and reply to Louise Kitchen's forward curve request saying the curves have been refreshed.",
                 [st(lambda s: task(s, "task-002")["status"] == "completed", "completed"), sent(lambda m: m["inReplyTo"] == "msg-019", "reply to 019")],
                 [rub("task-002 completed; reply to msg-019.", "action-taken")],
                 oracle=lambda api: (api.todo_updateTask("list-1", "task-002", {"status": "completed"}), api.messages_reply("msg-019", "Curves refreshed."), "Done.")[2]))
    add(Scenario("OR-017", "orchestration", 3, ["calendar", "messages"], "Find the earliest free hour tomorrow afternoon (between 12:00 and 18:00 UTC) for a 'Bandwidth pricing' meeting with Louise Kitchen, book it, and email her the time.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-16T12:00:00Z" and e["end"]["dateTime"] == "2001-10-16T13:00:00Z" and "louise.kitchen@enron.com" in attendee_addrs(e) for e in new_events(s)), "booked 12:00"),
                  sent(lambda m: "louise.kitchen@enron.com" in m["to"] and "12" in m["body"], "email time")],
                 [rub("Booked Oct 16 12:00-13:00 UTC (free after 11-12 meetings) with Kitchen; emailed her.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Bandwidth pricing", "2001-10-16T12:00:00", "2001-10-16T13:00:00", attendees=["louise.kitchen@enron.com"]), api.messages_send("Bandwidth pricing", "Booked Oct 16 12:00-13:00 UTC.", ["louise.kitchen@enron.com"]), "Done.")[2]))
    return S
