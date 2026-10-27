"""Prober pieces: probe_done constants/steer, graph reader formatting+gate, prompt segment assembly."""
import re

from messages import HANDOFF_TEXT, new_handoff_message  # noqa: F401  (HANDOFF_TEXT re-exported)

PROBE_DONE_ACK_TEXT = (
    "Assessment recorded — it is shown to the learner now and the teacher plans from it. "
    "Say your closing sentence and end your turn; the teaching phase takes over from here.")

PROBE_DONE_SCHEMA = {"type": "object", "required": ["assessment"], "properties": {"assessment": {
    "type": "object", "required": ["strands"], "properties": {
        "strands": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["strand", "assessment"],
            "properties": {"strand": {"type": "string"}, "assessment": {"type": "string"}}}},
        "summary": {"type": "string"}}}}}


def build_probe_handoff_steer(chat_id):
    return new_handoff_message(chat_id)


def steer_delivered(messages, steer_id):
    return any(m.get("id") == steer_id for m in messages)


# ---- graph reader (graph.ts 41-78; settings-resolution 249-254) ----------------------------
class GraphStore:
    """Marker object: 'a graph store was handed to the prober' (ctx.graphStore)."""


def graph_tools_enabled(effective):
    en = effective["agent"]["graphTools"].get("enabled")
    return bool(effective["graph"]["enabled"] and (True if en is None else en))


def sort_sessions(sessions):
    # graphSessionIndex order: updatedAt desc, createdAt desc, id asc (localeCompare approximated by plain compare)
    s = sorted(sessions, key=lambda x: x["id"])
    s.sort(key=lambda x: x.get("createdAt") or "", reverse=True)
    s.sort(key=lambda x: x.get("updatedAt") or "", reverse=True)
    return s


def list_sessions(sessions):
    if not sessions:
        return "The knowledge graph is empty — no session has contributed propositions yet."
    ordered = sort_sessions(sessions)
    lines = []
    for i, s in enumerate(ordered):
        n = s["propositions"]
        last = f", last active {s['updatedAt']}" if s.get("updatedAt") else ""
        lines.append(f"{i + 1}. {s['name']} ({s['kind']}, {n} proposition{'' if n == 1 else 's'}, "
                     f"born {s.get('createdAt') or 'unknown date'}{last}) — id: {s['id']}")
    return f"{len(ordered)} session(s) in the knowledge graph, most recent first:\n" + "\n".join(lines)


def list_propositions(by_session, session):
    props = sorted(by_session.get(session, []), key=lambda p: p["nodeId"])
    if not props:
        return f'No propositions born in session "{session}". Call list_sessions for the current ids.'
    return f"{len(props)} proposition(s) covered in this session:\n" + "\n".join(f"- {p['name']}" for p in props)


# ---- prompt assembly (prompt-segments.ts 62-97, teacher-agent.ts 74-81) -----------------------------
FRAGMENT_RE = re.compile(r"\d+-[\w.-]+\.md", re.ASCII)  # fullmatch: ^\d+-[\w.-]+\.md$


def list_source_segments(agent, files):
    """files: {dirname: [filenames]} stands in for the prompts directory listing."""
    segs = [{"path": "system-prompt.md", "shared": True}]
    for f in sorted(n for n in files.get(agent, []) if FRAGMENT_RE.fullmatch(n)):
        segs.append({"path": f"{agent}/{f}", "shared": False})
    for f in sorted(n for n in files.get("shared", []) if FRAGMENT_RE.fullmatch(n)):
        segs.append({"path": f"shared/{f}", "shared": True})
    return segs


def compose_instructions(segments, texts, overrides=None):
    overrides = overrides or {}
    parts = [overrides.get(s["path"], texts[s["path"]]).strip() for s in segments]
    return "\n\n---\n\n".join(p for p in parts if p)
