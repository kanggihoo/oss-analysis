"""Acceptance tests transcribed from practice-session.md 1.6 (T-01..T-16),
plus a few extra tests for guesses/edges. Test names carry the T-ID."""
import unittest

import practice as P

NODES = [{"id": "p1", "name": "Chain rule"}, {"id": "p2", "name": "Product rule"}]
GOOD = {"statement": "s", "mode": "recall", "modelSolution": "sol"}
CONCLUDE = {"outcome": "solved", "verdict": "v", "rung": None, "missClass": None, "retest": False}


# --- record-building helpers -------------------------------------------------
def call(cid, name, args=None):
    return {"role": "assistant", "content": [{"type": "toolCall", "id": cid, "name": name, "arguments": args or {}}]}


def result(cid, name, is_error=False):
    return {"role": "toolResult", "toolCallId": cid, "toolName": name,
            "content": [{"type": "text", "text": "x"}], "details": None, "isError": is_error}


def posed(cid="c1", args=None):
    return [call(cid, "problem", args or GOOD), result(cid, "problem")]


def concluded(cid="k1"):
    return [call(cid, "conclude", CONCLUDE), result(cid, "conclude")]


def marker(t, **details):
    return {"role": "custom", "customType": t, "content": "", "details": details}


def active_id(msgs):
    a = P.active_problem_of(msgs)
    return a["toolCallId"] if a else None


class ToolGateTests(unittest.TestCase):
    def test_T01_problem_while_active_is_rejected(self):
        tools = P.practice_tools(posed("c1"))
        r = tools["problem"].call(GOOD)
        self.assertTrue(r.is_error)
        self.assertIn("a problem is already active — call conclude on it before posing the next one", r.text)
        self.assertEqual(r.details["problems"], ["a problem is already active — call conclude on it before posing the next one"])

    def test_T02_conclude_without_active_problem_is_rejected(self):
        for msgs in ([], posed("c1") + concluded()):
            r = P.practice_tools(msgs)["conclude"].call(CONCLUDE)
            self.assertTrue(r.is_error)
            self.assertIn("no active problem to conclude — pose one first", r.text)

    def test_T03_conclude_then_problem_in_one_turn(self):
        tools = P.practice_tools(posed("c1"))
        self.assertFalse(tools["conclude"].call(CONCLUDE).is_error)
        self.assertFalse(tools["problem"].call(GOOD).is_error)
        # and the reverse direction: the closure is the truth, problem -> problem fails
        self.assertTrue(tools["problem"].call(GOOD).is_error)

    def test_T04_target_normalization_and_validation(self):
        t = P.practice_tools([], lambda: NODES)["problem"]
        a = dict(GOOD, target=["chain rule"])
        self.assertEqual(t.prepare(a)["target"], ["p1"])
        self.assertFalse(t.call(a).is_error)

        t = P.practice_tools([], lambda: NODES)["problem"]
        r = t.call(dict(GOOD, target=["zzz"]))
        self.assertTrue(r.is_error)
        self.assertIn('target ["zzz"] is not a known proposition', r.text)
        self.assertIn("omit target entirely", r.text)

        t = P.practice_tools([], lambda: NODES)["problem"]
        a = dict(GOOD, target=[])
        self.assertNotIn("target", t.prepare(a))
        self.assertFalse(t.call(a).is_error)

        t = P.practice_tools([], lambda: NODES)["problem"]
        self.assertFalse(t.call(dict(GOOD)).is_error)

    def test_T05_mode_schema_and_heal(self):
        t = P.practice_tools([])["problem"]
        self.assertTrue(t.call(dict(GOOD, mode="analysis")).is_error)
        t = P.practice_tools([])["problem"]
        a = dict(GOOD, mode='"recall"')
        self.assertEqual(t.prepare(a)["mode"], "recall")
        self.assertFalse(t.call(a).is_error)

    def test_T14_results(self):
        tools = P.practice_tools([])
        r = tools["problem"].call(GOOD)
        self.assertFalse(r.is_error)
        self.assertTrue(r.terminate)
        self.assertIsNone(r.details)
        self.assertEqual(r.text, "Problem posed — the turn ends here; the learner's thinking traces and answer commits arrive as labeled messages.")
        r = tools["conclude"].call(CONCLUDE)
        self.assertFalse(r.is_error)
        self.assertFalse(r.terminate)
        self.assertEqual(r.text, P.CONCLUDE_ACK_TEXT)
        # NOT TESTABLE here: "result stays in the record" (persist filter is outside the pure layer)


class ActiveProblemTests(unittest.TestCase):
    def test_T06_activeProblemOf(self):
        self.assertEqual(active_id(posed("c1")), "c1")
        self.assertIsNone(active_id(posed("c1") + concluded()))
        err = [call("k1", "conclude", CONCLUDE), result("k1", "conclude", True)]
        self.assertEqual(active_id(posed("c1") + err), "c1")
        self.assertIsNone(active_id(posed("c1") + [marker("problem-dismissed", problemCallId="c1")]))
        bad = [call("c1", "problem", GOOD), result("c1", "problem", True)]
        self.assertIsNone(active_id(bad))

    def test_T06_extra_dangling_calls_skipped_and_repose_after_dismissal(self):
        self.assertIsNone(active_id([call("c1", "problem", GOOD)]))  # no result at all
        m = posed("c1") + [marker("problem-dismissed", problemCallId="c1")] + posed("c2")
        self.assertEqual(active_id(m), "c2")
        m = posed("c1") + [call("c2", "problem", GOOD), result("c2", "problem", True)]
        self.assertEqual(active_id(m), "c1")  # errored pose "did not happen"

    def test_R09_within_one_message_later_block_wins(self):
        blocks = [{"type": "toolCall", "id": "k", "name": "conclude", "arguments": {}},
                  {"type": "toolCall", "id": "c2", "name": "problem", "arguments": GOOD}]
        m = posed("c1") + [{"role": "assistant", "content": blocks}, result("k", "conclude"), result("c2", "problem")]
        self.assertEqual(active_id(m), "c2")

    def test_T16_reveal_uses_nearest_clean_problem(self):
        rejected = {"statement": "s", "mode": "recall", "modelSolution": "REJECTED"}
        m = (posed("c0", dict(GOOD, modelSolution="CLEAN"))
             + [call("c1", "problem", rejected), result("c1", "problem", True)]
             + [call("k1", "conclude", CONCLUDE), result("k1", "conclude")])
        self.assertEqual(P.model_solution_for_conclude(m, "k1"), "CLEAN")
        # only rejected poses before it -> nothing to reveal
        m = [call("c1", "problem", rejected), result("c1", "problem", True),
             call("k1", "conclude", CONCLUDE), result("k1", "conclude")]
        self.assertIsNone(P.model_solution_for_conclude(m, "k1"))
        # newest of two clean ones
        m = posed("a", dict(GOOD, modelSolution="A")) + concluded("k0") + posed("b", dict(GOOD, modelSolution="B")) + concluded("k1")
        self.assertEqual(P.model_solution_for_conclude(m, "k1"), "B")
        self.assertEqual(P.model_solution_for_conclude(m, "k0"), "A")

    def test_R14_quirk_reveal_scans_whole_message_including_later_blocks(self):
        # code behaviour: conclude and a NEW problem in the same assistant message -> reveal is the NEW pose's solution
        blocks = [{"type": "toolCall", "id": "k", "name": "conclude", "arguments": {}},
                  {"type": "toolCall", "id": "c2", "name": "problem", "arguments": dict(GOOD, modelSolution="NEW")}]
        m = posed("c1", dict(GOOD, modelSolution="OLD")) + [{"role": "assistant", "content": blocks},
                                                            result("k", "conclude"), result("c2", "problem")]
        self.assertEqual(P.model_solution_for_conclude(m, "k"), "NEW")


class InputTests(unittest.TestCase):
    def rec(self, msgs, kind="practice"):
        r = {"messages": list(msgs)}
        if kind:
            r["kind"] = kind
        return r

    def run_input(self, rec, raw):
        out = P.handle_input(rec, raw)
        rec["messages"].extend(out.appends)
        return out

    def test_T07_thinking(self):
        rec = self.rec(posed("c1"))
        with self.assertRaisesRegex(P.ChatInputError, "thinking input targets no active problem"):
            P.handle_input(rec, {"type": "thinking", "problemCallId": "c2", "text": "hi"})
        with self.assertRaisesRegex(P.ChatInputError, "thinking input requires non-empty text"):
            P.handle_input(rec, {"type": "thinking", "problemCallId": "c1", "text": ""})
        with self.assertRaisesRegex(P.ChatInputError, "thinking input requires non-empty text"):
            P.handle_input(rec, {"type": "thinking", "problemCallId": "c1", "text": "  \n"})
        out = P.handle_input(rec, {"type": "thinking", "problemCallId": "c1", "text": "my work"})
        self.assertTrue(out.starts_turn)
        self.assertEqual(len(out.appends), 1)
        m = out.appends[0]
        self.assertEqual((m["customType"], m["content"]), ("practice-thinking", "Your thinking:\nmy work"))
        self.assertEqual(m["details"], {"problemCallId": "c1", "text": "my work"})
        self.assertEqual(P.ChatInputError("x").status, 400)

    def test_T07_no_active_problem(self):
        with self.assertRaisesRegex(P.ChatInputError, "targets no active problem"):
            P.handle_input(self.rec([]), {"type": "thinking", "problemCallId": "c1", "text": "hi"})

    def test_T08_next(self):
        with self.assertRaisesRegex(P.ChatInputError, "next input is a practice-session affordance"):
            P.handle_input(self.rec([], kind=None), {"type": "next"})
        with self.assertRaisesRegex(P.ChatInputError, "next input requires no active problem"):
            P.handle_input(self.rec(posed("c1")), {"type": "next"})
        out = P.handle_input(self.rec(posed("c1") + concluded()), {"type": "next"})
        self.assertTrue(out.starts_turn)
        self.assertEqual([m["customType"] for m in out.appends], ["practice-next"])
        self.assertEqual(out.appends[0]["content"], P.NEXT_PROBLEM_TEXT)
        # empty record is also "no active problem"
        self.assertTrue(P.handle_input(self.rec([]), {"type": "next"}).starts_turn)

    def test_T09_dismiss_problem_then_text_synthesizes_pair_once(self):
        rec = self.rec(posed("c1"))
        out = self.run_input(rec, {"type": "dismiss-problem", "problemCallId": "c1"})
        self.assertFalse(out.starts_turn)
        self.assertEqual([m["customType"] for m in out.appends], ["problem-dismissed"])
        self.assertEqual(out.appends[0]["details"], {"problemCallId": "c1"})

        out = self.run_input(rec, {"type": "text", "text": "hello"})
        self.assertTrue(out.starts_turn)
        self.assertEqual(len(out.appends), 3)
        asst, res, user = out.appends
        self.assertEqual(asst["role"], "assistant")
        blk = asst["content"][0]
        self.assertEqual((blk["type"], blk["name"], blk["id"], blk["arguments"]),
                         ("toolCall", "conclude", "call_conc_c1", {"outcome": "dismissed"}))
        self.assertEqual((res["role"], res["toolCallId"], res["toolName"], res["isError"]),
                         ("toolResult", "call_conc_c1", "conclude", False))
        self.assertEqual(res["content"][0]["text"], P.CONCLUDE_ACK_TEXT)
        self.assertEqual(res["details"], {"outcome": "dismissed", "problemCallId": "c1"})
        self.assertEqual(user["role"], "user")
        self.assertIsNone(active_id(rec["messages"]))

        out = self.run_input(rec, {"type": "text", "text": "again"})
        self.assertEqual([m["role"] for m in out.appends], ["user"])

    def test_T09_extra_pair_rides_every_non_silent_input_and_dismiss_requires_active(self):
        for raw in ({"type": "continue"}, {"type": "next"}):
            rec = self.rec(posed("c1"))
            self.run_input(rec, {"type": "dismiss-problem", "problemCallId": "c1"})
            out = P.handle_input(rec, raw)
            self.assertEqual(out.appends[0]["role"], "assistant", raw)
        # thinking after a dismissal: no active problem -> 400 (pair never reached)
        rec = self.rec(posed("c1"))
        self.run_input(rec, {"type": "dismiss-problem", "problemCallId": "c1"})
        with self.assertRaises(P.ChatInputError):
            P.handle_input(rec, {"type": "thinking", "problemCallId": "c1", "text": "x"})
        # dismiss twice / wrong id
        with self.assertRaisesRegex(P.ChatInputError, "dismiss-problem input targets no active problem"):
            P.handle_input(rec, {"type": "dismiss-problem", "problemCallId": "c1"})
        with self.assertRaisesRegex(P.ChatInputError, "dismiss-problem input targets no active problem"):
            P.handle_input(self.rec(posed("c1")), {"type": "dismiss-problem", "problemCallId": "zz"})

    def test_T09_text_input_must_be_nonempty(self):
        with self.assertRaisesRegex(P.ChatInputError, "text input requires non-empty text"):
            P.handle_input(self.rec([]), {"type": "text", "text": "   "})


class SessionTests(unittest.TestCase):
    def test_T10_graph_context_content(self):
        nodes = [{"id": i, "name": i} for i in "ABCD"]
        chains = [{"id": "ch1", "premises": ["B", "A"], "conclusion": "C"}, {"id": "ch2", "premises": ["A"], "conclusion": "D"}]
        picks = [{"id": i, "name": i, "statement": f"stmt {i}"} for i in "ABC"]
        chat, _ = P.create_session({"kind": "practice", "graphContext": {"propositions": picks}}, None, nodes, chains)
        m = chat["messages"][0]
        self.assertEqual((m["role"], m["customType"], m["display"]), ("custom", "graph-context", True))
        self.assertEqual(m["content"], "\n".join([
            "[Session context] — picked from the learner's knowledge map when starting this session:",
            "",
            "Propositions (id — name: statement; the problem tool's target field uses these ids):",
            "- [A] A: stmt A", "- [B] B: stmt B", "- [C] C: stmt C",
            "", "Reasoning chains among them (premises → conclusion):",
            "- A, B → C"]))
        self.assertEqual(m["details"]["chains"], ["A, B → C"])
        self.assertEqual(len(m["details"]["propositions"]), 3)

    def test_T10_singleton_chain_line(self):
        nodes = [{"id": "A", "name": "Alpha"}]
        picks = [{"id": "A", "name": "Alpha", "statement": "s"}]
        chat, _ = P.create_session({"graphContext": {"propositions": picks}}, None, nodes, [])
        self.assertIn("- Alpha (no premises)", chat["messages"][0]["content"])

    def test_T11_pick_missing_from_graph(self):
        picks = [{"id": "X", "name": "Ex", "statement": "sx"}]
        chat, _ = P.create_session({"graphContext": {"propositions": picks}}, None, [], [])
        c = chat["messages"][0]["content"]
        self.assertIn("- [X] Ex: sx", c)
        self.assertNotIn("Reasoning chains", c)

    def test_T12_pick_filtering_and_cap(self):
        mk = lambda i: {"id": f"i{i}", "name": f"n{i}", "statement": f"s{i}"}
        chat, _ = P.create_session({"graphContext": {"propositions": [mk(i) for i in range(70)]}}, None, [], [])
        self.assertEqual(len(chat["messages"][0]["details"]["propositions"]), 64)
        # filter happens BEFORE the cap: 3 bad + 70 good -> 64 good
        bad = [{"id": "b", "name": "b", "statement": 5}, {"id": "b"}, "str"]
        chat, _ = P.create_session({"graphContext": {"propositions": bad + [mk(i) for i in range(70)]}}, None, [], [])
        ids = [p["id"] for p in chat["messages"][0]["details"]["propositions"]]
        self.assertEqual(ids, [f"i{i}" for i in range(64)])
        # nothing valid -> no marker
        chat, _ = P.create_session({"graphContext": {"propositions": bad}}, None, [], [])
        self.assertEqual(chat["messages"], [])

    def test_R01_kind_and_model_stamp(self):
        chat, stamp = P.create_session({"kind": "practice"}, {"models": {"strong": {"model": {"provider": "p", "id": "m"}, "thinkingLevel": "high"}}}, [], [])
        self.assertEqual(chat["kind"], "practice")
        self.assertEqual(stamp, {"model": {"provider": "p", "id": "m"}, "thinkingLevel": "high"})
        chat, stamp = P.create_session({"kind": "Practice"}, None, [], [])
        self.assertNotIn("kind", chat)
        self.assertIsNone(stamp)

    def test_T13_no_extraction_in_practice(self):
        self.assertFalse(P.extraction_triggered({"kind": "practice"}, True))
        self.assertTrue(P.extraction_triggered({}, True))
        self.assertFalse(P.extraction_triggered({}, False))
        self.assertEqual(P.agent_kind({"kind": "practice"}), "practice")

    def test_T15_to_llm_messages(self):
        msgs = [marker("graph-context"), marker("problem-dismissed", problemCallId="c1"),
                {"role": "custom", "customType": "practice-thinking", "content": "Your thinking:\nx", "details": {}},
                {"role": "custom", "customType": "plan-block", "content": "pb"}]
        msgs[0]["content"] = "ctx"
        out = P.to_llm_messages(msgs)
        self.assertEqual([(m["role"], m["content"][0]["text"]) for m in out], [("user", "ctx"), ("user", "Your thinking:\nx")])

    def test_R19_dangling_call_gets_synthesized_result(self):
        out = P.to_llm_messages([call("c1", "problem", GOOD)])
        self.assertEqual([m["role"] for m in out], ["assistant", "toolResult"])
        self.assertEqual(out[1]["toolCallId"], "c1")
        self.assertEqual(out[1]["content"][0]["text"], P.INTERRUPTED_TEXT)
        self.assertEqual(len(P.to_llm_messages(posed("c1"))), 2)

    def test_R04_tool_and_prompt_composition(self):
        self.assertEqual(P.practice_tool_names(jobs=False, research=False, graph=False),
                         ["problem", "conclude", "read", "ls", "find", "grep"])
        self.assertEqual(P.practice_tool_names(jobs=True, research=True, graph=True)[6:],
                         ["research", "pdf", "list_sessions", "list_propositions"])
        self.assertEqual(P.practice_tool_names(jobs=True, research=False, graph=False)[6:], ["pdf"])
        segs = P.practice_prompt_segments(["10-doctrine.md", "00-base.md", "notes.txt"],
                                          ["40-formatting.md", "20-question-tools.md", "10-voice.md", "25-confidence.md",
                                           "16-mental-model.md", "15-accuracy.md"])
        self.assertEqual(segs, ["practice/00-base.md", "practice/10-doctrine.md", "shared/10-voice.md",
                                "shared/15-accuracy.md", "shared/16-mental-model.md", "shared/40-formatting.md"])


class HealAndSchemaTests(unittest.TestCase):
    def test_conclude_schema(self):
        c = P.practice_tools(posed("c1"))["conclude"]
        self.assertTrue(c.call({"outcome": "solved"}).is_error)  # all fields required
        c = P.practice_tools(posed("c1"))["conclude"]
        self.assertTrue(c.call(dict(CONCLUDE, outcome="won")).is_error)
        c = P.practice_tools(posed("c1"))["conclude"]
        self.assertTrue(c.call(dict(CONCLUDE, rung="R6")).is_error)
        c = P.practice_tools(posed("c1"))["conclude"]
        self.assertFalse(c.call(dict(CONCLUDE, outcome="dismissed")).is_error)  # R-07: schema accepts

    def test_conclude_heal(self):
        c = P.practice_tools(posed("c1"))["conclude"]
        p = c.prepare({"outcome": '"solvedWithHints"', "verdict": "v", "rung": '"R2"', "missClass": "null", "retest": "true"})
        self.assertEqual((p["outcome"], p["rung"], p["missClass"], p["retest"]), ("solvedWithHints", "R2", None, True))
        self.assertFalse(c.call({"outcome": '"solved"', "verdict": "v", "rung": "null", "missClass": "null", "retest": "false"}).is_error)

    def test_heal_passthrough_same_reference_and_verdict_untouched(self):
        a = dict(GOOD)
        self.assertIs(P.heal_encoded_arguments(a, P.PROBLEM_SCHEMA), a)
        a = dict(GOOD, statement="[1,2]", modelSolution="true")  # plain strings are never parsed
        self.assertEqual(P.heal_encoded_arguments(a, P.PROBLEM_SCHEMA), a)

    def test_target_string_json_array_is_healed(self):
        t = P.practice_tools([], lambda: NODES)["problem"]
        self.assertEqual(t.prepare(dict(GOOD, target='["Chain rule"]'))["target"], ["p1"])

    def test_target_debris_and_name_matching(self):
        self.assertEqual(P.resolve_target_id(":p1.", NODES), "p1")
        self.assertEqual(P.resolve_target_id('"`  CHAIN RULE `"', NODES), "p1")
        self.assertIsNone(P.resolve_target_id("   ", NODES))
        self.assertIsNone(P.resolve_target_id("chain  rule", NODES))  # inner whitespace untouched
        dup = [{"id": "a", "name": "X"}, {"id": "b", "name": "x"}]
        self.assertEqual(P.resolve_target_id("x", dup), "a")  # first in store order

    def test_without_graph_nodes_only_empty_array_removed(self):
        t = P.practice_tools([])["problem"]
        self.assertNotIn("target", t.prepare(dict(GOOD, target=[])))
        r = t.call(dict(GOOD, target=["zzz"]))  # no validation against a graph
        self.assertFalse(r.is_error)

    def test_target_non_array_with_graph_is_silently_dropped(self):
        # code behaviour, contradicts a literal reading of R-05 ("unresolvable strings are left for execute to reject")
        t = P.practice_tools([], lambda: NODES)["problem"]
        self.assertNotIn("target", t.prepare(dict(GOOD, target="zzz")))
        t = P.practice_tools([])["problem"]
        self.assertTrue(t.call(dict(GOOD, target="zzz")).is_error)  # no graph -> schema rejects

    def test_problem_schema_edges(self):
        t = lambda: P.practice_tools([])["problem"]
        self.assertTrue(t().call({"statement": "s", "mode": "recall"}).is_error)  # modelSolution missing
        self.assertFalse(t().call({"statement": "", "mode": "recall", "modelSolution": ""}).is_error)  # empty strings accepted
        self.assertTrue(t().call(dict(GOOD, target=[1])).is_error)
        self.assertFalse(t().call(dict(GOOD, extra=1)).is_error)  # extra fields tolerated (guess)

    def test_unknown_target_checked_after_active_gate(self):
        tools = P.practice_tools(posed("c1"), lambda: NODES)
        r = tools["problem"].call(dict(GOOD, target=["zzz"]))
        self.assertIn("already active", r.text)

    def test_failed_pose_keeps_gate_unchanged(self):
        tools = P.practice_tools([], lambda: NODES)
        self.assertTrue(tools["problem"].call(dict(GOOD, target=["zzz"])).is_error)
        self.assertTrue(tools["conclude"].call(CONCLUDE).is_error)  # still nothing active


if __name__ == "__main__":
    unittest.main()
