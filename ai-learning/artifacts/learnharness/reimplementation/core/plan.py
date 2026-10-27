"""plan_init: mermaid subset parser, tree validation, derived position, phase machine, nodeId check."""
import re

# ---- tree (plan-tree.ts) ----------------------------------------------------------------------
class PlanTreeError(Exception):
    pass


def _assert_valid_node(node):
    if not isinstance(node.get("id"), str) or node["id"].strip() == "":
        raise PlanTreeError("Every node needs a non-empty `id` (a stable slug like 'chain-rule-intuition').")
    if not isinstance(node.get("title"), str) or node["title"].strip() == "":
        raise PlanTreeError(f'Node "{node["id"]}" needs a non-empty `title`.')


def _node_map(nodes):
    m = {}
    for n in nodes:
        _assert_valid_node(n)
        if n["id"] in m:
            raise PlanTreeError(f'Duplicate node id "{n["id"]}" — node ids must be unique.')
        m[n["id"]] = n
    return m


def _require_node(m, nid, what):
    if nid not in m:
        raise PlanTreeError(f'{what} references unknown node id "{nid}" — it is not in the tree.')


def _creates_cycle(edges, frm, to):
    adj = {}
    for e in edges:
        adj.setdefault(e["from"], []).append(e["to"])
    stack, seen = [to], set()
    while stack:
        cur = stack.pop()
        if cur == frm:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(adj.get(cur, []))
    return False


def _assert_valid_edge(frm, to, nodes, existing):
    m = _node_map(nodes)
    _require_node(m, frm, "Edge `from`")
    _require_node(m, to, "Edge `to`")
    if frm == to:
        raise PlanTreeError(f'Edge "{frm}" → "{to}" is a self-loop — a node can\'t require itself.')
    if any(e["from"] == frm and e["to"] == to for e in existing):
        raise PlanTreeError(f'Edge "{frm}" → "{to}" already exists — duplicate edges are not allowed.')
    if _creates_cycle(existing, frm, to):
        raise PlanTreeError(f'Edge "{frm}" → "{to}" would create a cycle: "{to}" already leads (directly or '
                            f'transitively) back to "{frm}". "from" must be understood before "to" — the tree is a DAG.')


def create_tree(nodes, edges):
    m = _node_map(nodes)
    for e in edges:
        _require_node(m, e["from"], "Edge `from`")
        _require_node(m, e["to"], "Edge `to`")
    accepted = []
    for e in edges:
        _assert_valid_edge(e["from"], e["to"], nodes, accepted)
        accepted.append({"from": e["from"], "to": e["to"]})
    return {"nodes": [dict(n) for n in nodes], "edges": accepted, "version": 1}


# ---- mermaid subset (mermaid-plan.ts) --------------------------------------------------------------
HEADER_RE = re.compile(r"(graph|flowchart)\s+(td|tb|lr|rl|bt)\s*", re.I)
SLUG_RE = re.compile(r"[a-z0-9]+([_-][a-z0-9]+)*")
ARROW_RE = re.compile(r"-->|==>|-\.->")
ENDPOINT_RE = re.compile(r"([^\s()\[\]]+)\s*(?:\[([^\[\]]*)\]|\(\s*\"([^\"]*)\"\s*\)|\(([^()]*)\))?")
_WS = "\t\n\v\f\r              " \
      "    　﻿"


def _t(s):
    return s.strip(_WS)


def _parse_endpoint(text):
    m = ENDPOINT_RE.fullmatch(_t(text))
    if not m or not m.group(1):
        return None
    label = next((g for g in (m.group(2), m.group(3), m.group(4)) if g is not None), "")
    label = _t(label)
    if len(label) >= 2 and ((label[0] == '"' and label[-1] == '"') or (label[0] == "'" and label[-1] == "'")):
        label = _t(label[1:-1])
    return {"id": m.group(1), "label": label}


def parse_mermaid_plan(mermaid):
    problems = []
    lines = re.split(r"\r?\n", mermaid)
    first = next((i for i, l in enumerate(lines) if len(_t(l)) > 0 and not _t(l).startswith("%%")), -1)
    if first == -1:
        return {"ok": False, "problems": ["The plan is empty — expected a `graph TD` block with nodes and `-->` requires-edges."]}
    header = _t(lines[first])
    if not HEADER_RE.fullmatch(header):
        problems.append(f"line {first + 1}: expected the header `graph TD` (or flowchart TD/TB) first, got `{header}`.")
    nodes, edges, seen = {}, [], set()

    def register(ep, line_no):
        i, label = ep["id"], ep["label"]
        if not SLUG_RE.fullmatch(i):
            problems.append(f"line {line_no}: node id `{i}` must be a lowercase slug (a-z, 0-9, joined by hyphens or "
                            f"underscores — e.g. `chain-rule-intuition`); ids are permanent and checks reference them.")
            return
        if i not in nodes:
            nodes[i] = label if label else i
        elif label and nodes[i] == i:
            nodes[i] = label

    for idx in range(first + 1, len(lines)):
        line, no = _t(lines[idx]), idx + 1
        if len(line) == 0 or line.startswith("%%"):
            continue
        segments = ARROW_RE.split(line)
        if len(segments) >= 2:
            eps, unreadable = [], False
            for seg in segments:
                ep = _parse_endpoint(seg)
                if ep is None:
                    problems.append(f"line {no}: can't read the edge `{line}` — expected `a[title] --> b[title]` "
                                    f"(chains like `a --> b --> c` are fine).")
                    unreadable = True
                    break
                eps.append(ep)
            if not unreadable:
                for ep in eps:
                    register(ep, no)
                for k in range(len(eps) - 1):
                    f, to = eps[k], eps[k + 1]
                    if f["id"] == to["id"]:
                        problems.append(f"line {no}: self-loop `{f['id']} --> {to['id']}` — a node can't require itself.")
                        continue
                    key = f"{f['id']}->{to['id']}"
                    if key not in seen:
                        seen.add(key)
                        edges.append({"from": f["id"], "to": to["id"]})
        else:
            node = _parse_endpoint(line)
            if node is None:
                problems.append(f"line {no}: can't parse `{line}` — ids are the strict part (lowercase slugs: a-z, 0-9, "
                                f"hyphens, underscores); node lines (`slug[title]`) and requires-edges (`a --> b`) are the "
                                f"accepted forms; subgraphs, styles, and classes are not part of the subset.")
                continue
            register(node, no)
    plan = {"nodes": [{"id": i, "title": t} for i, t in nodes.items()], "edges": edges}
    if problems:
        return {"ok": False, "problems": problems}
    if not plan["nodes"]:
        return {"ok": False, "problems": ["No nodes found — the plan needs at least one."]}
    return {"ok": True, "problems": [], "plan": plan}


# ---- derived position / phase (contracts/plan.ts, phases.ts) ------------------------------------------------
def derive_plan_statuses(tree, messages):
    ids = {n["id"] for n in tree["nodes"]}
    runs = []
    for m in messages:
        if m.get("role") != "assistant" or not isinstance(m.get("content"), list):
            continue
        for b in m["content"]:
            if b.get("type") != "toolCall" or b.get("name") not in ("quiz", "explain"):
                continue
            nid = (b.get("arguments") or {}).get("nodeId") if isinstance(b.get("arguments"), dict) else None
            if not isinstance(nid, str) or nid not in ids:
                continue
            if not runs or runs[-1] != nid:
                runs.append(nid)
    return {"current": runs[-1] if runs else None, "visited": set(runs[:-1])}


def derived_node_status(statuses, node_id):
    if statuses["current"] == node_id:
        return "current"
    if node_id in statuses["visited"]:
        return "visited"
    return "upcoming"


def _tagged_node_id(args):
    return isinstance(args, dict) and isinstance(args.get("nodeId"), str) and len(args["nodeId"]) > 0


def phase_at3(messages, up_to_index=None):
    phase = "probe"
    last = len(messages) - 1 if up_to_index is None else min(up_to_index, len(messages) - 1)
    for i in range(last + 1):
        m = messages[i]
        role = m.get("role")
        if role == "toolResult":
            if phase == "probe" and m.get("toolName") == "probe_done" and not m.get("isError"):
                phase = "plan"
        elif role == "assistant" and phase == "plan":
            for b in m.get("content", []):
                if b.get("type") == "toolCall" and b.get("name") in ("quiz", "explain") and _tagged_node_id(b.get("arguments")):
                    phase = "teach"
                    break
    return phase


def node_id_problem(ctx, node_id):
    record = ctx.chat_store.get_chat(ctx.chat_id)
    known = [n["id"] for n in ((record or {}).get("tree") or {}).get("nodes", [])]
    if node_id in known:
        return None
    head = f'nodeId "{node_id}" matches no node in this session\'s plan map. '
    if known:
        return head + f"Copy one of your plan_init slugs exactly ({', '.join(known[:5])}{', …' if len(known) > 5 else ''})."
    return head + "No plan map exists yet — call plan_init before posing quizzes."
