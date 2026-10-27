"""원본(기준 SHA 복사본)과 스펙-only 재구현을 같은 입력으로 비교한다.
사용: python3 -I diff_test.py <원본 샌드박스(run_pure.py가 만든 폴더)> <재구현 폴더(reimpl_learning의 부모)>
출력 형태: 비교한 사례 수와 불일치 목록. 같은 입력, 같은 시드(고정)로만 말한다.
"""
import dataclasses, math, os, random, sys
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2])
os.environ.pop("LEARNING_DEBUG", None)
import deeptutor.learning.models as OM, deeptutor.learning.scheduler as OS, deeptutor.learning.policy as OP, deeptutor.learning.grading as OG
from deeptutor.learning.mastery import compute_mastery as o_cm
import reimpl_learning.models as RM, reimpl_learning.scheduler as RS, reimpl_learning.engine as RE

D = 86400.0
mism = []; counts = {}
def note(kind, ok, detail=""):
    counts[kind] = counts.get(kind, 0) + 1
    if not ok and len([m for m in mism if m[0] == kind]) < 6:
        mism.append((kind, detail))
    if not ok: counts[kind + "!"] = counts.get(kind + "!", 0) + 1

def close(a, b, tol=1e-9):
    if a is None or b is None: return a is b
    if isinstance(a, bool) or isinstance(b, bool): return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)): return abs(a - b) <= tol * max(1.0, abs(a), abs(b))
    return a == b

def od(o):  # 원본 pydantic -> dict
    return o.model_dump()
def rd(r):
    return dataclasses.asdict(r)
def cmp_dict(kind, a, b, keys=None):
    keys = keys or sorted(set(a) & set(b))
    bad = [(k, a[k], b[k]) for k in keys if not close(a[k], b[k])]
    note(kind, not bad, bad[:3])

rng = random.Random(20261027)

# 1) compute_mastery
for _ in range(2000):
    n = rng.randint(0, 8)
    xs = [rng.choice([True, False, 0.0, 0.5, 1.0, rng.random()]) for _ in range(n)]
    note("compute_mastery", close(o_cm(xs), RE.compute_mastery(xs)), xs)

# 2) grade_answer
exp_pool = ["B", "photosynthesis", "a, b, c", "The mitochondria produces ATP", "42", "x^2 + 1", ""]
ans_pool = [" b ", "B", "photosyntesis", "I used a and b", "only a", "mitochondria make atp", "42.0", "x^2+1", "", "c", "a b c"]
for qt in ("choice", "short", "open"):
    for e in exp_pool:
        for a in ans_pool:
            note("grade_answer", OG.grade_answer(a, e, qt) == RE.grade_answer(a, e, qt), (a, e, qt))

# 3) 스케줄러: 증거 열 -> 상태 전이
oS = OS.SpacedRepetitionScheduler(); rS = RS.SpacedRepetitionScheduler()
KTS = ["memory", "concept", "procedure", "design"]
def mk_ev(kp, t):
    q = rng.choice([None, None, 0.0, 0.2, 0.3, 0.5, 0.6, 0.8, 1.0])
    res = rng.choice(["correct", "partial", "incorrect"])
    kw = dict(knowledge_point_id=kp, timestamp=t, result=res, quality=q, hints_used=rng.choice([0, 0, 1, 2, 3]),
              attempt_count=rng.choice([1, 1, 2, 3]), assessment_type=rng.choice(["quiz", "qualitative", "review"]))
    return kw
FIELDS = ["interval_index", "consecutive_correct", "consecutive_wrong", "next_review_at", "difficulty", "stability",
          "retrievability", "desired_retention", "review_count", "lapse_count", "last_review_at", "last_scheduled_at",
          "scheduled_after_failure"]
for trial in range(400):
    kt = rng.choice(KTS); t0 = 1_900_000_000.0 + rng.random() * 1e6
    dr = rng.choice([None, 0.7, 0.8, 0.9, 0.95, 0.99])
    os_ = oS.get_initial_state(OM.KnowledgeType(kt), now=t0, desired_retention=dr)
    rs_ = rS.get_initial_state(RM.KnowledgeType(kt), now=t0, desired_retention=dr)
    cmp_dict("initial_state", od(os_), rd(rs_), FIELDS)
    now = t0; evs = []
    for step in range(rng.randint(1, 8)):
        now += rng.choice([0.01, 0.05, 0.2, 0.249, 0.26, 0.28, 0.3, 1, 2, 3, 7, 14, 40]) * D  # 0.249/0.26/0.28은 같은 세션 창(0.25일) 경계 확인용
        kw = mk_ev("a", now); evs.append(kw)
        os_ = oS.schedule_review(os_, OM.KnowledgeType(kt), OM.LearningEvidence(**kw), now=now)
        rs_ = rS.schedule_review(rs_, RM.KnowledgeType(kt), RM.LearningEvidence(**kw), now=now)
        cmp_dict("schedule_review", od(os_), rd(rs_), FIELDS)
        probe = now + rng.choice([0, 0.5, 3, 20]) * D
        note("retrievability", close(oS.retrievability(os_, now=probe), rS.retrievability(rs_, now=probe)), (kw, probe - now))
    # replay
    ostate = oS.replay(OM.KnowledgeType(kt), [OM.LearningEvidence(**k) for k in evs], now=now, desired_retention=dr)
    rstate = rS.replay(RM.KnowledgeType(kt), [RM.LearningEvidence(**k) for k in evs], now=now, desired_retention=dr)
    cmp_dict("replay", od(ostate), rd(rstate), FIELDS)
    # forgetting risk (오류 기록 없음/있음)
    op = OM.LearningProgress(book_id="p"); rp = RM.LearningProgress(book_id="p")
    for cond in (False, True):
        if cond:
            op.error_records = [OM.ErrorRecord(id="e", question_id="q", knowledge_point_id="a", module_id="m", error_type=OM.ErrorType("application"), status="active")]
            rp.error_records = [RM.ErrorRecord(id="e", question_id="q", knowledge_point_id="a", module_id="m", error_type=RM.ErrorType("application"), status="active")]
        pn = now + rng.choice([0, 1, 10]) * D
        note("forgetting_risk", close(oS.forgetting_risk(os_, op, "a", now=pn), rS.forgetting_risk(rs_, rp, "a", now=pn)), (cond, pn - now))

# 4) next_objective: 임의 경로 상태
def build(M, n_mod, rng2):
    kps = []
    for mi in range(n_mod):
        pts = [M.KnowledgePoint(id=f"k{mi}_{j}", name=f"K{mi}_{j}", type=M.KnowledgeType(rng2.choice(KTS)), module_id=f"m{mi}")
               for j in range(rng2.randint(1, 3))]
        kps.append(M.LearningModule(id=f"m{mi}", name=f"M{mi}", order=mi, knowledge_points=pts))
    return kps
NOW = 1_950_000_000.0
for trial in range(600):
    seed = rng.randrange(10**9)
    rngs = [random.Random(seed), random.Random(seed)]
    progs = []
    for M, mods_rng in ((OM, rngs[0]), (RM, rngs[1])):
        mods = build(M, rng.randint(1, 3) if False else 2, mods_rng)  # 모듈 2개 고정, 크기는 시드로 동일
        progs.append(mods)
    ids = [kp.id for m in progs[0] for kp in m.knowledge_points]
    # 같은 확률 선택 (한 번만 뽑아 양쪽에 적용)
    mastery = {i: rng.choice([0.0, 0.3, 0.6, 0.9, 1.0]) for i in ids if rng.random() < 0.7}
    qual = {i: rng.choice([True, False]) for i in ids if rng.random() < 0.4}
    overrides = [i for i in ids if rng.random() < 0.15]
    deferred = [i for i in ids if rng.random() < 0.15]
    pending = rng.choice([None, None, None, rng.choice(ids)])
    strat = rng.choice([None, "probe_first", "teach_first"])
    reviews = {i: rng.choice([-5, -1, 3]) for i in ids if rng.random() < 0.3}
    attempted = [i for i in ids if rng.random() < 0.5]
    out = []
    for M, mods, S_, sch in ((OM, progs[0], OS, oS), (RM, progs[1], RS, rS)):
        p = M.LearningProgress(book_id="p", modules=mods)
        p.knowledge_types = {kp.id: kp.type for m in mods for kp in m.knowledge_points}
        p.mastery_levels = dict(mastery); p.qualitative_mastery = dict(qual)
        for i in overrides: p.learner_mastery_overrides[i] = M.LearnerMasteryOverride(knowledge_point_id=i)
        for i in deferred: p.deferred_objectives[i] = M.DeferredObjective(knowledge_point_id=i)
        if pending: p.pending_question = M.PendingQuestion(question_id="q1", knowledge_point_id=pending, prompt="?")
        if strat:
            try: p.learner_profile = M.LearnerProfile(teaching_strategy=strat)
            except Exception as e: out.append(("ERR", repr(e)))
        for i in attempted:
            p.quiz_attempts.append(M.QuizAttempt(question_id="x" + i, knowledge_point_id=i, is_correct=True))
        for i, d in reviews.items():
            kt = p.knowledge_types[i]
            st = sch.get_initial_state(kt, now=NOW + d * D - 3 * D)
            st.next_review_at = NOW + d * D
            p.repetition_states[i] = st
        p.review_queue = sch.build_review_queue(p, now=NOW)
        n = (OP if M is OM else RE).next_objective(p, now=NOW)
        out.append({k: getattr(n, k) for k in ("action", "knowledge_point_id", "status", "gate", "mastery", "threshold", "forgetting_risk")})
    if out and isinstance(out[0], tuple):
        note("next_objective", False, out); continue
    bad = [(k, out[0][k], out[1][k]) for k in out[0] if not close(out[0][k], out[1][k], 1e-6)]
    note("next_objective", not bad, (bad, "pending", pending, "strat", strat))

print("비교한 사례 수:", {k: v for k, v in counts.items() if not k.endswith("!")})
print("불일치 수:", {k[:-1]: v for k, v in counts.items() if k.endswith("!")} or "없음")
for k, d in mism: print("  불일치", k, d)
