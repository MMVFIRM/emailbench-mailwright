"""In-memory EmailBench-style API with changelog + snapshot.

Deviation from the paper (documented in README): reads reflect mutations
(the paper's changelog implementation kept message reads frozen), folder counts
are live, and event durations keep fractional hours. Set frozen_reads=True to
emulate the paper's frozen-message-read behaviour.
"""
from __future__ import annotations

import copy
import itertools
import re
from datetime import datetime, timezone

from .corpus import build_corpus
from .odata import ODataError, compile_filter, order_key_fn


class APIError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def _err(code, msg):
    raise APIError(code, msg)


def _parse_dt(v):
    if v is None:
        return None
    if isinstance(v, dict):
        v = v.get("dateTime")
    if not isinstance(v, str):
        _err("InvalidDateTime", f"Expected ISO datetime string, got {v!r}")
    s = v.strip().replace(" ", "T")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        s += "T00:00:00"
    s = s.rstrip("Z")
    s = re.sub(r"([+-]\d{2}:\d{2})$", "", s)
    try:
        dt = datetime.fromisoformat(s.split(".")[0])
    except ValueError:
        _err("InvalidDateTime", f"Could not parse datetime {v!r}; use ISO 8601 like 2001-10-16T14:00:00")
    return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recips(v):
    if v is None:
        return []
    if isinstance(v, str):
        v = [x.strip() for x in re.split(r"[;,]", v) if x.strip()]
    out = []
    for r in v:
        if isinstance(r, str):
            out.append({"emailAddress": {"address": r, "name": r}})
        elif isinstance(r, dict):
            ea = r.get("emailAddress", r)
            if isinstance(ea, str):
                ea = {"address": ea}
            addr = ea.get("address")
            if not addr:
                _err("InvalidRecipients", f"Recipient missing address: {r!r}")
            out.append({"emailAddress": {"address": addr, "name": ea.get("name", addr)}})
        else:
            _err("InvalidRecipients", f"Bad recipient {r!r}")
    return out


class EmailBenchAPI:
    LIST_FIELDS = ("id", "subject", "from", "toRecipients", "ccRecipients", "receivedDateTime", "isRead",
                   "importance", "hasAttachments", "conversationId", "parentFolderId", "flag", "categories")

    def __init__(self, corpus=None, frozen_reads=False):
        self.frozen_reads = frozen_reads
        self.reset(corpus)

    # ------------------------------------------------------------ lifecycle
    def reset(self, corpus=None):
        self.seed = corpus or build_corpus()
        self.s = copy.deepcopy(self.seed)
        self.changelog = []
        self.sent, self.deleted_ids, self.moved = [], [], []
        self._ids = itertools.count(5001)

    def _nid(self, prefix):
        return f"{prefix}-{next(self._ids)}"

    def _log(self, op, **kw):
        self.changelog.append(dict(op=op, **kw))

    def snapshot(self):
        s = copy.deepcopy(self.s)
        return dict(messages=s["messages"], folders=s["folders"], events=s["events"], contacts=s["contacts"],
                    todoLists=s["todoLists"], todoTasks=s["todoTasks"], filters=s["filters"],
                    settings=s["settings"], sentMessages=copy.deepcopy(self.sent),
                    deletedIds=list(self.deleted_ids), movedMessages=copy.deepcopy(self.moved),
                    changelog=copy.deepcopy(self.changelog), labels=s["labels"])

    # ------------------------------------------------------------ helpers
    def _read_msgs(self):
        return self.seed["messages"] if self.frozen_reads else self.s["messages"]

    def _msg(self, mid):
        for m in self.s["messages"]:
            if m["id"] == mid:
                return m
        _err("ErrorItemNotFound", f"Message {mid!r} not found")

    def _folder_id(self, ref):
        if not ref:
            _err("InvalidFolder", "destinationFolderId is required")
        for f in self.s["folders"]:
            if f["id"] == ref or (f.get("wellKnownName") or "").lower() == str(ref).lower():
                return f["id"]
        _err("ErrorFolderNotFound", f"Folder {ref!r} not found. Use folders_list or folders_getByName to obtain a folder id.")

    def _summ(self, m):
        d = {k: copy.deepcopy(m[k]) for k in self.LIST_FIELDS}
        d["bodyPreview"] = m["body"][:120]
        return d

    # ------------------------------------------------------------ messages
    def messages_list(self, top=10, filter=None, orderBy=None, skip=0, folderId=None):
        top = max(1, min(int(top or 10), 100))
        skip = int(skip or 0)
        try:
            pred = compile_filter(filter)
        except ODataError as e:
            _err("BadFilter", f"Invalid filter: {e}")
        msgs = self._read_msgs()
        if folderId:
            fid = self._folder_id(folderId)
            msgs = [m for m in msgs if m["parentFolderId"] == fid]
        msgs = [m for m in msgs if not m.get("isDraft") or folderId]
        msgs = [m for m in msgs if pred(m)]
        k, rev = order_key_fn(orderBy)
        msgs = sorted(msgs, key=k, reverse=rev)
        page = msgs[skip:skip + top]
        out = dict(value=[self._summ(m) for m in page], totalCount=len(msgs))
        if skip + top < len(msgs):
            out["nextSkip"] = skip + top
        return out

    def messages_get(self, id):
        for m in self._read_msgs():
            if m["id"] == id:
                return copy.deepcopy(m)
        _err("ErrorItemNotFound", f"Message {id!r} not found")

    def messages_search(self, query, top=25):
        if not query or not str(query).strip():
            _err("BadQuery", "query is required")
        top = max(1, min(int(top or 25), 100))
        q = str(query)
        field_terms = re.findall(r'(\w+):"([^"]+)"|(\w+):(\S+)', q)
        rest = re.sub(r'\w+:"[^"]+"|\w+:\S+', " ", q)
        phrases = re.findall(r'"([^"]+)"', rest)
        rest = re.sub(r'"[^"]+"', " ", rest)
        words = [w for w in re.split(r"\s+", rest) if w and w.upper() not in ("AND",)]
        ors = "OR" in words
        words = [w for w in words if w != "OR"]

        def text(m):
            return " ".join([m["subject"], m["body"], m["from"]["emailAddress"]["name"], m["from"]["emailAddress"]["address"],
                             " ".join(r["emailAddress"]["address"] + " " + r["emailAddress"].get("name", "") for r in m["toRecipients"] + m["ccRecipients"]),
                             " ".join(a["name"] for a in m["attachments"])]).lower()

        def ok(m):
            t = text(m)
            for f1, v1, f2, v2 in field_terms:
                f, v = (f1 or f2).lower(), (v1 or v2).lower()
                if f == "from":
                    src = (m["from"]["emailAddress"]["name"] + " " + m["from"]["emailAddress"]["address"]).lower()
                elif f == "to":
                    src = " ".join(r["emailAddress"]["address"] + " " + r["emailAddress"].get("name", "") for r in m["toRecipients"] + m["ccRecipients"]).lower()
                elif f == "subject":
                    src = m["subject"].lower()
                elif f == "body":
                    src = m["body"].lower()
                elif f in ("hasattachment", "hasattachments"):
                    if (v == "true") != m["hasAttachments"]:
                        return False
                    continue
                else:
                    src = t
                if v not in src:
                    return False
            terms = [p.lower() for p in phrases] + [w.lower().strip(",.") for w in words]
            if not terms:
                return True
            hits = [x in t for x in terms]
            return any(hits) if ors else all(hits)

        res = [m for m in self._read_msgs() if ok(m) and not m.get("isDraft")]
        res.sort(key=lambda m: m["receivedDateTime"], reverse=True)
        return dict(value=[self._summ(m) for m in res[:top]], totalCount=len(res))

    def messages_count(self, filter=None):
        try:
            pred = compile_filter(filter)
        except ODataError as e:
            _err("BadFilter", f"Invalid filter: {e}")
        return dict(count=sum(1 for m in self._read_msgs() if pred(m) and not m.get("isDraft")))

    def _new_sent(self, subject, body, to, cc=None, importance="normal", reply_to=None, kind="send"):
        to, cc = _recips(to), _recips(cc)
        if not to:
            _err("InvalidRecipients", "At least one recipient is required")
        mid = self._nid("msg")
        now = self.s["reference_time"]
        m = dict(id=mid, subject=subject or "", body=body or "", toRecipients=to, ccRecipients=cc,
                 receivedDateTime=now, sentDateTime=now, isRead=True, importance=importance or "normal",
                 conversationId=(reply_to or {}).get("conversationId", f"conv-{mid}"), parentFolderId="folder-sent",
                 attachments=[], flag={"flagStatus": "notFlagged"}, categories=[], isDraft=False, hasAttachments=False,
                 **{"from": {"emailAddress": {"name": self.s["me"]["name"], "address": self.s["me"]["address"]}}})
        self.s["messages"].append(m)
        rec = dict(id=mid, kind=kind, subject=m["subject"], body=m["body"],
                   to=[r["emailAddress"]["address"].lower() for r in to], cc=[r["emailAddress"]["address"].lower() for r in cc],
                   inReplyTo=(reply_to or {}).get("id"), importance=m["importance"])
        self.sent.append(rec)
        self._log(kind, id=mid, inReplyTo=rec["inReplyTo"])
        return dict(success=True, id=mid)

    def messages_send(self, subject, body, toRecipients, ccRecipients=None, importance="normal"):
        return self._new_sent(subject, body, toRecipients, ccRecipients, importance)

    def messages_createDraft(self, subject, body, toRecipients=None):
        mid = self._nid("msg")
        m = dict(id=mid, subject=subject or "", body=body or "", toRecipients=_recips(toRecipients), ccRecipients=[],
                 receivedDateTime=self.s["reference_time"], sentDateTime=None, isRead=True, importance="normal",
                 conversationId=f"conv-{mid}", parentFolderId="folder-drafts", attachments=[], hasAttachments=False,
                 flag={"flagStatus": "notFlagged"}, categories=[], isDraft=True,
                 **{"from": {"emailAddress": {"name": self.s["me"]["name"], "address": self.s["me"]["address"]}}})
        self.s["messages"].append(m)
        self._log("createDraft", id=mid)
        return dict(success=True, id=mid)

    def messages_update(self, id, patch):
        m = self._msg(id)
        if not isinstance(patch, dict):
            _err("BadPatch", "patch must be an object")
        allowed = {"isRead", "importance", "flag", "categories", "subject", "body"}
        bad = set(patch) - allowed
        if bad:
            _err("BadPatch", f"Unsupported fields {sorted(bad)}; allowed: {sorted(allowed)}")
        for k, v in patch.items():
            if k == "flag" and isinstance(v, str):
                v = {"flagStatus": v}
            if k == "importance" and v not in ("low", "normal", "high"):
                _err("BadPatch", "importance must be low|normal|high")
            m[k] = copy.deepcopy(v)
        self._log("updateMessage", id=id, patch=copy.deepcopy(patch))
        return dict(success=True, id=id)

    def _move(self, id, dest):
        m = self._msg(id)
        fid = self._folder_id(dest)
        src = m["parentFolderId"]
        m["parentFolderId"] = fid
        self.moved.append(dict(id=id, fromFolderId=src, toFolderId=fid))
        self._log("move", id=id, fromFolderId=src, toFolderId=fid)

    def messages_move(self, id, destinationFolderId):
        self._move(id, destinationFolderId)
        return dict(success=True, id=id, destinationFolderId=self._folder_id(destinationFolderId))

    def messages_batchMove(self, ids, destinationFolderId):
        if isinstance(ids, str):
            ids = [x.strip() for x in ids.split(",") if x.strip()]
        fid = self._folder_id(destinationFolderId)
        moved, failed = [], []
        for i in ids or []:
            try:
                self._move(i, fid)
                moved.append(i)
            except APIError as e:
                failed.append(dict(id=i, error=e.message))
        return dict(moved=moved, failed=failed, destinationFolderId=fid)

    def messages_delete(self, id):
        m = self._msg(id)
        src = m["parentFolderId"]
        m["parentFolderId"] = "folder-deleted"
        self.deleted_ids.append(id)
        self._log("delete", id=id, fromFolderId=src)
        return dict(success=True, id=id)

    def messages_reply(self, id, comment):
        m = self._msg(id)
        return self._new_sent("RE: " + m["subject"], comment, [m["from"]["emailAddress"]["address"]], reply_to=m, kind="reply")

    def messages_replyAll(self, id, comment):
        m = self._msg(id)
        me = self.s["me"]["address"].lower()
        to = [m["from"]["emailAddress"]["address"]] + [r["emailAddress"]["address"] for r in m["toRecipients"] if r["emailAddress"]["address"].lower() != me]
        cc = [r["emailAddress"]["address"] for r in m["ccRecipients"] if r["emailAddress"]["address"].lower() != me]
        return self._new_sent("RE: " + m["subject"], comment, to, cc, reply_to=m, kind="replyAll")

    def messages_forward(self, id, toRecipients, comment=""):
        m = self._msg(id)
        body = (comment or "") + "\n\n---------- Forwarded message ----------\n" + m["body"]
        return self._new_sent("FW: " + m["subject"], body, toRecipients, reply_to=m, kind="forward")

    # ------------------------------------------------------------ folders
    def _folder_view(self, f):
        d = dict(f)
        msgs = self._read_msgs()
        d["totalItemCount"] = sum(1 for m in msgs if m["parentFolderId"] == f["id"])
        d["unreadItemCount"] = sum(1 for m in msgs if m["parentFolderId"] == f["id"] and not m["isRead"])
        d["childFolderCount"] = sum(1 for g in self.s["folders"] if g.get("parentFolderId") == f["id"])
        return d

    def folders_list(self):
        return dict(value=[self._folder_view(f) for f in self.s["folders"]])

    def folders_get(self, id):
        for f in self.s["folders"]:
            if f["id"] == id or (f.get("wellKnownName") or "") == str(id).lower():
                return self._folder_view(f)
        _err("ErrorFolderNotFound", f"Folder {id!r} not found")

    def folders_getByName(self, name):
        hits = [f for f in self.s["folders"] if f["displayName"].lower() == str(name).lower()]
        if not hits:
            _err("ErrorFolderNotFound", f"No folder named {name!r}")
        return dict(value=[self._folder_view(f) for f in hits])

    def folders_create(self, displayName, parentFolderId=None):
        if not displayName:
            _err("BadRequest", "displayName required")
        pid = self._folder_id(parentFolderId) if parentFolderId else None
        for f in self.s["folders"]:
            if f["displayName"].lower() == displayName.lower() and f.get("parentFolderId") == pid:
                _err("ErrorFolderExists", f"A folder named {displayName!r} already exists here (id {f['id']})")
        fid = self._nid("folder")
        self.s["folders"].append(dict(id=fid, displayName=displayName, parentFolderId=pid, wellKnownName=None))
        self._log("createFolder", id=fid, displayName=displayName, parentFolderId=pid)
        return dict(success=True, id=fid, displayName=displayName, parentFolderId=pid)

    def folders_rename(self, id, newName):
        fid = self._folder_id(id)
        f = next(f for f in self.s["folders"] if f["id"] == fid)
        if f.get("wellKnownName"):
            _err("Forbidden", "Cannot rename a default folder")
        old = f["displayName"]
        f["displayName"] = newName
        self._log("renameFolder", id=fid, old=old, new=newName)
        return dict(success=True, id=fid, displayName=newName)

    def folders_delete(self, id):
        fid = self._folder_id(id)
        f = next(f for f in self.s["folders"] if f["id"] == fid)
        if f.get("wellKnownName"):
            _err("Forbidden", "Cannot delete a default folder")
        self.s["folders"] = [g for g in self.s["folders"] if g["id"] != fid]
        for m in self.s["messages"]:
            if m["parentFolderId"] == fid:
                m["parentFolderId"] = "folder-deleted"
        self._log("deleteFolder", id=fid)
        return dict(success=True, id=fid)

    # ------------------------------------------------------------ filters
    def filters_list(self):
        return dict(value=copy.deepcopy(self.s["filters"]))

    def filters_create(self, name, isEnabled=True, criteria=None, actions=None):
        if not name:
            _err("BadRequest", "name required")
        if not criteria or not actions:
            _err("BadRequest", "criteria and actions are required (e.g. criteria={'fromAddresses':[...]} actions={'moveToFolder': folderId})")
        actions = copy.deepcopy(actions)
        if actions.get("moveToFolder"):
            actions["moveToFolder"] = self._folder_id(actions["moveToFolder"])
        fid = self._nid("filter")
        f = dict(id=fid, name=name, isEnabled=bool(isEnabled), sequence=len(self.s["filters"]) + 1,
                 criteria=copy.deepcopy(criteria), actions=actions)
        self.s["filters"].append(f)
        self._log("createFilter", id=fid)
        return dict(success=True, id=fid)

    def filters_update(self, id, patch):
        f = next((f for f in self.s["filters"] if f["id"] == id), None)
        if not f:
            _err("ErrorItemNotFound", f"Filter {id!r} not found")
        for k, v in (patch or {}).items():
            if k not in ("name", "isEnabled", "criteria", "actions", "sequence"):
                _err("BadPatch", f"Unsupported field {k}")
            f[k] = copy.deepcopy(v)
        self._log("updateFilter", id=id, patch=copy.deepcopy(patch))
        return dict(success=True, id=id)

    def filters_delete(self, id):
        if not any(f["id"] == id for f in self.s["filters"]):
            _err("ErrorItemNotFound", f"Filter {id!r} not found")
        self.s["filters"] = [f for f in self.s["filters"] if f["id"] != id]
        self._log("deleteFilter", id=id)
        return dict(success=True, id=id)

    # ------------------------------------------------------------ calendar
    def _evt(self, id):
        for e in self.s["events"]:
            if e["id"] == id:
                return e
        _err("ErrorItemNotFound", f"Event {id!r} not found")

    def calendar_list(self, top=25, startDateTime=None, endDateTime=None):
        top = max(1, min(int(top or 25), 100))
        s, e = _parse_dt(startDateTime), _parse_dt(endDateTime)
        evs = [x for x in self.s["events"] if not x.get("isCancelled")]
        if s:
            evs = [x for x in evs if x["end"]["dateTime"] > s]
        if e:
            evs = [x for x in evs if x["start"]["dateTime"] < e]
        evs.sort(key=lambda x: x["start"]["dateTime"])
        out = dict(value=copy.deepcopy(evs[:top]), totalCount=len(evs))
        if len(evs) > top:
            out["note"] = f"{len(evs) - top} more events not shown; increase top or narrow the window"
        return out

    def calendar_get(self, id):
        return copy.deepcopy(self._evt(id))

    def _atts(self, attendees):
        out = []
        for a in _recips(attendees):
            out.append(dict(emailAddress=a["emailAddress"], type="required", status=dict(response="none")))
        return out

    def calendar_create(self, subject, start, end, location=None, attendees=None, body=None, isAllDay=False):
        s, e = _parse_dt(start), _parse_dt(end)
        if not s or not e:
            _err("BadRequest", "start and end are required")
        if e <= s:
            _err("BadRequest", "end must be after start")
        eid = self._nid("evt")
        loc = location.get("displayName") if isinstance(location, dict) else (location or "")
        ev = dict(id=eid, subject=subject, body=body or "", start=dict(dateTime=s, timeZone="UTC"),
                  end=dict(dateTime=e, timeZone="UTC"), location=dict(displayName=loc), isAllDay=bool(isAllDay),
                  organizer=dict(emailAddress=dict(name=self.s["me"]["name"], address=self.s["me"]["address"])),
                  attendees=self._atts(attendees), responseStatus=dict(response="organizer"), isCancelled=False, showAs="busy")
        self.s["events"].append(ev)
        self._log("createEvent", id=eid)
        return dict(success=True, id=eid, start=ev["start"], end=ev["end"])

    def calendar_update(self, id, patch):
        ev = self._evt(id)
        for k, v in (patch or {}).items():
            if k in ("start", "end"):
                ev[k] = dict(dateTime=_parse_dt(v), timeZone="UTC")
            elif k == "attendees":
                ev[k] = self._atts(v)
            elif k == "location":
                ev[k] = dict(displayName=v.get("displayName") if isinstance(v, dict) else v)
            elif k in ("subject", "body", "isAllDay", "showAs", "importance"):
                ev[k] = v
            else:
                _err("BadPatch", f"Unsupported field {k}")
        if ev["end"]["dateTime"] <= ev["start"]["dateTime"]:
            _err("BadRequest", "end must be after start")
        self._log("updateEvent", id=id, patch=copy.deepcopy(patch))
        return dict(success=True, id=id)

    def calendar_delete(self, id):
        self._evt(id)
        self.s["events"] = [e for e in self.s["events"] if e["id"] != id]
        self._log("deleteEvent", id=id)
        return dict(success=True, id=id)

    def _respond(self, id, resp, comment):
        ev = self._evt(id)
        if ev["responseStatus"]["response"] == "organizer":
            _err("Forbidden", "You are the organizer of this event")
        ev["responseStatus"] = dict(response=resp)
        self._log("respondEvent", id=id, response=resp, comment=comment)
        return dict(success=True, id=id, response=resp)

    def calendar_accept(self, id, comment=""):
        return self._respond(id, "accepted", comment)

    def calendar_decline(self, id, comment=""):
        return self._respond(id, "declined", comment)

    # ------------------------------------------------------------ contacts
    def contacts_list(self, top=50):
        top = max(1, min(int(top or 50), 100))
        return dict(value=copy.deepcopy(self.s["contacts"][:top]), totalCount=len(self.s["contacts"]))

    def contacts_search(self, query):
        q = str(query or "").lower().strip()
        if not q:
            _err("BadQuery", "query required")

        def blob(c):
            return " ".join(str(x) for x in [c["displayName"], c.get("givenName"), c.get("surname"), c.get("companyName"),
                                             c.get("department"), c.get("jobTitle")] + [e["address"] for e in c["emailAddresses"]] if x).lower()
        terms = q.split()
        return dict(value=[copy.deepcopy(c) for c in self.s["contacts"] if all(t in blob(c) for t in terms)])

    def contacts_create(self, displayName=None, givenName=None, surname=None, emailAddresses=None, companyName=None,
                        department=None, jobTitle=None):
        if not (displayName or givenName or surname):
            _err("BadRequest", "displayName or name required")
        ems = []
        for e in (emailAddresses or []) if not isinstance(emailAddresses, str) else [emailAddresses]:
            ems.append(dict(address=e, name=displayName) if isinstance(e, str) else dict(address=e.get("address"), name=e.get("name", displayName)))
        cid = self._nid("contact")
        c = dict(id=cid, displayName=displayName or f"{givenName or ''} {surname or ''}".strip(), givenName=givenName,
                 surname=surname, emailAddresses=ems, companyName=companyName, department=department, jobTitle=jobTitle, businessPhones=[])
        self.s["contacts"].append(c)
        self._log("createContact", id=cid)
        return dict(success=True, id=cid)

    def contacts_delete(self, id):
        if not any(c["id"] == id for c in self.s["contacts"]):
            _err("ErrorItemNotFound", f"Contact {id!r} not found")
        self.s["contacts"] = [c for c in self.s["contacts"] if c["id"] != id]
        self._log("deleteContact", id=id)
        return dict(success=True, id=id)

    # ------------------------------------------------------------ todo
    def todo_lists(self):
        return dict(value=copy.deepcopy(self.s["todoLists"]))

    def todo_createList(self, displayName):
        lid = self._nid("list")
        self.s["todoLists"].append(dict(id=lid, displayName=displayName))
        self._log("createList", id=lid)
        return dict(success=True, id=lid)

    def _list(self, lid):
        if not any(l["id"] == lid for l in self.s["todoLists"]):
            _err("ErrorItemNotFound", f"Todo list {lid!r} not found; call todo_lists first")

    def todo_tasks(self, listId):
        self._list(listId)
        return dict(value=[copy.deepcopy(t) for t in self.s["todoTasks"] if t["listId"] == listId])

    def todo_createTask(self, listId, title, body=None, dueDateTime=None, importance="normal"):
        self._list(listId)
        tid = self._nid("task")
        t = dict(id=tid, listId=listId, title=title, body=body or "",
                 dueDateTime=(dict(dateTime=_parse_dt(dueDateTime), timeZone="UTC") if dueDateTime else None),
                 importance=importance or "normal", status="notStarted")
        self.s["todoTasks"].append(t)
        self._log("createTask", id=tid, listId=listId)
        return dict(success=True, id=tid)

    def todo_updateTask(self, listId, taskId, patch):
        self._list(listId)
        t = next((t for t in self.s["todoTasks"] if t["id"] == taskId and t["listId"] == listId), None)
        if not t:
            _err("ErrorItemNotFound", f"Task {taskId!r} not in list {listId!r}")
        for k, v in (patch or {}).items():
            if k == "dueDateTime":
                t[k] = dict(dateTime=_parse_dt(v), timeZone="UTC") if v else None
            elif k in ("title", "body", "importance", "status"):
                if k == "status" and v not in ("notStarted", "inProgress", "completed", "waitingOnOthers", "deferred"):
                    _err("BadPatch", "status must be notStarted|inProgress|completed|waitingOnOthers|deferred")
                t[k] = v
            else:
                _err("BadPatch", f"Unsupported field {k}")
        self._log("updateTask", id=taskId, patch=copy.deepcopy(patch))
        return dict(success=True, id=taskId)

    def todo_deleteTask(self, listId, taskId):
        self._list(listId)
        if not any(t["id"] == taskId for t in self.s["todoTasks"]):
            _err("ErrorItemNotFound", f"Task {taskId!r} not found")
        self.s["todoTasks"] = [t for t in self.s["todoTasks"] if t["id"] != taskId]
        self._log("deleteTask", id=taskId)
        return dict(success=True, id=taskId)

    # ------------------------------------------------------------ settings / identity
    def settings_getVacationResponder(self):
        return copy.deepcopy(self.s["settings"]["vacationResponder"])

    def settings_setVacationResponder(self, enabled, message=None, startDateTime=None, endDateTime=None, sendToContactsOnly=False):
        v = dict(enabled=bool(enabled), message=message or "", startDateTime=_parse_dt(startDateTime) if startDateTime else None,
                 endDateTime=_parse_dt(endDateTime) if endDateTime else None, sendToContactsOnly=bool(sendToContactsOnly))
        self.s["settings"]["vacationResponder"] = v
        self._log("setVacation", **v)
        return dict(success=True, **v)

    def settings_getSenderClassifications(self):
        return dict(value=copy.deepcopy(self.s["settings"]["senderClassifications"]))

    def settings_createSenderClassification(self, senderEmailAddress, classifyAs):
        if classifyAs not in ("focused", "other"):
            _err("BadRequest", "classifyAs must be 'focused' or 'other'")
        sc = self.s["settings"]["senderClassifications"]
        sc[:] = [x for x in sc if x["senderEmailAddress"].lower() != senderEmailAddress.lower()]
        cid = self._nid("sc")
        sc.append(dict(id=cid, senderEmailAddress=senderEmailAddress, classifyAs=classifyAs))
        self._log("senderClassification", id=cid, sender=senderEmailAddress, classifyAs=classifyAs)
        return dict(success=True, id=cid)

    def settings_getLabels(self):
        return dict(value=copy.deepcopy(self.s["labels"]))

    def getCurrentUser(self):
        me = self.s["me"]
        return dict(id=me["id"], displayName=me["name"], mail=me["address"], jobTitle=me["jobTitle"],
                    department=me["department"], officeLocation=me["officeLocation"])
