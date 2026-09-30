"""Scenario / assertion types and snapshot helpers."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Static:
    kind: str                     # return-contains | state-check | exists | sent-message
    desc: str
    fn: Callable                  # (snapshot, answer) -> bool
    critical: bool = True
    weight: float = 1.0


@dataclass
class Rubric:
    text: str
    dimension: str = "correctness"
    critical: bool = True
    weight: float = 1.0


@dataclass
class Scenario:
    id: str
    category: str
    difficulty: int
    domains: list
    query: str
    static: list = field(default_factory=list)
    rubrics: list = field(default_factory=list)
    oracle: Optional[Callable] = None       # (api) -> answer str ; reference solution used in tests only
    notes: str = ""

    @property
    def split(self):
        h = int(hashlib.sha256(self.id.encode()).hexdigest(), 16) % 100
        return "dev" if h < 30 else "test"


# ------------------------------------------------------------------ assertion builders
def _norm_answer(a):
    a = a or ""
    a = a.replace("’", "'").replace("–", "-").replace("—", "-")
    a = re.sub(r"(?<=\d),(?=\d{3})", "", a)          # 50,000 -> 50000
    a = re.sub(r"[*`]", "", a)                         # strip markdown emphasis (keep _ for file names)
    return a


def ans(*patterns, mode="all", critical=True, desc=None):
    pats = [re.compile(p, re.I) for p in patterns]

    def fn(snap, answer):
        a = _norm_answer(answer)
        hits = [bool(p.search(a)) for p in pats]
        return all(hits) if mode == "all" else any(hits)
    return Static("return-contains", desc or f"answer contains {mode} of {list(patterns)}", fn, critical)


def ans_not(*patterns, critical=True, desc=None):
    pats = [re.compile(p, re.I) for p in patterns]

    def fn(snap, answer):
        a = _norm_answer(answer)
        return not any(p.search(a) for p in pats)
    return Static("return-contains", desc or f"answer excludes {list(patterns)}", fn, critical)


def st(fn, desc, critical=True):
    return Static("state-check", desc, lambda snap, a: bool(fn(snap)), critical)


def ex(fn, desc, critical=True):
    return Static("exists", desc, lambda snap, a: bool(fn(snap)), critical)


def sent(fn, desc, critical=True):
    return Static("sent-message", desc, lambda snap, a: any(fn(m) for m in snap["sentMessages"]), critical)


def rub(text, dim="correctness", critical=True):
    return Rubric(text, dim, critical)


# ------------------------------------------------------------------ snapshot helpers
def folder_by_name(snap, name, parent_name=None):
    for f in snap["folders"]:
        if f["displayName"].strip().lower() == name.lower():
            if parent_name is None:
                return f
            p = folder_by_name(snap, parent_name)
            if p and f.get("parentFolderId") == p["id"]:
                return f
    return None


def msgs_in(snap, folder_id):
    return {m["id"] for m in snap["messages"] if m["parentFolderId"] == folder_id}


def msg(snap, mid):
    return next((m for m in snap["messages"] if m["id"] == mid), None)


def in_folder(snap, mid, fname, parent=None):
    f = folder_by_name(snap, fname, parent)
    m = msg(snap, mid)
    return bool(f and m and m["parentFolderId"] == f["id"])


def events_named(snap, *words):
    return [e for e in snap["events"] if all(w.lower() in e["subject"].lower() for w in words)]


def new_events(snap):
    return [e for e in snap["events"] if not e["id"].startswith("evt-0")]


def attendee_addrs(e):
    return {a["emailAddress"]["address"].lower() for a in e.get("attendees", [])}


def tasks_titled(snap, *words, list_name=None):
    out = []
    lids = None
    if list_name:
        lids = {l["id"] for l in snap["todoLists"] if l["displayName"].lower() == list_name.lower()}
    for t in snap["todoTasks"]:
        if all(w.lower() in t["title"].lower() for w in words) and (lids is None or t["listId"] in lids):
            out.append(t)
    return out


def task(snap, tid):
    return next((t for t in snap["todoTasks"] if t["id"] == tid), None)


def event(snap, eid):
    return next((e for e in snap["events"] if e["id"] == eid), None)


def sent_to(snap, addr, kind=None):
    return [m for m in snap["sentMessages"] if addr.lower() in m["to"] + m["cc"] and (kind is None or m["kind"] == kind)]


def no_sent_items_moved(snap):
    return all(mv["fromFolderId"] != "folder-sent" for mv in snap["movedMessages"])


def not_mutated(snap, *ops):
    return not any(c["op"] in ops for c in snap["changelog"])


def no_mutations(snap):
    return len(snap["changelog"]) == 0
