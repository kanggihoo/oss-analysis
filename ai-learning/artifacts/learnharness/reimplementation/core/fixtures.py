"""Test helpers: record/message builders (dict-shaped LhMessage)."""
from store import ChatStore


def assistant(*calls, text=None, mid="a"):
    content = []
    if text is not None:
        content.append({"type": "text", "text": text})
    for cid, name, args in calls:
        content.append({"type": "toolCall", "id": cid, "name": name, "arguments": args})
    return {"id": mid, "role": "assistant", "content": content}


def tool_result(cid, name, is_error=False, text="ok", details=None):
    return {"role": "toolResult", "toolCallId": cid, "toolName": name,
            "content": [{"type": "text", "text": text}], "details": details, "isError": is_error}


def user(text, mid="u"):
    return {"id": mid, "role": "user", "content": [{"type": "text", "text": text}]}


def opts(*vals):
    return [{"label": v.upper(), "value": v} for v in vals]


def probe_args(correct="a", values=("a", "b", "c"), **kw):
    d = {"question": "q?", "options": opts(*values), "explanation": "because",
         "correctAnswer": correct}
    d.update(kw)
    return d


def store_with(chat_id="c1", messages=None, tree=None):
    s = ChatStore()
    s.create_chat(chat_id, messages=messages or [], tree=tree)
    return s


def tree_of(*ids):
    return {"nodes": [{"id": i, "title": i} for i in ids], "edges": [], "version": 1}
