"""Extra R-ID checks written by the re-implementer (not spec T-IDs); expectations derived from rule text."""
import unittest

from reimpl_learning.engine import (
    MemoryStore, Tx, apply_grade, classify_error, defer_objective, learning_stage,
    next_objective, record_qualitative_for_path, recompute_objective_state, is_mastered)
from reimpl_learning.models import (
    ErrorType, KnowledgeType as KT, MasteryInteractionError, PendingQuestion)
from reimpl_learning.scheduler import SpacedRepetitionScheduler
from test_mastery_engine import prog, kp, NOW, D


class Extras(unittest.TestCase):
    def test_R01_legacy_enum(self):
        self.assertIs(KT("概念型"), KT.CONCEPT)
        self.assertIs(ErrorType("应用错误"), ErrorType.APPLICATION_ERROR)

    def test_R11_classify(self):
        self.assertIs(classify_error("  "), ErrorType.METACOGNITIVE)
        self.assertIs(classify_error("x"), ErrorType.APPLICATION_ERROR)

    def test_R14_wrapper_rejects_memory(self):
        p = prog([kp("a")])
        with self.assertRaises(MasteryInteractionError):
            record_qualitative_for_path(p, "a", passed=True)
        with self.assertRaises(MasteryInteractionError):
            record_qualitative_for_path(p, "zz", passed=True)

    def test_R15_defer(self):
        st = MemoryStore()
        st.create(prog([kp("a"), kp("b")]))
        st.register_question("p", PendingQuestion(question_id="q", knowledge_point_id="a",
                                                  expected_answer="x"), now=NOW)
        _, r = st.mutate("p", lambda tx: defer_objective(tx, ""))
        self.assertEqual(r, {"knowledge_point_id": "a", "abandoned_question": True})
        p = st.get("p")
        self.assertIsNone(p.pending_question)
        self.assertIn("a", p.deferred_objectives)
        self.assertEqual(next_objective(p, now=NOW).knowledge_point_id, "b")
        # answering clears the defer record
        apply_grade(p, question_id="q9", knowledge_point_id="a", user_answer="x",
                    expected_answer="y", question_type="short", now=NOW)
        self.assertNotIn("a", p.deferred_objectives)

    def test_R18_recompute_matches_live(self):
        s = SpacedRepetitionScheduler()
        p = prog([kp("a", KT.CONCEPT)])
        for i, (ans, dt) in enumerate([("b", 0), ("x", 3 * D), ("b", 5 * D)]):
            apply_grade(p, question_id=f"q{i}", knowledge_point_id="a", user_answer=ans,
                        expected_answer="b", question_type="choice", scheduler=s, now=NOW + dt)
        live = p.repetition_states["a"]
        recompute_objective_state(p, "a", s, now=NOW + 5 * D)
        self.assertEqual(live, p.repetition_states["a"])

    def test_R20_stage(self):
        p = prog([kp("a")])
        self.assertEqual(learning_stage(p, "a"), "not_yet_covered")
        apply_grade(p, question_id="q", knowledge_point_id="a", user_answer="x",
                    expected_answer="b", question_type="choice", now=NOW)
        self.assertEqual(learning_stage(p, "a"), "practiced_not_demonstrated")
        apply_grade(p, question_id="q2", knowledge_point_id="a", user_answer="b",
                    expected_answer="b", question_type="choice", now=NOW, assistance_used=True)
        self.assertEqual(learning_stage(p, "a"), "practiced_with_help")
        apply_grade(p, question_id="q3", knowledge_point_id="a", user_answer="b",
                    expected_answer="b", question_type="choice", now=NOW)
        self.assertEqual(learning_stage(p, "a"), "independently_demonstrated")


if __name__ == "__main__":
    unittest.main()
