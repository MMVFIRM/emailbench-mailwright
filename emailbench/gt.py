"""Ground-truth queries over the seed corpus (used to generate expected answers)."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from .corpus import AUTOMATED_SENDERS, REFERENCE_TIME, USERS, build_corpus

C = build_corpus()
MSGS = C["messages"]
EVENTS = C["events"]
CONTACTS = C["contacts"]
TASKS = C["todoTasks"]
LISTS = C["todoLists"]
NAME = {u["address"]: u["name"] for u in USERS.values()}


def dt(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def inbox():
    return [m for m in MSGS if m["parentFolderId"] == "folder-inbox"]


def sent_items():
    return [m for m in MSGS if m["parentFolderId"] == "folder-sent"]


def sender(m):
    return m["from"]["emailAddress"]["address"]


def sender_name(m):
    return m["from"]["emailAddress"]["name"]


def by_sender(key):
    a = USERS[key]["address"]
    return [m for m in inbox() if sender(m) == a]


def unread(ms=None):
    return [m for m in (ms if ms is not None else inbox()) if not m["isRead"]]


def ids(ms):
    return [m["id"] for m in ms]


def within_hours(h, ms=None):
    cut = REFERENCE_TIME - timedelta(hours=h)
    return [m for m in (ms if ms is not None else inbox()) if dt(m["receivedDateTime"]) >= cut]


def mentions(word, ms=None):
    w = word.lower()
    return [m for m in (ms if ms is not None else MSGS) if w in (m["subject"] + " " + m["body"]).lower()]


def automated(ms=None):
    return [m for m in (ms if ms is not None else inbox()) if sender(m) in AUTOMATED_SENDERS]


def high(ms=None):
    return [m for m in (ms if ms is not None else inbox()) if m["importance"] == "high"]


def sender_counts(ms=None):
    return Counter(sender(m) for m in (ms if ms is not None else inbox()))


def unread_rates():
    tot, un = Counter(), Counter()
    for m in inbox():
        tot[sender(m)] += 1
        un[sender(m)] += (not m["isRead"])
    return {a: (un[a], tot[a], 100.0 * un[a] / tot[a]) for a in tot}


def ev(eid):
    return next(e for e in EVENTS if e["id"] == eid)


def events_on(day):
    d = f"2001-10-{day:02d}"
    return sorted([e for e in EVENTS if e["start"]["dateTime"][:10] <= d <= (e["end"]["dateTime"][:10] if not e["isAllDay"] else (dt(e["end"]["dateTime"]) - timedelta(seconds=1)).strftime("%Y-%m-%d"))],
                  key=lambda e: e["start"]["dateTime"])


def hm(s):
    return s[11:16]


def attendees(e):
    return [a["emailAddress"]["address"] for a in e["attendees"]]


def busy_intervals(day):
    out = []
    for e in events_on(day):
        if e["isAllDay"]:
            out.append(("00:00", "24:00", e["subject"]))
        else:
            out.append((hm(e["start"]["dateTime"]), hm(e["end"]["dateTime"]), e["subject"]))
    return out


def free_slots(day, start="08:00", end="18:00", min_minutes=30):
    busy = sorted((s, e) for s, e, _ in busy_intervals(day))
    cur, out = start, []
    for s, e in busy:
        if e <= cur:
            continue
        if s > cur:
            s2 = min(s, end)
            if _mins(s2) - _mins(cur) >= min_minutes:
                out.append((cur, s2))
        cur = max(cur, e)
        if cur >= end:
            break
    if cur < end and _mins(end) - _mins(cur) >= min_minutes:
        out.append((cur, end))
    return out


def _mins(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def contact_by_email(a):
    return next((c for c in CONTACTS if c["emailAddresses"][0]["address"] == a), None)


def tasks_in(list_name):
    lid = next(l["id"] for l in LISTS if l["displayName"] == list_name)
    return [t for t in TASKS if t["listId"] == lid]


def list_of(task):
    return next(l["displayName"] for l in LISTS if l["id"] == task["listId"])
