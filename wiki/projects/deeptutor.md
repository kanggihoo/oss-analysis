---
title: DeepTutor
created: 2026-06-20
updated: 2026-06-20
type: project
tags: [open-source, project, architecture, agent-framework, workflow, pattern]
sources:
  - deepwiki-ko/DeepTutor/4-intelligent-agent-modules.md
  - deepwiki-ko/DeepTutor/4.1-smart-solver.md
  - deepwiki-ko/DeepTutor/4.2-deep-research.md
  - deepwiki-ko/DeepTutor/4.3-quiz-generation.md
  - deepwiki-ko/DeepTutor/4.4-book-engine.md
  - deepwiki-ko/DeepTutor/4.5-idea-generation-and-co-writer.md
  - deepwiki-ko/DeepTutor/4.6-vision-solver-and-math-animator.md
  - deepwiki-ko/DeepTutor/4.7-visualization-agent.md
  - deepwiki-ko/DeepTutor/4.8-auto-mode.md
  - deepwiki-ko/DeepTutor/4.9-mastery-path-learning-engine.md
  - deepwiki-ko/DeepTutor/4.9.1-learning-models-and-spaced-repetition.md
  - deepwiki-ko/DeepTutor/4.9.2-learning-service-and-grading-pipeline.md
  - repos/DeepTutor/AGENTS.md
  - repos/DeepTutor/deeptutor/runtime/bootstrap/builtin_capabilities.py
  - repos/DeepTutor/deeptutor/core/context.py
  - repos/DeepTutor/deeptutor/core/stream.py
  - repos/DeepTutor/deeptutor/core/stream_bus.py
  - repos/DeepTutor/deeptutor/agents/chat/agentic_pipeline.py
  - repos/DeepTutor/deeptutor/agents/research/pipeline.py
  - repos/DeepTutor/deeptutor/agents/question/pipeline.py
  - repos/DeepTutor/deeptutor/book/engine.py
  - repos/DeepTutor/deeptutor/agents/visualize/capability.py
  - repos/DeepTutor/deeptutor/agents/math_animator/capability.py
  - repos/DeepTutor/deeptutor/capabilities/mastery/tools.py
  - repos/DeepTutor/deeptutor/learning/policy.py
  - repos/DeepTutor/deeptutor/learning/scheduler.py
  - repos/DeepTutor/deeptutor/learning/service.py
confidence: high
---

# DeepTutor

DeepTutor is an agent-native learning companion whose current checkout (`88c2565389dd6b8bdee228b50f8c76d8c990d6b6`) is organized around a shared `UnifiedContext`, capability registry, tool registry, and `StreamBus`. The DeepWiki pages under `deepwiki-ko/DeepTutor/4*` are useful as a module map, but several paths are stale; current source under `repos/DeepTutor/` is the authority, following [[evidence-backed-analysis]] and [[workspace-boundaries]].

## Current capability boundary

The active builtin capability list is `chat`, `deep_solve`, `deep_question`, `deep_research`, `math_animator`, `visualize`, and `mastery_path`; a separate DeepWiki-style `auto` capability is not registered in current source. `ChatOrchestrator` resolves `context.active_capability or "chat"` through the registry, so unknown modes fail instead of being routed by a hidden meta-agent.

Important current-source corrections:

1. **Smart Solver is a chat-loop extension, not a separate solve pipeline.** `DeepSolveCapability` sets `solve_mode` / `solve_session_id` metadata, then runs `AgenticChatPipeline`; `SolveLoopCapability` injects the solve system prompt and server-owned tool kwargs.
2. **Deep Research still has a dedicated pipeline.** It uses Rephrase → Decompose → Research blocks → Reporting, with label protocols such as `THINK`, `TOOL`, `APPEND`, `FINISH`, `OUTLINE`, `SECTION`, and `CONCLUSION`.
3. **Quiz generation is Explore → Plan → Quiz.** The current authority is `deeptutor/agents/question/pipeline.py` and `prompts/en/pipeline.yaml`, not the older `deeptutor/capabilities/deep_question.py` path cited by DeepWiki.
4. **Book Engine is a service-level content compiler.** It creates `BookProposal`, explores sources, synthesizes `Spine` + `ConceptGraph`, then compiles `Page` objects from typed `Block` generators.
5. **Mastery Path uses the chat loop for tutoring and deterministic learning code for gates.** The LLM explains and asks; `learning.policy`, `learning.service`, `learning.scheduler`, and mastery tools decide progress, grading, and review scheduling.

## Prompt and context patterns

DeepTutor repeatedly uses the same architectural seam: LLMs receive explicit prompt sections and domain-specific action grammar, while Python code owns state transitions, validation, persistence, and event streaming.

| Module | Prompt/context pattern | Structured intermediate representation |
|---|---|---|
| Smart Solver | `system.md` tells the model to first call `solve_plan`, finish each step with `solve_finish_step`, and replan only within budget. Tool kwargs inject `_solve_session_id` server-side. | `SolveSession`, `SolveStep`, `_context_checkpoint` summaries. |
| Deep Research | YAML prompt manager supplies phase-specific label protocols; block loops see tool summaries plus citation IDs instead of unbounded raw results. | `TopicBlock`, `DynamicTopicQueue`, `ToolTrace`, citation registry, final Markdown report. |
| Quiz Generation | Explore prompt gathers evidence/history; Plan prompt emits strict JSON templates; Quiz prompt produces one strict JSON question at a time. | `QuizTemplate`, normalized `QuizPair`, emitted question events. |
| Book Engine | Ideation context renders `[User Intent]`, notebook, question notebook, past conversations, and knowledge sources; source explorer and spine synthesizer use JSON output. | `BookProposal`, `ExplorationReport`, `Spine`, `ConceptGraph`, `Page`, typed `Block`. |
| Co-Writer | Selection edit prompt wraps selected Markdown and asks for only the replacement snippet; optional RAG/Web context is gathered before the edit call. | Document manifest, operation history, direct replacement snippet. |
| Vision / Visualization | Vision Solver uses one multimodal JSON call with GeoGebra syntax rules; Visualization first routes render type, then injects only format-specific rules. | GeoGebra command list; `VisualizationAnalysis`; fenced SVG/Chart.js/Mermaid/HTML result. |
| Math Animator | Analysis/design/code prompts split concept understanding from Manim implementation; render errors feed repair prompts. | Concept brief, design plan, Manim code, render artifact, retry trace. |
| Mastery Path | System prompt requires `mastery_status` first; model builds/asks/assesses through tools but storage keys and expected answers are server-owned. | `LearningProgress`, `PendingQuestion`, `ReviewItem`, quiz attempts, error records. |

## Source-verified module notes

Detailed per-mode runtime, prompt/context, tool, validation, and storage behavior is in [[deeptutor-mode-workflows]]. The reusable personal-learning-agent patterns extracted from those modes are in [[stealable-pattern-learning-ai-agent-modules]].

### Smart Solver

`DeepSolveCapability` sets solve metadata and delegates to the shared `AgenticChatPipeline`; `SolveLoopCapability` mounts solve prompt/tool behavior only when `solve_mode` is active. The important learning pattern is a **deterministic spine**: the model can reason freely, but step IDs, done flags, replan budget, and context checkpoint folding live in server code.

### Deep Research

`ResearchPipeline` is the richest agentic workflow: it can pause for `ask_user`, preview an outline before expensive work, run topic blocks in a dynamic queue, add new blocks with `APPEND`, summarize tool results through a note sidecar, and write the final report section-by-section with citations. This is a strong pattern for long learning tasks where the learner should approve the structure before paying the full research cost.

### Quiz Generation

`QuestionPipeline` separates evidence gathering, educational planning, and item generation. It also includes prior quiz history in the prompt so weak spots and repetition can shape new questions. The useful design is not just “generate questions,” but **make a plan of question intents first**, then generate each question against a template and validate/repair the JSON.

### Book Engine and Co-Writer

The book subsystem turns vague learning intent into a persistent educational artifact. `IdeationContext.render()` makes user intent, notebooks, previous conversations, question notebook, and knowledge sources explicit sections; `SourceExplorer` creates query and coverage state; `SpineSynthesizer` couples chapter structure with a concept graph. Co-Writer is narrower: gather optional RAG/Web context, then ask for a selected Markdown snippet replacement only, which is safer than whole-document rewriting.

### Vision, Visualization, and Math Animator

Visualization code shows a useful cost hierarchy: route first, then validate locally, then repair only if needed. SVG/Chart.js/Mermaid/HTML validation is deterministic; Manim routes into a renderer-backed pipeline where the subprocess exit code and artifacts are the real oracle. Vision Solver similarly uses a single multimodal structured call and repairs only when no usable GeoGebra commands are produced.

### Mastery Path

Mastery Path is the most directly reusable learning engine. It keeps expected answers in `PendingQuestion`, grades through deterministic rules, computes mastery with recency weighting and evidence caps, distinguishes quantitative memory/procedure gates from qualitative concept/design gates, and schedules reviews by knowledge type. The LLM is the tutor interface; the policy engine is the source of truth for advancement.

## Taste Notes

### Responsibility Boundaries

- `UnifiedContext` carries user message, history, tools, knowledge bases, attachments, metadata, memory, persona, and source manifest across capabilities.
- Prompt modules decide interaction grammar and instruction hierarchy; Python services own IDs, budgets, validation, persistence, and stage transitions.
- Shared streaming (`StreamEvent` / `StreamBus`) lets every capability expose stage progress, content, thinking, tool calls, results, errors, and final envelopes in one UI protocol.
- Learning state and progression are deterministic; the LLM never becomes the sole authority for mastery.

### Architecture Decision Taste

1. **Chat-loop extension for guided solving** / alternative: separate solver runtime / why tasteful: reuses tools, streaming, and history while adding a solve-specific deterministic state / trade-off: solve mode inherits chat-loop complexity / evidence: `capabilities/solve/capability.py`, `capabilities/solve/loop.py`, `capabilities/solve/tools.py`.
2. **Label-protocol research loops** / alternative: one giant research prompt / why tasteful: recoverable state machine with `APPEND` and stage-level UI / trade-off: prompt protocol drift must be repaired / evidence: `agents/research/pipeline.py`, `agents/research/prompts/en/pipeline.yaml`.
3. **Intermediate representations for education content** / alternative: direct final prose / why tasteful: plan, validate, stream, store, and regenerate at item/block level / trade-off: many schemas and coercers to maintain / evidence: quiz templates, book spine/page/block models.
4. **Validation oracle before self-review** / alternative: ask the LLM whether its output is good / why tasteful: XML/JSON/Mermaid/Manim failures are concrete and repairable / trade-off: validators must track target renderer syntax / evidence: visualize utils, Manim renderer/retry manager.
5. **Deterministic mastery gate** / alternative: let the tutor decide the learner is ready / why tasteful: reproducible progress, spaced repetition, and grading traces / trade-off: deterministic grading is shallow for open-ended answers / evidence: `learning/policy.py`, `learning/grading.py`, `learning/service.py`.

### Trade-offs / Risks

- DeepWiki path drift is material: `deeptutor/agents/auto/*` and several old `deeptutor/capabilities/deep_*.py` paths are not current authority.
- The architecture has many prompts and schema coercion layers; strong UX depends on keeping prompt files, validators, and frontend viewers synchronized.
- Deterministic grading is safe but limited; concept/design mastery still depends on tutor-mediated qualitative assessment.
- Manim/visualization capabilities depend on environment packages and renderer behavior, so production reliability needs dependency checks and non-retriable error classification.

### Stealable Patterns

- See [[stealable-pattern-learning-ai-agent-modules]] for the reusable learning-AI patterns extracted from DeepTutor.
- Use source verification boundaries from [[evidence-backed-analysis]] whenever DeepWiki describes prompt pipelines or agent modules.
- Reuse the workspace separation in [[workspace-boundaries]]: translated DeepWiki pages are baseline artifacts, while `repos/DeepTutor/` source is authority.

### Comparison Hooks

- Compare with [[Understand-Anything]] on deterministic preprocessing plus LLM semantic judgment: DeepTutor applies the split to learning workflows, while Understand-Anything applies it to graph construction.
- Compare with [[graphify]] on graph/report generation versus DeepTutor's per-capability educational IRs.
