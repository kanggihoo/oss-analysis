"""Plain-dataclass state objects. Field names follow the specs' section 1.3."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

_KT_LEGACY = {"记忆型": "memory", "概念型": "concept", "程序型": "procedure", "设计型": "design"}
_ET_LEGACY = {"知识结构性": "structural", "理解偏差型": "deviation",
              "应用错误": "application", "元认知型": "metacognitive"}


class KnowledgeType(str, Enum):
    MEMORY = "memory"
    CONCEPT = "concept"
    PROCEDURE = "procedure"
    DESIGN = "design"

    @classmethod
    def _missing_(cls, value):
        m = _KT_LEGACY.get(str(value))
        return cls(m) if m else None


class ErrorType(str, Enum):
    KNOWLEDGE_STRUCTURAL = "structural"
    UNDERSTANDING_DEVIATION = "deviation"
    APPLICATION_ERROR = "application"
    METACOGNITIVE = "metacognitive"

    @classmethod
    def _missing_(cls, value):
        m = _ET_LEGACY.get(str(value))
        return cls(m) if m else None


class MasteryInteractionError(Exception):
    pass


class NoPendingInteractionError(MasteryInteractionError):
    # ponytail: subclass relation is my guess; spec lists three separate names
    pass


class StaleInteractionError(MasteryInteractionError):
    pass


class ObjectiveRelationError(ValueError):
    pass


@dataclass(kw_only=True)
class KnowledgePoint:
    id: str
    name: str
    type: KnowledgeType
    module_id: str
    prerequisite_ids: list = field(default_factory=list)
    topic_source_ids: list = field(default_factory=list)
    required_visual_tasks: list = field(default_factory=list)

    def __post_init__(self):
        self.type = KnowledgeType(self.type)


@dataclass(kw_only=True)
class LearningModule:
    id: str
    name: str
    order: int
    pass_threshold: float = 0.7
    objective: str = ""
    knowledge_points: list = field(default_factory=list)


@dataclass(kw_only=True)
class QuizAttempt:
    question_id: str
    knowledge_point_id: str
    module_id: str = ""
    is_correct: bool
    result: str | None = None
    user_answer: Any = None
    error_type: ErrorType | None = None
    self_attribution: str = ""
    mastery_estimate: float = 0.0
    timestamp: float = field(default_factory=time.time)
    voided: bool = False
    void_reason: str = ""
    independent: bool = True
    visual_context: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.result is None:
            self.result = "correct" if self.is_correct else "incorrect"
        if self.error_type is not None:
            self.error_type = ErrorType(self.error_type)


@dataclass(kw_only=True)
class RetryAttempt:
    timestamp: float
    is_correct: bool
    attempt_number: int


@dataclass(kw_only=True)
class ErrorRecord:
    id: str
    question_id: str
    knowledge_point_id: str
    module_id: str
    error_type: ErrorType
    self_attribution: str = ""
    ai_confirmation: str = ""
    retry_history: list = field(default_factory=list)
    status: str = "active"  # active | retrying | review | graduated
    created_at: float = field(default_factory=time.time)


@dataclass(kw_only=True)
class LearningEvidence:
    evidence_id: str = ""
    question_id: str = ""
    knowledge_point_id: str
    timestamp: float = field(default_factory=time.time)
    source: str = "mastery_path"
    assessment_type: str = "quiz"  # quiz | qualitative | review
    result: str = "incorrect"  # correct | incorrect | partial
    quality: float | None = None
    hints_used: int = 0
    attempt_count: int = 1
    confidence: float | None = None
    learner_answer: str = ""
    feedback: str = ""
    response_time: float | None = None
    session_id: str = ""
    turn_id: str = ""
    visual_context: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class RepetitionState:
    interval_index: int = 0
    consecutive_correct: int = 0
    consecutive_wrong: int = 0
    next_review_at: float
    difficulty: float = 0.3
    stability: float = 0.0
    retrievability: float = 1.0
    desired_retention: float = 0.9
    review_count: int = 0
    lapse_count: int = 0
    last_review_at: float | None = None
    last_scheduled_at: float | None = None
    scheduled_after_failure: bool = False


@dataclass(kw_only=True)
class ReviewTask:
    id: str
    knowledge_point_id: str
    knowledge_type: KnowledgeType
    due_at: float
    priority: int
    state: RepetitionState
    forgetting_risk: float = 0.0
    reason: str = ""
    evidence_source: str = ""
    evidence_id: str = ""


@dataclass(kw_only=True)
class PendingQuestion:
    # ponytail: groups (questions=[...]), options, visual/source fields are out of scope
    question_id: str
    knowledge_point_id: str
    module_id: str = ""
    prompt: str = ""
    question_type: str = "short"
    expected_answer: str = ""
    options: list = field(default_factory=list)
    explanation: str = ""
    difficulty: str = ""
    assistance_used: bool = False
    created_at: float = field(default_factory=time.time)
    accepted_answers: list = field(default_factory=list)


@dataclass(kw_only=True)
class LearnerMasteryOverride:
    knowledge_point_id: str
    note: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass(kw_only=True)
class DeferredObjective:
    knowledge_point_id: str
    note: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass(kw_only=True)
class LearnerProfile:
    teaching_strategy: str = "probe_first"  # probe_first | teach_first
    prior_knowledge: str = ""
    target_level: str = ""
    time_budget: str = ""
    preferences: str = ""
    notes: str = ""


class InteractionStatus(str, Enum):
    REGISTERED = "registered"
    AWAITING_INPUT = "awaiting_input"
    ANSWERED = "answered"
    GRADED = "graded"
    ABANDONED = "abandoned"


ACTIVE_STATUSES = {InteractionStatus.REGISTERED, InteractionStatus.AWAITING_INPUT,
                   InteractionStatus.ANSWERED}


@dataclass(kw_only=True)
class MasteryInteraction:
    interaction_id: str
    path_id: str
    question: PendingQuestion
    status: InteractionStatus = InteractionStatus.REGISTERED
    session_id: str = ""
    turn_id: str = ""
    result: dict | None = None


@dataclass(kw_only=True)
class LearningProgress:
    book_id: str
    learner_profile: LearnerProfile | None = None
    name: str = ""
    modules: list = field(default_factory=list)
    mastery_levels: dict = field(default_factory=dict)
    qualitative_mastery: dict = field(default_factory=dict)
    knowledge_types: dict = field(default_factory=dict)
    quiz_attempts: list = field(default_factory=list)
    error_records: list = field(default_factory=list)
    learning_evidence: list = field(default_factory=list)
    desired_retention: float = 0.9
    repetition_states: dict = field(default_factory=dict)
    review_queue: list = field(default_factory=list)
    learner_mastery_overrides: dict = field(default_factory=dict)
    deferred_objectives: dict = field(default_factory=dict)
    explained_objectives: dict = field(default_factory=dict)
    pending_question: PendingQuestion | None = None
    feynman_retries: dict = field(default_factory=dict)
    feynman_explanations: dict = field(default_factory=dict)
    stage_failure_counts: dict = field(default_factory=dict)
    stage_failure_notes: dict = field(default_factory=dict)
    version: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self):
        d = float(self.desired_retention)
        if not math.isfinite(d) or not 0.7 <= d <= 0.99:
            raise ValueError("desired_retention must be between 0.7 and 0.99")
