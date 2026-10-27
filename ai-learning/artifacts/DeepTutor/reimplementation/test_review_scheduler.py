import math
import os
import unittest

from reimpl_learning.engine import due_reviews
from reimpl_learning.models import (ErrorRecord, ErrorType, KnowledgeType as KT,
                                    LearningEvidence, LearningProgress, RepetitionState)
from reimpl_learning.scheduler import SpacedRepetitionScheduler, validate_desired_retention

t0 = 1_700_000_000.0
D = 86400.0
NL = -math.log(0.9)


def ev(q=None, result="correct", ts=0.0, **kw):
    return LearningEvidence(knowledge_point_id="a", timestamp=ts, quality=q, result=result, **kw)


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.s = SpacedRepetitionScheduler()

    def concept(self):
        return self.s.get_initial_state(KT.CONCEPT, now=t0)

    def test_T01_initial_concept(self):
        st = self.concept()
        self.assertAlmostEqual(st.stability, 28.475, delta=0.002)
        self.assertEqual(st.difficulty, 0.4)
        self.assertAlmostEqual(st.next_review_at, t0 + 3 * D, delta=1)
        self.assertEqual(st.last_scheduled_at, t0)
        self.assertIsNone(st.last_review_at)
        self.assertEqual((st.review_count, st.lapse_count, st.consecutive_correct,
                          st.consecutive_wrong), (0, 0, 0, 0))

    def test_T02_initial_concept_08(self):
        st = self.s.get_initial_state(KT.CONCEPT, now=t0, desired_retention=0.8)
        self.assertAlmostEqual(st.stability, 28.475, delta=0.002)
        self.assertAlmostEqual((st.next_review_at - t0) / D, 6.354, delta=0.001)
        self.assertEqual(st.desired_retention, 0.8)

    def test_T03_initial_memory(self):
        st = self.s.get_initial_state(KT.MEMORY, now=t0)
        self.assertEqual(st.stability, 0.5)
        self.assertEqual(st.difficulty, 0.3)
        self.assertEqual(st.next_review_at, t0)

    def test_T04_validate(self):
        for bad in (0.69, float("nan")):
            with self.assertRaises(ValueError):
                validate_desired_retention(bad)
        self.assertEqual(validate_desired_retention(0.7), 0.7)
        self.assertEqual(validate_desired_retention(0.99), 0.99)

    def test_T05_quality(self):
        from reimpl_learning.scheduler import _resolved_quality as rq
        self.assertAlmostEqual(rq(ev(None, "correct", hints_used=2, attempt_count=3)), 0.74)
        self.assertAlmostEqual(rq(ev(None, "partial")), 0.4)
        self.assertAlmostEqual(rq(ev(0.3, "partial", hints_used=5, attempt_count=9)), 0.3)

    def after_T06(self):
        st = self.concept()
        self.s.schedule_review(st, KT.CONCEPT, ev(1.0, ts=t0 + 3 * D))
        return st

    def test_T06_success(self):
        st = self.after_T06()
        self.assertAlmostEqual(st.difficulty, 0.352, delta=0.001)
        self.assertEqual((st.consecutive_correct, st.review_count), (1, 1))
        self.assertAlmostEqual(st.stability, 60.902, delta=0.01)
        self.assertAlmostEqual((st.next_review_at - st.last_review_at) / D, 6.416, delta=0.001)
        self.assertEqual(st.interval_index, 1)
        self.assertFalse(st.scheduled_after_failure)
        self.assertEqual(st.last_review_at, t0 + 3 * D)
        self.assertEqual(st.last_scheduled_at, t0 + 3 * D)

    def test_T07_failure(self):
        st = self.concept()
        self.s.schedule_review(st, KT.CONCEPT, ev(0.0, "incorrect", ts=t0 + 3 * D))
        self.assertAlmostEqual(st.difficulty, 0.552, delta=0.001)
        self.assertEqual((st.lapse_count, st.consecutive_wrong), (1, 1))
        self.assertAlmostEqual(st.stability, 7.364, delta=0.01)
        self.assertEqual(st.retrievability, 0.2)
        self.assertTrue(st.scheduled_after_failure)
        self.assertAlmostEqual((st.next_review_at - st.last_review_at) / D, 0.388, delta=0.001)
        self.assertEqual(st.interval_index, 0)

    def test_T08_partial_half(self):
        st = self.concept()
        self.s.schedule_review(st, KT.CONCEPT, ev(0.5, "partial", ts=t0 + 3 * D))
        self.assertAlmostEqual(st.difficulty, 0.452, delta=0.001)
        self.assertAlmostEqual(st.stability, 28.475, delta=0.002)
        self.assertAlmostEqual((st.next_review_at - st.last_review_at) / D, 3.0, delta=0.001)
        self.assertEqual(st.consecutive_correct, 1)

    def test_T09_same_session_success(self):
        st = self.after_T06()
        m1 = st.last_review_at
        before = (st.stability, st.next_review_at, st.last_scheduled_at, st.difficulty,
                  st.consecutive_correct)
        self.s.schedule_review(st, KT.CONCEPT, ev(1.0, ts=m1 + 0.1 * D))
        self.assertEqual(st.review_count, 2)
        self.assertEqual(st.last_review_at, m1 + 0.1 * D)
        self.assertEqual(st.retrievability, 1.0)
        self.assertEqual(before, (st.stability, st.next_review_at, st.last_scheduled_at,
                                  st.difficulty, st.consecutive_correct))

    def test_T10_same_session_failure(self):
        st = self.after_T06()
        m1 = st.last_review_at
        old_stab = st.stability
        self.s.schedule_review(st, KT.CONCEPT, ev(0.0, "incorrect", ts=m1 + 0.1 * D))
        self.assertEqual(st.lapse_count, 1)
        self.assertLess(st.stability, old_stab)
        self.assertTrue(st.scheduled_after_failure)
        # b: partial q=0.2 while already scheduled_after_failure
        snap = (st.stability, st.next_review_at, st.last_scheduled_at, st.lapse_count)
        rc = st.review_count
        self.s.schedule_review(st, KT.CONCEPT, ev(0.2, "partial", ts=st.last_review_at + 0.01 * D))
        self.assertEqual(st.review_count, rc + 1)
        self.assertEqual(snap, (st.stability, st.next_review_at, st.last_scheduled_at,
                                st.lapse_count))

    def test_T11_memory_success(self):
        st = self.s.get_initial_state(KT.MEMORY, now=t0)
        self.s.schedule_review(st, KT.MEMORY, ev(1.0, ts=t0))
        self.assertAlmostEqual(st.difficulty, 0.264, delta=0.001)
        self.assertAlmostEqual(st.stability, 1.096, delta=0.001)
        self.assertAlmostEqual((st.next_review_at - st.last_review_at) / D, 0.115, delta=0.001)
        self.assertEqual(st.interval_index, 0)

    def test_T12_retrievability(self):
        T = t0
        st = RepetitionState(next_review_at=T + 5 * D, stability=10, last_review_at=T)
        self.assertAlmostEqual(self.s.retrievability(st, now=T + 10 * D), math.exp(-1), delta=0.001)
        st2 = RepetitionState(next_review_at=T + 5 * D, stability=10)
        self.assertEqual(self.s.retrievability(st2, now=T), 1.0)

    def test_T13_forgetting_risk(self):
        T = t0
        st = RepetitionState(next_review_at=T + 5 * D, stability=10, last_review_at=T)
        p = LearningProgress(book_id="p")
        now = T + 10 * D
        self.assertAlmostEqual(self.s.forgetting_risk(st, p, "a", now=now), 0.882, delta=0.001)
        st.lapse_count = 1
        self.assertAlmostEqual(self.s.forgetting_risk(st, p, "a", now=now), 0.982, delta=0.001)
        p.error_records.append(ErrorRecord(id="e", question_id="q", knowledge_point_id="a",
                                           module_id="m", error_type=ErrorType.APPLICATION_ERROR))
        self.assertEqual(self.s.forgetting_risk(st, p, "a", now=now), 1.0)

    def test_T14_queue(self):
        now = t0
        p = LearningProgress(book_id="p", knowledge_types={"A": KT.CONCEPT, "B": KT.CONCEPT})
        a = self.s.get_initial_state(KT.CONCEPT, now=now)
        b = self.s.get_initial_state(KT.CONCEPT, now=now)
        a.next_review_at = now - D
        b.next_review_at = now + 5 * D
        p.repetition_states = {"A": a, "B": b}
        p.review_queue = self.s.build_review_queue(p, now=now)
        self.assertEqual([t.knowledge_point_id for t in p.review_queue], ["A", "B"])
        self.assertAlmostEqual(p.review_queue[0].forgetting_risk, 0.1774, delta=0.001)
        self.assertEqual(p.review_queue[1].forgetting_risk, 0)
        self.assertEqual([t.knowledge_point_id for t in due_reviews(p, now=now)], ["A"])

    def test_T15_replay(self):
        st = self.s.replay(KT.CONCEPT, [], now=t0)
        self.assertEqual(st.next_review_at, t0 + 3 * D)
        with self.assertRaises(ValueError):
            self.s.replay(KT.CONCEPT, [ev(1.0, ts=t0)], initial_state=st, desired_retention=0.8)

    def test_T16_set_desired_retention(self):
        p = LearningProgress(book_id="p", knowledge_types={"a": KT.CONCEPT})
        p.repetition_states["a"] = self.concept()
        self.s.set_desired_retention(p, 0.8, now=t0)
        st = p.repetition_states["a"]
        self.assertAlmostEqual(st.stability, 28.475, delta=0.002)
        self.assertAlmostEqual((st.next_review_at - t0) / D, 6.354, delta=0.001)
        self.assertEqual(st.interval_index, 1)
        self.assertEqual((st.desired_retention, p.desired_retention), (0.8, 0.8))
        self.assertEqual(p.learning_evidence, [])
        self.assertEqual(len(p.review_queue), 1)

    def test_T17_debug_units(self):
        os.environ["LEARNING_DEBUG"] = "1"
        try:
            s = SpacedRepetitionScheduler()
        finally:
            del os.environ["LEARNING_DEBUG"]
        st = s.get_initial_state(KT.CONCEPT, now=t0)
        self.assertAlmostEqual(st.next_review_at, t0 + 3.0, delta=1e-6)


if __name__ == "__main__":
    unittest.main()
