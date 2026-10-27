"""Pure state/validation logic of the learnharness practice session, written
from practice-session.md (1부) only. No LLM, UI, network.

Messages are plain dicts shaped like the spec's record:
  assistant {role, content:[{type:"toolCall"|"text", id, name, arguments}]}
  toolResult {role, toolCallId, toolName, content:[{type:"text",text}], details, isError}
  custom marker {role:"custom", customType, content, details, display}
  user {role:"user", content:[{type:"text", text}]}   (shape of user msg = guess)
"""
import json
import re
import time
import uuid
from collections import namedtuple
from dataclasses import dataclass
from typing import Any, Callable, Optional

# --- fixed strings (spec 1.3) --------------------------------------------------
CONCLUDE_ACK_TEXT = (
    "Problem concluded. Say your closing words about the learner's work if useful, then END YOUR TURN — "
    "no further tool calls. The next problem is NEVER posed here: it waits for the learner's explicit "
    "go-ahead (a *Next problem* message, or their own words asking for the next one). Between problems, "
    "answer their questions about the concluded one."
)
NEXT_PROBLEM_TEXT = (
    "[NEXT PROBLEM] — the learner's explicit go-ahead: pose the next problem now per the selection rules, "
    "or wrap the session in text if the arc is complete."
)
THINKING_LABEL = "Your thinking"
PROBLEM_POSED_TEXT = (
    "Problem posed — the turn ends here; the learner's thinking traces and answer commits arrive as labeled messages."
)
# from question-answer-contract (C-15), needed by to_llm_messages
INTERRUPTED_TEXT = "The question was interrupted — the learner never answered; continue without holding a result for it."
ALREADY_ACTIVE = "a problem is already active — call conclude on it before posing the next one"
NO_ACTIVE = "no active problem to conclude — pose one first"
UNKNOWN_TARGET = (
    "target {} is not a known proposition — targets must be proposition ids from the session context; "
    "if the material is not in the map, omit target entirely"
)


# --- helpers -------------------------------------------------------------------
_DEBRIS = " \t\r\n:.\"'`"


def strip_debris(s: str) -> str:
    # ponytail: JS \s also matches NBSP/BOM etc.; str.strip with ASCII set misses those
    return s.strip(_DEBRIS)


def _u16(s: str):  # JS default sort / `<` compare UTF-16 code units
    return s.encode("utf-16-be")


def resolve_target_id(target: str, nodes: list) -> Optional[str]:
    t = strip_debris(target)
    if not t:
        return None
    if any(n["id"] == t for n in nodes):
        return t
    low = t.lower()
    for n in nodes:
        if strip_debris(n["name"]).lower() == low:
            return n["id"]
    return None


@dataclass
class ToolResult:
    text: str
    is_error: bool = False
    details: Any = None
    terminate: bool = False


def invalid_input_result(tool: str, problems: list) -> ToolResult:
    text = f'Invalid tool input for tool "{tool}":\n' + "\n".join(f"- {p}" for p in problems)
    return ToolResult(text, True, {"tool": tool, "problems": problems})


class ChatInputError(Exception):
    status = 400


# --- schemas + heal (TypeBox-shaped) ---------------------------------------------
def _lit(*vals):
    return {"anyOf": [{"type": "null"} if v is None else {"const": v} for v in vals]}


PROBLEM_SCHEMA = {
    "required": ["statement", "mode", "modelSolution"],
    "properties": {
        "statement": {"type": "string"},
        "mode": _lit("recall", "discrimination", "composition"),
        "target": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "modelSolution": {"type": "string"},
    },
}
CONCLUDE_SCHEMA = {
    "required": ["outcome", "verdict", "rung", "missClass", "retest"],
    "properties": {
        "outcome": _lit("solved", "solvedWithHints", "movedOn", "surrendered", "dismissed"),
        "verdict": {"type": "string"},
        "rung": _lit("R0", "R1", "R2", "R3", "R4", "R5", None),
        "missClass": _lit("cue", "discrimination", "execution", "careless", "structural", None),
        "retest": {"type": "boolean"},
    },
}

_UNDEF = object()


def _literals(prop):
    if "anyOf" in prop:
        return [x for m in prop["anyOf"] for x in _literals(m)]
    return [prop["const"]] if "const" in prop else []


def _accepts_null(prop):
    return prop.get("type") == "null" or any(m.get("type") == "null" for m in prop.get("anyOf", []))


def _try_parse(raw):
    def bad(_):
        raise ValueError
    try:
        return json.loads(raw, parse_constant=bad)  # JS JSON.parse rejects NaN/Infinity
    except ValueError:
        return _UNDEF


def heal_encoded_arguments(args, schema):
    """JSON-string-encoded enum/null/bool/number/array -> real value, only when it fits the schema."""
    if not isinstance(args, dict):
        return args
    healed = None
    for key, prop in schema["properties"].items():
        raw = args.get(key)
        if not isinstance(raw, str):
            continue
        parsed = _try_parse(raw)
        fixed = _UNDEF
        lits = _literals(prop)
        if lits:
            if raw in lits:
                continue
            if parsed is not _UNDEF and any(type(parsed) is type(x) and parsed == x for x in lits):
                fixed = parsed
        if fixed is _UNDEF and _accepts_null(prop) and parsed is None:
            fixed = None
        t = prop.get("type")
        if fixed is _UNDEF and t == "boolean" and isinstance(parsed, bool):
            fixed = parsed
        if fixed is _UNDEF and t in ("number", "integer") and isinstance(parsed, (int, float)) and not isinstance(parsed, bool):
            fixed = parsed
        if fixed is _UNDEF and t == "array" and isinstance(parsed, list):
            fixed = parsed
        if fixed is not _UNDEF:
            if healed is None:
                healed = dict(args)
            healed[key] = fixed
    return healed if healed is not None else args


def _check(v, prop) -> bool:
    if "anyOf" in prop:
        return any(_check(v, m) for m in prop["anyOf"])
    if "const" in prop:
        return type(v) is type(prop["const"]) and v == prop["const"]
    t = prop.get("type")
    if t == "string":
        return isinstance(v, str)
    if t == "boolean":
        return isinstance(v, bool)
    if t == "null":
        return v is None
    if t == "array":
        return (isinstance(v, list) and len(v) >= prop.get("minItems", 0)
                and all(_check(x, prop["items"]) for x in v))
    return False


def validate(args, schema) -> list:
    if not isinstance(args, dict):
        return ["must be object"]
    problems = [f"must have required property '{k}'" for k in schema["required"] if k not in args]
    for k, prop in schema["properties"].items():
        if k in args and not _check(args[k], prop):
            problems.append(f"property '{k}' has an invalid value")
    return problems


# --- tools -----------------------------------------------------------------------
class PracticeGate:
    def __init__(self, active: bool):
        self.problem_active = active


class Tool:
    def __init__(self, name, schema, prepare, execute):
        self.name, self.schema, self.prepare, self._execute = name, schema, prepare, execute

    def call(self, raw_args) -> ToolResult:
        """prepareArguments -> heal -> schema validation -> execute (the agent loop's order)."""
        args = heal_encoded_arguments(self.prepare(raw_args), self.schema)  # registry-wide second heal
        problems = validate(args, self.schema)
        if problems:  # error text of the real validator is not in the spec: guess
            return ToolResult(f'Validation failed for tool "{self.name}":\n' + "\n".join(f"- {p}" for p in problems), True)
        return self._execute(args)


def create_practice_gate(messages) -> PracticeGate:
    return PracticeGate(active_problem_of(messages or []) is not None)


def _without(args, key):
    out = dict(args)
    out.pop(key, None)
    return out


def practice_tools(messages, graph_nodes: Optional[Callable[[], list]] = None) -> dict:
    """One call per turn: the gate is seeded once from the record, then the closure is the truth."""
    gate = create_practice_gate(messages)

    def prepare_problem(args):
        healed = heal_encoded_arguments(args, PROBLEM_SCHEMA)
        if not isinstance(healed, dict):
            return healed
        target = healed.get("target")
        if graph_nodes is None:
            return _without(healed, "target") if isinstance(target, list) and not target else healed
        if not isinstance(target, list) or not target:
            return _without(healed, "target")
        nodes = graph_nodes()
        norm = [(resolve_target_id(t, nodes) or t) if isinstance(t, str) else t for t in target]
        return healed if norm == target else {**healed, "target": norm}

    def exec_problem(inp):
        if gate.problem_active:
            return invalid_input_result("problem", [ALREADY_ACTIVE])
        if graph_nodes is not None and inp.get("target"):
            nodes = graph_nodes()
            unknown = [t for t in inp["target"] if resolve_target_id(t, nodes) is None]
            if unknown:
                lst = json.dumps(unknown, separators=(",", ":"), ensure_ascii=False)
                return invalid_input_result("problem", [UNKNOWN_TARGET.format(lst)])
        gate.problem_active = True
        return ToolResult(PROBLEM_POSED_TEXT, details=None, terminate=True)

    def exec_conclude(_inp):
        if not gate.problem_active:
            return invalid_input_result("conclude", [NO_ACTIVE])
        gate.problem_active = False
        return ToolResult(CONCLUDE_ACK_TEXT)

    return {
        "problem": Tool("problem", PROBLEM_SCHEMA, prepare_problem, exec_problem),
        "conclude": Tool("conclude", CONCLUDE_SCHEMA, lambda a: heal_encoded_arguments(a, CONCLUDE_SCHEMA), exec_conclude),
    }


def practice_tool_names(jobs: bool, research: bool, graph: bool) -> list:
    """Registry composition (R-04). `research` only matters when jobs is given (guess, see RESULT)."""
    names = ["problem", "conclude", "read", "ls", "find", "grep"]
    if jobs and research:
        names.append("research")
    if jobs:
        names.append("pdf")
    if graph:
        names += ["list_sessions", "list_propositions"]
    return names


_FRAGMENT_RE = re.compile(r"^\d+-.+\.md$")  # guess: FRAGMENT_RE is not in the cited ranges
_PRACTICE_SHARED = ["10-voice.md", "15-accuracy.md", "16-mental-model.md", "40-formatting.md"]


def practice_prompt_segments(practice_files: list, shared_files: list) -> list:
    """No system-prompt.md; practice/ fragments sorted, then the 4 allowed shared fragments sorted."""
    seg = [f"practice/{f}" for f in sorted(practice_files) if _FRAGMENT_RE.match(f)]
    seg += [f"shared/{f}" for f in sorted(shared_files) if _FRAGMENT_RE.match(f) and f in _PRACTICE_SHARED]
    return seg


def agent_kind(record) -> str:
    return "practice" if record.get("kind") == "practice" else "teach"  # non-practice branch: not in this spec


def compaction_kind(record) -> Optional[str]:
    return "practice" if record.get("kind") == "practice" else None  # other kinds: row 9, unwritten


def extraction_triggered(record, extraction_enabled: bool) -> bool:
    return record.get("kind") != "practice" and extraction_enabled


# --- record folds ----------------------------------------------------------------
def _clean_ids(messages) -> set:
    return {m["toolCallId"] for m in messages if m.get("role") == "toolResult" and not m.get("isError")}


def _blocks_rev(m):
    return reversed(m.get("content") or [])


def active_problem_of(messages):
    clean = _clean_ids(messages)
    for m in reversed(messages):
        role = m.get("role")
        if role == "custom":
            if m.get("customType") == "problem-dismissed":
                return None
        elif role == "assistant":
            for b in _blocks_rev(m):
                if b.get("type") != "toolCall":
                    continue
                if b["name"] == "conclude":
                    if b["id"] in clean:
                        return None
                    continue
                if b["name"] == "problem" and b["id"] in clean:
                    return {"toolCallId": b["id"], "input": b.get("arguments")}
    return None


def pending_problem_dismissal_of(messages) -> Optional[str]:
    clean = _clean_ids(messages)
    for m in reversed(messages):
        role = m.get("role")
        if role == "custom":
            if m.get("customType") == "problem-dismissed":
                return (m.get("details") or {}).get("problemCallId")
        elif role == "assistant":
            for b in _blocks_rev(m):
                if b.get("type") == "toolCall" and b["name"] in ("conclude", "problem") and b["id"] in clean:
                    return None
    return None


def problem_input_for_conclude(messages, conclude_call_id):
    mi = next((i for i, m in enumerate(messages) if m.get("role") == "assistant"
               and any(b.get("type") == "toolCall" and b["id"] == conclude_call_id for b in m["content"])), -1)
    if mi < 0:
        return None
    clean = _clean_ids(messages)
    for i in range(mi, -1, -1):
        m = messages[i]
        if m.get("role") != "assistant":
            continue
        for b in _blocks_rev(m):  # NB: includes blocks AFTER the conclude block in its own message (code quirk)
            if b.get("type") == "toolCall" and b["name"] == "problem" and b["id"] in clean:
                return b.get("arguments")
    return None


def model_solution_for_conclude(messages, conclude_call_id):
    inp = problem_input_for_conclude(messages, conclude_call_id)
    s = inp.get("modelSolution") if isinstance(inp, dict) else None
    return s if isinstance(s, str) else None


# --- markers -----------------------------------------------------------------------
def _marker(custom_type, content, details):
    return {"role": "custom", "customType": custom_type, "content": content, "display": True,
            "details": details, "timestamp": int(time.time() * 1000)}


def new_thinking_message(problem_call_id, text):
    return _marker("practice-thinking", f"{THINKING_LABEL}:\n{text}", {"problemCallId": problem_call_id, "text": text})


def new_next_message():
    return _marker("practice-next", NEXT_PROBLEM_TEXT, {})


def new_problem_dismissed_marker(problem_call_id):
    return _marker("problem-dismissed", "", {"problemCallId": problem_call_id})


def new_user_message(text):
    return {"role": "user", "content": [{"type": "text", "text": text}], "timestamp": int(time.time() * 1000)}


def concluded_by_dismissal_pair(problem_call_id):
    cid, now = f"call_conc_{problem_call_id}", int(time.time() * 1000)
    zero = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "totalTokens": 0}
    return [
        {"role": "assistant", "timestamp": now, "api": "faux", "provider": "synthetic", "model": "synthetic-conclude",
         "usage": zero, "stopReason": "toolUse",
         "content": [{"type": "toolCall", "id": cid, "name": "conclude", "arguments": {"outcome": "dismissed"}}]},
        {"role": "toolResult", "toolCallId": cid, "toolName": "conclude", "isError": False, "timestamp": now,
         "content": [{"type": "text", "text": CONCLUDE_ACK_TEXT}],
         "details": {"outcome": "dismissed", "problemCallId": problem_call_id}},
    ]


def to_llm_messages(messages) -> list:
    """Marker flattening + dangling-call synthesis. Compaction cut / leading system chrome: out of scope."""
    out = []
    for i, m in enumerate(messages):
        role = m.get("role")
        if role == "custom":
            if m.get("customType") in ("plan-block", "problem-dismissed"):
                continue
            out.append({"role": "user", "content": [{"type": "text", "text": m["content"]}], "timestamp": m.get("timestamp")})
            continue
        out.append({k: v for k, v in m.items() if k != "id"})
        if role == "assistant":
            answered = {x["toolCallId"] for x in messages[i + 1:] if x.get("role") == "toolResult"}
            for b in m["content"]:
                if b.get("type") == "toolCall" and b["id"] not in answered:
                    out.append({"role": "toolResult", "toolCallId": b["id"], "toolName": b["name"], "isError": False,
                                "content": [{"type": "text", "text": INTERRUPTED_TEXT}], "timestamp": m.get("timestamp")})
    return out


# --- inputs ------------------------------------------------------------------------
InputOutcome = namedtuple("InputOutcome", "appends starts_turn")


def _nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def parse_chat_input(raw) -> dict:
    if not isinstance(raw, dict):
        raise ChatInputError("input must be an object")
    t = raw.get("type")
    if t == "text":
        if not _nonempty_str(raw.get("text")):
            raise ChatInputError("text input requires non-empty text")
        return {"type": "text", "text": raw["text"]}
    if t == "continue":
        return {"type": "continue"}
    if t == "thinking":
        if not isinstance(raw.get("problemCallId"), str) or not raw["problemCallId"]:
            raise ChatInputError("thinking input requires problemCallId")
        if not _nonempty_str(raw.get("text")):
            raise ChatInputError("thinking input requires non-empty text")
        return {"type": "thinking", "problemCallId": raw["problemCallId"], "text": raw["text"]}
    if t == "next":
        return {"type": "next"}
    if t == "dismiss-problem":  # no shape validation specified: id mismatch falls out as "no active problem"
        return {"type": "dismiss-problem", "problemCallId": raw.get("problemCallId")}
    if t in ("answer", "dismiss"):
        raise NotImplementedError("question-answer inputs are out of scope here")
    raise ChatInputError(f"unknown input type: {t}")


def _dismissal_conclusion(messages) -> list:
    pid = pending_problem_dismissal_of(messages)
    return concluded_by_dismissal_pair(pid) if pid else []


def handle_input(record, raw) -> InputOutcome:
    """parse + validate + appends; starts_turn is False only for the silent dismiss-problem route."""
    inp = parse_chat_input(raw)
    msgs = record["messages"]
    t = inp["type"]
    if t == "dismiss-problem":
        active = active_problem_of(msgs)
        if not active or active["toolCallId"] != inp["problemCallId"]:
            raise ChatInputError("dismiss-problem input targets no active problem")
        return InputOutcome([new_problem_dismissed_marker(inp["problemCallId"])], False)
    if t == "text":
        return InputOutcome(_dismissal_conclusion(msgs) + [new_user_message(inp["text"])], True)
    if t == "continue":
        return InputOutcome(_dismissal_conclusion(msgs), True)
    if t == "thinking":
        active = active_problem_of(msgs)
        if not active or active["toolCallId"] != inp["problemCallId"]:
            raise ChatInputError("thinking input targets no active problem")
        return InputOutcome(_dismissal_conclusion(msgs) + [new_thinking_message(inp["problemCallId"], inp["text"])], True)
    # next
    if record.get("kind") != "practice":
        raise ChatInputError("next input is a practice-session affordance")
    if active_problem_of(msgs):
        raise ChatInputError("next input requires no active problem")
    return InputOutcome(_dismissal_conclusion(msgs) + [new_next_message()], True)


# --- session creation (R-01, R-02) ---------------------------------------------------
def chains_for_selection(nodes, chains) -> list:
    selected = {n["id"] for n in nodes}
    chained, included = set(), []
    for c in chains:
        if c["conclusion"] not in selected or not all(p in selected for p in c["premises"]):
            continue
        included.append({"id": c["id"], "premises": sorted(c["premises"], key=_u16), "conclusion": c["conclusion"]})
        chained.add(c["conclusion"])
        chained.update(c["premises"])
    for n in nodes:
        if n["id"] not in chained:  # a lone proposition becomes a chain whose id is the node id (spec silent)
            included.append({"id": n["id"], "premises": [], "conclusion": n["id"]})
    return sorted(included, key=lambda c: _u16(c["id"]))


def format_chain_line(chain, names: dict) -> str:
    name = lambda i: names[i]["name"] if i in names else i
    prem = ", ".join(name(p) for p in sorted(chain["premises"], key=_u16))
    return f"{prem} → {name(chain['conclusion'])}" if prem else f"{name(chain['conclusion'])} (no premises)"


def new_graph_context_message(picks, chain_lines):
    lines = [
        "[Session context] — picked from the learner's knowledge map when starting this session:",
        "",
        "Propositions (id — name: statement; the problem tool's target field uses these ids):",
        *[f"- [{p['id']}] {p['name']}: {p['statement']}" for p in picks],
    ]
    if chain_lines:
        lines += ["", "Reasoning chains among them (premises → conclusion):", *[f"- {c}" for c in chain_lines]]
    return _marker("graph-context", "\n".join(lines), {"propositions": picks, "chains": chain_lines})


def create_session(body, settings, graph_nodes, graph_chains):
    """-> (chat record, model stamp or None). `settings` = parsed settings record or None."""
    body = body if isinstance(body, dict) else {}
    title = body["title"] if isinstance(body.get("title"), str) else ""
    chat = {"id": f"chat_{int(time.time() * 1000):x}_{uuid.uuid4().hex[:8]}",
            "title": (title or "Untitled session").strip() or "Untitled session",  # titleFromPrompt: unknown, guessed identity
            "messages": []}
    if body.get("kind") == "practice":
        chat["kind"] = "practice"
    strong = ((settings or {}).get("models") or {}).get("strong")
    stamp = None
    if strong and strong.get("model"):
        stamp = {"model": {"provider": strong["model"]["provider"], "id": strong["model"]["id"]},
                 "thinkingLevel": strong.get("thinkingLevel")}
    raw = (body.get("graphContext") or {}).get("propositions") if isinstance(body.get("graphContext"), dict) else None
    picks = [p for p in raw if isinstance(p, dict) and all(isinstance(p.get(k), str) for k in ("id", "name", "statement"))][:64] if isinstance(raw, list) else []
    if picks:
        by_id = {n["id"]: n for n in graph_nodes}
        picked = [by_id[p["id"]] for p in picks if p["id"] in by_id]
        lines = [format_chain_line(c, by_id) for c in chains_for_selection(picked, graph_chains)]
        chat["messages"].append(new_graph_context_message(picks, lines))
    return chat, stamp
