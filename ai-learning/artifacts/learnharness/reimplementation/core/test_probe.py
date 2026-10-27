"""probe-measurement.md 1.6 acceptance cases (T-01..T-11) + extra [강제] rules.
Names: test_PM_Txx_*; extras test_PM_Rxx_*."""
import logging
import unittest

import chat_server as cs
import probe
from fixtures import assistant, probe_args, store_with, tool_result, user
from tools import (call_tool, create_prober_tools, create_teacher_tools, probe_done_tool,
                   ProberContext)

ASSESSMENT = {"assessment": {"strands": [
    {"strand": "limits", "assessment": "floor: epsilon-delta; ceiling: uniform"},
    {"strand": "derivative", "assessment": "floor: slope"}], "summary": "wants calculus"}}


class Deliver:
    def __init__(self, exc=None):
        self.calls, self.exc = [], exc

    def __call__(self, steer):
        self.calls.append(steer)
        if self.exc:
            raise self.exc


def make(messages=None, deliver=None, chat_id="c1"):
    store = store_with(chat_id, messages=messages or [])
    d = deliver or Deliver()
    tool = probe_done_tool(ProberContext(chat_id=chat_id, chat_store=store, deliver=d))
    return store, d, tool


class T(unittest.TestCase):
    def test_PM_T01_open_question_refuses(self):
        store, d, tool = make([assistant(("q1", "probe", probe_args()))])
        r = call_tool(tool, ASSESSMENT)
        self.assertTrue(r["executed"])
        self.assertEqual(r["result"], {"ok": False, "error": (
            "A question is still open — resolve it (or let him answer) before concluding the probe. "
            "probe_done only fires with no question outstanding.")})
        self.assertEqual(d.calls, [])

    def test_PM_T02_already_concluded(self):
        store, d, tool = make([assistant(("p1", "probe_done", ASSESSMENT)), tool_result("p1", "probe_done")])
        r = call_tool(tool, ASSESSMENT)["result"]
        self.assertEqual(r, {"ok": False, "error": "The probe is already concluded — probe_done fires exactly once."})
        self.assertEqual(d.calls, [])

    def test_PM_R06_open_question_checked_before_already_concluded(self):
        store, d, tool = make([assistant(("p1", "probe_done", ASSESSMENT)), tool_result("p1", "probe_done"),
                               assistant(("q1", "probe", probe_args()))])
        r = call_tool(tool, ASSESSMENT)["result"]
        self.assertTrue(r["error"].startswith("A question is still open"))

    def test_PM_T03_success_delivers_one_steer(self):
        store, d, tool = make([user("teach me")])
        r = call_tool(tool, ASSESSMENT)["result"]
        self.assertEqual(r["text"], probe.PROBE_DONE_ACK_TEXT)
        self.assertEqual(r["details"], {"ok": True})
        self.assertEqual(len(d.calls), 1)
        s = d.calls[0]
        self.assertEqual(s["id"], "steer_probe_c1")
        self.assertEqual((s["role"], s["customType"], s["details"]), ("custom", "probe-handoff", {"chatId": "c1"}))
        self.assertEqual(s["content"], probe.HANDOFF_TEXT)
        self.assertNotIn("strand", str(r))  # no echo of the assessment

    def test_PM_T04_deliver_exception_is_logged_and_result_still_ok(self):
        store, d, tool = make(deliver=Deliver(exc=RuntimeError("queue down")))
        with self.assertLogs("probe", level=logging.ERROR) as lg:
            r = call_tool(tool, ASSESSMENT)["result"]
        self.assertEqual(r["details"], {"ok": True})
        self.assertEqual(r["text"], probe.PROBE_DONE_ACK_TEXT)
        self.assertIn("queue down", "\n".join(lg.output))

    def test_PM_R07_chat_not_found(self):
        store, d, tool = make()
        tool2 = probe_done_tool(ProberContext(chat_id="ghost", chat_store=store, deliver=d))
        self.assertEqual(call_tool(tool2, ASSESSMENT)["result"], {"ok": False, "error": "Chat not found: ghost"})

    def test_PM_T05_empty_strands_rejected_by_schema(self):
        store, d, tool = make()
        r = call_tool(tool, {"assessment": {"strands": []}})
        self.assertFalse(r["executed"])
        self.assertEqual(d.calls, [])

    def test_PM_T06_assessment_as_string_rejected(self):
        store, d, tool = make()
        r = call_tool(tool, {"assessment": "everything is fine"})
        self.assertFalse(r["executed"])
        # missing strand text / wrong types also rejected; summary optional
        self.assertFalse(call_tool(tool, {"assessment": {"strands": [{"strand": "x"}]}})["executed"])
        self.assertTrue(call_tool(tool, {"assessment": {"strands": [{"strand": "x", "assessment": "y"}]}})["executed"])

    def test_PM_T07_phase_seam_any_probe_done_call(self):
        self.assertTrue(cs.has_probe_done([assistant(("p", "probe_done", {}))]))  # no result at all
        self.assertTrue(cs.has_probe_done([assistant(("p", "probe_done", {})), tool_result("p", "probe_done", is_error=True)]))
        self.assertFalse(cs.has_probe_done([assistant(("q", "probe", {})), user("x")]))
        self.assertFalse(cs.has_probe_done([]))
        # only assistant messages count
        self.assertFalse(cs.has_probe_done([tool_result("p", "probe_done")]))
        self.assertEqual(cs.select_agent([assistant(("p", "probe_done", {}))]), "teacher")
        self.assertEqual(cs.select_agent([user("x")]), "prober")
        self.assertEqual(cs.select_agent([user("x")], kind="practice"), "practice")

    def test_PM_T08_probe_done_survives_toggle(self):
        ctx = ProberContext(chat_id="c1", chat_store=store_with(), deliver=Deliver())
        tools = create_prober_tools(ctx, enabled={"probe_done": False, "research": False})
        self.assertIn("probe_done", tools)
        self.assertNotIn("research", tools)  # other toggles still work

    def test_PM_T09_graph_tools_gate(self):
        ctx = ProberContext(chat_id="c1", chat_store=store_with(), deliver=Deliver())
        self.assertNotIn("list_sessions", create_prober_tools(ctx))
        ctx_g = ProberContext(chat_id="c1", chat_store=store_with(), deliver=Deliver(), graph_store=probe.GraphStore())
        t = create_prober_tools(ctx_g)
        self.assertIn("list_sessions", t)
        self.assertIn("list_propositions", t)
        # settings gate: graph.enabled and agent.graphTools.enabled (default on)
        self.assertTrue(probe.graph_tools_enabled({"graph": {"enabled": True}, "agent": {"graphTools": {}}}))
        self.assertFalse(probe.graph_tools_enabled({"graph": {"enabled": False}, "agent": {"graphTools": {}}}))
        self.assertFalse(probe.graph_tools_enabled({"graph": {"enabled": True}, "agent": {"graphTools": {"enabled": False}}}))
        self.assertTrue(probe.graph_tools_enabled({"graph": {"enabled": True}, "agent": {"graphTools": {"enabled": True}}}))

    def test_PM_T10_list_sessions_empty(self):
        self.assertEqual(probe.list_sessions([]),
                         "The knowledge graph is empty — no session has contributed propositions yet.")

    def test_PM_list_sessions_format_and_order(self):
        sessions = [
            {"id": "s1", "name": "Old chat", "kind": "chat", "createdAt": "2026-01-01", "updatedAt": "2026-01-02", "propositions": 1},
            {"id": "f1", "name": "notes.md", "kind": "file", "createdAt": None, "updatedAt": None, "propositions": 3},
            {"id": "s2", "name": "New chat", "kind": "chat", "createdAt": "2026-02-01", "updatedAt": "2026-03-01", "propositions": 2},
        ]
        out = probe.list_sessions(sessions).split("\n")
        self.assertEqual(out[0], "3 session(s) in the knowledge graph, most recent first:")
        self.assertEqual(out[1], "1. New chat (chat, 2 propositions, born 2026-02-01, last active 2026-03-01) — id: s2")
        self.assertEqual(out[2], "2. Old chat (chat, 1 proposition, born 2026-01-01, last active 2026-01-02) — id: s1")
        self.assertEqual(out[3], "3. notes.md (file, 3 propositions, born unknown date) — id: f1")

    def test_PM_list_propositions(self):
        props = {"s1": [{"nodeId": "n2", "name": "B"}, {"nodeId": "n1", "name": "A"}]}
        self.assertEqual(probe.list_propositions(props, "s1"), "2 proposition(s) covered in this session:\n- A\n- B")
        self.assertEqual(probe.list_propositions(props, "zz"),
                         'No propositions born in session "zz". Call list_sessions for the current ids.')

    def test_PM_T11_steer_idempotent(self):
        store, d, tool = make([user("hi")])
        deliver = cs.make_wake_deliver(store, "c1")
        steer = probe.build_probe_handoff_steer("c1")
        deliver(steer)
        deliver(probe.build_probe_handoff_steer("c1"))
        ids = [m.get("id") for m in store.get_chat("c1")["messages"]]
        self.assertEqual(ids.count("steer_probe_c1"), 1)
        self.assertTrue(probe.steer_delivered(store.get_chat("c1")["messages"], "steer_probe_c1"))
        self.assertFalse(probe.steer_delivered([], "steer_probe_c1"))

    def test_PM_R02_prompt_assembly_order(self):
        files = {"prober": ["20-b.md", "10-a.md", "README.md", "x-1.md", "5.md"],
                 "shared": ["25-conf.md", "10-voice.md", "notes.txt", "a10-x.md"]}
        segs = probe.list_source_segments("prober", files)
        self.assertEqual([s["path"] for s in segs],
                         ["system-prompt.md", "prober/10-a.md", "prober/20-b.md", "shared/10-voice.md", "shared/25-conf.md"])
        # (note: "5.md" has no "-name" part so it is not a fragment)
        texts = {"system-prompt.md": " base \n", "prober/10-a.md": "A", "prober/20-b.md": "",
                 "shared/10-voice.md": "V", "shared/25-conf.md": "C"}
        self.assertEqual(probe.compose_instructions(segs, texts), "base\n\n---\n\nA\n\n---\n\nV\n\n---\n\nC")
        # override replaces the segment text
        self.assertIn("OVR", probe.compose_instructions(segs, texts, overrides={"prober/10-a.md": "OVR"}))

    def test_PM_R03_prober_tool_set(self):
        ctx = ProberContext(chat_id="c1", chat_store=store_with(), deliver=Deliver())
        names = set(create_prober_tools(ctx))
        self.assertEqual(names, {"probe", "ask_user_question", "read", "ls", "find", "grep", "research", "pdf", "probe_done"})
        self.assertEqual(set(create_prober_tools(ctx, enabled={"explain": True})) - names, {"recall"})
        self.assertNotIn("probe", create_prober_tools(ctx, enabled={"explain": True}))
        self.assertNotIn("plan_init", names)
        self.assertTrue({"demo", "visual"}.isdisjoint(names))
        # research stays registered with no search provider (R-12: spec's reading)
        ctx2 = ProberContext(chat_id="c1", chat_store=store_with(), deliver=Deliver(), search_available=False)
        self.assertIn("research", create_prober_tools(ctx2))

    def test_PM_R13_extraction_never_sees_assessment(self):
        msgs = [assistant(("p", "probe_done", ASSESSMENT), text="closing", mid="a9"), user("secret thoughts")]
        view = cs.prose_view(msgs)
        self.assertNotIn("limits", view)
        self.assertNotIn("secret", view)


if __name__ == "__main__":
    unittest.main()
