"""calendar-read (12), calendar-write (12), calendar-triage (8), meeting-prep (9)."""
from __future__ import annotations

from . import gt
from .scenario import (Scenario, ans, ans_not, attendee_addrs, event, events_named, new_events, no_mutations, rub,
                       sent, st, tasks_titled)

CAL = ["calendar"]


def _resp(s, eid):
    e = event(s, eid)
    return e and e["responseStatus"]["response"]


def calendar_read():
    S, add = [], None
    S = []
    add = S.append
    add(Scenario("CR-001", "calendar-read", 1, CAL, "What meetings do I have today (October 15)?",
                 [ans(r"standup", r"1:1 with skilling|skilling", r"risk committee", r"gas volatility")],
                 [rub("Four events on Oct 15: Research Team Standup 09:00-09:30, 1:1 with Skilling 13:00-13:30, Risk Committee Meeting 15:00-16:30, Gas Volatility Sync 17:00-17:45 (UTC).", "completeness")],
                 oracle=lambda api: "Standup 09:00; 1:1 with Skilling 13:00; Risk Committee 15:00; Gas Volatility Sync 17:00"))
    add(Scenario("CR-002", "calendar-read", 1, CAL, "What's on my calendar tomorrow?",
                 [ans(r"FERC Compliance", r"Dynegy Partnership", r"Kitchen")],
                 [rub("Oct 16: FERC Compliance Review 11:00-12:00, Dynegy Partnership Review 11:00-12:00 (overlap), 1:1 with Kitchen 15:00-15:30.", "completeness")],
                 oracle=lambda api: "FERC Compliance Review 11-12; Dynegy Partnership Review 11-12; 1:1 with Kitchen 15:00"))
    add(Scenario("CR-003", "calendar-read", 2, CAL, "Do I have any double-booked meetings in the next two weeks? Tell me which ones.",
                 [ans(r"FERC Compliance", r"Dynegy Partnership")],
                 [rub("Only conflict: FERC Compliance Review and Dynegy Partnership Review, both Oct 16 11:00-12:00 UTC. The Energy Risk Conference (all-day Oct 22-23) has no overlapping meetings.")],
                 oracle=lambda api: "FERC Compliance Review and Dynegy Partnership Review both Oct 16 11:00-12:00"))
    add(Scenario("CR-004", "calendar-read", 1, CAL, "When is my next meeting and who is attending?",
                 [ans(r"1:1 with Skilling|Skilling", r"13:00|1(:00)?\s?pm")],
                 [rub("Current time is 2001-10-15 10:00 UTC; next meeting is 1:1 with Skilling at 13:00-13:30 UTC with Jeff Skilling. (Standup at 09:00 has already passed.)")],
                 oracle=lambda api: "1:1 with Skilling at 13:00 UTC, with Jeff Skilling"))
    nr = [e for e in gt.EVENTS if e["responseStatus"]["response"] == "notResponded"]
    add(Scenario("CR-005", "calendar-read", 2, CAL, "How many meeting invitations haven't I responded to yet? List them.",
                 [ans(rf"\b{len(nr)}\b|four"), ans(r"Dynegy Partnership", r"Raptor Deep Dive", r"All-Hands", r"Dynegy Credit")],
                 [rub(f"{len(nr)} not responded: " + ", ".join(e['subject'] for e in nr) + ".")],
                 oracle=lambda api: f"{len(nr)}: " + ", ".join(e['subject'] for e in nr)))
    add(Scenario("CR-006", "calendar-read", 1, CAL, "Where and when is the team lunch?",
                 [ans(r"Pappadeaux", r"12:00|noon|12 ?pm", r"18")], [rub("Team Lunch at Pappadeaux Seafood Kitchen, Oct 18 12:00-13:30 UTC.")],
                 oracle=lambda api: "Pappadeaux Seafood Kitchen, Oct 18 12:00-13:30"))
    wk = [e for e in gt.EVENTS if "2001-10-15" <= e["start"]["dateTime"][:10] <= "2001-10-19" and not e["isAllDay"]]
    hrs = sum((gt.dt(e["end"]["dateTime"]) - gt.dt(e["start"]["dateTime"])).total_seconds() for e in wk) / 3600
    add(Scenario("CR-007", "calendar-read", 3, CAL, "Add up the durations of every event on my calendar from Monday Oct 15 through Friday Oct 19. What's the total in hours?",
                 [ans(r"13\.25|13 hours(,| and)? 15|13h ?15|13¼")],
                 [rub(f"{len(wk)} events Oct 15-19 totaling {hrs:g} hours (13h15m), counting overlapping events separately and including Focus Time (3h).")],
                 oracle=lambda api: f"{hrs:g} hours"))
    sk = [e for e in gt.EVENTS if "2001-10-15" <= e["start"]["dateTime"][:10] <= "2001-10-21" and ("jeff.skilling@enron.com" in gt.attendees(e) or e["organizer"]["emailAddress"]["address"] == "jeff.skilling@enron.com")]
    add(Scenario("CR-008", "calendar-read", 2, CAL, "Which of my meetings this week (Oct 15-21) include Jeff Skilling?",
                 [ans(r"standup", r"1:1 with Skilling", r"Risk Committee", r"Raptor Deep Dive")],
                 [rub(f"{len(sk)} meetings: " + ", ".join(e['subject'] for e in sk) + ".", "completeness")],
                 oracle=lambda api: ", ".join(e['subject'] for e in sk)))
    add(Scenario("CR-009", "calendar-read", 1, CAL, "When and where is the Energy Risk Conference?",
                 [ans(r"22", r"23", r"Hyatt")], [rub("All-day Oct 22-23, 2001 at the Hyatt Regency Houston.")],
                 oracle=lambda api: "Oct 22-23 at Hyatt Regency Houston"))
    add(Scenario("CR-010", "calendar-read", 1, CAL, "What meetings did I have last week (October 8-14)?",
                 [ans(r"Raptor Kick-?off", r"Q3 Trading Retrospective")], [rub("Project Raptor Kick-off (Oct 8 14:00-15:00) and Q3 Trading Retrospective (Oct 12 15:00-16:30).")],
                 oracle=lambda api: "Project Raptor Kick-off; Q3 Trading Retrospective"))
    add(Scenario("CR-011", "calendar-read", 2, CAL, "Am I free on Wednesday October 17 from 13:00 to 14:00 UTC?",
                 [ans(r"\byes\b|you are free|you're free|free")], [rub("Yes. Oct 17 has Focus Time 09:00-12:00 and Project Raptor Deep Dive 14:00-16:00; 13:00-14:00 is free.")],
                 oracle=lambda api: "Yes, you're free."))
    mine = [e for e in gt.EVENTS if e["responseStatus"]["response"] == "organizer"]
    add(Scenario("CR-012", "calendar-read", 2, CAL, "List all the events where I am the organizer.",
                 [ans(r"standup", r"focus time", r"lunch")], [rub(f"{len(mine)} events organized by Kaminski: " + ", ".join(e['subject'] for e in mine) + ".")],
                 oracle=lambda api: ", ".join(e['subject'] for e in mine)))
    return S


def _new(s, *words):
    return [e for e in new_events(s) if all(w.lower() in e["subject"].lower() for w in words)]


def calendar_write():
    S = []
    add = S.append
    add(Scenario("CW-001", "calendar-write", 1, CAL, "Create a meeting called 'Weather Model Review' on October 18, 2001 from 15:00 to 16:00 UTC with Zimin Lu and Stinson Gibner.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-18T15:00:00Z" and e["end"]["dateTime"] == "2001-10-18T16:00:00Z" and {"zimin.lu@enron.com", "stinson.gibner@enron.com"} <= attendee_addrs(e) for e in _new(s, "weather model review")), "event exists with time+attendees")],
                 [rub("Created 'Weather Model Review' Oct 18 15:00-16:00 UTC with Lu and Gibner.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Weather Model Review", "2001-10-18T15:00:00", "2001-10-18T16:00:00", attendees=["zimin.lu@enron.com", "stinson.gibner@enron.com"]), "Created.")[1]))
    add(Scenario("CW-002", "calendar-write", 1, CAL, "Accept the Project Raptor Deep Dive invitation.",
                 [st(lambda s: _resp(s, "evt-011") == "accepted", "evt-011 accepted")], [rub("Accepted evt-011.", "action-taken")],
                 oracle=lambda api: (api.calendar_accept("evt-011"), "Accepted.")[1]))
    add(Scenario("CW-003", "calendar-write", 1, CAL, "Decline the Trading Division All-Hands with the comment 'Conflict with a research deadline'.",
                 [st(lambda s: _resp(s, "evt-013") == "declined", "evt-013 declined")],
                 [rub("Declined evt-013 with the comment.", "action-taken")],
                 oracle=lambda api: (api.calendar_decline("evt-013", "Conflict with a research deadline"), "Declined.")[1]))
    add(Scenario("CW-004", "calendar-write", 2, CAL, "Move my 1:1 with Louise Kitchen tomorrow to 16:00-16:30 UTC.",
                 [st(lambda s: event(s, "evt-009")["start"]["dateTime"] == "2001-10-16T16:00:00Z" and event(s, "evt-009")["end"]["dateTime"] == "2001-10-16T16:30:00Z", "evt-009 moved")],
                 [rub("Updated evt-009 (not a new event) to Oct 16 16:00-16:30.", "action-taken")],
                 oracle=lambda api: (api.calendar_update("evt-009", {"start": "2001-10-16T16:00:00", "end": "2001-10-16T16:30:00"}), "Moved.")[1]))
    add(Scenario("CW-005", "calendar-write", 1, CAL, "Cancel the team lunch at Pappadeaux.",
                 [st(lambda s: event(s, "evt-012") is None, "evt-012 deleted"), st(lambda s: len(s["events"]) == 14, "no other events deleted")],
                 [rub("Deleted evt-012 only.", "action-taken")],
                 oracle=lambda api: (api.calendar_delete("evt-012"), "Cancelled.")[1]))
    add(Scenario("CW-006", "calendar-write", 1, CAL, "Schedule a 30-minute 'FERC analysis check-in' with Steven Kean and Richard Shapiro on October 17 at 13:00 UTC.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-17T13:00:00Z" and e["end"]["dateTime"] == "2001-10-17T13:30:00Z" and {"steven.kean@enron.com", "richard.shapiro@enron.com"} <= attendee_addrs(e) for e in _new(s, "ferc")), "event correct")],
                 [rub("Created FERC analysis check-in Oct 17 13:00-13:30 with Kean and Shapiro.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("FERC analysis check-in", "2001-10-17T13:00:00", "2001-10-17T13:30:00", attendees=["steven.kean@enron.com", "richard.shapiro@enron.com"]), "Done.")[1]))
    add(Scenario("CW-007", "calendar-write", 2, CAL, "Add John Lavorato to the team lunch at Pappadeaux.",
                 [st(lambda s: {"john.lavorato@enron.com", "stinson.gibner@enron.com", "zimin.lu@enron.com"} <= attendee_addrs(event(s, "evt-012")), "Lavorato added, existing attendees kept")],
                 [rub("evt-012 attendees now include Lavorato while keeping Gibner and Lu.", "action-taken")],
                 oracle=lambda api: (api.calendar_update("evt-012", {"attendees": ["stinson.gibner@enron.com", "zimin.lu@enron.com", "john.lavorato@enron.com"]}), "Added.")[1]))
    add(Scenario("CW-008", "calendar-write", 2, CAL, "Create an all-day event called 'Research Offsite Planning' on October 25, 2001.",
                 [ex(lambda s: any(e["isAllDay"] and e["start"]["dateTime"][:10] == "2001-10-25" for e in _new(s, "offsite")), "all-day event on Oct 25")],
                 [rub("All-day event 'Research Offsite Planning' on Oct 25.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Research Offsite Planning", "2001-10-25T00:00:00", "2001-10-26T00:00:00", isAllDay=True), "Created.")[1]))
    add(Scenario("CW-009", "calendar-write", 1, CAL, "Change the location of the Research Team Standup to 'EB 1974'.",
                 [st(lambda s: event(s, "evt-003")["location"]["displayName"].strip().upper() == "EB 1974", "location updated")],
                 [rub("evt-003 location changed to EB 1974.", "action-taken")],
                 oracle=lambda api: (api.calendar_update("evt-003", {"location": "EB 1974"}), "Updated.")[1]))
    add(Scenario("CW-010", "calendar-write", 2, CAL, "Accept every meeting invitation I haven't responded to that falls on October 16 or October 17.",
                 [st(lambda s: _resp(s, "evt-008") == "accepted" and _resp(s, "evt-011") == "accepted", "008 & 011 accepted"),
                  st(lambda s: _resp(s, "evt-013") == "notResponded" and _resp(s, "evt-014") == "notResponded", "others untouched")],
                 [rub("Accepted Dynegy Partnership Review (Oct 16) and Project Raptor Deep Dive (Oct 17) only.", "action-taken")],
                 oracle=lambda api: ([api.calendar_accept(i) for i in ("evt-008", "evt-011")], "Accepted 2.")[1]))
    add(Scenario("CW-011", "calendar-write", 2, CAL, "Extend today's Risk Committee Meeting by 30 minutes.",
                 [st(lambda s: event(s, "evt-005")["end"]["dateTime"] == "2001-10-15T17:00:00Z" and event(s, "evt-005")["start"]["dateTime"] == "2001-10-15T15:00:00Z", "ends 17:00")],
                 [rub("evt-005 now 15:00-17:00 UTC.", "action-taken")],
                 oracle=lambda api: (api.calendar_update("evt-005", {"end": "2001-10-15T17:00:00"}), "Extended.")[1]))
    add(Scenario("CW-012", "calendar-write", 3, CAL, "Schedule a 1-hour 'Raptor valuation memo review' with Mark Taylor in the earliest free hour between 09:00 and 12:00 UTC on any day after October 17 (weekdays only).",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-18T09:00:00Z" and e["end"]["dateTime"] == "2001-10-18T10:00:00Z" and "mark.taylor@enron.com" in attendee_addrs(e) for e in _new(s, "raptor")), "Oct 18 09:00-10:00 with Taylor")],
                 [rub("Booked Oct 18 09:00-10:00 UTC (first weekday after Oct 17; morning free) with Mark Taylor.", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Raptor valuation memo review", "2001-10-18T09:00:00", "2001-10-18T10:00:00", attendees=["mark.taylor@enron.com"]), "Booked Oct 18 09:00.")[1]))
    return S


def ex(fn, desc, critical=True):
    from .scenario import ex as _ex
    return _ex(fn, desc, critical)


def calendar_triage():
    S = []
    add = S.append
    add(Scenario("CT-001", "calendar-triage", 3, ["calendar", "messages"], "Resolve my October 16 11:00 conflict: keep the FERC Compliance Review, decline the Dynegy Partnership Review, and email Rebecca Mark proposing we meet at 16:00 UTC that day instead.",
                 [st(lambda s: _resp(s, "evt-008") == "declined", "008 declined"), st(lambda s: _resp(s, "evt-007") == "accepted", "007 kept"),
                  sent(lambda m: "rebecca.mark@dynegy.com" in m["to"] + m["cc"] and "16" in m["body"], "email to Mark with 16:00")],
                 [rub("Declined evt-008, left evt-007 accepted, emailed Rebecca Mark proposing Oct 16 16:00.", "action-taken")],
                 oracle=lambda api: (api.calendar_decline("evt-008", "Conflict"), api.messages_send("Dynegy Partnership Review", "Could we meet Oct 16 at 16:00 UTC instead?", ["rebecca.mark@dynegy.com"]), "Done.")[2]))
    add(Scenario("CT-002", "calendar-triage", 2, CAL, "Decline every meeting on Saturday, October 20.",
                 [st(lambda s: _resp(s, "evt-014") == "declined", "014 declined")], [rub("Declined Dynegy Credit Review (only Oct 20 event).", "action-taken")],
                 oracle=lambda api: (api.calendar_decline("evt-014"), "Declined.")[1]))
    add(Scenario("CT-003", "calendar-triage", 3, ["calendar", "contacts"], "Go through the invitations I haven't responded to: accept the ones organized by Enron colleagues and decline the ones organized by people from Dynegy.",
                 [st(lambda s: _resp(s, "evt-008") == "declined" and _resp(s, "evt-014") == "declined", "Dynegy-organized declined"),
                  st(lambda s: _resp(s, "evt-011") == "accepted" and _resp(s, "evt-013") == "accepted", "Enron-organized accepted")],
                 [rub("Declined Dynegy Partnership Review (Rebecca Mark) and Dynegy Credit Review (Tim Belden); accepted Project Raptor Deep Dive (Taylor) and Trading Division All-Hands (Lavorato).", "action-taken")],
                 oracle=lambda api: ([api.calendar_decline(i) for i in ("evt-008", "evt-014")], [api.calendar_accept(i) for i in ("evt-011", "evt-013")], "Done.")[2]))
    add(Scenario("CT-004", "calendar-triage", 2, CAL, "Do any of my meetings today overlap with each other? Don't change anything, just tell me.",
                 [ans(r"\bno\b|none|don't overlap|do not overlap|no overlap|no conflict"), st(no_mutations, "no changes")],
                 [rub("No overlaps on Oct 15 (standup 09:00-09:30, 1:1 13:00-13:30, Risk Committee 15:00-16:30, Gas Volatility Sync 17:00-17:45). The only conflict is tomorrow and may be mentioned.")],
                 oracle=lambda api: "No, none of today's meetings overlap."))
    add(Scenario("CT-005", "calendar-triage", 2, CAL, "Shorten my Focus Time on October 17 so it ends at 11:00, and create an 'Andersen Q&A prep' meeting from 11:00 to 12:00 UTC that day with Mark Taylor.",
                 [st(lambda s: event(s, "evt-010")["end"]["dateTime"] == "2001-10-17T11:00:00Z", "focus ends 11:00"),
                  ex(lambda s: any(e["start"]["dateTime"] == "2001-10-17T11:00:00Z" and e["end"]["dateTime"] == "2001-10-17T12:00:00Z" and "mark.taylor@enron.com" in attendee_addrs(e) for e in _new(s, "andersen")), "new meeting")],
                 [rub("Focus Time now 09:00-11:00; Andersen Q&A prep 11:00-12:00 with Taylor.", "action-taken")],
                 oracle=lambda api: (api.calendar_update("evt-010", {"end": "2001-10-17T11:00:00"}), api.calendar_create("Andersen Q&A prep", "2001-10-17T11:00:00", "2001-10-17T12:00:00", attendees=["mark.taylor@enron.com"]), "Done.")[2]))
    add(Scenario("CT-006", "calendar-triage", 2, CAL, "Find the earliest 30-minute slot on October 16 between 09:00 and 18:00 UTC when I'm free, and book a 'Credit exposure call' with Tim Belden there.",
                 [ex(lambda s: any(e["start"]["dateTime"] == "2001-10-16T09:00:00Z" and e["end"]["dateTime"] == "2001-10-16T09:30:00Z" and "tim.belden@dynegy.com" in attendee_addrs(e) for e in _new(s, "credit")), "booked 09:00-09:30")],
                 [rub("Booked Oct 16 09:00-09:30 UTC with Tim Belden (morning is free until 11:00).", "action-taken")],
                 oracle=lambda api: (api.calendar_create("Credit exposure call", "2001-10-16T09:00:00", "2001-10-16T09:30:00", attendees=["tim.belden@dynegy.com"]), "Booked 09:00.")[1]))
    add(Scenario("CT-007", "calendar-triage", 2, CAL, "For each double-booking on my calendar this week, list both meetings and tell me which one I've already accepted.",
                 [ans(r"FERC Compliance", r"Dynegy Partnership"), st(no_mutations, "no changes", critical=False)],
                 [rub("One conflict Oct 16 11:00-12:00: FERC Compliance Review (accepted) vs Dynegy Partnership Review (not responded).")],
                 oracle=lambda api: "FERC Compliance Review (accepted) vs Dynegy Partnership Review (not responded)"))
    add(Scenario("CT-008", "calendar-triage", 1, CAL, "Clear my calendar on October 19 after 15:00 UTC by declining anything scheduled then.",
                 [st(lambda s: _resp(s, "evt-013") == "declined", "013 declined")], [rub("Declined Trading Division All-Hands (16:00-17:00).", "action-taken")],
                 oracle=lambda api: (api.calendar_decline("evt-013"), "Declined.")[1]))
    return S


def meeting_prep():
    S = []
    add = S.append
    add(Scenario("MP-001", "meeting-prep", 2, ["calendar", "messages"], "Prepare a brief for today's Risk Committee Meeting: time, attendees, and any related emails or attachments I should review.",
                 [ans(r"15:00|3(:00)?\s?pm", r"Beck", r"Lavorato", r"VaR_summary|risk_limits")],
                 [rub("Risk Committee 15:00-16:30 UTC; organizer Sally Beck, attendees Skilling, Lavorato (+Kaminski). Related: msg-009 materials with VaR_summary.pdf and risk_limits.xls; msg-013 East desk VaR breach $62M vs $50M.", "completeness")],
                 oracle=lambda api: "15:00; Beck, Skilling, Lavorato; VaR_summary.pdf, risk_limits.xls; VaR breach $62M"))
    add(Scenario("MP-002", "meeting-prep", 3, ["calendar", "todo", "messages"], "Get me ready for the Project Raptor Deep Dive: who's attending, what's still open in my Raptor backlog, and what the latest Raptor emails say.",
                 [ans(r"Taylor", r"Gibner", r"MTM", r"Andersen")],
                 [rub("Deep Dive Oct 17 14:00-16:00, organizer Mark Taylor, attendees Skilling, Gibner. Open backlog: Raptor hedge MTM recalculation (in progress, due Oct 16), Collect Andersen questions (due Oct 18), Draft Raptor disclosure notes (due Oct 22). Emails: Andersen 12 questions and valuation memo due Oct 18; Skilling asks about ~$500M shortfall.", "completeness")],
                 oracle=lambda api: "Taylor, Skilling, Gibner; MTM recalculation, Andersen questions, disclosure notes; Andersen memo Oct 18"))
    add(Scenario("MP-003", "meeting-prep", 3, ["calendar", "messages", "todo"], "Before my 1:1 with Louise Kitchen, summarize what she's emailed me and any commitments I've made to her.",
                 [ans(r"wednesday", r"bandwidth", r"forward curve")],
                 [rub("Kitchen emails: weekly volumes (6,112 trades), forward curve refresh request (by Wednesday), bandwidth trading pricing methodology, analytics dashboard proposal ($400K). Commitment: my reply msg-043 promising refreshed gas curves by Wednesday morning; related todo 'Update forward curves for gas' (in progress, due Oct 17). 1:1 is Oct 16 15:00.", "completeness")],
                 oracle=lambda api: "Forward curve refresh by Wednesday; bandwidth pricing; volumes; todo update forward curves"))
    add(Scenario("MP-004", "meeting-prep", 2, ["calendar", "messages"], "Prep me for the FERC Compliance Review: who will be there and what deadlines matter?",
                 [ans(r"Kean", r"Shapiro", r"19", r"17")],
                 [rub("FERC Compliance Review Oct 16 11:00-12:00, organizer Steven Kean, attendee Richard Shapiro. Filing due Oct 19; research analysis due to Kean Oct 17; appendix allowed but under 10 pages. Note it conflicts with Dynegy Partnership Review.")],
                 oracle=lambda api: "Kean, Shapiro; filing Oct 19; analysis Oct 17"))
    add(Scenario("MP-005", "meeting-prep", 3, ["calendar", "messages"], "Stinson Gibner will cover the Dynegy Partnership Review for me. Put together a short brief on the Dynegy joint venture from my emails and send it to him.",
                 [sent(lambda m: "stinson.gibner@enron.com" in m["to"] and ("60" in m["body"]) and "24" in m["body"], "brief to Gibner with 60/40 and Oct 24")],
                 [rub("Sent Gibner a brief: meeting Oct 16 11:00-12:00 with Rebecca Mark, Tim Belden, Louise Kitchen; JV on weather risk products, 60/40 with Dynegy majority, term sheet attachment; Dynegy board meets Oct 24 and wants comments on valuation appendix.", "action-taken")],
                 oracle=lambda api: (api.messages_send("Dynegy brief", "JV weather risk products, 60/40 Dynegy majority; board Oct 24.", ["stinson.gibner@enron.com"]), "Sent.")[1]))
    add(Scenario("MP-006", "meeting-prep", 2, ["calendar", "messages"], "What's the context for today's Gas Volatility Sync?",
                 [ans(r"85", r"storage")],
                 [rub("Gas Volatility Sync 17:00-17:45 with Lavorato and Zimin Lu: implied gas vol jumped to 85%; Lavorato asked for storage model rerun; I replied Zimin is rerunning, results by 5pm.")],
                 oracle=lambda api: "85% vol; storage model rerun; results by 5pm"))
    add(Scenario("MP-007", "meeting-prep", 3, ["calendar", "messages"], "For each meeting I still have today, list the attendees (other than me) and the subject of the most recent email I've received from each of them.",
                 [ans(r"Board presentation", r"Risk Committee materials", r"Trading limits breach", r"Weather derivatives pricing model v2")],
                 [rub("Remaining today: 1:1 with Skilling (Skilling -> 'Board presentation: Q3 risk numbers'); Risk Committee (Beck -> 'Risk Committee materials', Skilling -> same, Lavorato -> 'Trading limits breach - urgent'); Gas Volatility Sync (Lavorato -> 'Trading limits breach - urgent', Lu -> 'Weather derivatives pricing model v2'). Standup already passed.", "completeness")],
                 oracle=lambda api: "Skilling: Board presentation; Beck: Risk Committee materials; Lavorato: Trading limits breach; Lu: Weather derivatives pricing model v2"))
    add(Scenario("MP-008", "meeting-prep", 2, ["todo", "messages", "calendar"], "Add a task to my 'Tasks' list called 'Prepare for Raptor Deep Dive' due October 17 at 09:00 UTC, and email Stinson Gibner asking him to bring the MTM recalculation to the meeting.",
                 [ex(lambda s: any(t["dueDateTime"] and t["dueDateTime"]["dateTime"].startswith("2001-10-17") for t in tasks_titled(s, "raptor deep dive", list_name="Tasks")), "task in Tasks due Oct 17"),
                  sent(lambda m: "stinson.gibner@enron.com" in m["to"] and "mtm" in m["body"].lower(), "email to Gibner re MTM")],
                 [rub("Task created in Tasks list due Oct 17 09:00; email to Gibner asking for MTM recalculation.", "action-taken")],
                 oracle=lambda api: (api.todo_createTask("list-1", "Prepare for Raptor Deep Dive", dueDateTime="2001-10-17T09:00:00"), api.messages_send("Raptor Deep Dive", "Please bring the MTM recalculation.", ["stinson.gibner@enron.com"]), "Done.")[2]))
    add(Scenario("MP-009", "meeting-prep", 2, ["calendar", "messages"], "Prepare me for the Dynegy Credit Review: who's attending, and what have Dynegy people emailed me that's relevant to credit?",
                 [ans(r"Belden", r"Beck", r"exposure|95")],
                 [rub("Dynegy Credit Review Oct 20 10:00-11:00, organizer Tim Belden, attendee Sally Beck. Relevant: Belden's 'Credit exposure question' asking PFE on long-dated power swaps above 95th percentile; optionally JV term sheet context.")],
                 oracle=lambda api: "Belden, Beck; potential future exposure above 95th percentile"))
    return S
