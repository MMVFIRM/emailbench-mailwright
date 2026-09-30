"""Scenario registry."""
from collections import Counter

from .scen_calendar import calendar_read, calendar_triage, calendar_write, meeting_prep
from .scen_cross import cross_domain, multi_domain, orchestration
from .scen_messages import messages_read, messages_write
from .scen_ops import boards, contacts, filters, folders, inbox_cleanup, settings, todo

PAPER_COUNTS = {"messages-read": 39, "orchestration": 17, "cross-domain": 15, "messages-write": 15, "multi-domain": 12,
                "calendar-read": 12, "calendar-write": 12, "boards": 10, "todo": 9, "meeting-prep": 9, "inbox-cleanup": 9,
                "folders": 9, "calendar-triage": 8, "settings": 8, "contacts": 12, "filters": 10}


def all_scenarios():
    out = []
    for f in (messages_read, messages_write, calendar_read, calendar_write, calendar_triage, meeting_prep, folders,
              filters, settings, contacts, todo, boards, inbox_cleanup, cross_domain, multi_domain, orchestration):
        out.extend(f())
    ids = [s.id for s in out]
    assert len(ids) == len(set(ids)), [i for i, c in Counter(ids).items() if c > 1]
    return out


def holdout2_scenarios():
    from .scen_holdout2 import holdout2
    out = holdout2()
    assert len({x.id for x in out}) == len(out)
    return out


def get(split=None, ids=None, categories=None):
    if split == "holdout2":
        s = holdout2_scenarios()
        split = None
    else:
        s = all_scenarios()
    if split:
        s = [x for x in s if x.split == split]
    if ids:
        s = [x for x in s if x.id in set(ids)]
    if categories:
        s = [x for x in s if x.category in set(categories)]
    return s
