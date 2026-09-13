---
title: Stealable Pattern: Learning AI Agent Modules
created: 2026-06-20
updated: 2026-06-20
type: concept
tags: [agent-framework, architecture, workflow, pattern, judgment]
sources:
  - wiki/projects/deeptutor.md
  - deepwiki-ko/DeepTutor/4-intelligent-agent-modules.md
  - deepwiki-ko/DeepTutor/4.1-smart-solver.md
  - deepwiki-ko/DeepTutor/4.2-deep-research.md
  - deepwiki-ko/DeepTutor/4.3-quiz-generation.md
  - deepwiki-ko/DeepTutor/4.4-book-engine.md
  - deepwiki-ko/DeepTutor/4.5-idea-generation-and-co-writer.md
  - deepwiki-ko/DeepTutor/4.6-vision-solver-and-math-animator.md
  - deepwiki-ko/DeepTutor/4.7-visualization-agent.md
  - deepwiki-ko/DeepTutor/4.9-mastery-path-learning-engine.md
  - repos/DeepTutor/deeptutor/agents/research/pipeline.py
  - repos/DeepTutor/deeptutor/agents/question/pipeline.py
  - repos/DeepTutor/deeptutor/book/models.py
  - repos/DeepTutor/deeptutor/agents/visualize/utils.py
  - repos/DeepTutor/deeptutor/agents/math_animator/renderer.py
  - repos/DeepTutor/deeptutor/learning/policy.py
confidence: high
---

# Stealable Pattern: Learning AI Agent Modules

This page distills source-verified patterns from [[deeptutor]] into reusable design guidance for building a personal learning AI assistant. The core lesson is: use the LLM for explanation, planning, adaptation, and language; use deterministic code for state, gates, validation, storage, and renderer/tool truth. This complements [[open-source-analysis-judgment-model]] by capturing a concrete architecture taste rather than a one-off project summary.

## Pattern 1: prompt sections as learning context contracts

Do not pass an undifferentiated blob of “context.” DeepTutor repeatedly renders context as named sections:

- Book ideation: `[User Intent]`, `[Notebook Context]`, `[Question Notebook]`, `[Past Conversations]`, `[Knowledge Sources]`.
- Quiz generation: user request, count, allowed types, difficulty, attachments, conversation context, prior quiz history.
- Math animation: user input, history context, output mode, style hint, reference image count.
- Co-Writer: selected Markdown snippet, instruction, edit mode, optional reference material.

For a personal learning assistant, this suggests a stable prompt contract such as: learner goal, current concept, known misconceptions, prior attempts, source anchors, desired output format, and UI constraints. The key is to make each context role explicit so the model can reason about priority and provenance.

## Pattern 2: split explore, plan, generate

DeepTutor rarely asks the model to jump directly from request to final artifact.

- Quiz: Explore evidence and history → Plan question templates → Generate one question per template.
- Book: Ideate proposal → Explore sources → Synthesize spine/concept graph → Compile pages/blocks.
- Research: Rephrase/clarify → Decompose outline → Research topic blocks → Report sections.

For your own system, this means expensive learning outputs should have an inspectable intermediate plan. A tutor can show “I will teach these 5 subskills in this order” before producing a full course, quiz set, or essay feedback.

## Pattern 3: make intermediate representations first-class

Useful IRs in DeepTutor include:

| IR | Why it matters |
|---|---|
| `SolveSession` / `SolveStep` | Separates student-facing reasoning from server-owned step completion. |
| `TopicBlock` / `ToolTrace` | Keeps research evidence, source summaries, and citations attached to subtopics. |
| `QuizTemplate` / `QuizPair` | Lets the system plan pedagogical intent before rendering final questions. |
| `BookProposal` / `Spine` / `Page` / `Block` | Turns a vague learning goal into persistent, navigable learning material. |
| `VisualizationAnalysis` | Routes diagram type before injecting format-specific generation rules. |
| `LearningProgress` / `PendingQuestion` / `ReviewItem` | Keeps mastery and grading state outside the model. |

A learning AI assistant should store these IRs, not just final chat messages. They make regeneration, review, spaced repetition, and UI rendering much easier.

## Pattern 4: use LLM action grammar, but enforce it in code

DeepTutor uses label protocols and tools to make LLM behavior parseable:

- Research block loops: `THINK`, `TOOL`, `APPEND`, `FINISH`.
- Reporting: `OUTLINE`, `INTRO`, `SECTION`, `CONCLUSION`.
- Solver: first call `solve_plan`, complete each step with `solve_finish_step`, replan through `solve_replan`.
- Mastery: first call `mastery_status`, then quiz/grade/assess/build through tools.

The reusable idea is not the exact labels. It is the combination of **model-readable grammar** and **host-side state validation**. The model proposes; code accepts, rejects, repairs, or advances.

## Pattern 5: compress evidence, keep anchors

DeepTutor avoids putting every raw tool result into every downstream prompt:

- Research uses a note/citation sidecar: raw tool result → compact summary + citation id → `ToolTrace`.
- Quiz has a tool summarizer that preserves source IDs, numeric facts, formulas, and page/URL evidence.
- Book Engine stores exploration chunks and reuses relevant chunks per block.
- Smart Solver folds previous step chatter into `_context_checkpoint` summaries.

For a personal tutor, this suggests a two-layer memory: detailed trace for audit/UI, compact source-anchored summary for the next LLM call. This is better than either raw context flooding or source-free summaries.

## Pattern 6: validate locally before asking the LLM to review

DeepTutor's visual modules show a cost-effective loop:

1. Generate artifact.
2. Run deterministic validation or the actual renderer.
3. Repair only when there is a concrete error.
4. Fall back deterministically when repair is not worth it.

Examples:

- SVG/XML, Chart.js JSON, Mermaid first-keyword, and HTML heuristics are checked locally.
- Manim code is rendered with a subprocess; renderer failure is the repair signal.
- Vision Solver repairs only when no usable GeoGebra command exists.

For a learning assistant, use this for generated quizzes, flashcards, diagrams, code examples, SQL, math notation, and spaced repetition schedules: never rely on “the model says it is valid” when a cheap validator exists.

## Pattern 7: separate tutoring voice from mastery truth

Mastery Path is the strongest educational architecture pattern in DeepTutor:

- LLM: explains, asks, adapts, judges qualitative concept/design explanations when appropriate.
- Deterministic engine: stores expected answer, grades simple answers, computes mastery, schedules review, decides next objective.

For your own learning AI, avoid letting the model unilaterally declare “you mastered this.” Store attempts, use recency-weighted scores, cap confidence when evidence is sparse, and make review schedules type-specific.

## Pattern 8: stream item/block progress

Long educational generation should be incremental:

- Quiz emits each finished question as an event.
- Book compilation emits block-ready events and persists blocks as they complete.
- Research emits stage and section progress.
- Math Animator emits analysis, generation, render/retry, summary, and artifact events.

This supports better UX and failure recovery: the learner sees progress, and partial artifacts can still be useful.

## Minimal blueprint for a personal learning AI

A small but DeepTutor-inspired version could start with these components:

1. `LearningContext`: learner goal, current topic, source anchors, prior attempts, weak spots, selected notes.
2. `TutorPlanner`: Explore → Plan → Generate for lessons, quizzes, and study plans.
3. `MasteryEngine`: deterministic `PendingQuestion`, grading rules, mastery score, spaced repetition queue.
4. `EvidenceStore`: raw source trace plus compact citation summaries.
5. `ArtifactValidators`: JSON schema, markdown rules, diagram/render validators, code execution tests where safe.
6. `StreamProtocol`: stage, content, tool call/result, item-ready, final result.

The most important design taste is to keep the LLM as a high-quality pedagogical interface, not as the database, scheduler, grader, and validator all at once.

## Related

- [[deeptutor]]
- [[evidence-backed-analysis]]
- [[llm-wiki-operating-model]]
