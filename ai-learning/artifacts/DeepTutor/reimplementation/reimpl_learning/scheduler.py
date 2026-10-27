"""Spaced-repetition scheduler (review-scheduler.md R-01..R-18)."""
from __future__ import annotations

import copy
import math
import os
import time

from .models import KnowledgeType, LearningEvidence, RepetitionState, ReviewTask

K = KnowledgeType
INTERVAL_SEQUENCES = {K.MEMORY: [0, 1, 3, 7, 14, 30, 60], K.CONCEPT: [3, 7, 14, 30],
                      K.PROCEDURE: [3, 7, 14], K.DESIGN: [14, 28]}
_TYPE_PRIORITY = {K.MEMORY: 2, K.CONCEPT: 3, K.PROCEDURE: 4, K.DESIGN: 5}
_TYPE_DIFFICULTY = {K.MEMORY: 0.3, K.CONCEPT: 0.4, K.PROCEDURE: 0.5, K.DESIGN: 0.6}
DEFAULT_DESIRED_RETENTION = 0.9
MIN_DESIRED_RETENTION = 0.7
MAX_DESIRED_RETENTION = 0.99
_MIN_STAB = 0.5
_FAIL_Q = 0.5
_EPS = 1e-6
_SAME_SESSION_DAYS = 0.25
_LABELS = {"deep_question": "Question Bank", "immersive_reading": "Reading", "book": "Book",
           "partner_chat": "Study Partner", "import": "Imported"}


def validate_desired_retention(value) -> float:
    d = float(value)
    if not math.isfinite(d) or not MIN_DESIRED_RETENTION <= d <= MAX_DESIRED_RETENTION:
        raise ValueError(
            f"desired_retention must be between {MIN_DESIRED_RETENTION} and {MAX_DESIRED_RETENTION}")
    return d


def _error_kp_ids(progress) -> set:
    return {r.knowledge_point_id for r in progress.error_records
            if r.status in ("active", "retrying")}


def review_sort_key(task: ReviewTask, *, now: float):
    return (-task.forgetting_risk, -max(0.0, now - task.due_at), task.priority)


def _resolved_quality(ev: LearningEvidence) -> float:
    if ev.quality is not None:
        q = float(ev.quality)
    elif ev.result == "correct":
        q = 1.0
    elif ev.result == "partial":
        q = 0.4
    else:
        q = 0.0
    if ev.quality is None:
        q -= min(0.25, ev.hints_used * 0.08)
        q -= min(0.2, max(0, ev.attempt_count - 1) * 0.05)
    return max(0.0, min(1.0, q))


def _snap_interval_index(intervals, days, max_index) -> int:
    n = min(range(len(intervals)), key=lambda i: abs(float(intervals[i]) - days))
    return max(0, min(n, max_index))


def _format_span(days: float) -> str:
    if days < 1.0 / 24.0:
        return "moments"
    if days < 1:
        h = max(1, int(round(days * 24)))
        return f"{h} hour{'s' if h != 1 else ''}"
    if days < 1.5:
        return "1 day"
    return f"{int(round(days))} days"


class SpacedRepetitionScheduler:
    def __init__(self, *, desired_retention: float = DEFAULT_DESIRED_RETENTION):
        self.DEBUG_MODE = os.environ.get("LEARNING_DEBUG", "").lower() in ("1", "true", "yes")
        self.desired_retention = validate_desired_retention(desired_retention)

    def _unit(self) -> float:
        return 1.0 if self.DEBUG_MODE else 86400.0

    @staticmethod
    def _stability_from_interval(days, r) -> float:
        r = min(max(r, _EPS), 1.0 - _EPS)
        if days <= 0:
            return _MIN_STAB
        return max(_MIN_STAB, days / -math.log(r))

    @staticmethod
    def _interval_from_stability(stability, r) -> float:
        r = min(max(r, _EPS), 1.0 - _EPS)
        return max(_EPS, max(stability, _EPS) * -math.log(r))

    def _scheduled_interval_days(self, state, ktype) -> float:
        # NOTE: review_count==0 + memory special case is not in the spec's R-11/R-16 text;
        # taken from C-03 code.
        if state.review_count == 0 and INTERVAL_SEQUENCES[ktype][0] == 0:
            return 0.0
        d = self._interval_from_stability(state.stability, state.desired_retention)
        if state.scheduled_after_failure:
            d = min(d, max(d * 0.5, _MIN_STAB * 0.2))
        return d

    def hydrate(self, state, ktype):
        if state.stability > 0:
            if state.difficulty <= 0:
                state.difficulty = _TYPE_DIFFICULTY.get(ktype, 0.3)
            return state
        iv = INTERVAL_SEQUENCES[ktype]
        state.interval_index = max(0, min(state.interval_index, len(iv) - 1))
        state.desired_retention = state.desired_retention or DEFAULT_DESIRED_RETENTION
        state.stability = self._stability_from_interval(float(iv[state.interval_index]),
                                                        state.desired_retention)
        state.difficulty = _TYPE_DIFFICULTY.get(ktype, 0.3)
        if state.retrievability <= 0:
            state.retrievability = 1.0
        return state

    def get_initial_state(self, knowledge_type, *, now=None, desired_retention=None):
        ktype = KnowledgeType(knowledge_type)
        first = float(INTERVAL_SEQUENCES[ktype][0])
        moment = time.time() if now is None else now
        desired = (self.desired_retention if desired_retention is None
                   else validate_desired_retention(desired_retention))
        stab = self._stability_from_interval(first, DEFAULT_DESIRED_RETENTION)
        init = first if first == 0 else self._interval_from_stability(stab, desired)
        return RepetitionState(
            interval_index=0, consecutive_correct=0, consecutive_wrong=0,
            next_review_at=moment + init * self._unit(), difficulty=_TYPE_DIFFICULTY[ktype],
            stability=stab, retrievability=1.0, desired_retention=desired, review_count=0,
            lapse_count=0, last_review_at=None, last_scheduled_at=moment,
            scheduled_after_failure=False)

    def schedule_next(self, state, knowledge_type, is_correct):
        ev = LearningEvidence(knowledge_point_id="", assessment_type="review",
                              result="correct" if is_correct else "incorrect",
                              quality=1.0 if is_correct else 0.0)
        return self.schedule_review(state, knowledge_type, ev)

    def schedule_review(self, state, knowledge_type, evidence, *, now=None):
        ktype = KnowledgeType(knowledge_type)
        self.hydrate(state, ktype)
        em = evidence.timestamp if now is None else now
        moment = max(em, state.last_review_at) if state.last_review_at is not None else em
        q = _resolved_quality(evidence)
        iv = INTERVAL_SEQUENCES[ktype]
        prev_stab = max(state.stability, _EPS)
        prev_ret = self.retrievability(state, now=moment)
        elapsed = (max(0.0, moment - state.last_review_at) / self._unit()
                   if state.last_review_at is not None else 0.0)
        window = min(_SAME_SESSION_DAYS,
                     self._interval_from_stability(prev_stab, DEFAULT_DESIRED_RETENTION) * 0.5)
        if state.last_review_at is not None and elapsed < window:
            if q >= _FAIL_Q:
                state.review_count += 1
                state.last_review_at = moment
                state.retrievability = 1.0
                state.consecutive_wrong = 0
                return state
            if state.scheduled_after_failure and (
                    evidence.result == "partial" or evidence.assessment_type == "qualitative"):
                state.review_count += 1
                state.last_review_at = moment
                state.retrievability = max(q, 0.2)
                return state
        spacing = min(elapsed / prev_stab, 4.0)
        state.difficulty = float(min(0.95, max(0.05, state.difficulty
                                 + 0.12 * ((1.0 - q) - state.difficulty)
                                 + 0.08 * (prev_ret - q))))
        if q < _FAIL_Q:
            state.consecutive_wrong += 1
            state.consecutive_correct = 0
            state.lapse_count += 1
            state.stability = max(_MIN_STAB * 0.1, prev_stab * (0.55 - 0.25 * prev_ret)
                                  * (1.0 - 0.25 * state.difficulty))
            state.retrievability = max(q, 0.2)
            if state.consecutive_wrong >= 2:
                state.consecutive_wrong = 0
        else:
            state.consecutive_wrong = 0
            state.consecutive_correct += 1
            effort = 1.0 + (1.0 - prev_ret) * 1.5
            bonus = 1.0 + spacing * 0.15
            learn = 1.35 - 0.6 * state.difficulty
            strength = max(0.0, (q - _FAIL_Q) / (1.0 - _FAIL_Q))
            growth = 1.0 + strength * learn * effort * bonus
            if q >= 0.8 and state.consecutive_correct >= 2:
                growth *= 1.15
            state.stability = max(_MIN_STAB, prev_stab * growth)
            state.retrievability = 1.0
            if state.consecutive_correct >= 2:
                state.consecutive_correct = 0
        state.review_count += 1
        state.last_review_at = moment
        state.last_scheduled_at = moment
        state.scheduled_after_failure = q < _FAIL_Q
        days = self._scheduled_interval_days(state, ktype)
        state.next_review_at = moment + days * self._unit()
        state.interval_index = _snap_interval_index(iv, days, len(iv) - 1)
        return state

    def retrievability(self, state, *, now=None) -> float:
        moment = time.time() if now is None else now
        stab = max(state.stability, _EPS)
        anchor = state.last_review_at if state.last_review_at is not None else state.next_review_at
        el = max(0.0, (moment - anchor) / self._unit())
        return float(min(1.0, max(0.0, math.exp(-el / stab))))

    def forgetting_risk(self, state, progress, kp_id, *, now=None) -> float:
        moment = time.time() if now is None else now
        risk = 1.0 - self.retrievability(state, now=moment)
        if moment > state.next_review_at:
            risk += min((moment - state.next_review_at) / self._unit() / 7.0, 0.25)
        if kp_id in _error_kp_ids(progress):
            risk += 0.2
        if state.lapse_count:
            risk += min(0.1 * state.lapse_count, 0.2)
        return float(min(1.0, max(0.0, risk)))

    def review_reason(self, state, progress, kp_id, *, now=None, latest_evidence=None) -> str:
        moment = time.time() if now is None else now
        unit = self._unit()
        recall = self.retrievability(state, now=moment)
        parts = []
        delta = moment - state.next_review_at
        if delta >= unit:
            parts.append(f"due {_format_span(delta / unit)} ago")
        elif delta >= 0:
            parts.append("due now")
        else:
            parts.append(f"due in {_format_span(-delta / unit)}")
        desired = state.desired_retention or DEFAULT_DESIRED_RETENTION
        if recall + 1e-9 < desired:
            parts.append(f"retrievability {recall:.0%} below {desired:.0%} target")
        else:
            parts.append(f"retrievability {recall:.0%}")
        failures = state.consecutive_wrong + (1 if kp_id in _error_kp_ids(progress) else 0)
        if state.lapse_count:
            parts.append(f"{state.lapse_count} lapse{'s' if state.lapse_count != 1 else ''}")
        elif failures:
            parts.append("recent failure")
        if latest_evidence is not None:
            src = _LABELS.get(latest_evidence.source)
            if src is not None:
                parts.append(f"latest {src} assessment: {latest_evidence.result}")
        return "; ".join(parts) + "."

    def build_review_queue(self, progress, *, now=None):
        moment = time.time() if now is None else now
        err = _error_kp_ids(progress)
        latest = {}
        for ev in progress.learning_evidence:
            latest[ev.knowledge_point_id] = ev
        tasks = []
        for kp_id, state in progress.repetition_states.items():
            ktype = progress.knowledge_types.get(kp_id, KnowledgeType.MEMORY)
            self.hydrate(state, ktype)
            risk = self.forgetting_risk(state, progress, kp_id, now=moment)
            ev = latest.get(kp_id)
            tasks.append(ReviewTask(
                id=f"review_{kp_id}", knowledge_point_id=kp_id, knowledge_type=ktype,
                due_at=state.next_review_at,
                priority=1 if kp_id in err else _TYPE_PRIORITY[ktype], state=state,
                forgetting_risk=round(risk, 4),
                reason=self.review_reason(state, progress, kp_id, now=moment, latest_evidence=ev),
                evidence_source=ev.source if ev is not None else "",
                evidence_id=ev.evidence_id if ev is not None else ""))
        tasks.sort(key=lambda t: review_sort_key(t, now=moment))
        return tasks

    def get_due_tasks(self, progress, max_tasks=5):
        moment = time.time()
        due = [t for t in self.build_review_queue(progress, now=moment) if t.due_at <= moment]
        return due[:max_tasks]

    def set_desired_retention(self, progress, desired_retention, *, now=None):
        desired = validate_desired_retention(desired_retention)
        moment = time.time() if now is None else now
        for kp_id, state in progress.repetition_states.items():
            ktype = progress.knowledge_types.get(kp_id, KnowledgeType.MEMORY)
            self.hydrate(state, ktype)
            old = validate_desired_retention(state.desired_retention)
            anchor = state.last_scheduled_at
            state.desired_retention = desired
            if anchor is not None:
                days = self._scheduled_interval_days(state, ktype)
                state.next_review_at = anchor + days * self._unit()
                days = (state.next_review_at - anchor) / self._unit()
                iv = INTERVAL_SEQUENCES[ktype]
                state.interval_index = _snap_interval_index(iv, days, len(iv) - 1)
            elif state.last_review_at is not None:
                ratio = -math.log(desired) / -math.log(old)
                state.next_review_at = (state.last_review_at
                                        + (state.next_review_at - state.last_review_at) * ratio)
            elif state.next_review_at > moment:
                ratio = -math.log(desired) / -math.log(old)
                state.next_review_at = moment + (state.next_review_at - moment) * ratio
        progress.desired_retention = desired
        progress.review_queue = self.build_review_queue(progress, now=moment)

    def replay(self, knowledge_type, evidence, *, now=None, desired_retention=None,
               initial_state=None):
        ktype = KnowledgeType(knowledge_type)
        if initial_state is not None:
            if desired_retention is not None:
                raise ValueError("initial_state already contains desired_retention")
            state = copy.deepcopy(initial_state)
        elif not evidence:
            return self.get_initial_state(ktype, now=now, desired_retention=desired_retention)
        else:
            state = self.get_initial_state(ktype, now=evidence[0].timestamp,
                                           desired_retention=desired_retention)
        for ev in evidence:
            self.schedule_review(state, ktype, ev, now=ev.timestamp)
        return state
