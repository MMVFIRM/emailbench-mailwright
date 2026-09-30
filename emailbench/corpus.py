"""Deterministic synthetic Kaminski corpus, reconstructed from EmailBench Appendix O.

Everything is anchored to REFERENCE_TIME (2001-10-15T10:00:00Z, a Monday).
Nothing here is an original Enron email; bodies are fabricated.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

REFERENCE_TIME = datetime(2001, 10, 15, 10, 0, 0, tzinfo=timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hours_ago(h: float) -> str:
    return iso(REFERENCE_TIME - timedelta(hours=h))


# ---------------------------------------------------------------- people
ME = {"name": "Vince Kaminski", "address": "vkamins@enron.com"}

USERS = {
    "me": dict(name="Vince Kaminski", address="vkamins@enron.com", dept="Research", title="VP & Head of Research", company="Enron Corp"),
    "skilling": dict(name="Jeff Skilling", address="jeff.skilling@enron.com", dept="Executive", title="President & COO", company="Enron Corp"),
    "kitchen": dict(name="Louise Kitchen", address="louise.kitchen@enron.com", dept="Trading", title="Pres., EnronOnline", company="Enron Corp"),
    "beck": dict(name="Sally Beck", address="sally.beck@enron.com", dept="Operations", title="VP Operations", company="Enron Corp"),
    "lavorato": dict(name="John Lavorato", address="john.lavorato@enron.com", dept="Trading", title="CEO, Enron Americas", company="Enron Corp"),
    "shapiro": dict(name="Richard Shapiro", address="richard.shapiro@enron.com", dept="Gov. Affairs", title="VP Gov. Affairs", company="Enron Corp"),
    "kean": dict(name="Steven Kean", address="steven.kean@enron.com", dept="Executive", title="VP & Chief of Staff", company="Enron Corp"),
    "taylor": dict(name="Mark Taylor", address="mark.taylor@enron.com", dept="Legal", title="VP & Gen. Counsel", company="Enron Corp"),
    "lay": dict(name="Kenneth Lay", address="kenneth.lay@enron.com", dept="Executive", title="Chairman & CEO", company="Enron Corp"),
    "gibner": dict(name="Stinson Gibner", address="stinson.gibner@enron.com", dept="Research", title="Senior Analyst", company="Enron Corp"),
    "lu": dict(name="Zimin Lu", address="zimin.lu@enron.com", dept="Research", title="Quant. Analyst", company="Enron Corp"),
    "belden": dict(name="Tim Belden", address="tim.belden@dynegy.com", dept="Trading", title="VP Western Trading", company="Dynegy"),
    "mark": dict(name="Rebecca Mark", address="rebecca.mark@dynegy.com", dept="Development", title="VP Bus. Dev.", company="Dynegy"),
    "eol": dict(name="EnronOnline System", address="system@enrononline.com", dept=None, title="(bot)", company="EnronOnline"),
    "legal": dict(name="Legal Ticketing", address="legal-tickets@enron.com", dept=None, title="(bot)", company="Enron Corp"),
    "gasbank": dict(name="GasBank Platform", address="alerts@gasbank.enron.com", dept=None, title="(bot)", company="Enron Corp"),
}
AUTOMATED_SENDERS = {"system@enrononline.com", "legal-tickets@enron.com", "alerts@gasbank.enron.com"}


def _addr(key):
    u = USERS[key]
    return {"emailAddress": {"name": u["name"], "address": u["address"]}}


# ---------------------------------------------------------------- folders
FOLDERS = [
    dict(id="folder-inbox", displayName="Inbox", parentFolderId=None, wellKnownName="inbox"),
    dict(id="folder-sent", displayName="Sent Items", parentFolderId=None, wellKnownName="sentitems"),
    dict(id="folder-drafts", displayName="Drafts", parentFolderId=None, wellKnownName="drafts"),
    dict(id="folder-deleted", displayName="Deleted Items", parentFolderId=None, wellKnownName="deleteditems"),
    dict(id="folder-archive", displayName="Archive", parentFolderId=None, wellKnownName="archive"),
    dict(id="folder-junk", displayName="Junk Email", parentFolderId=None, wellKnownName="junkemail"),
]

LABELS = [
    dict(id="label-1", displayName="Urgent", color="preset0"),
    dict(id="label-2", displayName="Raptor", color="preset1"),
    dict(id="label-3", displayName="FERC", color="preset3"),
    dict(id="label-4", displayName="Research", color="preset4"),
    dict(id="label-5", displayName="Dynegy", color="preset7"),
    dict(id="label-6", displayName="Personal", color="preset8"),
]

# ---------------------------------------------------------------- messages
# (seq, sender, to, cc, subject, body, hoursAgo, importance, conversationId, attachments, flagged, categories)
_INCOMING = [
    (1, "skilling", ["me"], [], "Board presentation: Q3 risk numbers",
     "Vince, I need the Q3 value-at-risk numbers for the board deck by Wednesday noon. Please include the trading-book breakdown and the stress-test results.",
     2, "high", None, [], False, ["Urgent"]),
    (2, "gibner", ["me"], ["lu"], "Monte Carlo simulation parameters",
     "I propose 50,000 paths with antithetic variates for the gas storage model. Mean reversion speed estimated at 2.3 per year. Let me know if you agree.",
     3, "normal", "conv-montecarlo", [], False, ["Research"]),
    (3, "eol", ["me"], [], "Trade confirmation #EOL-88213",
     "Automated confirmation: 10,000 MMBtu Henry Hub natural gas, November delivery, fixed price $2.41. Counterparty: Reliant Energy.",
     4, "normal", None, [], False, []),
    (4, "kitchen", ["me"], [], "EnronOnline volumes - weekly summary",
     "EnronOnline transacted 6,112 trades last week with notional value of $3.2 billion. Gas products remain 58% of volume.",
     5, "normal", None, [], False, []),
    (5, "lu", ["me"], [], "Weather derivatives pricing model v2",
     "Attached is version 2 of the heating-degree-day pricing model. Backtest error dropped from 7.4% to 4.1% after the new temperature smoothing.",
     6, "normal", "conv-weather", ["weather_model_v2.xls"], False, ["Research"]),
    (6, "lay", ["me"], [], "All-employee meeting follow-up",
     "Thank you for attending the all-employee meeting. Please send me a short note on how the research group supports the trading businesses before Friday.",
     9, "high", None, [], False, []),
    (7, "legal", ["me"], [], "Ticket LT-4471: NDA review assigned",
     "Ticket LT-4471 has been assigned to you: review the mutual NDA with Citadel Investment Group. SLA: 5 business days.",
     10, "normal", None, [], False, []),
    (8, "kean", ["me"], ["shapiro"], "FERC filing deadline - action needed",
     "The FERC quarterly market-behavior filing is due October 19. I need your group's price-formation analysis by October 17 so legal can review it.",
     12, "high", "conv-ferc", [], True, ["FERC"]),
    (9, "beck", ["me"], [], "Risk Committee materials",
     "Attached are the Risk Committee materials for today's meeting at 15:00, including the VaR summary and the updated risk limits.",
     14, "normal", None, ["VaR_summary.pdf", "risk_limits.xls"], False, []),
    (10, "taylor", ["me"], ["skilling"], "Raptor SPE structure - legal review",
     "Vince, attached is the current structure chart for the Raptor vehicles. Legal needs your view on whether the hedge valuations are supportable.",
     16, "normal", "conv-raptor", ["raptor_structure.pdf"], False, ["Raptor"]),
    (11, "belden", ["me"], [], "Western power price curves",
     "Our western power forward curves for Q1 2002 are attached in the shared drive. Palo Verde peak is marked at $38.50/MWh.",
     18, "normal", None, [], False, []),
    (12, "gasbank", ["me"], [], "GasBank daily position alert",
     "Daily position alert: net long 4.2 Bcf across GasBank storage contracts. No limit breaches detected.",
     20, "normal", None, [], False, []),
    (13, "lavorato", ["me"], [], "Trading limits breach - urgent",
     "The East desk breached its VaR limit yesterday: $62 million against a $50 million limit. I need your team to verify the model inputs today.",
     22, "high", None, [], True, ["Urgent"]),
    (14, "shapiro", ["kean"], ["me"], "Regulatory update: California market",
     "Summary of the California ISO price-cap changes effective November 1. Research should review the impact on our western positions.",
     24, "normal", None, [], False, []),
    (15, "skilling", ["me"], [], "Raptor hedge valuation",
     "What is your current estimate of the credit capacity shortfall in the Raptor hedges? I heard numbers around $500 million and want your independent view.",
     26, "normal", "conv-raptor", [], False, ["Raptor"]),
    (16, "eol", ["me"], [], "Trade confirmation #EOL-88190",
     "Automated confirmation: 25 MW PJM West on-peak power, December delivery, fixed price $31.75/MWh. Counterparty: Constellation.",
     28, "normal", None, [], False, []),
    (17, "gibner", ["me"], ["lu"], "Re: Monte Carlo simulation parameters",
     "Update: with 50,000 paths the standard error is 0.8%. Going to 100,000 paths only brings it to 0.6%, so I suggest we keep 50,000.",
     30, "normal", "conv-montecarlo", [], False, ["Research"]),
    (18, "mark", ["me"], [], "Dynegy joint venture term sheet",
     "Attached is the draft term sheet for the Dynegy joint venture on weather risk products. We propose a 60/40 split with Dynegy as the majority partner.",
     32, "normal", "conv-dynegy", ["JV_term_sheet.docx"], False, ["Dynegy"]),
    (19, "kitchen", ["me"], [], "Forward curve update request",
     "Could your team refresh the natural gas forward curves for EnronOnline by Wednesday? Traders see a gap versus NYMEX settlement prices.",
     34, "normal", None, [], False, []),
    (20, "lu", ["me"], [], "Re: Weather derivatives pricing model v2",
     "Follow-up on the weather model: I added Chicago and Atlanta stations. The model now covers 14 weather stations.",
     36, "normal", "conv-weather", [], False, ["Research"]),
    (21, "beck", ["me"], [], "VaR model review schedule",
     "Internal audit wants to schedule the annual VaR model review. Proposed window is October 22 through October 26. Attached is the review calendar.",
     38, "normal", None, ["review_calendar.xls"], False, []),
    (22, "taylor", ["me"], [], "Re: Raptor SPE structure - legal review",
     "Following up: Arthur Andersen asked for the valuation memo by October 18. Can your team draft it?",
     40, "normal", "conv-raptor", [], False, ["Raptor"]),
    (23, "kean", ["me"], [], "Re: FERC filing deadline",
     "Correction: the FERC staff confirmed the filing may include an appendix with model methodology. Keep it under 10 pages.",
     42, "normal", "conv-ferc", [], False, ["FERC"]),
    (24, "legal", ["me"], [], "Ticket LT-4480: URGENT compliance hold",
     "Ticket LT-4480: a document-retention compliance hold has been issued for the trading analytics group. Do not delete any research files.",
     44, "high", None, [], False, []),
    (25, "belden", ["me"], [], "Credit exposure question",
     "What is your group's current estimate of potential future exposure on our long-dated power swaps? Credit wants a number above the 95th percentile.",
     45, "normal", None, [], False, []),
    (26, "lay", ["me"], [], "Quarterly strategy offsite",
     "The quarterly strategy offsite is confirmed for November 5 at the Woodlands. Please prepare a 15-minute segment on quantitative risk.",
     46, "normal", None, [], False, []),
    (27, "lavorato", ["me"], [], "Gas volatility spike - need model run",
     "Implied gas volatility jumped to 85%. Please rerun the storage valuation model with the new vol surface and send results today.",
     48, "high", None, [], True, ["Urgent"]),
    (28, "shapiro", ["me"], [], "Energy Risk Conference registration",
     "You are registered for the Energy Risk Conference in Houston, October 22-23. Your panel on price-spike modeling is on October 22 at 14:00.",
     50, "normal", None, [], False, []),
    (29, "skilling", ["me"], [], "Research group headcount",
     "How many analysts are currently in the research group, and do you need additional headcount for 2002?",
     52, "normal", "conv-headcount", [], False, []),
    (30, "mark", ["me"], ["belden"], "Re: Dynegy joint venture term sheet",
     "Following up on the term sheet: our board meets October 24. We would like your comments on the valuation appendix before then.",
     54, "normal", "conv-dynegy", [], False, ["Dynegy"]),
    (31, "kitchen", ["me"], [], "EnronOnline new product launch",
     "We plan to launch bandwidth trading on EnronOnline next month. Can research provide a pricing methodology for bandwidth swaps?",
     56, "normal", None, [], False, []),
    (32, "gibner", ["me"], [], "Credit model calibration results",
     "Calibration of the credit model is complete. Default correlation estimated at 0.27; results attached.",
     58, "normal", None, ["calibration_results.xls"], False, ["Research"]),
    (33, "lu", ["me"], [], "Spread option pricing question",
     "For spark spread options, should we use the Margrabe formula or the two-factor Monte Carlo? The heat rate is 10,500 Btu/kWh.",
     60, "normal", None, [], False, []),
    (34, "beck", ["me"], [], "Operations: settlement discrepancies",
     "Operations found 23 settlement discrepancies in September, totaling $1.4 million. Some may relate to curve mismatches from research.",
     62, "normal", None, [], False, []),
    (35, "taylor", ["me"], [], "Raptor: Arthur Andersen questions",
     "Arthur Andersen sent a list of 12 questions on the Raptor collars. I have forwarded them to your team; answers are needed by October 18.",
     64, "normal", "conv-raptor", [], False, ["Raptor"]),
    (36, "lay", ["me"], [], "Board meeting prep",
     "For the October board meeting please prepare a one-page summary of market risk exposures. Keep it non-technical.",
     70, "high", None, [], False, []),
    (37, "kean", ["me"], [], "Press inquiry: research group",
     "The Wall Street Journal asked about our quantitative research group. Please do not speak to reporters; route questions to me.",
     72, "normal", None, [], False, []),
    (38, "skilling", ["me"], [], "Re: Research group headcount",
     "Following up on headcount: HR approved two additional analyst positions for Q1 2002.",
     74, "normal", "conv-headcount", [], False, []),
    (39, "gasbank", ["me"], [], "GasBank: margin call warning",
     "Margin call warning: collateral requirement on NYMEX positions increased by $18 million. Treasury has been notified.",
     76, "high", None, [], False, []),
    (40, "lavorato", ["me"], [], "Trading floor lunch Friday",
     "Lunch for the trading floor on Friday at noon. Research team is welcome to join.",
     80, "normal", None, [], False, []),
]

_SENT = [
    (41, ["skilling"], [], "Re: Board presentation: Q3 risk numbers", "Jeff, I will have the Q3 VaR numbers to you by Tuesday evening.", 1),
    (42, ["lu"], [], "Weather model review comments", "Zimin, nice work on v2. Please document the smoothing method before we release it.", 7),
    (43, ["kitchen"], [], "Re: Forward curve update request", "Louise, we will refresh the gas curves by Wednesday morning.", 30),
    (44, ["beck"], [], "Re: VaR model review schedule", "Sally, October 22-26 conflicts with the Energy Risk Conference. Could we start October 24?", 35),
    (45, ["lavorato"], [], "Re: Gas volatility spike - need model run", "John, Zimin is rerunning the storage model now; results by 5pm.", 47),
    (46, ["gibner"], ["lu"], "Research team priorities for Q4", "Priorities for Q4: weather model release, credit model validation, and FERC analysis support.", 50),
    (47, ["taylor"], [], "Raptor valuation assumptions", "Mark, attached are the valuation assumptions we used for the Raptor collars.", 60),
    (48, ["kean"], [], "Research group press talking points", "Steve, understood on press contacts. Here are three talking points if needed.", 70),
    (49, ["shapiro"], [], "California market model", "Rick, our California market model is being updated for the new price caps.", 90),
    (50, ["belden"], [], "Price curve methodology", "Tim, here is a short description of our forward curve methodology.", 100),
    (51, ["mark"], [], "JV: research support", "Rebecca, research can support the joint venture valuation work starting next month.", 110),
    (52, ["skilling"], [], "Weekly research summary", "Weekly summary: weather model v2 in testing, credit model calibrated, storage model rerun pending.", 120),
    (53, ["lay"], [], "Research group overview for board", "Ken, attached is a one-page overview of the research group's work.", 130),
    (54, ["lu", "gibner"], [], "Team offsite agenda", "Draft agenda for the research team offsite: model validation standards and 2002 planning.", 140),
    (55, ["beck"], [], "Risk Committee deck feedback", "Sally, a few comments on the Risk Committee deck: the stress scenarios need a longer horizon.", 150),
]
_SENT_ATTACH = {47: ["raptor_assumptions.xls"]}

_OLDER = [  # daysAgo
    (56, "skilling", "Q2 research review", "Good Q2 review. Let us discuss the 2002 research budget next month.", 10, "normal", None),
    (57, "kitchen", "EnronOnline analytics proposal", "Proposal for a real-time analytics dashboard on EnronOnline order flow. Budget estimate $400,000.", 12, "normal", None),
    (58, "gibner", "Summer intern projects", "Summary of the summer intern projects: two on weather hedging, one on credit scoring.", 14, "normal", None),
    (59, "lu", "Conference paper draft", "Attached is the conference paper draft on mean-reverting jump diffusion, with figures.", 16, "normal", None),
    (60, "beck", "Audit request: model inventory", "Internal audit needs a complete inventory of pricing models in production. Please send by end of month.", 18, "normal", None),
    (61, "lavorato", "Year-end review process", "Year-end review forms are due December 1. Please complete reviews for your direct reports.", 20, "low", None),
    (62, "shapiro", "FERC Order 2000 summary", "Summary of FERC Order 2000 on regional transmission organizations and what it means for our power trading.", 22, "normal", None),
    (63, "taylor", "Contract template update", "Legal updated the ISDA schedule template. Please use the new version for all research-supported deals.", 25, "normal", None),
    (64, "belden", "Western trading desk intro", "Introducing the western trading desk team. We look forward to working with research.", 30, "normal", None),
    (65, "kean", "Welcome to the fall planning cycle", "The fall planning cycle begins now. Department plans are due November 15.", 40, "low", None),
]
_OLDER_ATTACH = {59: ["conference_paper_draft.doc", "figures.pdf"], 62: ["FERC_Order2000.pdf"]}


def _mid(seq):
    return f"msg-{seq:03d}"


def build_messages():
    msgs = []
    for (seq, snd, to, cc, subj, body, h, imp, conv, att, flagged, cats) in _INCOMING:
        msgs.append(dict(
            id=_mid(seq), subject=subj, body=body, sender=_addr(snd)["emailAddress"],
            toRecipients=[_addr(k) for k in to], ccRecipients=[_addr(k) for k in cc],
            receivedDateTime=hours_ago(h), sentDateTime=hours_ago(h), isRead=(seq % 3 != 0),
            importance=imp, conversationId=conv or f"conv-{seq:03d}", parentFolderId="folder-inbox",
            attachments=[dict(id=f"att-{seq:03d}-{i+1}", name=n) for i, n in enumerate(att)],
            flag={"flagStatus": "flagged" if flagged else "notFlagged"}, categories=list(cats), isDraft=False,
        ))
    for (seq, to, cc, subj, body, h) in _SENT:
        att = _SENT_ATTACH.get(seq, [])
        msgs.append(dict(
            id=_mid(seq), subject=subj, body=body, sender=dict(ME),
            toRecipients=[_addr(k) for k in to], ccRecipients=[_addr(k) for k in cc],
            receivedDateTime=hours_ago(h), sentDateTime=hours_ago(h), isRead=True, importance="normal",
            conversationId=f"conv-{seq:03d}", parentFolderId="folder-sent",
            attachments=[dict(id=f"att-{seq:03d}-{i+1}", name=n) for i, n in enumerate(att)],
            flag={"flagStatus": "notFlagged"}, categories=[], isDraft=False,
        ))
    for (seq, snd, subj, body, d, imp, conv) in _OLDER:
        att = _OLDER_ATTACH.get(seq, [])
        msgs.append(dict(
            id=_mid(seq), subject=subj, body=body, sender=_addr(snd)["emailAddress"],
            toRecipients=[_addr("me")], ccRecipients=[],
            receivedDateTime=hours_ago(24 * d), sentDateTime=hours_ago(24 * d), isRead=(seq % 3 != 0),
            importance=imp, conversationId=conv or f"conv-{seq:03d}", parentFolderId="folder-inbox",
            attachments=[dict(id=f"att-{seq:03d}-{i+1}", name=n) for i, n in enumerate(att)],
            flag={"flagStatus": "notFlagged"}, categories=[], isDraft=False,
        ))
    for m in msgs:
        m["from"] = {"emailAddress": dict(m.pop("sender"))}
        m["hasAttachments"] = bool(m["attachments"])
    return msgs


# ---------------------------------------------------------------- calendar
def _at(day, hh, mm=0):
    return iso(datetime(2001, 10, day, hh, mm, tzinfo=timezone.utc))


def _att(keys, status="accepted"):
    return [dict(emailAddress=dict(name=USERS[k]["name"], address=USERS[k]["address"]),
                 type="required", status=dict(response=status)) for k in keys]


_EVENTS = [
    ("evt-001", "Project Raptor Kick-off", 8, (14, 0), (15, 0), "EB 50M", "skilling", ["taylor", "gibner"], "accepted", "Kick-off for the Raptor hedge valuation review."),
    ("evt-002", "Q3 Trading Retrospective", 12, (15, 0), (16, 30), "EB 30C1", "lavorato", ["kitchen", "beck"], "accepted", "Review of Q3 trading results and risk events."),
    ("evt-003", "Research Team Standup", 15, (9, 0), (9, 30), "EB 1972", "me", ["gibner", "lu", "skilling"], "organizer", "Weekly research standup."),
    ("evt-004", "1:1 with Skilling", 15, (13, 0), (13, 30), "EB 50M", "skilling", [], "accepted", "Monthly one-on-one."),
    ("evt-005", "Risk Committee Meeting", 15, (15, 0), (16, 30), "EB 49C2", "beck", ["skilling", "lavorato"], "accepted", "Monthly Risk Committee: VaR, limits, stress tests."),
    ("evt-006", "Gas Volatility Sync", 15, (17, 0), (17, 45), "EB 3321", "lavorato", ["lu"], "tentativelyAccepted", "Discuss implied volatility spike and storage model rerun."),
    ("evt-007", "FERC Compliance Review", 16, (11, 0), (12, 0), "EB 47C1", "kean", ["shapiro"], "accepted", "Review draft FERC market-behavior filing."),
    ("evt-008", "Dynegy Partnership Review", 16, (11, 0), (12, 0), "Dynegy HQ / dial-in", "mark", ["belden", "kitchen"], "notResponded", "Review joint venture term sheet with Dynegy."),
    ("evt-009", "1:1 with Kitchen", 16, (15, 0), (15, 30), "EB 30C1", "kitchen", [], "accepted", "EnronOnline analytics and forward curves."),
    ("evt-010", "Focus Time", 17, (9, 0), (12, 0), None, "me", [], "organizer", "Blocked for FERC price-formation analysis."),
    ("evt-011", "Project Raptor Deep Dive", 17, (14, 0), (16, 0), "EB 50M", "taylor", ["skilling", "gibner"], "notResponded", "Deep dive on Raptor collar valuations for Andersen."),
    ("evt-012", "Team Lunch at Pappadeaux", 18, (12, 0), (13, 30), "Pappadeaux Seafood Kitchen", "me", ["gibner", "lu"], "organizer", "Research team lunch."),
    ("evt-013", "Trading Division All-Hands", 19, (16, 0), (17, 0), "Enron Tower Auditorium", "lavorato", ["kitchen", "beck"], "notResponded", "Quarterly all-hands for the trading division."),
    ("evt-014", "Dynegy Credit Review", 20, (10, 0), (11, 0), "Dial-in", "belden", ["beck"], "notResponded", "Credit exposure review with Dynegy."),
]


def build_events():
    evs = []
    for (eid, subj, day, s, e, loc, org, others, my_status, body) in _EVENTS:
        attendees = _att(others)
        if org != "me":
            attendees = _att([org], "organizer") + attendees
        evs.append(dict(
            id=eid, subject=subj, body=body,
            start=dict(dateTime=_at(day, *s), timeZone="UTC"), end=dict(dateTime=_at(day, *e), timeZone="UTC"),
            location=dict(displayName=loc or ""), isAllDay=False,
            organizer=dict(emailAddress=dict(name=USERS[org]["name"], address=USERS[org]["address"])),
            attendees=attendees, responseStatus=dict(response=my_status), isCancelled=False,
            showAs="busy",
        ))
    evs.append(dict(
        id="evt-015", subject="Energy Risk Conference", body="Annual Energy Risk Conference. Panel on price-spike modeling Oct 22 14:00.",
        start=dict(dateTime=_at(22, 0), timeZone="UTC"), end=dict(dateTime=_at(24, 0), timeZone="UTC"),
        location=dict(displayName="Hyatt Regency Houston"), isAllDay=True,
        organizer=dict(emailAddress=dict(name=USERS["shapiro"]["name"], address=USERS["shapiro"]["address"])),
        attendees=_att(["shapiro"], "organizer"), responseStatus=dict(response="accepted"), isCancelled=False, showAs="oof",
    ))
    return evs


# ---------------------------------------------------------------- contacts
def build_contacts():
    out = []
    keys = ["skilling", "kitchen", "beck", "lavorato", "shapiro", "kean", "taylor", "lay", "gibner", "lu", "belden", "mark"]
    phones = ["713-853-6894", "713-853-7021", "713-853-5926", "713-853-7991", "713-853-3407", "713-853-1586",
              "713-853-7459", "713-853-6773", "713-853-4541", "713-853-6388", "503-464-3820", "713-507-6400"]
    for i, k in enumerate(keys):
        u = USERS[k]
        g, s = u["name"].split(" ", 1)
        out.append(dict(id=f"contact-{i+1:03d}", displayName=u["name"], givenName=g, surname=s,
                        emailAddresses=[dict(address=u["address"], name=u["name"])], companyName=u["company"],
                        department=u["dept"], jobTitle=u["title"], businessPhones=[phones[i]]))
    inst = [("Enron Treasury", "treasury@enron.com", "Enron Corp", "Treasury", "713-853-1000"),
            ("NYMEX Operations", "operations@nymex.com", "NYMEX", "Operations", "212-299-2000"),
            ("FERC Filings", "filings@ferc.gov", "FERC", "Office of the Secretary", "202-502-8400")]
    for j, (n, a, c, d, p) in enumerate(inst):
        out.append(dict(id=f"contact-{13+j:03d}", displayName=n, givenName=None, surname=None,
                        emailAddresses=[dict(address=a, name=n)], companyName=c, department=d, jobTitle=None,
                        businessPhones=[p]))
    return out


CONTACT_GROUPS = [
    dict(id="cg-1", displayName="Research Team", members=["stinson.gibner@enron.com", "zimin.lu@enron.com"]),
    dict(id="cg-2", displayName="Risk Committee", members=["sally.beck@enron.com", "jeff.skilling@enron.com", "john.lavorato@enron.com"]),
    dict(id="cg-3", displayName="Regulatory Affairs", members=["richard.shapiro@enron.com", "steven.kean@enron.com"]),
]


# ---------------------------------------------------------------- todo
def build_todo():
    lists = [dict(id="list-1", displayName="Tasks"), dict(id="list-2", displayName="Research Items"),
             dict(id="list-3", displayName="Project Raptor Backlog")]
    T = lambda i, lid, title, due, imp, status, body="": dict(
        id=f"task-{i:03d}", listId=lid, title=title, body=body,
        dueDateTime=(dict(dateTime=_at(*due), timeZone="UTC") if due else None),
        importance=imp, status=status)
    tasks = [
        T(1, "list-1", "Review VaR model backtest", (16, 17), "high", "notStarted", "Check the 250-day backtest exceptions."),
        T(2, "list-1", "Update forward curves for gas", (17, 17), "normal", "inProgress", "Requested by Louise Kitchen."),
        T(3, "list-1", "Prepare Risk Committee slides", (15, 12), "high", "completed"),
        T(4, "list-1", "Submit expense report", (12, 17), "low", "notStarted"),
        T(5, "list-2", "SPE valuation methodology memo", (19, 17), "normal", "notStarted"),
        T(6, "list-2", "Weather derivatives paper draft", (26, 17), "low", "inProgress"),
        T(7, "list-2", "Monte Carlo convergence study", None, "normal", "notStarted"),
        T(8, "list-3", "Raptor hedge MTM recalculation", (16, 17), "high", "inProgress"),
        T(9, "list-3", "Collect Andersen questions", (18, 17), "normal", "notStarted"),
        T(10, "list-3", "Draft Raptor disclosure notes", (22, 17), "normal", "notStarted"),
    ]
    return lists, tasks


BOARDS = [
    dict(id="board-1", displayName="Project Raptor", columns=["To Do", "In Progress", "Done"],
         tasks=[("Valuation memo", "To Do"), ("Andersen Q&A", "In Progress"), ("Collar MTM", "In Progress"), ("Kick-off", "Done")]),
    dict(id="board-2", displayName="Q4 Research Goals", columns=["Planned", "Active", "Complete"],
         tasks=[("Weather model release", "Active"), ("Credit model validation", "Planned"), ("FERC analysis", "Active")]),
]

FILTERS = [dict(id="filter-1", name="Auto-move EnronOnline trade confirmations", isEnabled=True, sequence=1,
                criteria=dict(fromAddresses=["system@enrononline.com"], subjectContains=["Trade confirmation"]),
                actions=dict(moveToFolder="folder-archive"))]

SETTINGS = dict(
    vacationResponder=dict(enabled=False, message="", startDateTime=None, endDateTime=None, sendToContactsOnly=False),
    senderClassifications=[dict(id="sc-1", senderEmailAddress="system@enrononline.com", classifyAs="other")],
    timeZone="UTC",
    workingHours=dict(start="08:00", end="18:00", days=["monday", "tuesday", "wednesday", "thursday", "friday"]),
)


def build_corpus():
    lists, tasks = build_todo()
    return copy.deepcopy(dict(
        reference_time=iso(REFERENCE_TIME), me=dict(ME, jobTitle="VP & Head of Research", department="Research",
                                                     officeLocation="Enron Tower, Floor 19", id="user-kaminski"),
        users=USERS, folders=FOLDERS, labels=LABELS, messages=build_messages(), events=build_events(),
        contacts=build_contacts(), contactGroups=CONTACT_GROUPS, todoLists=lists, todoTasks=tasks,
        boards=BOARDS, filters=FILTERS, settings=SETTINGS,
    ))
