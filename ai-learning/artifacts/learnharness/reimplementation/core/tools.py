"""Tool objects (name, schema, prepareArguments, executionMode, execute), registries, and a mini agent-loop runner.
LLM / UI / real job tools are not implemented: read/ls/find/grep/research/pdf/demo/visual are inert stubs."""
import dataclasses
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

import plan
import probe
import qa
from messages import dangling_question_of, has_probe_done

logger = logging.getLogger("probe")


@dataclass
class Tool:
    name: str
    parameters: dict
    execute: Optional[Callable[[str, Any], Any]] = None
    prepare_arguments: Optional[Callable[[Any], Any]] = None
    execution_mode: Optional[str] = None


@dataclass
class ToolContext:
    chat_id: str
    chat_store: Any


@dataclass
class TeacherContext(ToolContext):
    search_available: bool = True


@dataclass
class ProberContext:
    chat_id: str
    chat_store: Any
    deliver: Callable[[dict], None]
    graph_store: Any = None
    search_available: bool = True


# ---- heal wrapper / agent-loop simulation -------------------------------------------------
def with_argument_heal(tool):
    inner = tool.prepare_arguments
    return dataclasses.replace(tool, prepare_arguments=lambda args: qa.heal_encoded_arguments(
        inner(args) if inner else args, tool.parameters))


def call_tool(tool, raw_args, tool_call_id="call-1", healed=True):
    """prepareArguments (tool's own) -> registry heal (healToolRecord wrap) -> schema validation -> execute.
    Schema failure: execute is not called."""
    t = with_argument_heal(tool) if healed else tool
    args = t.prepare_arguments(raw_args) if t.prepare_arguments else raw_args
    problems = qa.validate(tool.parameters, args)
    if problems:
        return {"executed": False, "result": qa.invalid_input_result(tool.name, problems)}
    return {"executed": True, "result": tool.execute(tool_call_id, args)}


# ---- question tools (tools.ts 79-95, 205-261, 375-391) -------------------------------------
def ask_user_question_tool():
    def execute(_id, inp):
        problems = qa.ask_option_problems(inp.get("options") or [])
        return qa.invalid_input_result("ask_user_question", problems) if problems else qa.question_result()
    return Tool("ask_user_question", qa.ASK_SCHEMA, execute, qa.prepare_question_arguments, "sequential")


def probe_tool():
    def execute(_id, inp):
        problems = qa.quiz_input_problems(inp)
        return qa.invalid_input_result("probe", problems) if problems else qa.question_result()
    return Tool("probe", qa.PROBE_SCHEMA, execute, qa.prepare_question_arguments, "sequential")


def recall_tool():
    def execute(_id, inp):
        problems = qa.explain_input_problems(inp)
        return qa.invalid_input_result("recall", problems) if problems else qa.question_result()
    return Tool("recall", qa.EXPLAIN_BASE_SCHEMA, execute, qa.prepare_question_arguments, "sequential")


def teach_quiz_tool(ctx):
    def execute(_id, inp):
        problems = list(qa.quiz_input_problems(inp))
        np_ = plan.node_id_problem(ctx, inp["nodeId"])
        if np_:
            problems.append(np_)
        return qa.invalid_input_result("quiz", problems) if problems else qa.question_result()
    return Tool("quiz", qa.QUIZ_SCHEMA, execute, qa.prepare_question_arguments, "sequential")


def teach_explain_tool(ctx):
    def execute(_id, inp):
        problems = list(qa.explain_input_problems(inp))
        np_ = plan.node_id_problem(ctx, inp["nodeId"])
        if np_:
            problems.append(np_)
        return qa.invalid_input_result("explain", problems) if problems else qa.question_result()
    return Tool("explain", qa.EXPLAIN_SCHEMA, execute, qa.prepare_question_arguments, "sequential")


# ---- probe_done (tools/probe.ts) ---------------------------------------------------------------
def probe_done_tool(ctx):
    def execute(_id, _inp):
        record = ctx.chat_store.get_chat(ctx.chat_id)
        if record is None:
            return {"ok": False, "error": f"Chat not found: {ctx.chat_id}"}
        if dangling_question_of(record["messages"]) is not None:  # open question is checked FIRST
            return {"ok": False, "error": (
                "A question is still open — resolve it (or let him answer) before concluding the probe. "
                "probe_done only fires with no question outstanding.")}
        if has_probe_done(record["messages"]):
            return {"ok": False, "error": "The probe is already concluded — probe_done fires exactly once."}
        try:
            ctx.deliver(probe.build_probe_handoff_steer(ctx.chat_id))
        except Exception as err:  # wake is an optimization, not a gate
            logger.error("[chat %s] probe handoff queueing failed: %s", ctx.chat_id, err)
        return {"text": probe.PROBE_DONE_ACK_TEXT, "details": {"ok": True}}
    return Tool("probe_done", probe.PROBE_DONE_SCHEMA, execute)


# ---- plan_init (tools/plan.ts) ---------------------------------------------------------------------
PLAN_NODE_IDS_REMINDER = ("These are the plan's node ids — the only valid nodeId values for every quiz and explain "
                          "call from here on. Reference them exactly.")


def plan_init_tool(ctx):
    import json

    def execute(_id, inp):
        record = ctx.chat_store.get_chat(ctx.chat_id)
        if record is None:
            return {"ok": False, "error": f"Chat not found: {ctx.chat_id}"}
        parsed = plan.parse_mermaid_plan(inp["mermaid"])
        if not parsed["ok"]:
            return {"ok": False, "error": "\n".join(parsed["problems"])}
        try:
            nxt = plan.create_tree(parsed["plan"]["nodes"], parsed["plan"]["edges"])
        except plan.PlanTreeError as err:
            return {"ok": False, "error": str(err)}
        ctx.chat_store.save_tree(ctx.chat_id, nxt)
        return {"text": json.dumps({"ok": True, "nodeIds": [n["id"] for n in nxt["nodes"]],
                                    "reminder": PLAN_NODE_IDS_REMINDER}, ensure_ascii=False, separators=(",", ":")),
                "details": {"ok": True, "tree": nxt}}
    schema = {"type": "object", "required": ["mermaid"], "properties": {"mermaid": {"type": "string", "minLength": 1}}}
    return Tool("plan_init", schema, execute)


# ---- registries (tools.ts 287-348, 422-466; pending.ts filterEnabledTools) -----------------------------
def _stub(name):
    return Tool(name, {"type": "object"}, None)


def filter_enabled_tools(tools, enabled=None):
    if not enabled:
        return dict(tools)
    return {n: t for n, t in tools.items() if enabled.get(n) is not False}


def quiz_mechanics(enabled=None):
    return "free" if enabled and enabled.get("explain") is True else "choice"


def _without_mechanics(enabled):
    if not enabled:
        return None
    return {k: v for k, v in enabled.items() if k not in ("explain", "quiz")}


def heal_tool_record(tools):
    return {n: with_argument_heal(t) for n, t in tools.items()}


def create_prober_tools(ctx, enabled=None):
    done = {"probe_done": probe_done_tool(ctx)}
    quizzing = {"recall": recall_tool()} if quiz_mechanics(enabled) == "free" else {"probe": probe_tool()}
    tools = {**quizzing, "ask_user_question": ask_user_question_tool(),
             **{n: _stub(n) for n in ("read", "ls", "find", "grep")},
             # R-12 per the spec: research is registered without a search provider (jobs.ts not opened)
             "research": _stub("research"), "pdf": _stub("pdf")}
    if ctx.graph_store is not None:
        tools.update({"list_sessions": _stub("list_sessions"), "list_propositions": _stub("list_propositions")})
    tools.update(done)
    return heal_tool_record({**filter_enabled_tools(tools, _without_mechanics(enabled)), **done})


def create_teacher_tools(ctx, enabled=None):
    quizzing = {"explain": teach_explain_tool(ctx)} if quiz_mechanics(enabled) == "free" else {"quiz": teach_quiz_tool(ctx)}
    tools = {**quizzing, "ask_user_question": ask_user_question_tool(),
             **{n: _stub(n) for n in ("read", "ls", "find", "grep")},
             "plan_init": plan_init_tool(ctx),
             **{n: _stub(n) for n in ("research", "demo", "visual", "pdf")}}
    return heal_tool_record(filter_enabled_tools(tools, _without_mechanics(enabled)))
