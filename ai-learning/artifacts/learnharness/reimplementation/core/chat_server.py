"""POST /api/chat input handling (input-events.ts, chat-handler.ts 280-303, 343-352)."""
from dataclasses import dataclass

import probe as _probe
from messages import (HANDOFF_TEXT, INTERRUPTED_TEXT, dangling_question_of, ends_in_dismissal,  # noqa: F401
                      has_probe_done, new_answer_result, new_message_id, to_llm_messages)
from qa import QUESTION_TOOLS, tool_question_kind  # noqa: F401


class ChatInputError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


@dataclass
class Response:
    status: int
    body: dict
    turn_started: bool = False


def _nonempty_str(v):
    return isinstance(v, str) and len(v) > 0


def parse_chat_input(inp):
    if not isinstance(inp, dict):
        raise ChatInputError("input must be an object")
    t = inp.get("type")
    if t == "text":
        if not isinstance(inp.get("text"), str) or not inp["text"].strip():
            raise ChatInputError("text input requires non-empty text")
        return {"type": "text", "text": inp["text"]}
    if t == "answer":
        if not _nonempty_str(inp.get("toolCallId")):
            raise ChatInputError("answer input requires toolCallId")
        if not isinstance(inp.get("answer"), dict):
            raise ChatInputError("answer input requires the graded answer object")
        return {"type": "answer", "toolCallId": inp["toolCallId"], "answer": inp["answer"]}
    if t == "continue":
        return {"type": "continue"}  # continuation fold is out of scope (inputAppends 'continue' case not in 1.5 range)
    raise ChatInputError(f"unknown input type: {t}")


def parse_dismiss_input(inp):
    if not isinstance(inp, dict):
        raise ChatInputError("input must be an object")
    if inp.get("type") != "dismiss":  # dismiss-problem (practice) is out of scope
        raise ChatInputError(f"unknown input type: {inp.get('type')}")
    if not _nonempty_str(inp.get("toolCallId")):
        raise ChatInputError("dismiss input requires toolCallId")
    answer = inp.get("answer")
    if not isinstance(answer, dict):
        raise ChatInputError("dismiss input requires the dismissal answer object")
    if answer.get("dismissed") is not True:
        raise ChatInputError("dismiss input's answer must be a dismissal (dismissed: true)")
    return {"type": "dismiss", "toolCallId": inp["toolCallId"], "answer": answer}


def input_appends(record, inp):
    if inp["type"] == "text":
        # dismissalConclusion(record) is outside the 1.5 ranges; plain user message here
        return [{"id": new_message_id(), "role": "user", "content": [{"type": "text", "text": inp["text"]}]}]
    if inp["type"] == "answer":
        pending = dangling_question_of(record["messages"])
        if pending is None or pending["toolCallId"] != inp["toolCallId"]:
            raise ChatInputError("answer input targets no pending question call")
        return [new_answer_result(inp["toolCallId"], pending["tool"], inp["answer"])]
    raise NotImplementedError("continue")


def dismiss_appends(record, inp):
    pending = dangling_question_of(record["messages"])
    if pending is None or pending["toolCallId"] != inp["toolCallId"]:
        raise ChatInputError("dismiss input targets no pending question call")
    if inp["answer"].get("kind") != tool_question_kind(pending["tool"]):
        raise ChatInputError("dismiss input's answer kind does not match the question")
    return [new_answer_result(inp["toolCallId"], pending["tool"], inp["answer"])]


class TurnRegistry:
    def __init__(self):
        self.running = set()

    def begin_turn(self, chat_id):
        if chat_id in self.running:
            return False
        self.running.add(chat_id)
        return True

    def end_turn(self, chat_id):
        self.running.discard(chat_id)


def handle_chat_request(store, chat_id, raw_input, turns=None):
    """Order follows chat-handler.ts 280-303: append -> parallel gate (save, no turn) -> one-turn guard ->
    write-ahead save -> turn starts. Returns Response; raises ChatInputError for 400/409."""
    turns = turns or TurnRegistry()
    record = store.get_chat(chat_id)
    if record is None:
        raise ChatInputError(f"Chat not found: {chat_id}", 404)
    inp = parse_chat_input(raw_input)
    appends = input_appends(record, inp)
    merged = record["messages"] + appends
    if inp["type"] == "answer" and dangling_question_of(merged) is not None:
        store.save_messages(chat_id, merged)
        return Response(200, {}, False)
    if not turns.begin_turn(chat_id):
        raise ChatInputError("A turn is already running for this session", 409)
    store.save_messages(chat_id, merged)  # write-ahead: persisted before the turn starts
    return Response(200, {"agent": select_agent(merged, record.get("kind"))}, True)


def handle_dismiss_request(store, chat_id, raw_input):
    record = store.get_chat(chat_id)
    if record is None:
        raise ChatInputError(f"Chat not found: {chat_id}", 404)
    appends = dismiss_appends(record, parse_dismiss_input(raw_input))
    store.save_messages(chat_id, record["messages"] + appends)
    return Response(200, {}, False)  # quiet path: no wake


def select_agent(messages, kind=None):
    if kind == "practice":
        return "practice"
    return "teacher" if has_probe_done(messages) else "prober"


def make_wake_deliver(store, chat_id):
    """Test double for the wake pipeline's deliver(steer): appends the steer unless its id is already in the record."""
    def deliver(steer):
        rec = store.get_chat(chat_id)
        if _probe.steer_delivered(rec["messages"], steer["id"]):
            return
        store.save_messages(chat_id, rec["messages"] + [steer])
    return deliver


def prose_view(messages, title=None):
    """Extraction view (teaching R-08): only assistant text blocks. Line format 'TEACHER [id] text' is taken from the
    proseView comment; messageViewLines itself is outside the 1.5 ranges (guess)."""
    lines = []
    for m in messages:
        if m.get("role") != "assistant":
            continue
        for b in m["content"]:
            if b.get("type") == "text" and b.get("text"):
                lines.append(f"TEACHER [{m.get('id')}] {b['text']}")
    head = f"# {title}\n\n" if title else ""
    return head + "\n\n".join(lines)
