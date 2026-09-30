"""The 46 evaluated tools (paper Table 34) as JSON-schema function definitions + dispatcher."""
from __future__ import annotations

import json

from .api import APIError, EmailBenchAPI

S = lambda d="": {"type": "string", "description": d}
I = lambda d="": {"type": "integer", "description": d}
B = lambda d="": {"type": "boolean", "description": d}
O = lambda d="": {"type": "object", "description": d, "additionalProperties": True}
A = lambda d="", items=None: {"type": "array", "description": d, "items": items or {"type": "string"}}
RECIPS = A("Recipient email addresses", {"type": "string"})

_T = [
    ("messages_list", "List messages (all folders unless folderId given). Supports OData filter, orderBy, top, skip.",
     dict(top=I("Max results (default 10, max 100)"), filter=S("OData filter, e.g. isRead eq false and from/emailAddress/address eq 'x@y.com'"),
          orderBy=S("e.g. receivedDateTime desc"), skip=I("Offset for paging"), folderId=S("Folder id or well-known name (inbox, sentitems, ...)")), []),
    ("messages_get", "Get a single message with full body and attachments.", dict(id=S()), ["id"]),
    ("messages_search", "Full-text search over subject, body, sender, recipients.", dict(query=S(), top=I()), ["query"]),
    ("messages_count", "Count messages matching an OData filter.", dict(filter=S()), []),
    ("messages_send", "Send a new email.", dict(subject=S(), body=S(), toRecipients=RECIPS, ccRecipients=RECIPS, importance=S("low|normal|high")), ["subject", "body", "toRecipients"]),
    ("messages_createDraft", "Create a draft email.", dict(subject=S(), body=S(), toRecipients=RECIPS), ["subject", "body"]),
    ("messages_update", "Update message properties (isRead, importance, flag, categories).", dict(id=S(), patch=O("Fields to change")), ["id", "patch"]),
    ("messages_move", "Move a message to a folder.", dict(id=S(), destinationFolderId=S()), ["id", "destinationFolderId"]),
    ("messages_delete", "Delete a message (moves to Deleted Items).", dict(id=S()), ["id"]),
    ("messages_reply", "Reply to the sender of a message.", dict(id=S(), comment=S()), ["id", "comment"]),
    ("messages_replyAll", "Reply to all recipients of a message.", dict(id=S(), comment=S()), ["id", "comment"]),
    ("messages_forward", "Forward a message.", dict(id=S(), toRecipients=RECIPS, comment=S()), ["id", "toRecipients"]),
    ("messages_batchMove", "Move multiple messages to a folder.", dict(ids=A("Message ids"), destinationFolderId=S()), ["ids", "destinationFolderId"]),
    ("folders_list", "List all mail folders.", {}, []),
    ("folders_get", "Get a folder by id.", dict(id=S()), ["id"]),
    ("folders_getByName", "Find folders by display name.", dict(name=S()), ["name"]),
    ("folders_create", "Create a mail folder (optionally under a parent).", dict(displayName=S(), parentFolderId=S()), ["displayName"]),
    ("folders_rename", "Rename a folder.", dict(id=S(), newName=S()), ["id", "newName"]),
    ("folders_delete", "Delete a folder.", dict(id=S()), ["id"]),
    ("filters_list", "List inbox filters (rules).", {}, []),
    ("filters_create", "Create an inbox filter.", dict(name=S(), isEnabled=B(), criteria=O("e.g. {fromAddresses:[...], subjectContains:[...], bodyContains:[...], importance:'high'}"),
                                                       actions=O("e.g. {moveToFolder: folderId, markAsRead: true, assignCategories:[...], delete: true}")), ["name", "criteria", "actions"]),
    ("filters_update", "Update an inbox filter.", dict(id=S(), patch=O()), ["id", "patch"]),
    ("filters_delete", "Delete an inbox filter.", dict(id=S()), ["id"]),
    ("calendar_list", "List calendar events, optionally within a time window.", dict(top=I(), startDateTime=S("ISO 8601"), endDateTime=S("ISO 8601")), []),
    ("calendar_get", "Get an event by id.", dict(id=S()), ["id"]),
    ("calendar_create", "Create a calendar event.", dict(subject=S(), start=S("ISO 8601 UTC"), end=S("ISO 8601 UTC"), location=S(), attendees=RECIPS, body=S(), isAllDay=B()), ["subject", "start", "end"]),
    ("calendar_update", "Update an event.", dict(id=S(), patch=O()), ["id", "patch"]),
    ("calendar_delete", "Delete an event.", dict(id=S()), ["id"]),
    ("calendar_accept", "Accept a meeting invitation.", dict(id=S(), comment=S()), ["id"]),
    ("calendar_decline", "Decline a meeting invitation.", dict(id=S(), comment=S()), ["id"]),
    ("contacts_list", "List contacts.", dict(top=I()), []),
    ("contacts_search", "Search contacts by name, email, company, department or title.", dict(query=S()), ["query"]),
    ("contacts_create", "Create a contact.", dict(displayName=S(), givenName=S(), surname=S(), emailAddresses=A(), companyName=S(), department=S(), jobTitle=S()), ["displayName"]),
    ("contacts_delete", "Delete a contact.", dict(id=S()), ["id"]),
    ("todo_lists", "List to-do lists.", {}, []),
    ("todo_createList", "Create a to-do list.", dict(displayName=S()), ["displayName"]),
    ("todo_tasks", "List tasks in a to-do list.", dict(listId=S()), ["listId"]),
    ("todo_createTask", "Create a task in a to-do list.", dict(listId=S(), title=S(), body=S(), dueDateTime=S("ISO 8601"), importance=S("low|normal|high")), ["listId", "title"]),
    ("todo_updateTask", "Update a task (title, status, dueDateTime, importance, body).", dict(listId=S(), taskId=S(), patch=O()), ["listId", "taskId", "patch"]),
    ("todo_deleteTask", "Delete a task.", dict(listId=S(), taskId=S()), ["listId", "taskId"]),
    ("settings_getVacationResponder", "Get automatic-reply (vacation) settings.", {}, []),
    ("settings_setVacationResponder", "Set automatic-reply (vacation) settings.", dict(enabled=B(), message=S(), startDateTime=S(), endDateTime=S(), sendToContactsOnly=B()), ["enabled"]),
    ("settings_getSenderClassifications", "Get Focused/Other sender classifications.", {}, []),
    ("settings_createSenderClassification", "Always classify a sender as focused or other.", dict(senderEmailAddress=S(), classifyAs=S("focused|other")), ["senderEmailAddress", "classifyAs"]),
    ("settings_getLabels", "List category labels.", {}, []),
    ("getCurrentUser", "Get the signed-in user's profile.", {}, []),
]
assert len(_T) == 46, len(_T)

TOOL_NAMES = [t[0] for t in _T]


def tool_schemas():
    """Responses-API function tool definitions."""
    out = []
    for name, desc, props, req in _T:
        out.append(dict(type="function", name=name, description=desc,
                        parameters=dict(type="object", properties=props, required=req), strict=False))
    return out


def call_tool(api: EmailBenchAPI, name: str, args, max_chars=8000):
    """Execute a tool; returns (result_text, ok, raw)."""
    if name not in TOOL_NAMES:
        res = dict(error=dict(code="UnknownTool", message=f"Unknown tool {name}"))
        return json.dumps(res), False, res
    if isinstance(args, str):
        try:
            args = json.loads(args or "{}")
        except json.JSONDecodeError as e:
            res = dict(error=dict(code="BadArguments", message=f"Arguments are not valid JSON: {e}"))
            return json.dumps(res), False, res
    args = {k: v for k, v in (args or {}).items() if v is not None}
    try:
        raw = getattr(api, name)(**args)
        ok = True
    except APIError as e:
        raw, ok = dict(error=dict(code=e.code, message=e.message)), False
    except TypeError as e:
        raw, ok = dict(error=dict(code="BadArguments", message=str(e))), False
    txt = json.dumps(raw, default=str)
    if len(txt) > max_chars:
        txt = txt[:max_chars] + "...[truncated]"
    return txt, ok, raw
