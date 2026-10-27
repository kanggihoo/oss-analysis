"""Native record helpers (native-messages.ts ranges in the 1.5 tables)."""
import itertools

import qa
from qa import QUESTION_TOOLS

INTERRUPTED_TEXT = ("The question was interrupted — the learner never answered; "
                    "continue without holding a result for it.")
HANDOFF_TEXT = (
    "Next: plan the full teaching arc from my current understanding to the goal understanding. "
    "Apply the teaching methodology in your system prompt, and find the optimal way to teach me this. "
    "Find the unconditional truths, plan the motivated derivations/discoveries, so every reasoning step has to land as obviously true. "
    "Take your time here and really think this through. "
    "When it's genuinely reasoned out, call plan_init and present the plan; I'll accept it or ask for changes.")

_ids = itertools.count(1)


def new_message_id():
    return f"m{next(_ids)}"


def result_ids_from(messages):
    # resultIdsFrom is outside the 1.5 ranges: inferred as the toolCallIds of toolResult messages.
    return {m["toolCallId"] for m in messages if m.get("role") == "toolResult"}


def new_answer_result(tool_call_id, tool_name, answer):
    import json
    return {"id": new_message_id(), "role": "toolResult", "toolCallId": tool_call_id, "toolName": tool_name,
            "content": [{"type": "text", "text": json.dumps(qa.compact_answer_for_model(answer), ensure_ascii=False, separators=(",", ":"))}],  # JSON.stringify style: no spaces
            "details": answer, "isError": False, "timestamp": 0}


def new_handoff_message(chat_id):
    return {"id": f"steer_probe_{chat_id}", "role": "custom", "customType": "probe-handoff",
            "content": HANDOFF_TEXT, "display": True, "details": {"chatId": chat_id}, "timestamp": 0}


def dangling_question_of(messages):
    for mi in range(len(messages) - 1, -1, -1):
        m = messages[mi]
        if m.get("role") != "assistant":
            continue
        answered = result_ids_from(messages[mi + 1:])
        for block in m["content"]:
            if block.get("type") != "toolCall" or block["name"] not in QUESTION_TOOLS:
                continue
            if block["id"] in answered:
                continue
            return {"toolCallId": block["id"], "tool": block["name"], "input": block.get("arguments")}
        return None  # newest assistant message: all questions answered
    return None


def has_probe_done(messages):
    return any(m.get("role") == "assistant" and any(
        b.get("type") == "toolCall" and b.get("name") == "probe_done" for b in m["content"]) for m in messages)


def is_dismissed_result(m):
    return m.get("role") == "toolResult" and (m.get("details") or {}).get("dismissed") is True


def ends_in_dismissal(messages):
    return bool(messages) and is_dismissed_result(messages[-1])


def to_llm_messages(messages):
    """Model input: custom markers become user text (plan-block / problem-dismissed are UI-only),
    record ids are stripped, and unanswered tool calls get a synthetic 'interrupted' result.
    Compaction (cut/head) is out of scope. The record is not modified."""
    out = []
    for i, m in enumerate(messages):
        role = m.get("role")
        if role == "custom":
            if m.get("customType") in ("plan-block", "problem-dismissed"):
                continue
            out.append({"role": "user", "content": [{"type": "text", "text": m["content"]}]})
            continue
        out.append({k: v for k, v in m.items() if k != "id"})
        if role == "assistant":
            calls = [b for b in m["content"] if b.get("type") == "toolCall"]
            answered = result_ids_from(messages[i + 1:])
            for call in calls:
                if call["id"] in answered:
                    continue
                out.append({"role": "toolResult", "toolCallId": call["id"], "toolName": call["name"],
                            "content": [{"type": "text", "text": INTERRUPTED_TEXT}], "isError": False})
    return out
