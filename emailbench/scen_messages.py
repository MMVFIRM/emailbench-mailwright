"""messages-read (39) and messages-write (15) scenarios."""
from __future__ import annotations

from . import gt
from .scenario import (Scenario, ans, ans_not, msg, no_mutations, rub, sent, sent_to, st)

M = ["messages"]


def _subj(ids_):
    return "; ".join(f"{i} '{next(m['subject'] for m in gt.MSGS if m['id'] == i)}'" for i in ids_)


def messages_read():
    S = []
    add = S.append

    n_unread = len(gt.unread())
    add(Scenario("MR-001", "messages-read", 1, M, "How many unread emails do I have in my inbox?",
                 [ans(rf"\b{n_unread}\b")], [rub(f"States there are {n_unread} unread emails in the Inbox.")],
                 oracle=lambda api: f"You have {n_unread} unread emails in your inbox."))
    n_in = len(gt.inbox())
    add(Scenario("MR-002", "messages-read", 1, M, "How many emails are in my inbox in total, and how many of those are unread?",
                 [ans(rf"\b{n_in}\b", rf"\b{n_unread}\b")], [rub(f"Inbox total {n_in}, unread {n_unread}.")],
                 oracle=lambda api: f"{n_in} total, {n_unread} unread."))

    hu = gt.unread(gt.high())
    add(Scenario("MR-003", "messages-read", 2, M, "List my unread high-importance emails with sender and subject.",
                 [ans(*[r"lay", r"LT-4480|compliance hold", r"volatility", r"board meeting prep", r"margin call"])],
                 [rub(f"Lists exactly these {len(hu)} unread high-importance emails: {_subj(gt.ids(hu))}. No read or normal-importance emails.", "completeness")],
                 oracle=lambda api: "; ".join(f"{gt.sender_name(m)}: {m['subject']}" for m in hu)))

    sc = gt.sender_counts().most_common(2)
    top = gt.NAME[sc[0][0]]
    add(Scenario("MR-004", "messages-read", 2, M, "Who has sent me the most emails in my inbox, and how many?",
                 [ans(r"skilling", rf"\b{sc[0][1]}\b")], [rub(f"Top sender is {top} with {sc[0][1]} inbox emails (next highest is {sc[1][1]}).")],
                 oracle=lambda api: f"{top} with {sc[0][1]} emails."))

    add(Scenario("MR-005", "messages-read", 1, M, "What did John Lavorato ask me to do in his most recent email?",
                 [ans(r"verify|model inputs", r"\$?62")], [rub("Most recent Lavorato email is 'Trading limits breach - urgent' (msg-013): East desk breached VaR limit ($62M vs $50M limit); asks research to verify the model inputs today.")],
                 oracle=lambda api: "Verify the model inputs today; East desk breached VaR, $62 million vs $50 million limit."))

    att = [m for m in gt.inbox() if m["hasAttachments"]]
    add(Scenario("MR-006", "messages-read", 2, M, "Which emails in my inbox have attachments? Give the sender and the attachment file names.",
                 [ans(rf"\b{len(att)}\b|weather_model_v2", r"VaR_summary", r"JV_term_sheet", r"calibration_results", r"raptor_structure", r"review_calendar", r"FERC_Order2000", r"conference_paper_draft")],
                 [rub("Lists the 8 inbox emails with attachments: " + "; ".join(f"{m['id']} ({gt.sender_name(m)}): {', '.join(a['name'] for a in m['attachments'])}" for m in att), "completeness")],
                 oracle=lambda api: f"{len(att)} emails: " + "; ".join(f"{gt.sender_name(m)}: {', '.join(a['name'] for a in m['attachments'])}" for m in att)))

    add(Scenario("MR-007", "messages-read", 2, M, "Summarize the Monte Carlo simulation parameters thread. What was the final recommendation?",
                 [ans(r"50000|50k|50 000", r"0\.8\s?%")], [rub("Thread (msg-002, msg-017, Gibner): proposes 50,000 paths with antithetic variates, mean reversion 2.3/yr; follow-up: SE 0.8% at 50k vs 0.6% at 100k paths, recommends keeping 50,000 paths.")],
                 oracle=lambda api: "Gibner proposes 50,000 paths; SE 0.8% (100k gives 0.6%); keep 50,000."))

    rap = [m for m in gt.mentions("raptor", gt.inbox())]
    add(Scenario("MR-008", "messages-read", 2, M, "Summarize all the emails I've received about Raptor, including any deadlines.",
                 [ans(r"october 18|oct\.? 18|10/18|2001-10-18", r"andersen")],
                 [rub("Covers the 4 Raptor emails received: msg-010 (Taylor, structure chart, legal wants view on hedge valuations), msg-015 (Skilling, credit capacity shortfall ~$500 million), msg-022 (Taylor, Andersen wants valuation memo by Oct 18), msg-035 (Taylor, Andersen 12 questions on collars due Oct 18).", "completeness")],
                 oracle=lambda api: "Raptor: Taylor structure chart; Skilling $500 million shortfall; Andersen memo by October 18; 12 questions due October 18."))

    add(Scenario("MR-009", "messages-read", 1, M, "When is the FERC filing due, and by when does Steve Kean need our analysis?",
                 [ans(r"19", r"17")], [rub("Filing due October 19; Kean needs the price-formation analysis by October 17. (Follow-up: appendix allowed, under 10 pages.)")],
                 oracle=lambda api: "Filing due October 19; analysis needed by October 17."))

    w8 = gt.within_hours(8)
    add(Scenario("MR-010", "messages-read", 2, M, "How many emails did I receive in the last 8 hours? List them.",
                 [ans(rf"\b{len(w8)}\b")], [rub(f"{len(w8)} emails received in the last 8 hours (reference now 2001-10-15 10:00 UTC): {_subj(gt.ids(w8))}.", "completeness")],
                 oracle=lambda api: f"{len(w8)} emails: " + "; ".join(m["subject"] for m in w8)))

    cc = [m for m in gt.inbox() if any(r["emailAddress"]["address"] == "vkamins@enron.com" for r in m["ccRecipients"])]
    add(Scenario("MR-011", "messages-read", 2, M, "Which emails was I only cc'd on (not a direct recipient)?",
                 [ans(r"california")], [rub(f"Only {_subj(gt.ids(cc))} from Richard Shapiro (to Steven Kean, cc Kaminski).")],
                 oracle=lambda api: "Only 'Regulatory update: California market' from Richard Shapiro."))

    fl = [m for m in gt.MSGS if m["flag"]["flagStatus"] == "flagged"]
    add(Scenario("MR-012", "messages-read", 1, M, "Show me my flagged emails.",
                 [ans(r"FERC filing deadline", r"Trading limits breach", r"Gas volatility spike")],
                 [rub(f"Exactly {len(fl)} flagged: {_subj(gt.ids(fl))}.")],
                 oracle=lambda api: "; ".join(m["subject"] for m in fl)))

    rates = sorted([(a, u, t, p) for a, (u, t, p) in gt.unread_rates().items() if p > 50], key=lambda x: -x[3])
    add(Scenario("MR-013", "messages-read", 2, M, "For each sender who emailed me (including automated senders), calculate what percentage of their emails in my inbox are unread. Show only senders with >50% unread rate, sorted by unread percentage descending.",
                 [ans(r"100(\.0+)?\s?%", r"75(\.0+)?\s?%", r"66\.?[67]?\d*\s?%|67(\.0+)?\s?%"), ans(r"gasbank", r"rebecca|mark", r"beck", r"lay")],
                 [rub("Inbox-based unread rates >50%: " + ", ".join(f"{gt.NAME[a]} {u}/{t} = {p:.1f}%" for a, u, t, p in rates) + ". Sorted descending (the two 100% entries may be in either order). Nobody else exceeds 50%.")],
                 oracle=lambda api: "; ".join(f"{gt.NAME[a]}: {p:.1f}% ({u}/{t})" for a, u, t, p in rates)))

    add(Scenario("MR-014", "messages-read", 1, M, "What level did implied gas volatility jump to, according to my email?",
                 [ans(r"85\s?%")], [rub("85% (Lavorato, msg-027, requested storage model rerun).")], oracle=lambda api: "85%"))

    add(Scenario("MR-015", "messages-read", 2, M, "List the EnronOnline trade confirmations I received, with the counterparty and price for each.",
                 [ans(r"reliant", r"constellation", r"2\.41", r"31\.75")],
                 [rub("Two confirmations: #EOL-88213 (10,000 MMBtu Henry Hub gas, Nov, $2.41, Reliant Energy) and #EOL-88190 (25 MW PJM West on-peak, Dec, $31.75/MWh, Constellation).")],
                 oracle=lambda api: "EOL-88213 Reliant $2.41; EOL-88190 Constellation $31.75"))

    add(Scenario("MR-016", "messages-read", 2, M, "Summarize every email Tim Belden has sent me.",
                 [ans(r"38\.50", r"95"), ans(r"\b3\b|three", mode="any", critical=False)],
                 [rub("Three emails: msg-011 western power curves (Palo Verde peak $38.50/MWh); msg-025 asks for potential future exposure estimate on long-dated power swaps above 95th percentile; msg-064 western trading desk intro.", "completeness")],
                 oracle=lambda api: "3 emails: curves Palo Verde $38.50; PFE above 95th percentile; desk intro."))

    add(Scenario("MR-017", "messages-read", 1, M, "How many emails have I sent to Sally Beck, and what were they about?",
                 [ans(r"\b2\b|two", r"conference|october 24|oct 24", r"stress|deck")],
                 [rub("Two sent emails to Beck: msg-044 (VaR review Oct 22-26 conflicts with Energy Risk Conference; proposes starting Oct 24) and msg-055 (Risk Committee deck feedback: stress scenarios need longer horizon).")],
                 oracle=lambda api: "2: VaR review conflicts with conference, proposing October 24; deck feedback on stress scenarios."))

    add(Scenario("MR-018", "messages-read", 2, M, "Did I respond to Louise Kitchen's forward curve request? If so, what did I commit to?",
                 [ans(r"yes|did respond|replied|responded", r"wednesday")],
                 [rub("Yes: sent msg-043 'Re: Forward curve update request' committing to refresh the gas curves by Wednesday morning.")],
                 oracle=lambda api: "Yes, you replied committing to refresh the gas curves by Wednesday morning."))

    add(Scenario("MR-019", "messages-read", 1, M, "What default correlation did the credit model calibration produce?",
                 [ans(r"0\.27")], [rub("0.27 (Gibner, msg-032, results attached in calibration_results.xls).")], oracle=lambda api: "0.27"))
    add(Scenario("MR-020", "messages-read", 1, M, "How many weather stations does the weather derivatives model cover now?",
                 [ans(r"\b14\b")], [rub("14 stations after Zimin Lu added Chicago and Atlanta (msg-020).")], oracle=lambda api: "14"))

    aa = gt.mentions("andersen", gt.inbox())
    add(Scenario("MR-021", "messages-read", 1, M, "Which emails mention Arthur Andersen?",
                 [ans(r"valuation memo|SPE structure", r"12 questions|Andersen questions")],
                 [rub(f"Exactly {_subj(gt.ids(aa))}, both from Mark Taylor.")],
                 oracle=lambda api: "; ".join(m["subject"] for m in aa)))

    au = gt.unread(gt.automated())
    add(Scenario("MR-022", "messages-read", 2, M, "How many unread emails do I have from automated/system senders (EnronOnline, legal ticketing, GasBank)? List them.",
                 [ans(rf"\b{len(au)}\b")], [rub(f"{len(au)} unread automated: {_subj(gt.ids(au))}.", "completeness")],
                 oracle=lambda api: f"{len(au)}: " + "; ".join(m["subject"] for m in au)))

    add(Scenario("MR-023", "messages-read", 1, M, "What heat rate did Zimin mention in his spread option question, and what two methods is he choosing between?",
                 [ans(r"10500", r"margrabe")], [rub("10,500 Btu/kWh; Margrabe formula vs two-factor Monte Carlo.")], oracle=lambda api: "10,500 Btu/kWh; Margrabe vs two-factor Monte Carlo"))

    threads = {}
    for m in gt.inbox():
        threads.setdefault(m["conversationId"], []).append(m)
    multi = {k: v for k, v in threads.items() if len(v) > 1}
    add(Scenario("MR-024", "messages-read", 3, M, "Which conversation threads in my inbox have more than one message? Give each thread's topic and message count.",
                 [ans(r"raptor", r"monte carlo", r"weather", r"ferc", r"dynegy", r"headcount")],
                 [rub("Multi-message inbox threads: " + "; ".join(f"{v[-1]['subject']} ({len(v)})" for v in multi.values()) + ". Raptor has 4; the other five have 2 each.", "completeness")],
                 oracle=lambda api: "Raptor 4; Monte Carlo 2; weather 2; FERC 2; Dynegy 2; headcount 2"))

    old = min(gt.inbox(), key=lambda m: m["receivedDateTime"])
    add(Scenario("MR-025", "messages-read", 1, M, "What's the oldest email in my inbox, who sent it, and when?",
                 [ans(r"kean", r"fall planning")], [rub(f"{old['id']} '{old['subject']}' from {gt.sender_name(old)} received {old['receivedDateTime'][:10]}.")],
                 oracle=lambda api: f"{old['subject']} from {gt.sender_name(old)} on {old['receivedDateTime'][:10]}"))

    dyn = [m for m in gt.inbox() if gt.sender(m).endswith("@dynegy.com")]
    add(Scenario("MR-026", "messages-read", 2, M, "How many emails have I received from people at Dynegy (dynegy.com addresses)? Break it down by person.",
                 [ans(rf"\b{len(dyn)}\b", r"belden", r"rebecca|mark")], [rub(f"{len(dyn)} total: Tim Belden 3, Rebecca Mark 2.")],
                 oracle=lambda api: f"{len(dyn)}: Belden 3, Mark 2"))

    lay = gt.by_sender("lay")
    add(Scenario("MR-027", "messages-read", 2, M, "Summarize the emails from Kenneth Lay, with the date each arrived.",
                 [ans(r"friday", r"woodlands|offsite", r"board")],
                 [rub("Three: " + "; ".join(f"{m['id']} '{m['subject']}' {m['receivedDateTime'][:16]}" for m in lay) + ". Content: note on research support before Friday; strategy offsite Nov 5 at the Woodlands (15-min quantitative risk segment); one-page non-technical market risk summary for October board.", "completeness")],
                 oracle=lambda api: "All-employee follow-up (note before Friday); offsite at Woodlands; board prep one-page summary."))

    add(Scenario("MR-028", "messages-read", 1, M, "What were last week's EnronOnline trading volumes?",
                 [ans(r"6112", r"3\.2")], [rub("6,112 trades, $3.2 billion notional; gas 58% of volume.")], oracle=lambda api: "6,112 trades, $3.2 billion"))
    add(Scenario("MR-029", "messages-read", 1, M, "How many settlement discrepancies did Operations find in September, and what was the total?",
                 [ans(r"\b23\b", r"1\.4")], [rub("23 discrepancies totaling $1.4 million (Beck, msg-034).")], oracle=lambda api: "23, $1.4 million"))
    add(Scenario("MR-030", "messages-read", 1, M, "What did HR approve regarding research headcount?",
                 [ans(r"two|\b2\b", r"analyst")], [rub("Two additional analyst positions for Q1 2002 (Skilling, msg-038).")], oracle=lambda api: "Two additional analyst positions for Q1 2002"))

    oct13 = [m for m in gt.inbox() if m["receivedDateTime"][:10] == "2001-10-13"]
    add(Scenario("MR-031", "messages-read", 2, M, "How many emails did I receive on October 13, 2001 (UTC)?",
                 [ans(rf"\b{len(oct13)}\b")], [rub(f"{len(oct13)} emails received on 2001-10-13 UTC: {', '.join(gt.ids(oct13))}.")],
                 oracle=lambda api: f"{len(oct13)}"))

    add(Scenario("MR-032", "messages-read", 2, M, "Who has emailed me about Raptor, and how many Raptor emails has each person sent?",
                 [ans(r"taylor", r"skilling")], [rub("Mark Taylor 3 (msg-010, 022, 035); Jeff Skilling 1 (msg-015). No one else.")],
                 oracle=lambda api: "Mark Taylor 3; Jeff Skilling 1"))
    add(Scenario("MR-033", "messages-read", 1, M, "What is Palo Verde peak marked at for Q1 2002?",
                 [ans(r"38\.50?")], [rub("$38.50/MWh (Belden, msg-011).")], oracle=lambda api: "$38.50/MWh"))
    add(Scenario("MR-034", "messages-read", 1, M, "I got a legal ticket about an NDA. Who is the counterparty and what's the SLA?",
                 [ans(r"citadel", r"5 business days|five business days")], [rub("Ticket LT-4471: mutual NDA with Citadel Investment Group; SLA 5 business days.")],
                 oracle=lambda api: "Citadel Investment Group; 5 business days"))
    add(Scenario("MR-035", "messages-read", 1, M, "How much did the collateral requirement increase in the GasBank margin call warning?",
                 [ans(r"\$?18")], [rub("$18 million on NYMEX positions; Treasury notified (msg-039).")], oracle=lambda api: "$18 million"))
    add(Scenario("MR-036", "messages-read", 1, M, "Has anyone emailed me about the Woodlands? What do they need from me?",
                 [ans(r"lay|ken", r"15")], [rub("Kenneth Lay (msg-026): quarterly strategy offsite Nov 5 at the Woodlands; prepare a 15-minute segment on quantitative risk.")],
                 oracle=lambda api: "Ken Lay: offsite Nov 5, prepare a 15-minute quantitative risk segment"))

    ex_unread = [m for m in gt.unread() if gt.sender(m) in {"jeff.skilling@enron.com", "steven.kean@enron.com", "kenneth.lay@enron.com"}]
    add(Scenario("MR-037", "messages-read", 3, ["messages", "contacts"], "Which of my unread emails are from people in the Executive department? Use my contacts to determine departments.",
                 [ans(r"raptor hedge", r"all-employee", r"board meeting prep")],
                 [rub(f"Executive dept contacts: Skilling, Kean, Lay. Unread from them: {_subj(gt.ids(ex_unread))} ({len(ex_unread)} total). Kean has none unread.")],
                 oracle=lambda api: "; ".join(m["subject"] for m in ex_unread)))
    add(Scenario("MR-038", "messages-read", 1, M, "What ownership split is Dynegy proposing for the joint venture, and when does their board meet?",
                 [ans(r"60\s?/\s?40|60-40|60 ?%", r"24")], [rub("60/40 with Dynegy as majority partner; board meets October 24.")],
                 oracle=lambda api: "60/40 Dynegy majority; board October 24"))

    groups = {}
    for m in gt.unread():
        groups.setdefault(gt.sender_name(m), []).append(m["subject"])
    add(Scenario("MR-039", "messages-read", 3, M, "Give me a digest of all my unread emails, grouped by sender, with one line per email.",
                 [ans(rf"\b{n_unread}\b", critical=False), ans(r"margin call", r"LT-4480|compliance hold", r"Dynegy joint venture", r"Audit request", r"Contract template")],
                 [rub(f"Covers all {n_unread} unread inbox emails grouped by sender: " + "; ".join(f"{k}: {len(v)}" for k, v in groups.items()) + ". No read emails included.", "completeness")],
                 oracle=lambda api: f"{n_unread} unread. " + " | ".join(f"{k}: " + ", ".join(v) for k, v in groups.items())))
    return S


def messages_write():
    S = []
    add = S.append
    add(Scenario("MW-001", "messages-write", 1, M, "Reply to Jeff Skilling's email about the Raptor hedge valuation and tell him I'll send my independent estimate by Friday.",
                 [sent(lambda m: m["kind"] in ("reply", "replyAll") and m["inReplyTo"] == "msg-015" and "friday" in m["body"].lower(), "reply to msg-015 mentioning Friday")],
                 [rub("Replied to msg-015 (not a new unrelated email) saying the independent estimate comes by Friday.", "action-taken")],
                 oracle=lambda api: (api.messages_reply("msg-015", "Jeff, I'll send my independent estimate by Friday."), "Replied.")[1]))
    add(Scenario("MW-002", "messages-write", 1, M, "Send an email to Zimin Lu and Stinson Gibner with the subject 'Storage model rerun' asking them to rerun the storage valuation with the new 85% vol surface.",
                 [sent(lambda m: {"zimin.lu@enron.com", "stinson.gibner@enron.com"} <= set(m["to"] + m["cc"]) and "storage model rerun" in m["subject"].lower(), "email to Lu+Gibner with subject")],
                 [rub("Email sent to both zimin.lu@enron.com and stinson.gibner@enron.com, subject 'Storage model rerun', body asks for rerun with 85% vol.", "action-taken")],
                 oracle=lambda api: (api.messages_send("Storage model rerun", "Please rerun the storage valuation with the new 85% vol surface.", ["zimin.lu@enron.com", "stinson.gibner@enron.com"]), "Sent.")[1]))
    add(Scenario("MW-003", "messages-write", 1, M, "Forward Sally Beck's Risk Committee materials email to Zimin Lu.",
                 [sent(lambda m: m["kind"] == "forward" and m["inReplyTo"] == "msg-009" and "zimin.lu@enron.com" in m["to"], "forward msg-009 to Lu")],
                 [rub("Forwarded msg-009 'Risk Committee materials' to Zimin Lu.", "action-taken")],
                 oracle=lambda api: (api.messages_forward("msg-009", ["zimin.lu@enron.com"], "FYI"), "Forwarded.")[1]))
    add(Scenario("MW-004", "messages-write", 2, M, "Mark all unread emails from the GasBank platform as read.",
                 [st(lambda s: msg(s, "msg-012")["isRead"] and msg(s, "msg-039")["isRead"], "msg-012 and msg-039 read")],
                 [rub("Marked msg-012 and msg-039 (GasBank) as read; did not change others; reports 2 emails.", "action-taken")],
                 oracle=lambda api: ([api.messages_update(i, {"isRead": True}) for i in ("msg-012", "msg-039")], "Marked 2 as read.")[1]))
    add(Scenario("MW-005", "messages-write", 2, M, "Flag both emails about the Dynegy joint venture term sheet for follow-up.",
                 [st(lambda s: all(msg(s, i)["flag"].get("flagStatus") == "flagged" for i in ("msg-018", "msg-030")), "018 and 030 flagged")],
                 [rub("Flagged msg-018 and msg-030.", "action-taken")],
                 oracle=lambda api: ([api.messages_update(i, {"flag": {"flagStatus": "flagged"}}) for i in ("msg-018", "msg-030")], "Flagged 2.")[1]))
    add(Scenario("MW-006", "messages-write", 2, M, "Reply all to Steve Kean's FERC filing deadline email confirming that research will deliver the price-formation analysis by October 17.",
                 [sent(lambda m: m["kind"] == "replyAll" and m["inReplyTo"] == "msg-008", "replyAll to msg-008"),
                  sent(lambda m: m["inReplyTo"] == "msg-008" and "richard.shapiro@enron.com" in m["to"] + m["cc"], "Shapiro included")],
                 [rub("Reply-all to msg-008 (Kean + Shapiro) confirming delivery by October 17.", "action-taken")],
                 oracle=lambda api: (api.messages_replyAll("msg-008", "Confirmed: research will deliver the price-formation analysis by October 17."), "Done.")[1]))
    add(Scenario("MW-007", "messages-write", 2, M, "Draft (but do not send) an email to Ken Lay describing how the research group supports the trading businesses. Keep it to three sentences.",
                 [st(lambda s: any(m.get("isDraft") and any(r["emailAddress"]["address"].lower() == "kenneth.lay@enron.com" for r in m["toRecipients"]) for m in s["messages"]), "draft to Lay exists"),
                  st(lambda s: not any("kenneth.lay@enron.com" in m["to"] for m in s["sentMessages"]), "nothing sent to Lay")],
                 [rub("Created a draft to kenneth.lay@enron.com (not sent) with a short description of research support to trading.", "action-taken")],
                 oracle=lambda api: (api.messages_createDraft("Research support for trading", "Research builds pricing and risk models. We validate curves. We support trading desks daily.", ["kenneth.lay@enron.com"]), "Draft created.")[1]))
    add(Scenario("MW-008", "messages-write", 2, M, "Delete all the EnronOnline trade confirmation emails.",
                 [st(lambda s: {"msg-003", "msg-016"} <= set(s["deletedIds"]), "003 and 016 deleted"),
                  st(lambda s: set(s["deletedIds"]) <= {"msg-003", "msg-016"}, "nothing else deleted")],
                 [rub("Deleted exactly the 2 trade confirmations (msg-003, msg-016).", "action-taken")],
                 oracle=lambda api: ([api.messages_delete(i) for i in ("msg-003", "msg-016")], "Deleted 2.")[1]))
    add(Scenario("MW-009", "messages-write", 1, M, "Send John Lavorato a high-importance email with the subject 'VaR limit breach - model inputs verified' saying we checked the East desk inputs and found no errors.",
                 [sent(lambda m: "john.lavorato@enron.com" in m["to"] and m["importance"] == "high" and "model inputs verified" in m["subject"].lower(), "high-importance email to Lavorato")],
                 [rub("High-importance email to Lavorato with the given subject and a body about East desk inputs checked, no errors.", "action-taken")],
                 oracle=lambda api: (api.messages_send("VaR limit breach - model inputs verified", "We checked the East desk inputs and found no errors.", ["john.lavorato@enron.com"], importance="high"), "Sent.")[1]))
    add(Scenario("MW-010", "messages-write", 2, M, "Reply to each unread email from Rebecca Mark to acknowledge receipt.",
                 [sent(lambda m: m["inReplyTo"] == "msg-018", "reply to 018"), sent(lambda m: m["inReplyTo"] == "msg-030", "reply to 030")],
                 [rub("Replied to both unread Rebecca Mark emails (msg-018, msg-030) with acknowledgements.", "action-taken")],
                 oracle=lambda api: ([api.messages_reply(i, "Received, thank you.") for i in ("msg-018", "msg-030")], "Replied to 2.")[1]))
    hi = gt.ids(gt.high())
    add(Scenario("MW-011", "messages-write", 2, M, "Mark every high-importance email in my inbox as read.",
                 [st(lambda s: all(msg(s, i)["isRead"] for i in hi), "all high-importance read")],
                 [rub(f"All {len(hi)} high-importance inbox emails are read ({', '.join(hi)}); the 5 previously unread were updated.", "action-taken")],
                 oracle=lambda api: ([api.messages_update(i, {"isRead": True}) for i in hi], "Done.")[1]))
    add(Scenario("MW-012", "messages-write", 1, M, "Email Sally Beck proposing that the VaR model review start on October 24 instead, and cc Stinson Gibner.",
                 [sent(lambda m: "sally.beck@enron.com" in m["to"] and "stinson.gibner@enron.com" in m["cc"] + m["to"] and "24" in m["body"], "Beck to, Gibner cc, mentions 24")],
                 [rub("Email to Beck with Gibner in cc proposing an October 24 start.", "action-taken")],
                 oracle=lambda api: (api.messages_send("VaR model review", "Could we start the review on October 24?", ["sally.beck@enron.com"], ["stinson.gibner@enron.com"]), "Sent.")[1]))
    add(Scenario("MW-013", "messages-write", 1, M, "Forward Zimin's weather derivatives model v2 email to Tim Belden with a note that it may help with western hedging.",
                 [sent(lambda m: m["kind"] == "forward" and m["inReplyTo"] == "msg-005" and "tim.belden@dynegy.com" in m["to"], "forward 005 to Belden")],
                 [rub("Forwarded msg-005 (the original v2 email with attachment) to Tim Belden with the note.", "action-taken")],
                 oracle=lambda api: (api.messages_forward("msg-005", ["tim.belden@dynegy.com"], "May help with western hedging."), "Forwarded.")[1]))
    ferc = gt.ids(gt.mentions("ferc", gt.inbox()))
    add(Scenario("MW-014", "messages-write", 2, M, "Apply the 'FERC' category label to every email in my inbox that mentions FERC.",
                 [st(lambda s: all("FERC" in msg(s, i)["categories"] for i in ferc), "all FERC inbox emails labeled")],
                 [rub(f"Labeled {', '.join(ferc)} with FERC (preserving other categories).", "action-taken")],
                 oracle=lambda api: ([api.messages_update(i, {"categories": sorted(set(api.messages_get(i)["categories"]) | {"FERC"})}) for i in ferc], "Labeled.")[1]))
    add(Scenario("MW-015", "messages-write", 1, M, "Reply to Steve Kean's press inquiry email saying understood, I'll route any reporter questions to him.",
                 [sent(lambda m: m["inReplyTo"] == "msg-037" and m["kind"] in ("reply", "replyAll"), "reply to msg-037")],
                 [rub("Reply to msg-037 confirming reporter questions will be routed to Kean.", "action-taken")],
                 oracle=lambda api: (api.messages_reply("msg-037", "Understood, I'll route any reporter questions to you."), "Replied.")[1]))
    return S
