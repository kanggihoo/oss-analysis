"""plan-tree.md 1.6 acceptance cases (T-01..T-15) + extra [강제] rules.
Names: test_PT_Txx_*; extras test_PT_Rxx_*."""
import json
import unittest

import plan
from fixtures import assistant, store_with, tool_result, tree_of, user
from tools import (call_tool, create_prober_tools, create_teacher_tools, plan_init_tool,
                   teach_explain_tool, teach_quiz_tool, ProberContext, TeacherContext, ToolContext)

REMINDER = ("These are the plan's node ids — the only valid nodeId values for every quiz and explain call "
            "from here on. Reference them exactly.")


def run_plan(mermaid, store=None, chat_id="c1"):
    store = store or store_with(chat_id)
    tool = plan_init_tool(ToolContext(chat_id=chat_id, chat_store=store))
    return store, call_tool(tool, {"mermaid": mermaid})


def titles(tree):
    return {n["id"]: n["title"] for n in tree["nodes"]}


def edges(tree):
    return [(e["from"], e["to"]) for e in tree["edges"]]


class T(unittest.TestCase):
    def test_PT_T01_chain_saved(self):
        store, r = run_plan("graph TD\n a[One] --> b[Two] --> c[Three]")
        res = r["result"]
        tree = store.get_chat("c1")["tree"]
        self.assertEqual([n["id"] for n in tree["nodes"]], ["a", "b", "c"])
        self.assertEqual(titles(tree), {"a": "One", "b": "Two", "c": "Three"})
        self.assertEqual(edges(tree), [("a", "b"), ("b", "c")])
        self.assertEqual(tree["version"], 1)
        self.assertEqual(json.loads(res["text"]), {"ok": True, "nodeIds": ["a", "b", "c"], "reminder": REMINDER})
        self.assertEqual(res["details"], {"ok": True, "tree": tree})
        self.assertTrue(all("summary" not in n for n in tree["nodes"]))

    def test_PT_T02_uppercase_id(self):
        store, r = run_plan("graph TD\n A --> b")
        res = r["result"]
        self.assertIs(res["ok"], False)
        self.assertIn("line 2:", res["error"])
        self.assertIn("node id `A` must be a lowercase slug", res["error"])
        self.assertIsNone(store.get_chat("c1")["tree"])

    def test_PT_T03_missing_header(self):
        store, r = run_plan("a --> b")
        res = r["result"]
        self.assertIs(res["ok"], False)
        self.assertTrue(res["error"].startswith("line 1: expected the header `graph TD`"))
        self.assertNotIn("No nodes found", res["error"])  # problem list wins over "no nodes"
        self.assertIsNone(store.get_chat("c1")["tree"])

    def test_PT_T04_cycle(self):
        store, r = run_plan("graph TD\n a --> b\n b --> a")
        res = r["result"]
        self.assertIs(res["ok"], False)
        self.assertIn('would create a cycle: "a" already leads (directly or transitively) back to "b"', res["error"])
        self.assertIsNone(store.get_chat("c1")["tree"])

    def test_PT_T05_self_loop(self):
        _, r = run_plan("graph TD\n a --> a")
        self.assertIn("line 2: self-loop `a --> a`", r["result"]["error"])

    def test_PT_T06_first_label_wins_unlabeled_gets_filled(self):
        store, _ = run_plan("graph TD\n a[One]\n a[Two]")
        self.assertEqual(titles(store.get_chat("c1")["tree"]), {"a": "One"})
        store, _ = run_plan("graph TD\n a\n a[Title]")
        self.assertEqual(titles(store.get_chat("c1")["tree"]), {"a": "Title"})
        store, _ = run_plan("graph TD\n a --> b\n b[Late]")
        self.assertEqual(titles(store.get_chat("c1")["tree"]), {"a": "a", "b": "Late"})

    def test_PT_T07_arrow_spellings_collapse(self):
        store, _ = run_plan("graph TD\n a-->b\n a ==> b\n a -.-> b")
        self.assertEqual(edges(store.get_chat("c1")["tree"]), [("a", "b")])

    def test_PT_T08_comments_and_blank_lines(self):
        store, _ = run_plan("\n%% top comment\ngraph TD\n\n %% c\n a --> b\n\n")
        tree = store.get_chat("c1")["tree"]
        self.assertEqual([n["id"] for n in tree["nodes"]], ["a", "b"])
        self.assertEqual(edges(tree), [("a", "b")])

    def test_PT_T09_slug_rules(self):
        _, r = run_plan("graph TD\n a-")
        self.assertIn("must be a lowercase slug", r["result"]["error"])
        store, r = run_plan("graph TD\n chain_rule --> chain-rule")
        self.assertEqual([n["id"] for n in store.get_chat("c1")["tree"]["nodes"]], ["chain_rule", "chain-rule"])
        for bad in ("a--b", "_a", "a_", "a.b", "a b c"):
            _, r = run_plan(f"graph TD\n {bad}")
            self.assertIs(r["result"]["ok"], False, bad)

    def test_PT_T10_position_derivation(self):
        tree = tree_of("a", "b", "c")
        msgs = [assistant(("1", "quiz", {"nodeId": "a"})), assistant(("2", "quiz", {"nodeId": "a"})),
                assistant(("3", "explain", {"nodeId": "b"})), assistant(("4", "quiz", {"nodeId": "없는-id"})),
                assistant(("5", "quiz", {"nodeId": "a"}))]
        st = plan.derive_plan_statuses(tree, msgs)
        self.assertEqual(st["current"], "a")
        self.assertEqual(st["visited"], {"a", "b"})
        self.assertEqual([plan.derived_node_status(st, n) for n in "abc"], ["current", "visited", "upcoming"])

    def test_PT_T11_no_tags_or_replaced_tree(self):
        st = plan.derive_plan_statuses(tree_of("a"), [user("hi"), assistant(("1", "read", {"nodeId": "a"}))])
        self.assertIsNone(st["current"])
        self.assertEqual(st["visited"], set())
        msgs = [assistant(("1", "quiz", {"nodeId": "old"})), assistant(("2", "quiz", {"nodeId": "new"}))]
        st = plan.derive_plan_statuses(tree_of("new"), msgs)
        self.assertEqual((st["current"], st["visited"]), ("new", set()))
        # deterministic, results/answers irrelevant, non-string nodeId ignored
        msgs = [assistant(("1", "quiz", {"nodeId": 5})), assistant(("2", "quiz", {})),
                tool_result("1", "quiz", is_error=True)]
        self.assertIsNone(plan.derive_plan_statuses(tree_of("a"), msgs)["current"])

    def test_PT_R09_return_trip_current_wins(self):
        msgs = [assistant(("1", "quiz", {"nodeId": "a"})), assistant(("2", "quiz", {"nodeId": "b"})),
                assistant(("3", "quiz", {"nodeId": "a"}))]
        st = plan.derive_plan_statuses(tree_of("a", "b"), msgs)
        self.assertEqual((st["current"], st["visited"]), ("a", {"a", "b"}))
        self.assertEqual(plan.derived_node_status(st, "a"), "current")
        # same node twice inside one assistant message folds too
        msgs = [assistant(("1", "quiz", {"nodeId": "a"}), ("2", "explain", {"nodeId": "a"}))]
        st = plan.derive_plan_statuses(tree_of("a"), msgs)
        self.assertEqual((st["current"], st["visited"]), ("a", set()))

    def test_PT_T12_node_id_validation_at_call_time(self):
        q = {"type": "check", "nodeId": "a", "question": "q", "options": [{"label": "A", "value": "a"}, {"label": "B", "value": "b"}],
             "explanation": "e", "correctAnswer": "a"}
        store = store_with(tree=None)
        tool = teach_quiz_tool(ToolContext(chat_id="c1", chat_store=store))
        res = call_tool(tool, q)["result"]
        self.assertIs(res["isError"], True)
        self.assertIn("nodeId \"a\" matches no node in this session's plan map. No plan map exists yet — call plan_init before posing quizzes.",
                      res["content"][0]["text"])
        store = store_with(tree=tree_of("x", "y"))
        tool = teach_quiz_tool(ToolContext(chat_id="c1", chat_store=store))
        res = call_tool(tool, {**q, "nodeId": "z"})["result"]
        self.assertIs(res["isError"], True)
        self.assertIn('nodeId "z" matches no node in this session\'s plan map. Copy one of your plan_init slugs exactly (x, y).',
                      res["content"][0]["text"])
        self.assertNotIn("terminate", res)
        # explain too, and it is merged with other problems into one list
        etool = teach_explain_tool(ToolContext(chat_id="c1", chat_store=store))
        res = call_tool(etool, {"type": "predict", "nodeId": "z", "question": "q", "correctAnswer": " "})["result"]
        self.assertEqual(res["content"][0]["text"].count("\n- "), 2)

    def test_PT_R10_truncates_to_five_and_sees_same_turn_plan_init(self):
        store = store_with(tree=tree_of(*"abcdefg"))
        ctx = ToolContext(chat_id="c1", chat_store=store)
        self.assertIn("(a, b, c, d, e, …)", plan.node_id_problem(ctx, "zz"))
        self.assertIsNone(plan.node_id_problem(ctx, "g"))
        # plan_init in the same turn is immediately visible to a following quiz
        store = store_with()
        ctx = ToolContext(chat_id="c1", chat_store=store)
        self.assertIsNotNone(plan.node_id_problem(ctx, "n1"))
        call_tool(plan_init_tool(ctx), {"mermaid": "graph TD\n n1 --> n2"})
        self.assertIsNone(plan.node_id_problem(ctx, "n1"))

    def test_PT_T13_phase_machine(self):
        ok = [assistant(("p", "probe_done", {})), tool_result("p", "probe_done")]
        err = [assistant(("p", "probe_done", {})), tool_result("p", "probe_done", is_error=True)]
        self.assertEqual(plan.phase_at3(ok), "plan")
        self.assertEqual(plan.phase_at3(err), "probe")
        self.assertEqual(plan.phase_at3([]), "probe")
        # untagged quiz does not cross into teach
        self.assertEqual(plan.phase_at3(ok + [assistant(("q", "quiz", {"question": "?"}))]), "plan")
        self.assertEqual(plan.phase_at3(ok + [assistant(("q", "quiz", {"nodeId": ""}))]), "plan")
        # tagged call -> teach, even if the call errored / was never answered
        msgs = ok + [assistant(("q", "quiz", {"nodeId": "a"})), tool_result("q", "quiz", is_error=True)]
        self.assertEqual(plan.phase_at3(msgs), "teach")
        self.assertEqual(plan.phase_at3(msgs, up_to_index=1), "plan")
        self.assertEqual(plan.phase_at3(msgs, up_to_index=2), "teach")  # the assistant message itself
        # probe-phase quiz with a nodeId before probe_done does not skip the plan stage
        early = [assistant(("q", "quiz", {"nodeId": "a"}))] + ok
        self.assertEqual(plan.phase_at3(early), "plan")
        # one-way: a later failing probe_done cannot move back
        self.assertEqual(plan.phase_at3(msgs + err), "teach")
        # explain also tags
        self.assertEqual(plan.phase_at3(ok + [assistant(("q", "explain", {"nodeId": "a"}))]), "teach")

    def test_PT_T14_chat_not_found(self):
        store = store_with()
        tool = plan_init_tool(ToolContext(chat_id="ghost", chat_store=store))
        self.assertEqual(call_tool(tool, {"mermaid": "graph TD\n a"})["result"], {"ok": False, "error": "Chat not found: ghost"})

    def test_PT_T15_forty_nodes_no_ceiling(self):
        lines = ["graph TD"] + [f" n{i} --> n{i + 1}" for i in range(39)]
        store, r = run_plan("\n".join(lines))
        self.assertEqual(len(store.get_chat("c1")["tree"]["nodes"]), 40)
        self.assertEqual(len(json.loads(r["result"]["text"])["nodeIds"]), 40)

    # ---- extra [강제] ------------------------------------------------------------
    def test_PT_R02_all_problems_collected_and_empty_cases(self):
        _, r = run_plan("graph TD\n A --> b\n c --> C\n a --> a")
        lines = r["result"]["error"].split("\n")
        self.assertEqual(len(lines), 3)
        self.assertTrue(all(l.startswith("line ") for l in lines))
        self.assertEqual(plan.parse_mermaid_plan("")["problems"],
                         ["The plan is empty — expected a `graph TD` block with nodes and `-->` requires-edges."])
        self.assertEqual(plan.parse_mermaid_plan("%% only comment\n\n")["problems"][0][:19], "The plan is empty —")
        self.assertEqual(plan.parse_mermaid_plan("graph TD")["problems"], ["No nodes found — the plan needs at least one."])
        # mermaid min length 1 is a schema rule
        self.assertFalse(call_tool(plan_init_tool(ToolContext("c1", store_with())), {"mermaid": ""})["executed"])

    def test_PT_R03_header_and_labels(self):
        for h in ("graph TD", "flowchart LR", "GRAPH tb", "graph   BT", "flowchart RL"):
            self.assertTrue(plan.parse_mermaid_plan(f"{h}\n a")["ok"], h)
        for h in ("graph", "graph XX", "digraph TD", "graph TD extra"):
            self.assertFalse(plan.parse_mermaid_plan(f"{h}\n a")["ok"], h)
        p = plan.parse_mermaid_plan('graph TD\n a["Quoted one"] --> b("Paren q") --> c(Plain paren)\n d[ \'sq\' ]')["plan"]
        self.assertEqual({n["id"]: n["title"] for n in p["nodes"]},
                         {"a": "Quoted one", "b": "Paren q", "c": "Plain paren", "d": "sq"})
        # unreadable edge / node lines
        self.assertIn("can't read the edge", plan.parse_mermaid_plan("graph TD\n a --> ")["problems"][0])
        self.assertIn("can't parse", plan.parse_mermaid_plan("graph TD\n subgraph x y")["problems"][0])
        self.assertFalse(plan.parse_mermaid_plan("graph TD\n a --> b\n style a fill:#f9f")["ok"])

    def test_PT_R04_structure_errors(self):
        with self.assertRaises(plan.PlanTreeError):
            plan.create_tree([{"id": "a", "title": "a"}, {"id": "a", "title": "a"}], [])
        with self.assertRaises(plan.PlanTreeError):
            plan.create_tree([{"id": "a", "title": "a"}], [{"from": "a", "to": "zz"}])
        with self.assertRaises(plan.PlanTreeError):
            plan.create_tree([{"id": "a", "title": "a"}], [{"from": "a", "to": "a"}])
        with self.assertRaises(plan.PlanTreeError):
            plan.create_tree([{"id": "a", "title": "a"}, {"id": "b", "title": "b"}],
                             [{"from": "a", "to": "b"}, {"from": "a", "to": "b"}])
        nodes = [{"id": x, "title": x} for x in "abc"]
        with self.assertRaises(plan.PlanTreeError) as cm:  # transitive cycle
            plan.create_tree(nodes, [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}, {"from": "c", "to": "a"}])
        self.assertIn("would create a cycle", str(cm.exception))
        t = plan.create_tree(nodes, [{"from": "a", "to": "b"}])
        self.assertEqual(t["version"], 1)

    def test_PT_R06_R08_replace_wholesale_updated_at_unchanged(self):
        store = store_with()
        store.get_chat("c1")["updatedAt"] = "T0"
        run_plan("graph TD\n a --> b", store)
        run_plan("graph TD\n x --> y", store)  # old ids vanish, accepted
        tree = store.get_chat("c1")["tree"]
        self.assertEqual([n["id"] for n in tree["nodes"]], ["x", "y"])
        self.assertEqual(tree["version"], 1)
        self.assertEqual(store.get_chat("c1")["updatedAt"], "T0")

    def test_PT_R01_plan_init_only_on_teacher_and_filter_semantics(self):
        ctx_p = ProberContext(chat_id="c1", chat_store=store_with(), deliver=lambda s: None)
        self.assertNotIn("plan_init", create_prober_tools(ctx_p))
        tctx = TeacherContext(chat_id="c1", chat_store=store_with())
        self.assertIn("plan_init", create_teacher_tools(tctx))
        # factory-level filter drops any explicitly-false name (see RESULT.md: spec R-01 says 'cannot be toggled off')
        self.assertNotIn("plan_init", create_teacher_tools(tctx, enabled={"plan_init": False}))

    def test_PT_R11_quiz_in_probe_phase_never_a_tag_before_plan(self):
        # first tagged call is the seam, not later ones
        ok = [assistant(("p", "probe_done", {})), tool_result("p", "probe_done")]
        msgs = ok + [assistant(("q1", "quiz", {"nodeId": "a"}), mid="m1"), assistant(("q2", "quiz", {"nodeId": "b"}), mid="m2")]
        self.assertEqual(plan.phase_at3(msgs, up_to_index=1), "plan")
        self.assertEqual(plan.phase_at3(msgs, up_to_index=2), "teach")


if __name__ == "__main__":
    unittest.main()
