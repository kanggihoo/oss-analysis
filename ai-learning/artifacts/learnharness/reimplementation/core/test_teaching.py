"""teaching-cycle.md 1.6 acceptance cases (T-01..T-08) + extra [강제] rules.
Names: test_TC_Txx_*; extras test_TC_Rxx_*."""
import unittest

import chat_server as cs
import plan
import qa
import probe
from fixtures import assistant, opts, store_with, tool_result, tree_of, user
from tools import (call_tool, create_teacher_tools, teach_explain_tool, teach_quiz_tool,
                   TeacherContext, ToolContext)


def quiz_args(**kw):
    d = {"type": "check", "nodeId": "a", "question": "q?", "options": opts("a", "b"),
         "explanation": "e", "correctAnswer": "a"}
    d.update(kw)
    return d


def ctx(tree=None):
    return ToolContext(chat_id="c1", chat_store=store_with(tree=tree or tree_of("a", "b")))


class T(unittest.TestCase):
    def test_TC_T01_type_or_nodeid_missing(self):
        tool = teach_quiz_tool(ctx())
        for missing in ("type", "nodeId"):
            args = quiz_args()
            del args[missing]
            r = call_tool(tool, args)
            self.assertFalse(r["executed"], missing)
        # explain too
        etool = teach_explain_tool(ctx())
        self.assertFalse(call_tool(etool, {"nodeId": "a", "question": "q", "correctAnswer": "x"})["executed"])
        self.assertFalse(call_tool(etool, {"type": "check", "question": "q", "correctAnswer": "x"})["executed"])
        self.assertTrue(call_tool(etool, {"type": "check", "nodeId": "a", "question": "q", "correctAnswer": "x"})["executed"])

    def test_TC_T02_type_enum(self):
        r = call_tool(teach_quiz_tool(ctx()), quiz_args(type="maybe"))
        self.assertFalse(r["executed"])
        self.assertFalse(call_tool(teach_quiz_tool(ctx()), quiz_args(type="Predict"))["executed"])
        self.assertTrue(call_tool(teach_quiz_tool(ctx()), quiz_args(type="predict"))["executed"])

    def test_TC_T03_quoted_type_is_healed(self):
        tool = teach_quiz_tool(ctx())
        r = call_tool(tool, quiz_args(type='"predict"'))
        self.assertTrue(r["executed"])
        self.assertIs(r["result"]["terminate"], True)
        r = call_tool(teach_explain_tool(ctx()), {"type": '"check"', "nodeId": "a", "question": "q", "correctAnswer": "x"})
        self.assertTrue(r["executed"])
        # healed value is what execute receives
        reg = create_teacher_tools(TeacherContext(chat_id="c1", chat_store=store_with(tree=tree_of("a"))))
        self.assertEqual(reg["quiz"].prepare_arguments(quiz_args(type='"predict"'))["type"], "predict")

    def test_TC_T04_reveal_rule(self):
        f = qa.question_needs_reveal
        self.assertIs(f("quiz", {"type": "check"}, "teach"), True)
        self.assertIs(f("quiz", {"type": "predict"}, "teach"), False)
        self.assertIs(f("explain", {}, "teach"), True)
        self.assertIs(f("quiz", {"type": "check"}, "plan"), False)
        self.assertIs(f("ask_user_question", {}, "teach"), False)
        self.assertIs(f("probe", {}, "probe"), False)
        # extras: recall/probe in teach never collapse; unknown type -> check; quoted predict normalizes
        self.assertIs(f("probe", {}, "teach"), False)
        self.assertIs(f("quiz", {"type": "weird"}, "teach"), True)
        self.assertIs(f("quiz", {"type": '"predict"'}, "teach"), False)
        self.assertIs(f("quiz", None, "teach"), True)
        self.assertIs(f("quiz", {"type": 7}, "teach"), True)

    def test_TC_T05_position_from_tags_regardless_of_type(self):
        msgs = [assistant(("1", "quiz", {"type": "predict", "nodeId": "a"})),
                assistant(("2", "quiz", {"type": "check", "nodeId": "a"})),
                assistant(("3", "explain", {"type": "check", "nodeId": "b"}))]
        st = plan.derive_plan_statuses(tree_of("a", "b"), msgs)
        self.assertEqual((st["current"], st["visited"]), ("b", {"a"}))

    def test_TC_T06_unknown_node_returns_error_same_turn(self):
        res = call_tool(teach_quiz_tool(ctx()), quiz_args(nodeId="nope"))["result"]
        self.assertIs(res["isError"], True)
        self.assertNotIn("terminate", res)
        stop = qa.make_question_stopper()
        self.assertFalse(stop(assistant(("k", "quiz", {})), [{"toolCallId": "k", "isError": True}]))

    def test_TC_T07_teacher_prompt_order(self):
        files = {"teacher": ["30-question-principles.md", "05-method.md", "50-demos.md", "10-planning.md",
                             "20-teaching.md", "40-jobs.md", "28-predictions.md"],
                 "shared": ["40-formatting.md", "10-voice.md", "15-accuracy.md", "16-mental-model.md",
                            "20-question-tools.md", "25-confidence.md", "30-learner-files.md"]}
        segs = [s["path"] for s in probe.list_source_segments("teacher", files)]
        self.assertEqual(segs, ["system-prompt.md"] +
                         [f"teacher/{n}" for n in ("05-method.md", "10-planning.md", "20-teaching.md", "28-predictions.md",
                                                  "30-question-principles.md", "40-jobs.md", "50-demos.md")] +
                         [f"shared/{n}" for n in ("10-voice.md", "15-accuracy.md", "16-mental-model.md", "20-question-tools.md",
                                                  "25-confidence.md", "30-learner-files.md", "40-formatting.md")])

    def test_TC_T08_extraction_sees_only_teacher_text(self):
        msgs = [user("learner msg", mid="u1"),
                assistant(("q", "quiz", quiz_args()), text="TEACHER PROSE", mid="a1"),
                tool_result("q", "quiz", text="LEARNER ANSWER TEXT"),
                assistant(text="more prose", mid="a2")]
        msgs[1]["content"].append({"type": "thinking", "thinking": "SECRET THOUGHT"})
        view = cs.prose_view(msgs)
        self.assertIn("TEACHER PROSE", view)
        self.assertIn("more prose", view)
        self.assertIn("a1", view)  # labeled with the actual message id
        for leak in ("learner msg", "LEARNER ANSWER", "SECRET THOUGHT", "question", "correctAnswer"):
            self.assertNotIn(leak, view)

    # ---- extras ----------------------------------------------------------------------
    def test_TC_R01_teacher_tool_set(self):
        tctx = TeacherContext(chat_id="c1", chat_store=store_with())
        names = set(create_teacher_tools(tctx))
        self.assertEqual(names, {"quiz", "ask_user_question", "read", "ls", "find", "grep", "plan_init",
                                 "research", "demo", "visual", "pdf"})
        free = set(create_teacher_tools(tctx, enabled={"explain": True}))
        self.assertEqual(free ^ names, {"quiz", "explain"})
        # quiz cannot be toggled off through the mechanics key
        self.assertIn("quiz", create_teacher_tools(tctx, enabled={"quiz": False}))
        # job tool toggle works
        self.assertNotIn("demo", create_teacher_tools(tctx, enabled={"demo": False}))

    def test_TC_R07_invalid_input_result_shape(self):
        res = qa.invalid_input_result("quiz", ["p1", "p2"])
        self.assertEqual(res["content"][0]["text"], 'Invalid tool input for tool "quiz":\n- p1\n- p2')
        self.assertEqual(res["details"], {"tool": "quiz", "problems": ["p1", "p2"]})
        self.assertIs(res["isError"], True)

    def test_TC_R02_probe_tools_have_no_type_or_node_id_requirement(self):
        # probe (prober) takes no type/nodeId: a probe call with neither passes
        from tools import probe_tool
        from fixtures import probe_args
        self.assertTrue(call_tool(probe_tool(), probe_args())["executed"])
        # teacher quiz option schema has no `description`; extra keys are tolerated (not rejected) - guess
        args = quiz_args(options=[{"label": "A", "value": "a", "description": "hint"}, {"label": "B", "value": "b"}])
        self.assertTrue(call_tool(teach_quiz_tool(ctx()), args)["executed"])


if __name__ == "__main__":
    unittest.main()
