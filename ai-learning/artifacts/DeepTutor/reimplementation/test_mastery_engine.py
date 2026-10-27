import unittest

from reimpl_learning.engine import (
    MemoryStore, Tx, apply_grade, compute_mastery, calculate_mastery, defer_objective,
    find_knowledge_point, grade_answer, is_mastered, mastery_source, next_objective,
    objective_status, display_mastery, record_qualitative, record_quiz_attempt,
    replace_modules, set_learner_mastery_override, validate_objective_relations,
    record_qualitative_for_path, classify_error)
from reimpl_learning.models import (
    ErrorType, InteractionStatus, KnowledgePoint, KnowledgeType as KT, LearnerProfile,
    LearningModule, LearningProgress, MasteryInteractionError, ObjectiveRelationError,
    PendingQuestion, QuizAttempt, StaleInteractionError, DeferredObjective)
from reimpl_learning.scheduler import SpacedRepetitionScheduler

NOW = 1_700_000_000.0
D = 86400.0


def kp(i, t=KT.MEMORY, mod="m1", **kw):
    return KnowledgePoint(id=i, name=i.upper(), type=t, module_id=mod, **kw)


def prog(*mods, **kw):
    """mods: lists of KnowledgePoint -> modules m1, m2, ... with order 1.."""
    p = LearningProgress(book_id="p", **kw)
    replace_modules(p, [LearningModule(id=f"m{n}", name=f"M{n}", order=n, knowledge_points=list(k))
                        for n, k in enumerate(mods, 1)])
    return p


def attempt(correct=True, kpid="a", q="q", **kw):
    return QuizAttempt(question_id=q, knowledge_point_id=kpid, is_correct=correct, **kw)


class T(unittest.TestCase):
    def test_T01_empty(self):
        self.assertEqual(compute_mastery([]), 0.0)

    def test_T02_caps(self):
        self.assertAlmostEqual(compute_mastery([True]), 0.5)
        self.assertAlmostEqual(compute_mastery([True, True]), 0.8)
        self.assertAlmostEqual(compute_mastery([True, True, True]), 1.0)

    def test_T03_recency(self):
        m = compute_mastery([False, True, True, True, True])
        self.assertAlmostEqual(m, 0.875)
        self.assertLess(m, 0.9)

    def test_T04_partial_list(self):
        p = prog([kp("a")])
        for _ in range(4):
            p.quiz_attempts.append(attempt(True))
        p.quiz_attempts.append(attempt(False, result="partial"))
        self.assertAlmostEqual(calculate_mastery(p, "a"), 0.875)

    def test_T05_filters(self):
        p = prog([kp("a")])
        p.quiz_attempts += [attempt(True), attempt(True), attempt(True),
                            attempt(False, independent=False), attempt(False, voided=True)]
        self.assertAlmostEqual(calculate_mastery(p, "a"), 1.0)

    def test_T06_concept_qualitative_gate(self):
        p = prog([kp("a", KT.CONCEPT)], mastery_levels={"a": 1.0})
        k = p.modules[0].knowledge_points[0]
        self.assertFalse(is_mastered(p, k))
        record_qualitative(p, "a", passed=True, evidence="expl", now=NOW)
        self.assertTrue(is_mastered(p, k))
        self.assertEqual(mastery_source(p, k), "system")

    def test_T07_override(self):
        p = prog([kp("a", KT.CONCEPT)])
        k = p.modules[0].knowledge_points[0]
        p.mastery_levels["a"] = 0.3
        set_learner_mastery_override(p, "a", mastered=True, note="x" * 600)
        self.assertEqual(len(p.learner_mastery_overrides["a"].note), 500)
        self.assertTrue(is_mastered(p, k))
        self.assertEqual(mastery_source(p, k), "learner")
        self.assertEqual(objective_status(p, k), "mastered")
        self.assertEqual(display_mastery(p, k), 0.3)

    def pending(self, qid="q1", kpid="a", **kw):
        return PendingQuestion(question_id=qid, knowledge_point_id=kpid, prompt="?",
                               question_type="choice", expected_answer="b", **kw)

    def test_T08_pending_first(self):
        p = prog([kp("a"), kp("b")])
        s = SpacedRepetitionScheduler()
        p.knowledge_types["a"] = KT.MEMORY
        p.repetition_states["a"] = s.get_initial_state(KT.MEMORY, now=NOW - D)
        p.review_queue = s.build_review_queue(p, now=NOW)
        p.pending_question = self.pending(kpid="b")
        step = next_objective(p, now=NOW)
        self.assertEqual((step.action, step.knowledge_point_id), ("answer_pending", "b"))

    def test_T09_review(self):
        p = prog([kp("a"), kp("b")])
        s = SpacedRepetitionScheduler()
        p.repetition_states["b"] = s.get_initial_state(KT.MEMORY, now=NOW - D)
        p.review_queue = s.build_review_queue(p, now=NOW)
        step = next_objective(p, now=NOW)
        self.assertEqual((step.action, step.knowledge_point_id), ("review", "b"))

    def test_T10_probe_teach(self):
        p = prog([kp("a"), kp("b")], [kp("c", mod="m2")])
        p.mastery_levels["a"] = 1.0
        s = next_objective(p, now=NOW)
        self.assertEqual((s.knowledge_point_id, s.action), ("b", "probe"))
        p.learner_profile = LearnerProfile(teaching_strategy="teach_first")
        self.assertEqual(next_objective(p, now=NOW).action, "teach")

    def test_T11_all_deferred(self):
        p = prog([kp("a"), kp("b")], [kp("c", mod="m2")])
        for i in "abc":
            p.deferred_objectives[i] = DeferredObjective(knowledge_point_id=i)
        self.assertEqual(next_objective(p, now=NOW).knowledge_point_id, "a")

    def test_T12_complete(self):
        p = prog([kp("a"), kp("b", KT.CONCEPT)])
        p.mastery_levels["a"] = 0.95
        p.qualitative_mastery["b"] = True
        self.assertEqual(next_objective(p, now=NOW).action, "complete")

    def test_T13_grade_choice_short(self):
        self.assertTrue(grade_answer(" b ", "B", "choice"))
        self.assertTrue(grade_answer("photosyntesis", "photosynthesis", "short"))
        self.assertFalse(grade_answer("x", "", "short"))

    def test_T14_open(self):
        self.assertTrue(grade_answer("I used a and b", "a, b, c", "open"))
        self.assertFalse(grade_answer("only a", "a, b, c", "open"))

    def grade(self, p, ans, qid="q1", kpid="a", sched=None, **kw):
        return apply_grade(p, question_id=qid, knowledge_point_id=kpid, module_id="m1",
                           user_answer=ans, expected_answer="b", question_type="choice",
                           scheduler=sched, now=NOW, **kw)

    def test_T15_error_record_lifecycle(self):
        p = prog([kp("a")])
        self.grade(p, "x")
        self.assertEqual(len(p.error_records), 1)
        self.assertEqual(p.error_records[0].status, "active")
        self.grade(p, "x")
        self.assertEqual(p.error_records[0].status, "retrying")
        self.assertEqual(len(p.error_records[0].retry_history), 1)
        self.grade(p, "b")
        r = p.error_records[0]
        self.assertEqual((len(p.error_records), r.status, len(r.retry_history)), (1, "graduated", 2))
        p2 = prog([kp("a")])
        record_quiz_attempt(p2, attempt(False, result="partial", error_type=None))
        self.assertEqual(p2.error_records, [])

    def test_T16_evidence_and_queue(self):
        p = prog([kp("a")])
        s = SpacedRepetitionScheduler()
        self.grade(p, "b", sched=s)
        e = p.learning_evidence[0]
        self.assertEqual((e.assessment_type, e.quality, e.attempt_count), ("quiz", 1.0, 1))
        self.assertIn("a", p.repetition_states)
        self.assertIn("a", [t.knowledge_point_id for t in p.review_queue])
        self.grade(p, "b", qid="q2", sched=s)
        self.assertEqual(p.learning_evidence[1].assessment_type, "review")

    def test_T17_retry_and_hint_quality(self):
        p = prog([kp("a")])
        s = SpacedRepetitionScheduler()
        self.grade(p, "x", sched=s)
        self.grade(p, "b", sched=s)  # active error record exists for q1
        self.assertEqual(p.learning_evidence[1].quality, 0.6)
        p2 = prog([kp("a")])
        self.grade(p2, "b", assistance_used=True)
        e = p2.learning_evidence[0]
        self.assertLessEqual(e.quality, 0.6)
        self.assertGreaterEqual(e.hints_used, 1)
        self.assertFalse(p2.quiz_attempts[0].independent)

    def store_with_q(self, kpid="a", sched=None):
        st = MemoryStore()
        p = prog([kp("a"), kp("b", KT.CONCEPT)])
        st.create(p)
        st.register_question("p", self.pending(kpid=kpid), now=NOW)
        return st

    def test_T18_verdict_final(self):
        st = self.store_with_q()
        r = st.grade_interaction("p", "q1", "ans", verdict={"result": "correct", "confidence": 0.79,
                                                          "feedback": "f"}, now=NOW)
        self.assertEqual((r["final"], r["result"]), (False, "ungraded"))
        p = st.get("p")
        self.assertEqual((p.quiz_attempts, p.learning_evidence), ([], []))
        self.assertIsNotNone(p.pending_question)
        status = st.mutate("p", lambda tx: tx.active_interaction().status)[1]
        self.assertEqual(status, InteractionStatus.ANSWERED)
        r = st.grade_interaction("p", "q1", "ans", verdict={"result": "correct", "confidence": 0.8,
                                                          "feedback": "f"}, now=NOW)
        self.assertTrue(r["final"])
        p = st.get("p")
        self.assertEqual(len(p.quiz_attempts), 1)
        self.assertIsNone(p.pending_question)
        # R-17 idempotence
        r2 = st.grade_interaction("p", "q1", "ans", now=NOW)
        self.assertTrue(r2["replayed"])
        self.assertEqual(len(st.get("p").quiz_attempts), 1)

    def test_T19_qualitative_fail(self):
        p = prog([kp("a", KT.CONCEPT)], qualitative_mastery={"a": True}, mastery_levels={"a": 1.0})
        record_qualitative(p, "a", passed=False, now=NOW)
        self.assertEqual(p.qualitative_mastery["a"], False)
        self.assertAlmostEqual(p.mastery_levels["a"], 0.4)
        e = p.learning_evidence[0]
        self.assertEqual((e.result, e.quality), ("partial", 0.2))

    def test_T20_qualitative_idempotent(self):
        p = prog([kp("a", KT.CONCEPT)])
        self.assertTrue(record_qualitative(p, "a", passed=True, session_id="s", turn_id="t", now=NOW))
        lvl = dict(p.mastery_levels)
        self.assertFalse(record_qualitative(p, "a", passed=False, session_id="s", turn_id="t", now=NOW))
        self.assertEqual(len(p.learning_evidence), 1)
        self.assertEqual(p.mastery_levels, lvl)
        self.assertTrue(p.qualitative_mastery["a"])

    def test_T21_replace_modules(self):
        p = prog([kp("a"), kp("b")])
        s = SpacedRepetitionScheduler()
        self.grade(p, "b", kpid="a", sched=s)
        self.grade(p, "b", kpid="b", qid="q2", sched=s)
        replace_modules(p, [LearningModule(id="m1", name="M", order=1,
                                           knowledge_points=[kp("b"), kp("c", KT.CONCEPT)])])
        self.assertNotIn("a", p.mastery_levels)
        self.assertNotIn("a", p.repetition_states)
        self.assertEqual([x.knowledge_point_id for x in p.quiz_attempts], ["b"])
        self.assertEqual([x.knowledge_point_id for x in p.learning_evidence], ["b"])
        self.assertEqual([t.knowledge_point_id for t in p.review_queue], ["b"])
        self.assertIn("b", p.repetition_states)
        self.assertEqual(p.knowledge_types["c"], KT.CONCEPT)

    def test_T22_self_prereq(self):
        m = LearningModule(id="m", name="m", order=1, knowledge_points=[kp("a", prerequisite_ids=["a"])])
        with self.assertRaisesRegex(ObjectiveRelationError, "cannot be its own prerequisite"):
            validate_objective_relations([m], [])

    def test_T23_cycle(self):
        m = LearningModule(id="m", name="m", order=1, knowledge_points=[
            kp("a", prerequisite_ids=["b"]), kp("b", prerequisite_ids=["a"])])
        with self.assertRaisesRegex(ObjectiveRelationError, "Prerequisite cycle: "):
            validate_objective_relations([m], [])

    def test_T24_prereq_not_blocking(self):
        p = prog([kp("a", prerequisite_ids=["b"]), kp("b")])
        self.assertEqual(next_objective(p, now=NOW).knowledge_point_id, "a")

    def test_T25_register(self):
        st = MemoryStore()
        p = prog([kp("a")])
        p.deferred_objectives["a"] = DeferredObjective(knowledge_point_id="a")
        st.create(p)
        q = self.pending()
        pr, inter, created = st.register_question("p", q, now=NOW)
        self.assertTrue(created)
        self.assertEqual(pr.pending_question.question_id, "q1")
        self.assertEqual(inter.status, InteractionStatus.REGISTERED)
        self.assertNotIn("a", pr.deferred_objectives)
        self.assertEqual(pr.pending_question.created_at, NOW)

    def test_T26_retain(self):
        st = self.store_with_q()
        pr, inter, created = st.register_question("p", self.pending("q2"), now=NOW)
        self.assertFalse(created)
        self.assertEqual(inter.interaction_id, "q1")
        self.assertEqual(pr.pending_question.question_id, "q1")

    def test_T27_replace(self):
        st = self.store_with_q()
        before = st.get("p")
        with self.assertRaises(StaleInteractionError):
            st.register_question("p", self.pending("q2"), pending_action="replace",
                                 replace_question_id="nope", now=NOW)
        self.assertEqual(st.get("p").pending_question.question_id, before.pending_question.question_id)
        pr, inter, created = st.register_question("p", self.pending("q2"), pending_action="replace",
                                                  replace_question_id="q1", now=NOW)
        self.assertTrue(created)
        self.assertEqual(pr.pending_question.question_id, "q2")
        old = st.mutate("p", lambda tx: tx.get_interaction("q1").status)[1]
        self.assertEqual(old, InteractionStatus.ABANDONED)

    def test_T28_unknown_kp(self):
        st = self.store_with_q()
        st2 = MemoryStore()
        st2.create(prog([kp("a")]))
        before = st2.get("p")
        with self.assertRaisesRegex(MasteryInteractionError, "Unknown objective"):
            st2.register_question("p", self.pending(kpid="zzz"), now=NOW)
        self.assertIsNone(st2.get("p").pending_question)


if __name__ == "__main__":
    unittest.main()
