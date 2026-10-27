"""question-answer-contract.md 1.6 acceptance cases (T-01..T-16) + extra [강제] rules.
Test names carry the spec's T-ID: test_QA_Txx_*; extras are test_QA_Rxx_*."""
import json
import unittest

import chat_server as cs
import qa
from fixtures import assistant, opts, probe_args, store_with, tool_result, user
from tools import (ask_user_question_tool, call_tool, probe_tool, recall_tool,
                   teach_explain_tool, teach_quiz_tool, ToolContext)


def probe_qd(call_id="call-1", **kw):
    return qa.make_question_data("probe", call_id, probe_args(**kw))


def pos(qd, value):
    return [o["value"] for o in qd["options"]].index(value) + 1


class T(unittest.TestCase):
    # ---- T-01..T-03: answer objects -------------------------------------
    def test_QA_T01_probe_correct_with_confidence_and_thinking(self):
        qd = probe_qd()
        ad = qa.build_answer(qd, {"values": ["a"], "confidence": 90, "thinking": "x"}, "probe")
        self.assertIs(ad["correct"], True)
        self.assertEqual(ad["confidence"], 90)
        idx = pos(qd, "a")
        self.assertEqual(ad["answers"][0]["index"], idx)
        compact = qa.compact_answer_for_model(ad)
        self.assertEqual(compact, {"kind": "quiz", "answers": [{"index": idx, "label": "A"}],
                                   "correct": True, "confidence": 90, "thinking": "x"})
        msg = cs.new_answer_result("call-1", "probe", ad)  # R-11
        self.assertEqual(json.loads(msg["content"][0]["text"]), compact)
        self.assertEqual(msg["content"][0]["text"], '{"kind":"quiz","answers":[{"index":%d,"label":"A"}],'
                         '"correct":true,"confidence":90,"thinking":"x"}' % idx)  # JSON.stringify-style, code key order
        self.assertEqual(msg["details"], ad)
        self.assertEqual((msg["role"], msg["toolName"], msg["isError"]), ("toolResult", "probe", False))

    def test_QA_T02_dont_know(self):
        qd = probe_qd()
        ad = qa.build_answer(qd, {"dontKnow": True, "confidence": 80}, "probe")
        self.assertIs(ad["dontKnow"], True)
        self.assertIs(ad["correct"], False)
        self.assertNotIn("confidence", ad)
        self.assertEqual(qa.compact_answer_for_model(ad), {"kind": "quiz", "dontKnow": True})

    def test_QA_T03_multiselect_exact_set(self):
        qd = qa.make_question_data("probe", "c", probe_args(correct=["a", "b"], multiSelect=True))
        self.assertIs(qa.build_answer(qd, {"values": ["a", "b"]})["correct"], True)
        self.assertIs(qa.build_answer(qd, {"values": ["a"]})["correct"], False)
        self.assertIs(qa.build_answer(qd, {"values": ["a", "b", "c"]})["correct"], False)

    # ---- T-04..T-07: input validation ------------------------------------
    def test_QA_T04_correct_answer_not_in_options(self):
        r = call_tool(probe_tool(), probe_args(correct="z"))
        self.assertTrue(r["executed"])
        res = r["result"]
        self.assertIs(res["isError"], True)
        self.assertNotIn("terminate", res)  # turn does not end
        text = res["content"][0]["text"]
        self.assertIn('Valid values: "a", "b", "c"', text)
        # stopper: an erroring question call must not end the turn (R-07)
        stop = qa.make_question_stopper()
        msg = assistant(("k1", "probe", {}))
        self.assertFalse(stop(msg, [{"toolCallId": "k1", "isError": True}]))

    def test_QA_T05_duplicate_option_values(self):
        args = probe_args(values=("x",))
        args["options"] = [{"label": "A", "value": "x"}, {"label": "B", "value": "x"}]
        args["correctAnswer"] = "x"
        res = call_tool(probe_tool(), args)["result"]
        self.assertIs(res["isError"], True)
        self.assertIn('Two options resolve to the same value "x"', res["content"][0]["text"])

    def test_QA_T06_multiple_correct_without_multiselect(self):
        res = call_tool(probe_tool(), probe_args(correct=["a", "b"]))["result"]
        self.assertIs(res["isError"], True)
        self.assertIn("multiSelect is not true", res["content"][0]["text"])

    def test_QA_T07_prefix_colon_stripped_but_exact_key_wins(self):
        res = call_tool(probe_tool(), probe_args(correct=":a"))["result"]
        self.assertFalse(res.get("isError"))
        self.assertIs(res["terminate"], True)
        # option whose value is exactly ":a" -> exact match is kept
        args = probe_args(correct=":a", values=(":a", "b"))
        res = call_tool(probe_tool(), args)["result"]
        self.assertIs(res["terminate"], True)
        qd = qa.make_question_data("probe", "c", args)
        self.assertEqual([qd["options"][i - 1]["value"] for i in qd["correctIndices"]], [":a"])

    # ---- T-08: recall -----------------------------------------------------
    def test_QA_T08_recall_answer(self):
        inp = {"question": "why?", "correctAnswer": "because X"}
        self.assertIs(call_tool(recall_tool(), inp)["result"]["terminate"], True)
        qd = qa.make_question_data("recall", "c", inp)
        ad = qa.build_answer(qd, {"text": "  my words  "}, "recall")
        self.assertEqual((ad["kind"], ad["text"], ad["committed"]), ("explain", "my words", "because X"))
        self.assertNotIn("correct", ad)
        self.assertEqual(qa.compact_answer_for_model(ad), {"kind": "explain", "text": "my words"})
        # R-06: blank correctAnswer rejected
        res = call_tool(recall_tool(), {"question": "q", "correctAnswer": "   "})["result"]
        self.assertIs(res["isError"], True)

    # ---- T-09: answer targets no pending call ------------------------------
    def test_QA_T09_answer_without_pending(self):
        store = store_with(messages=[user("hi")])
        before = list(store.get_chat("c1")["messages"])
        ans = {"type": "answer", "toolCallId": "nope", "answer": {"kind": "quiz"}}
        with self.assertRaises(cs.ChatInputError) as cm:
            cs.handle_chat_request(store, "c1", ans)
        self.assertEqual(cm.exception.status, 400)
        self.assertIn("answer input targets no pending question call", str(cm.exception))
        self.assertEqual(store.get_chat("c1")["messages"], before)
        # different id than the pending one
        store = store_with(messages=[assistant(("k1", "probe", probe_args()))])
        before = list(store.get_chat("c1")["messages"])
        with self.assertRaises(cs.ChatInputError):
            cs.handle_chat_request(store, "c1", {"type": "answer", "toolCallId": "k2", "answer": {}})
        self.assertEqual(store.get_chat("c1")["messages"], before)

    def test_QA_R10_answer_must_be_object_and_content_not_validated(self):
        store = store_with(messages=[assistant(("k1", "probe", probe_args()))])
        with self.assertRaises(cs.ChatInputError):
            cs.handle_chat_request(store, "c1", {"type": "answer", "toolCallId": "k1", "answer": "a"})
        # content is not re-graded: nonsense confidence/correct are stored as-is in details
        weird = {"kind": "quiz", "correct": True, "confidence": 777}
        resp = cs.handle_chat_request(store, "c1", {"type": "answer", "toolCallId": "k1", "answer": weird})
        self.assertTrue(resp.turn_started)
        self.assertEqual(store.get_chat("c1")["messages"][-1]["details"], weird)

    # ---- T-10, T-11: compact form ------------------------------------------
    def test_QA_T10_dismissed_hides_everything_else(self):
        ad = {"kind": "ask", "dismissed": True, "readingThinking": "r", "answers": [], "dontKnow": False,
              "questionText": "q"}
        self.assertEqual(qa.compact_answer_for_model(ad), {"kind": "ask", "dismissed": True})
        msg = cs.new_answer_result("k", "ask_user_question", ad)
        self.assertEqual(msg["details"]["readingThinking"], "r")

    def test_QA_T11_legacy_note_and_reading_thinking_key(self):
        ad = {"kind": "quiz", "note": "n", "readingThinking": "r", "answers": [], "dontKnow": False}
        self.assertEqual(qa.compact_answer_for_model(ad),
                         {"kind": "quiz", "thinking": "n", "thinkingWhileReading": "r"})

    def test_QA_R12_robust_to_foreign_shapes(self):
        self.assertEqual(qa.compact_answer_for_model({"kind": "quiz", "answers": "oops"}), {"kind": "quiz"})
        self.assertEqual(qa.compact_answer_for_model({"kind": "quiz"}), {"kind": "quiz"})
        # correct omitted when dontKnow even if present
        self.assertEqual(qa.compact_answer_for_model({"kind": "quiz", "dontKnow": True, "correct": False}),
                         {"kind": "quiz", "dontKnow": True})
        # empty text is not shown; other/text shown when set
        self.assertEqual(qa.compact_answer_for_model({"kind": "ask", "text": "", "other": "o"}),
                         {"kind": "ask", "other": "o"})

    # ---- T-12: parallel gate ------------------------------------------------
    def test_QA_T12_parallel_questions_gate(self):
        store = store_with(messages=[assistant(("k1", "probe", probe_args()), ("k2", "ask_user_question", {"question": "?"}))])
        r1 = cs.handle_chat_request(store, "c1", {"type": "answer", "toolCallId": "k1", "answer": {"kind": "quiz"}})
        self.assertFalse(r1.turn_started)
        msgs = store.get_chat("c1")["messages"]
        self.assertEqual([m["role"] for m in msgs], ["assistant", "toolResult"])
        self.assertEqual(msgs[-1]["toolCallId"], "k1")
        r2 = cs.handle_chat_request(store, "c1", {"type": "answer", "toolCallId": "k2", "answer": {"kind": "ask"}})
        self.assertTrue(r2.turn_started)
        msgs = store.get_chat("c1")["messages"]
        self.assertEqual([m.get("toolCallId") for m in msgs[1:]], ["k1", "k2"])

    # ---- T-13: shuffle ------------------------------------------------------
    def test_QA_T13_seeded_shuffle_deterministic_and_correct_indices(self):
        options = qa.normalize_options(opts("a", "b", "c", "d", "e"))
        o1 = qa.shuffle_options(options, qa.seeded_random("tool-call-xyz"))
        o2 = qa.shuffle_options(options, qa.seeded_random("tool-call-xyz"))
        self.assertEqual(o1, o2)
        self.assertEqual(sorted(o["value"] for o in o1), ["a", "b", "c", "d", "e"])
        # different seeds should be able to differ (sanity over several ids)
        orders = {tuple(o["value"] for o in qa.shuffle_options(options, qa.seeded_random(f"id-{i}"))) for i in range(20)}
        self.assertGreater(len(orders), 1)
        qd = qa.make_question_data("probe", "c-1", probe_args(correct="b", values=("a", "b", "c")))
        self.assertEqual(qd["correctIndices"], [pos(qd, "b")])
        # the input option list is not mutated (display order only)
        self.assertEqual([o["value"] for o in options], ["a", "b", "c", "d", "e"])

    def test_QA_R14_only_quiz_kinds_shuffled(self):
        o = opts("a", "b", "c", "d", "e", "f", "g", "h")
        ask = qa.make_question_data("ask_user_question", "id-1", {"question": "q", "options": o})
        self.assertEqual([x["value"] for x in ask["options"]], list("abcdefgh"))
        orders = set()
        for i in range(10):
            qd = qa.make_question_data("probe", f"id-{i}", probe_args(values=tuple("abcdefgh")))
            orders.add(tuple(x["value"] for x in qd["options"]))
        self.assertGreater(len(orders), 1)

    # ---- T-14: confidence clamp --------------------------------------------
    def test_QA_T14_confidence_clamp_round(self):
        qd = probe_qd()
        self.assertEqual(qa.build_answer(qd, {"values": ["a"], "confidence": 130})["confidence"], 100)
        self.assertEqual(qa.build_answer(qd, {"values": ["a"], "confidence": 49.6})["confidence"], 50)
        self.assertEqual(qa.build_answer(qd, {"values": ["a"], "confidence": -5})["confidence"], 0)
        # js Math.round semantics: .5 rounds up
        self.assertEqual(qa.build_answer(qd, {"values": ["a"], "confidence": 62.5})["confidence"], 63)
        # confidence only for quiz
        ask_qd = qa.make_question_data("ask_user_question", "i", {"question": "q"})
        self.assertNotIn("confidence", qa.build_answer(ask_qd, {"text": "t", "confidence": 50}))

    # ---- T-15: options as JSON string --------------------------------------
    def test_QA_T15_options_string_unwrapped(self):
        args = {"question": "q", "options": json.dumps([{"label": "A"}, {"label": "B"}])}
        r = call_tool(ask_user_question_tool(), args)
        self.assertTrue(r["executed"])
        self.assertIs(r["result"]["terminate"], True)
        # probe with string options also validates
        a2 = probe_args()
        a2["options"] = json.dumps(a2["options"])
        self.assertTrue(call_tool(probe_tool(), a2)["executed"])
        # unparseable string -> left alone -> schema rejects, execute not called
        bad = call_tool(ask_user_question_tool(), {"question": "q", "options": "not json"})
        self.assertFalse(bad["executed"])
        # JSON that is not an array also stays a string -> rejected
        bad = call_tool(ask_user_question_tool(), {"question": "q", "options": '{"a":1}'})
        self.assertFalse(bad["executed"])

    # ---- T-16: dismiss -------------------------------------------------------
    def test_QA_T16_dismiss_kind_must_match(self):
        store = store_with(messages=[assistant(("k1", "ask_user_question", {"question": "q"}))])
        bad = {"type": "dismiss", "toolCallId": "k1", "answer": {"dismissed": True, "kind": "quiz"}}
        with self.assertRaises(cs.ChatInputError) as cm:
            cs.handle_dismiss_request(store, "c1", bad)
        self.assertEqual(cm.exception.status, 400)
        self.assertEqual(len(store.get_chat("c1")["messages"]), 1)
        good = {"type": "dismiss", "toolCallId": "k1", "answer": {"dismissed": True, "kind": "ask"}}
        resp = cs.handle_dismiss_request(store, "c1", good)
        self.assertFalse(resp.turn_started)
        last = store.get_chat("c1")["messages"][-1]
        self.assertEqual(last["toolCallId"], "k1")
        self.assertTrue(cs.ends_in_dismissal(store.get_chat("c1")["messages"]))
        # not a dismissal / no pending / no object
        with self.assertRaises(cs.ChatInputError):
            cs.parse_dismiss_input({"type": "dismiss", "toolCallId": "k1", "answer": {"dismissed": False}})
        with self.assertRaises(cs.ChatInputError):
            cs.handle_dismiss_request(store, "c1", good)  # already answered -> not pending

    # ---- extra [강제] rules ---------------------------------------------------
    def test_QA_R03_blank_label_and_distinct_keys(self):
        self.assertEqual(len(qa.ask_option_problems([{"label": "  "}, {"label": "B"}])), 1)
        # key = value.trim() || label.trim(); "a" label vs value "a" collide
        probs = qa.ask_option_problems([{"label": "a"}, {"label": "B", "value": " a "}])
        self.assertEqual(len(probs), 1)
        # value blank falls back to label
        probs = qa.ask_option_problems([{"label": "a"}, {"label": "a", "value": "  "}])
        self.assertEqual(len(probs), 1)
        # an invalid ask is an error result and the turn does not end
        res = call_tool(ask_user_question_tool(), {"question": "q", "options": [{"label": "A"}, {"label": " "}]})["result"]
        self.assertIs(res["isError"], True)
        self.assertNotIn("terminate", res)

    def test_QA_R04_correct_answer_required_and_json_array_string(self):
        self.assertTrue(any("required" in p for p in qa.quiz_input_problems(
            {"options": opts("a", "b"), "correctAnswer": [], "multiSelect": True})))
        self.assertTrue(any("required" in p for p in qa.quiz_input_problems(
            {"options": opts("a", "b"), "correctAnswer": "  "})))
        # multi-select given as JSON string
        self.assertEqual(qa.quiz_input_problems(
            {"options": opts("a", "b", "c"), "correctAnswer": '["a","b"]', "multiSelect": True}), [])
        # repeated value counts once
        self.assertEqual(qa.quiz_input_problems(
            {"options": opts("a", "b"), "correctAnswer": ["a", "a"]}), [])

    def test_QA_R05_strip_only_ends_not_inside(self):
        keys = ["a b", "x"]
        self.assertEqual(qa.coerce_correct_answer(' "a b". ', keys), ["a b"])
        self.assertEqual(qa.coerce_correct_answer("a:b", keys), ["a:b"])  # inner untouched
        self.assertEqual(qa.coerce_correct_answer("`x`", keys), ["x"])
        # exact key that itself ends with a period is preserved
        self.assertEqual(qa.coerce_correct_answer("Done.", ["Done."]), ["Done."])
        # exact key that looks like a JSON array
        self.assertEqual(qa.coerce_correct_answer('["a"]', ['["a"]']), ['["a"]'])
        # invalid JSON array-looking string is a single literal
        self.assertEqual(qa.coerce_correct_answer("[a, b]", ["a"]), ["[a, b]"])

    def test_QA_R07_stopper_mixed_batch(self):
        stop = qa.make_question_stopper()
        msg = assistant(("q1", "probe", {}), ("r1", "read", {}))
        ok = [{"toolCallId": "q1"}, {"toolCallId": "r1"}]
        self.assertTrue(stop(msg, ok))
        self.assertFalse(stop(msg, [{"toolCallId": "q1", "isError": True}, {"toolCallId": "r1"}]))
        # error in a non-question call does not block
        self.assertTrue(stop(msg, [{"toolCallId": "q1"}, {"toolCallId": "r1", "isError": True}]))
        # no question call -> no end
        self.assertFalse(stop(assistant(("r1", "read", {})), [{"toolCallId": "r1"}]))
        # placeholder: terminate + fixed text, not stored (details None)
        res = qa.question_result()
        self.assertEqual((res["details"], res["terminate"]), (None, True))
        self.assertTrue(res["content"][0]["text"].startswith("Question posed"))

    def test_QA_R08_question_tools_sequential(self):
        ctx = ToolContext(chat_id="c1", chat_store=store_with())
        for t in (probe_tool(), recall_tool(), ask_user_question_tool(), teach_quiz_tool(ctx), teach_explain_tool(ctx)):
            self.assertEqual(t.execution_mode, "sequential")

    def test_QA_R09_pending_is_first_unanswered_in_newest_assistant(self):
        msgs = [assistant(("old", "probe", {}), mid="a1"), tool_result("old", "probe"),
                assistant(("r1", "read", {}), ("q1", "probe", {"x": 1}), ("q2", "ask_user_question", {}), mid="a2")]
        p = cs.dangling_question_of(msgs)
        self.assertEqual((p["toolCallId"], p["tool"]), ("q1", "probe"))
        msgs.append(tool_result("q1", "probe"))
        self.assertEqual(cs.dangling_question_of(msgs)["toolCallId"], "q2")
        msgs.append(tool_result("q2", "ask_user_question"))
        self.assertIsNone(cs.dangling_question_of(msgs))
        # an older unanswered call does not count once a newer assistant message exists
        msgs2 = [assistant(("q0", "probe", {}), mid="a1"), assistant(("r1", "read", {}), mid="a2")]
        self.assertIsNone(cs.dangling_question_of(msgs2))
        self.assertEqual(set(cs.QUESTION_TOOLS), {"quiz", "probe", "ask_user_question", "explain", "recall"})
        self.assertEqual([qa.tool_question_kind(t) for t in ("quiz", "probe", "explain", "recall", "ask_user_question")],
                         ["quiz", "quiz", "explain", "explain", "ask"])

    def test_QA_R13_build_answer_details(self):
        qd = probe_qd(values=("a", "b", "c"), correct="b")
        ad = qa.build_answer(qd, {"values": ["c", "zzz", "a"], "other": "  ", "thinking": " t ", "readingThinking": "   "}, "probe")
        # unknown value ignored; sorted by display index
        self.assertEqual([a["value"] for a in ad["answers"]], sorted([ "a", "c"], key=lambda v: pos(qd, v)))
        self.assertNotIn("other", ad)
        self.assertEqual(ad["thinking"], "t")
        self.assertNotIn("readingThinking", ad)
        self.assertEqual(ad["explanation"], "because")
        self.assertEqual(ad["correctIndices"], [pos(qd, "b")])
        self.assertEqual(ad["options"], [{"index": i + 1, "label": o["label"]} for i, o in enumerate(qd["options"])])

    def test_QA_R15_R16_answer_request_fields(self):
        stops = qa.CONFIDENCE_STOPS
        self.assertEqual(stops, [0, 30, 50, 70, 90, 100])
        r = qa.build_answer_request("quiz", values=["a"], confidence_index=qa.DEFAULT_CONFIDENCE_INDEX)
        self.assertEqual(r["confidence"], 50)  # 50 is a real value
        self.assertNotIn("confidence", qa.build_answer_request("explain", text="x"))
        self.assertNotIn("confidence", qa.build_answer_request("ask", text="x"))
        # thinking only for choice modes
        self.assertEqual(qa.build_answer_request("quiz", values=["a"], thinking=" t ")["thinking"], "t")
        self.assertNotIn("thinking", qa.build_answer_request("explain", text="x", thinking="t", mode="text"))
        # dontKnow: request still carries the slider; build_answer drops it
        qd = probe_qd()
        ad = qa.build_answer(qd, qa.build_answer_request("quiz", dont_know=True, confidence_index=4), "probe")
        self.assertNotIn("confidence", ad)

    def test_QA_R19_interrupted_call_gets_synthetic_result_in_model_input_only(self):
        msgs = [assistant(("q1", "probe", {}), ("r1", "read", {})), tool_result("r1", "read"), user("hello", mid="u2")]
        original = json.dumps(msgs, sort_keys=True)
        out = cs.to_llm_messages(msgs)
        synth = [m for m in out if m.get("toolCallId") == "q1"]
        self.assertEqual(len(synth), 1)
        self.assertEqual(synth[0]["content"][0]["text"], cs.INTERRUPTED_TEXT)
        self.assertEqual(json.dumps(msgs, sort_keys=True), original)  # record unchanged
        self.assertNotIn("id", out[0])  # record id stripped

    def test_QA_R20_one_turn_per_chat(self):
        store = store_with(messages=[assistant(("k1", "probe", probe_args()))])
        turns = cs.TurnRegistry()
        self.assertTrue(turns.begin_turn("c1"))
        with self.assertRaises(cs.ChatInputError) as cm:
            cs.handle_chat_request(store, "c1", {"type": "answer", "toolCallId": "k1", "answer": {"kind": "quiz"}}, turns)
        self.assertEqual(cm.exception.status, 409)
        self.assertIn("A turn is already running for this session", str(cm.exception))
        turns.end_turn("c1")
        resp = cs.handle_chat_request(store, "c1", {"type": "answer", "toolCallId": "k1", "answer": {"kind": "quiz"}}, turns)
        self.assertTrue(resp.turn_started)

    def test_QA_R17_wake_blocked_after_dismissal(self):
        # last record message is a dismissal result -> pause until next user input
        msgs = [assistant(("k1", "probe", {})), cs.new_answer_result("k1", "probe", {"kind": "quiz", "dismissed": True})]
        self.assertTrue(cs.ends_in_dismissal(msgs))
        self.assertFalse(cs.ends_in_dismissal(msgs + [user("next")]))
        self.assertFalse(cs.ends_in_dismissal([]))

    def test_QA_R02_options_unwrap_then_heal_then_schema(self):
        # multiSelect given as JSON-string boolean heals; options JSON string unwraps
        args = probe_args(correct=["a", "b"])
        args["multiSelect"] = "true"
        args["options"] = json.dumps(args["options"])
        r = call_tool(probe_tool(), args)
        self.assertTrue(r["executed"])
        self.assertIs(r["result"]["terminate"], True)
        # well-formed args pass untouched (same object)
        good = probe_args()
        self.assertIs(qa.prepare_question_arguments(good), good)


if __name__ == "__main__":
    unittest.main()
