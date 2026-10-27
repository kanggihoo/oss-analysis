"""review-scheduler 스펙의 T-18~T-26(작업자가 코드에서 손 계산한 사례)을 원본에서 실행해 관측값을 출력한다.
사용: python3 -I run_pure2.py <run_pure.py가 만든 샌드박스> . 기대값은 스펙 표와 사람이 대조한다(관측값만 출력, 판정은 아래 EXPECT 비교로 표시).
"""
import os, sys, time, math
sys.path.insert(0, sys.argv[1]); os.environ.pop("LEARNING_DEBUG", None)
import deeptutor.learning.models as M, deeptutor.learning.scheduler as S
D = 86400.0; t0 = 2_000_000.0
s = S.SpacedRepetitionScheduler(); KT = M.KnowledgeType
out = []
def rec(tid, ok, obs): out.append((tid, ok, obs))
def conc(): return s.get_initial_state(KT.CONCEPT, now=t0)
def prog(kts): 
    p = M.LearningProgress(book_id="p"); p.knowledge_types = dict(kts); return p
cp = prog({"a": KT.CONCEPT})
# T-18
st = conc(); exp18 = {3.01: "due now; retrievability 100%.", 4: "due 1 day ago; retrievability 97%.", 5.5: "due 2 days ago; retrievability 92%.",
     13: "due 10 days ago; retrievability 70% below 90% target.", 2.5: "due in 12 hours; retrievability 100%.",
     1.8: "due in 1 day; retrievability 100%.", 2.98: "due in moments; retrievability 100%."}
for d, e in exp18.items():
    g = s.review_reason(st, cp, "a", now=t0 + d * D); rec(f"T-18 t0+{d}D", g == e, g)
g = s.review_reason(st, cp, "a", now=t0); rec("T-18 t0", g.startswith("due in 3 days; retrieva"), g)
# T-19
base = "due 10 days ago; retrievability 70% below 90% target"
def r19(mod=None, err=False, ev=None):
    stx = conc()
    if mod: mod(stx)
    p = prog({"a": KT.CONCEPT})
    if err: p.error_records = [M.ErrorRecord(id="e", question_id="q", knowledge_point_id="a", module_id="m", error_type=M.ErrorType("application"), status="active")]
    return s.review_reason(stx, p, "a", now=t0 + 13 * D, latest_evidence=ev)
rec("T-19a", r19(lambda x: setattr(x, "lapse_count", 1)) == base + "; 1 lapse.", r19(lambda x: setattr(x, "lapse_count", 1)))
rec("T-19b", r19(lambda x: setattr(x, "lapse_count", 2)) == base + "; 2 lapses.", r19(lambda x: setattr(x, "lapse_count", 2)))
rec("T-19c", r19(lambda x: setattr(x, "consecutive_wrong", 1)) == base + "; recent failure.", r19(lambda x: setattr(x, "consecutive_wrong", 1)))
rec("T-19d", r19(err=True) == base + "; recent failure.", r19(err=True))
e_dq = M.LearningEvidence(knowledge_point_id="a", timestamp=1.0, source="deep_question", result="incorrect", evidence_id="x")
ge = r19(lambda x: setattr(x, "lapse_count", 1), ev=e_dq); rec("T-19e", ge == base + "; 1 lapse; latest Question Bank assessment: incorrect.", ge)
e_mp = M.LearningEvidence(knowledge_point_id="a", timestamp=1.0, source="mastery_path", result="incorrect", evidence_id="x")
gf = r19(ev=e_mp); rec("T-19f", gf == base + ".", gf)
def g_(v):
    def m(x): x.desired_retention = v
    return r19(m)
rec("T-19g", g_(0.8).startswith("due 10 days ago; retrievability 70% below 80% target") , g_(0.8)); rec("T-19g2", True, g_(0.7))
# T-20 hydrate
def hy(kt, **kw):
    x = M.RepetitionState(next_review_at=t0, **kw); return s.hydrate(x, kt)
a = hy(KT.CONCEPT, stability=0, interval_index=2, desired_retention=0.8, retrievability=0)
rec("T-20a", abs(a.stability - 62.7399) < 1e-3 and a.difficulty == 0.4 and a.retrievability == 1.0 and a.interval_index == 2 and a.desired_retention == 0.8 and a.next_review_at == t0, (a.stability, a.difficulty, a.retrievability, a.interval_index))
b = hy(KT.CONCEPT, stability=0, interval_index=9, desired_retention=0)
rec("T-20b", abs(b.stability - 284.7366) < 1e-3 and b.difficulty == 0.4 and b.desired_retention == 0.9 and b.interval_index == 3, (b.stability, b.difficulty, b.desired_retention, b.interval_index))
c = hy(KT.MEMORY, stability=0, interval_index=0); rec("T-20c", c.stability == 0.5 and c.difficulty == 0.3, (c.stability, c.difficulty))
d = hy(KT.PROCEDURE, stability=5, difficulty=0); rec("T-20d", d.stability == 5 and d.difficulty == 0.5, (d.stability, d.difficulty))
# T-21
p = prog({"a": KT.MEMORY}); p.repetition_states["a"] = s.get_initial_state(KT.MEMORY, now=t0)
s.set_desired_retention(p, 0.8, now=t0 + D); x = p.repetition_states["a"]
rec("T-21a", x.next_review_at == t0 and x.interval_index == 0 and x.desired_retention == 0.8, ((x.next_review_at - t0) / D, x.interval_index, x.desired_retention))
p = prog({"a": KT.MEMORY}); st1 = s.get_initial_state(KT.MEMORY, now=t0)
st1 = s.schedule_review(st1, KT.MEMORY, M.LearningEvidence(knowledge_point_id="a", timestamp=t0, result="correct", quality=1.0), now=t0); p.repetition_states["a"] = st1
s.set_desired_retention(p, 0.8, now=t0 + D); x = p.repetition_states["a"]
rec("T-21b", abs((x.next_review_at - t0) / D - 0.2445) < 1e-3 and x.interval_index == 0, ((x.next_review_at - t0) / D, x.interval_index))
# T-22
ratio = (-math.log(0.8)) / (-math.log(0.9))
L = t0 + 50 * D; now22 = t0 + 100 * D
def mk(**kw):
    x = conc(); x.stability = kw.pop("stab", 20.0)
    for k, v in kw.items(): setattr(x, k, v)
    return x
p = prog({"a": KT.CONCEPT}); x = mk(last_scheduled_at=None, last_review_at=L, next_review_at=L + 10 * D); ii = x.interval_index; p.repetition_states["a"] = x
s.set_desired_retention(p, 0.8, now=now22)
rec("T-22a", abs((x.next_review_at - L) / D - 21.1790) < 1e-3 and x.interval_index == ii and x.desired_retention == 0.8 and p.desired_retention == 0.8, ((x.next_review_at - L) / D, x.interval_index, ii))
p = prog({"a": KT.CONCEPT}); x = mk(last_scheduled_at=None, last_review_at=None, next_review_at=now22 + 4 * D); ii = x.interval_index; p.repetition_states["a"] = x
s.set_desired_retention(p, 0.8, now=now22)
rec("T-22b", abs((x.next_review_at - now22) / D - 8.4716) < 1e-3 and x.interval_index == ii, ((x.next_review_at - now22) / D, x.interval_index, ii))
p = prog({"a": KT.CONCEPT}); x = mk(last_scheduled_at=None, last_review_at=None, next_review_at=now22 - 4 * D); p.repetition_states["a"] = x
s.set_desired_retention(p, 0.8, now=now22); rec("T-22c", x.next_review_at == now22 - 4 * D and x.desired_retention == 0.8, (x.next_review_at - now22) / D)
p = prog({"a": KT.CONCEPT, "b": KT.CONCEPT}); p.repetition_states["b"] = mk(last_scheduled_at=t0); bad = mk(last_scheduled_at=t0); bad.desired_retention = 0.5
p.repetition_states["z"] = bad; p.knowledge_types["z"] = KT.CONCEPT
try:
    s.set_desired_retention(p, 0.8, now=now22); rec("T-22d", False, "예외 없음")
except ValueError as e:
    rec("T-22d", p.repetition_states["b"].desired_retention == 0.8, f"ValueError({e}); b.desired_retention={p.repetition_states['b'].desired_retention}")
# T-23, T-24
def p6():
    x = conc(); n = t0 + 3 * D
    return s.schedule_review(x, KT.CONCEPT, M.LearningEvidence(knowledge_point_id="a", timestamp=n, result="correct", quality=1.0), now=n), n
st6, n6 = p6(); snap = st6.model_copy(deep=True)
ev1 = lambda t: M.LearningEvidence(knowledge_point_id="a", timestamp=t, result="correct", quality=1.0)
r = s.schedule_review(st6.model_copy(deep=True), KT.CONCEPT, ev1(n6 + 21599), now=n6 + 21599)
rec("T-23a", r.review_count == 2 and r.last_review_at == n6 + 21599 and r.retrievability == 1.0 and r.stability == snap.stability and r.next_review_at == snap.next_review_at and r.consecutive_correct == 1, (r.review_count, r.stability, r.consecutive_correct))
r = s.schedule_review(st6.model_copy(deep=True), KT.CONCEPT, ev1(n6 + 21600), now=n6 + 21600)
rec("T-23b", abs(r.difficulty - 0.3094) < 1e-3 and r.consecutive_correct == 0 and abs(r.stability - 152.1299) < 1e-3 and r.review_count == 2 and abs((r.next_review_at - (n6 + 21600)) / D - 16.0285) < 1e-3 and r.interval_index == 2,
    (r.difficulty, r.consecutive_correct, r.stability, (r.next_review_at - (n6 + 21600)) / D, r.interval_index))
x = conc(); n = t0 + 3 * D
x = s.schedule_review(x, KT.CONCEPT, M.LearningEvidence(knowledge_point_id="a", timestamp=n, result="incorrect", quality=0.0), now=n)
n2 = t0 + 13 * D
r = s.schedule_review(x, KT.CONCEPT, M.LearningEvidence(knowledge_point_id="a", timestamp=n2, result="incorrect", quality=0.0), now=n2)
rec("T-24", r.lapse_count == 2 and r.consecutive_wrong == 0 and abs(r.difficulty - 0.6263) < 1e-3 and abs(r.stability - 3.0164) < 1e-3 and r.retrievability == 0.2 and r.review_count == 2 and r.scheduled_after_failure and abs((r.next_review_at - n2) / D - 0.1589) < 1e-3 and r.interval_index == 0,
    (r.lapse_count, r.consecutive_wrong, r.difficulty, r.stability, r.retrievability, (r.next_review_at - n2) / D, r.interval_index))
# T-25 (get_due_tasks는 time.time()을 쓰므로 실제 지금 기준)
now = time.time(); p = prog({})
st_ = conc()
def task(i, due, risk): return M.ReviewTask(id=f"T{i}", knowledge_point_id=f"k{i}", knowledge_type=KT.CONCEPT, due_at=due, priority=3, state=st_, forgetting_risk=risk)
risks = [0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
p.review_queue = [task(i + 1, 0, r_) for i, r_ in enumerate(risks)] + [task(8, now + 10 * D, 0.99)]
before = [t.id for t in p.review_queue]
a5 = [t.id for t in s.get_due_tasks(p)]; a2 = [t.id for t in s.get_due_tasks(p, max_tasks=2)]
rec("T-25", a5 == ["T1", "T2", "T3", "T4", "T5"] and a2 == ["T1", "T2"] and [t.id for t in p.review_queue] == before, (a5, a2))
# T-26
p = prog({"A": KT.CONCEPT, "B": KT.CONCEPT}); p.repetition_states = {"A": conc(), "B": conc(), "C": s.get_initial_state(KT.MEMORY, now=t0)}
p.error_records = [M.ErrorRecord(id="e", question_id="q", knowledge_point_id="A", module_id="m", error_type=M.ErrorType("application"), status="active")]
p.learning_evidence = [M.LearningEvidence(knowledge_point_id="A", timestamp=t0 + 9 * D, source="deep_question", evidence_id="ev1", result="correct"),
                       M.LearningEvidence(knowledge_point_id="A", timestamp=t0 + 1 * D, source="book", evidence_id="ev2", result="incorrect")]
q = {t.knowledge_point_id: t for t in s.build_review_queue(p, now=t0 + 3.01 * D)}
A = q["A"]
rec("T-26A", A.priority == 1 and A.evidence_source == "book" and A.evidence_id == "ev2" and A.reason == "due now; retrievability 100%; recent failure; latest Book assessment: incorrect.", (A.priority, A.evidence_source, A.evidence_id, A.reason))
B = q["B"]; rec("T-26B", B.priority == 3 and B.evidence_source == "" and B.evidence_id == "", (B.priority, B.evidence_source, B.evidence_id, B.reason))
rec("T-26C", "C" in q, (q.get("C").knowledge_type if "C" in q else None, q["C"].priority if "C" in q else None))

ok = 0
for tid, c, o in out:
    ok += bool(c); print(("PASS " if c else "FAIL ") + tid, "" if c else f"-> {o}")
print(f"\n통과 {ok} / 전체 {len(out)}")
