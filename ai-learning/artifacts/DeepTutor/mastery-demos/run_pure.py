"""원본 순수 모듈을 기준 SHA에서 꺼내 임시 폴더에 복사해 실행하고, 스펙 수락 사례(T-ID)의 기대값과 비교한다.

사용: python3 -I run_pure.py <repo 경로> <샌드박스 폴더>
- 원본 repo는 읽기만 한다(`git show <SHA>:<path>`). 샌드박스는 새로 만든 빈 폴더여야 한다.
- 복사하는 파일은 순수 계산 모듈뿐이다: learning/{models,policy,mastery,scheduler,pending,objective_relations,grading}.py,
  utils/text_display.py. service.py·storage.py(SQLite)는 실행하지 않는다.
"""
import math, os, subprocess, sys, time, traceback
from pathlib import Path

SHA = "a31d82624c27d75f4e771d4fcb78dce16470b383"
repo, sandbox = Path(sys.argv[1]), Path(sys.argv[2])
assert not sandbox.exists() or not any(sandbox.iterdir()), "샌드박스가 비어 있지 않다"
files = [f"deeptutor/learning/{n}.py" for n in
         ("models", "policy", "mastery", "scheduler", "pending", "objective_relations", "grading")] \
        + ["deeptutor/utils/text_display.py"]
for f in files:
    out = sandbox / f
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(subprocess.run(["git", "-C", str(repo), "show", f"{SHA}:{f}"],
                                  check=True, capture_output=True, text=True).stdout, encoding="utf-8")
for d in ("deeptutor", "deeptutor/learning", "deeptutor/utils"):
    (sandbox / d / "__init__.py").write_text("", encoding="utf-8")
sys.path.insert(0, str(sandbox))
os.environ.pop("LEARNING_DEBUG", None)

from deeptutor.learning.models import (DeferredObjective, KnowledgePoint, KnowledgeType as KT, LearnerMasteryOverride,
                                       LearningEvidence, LearningModule, LearningProgress, PendingQuestion, ReviewTask)
from deeptutor.learning import policy, scheduler as S, objective_relations as OR, grading
from deeptutor.learning.mastery import compute_mastery

D = 86400.0
results = []
def check(tid, cond, observed):
    results.append((tid, bool(cond), observed))
def run(tid, fn):
    try:
        fn()
    except Exception as e:
        results.append((tid, False, f"예외 {type(e).__name__}: {e}\n{traceback.format_exc(limit=2)}"))
approx = lambda a, b, tol=None: abs(a - b) <= 1e-3  # 스펙이 선언한 허용오차(±0.001)로 고정. 호출부의 tol 인자는 무시한다

def progress(kps, **kw):
    mods = {}
    for i, (kid, kt, mod) in enumerate(kps):
        mods.setdefault(mod, []).append(KnowledgePoint(id=kid, name=kid.upper(), type=kt, module_id=mod))
    p = LearningProgress(book_id="b", modules=[LearningModule(id=m, name=m, order=i, knowledge_points=v)
                         for i, (m, v) in enumerate(mods.items())], **kw)
    p.knowledge_types = {kid: kt for kid, kt, _ in kps}
    return p

# ---- mastery-engine ----
def t_mastery():
    check("ME-T01", compute_mastery([]) == 0.0, compute_mastery([]))
    r = [compute_mastery([True]), compute_mastery([True, True]), compute_mastery([True, True, True])]
    check("ME-T02", r == [0.5, 0.8, 1.0], r)
    v = compute_mastery([False, True, True, True, True])
    check("ME-T03", approx(v, 0.875) and v < 0.9, v)
    v = compute_mastery([True, True, True, True, 0.5])
    check("ME-T04(compute_mastery 부분만)", approx(v, 0.875), v)
run("ME-T01~04", t_mastery)

def t_t06_07():
    p = progress([("a", KT.CONCEPT, "m1")]); kp = p.modules[0].knowledge_points[0]
    p.mastery_levels["a"] = 1.0
    check("ME-T06a", not policy.is_mastered(p, kp), policy.is_mastered(p, kp))
    p.qualitative_mastery["a"] = True
    check("ME-T06b", policy.is_mastered(p, kp) and policy.mastery_source(p, kp) == "system", policy.mastery_source(p, kp))
    p2 = progress([("a", KT.CONCEPT, "m1")]); kp2 = p2.modules[0].knowledge_points[0]
    p2.mastery_levels["a"] = 0.3
    p2.learner_mastery_overrides["a"] = LearnerMasteryOverride(knowledge_point_id="a")
    ok = (policy.is_mastered(p2, kp2) and policy.mastery_source(p2, kp2) == "learner"
          and policy.objective_status(p2, kp2) == "mastered" and approx(policy.display_mastery(p2, kp2), 0.3))
    check("ME-T07", ok, (policy.mastery_source(p2, kp2), policy.objective_status(p2, kp2), policy.display_mastery(p2, kp2)))
run("ME-T06/07", t_t06_07)

def t_next():
    now = 1_000_000.0
    # T-08
    p = progress([("a", KT.MEMORY, "m1")])
    p.pending_question = PendingQuestion(question_id="q1", knowledge_point_id="a", prompt="?")
    st = S.SpacedRepetitionScheduler(); p.repetition_states["a"] = st.get_initial_state(KT.MEMORY, now=now - 5 * D)
    p.review_queue = st.build_review_queue(p, now=now)
    check("ME-T08", policy.next_objective(p, now=now).action == "answer_pending", policy.next_objective(p, now=now).action)
    # T-09
    p = progress([("a", KT.MEMORY, "m1"), ("b", KT.MEMORY, "m1")]); p.mastery_levels = {"a": 1.0}
    p.repetition_states["a"] = st.get_initial_state(KT.CONCEPT, now=now - 10 * D)
    p.knowledge_types["a"] = KT.CONCEPT
    p.review_queue = st.build_review_queue(p, now=now)
    n = policy.next_objective(p, now=now)
    check("ME-T09", n.action == "review" and n.knowledge_point_id == "a", (n.action, n.knowledge_point_id))
    # T-10
    p = progress([("A", KT.MEMORY, "m1"), ("B", KT.MEMORY, "m1"), ("C", KT.MEMORY, "m2")]); p.mastery_levels = {"A": 1.0}
    n = policy.next_objective(p, now=now)
    check("ME-T10a", n.knowledge_point_id == "B" and n.action == "probe", (n.knowledge_point_id, n.action))
    from deeptutor.learning.models import LearnerProfile
    try:
        p.learner_profile = LearnerProfile(teaching_strategy="teach_first")
        n = policy.next_objective(p, now=now)
        check("ME-T10b", n.action == "teach", n.action)
    except Exception as e:
        check("ME-T10b", False, f"{type(e).__name__}: {e}")
    # T-11
    p = progress([("a", KT.MEMORY, "m1"), ("b", KT.MEMORY, "m1")])
    p.deferred_objectives = {"a": DeferredObjective(knowledge_point_id="a"), "b": DeferredObjective(knowledge_point_id="b")}
    n = policy.next_objective(p, now=now)
    check("ME-T11", n.knowledge_point_id == "a", (n.action, n.knowledge_point_id))
    # T-12
    p = progress([("a", KT.MEMORY, "m1")]); p.mastery_levels = {"a": 0.95}
    check("ME-T12", policy.next_objective(p, now=now).action == "complete", policy.next_objective(p, now=now).action)
    # T-24
    p = progress([("a", KT.MEMORY, "m1"), ("b", KT.MEMORY, "m1")])
    p.modules[0].knowledge_points[0].prerequisite_ids = ["b"]
    n = policy.next_objective(p, now=now)
    check("ME-T24", n.knowledge_point_id == "a", (n.action, n.knowledge_point_id))
run("ME-T08~12,24", t_next)

def t_grade():
    check("ME-T13a", grading.grade_answer(" b ", "B", "choice") is True, grading.grade_answer(" b ", "B", "choice"))
    r2 = grading.grade_answer("photosyntesis", "photosynthesis", "short")
    check("ME-T13b", r2 is True, r2)
    r3 = grading.grade_answer("x", "", "short")
    check("ME-T13c", r3 is False, r3)
    a = grading.grade_answer("I used a and b", "a, b, c", "open"); b = grading.grade_answer("only a", "a, b, c", "open")
    check("ME-T14", a is True and b is False, (a, b))
run("ME-T13/14", t_grade)

def t_rel():
    def mk(prereq):
        return [LearningModule(id="m", name="m", order=0, knowledge_points=[
            KnowledgePoint(id=k, name=k.upper(), type=KT.CONCEPT, module_id="m", prerequisite_ids=v) for k, v in prereq.items()])]
    for tid, spec, frag in (("ME-T22", {"a": ["a"]}, "own prerequisite"), ("ME-T23", {"a": ["b"], "b": ["a"]}, "Prerequisite cycle")):
        try:
            OR.validate_objective_relations(mk(spec), [])
            check(tid, False, "예외 없음")
        except OR.ObjectiveRelationError as e:
            check(tid, frag in str(e), str(e))
run("ME-T22/23", t_rel)

# ---- review-scheduler ----
sch = S.SpacedRepetitionScheduler()
t0 = 2_000_000.0
def ev(q=None, result="correct", hints=0, attempts=1, t=0.0):
    return LearningEvidence(knowledge_point_id="a", timestamp=t, result=result, quality=q, hints_used=hints, attempt_count=attempts)

def rs1():
    s = sch.get_initial_state(KT.CONCEPT, now=t0)
    check("RS-T01", approx(s.stability, 28.4737, 1e-2) and approx(s.difficulty, 0.4) and approx(s.next_review_at, t0 + 3 * D, 1)
          and s.last_scheduled_at == t0 and s.last_review_at is None, (s.stability, s.difficulty, (s.next_review_at - t0) / D))
    s = sch.get_initial_state(KT.CONCEPT, now=t0, desired_retention=0.8)
    check("RS-T02", approx(s.stability, 28.4737, 1e-2) and approx((s.next_review_at - t0) / D, 6.354, 5e-3) and s.desired_retention == 0.8,
          (s.stability, (s.next_review_at - t0) / D, s.desired_retention))
    s = sch.get_initial_state(KT.MEMORY, now=t0)
    check("RS-T03", s.stability == 0.5 and approx(s.difficulty, 0.3) and s.next_review_at == t0, (s.stability, s.difficulty, s.next_review_at - t0))
    res = []
    for v in (0.69, 0.7, 0.99, float("nan")):
        try: S.validate_desired_retention(v); res.append("ok")
        except ValueError: res.append("ValueError")
    check("RS-T04", res == ["ValueError", "ok", "ok", "ValueError"], res)
run("RS-T01~04", rs1)

def rs5():
    q = [S._resolved_quality(ev(None, "correct", 2, 3)), S._resolved_quality(ev(None, "partial")), S._resolved_quality(ev(0.3, "partial"))]
    check("RS-T05", approx(q[0], 0.74) and approx(q[1], 0.4) and approx(q[2], 0.3), q)
run("RS-T05", rs5)

def base():
    return sch.get_initial_state(KT.CONCEPT, now=t0)
def rs6_8():
    now = t0 + 3 * D
    s = sch.schedule_review(base(), KT.CONCEPT, ev(1.0, t=now), now=now)
    check("RS-T06", approx(s.difficulty, 0.352) and s.consecutive_correct == 1 and s.review_count == 1 and approx(s.stability, 60.8995, 5e-2)
          and approx((s.next_review_at - now) / D, 6.416, 5e-3) and s.interval_index == 1 and s.scheduled_after_failure is False,
          (s.difficulty, s.stability, (s.next_review_at - now) / D, s.interval_index))
    s = sch.schedule_review(base(), KT.CONCEPT, ev(0.0, "incorrect", t=now), now=now)
    check("RS-T07", approx(s.difficulty, 0.552) and s.lapse_count == 1 and s.consecutive_wrong == 1 and approx(s.stability, 7.3633, 5e-2)
          and approx(s.retrievability, 0.2, 1e-2) and s.scheduled_after_failure and approx((s.next_review_at - now) / D, 0.388, 5e-3) and s.interval_index == 0,
          (s.difficulty, s.stability, s.retrievability, (s.next_review_at - now) / D, s.interval_index))
    s = sch.schedule_review(base(), KT.CONCEPT, ev(0.5, "partial", t=now), now=now)
    check("RS-T08", approx(s.difficulty, 0.452) and approx(s.stability, 28.4737, 1e-2) and approx((s.next_review_at - now) / D, 3.0, 5e-3) and s.consecutive_correct == 1,
          (s.difficulty, s.stability, (s.next_review_at - now) / D, s.consecutive_correct))
run("RS-T06~08", rs6_8)

def rs9_10():
    now = t0 + 3 * D
    s1 = sch.schedule_review(base(), KT.CONCEPT, ev(1.0, t=now), now=now)
    snap = s1.model_copy(deep=True)
    m = now + 0.1 * D
    s2 = sch.schedule_review(s1.model_copy(deep=True), KT.CONCEPT, ev(1.0, t=m), now=m)
    same = (s2.review_count == 2 and s2.last_review_at == m and approx(s2.retrievability, 1.0)
            and s2.stability == snap.stability and s2.next_review_at == snap.next_review_at and s2.last_scheduled_at == snap.last_scheduled_at
            and s2.difficulty == snap.difficulty and s2.consecutive_correct == snap.consecutive_correct)
    check("RS-T09", same, (s2.review_count, s2.stability, snap.stability, s2.next_review_at - snap.next_review_at))
    s3 = sch.schedule_review(s1.model_copy(deep=True), KT.CONCEPT, ev(0.0, "incorrect", t=m), now=m)
    check("RS-T10a", s3.lapse_count == snap.lapse_count + 1 and s3.stability < snap.stability and s3.scheduled_after_failure,
          (s3.lapse_count, s3.stability, s3.scheduled_after_failure))
    pre = s1.model_copy(deep=True); pre.scheduled_after_failure = True
    s4 = sch.schedule_review(pre.model_copy(deep=True), KT.CONCEPT, ev(0.2, "partial", t=m), now=m)
    check("RS-T10b", s4.review_count == pre.review_count + 1 and s4.stability == pre.stability and s4.next_review_at == pre.next_review_at,
          (s4.review_count, pre.review_count, s4.stability, pre.stability))
run("RS-T09/10", rs9_10)

def rs11():
    s = sch.get_initial_state(KT.MEMORY, now=t0)
    s = sch.schedule_review(s, KT.MEMORY, ev(1.0, t=t0), now=t0)
    check("RS-T11", approx(s.difficulty, 0.264) and approx(s.stability, 1.096, 5e-3) and approx((s.next_review_at - t0) / D, 0.115, 2e-3) and s.interval_index == 0,
          (s.difficulty, s.stability, (s.next_review_at - t0) / D, s.interval_index))
run("RS-T11", rs11)

def rs12_13():
    s = base(); s.stability = 10.0; s.last_review_at = t0
    r = sch.retrievability(s, now=t0 + 10 * D)
    check("RS-T12a", approx(r, math.exp(-1), 2e-3), r)
    s2 = base(); s2.last_review_at = None; s2.next_review_at = t0 + 5 * D
    r = sch.retrievability(s2, now=t0)
    check("RS-T12b", r == 1.0, r)
    p = progress([("a", KT.CONCEPT, "m1")])
    st = base(); st.stability = 10.0; st.last_review_at = t0; st.next_review_at = t0 + 5 * D; st.lapse_count = 0
    now = t0 + 10 * D
    r0 = sch.forgetting_risk(st, p, "a", now=now)
    st.lapse_count = 1
    r1 = sch.forgetting_risk(st, p, "a", now=now)
    from deeptutor.learning.models import ErrorRecord, ErrorType
    p.error_records = [ErrorRecord(id="e", question_id="q", knowledge_point_id="a", module_id="m1", error_type=ErrorType("application"), status="active")]
    r2 = sch.forgetting_risk(st, p, "a", now=now)
    check("RS-T13", approx(r0, 0.882, 3e-3) and approx(r1, 0.982, 3e-3) and r2 == 1.0, (r0, r1, r2))
run("RS-T12/13", rs12_13)

def rs14():
    now = t0 + 100 * D
    p = progress([("A", KT.CONCEPT, "m1"), ("B", KT.CONCEPT, "m1")])
    a = base(); a.next_review_at = now - D; b = base(); b.next_review_at = now + 5 * D
    p.repetition_states = {"A": a, "B": b}
    p.review_queue = sch.build_review_queue(p, now=now)
    ids = [t.knowledge_point_id for t in p.review_queue]
    due = [t.knowledge_point_id for t in policy.due_reviews(p, now=now)]
    check("RS-T14", ids == ["A", "B"] and due == ["A"], (ids, due, [round(t.forgetting_risk, 4) for t in p.review_queue]))
run("RS-T14", rs14)

def rs15_17():
    s0 = sch.replay(KT.CONCEPT, [], now=t0)
    check("RS-T15a", s0 is not None and s0.review_count == 0, s0)
    try:
        sch.replay(KT.CONCEPT, [ev(1.0, t=t0 + D)], now=t0 + D, desired_retention=0.8, initial_state=base())
        check("RS-T15b", False, "예외 없음")
    except ValueError as e:
        check("RS-T15b", True, str(e))
    p = progress([("a", KT.CONCEPT, "m1")]); p.repetition_states["a"] = sch.get_initial_state(KT.CONCEPT, now=t0)
    sch.set_desired_retention(p, 0.8, now=t0)
    s = p.repetition_states["a"]
    check("RS-T16", approx(s.stability, 28.4737, 1e-2) and approx((s.next_review_at - t0) / D, 6.354, 5e-3) and s.interval_index == 1 and s.desired_retention == 0.8,
          (s.stability, (s.next_review_at - t0) / D, s.interval_index, s.desired_retention))
    os.environ["LEARNING_DEBUG"] = "1"
    try:
        dbg = S.SpacedRepetitionScheduler()
        s = dbg.get_initial_state(KT.CONCEPT, now=t0)
        check("RS-T17", approx(s.next_review_at - t0, 3.0, 1e-6), s.next_review_at - t0)
    finally:
        os.environ.pop("LEARNING_DEBUG", None)
run("RS-T15~17", rs15_17)

ok = sum(1 for _, c, _ in results if c)
for tid, c, obs in results:
    print(("PASS " if c else "FAIL ") + tid, "" if c else f"-> {obs}")
print(f"\n통과 {ok} / 전체 {len(results)}")
