"""Mastery engine (mastery-engine.md R-01..R-22): policy, mastery, grading, service, memory store."""
from __future__ import annotations

import copy
import re
import time
import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher

from .models import (
    ACTIVE_STATUSES, DeferredObjective, ErrorRecord, ErrorType, InteractionStatus,
    KnowledgeType, LearnerMasteryOverride, LearningEvidence, LearningProgress,
    MasteryInteraction, MasteryInteractionError, NoPendingInteractionError,
    ObjectiveRelationError, QuizAttempt, RetryAttempt, StaleInteractionError,
)
from .scheduler import review_sort_key

K = KnowledgeType
QUANTITATIVE_GATE = {K.MEMORY: 0.9, K.PROCEDURE: 0.9}
QUALITATIVE_TYPES = frozenset({K.CONCEPT, K.DESIGN})
_QUAL_PASS_DISPLAY = 1.0

# ---------------------------------------------------------------- mastery (R-08)
_WEIGHTS = (0.5, 0.7, 0.85, 0.95, 1.0)
_CAP = {1: 0.5, 2: 0.8}


def compute_mastery(correctness) -> float:
    if not correctness:
        return 0.0
    recent = list(correctness)[-len(_WEIGHTS):]
    w = _WEIGHTS[-len(recent):]
    score = sum(wi * max(0.0, min(1.0, float(c))) for c, wi in zip(recent, w)) / sum(w)
    return min(score, _CAP.get(len(recent), 1.0))


# ---------------------------------------------------------------- grading (R-10, R-11)
def grade_answer(user_answer: str, expected_answer: str, question_type: str = "short") -> bool:
    user = user_answer.strip().lower()
    expected = expected_answer.strip().lower()
    if not expected:
        return False
    if question_type == "choice":
        return user.replace(" ", "") == expected.replace(" ", "")
    if question_type == "short":
        if user == expected:
            return True
        if len(expected) <= 30:
            return SequenceMatcher(None, user, expected).ratio() >= 0.85
        return False
    if question_type == "open":
        kws = [k.strip() for k in re.split(r"[,;，；。\n]+", expected) if k.strip()]
        if not kws:
            return False
        return sum(1 for kw in kws if kw in user) / len(kws) >= 0.6
    return False


def classify_error(user_answer: str) -> ErrorType:
    return ErrorType.METACOGNITIVE if not user_answer.strip() else ErrorType.APPLICATION_ERROR


# ---------------------------------------------------------------- policy (R-03..R-07, R-20)
def gate_threshold(kp_type) -> float:
    kp_type = KnowledgeType(kp_type)
    if kp_type in QUALITATIVE_TYPES:
        return _QUAL_PASS_DISPLAY
    return QUANTITATIVE_GATE.get(kp_type, 0.9)


def gate_kind(kp) -> str:
    return "qualitative" if kp.type in QUALITATIVE_TYPES else "quantitative"


def visual_achievements(progress, kp_id) -> list:
    return sorted({e.visual_context["task"] for e in progress.learning_evidence
                   if e.knowledge_point_id == kp_id and e.result == "correct"
                   and e.visual_context.get("task")
                   and e.visual_context.get("key_status") == "verified" and not e.hints_used})


def is_assessed_mastered(progress, kp) -> bool:
    if not set(kp.required_visual_tasks).issubset(visual_achievements(progress, kp.id)):
        return False
    if kp.type in QUALITATIVE_TYPES:
        return bool(progress.qualitative_mastery.get(kp.id, False))
    return progress.mastery_levels.get(kp.id, 0.0) >= gate_threshold(kp.type)


def mastery_source(progress, kp) -> str:
    if is_assessed_mastered(progress, kp):
        return "system"
    if kp.id in progress.learner_mastery_overrides:
        return "learner"
    return ""


def is_mastered(progress, kp) -> bool:
    return bool(mastery_source(progress, kp))


def display_mastery(progress, kp) -> float:
    if kp.type in QUALITATIVE_TYPES and progress.qualitative_mastery.get(kp.id):
        return _QUAL_PASS_DISPLAY
    return float(progress.mastery_levels.get(kp.id, 0.0))


def objective_status(progress, kp) -> str:
    if is_mastered(progress, kp):
        return "mastered"
    seen = (any(a.knowledge_point_id == kp.id for a in progress.quiz_attempts)
            or kp.id in progress.qualitative_mastery)
    return "learning" if seen else "new"


def learning_stage(progress, kp_id) -> str:
    attempts = [a for a in progress.quiz_attempts if a.knowledge_point_id == kp_id and not a.voided]
    ev = [e for e in progress.learning_evidence if e.knowledge_point_id == kp_id]
    if any(a.independent and a.is_correct for a in attempts) or any(
            e.assessment_type == "qualitative" and e.result == "correct" and not e.hints_used
            for e in ev):
        return "independently_demonstrated"
    if any(not a.independent for a in attempts) or any(e.hints_used for e in ev):
        return "practiced_with_help"
    if attempts or ev:
        return "practiced_not_demonstrated"
    ex = progress.explained_objectives.get(kp_id)
    if not ex:
        return "not_yet_covered"
    if (ex.get("coverage") == "partial" and ex.get("explanation_quote")
            and ex.get("delivery", {}).get("turn_id")):
        return "partially_explained"
    return "teaching_record_unverified"


def find_knowledge_point(progress, kp_id):
    for m in progress.modules:
        for kp in m.knowledge_points:
            if kp.id == kp_id:
                return kp, m.id, m.name
    return None, "", ""


def due_reviews(progress, *, now=None) -> list:
    moment = time.time() if now is None else now
    due = [t for t in progress.review_queue if t.due_at <= moment]
    due.sort(key=lambda t: review_sort_key(t, now=moment))
    return due


@dataclass(frozen=True)
class NextStep:
    action: str
    module_id: str = ""
    module_name: str = ""
    knowledge_point_id: str = ""
    knowledge_point_name: str = ""
    knowledge_point_type: str = ""
    status: str = ""
    gate: str = ""
    mastery: float = 0.0
    threshold: float = 0.0
    reason: str = ""
    forgetting_risk: float = 0.0
    pending_prompt: str = ""
    pending_question: dict | None = None  # public projection: no answer key / explanation
    session_id: str = ""


def _public_pending(p) -> dict:
    # ponytail: projection fields are my guess (spec: key/explanation are omitted)
    return {"question_id": p.question_id, "knowledge_point_id": p.knowledge_point_id,
            "module_id": p.module_id, "prompt": p.prompt, "question_type": p.question_type,
            "options": list(p.options)}


def next_objective(progress, *, now=None, pending_session_id: str = "") -> NextStep:
    p = progress.pending_question
    if p is not None:
        kp, mid, mname = find_knowledge_point(progress, p.knowledge_point_id)
        return NextStep(
            action="answer_pending", module_id=mid or p.module_id, module_name=mname,
            knowledge_point_id=p.knowledge_point_id,
            knowledge_point_name=kp.name if kp else "",
            knowledge_point_type=kp.type.value if kp else "",
            status=objective_status(progress, kp) if kp else "learning",
            gate=gate_kind(kp) if kp else "",
            mastery=display_mastery(progress, kp) if kp else 0.0,
            threshold=gate_threshold(kp.type) if kp else 0.0,
            reason="A posed question is awaiting the learner's answer; grade it with mastery_grade.",
            pending_prompt=p.prompt, pending_question=_public_pending(p),
            session_id=str(pending_session_id or ""))
    deferred = set(progress.deferred_objectives)
    due = [t for t in due_reviews(progress, now=now) if t.knowledge_point_id not in deferred]
    if due:
        kp, mid, mname = find_knowledge_point(progress, due[0].knowledge_point_id)
        if kp is not None:
            t = due[0]
            return NextStep(
                action="review", module_id=mid, module_name=mname, knowledge_point_id=kp.id,
                knowledge_point_name=kp.name, knowledge_point_type=kp.type.value,
                status=objective_status(progress, kp), gate=gate_kind(kp),
                mastery=display_mastery(progress, kp), threshold=gate_threshold(kp.type),
                reason=t.reason or "This objective is due for spaced-repetition review.",
                forgetting_risk=t.forgetting_risk)
    fallback = None
    for m in sorted(progress.modules, key=lambda m: m.order):
        for kp in m.knowledge_points:
            if is_mastered(progress, kp):
                continue
            status = objective_status(progress, kp)
            gate = gate_kind(kp)
            if status == "new":
                action = ("teach" if progress.learner_profile is not None
                          and progress.learner_profile.teaching_strategy == "teach_first"
                          else "probe")
            elif gate == "qualitative":
                action = "assess"
            else:
                action = "practice"
            if status == "new":
                reason = ("Untouched objective — teach before assessing, as the learner requested."
                          if action == "teach"
                          else "Untouched objective — probe first to let the learner test out.")
            else:
                reason = "Objective is below its mastery gate; keep working it until it clears."
            step = NextStep(
                action=action, module_id=m.id, module_name=m.name, knowledge_point_id=kp.id,
                knowledge_point_name=kp.name, knowledge_point_type=kp.type.value, status=status,
                gate=gate, mastery=display_mastery(progress, kp),
                threshold=gate_threshold(kp.type), reason=reason)
            if kp.id in deferred:
                if fallback is None:
                    fallback = step
                continue
            return step
    if fallback is not None:
        return fallback
    return NextStep(action="complete", reason="All objectives are mastered and no reviews are due.")


# ---------------------------------------------------------------- objective relations (R-21)
def _normalize_refs(values) -> list:
    out, seen = [], set()
    for v in values or ():
        r = str(v or "").strip()
        if not r or r in seen:
            continue
        seen.add(r)
        out.append(r)
    return out


def validate_objective_relations(modules, sources=()) -> None:
    # ponytail: topic-source reference checks are ignored (spec says ignore); `sources` unused
    points = [kp for m in modules for kp in m.knowledge_points]
    if len({p.id for p in points}) != len(points):
        raise ObjectiveRelationError("Knowledge point ids must be unique within a mastery path")
    names = {p.id: p.name for p in points}
    graph = {}
    for p in points:
        p.prerequisite_ids = _normalize_refs(p.prerequisite_ids)
        graph[p.id] = p.prerequisite_ids
        p.topic_source_ids = _normalize_refs(p.topic_source_ids)
    for pid, pre in graph.items():
        for r in pre:
            if r == pid:
                raise ObjectiveRelationError(f"Objective {names[pid]!r} cannot be its own prerequisite")
            if r not in graph:
                raise ObjectiveRelationError(f"Objective {names[pid]!r} has unknown prerequisite {r!r}")
    visiting, visited, path = set(), set(), []

    def visit(pid):
        if pid in visited:
            return
        if pid in visiting:
            cyc = path[path.index(pid):] + [pid]
            raise ObjectiveRelationError("Prerequisite cycle: " + " -> ".join(cyc))
        visiting.add(pid)
        path.append(pid)
        for r in graph[pid]:
            visit(r)
        path.pop()
        visiting.remove(pid)
        visited.add(pid)

    for pid in graph:
        visit(pid)


# ---------------------------------------------------------------- service (R-09, R-12..R-15, R-18, R-19)
def update_mastery(progress, kp_id, value) -> None:
    progress.mastery_levels[kp_id] = value


def calculate_mastery(progress, kp_id) -> float:
    c = [0.5 if a.result == "partial" else a.is_correct for a in progress.quiz_attempts
         if a.knowledge_point_id == kp_id and not a.voided and a.independent]
    return compute_mastery(c)


def record_quiz_attempt(progress, attempt: QuizAttempt, *, now=None) -> None:
    ts = time.time() if now is None else now
    if not attempt.is_correct and attempt.error_type is not None:
        existing = next((r for r in progress.error_records
                         if r.question_id == attempt.question_id
                         and r.knowledge_point_id == attempt.knowledge_point_id), None)
        if existing is not None:
            existing.retry_history.append(RetryAttempt(
                timestamp=ts, is_correct=False, attempt_number=len(existing.retry_history) + 1))
            existing.status = "retrying"
        else:
            progress.error_records.append(ErrorRecord(
                id=uuid.uuid4().hex, question_id=attempt.question_id,
                knowledge_point_id=attempt.knowledge_point_id, module_id=attempt.module_id,
                error_type=attempt.error_type, self_attribution=attempt.self_attribution,
                status="active", created_at=ts))
    elif attempt.is_correct:
        for r in progress.error_records:
            if (r.question_id == attempt.question_id
                    and r.knowledge_point_id == attempt.knowledge_point_id
                    and r.status in ("active", "retrying")):
                r.retry_history.append(RetryAttempt(
                    timestamp=ts, is_correct=True, attempt_number=len(r.retry_history) + 1))
                r.status = "graduated"
                break
    progress.quiz_attempts.append(attempt)
    progress.updated_at = ts


def _record_quiz_evidence(progress, kp_id, *, question_id="", is_correct, retrying=False,
                          session_id="", turn_id="", assessment_type="quiz", now=None):
    n = sum(1 for a in progress.quiz_attempts if a.knowledge_point_id == kp_id and not a.voided)
    ev = LearningEvidence(
        question_id=question_id, knowledge_point_id=kp_id, assessment_type=assessment_type,
        result="correct" if is_correct else "incorrect",
        quality=(0.6 if retrying else 1.0) if is_correct else 0.0,
        attempt_count=max(1, n), session_id=session_id, turn_id=turn_id,
        **({} if now is None else {"timestamp": now}))
    progress.learning_evidence.append(ev)
    return ev


def apply_grade(progress, *, question_id, knowledge_point_id, module_id="", user_answer,
                expected_answer, question_type, self_attribution="", scheduler=None,
                session_id="", turn_id="", visual_context=None, assistance_used=False,
                verdict=None, now=None) -> bool:
    """R-13. `now` (epoch s) is my addition for deterministic timestamps; None = time.time()."""
    vc = visual_context or {}
    is_correct = (verdict["result"] == "correct" if verdict
                  else bool(expected_answer) and grade_answer(user_answer, expected_answer,
                                                              question_type))
    retrying = any(r.question_id == question_id and r.knowledge_point_id == knowledge_point_id
                   and r.status in ("active", "retrying") for r in progress.error_records)
    already = knowledge_point_id in progress.repetition_states
    ts = {} if now is None else {"timestamp": now}
    record_quiz_attempt(progress, QuizAttempt(
        question_id=question_id, knowledge_point_id=knowledge_point_id, module_id=module_id,
        is_correct=is_correct,
        result=verdict["result"] if verdict else ("correct" if is_correct else "incorrect"),
        user_answer=user_answer, self_attribution=self_attribution,
        error_type=None if is_correct or verdict and verdict["result"] == "partial"
        else classify_error(user_answer),
        independent=not assistance_used and not vc.get("hints_used"),
        visual_context=vc, **ts), now=now)
    if knowledge_point_id:
        progress.deferred_objectives.pop(knowledge_point_id, None)
        ev = _record_quiz_evidence(
            progress, knowledge_point_id, question_id=question_id, is_correct=is_correct,
            retrying=retrying, session_id=session_id, turn_id=turn_id,
            assessment_type="review" if already else "quiz", now=now)
        ev.visual_context = vc
        ev.hints_used = max(int(vc.get("hints_used") or 0), int(assistance_used))
        if ev.hints_used and is_correct:
            ev.quality = min(ev.quality or 1.0, 0.6)
        if verdict:
            ev.result = verdict["result"]
            ev.quality = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}[verdict["result"]]
            ev.confidence = verdict.get("confidence")
            ev.learner_answer = user_answer
            ev.feedback = verdict.get("feedback", "")
            if ev.hints_used and is_correct:
                ev.quality = min(ev.quality, 0.6)
        update_mastery(progress, knowledge_point_id, calculate_mastery(progress, knowledge_point_id))
        kt = progress.knowledge_types.get(knowledge_point_id)
        if kt is not None and scheduler is not None:
            state = progress.repetition_states.get(knowledge_point_id) or scheduler.get_initial_state(
                kt, now=now, desired_retention=progress.desired_retention)
            progress.repetition_states[knowledge_point_id] = state
            scheduler.schedule_review(state, kt, ev)
            progress.review_queue = scheduler.build_review_queue(progress, now=now)
    return is_correct


grade_and_record = apply_grade  # ponytail: spec lists both names; same body (R-13)


def record_qualitative_in_memory(progress, kp_id, *, passed, evidence="", scheduler=None,
                                 session_id="", turn_id="", verdict=None, now=None) -> bool:
    evidence_id = ""
    if session_id or turn_id:
        evidence_id = uuid.uuid5(uuid.NAMESPACE_URL,
                                 f"deeptutor:qualitative:{session_id}:{turn_id}:{kp_id}").hex
        if any(e.evidence_id == evidence_id for e in progress.learning_evidence):
            return False
    progress.qualitative_mastery[kp_id] = bool(passed)
    progress.deferred_objectives.pop(kp_id, None)
    cur = progress.mastery_levels.get(kp_id, 0.0)
    progress.mastery_levels[kp_id] = max(cur, 1.0) if passed else min(cur, 0.4)
    if evidence:
        progress.feynman_explanations[kp_id] = evidence
    moment = time.time() if now is None else now
    table = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}
    ev = LearningEvidence(
        evidence_id=evidence_id, knowledge_point_id=kp_id, timestamp=moment,
        assessment_type="qualitative",
        result=verdict["result"] if verdict else ("correct" if passed else "partial"),
        quality=table[verdict["result"]] if verdict
        else ((1.0 if evidence else 0.9) if passed else 0.2),
        confidence=verdict.get("confidence") if verdict else None, learner_answer=evidence,
        feedback=verdict.get("feedback", "") if verdict else "", attempt_count=1,
        session_id=session_id, turn_id=turn_id)
    progress.learning_evidence.append(ev)
    kt = progress.knowledge_types.get(kp_id)
    if kt is not None and scheduler is not None:
        state = progress.repetition_states.get(kp_id) or scheduler.get_initial_state(
            kt, now=ev.timestamp, desired_retention=progress.desired_retention)
        progress.repetition_states[kp_id] = state
        scheduler.schedule_review(state, kt, ev, now=ev.timestamp)
        progress.review_queue = scheduler.build_review_queue(progress, now=now)
    progress.updated_at = moment
    return True


record_qualitative = record_qualitative_in_memory


def record_qualitative_for_path(progress, kp_id, **kw) -> bool:
    kp, _, _ = find_knowledge_point(progress, kp_id)
    if kp is None:
        raise MasteryInteractionError(f"Unknown objective {kp_id!r}")
    if kp.type not in QUALITATIVE_TYPES:
        raise MasteryInteractionError(f"{kp.name!r} is not a concept/design objective")
    return record_qualitative_in_memory(progress, kp_id, **kw)


def set_learner_mastery_override(progress, kp_id, *, mastered, note="", now=None) -> None:
    kp, _, _ = find_knowledge_point(progress, kp_id)
    if kp is None:
        raise MasteryInteractionError(f"Unknown objective {kp_id!r}")
    if mastered:
        progress.learner_mastery_overrides[kp_id] = LearnerMasteryOverride(
            knowledge_point_id=kp_id, note=str(note or "").strip()[:500],
            **({} if now is None else {"created_at": now}))
        progress.deferred_objectives.pop(kp_id, None)
    else:
        progress.learner_mastery_overrides.pop(kp_id, None)


def defer_objective(tx, kp_id="", *, note="", now=None) -> dict:
    progress = tx.progress
    target = str(kp_id or "").strip()
    if not target:
        target = (progress.pending_question.knowledge_point_id if progress.pending_question
                  else next_objective(progress, now=now).knowledge_point_id)
    kp, _, _ = find_knowledge_point(progress, target)
    if kp is None:
        raise MasteryInteractionError(f"Unknown objective {target!r}")
    if is_mastered(progress, kp):
        raise MasteryInteractionError(f"{kp.name!r} is already mastered, so there is nothing to defer")
    abandoned = False
    if progress.pending_question is not None and progress.pending_question.knowledge_point_id == target:
        progress.pending_question = None
        abandoned = True
    active = tx.active_interaction()
    if active is not None and active.question.knowledge_point_id == target:
        tx.abandon_active_interactions()
        abandoned = True
    progress.deferred_objectives[target] = DeferredObjective(
        knowledge_point_id=target, note=str(note or "").strip()[:500],
        **({} if now is None else {"created_at": now}))
    return {"knowledge_point_id": target, "abandoned_question": abandoned}


def recompute_objective_state(progress, kp_id, scheduler, *, now=None) -> None:
    if not kp_id:
        return
    update_mastery(progress, kp_id, calculate_mastery(progress, kp_id))
    if scheduler is None:
        return
    kt = progress.knowledge_types.get(kp_id)
    attempts = [a for a in progress.quiz_attempts if a.knowledge_point_id == kp_id and not a.voided]
    events = [e for e in progress.learning_evidence if e.knowledge_point_id == kp_id]
    if kt is None or (not attempts and not events):
        progress.repetition_states.pop(kp_id, None)
    elif events:
        progress.repetition_states[kp_id] = scheduler.replay(
            kt, events, desired_retention=progress.desired_retention)
    else:
        synth = [LearningEvidence(question_id=a.question_id, knowledge_point_id=kp_id,
                                  timestamp=a.timestamp, assessment_type="quiz",
                                  result="correct" if a.is_correct else "incorrect",
                                  quality=1.0 if a.is_correct else 0.0, attempt_count=i)
                 for i, a in enumerate(sorted(attempts, key=lambda a: a.timestamp), start=1)]
        progress.repetition_states[kp_id] = scheduler.replay(
            kt, synth, desired_retention=progress.desired_retention)
    progress.review_queue = scheduler.build_review_queue(progress, now=now)


def replace_modules(progress, modules) -> None:
    ids = {kp.id for m in modules for kp in m.knowledge_points}
    for name in ("mastery_levels", "knowledge_types", "qualitative_mastery", "repetition_states",
                 "learner_mastery_overrides", "deferred_objectives", "explained_objectives",
                 "feynman_retries", "feynman_explanations"):
        d = getattr(progress, name)
        for k in [k for k in d if k not in ids]:
            del d[k]
    progress.error_records = [r for r in progress.error_records if r.knowledge_point_id in ids]
    progress.quiz_attempts = [a for a in progress.quiz_attempts if a.knowledge_point_id in ids]
    progress.learning_evidence = [e for e in progress.learning_evidence
                                  if e.knowledge_point_id in ids]
    progress.review_queue = [t for t in progress.review_queue if t.knowledge_point_id in ids]
    progress.stage_failure_counts = {}
    progress.stage_failure_notes = {}
    progress.modules = list(modules)
    for m in modules:
        for kp in m.knowledge_points:
            progress.knowledge_types[kp.id] = kp.type


# ---------------------------------------------------------------- memory store + interactions (R-16, R-17, R-22)
class Tx:
    def __init__(self, progress, interactions):
        self.progress = progress
        self.interactions = interactions  # id -> MasteryInteraction (insertion order)

    def active_interaction(self):
        # ponytail: "active" = most recently inserted interaction with an active status
        act = [i for i in self.interactions.values() if i.status in ACTIVE_STATUSES]
        return act[-1] if act else None

    def get_interaction(self, iid):
        return self.interactions.get(iid)

    def put_interaction(self, i):
        self.interactions[i.interaction_id] = i

    def abandon_active_interactions(self):
        for i in self.interactions.values():
            if i.status in ACTIVE_STATUSES:
                i.status = InteractionStatus.ABANDONED


class MemoryStore:
    """Atomic read-modify-write: fn runs on a deep copy; committed only if fn doesn't raise."""

    def __init__(self):
        self._data = {}  # book_id -> (progress, interactions)

    def create(self, progress):
        self._data[progress.book_id] = (copy.deepcopy(progress), {})

    def get(self, book_id):
        return copy.deepcopy(self._data[book_id][0])

    def mutate(self, book_id, fn):
        p, i = self._data[book_id]
        tx = Tx(copy.deepcopy(p), copy.deepcopy(i))
        result = fn(tx)
        self._data[book_id] = (tx.progress, tx.interactions)
        return copy.deepcopy(tx.progress), result

    def register_question(self, book_id, pending, *, pending_action="retain",
                          replace_question_id="", session_id="", turn_id="", now=None):
        """R-22 -> (progress, interaction, created)."""
        if pending_action not in {"retain", "replace"}:
            raise MasteryInteractionError("pending_action must be retain or replace")
        if pending is None:
            raise MasteryInteractionError("A new question contract is required")

        def register(tx):
            active = tx.active_interaction()
            if active is not None and pending_action == "retain":
                return active, False
            if pending_action == "replace" and (
                    active is None or active.interaction_id != replace_question_id):
                raise StaleInteractionError(replace_question_id,
                                            active.interaction_id if active else "")
            kp, _, _ = find_knowledge_point(tx.progress, pending.knowledge_point_id)
            if kp is None:
                raise MasteryInteractionError(
                    f"Unknown objective {pending.knowledge_point_id!r}; refresh mastery_status")
            pending.created_at = time.time() if now is None else now
            if active is not None:
                active.status = InteractionStatus.ABANDONED
            inter = MasteryInteraction(interaction_id=pending.question_id, path_id=book_id,
                                       question=pending, status=InteractionStatus.REGISTERED,
                                       session_id=session_id, turn_id=turn_id)
            tx.progress.pending_question = pending
            tx.progress.deferred_objectives.pop(pending.knowledge_point_id, None)
            tx.put_interaction(inter)
            return inter, True

        # NOTE: original validates pending_action/known-kp inside or before the tx; any raise here
        # leaves state unchanged because mutate commits only on success.
        p, (inter, created) = self.mutate(book_id, register)
        return p, inter, created

    def grade_interaction(self, book_id, question_id, user_answer="", *, verdict=None,
                          scheduler=None, session_id="", turn_id="", self_attribution="",
                          now=None):
        """R-16/R-17 -> receipt dict {result, final, is_correct, replayed, ...}."""
        def grade(tx):
            done = tx.get_interaction(question_id)
            if done is not None and done.status == InteractionStatus.GRADED:
                return {**done.result, "replayed": True}
            active = tx.active_interaction()
            if active is None:
                raise NoPendingInteractionError("No pending question")
            if active.interaction_id != question_id:
                raise StaleInteractionError(question_id, active.interaction_id)
            q = active.question
            if verdict is not None:
                final = verdict["result"] != "ungraded" and verdict.get("confidence", 0) >= 0.8
                res = verdict["result"] if final else "ungraded"
                if not final:
                    active.status = InteractionStatus.ANSWERED
                    return {"result": "ungraded", "final": False, "is_correct": None,
                            "replayed": False}
                v = dict(verdict, result=res)
            else:
                v = None
            correct = apply_grade(
                tx.progress, question_id=q.question_id, knowledge_point_id=q.knowledge_point_id,
                module_id=q.module_id, user_answer=user_answer, expected_answer=q.expected_answer,
                question_type=q.question_type, self_attribution=self_attribution,
                scheduler=scheduler, session_id=session_id, turn_id=turn_id,
                assistance_used=q.assistance_used, verdict=v, now=now)
            r = v["result"] if v else ("correct" if correct else "incorrect")
            receipt = {"result": r, "final": True,
                       "is_correct": True if r == "correct" else False if r == "incorrect" else None,
                       "replayed": False}
            tx.progress.pending_question = None
            active.status = InteractionStatus.GRADED
            active.result = {k: v_ for k, v_ in receipt.items() if k != "replayed"}
            return receipt

        _, r = self.mutate(book_id, grade)
        return r
