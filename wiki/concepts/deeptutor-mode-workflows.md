---
title: DeepTutor Mode Workflows
created: 2026-06-20
updated: 2026-06-20
type: concept
tags: [agent-framework, architecture, workflow, pattern, open-source]
sources:
  - wiki/projects/deeptutor.md
  - repos/DeepTutor/deeptutor/runtime/bootstrap/builtin_capabilities.py
  - repos/DeepTutor/deeptutor/runtime/orchestrator.py
  - repos/DeepTutor/deeptutor/core/context.py
  - repos/DeepTutor/deeptutor/core/stream.py
  - repos/DeepTutor/deeptutor/core/stream_bus.py
  - repos/DeepTutor/deeptutor/services/session/turn_runtime.py
  - repos/DeepTutor/deeptutor/agents/chat/agentic_pipeline.py
  - repos/DeepTutor/deeptutor/agents/chat/agent_loop.py
  - repos/DeepTutor/deeptutor/capabilities/solve/capability.py
  - repos/DeepTutor/deeptutor/agents/research/pipeline.py
  - repos/DeepTutor/deeptutor/agents/question/pipeline.py
  - repos/DeepTutor/deeptutor/book/engine.py
  - repos/DeepTutor/deeptutor/co_writer/edit_agent.py
  - repos/DeepTutor/deeptutor/agents/visualize/capability.py
  - repos/DeepTutor/deeptutor/agents/math_animator/capability.py
  - repos/DeepTutor/deeptutor/agents/vision_solver/vision_solver_agent.py
  - repos/DeepTutor/deeptutor/capabilities/mastery/tools.py
  - repos/DeepTutor/deeptutor/learning/policy.py
confidence: high
---

# DeepTutor Mode Workflows

This page records how current [[deeptutor]] modes actually run at commit `88c2565389dd6b8bdee228b50f8c76d8c990d6b6`: what owns the mode, what context/prompt goes into the LLM, which tools or validators run, and where results are stored. DeepWiki pages were useful as a map, but current source is the authority.

## Runtime boundary

The true top-level capabilities are registered in `runtime/bootstrap/builtin_capabilities.py:3-11`: `chat`, `deep_solve`, `deep_question`, `deep_research`, `math_animator`, `visualize`, and `mastery_path`. `book`, `co_writer`, and `vision_solver` are real user-facing/service flows, but not `BaseCapability` entries: Book and Co-Writer are REST/WS/SSE services, while Vision Solver is the `geogebra_analysis` tool consumed by chat/solve.

All unified turns go through `ChatOrchestrator.handle()`: it chooses `context.active_capability or "chat"`, creates a `StreamBus`, runs `capability.run(context, bus)`, and yields events (`runtime/orchestrator.py:26-94`). The common `UnifiedContext` carries user message, OpenAI-format history, enabled tools, KB names, attachments, config, language, memory, persona, skills, source manifest, and metadata (`core/context.py:33-84`). `TurnRuntimeManager` builds this context, runs the orchestrator, stores assistant content/events, and mirrors events to SQLite plus workspace `events.jsonl` (`services/session/turn_runtime.py:1613-1722`, `1987-2020`).

## Mode map

| Mode/service | Owner | LLM prompt/context | Tools / validators | Storage / result |
|---|---|---|---|---|
| `chat` | `ChatCapability` → `AgenticChatPipeline` | System blocks from `agentic_chat.yaml` plus conversation history, current user message, KB seed, attachments, persona/memory/skills/source blocks. | Dynamic tool composition: user tools, auto-mounted tools, loop-owned tools, always-on tools. | Streamed as `responding`; final content/result and events saved by turn runtime. |
| `deep_solve` | `DeepSolveCapability` layered on chat | Chat prompt plus solve system block requiring `solve_plan`, `solve_finish_step`, `solve_replan`. | Normal chat tools plus solve-owned tools; server injects `_solve_session_id`. | `SolveSession` in process memory; `_context_checkpoint` folds tool chatter; final turn saved by runtime. |
| `deep_research` | Dedicated `ResearchPipeline` | YAML label protocols for rephrase, decompose, block research, note sidecar, report writing. | `ask_user` in rephrase; `rag`, `web_search`, `paper_search`, `code_execution` in block research; citation sidecar. | Outline preview on first call; citations JSON under task workspace; final report/result saved by runtime. |
| `deep_question` | `QuestionPipeline` | Explore prompt with request/history; Plan prompt emits templates; Quiz prompt emits one strict JSON question. | Dynamic tools similar to chat; mimic mode uses exam extraction templates; JSON normalize/repair. | Per-question events plus final quiz result saved by runtime. |
| `book` | `BookEngine` service | Ideation context sections; source query/summary prompts; spine draft/critique/revise; page/block prompts. | Direct RAG calls, block generators, deterministic overview/page fallbacks. | `data/user/workspace/book/book_<id>/` manifest/spine/pages/progress/log JSON. |
| `co_writer` | REST/SSE `EditAgent` service | Selected/full text, instruction, edit mode, optional RAG/Web reference material. | Direct `rag_search` / `web_search`, no chat ToolRegistry loop. | Co-writer history/tool-call JSON/doc manifests under workspace. |
| `visualize` | `VisualizeCapability` | Analysis prompt routes render type; codegen prompt includes only chosen format rules. | Deterministic SVG/Chart.js/Mermaid/HTML validation; targeted repair; Manim delegation. | Fenced artifact plus structured result in turn events. |
| `math_animator` | `MathAnimatorCapability` | Concept analysis → design → Manim code → repair → summary prompts, with history/style/attachments. | Manim subprocess is validation oracle; retry manager repairs up to budget. | Generated code/media/artifacts under math animator agent dir; result saved by runtime. |
| `geogebra_analysis` / vision | Built-in tool | One multimodal prompt with geometry anti-hallucination and JSON schema. | Command coercion; one repair pass only if no commands. | Tool result metadata inside parent chat/solve turn. |
| `mastery_path` | `MasteryPathCapability` layered on chat | Chat prompt plus mastery system block: call `mastery_status` first, then build/quiz/grade/assess. | Mastery tools plus deterministic learning policy/grading/scheduler. | Learning JSON store plus normal turn events/messages. |

## `chat`: default agent loop

`chat` is registered to `deeptutor.agents.chat.capability:ChatCapability` and exposes manifest stages `exploring/responding`, but current execution is effectively a single `AgentLoop` with stage `responding` (`agents/chat/capability.py:12-27`, `agents/chat/agent_loop.py:46-50`). `AgenticChatPipeline.run()` composes enabled tools, native schemas, multimodal messages, and then runs `AgentLoop` (`agents/chat/agentic_pipeline.py:301-321`).

Prompt assembly loads `agents/chat/prompts/en/agentic_chat.yaml`; `ChatPromptAssembler` builds blocks for general policy, runtime/loop policy, active loop capability, persona, partner policy, memory, tools/KB notes, skills, sources, extended tools, notebooks, and workspace (`agents/chat/prompt_blocks.py:46-93`). Messages are system prompt + previous conversation history + current user message; KB seed is appended to the user message instead of the system prompt to preserve prefix caching (`agents/chat/agentic_pipeline.py:345-386`, `984-1055`).

Tools are selected by `compose_enabled_tools()`: user-toggleable tools such as `brainstorm`, `web_search`, `paper_search`, `reason`, `geogebra_analysis`, `imagegen`, `videogen`; auto-mounts like `rag`, `read_source`, memory, notebook, `exec`, `code_execution`, `load_tools`; loop-owned tools; and always-on helpers such as `ask_user`, `web_fetch`, `github`, `cron` (`tools/builtin/__init__.py:1501-1541`, `agents/_shared/tool_composition.py:95-170`). Each LLM round streams content/thinking, accumulates tool-call deltas, dispatches tools, and marks the round as `narration` or `finish` (`agents/chat/agent_loop.py:455-579`).

## `deep_solve`: solver as chat-loop extension

`deep_solve` is not a bespoke planner/reasoner/writer pipeline in current source. `DeepSolveCapability.run()` sets `context.metadata["solve_mode"] = True`, resolves a turn-scoped solve session id, reads settings such as `max_replans` / `max_rounds`, and invokes the same `AgenticChatPipeline` (`capabilities/solve/capability.py:1-17`, `69-88`).

`SolveLoopCapability` becomes active from `solve_mode`, injects a solve system prompt, and mounts `solve_plan`, `solve_finish_step`, and `solve_replan` (`capabilities/solve/loop.py:21-69`). The English prompt requires the first action to be `solve_plan`, each completed step to be committed with `solve_finish_step`, and replanning only through budgeted `solve_replan` (`capabilities/solve/prompts/en/system.md:1-13`). Server code, not the LLM, injects `_solve_session_id` and enforces replan budget.

The persistent goal of the mode is a deterministic step spine: `SolveSession` and `SolveStep` track plan, done flags, summaries, and replan count in a bounded process-local dict (`capabilities/solve/session.py:1-14`, `79-92`). `solve_finish_step` emits `_context_checkpoint` metadata so the chat loop can fold previous tool chatter into a compact system checkpoint (`capabilities/solve/tools.py:196-203`, `agents/chat/agent_loop.py:327-362`).

## `deep_research`: dedicated label-protocol pipeline

`deep_research` owns a separate `ResearchPipeline` with phases Rephrase → Decompose → Research blocks → Reporting (`agents/research/pipeline.py:1-30`). `DeepResearchCapability.run()` validates config, selects the first KB, and uses a two-call UX: if `confirmed_outline` is absent it runs rephrase/decompose and returns an outline preview; if present it researches and writes the report (`agents/research/capability.py:47-99`, `agents/research/pipeline.py:461-556`).

Prompts come from `agents/research/prompts/en/pipeline.yaml`: protocol labels, protocol repair, rephrase, decompose, block research, note sidecar, and report prompts (`agents/research/pipeline.py:386-397`). Rephrase uses only `ask_user`; decompose is a strict `OUTLINE` JSON step; each block uses `THINK`, `TOOL`, `APPEND`, `FINISH`; reporting uses `OUTLINE`, `INTRO`, `SECTION`, `CONCLUSION` (`agents/research/pipeline.py:589-852`, `1060-1162`).

Research tools are deliberately narrow: `rag`, `web_search`, `paper_search`, `code_execution` are allowed in block research (`agents/research/pipeline.py:96-102`, `1700-1791`). `_BlockLoopHost` dispatches tools, then citable results are summarized by a note agent, assigned citation ids, registered in `CitationManager`, and returned to the model as `[CIT-x-y] summary` instead of raw blobs (`agents/research/pipeline.py:2260-2383`). Citations are persisted to `deep_research/<research_id>/citations.json` through `utils/citation_manager.py:21-35`, `158-172`.

## `deep_question`: custom, mimic, and follow-up paths

`deep_question` is the actual quiz capability; its manifest says `ideation/generation`, but the current pipeline stages are `exploring`, `planning`, and `quizzing` (`agents/question/capability.py:28-36`, `agents/question/pipeline.py:79-89`). Three paths exist. Follow-up mode is metadata-driven: if `question_followup_context.question` exists, `FollowupAgent` answers about an existing question using question/learner answer/correct answer/explanation/knowledge context (`agents/question/capability.py:48-83`, `agents/question/agents/followup_agent.py:26-118`).

Custom mode loads quiz history, builds request config, and runs `QuestionPipeline.run()` (`agents/question/capability.py:85-141`). The Explore prompt receives user request, requested count, allowed question types, per-type counts, difficulty, attachments, conversation context, and prior quiz history (`agents/question/prompts/en/pipeline.yaml:37-120`, `agents/question/pipeline.py:632-652`). The Plan prompt emits strict `PLAN` JSON templates (`pipeline.yaml:149-189`, `agents/question/pipeline.py:690-814`). The Quiz prompt generates one strict JSON question at a time, then parser/normalizer/repair code coerces it into `QuizPair` (`pipeline.yaml:193-260`, `agents/question/pipeline.py:819-956`, `1292-1415`).

Mimic mode parses an uploaded/previous exam into templates and skips Explore/Plan; it runs only quiz generation against `templates_override` (`agents/question/capability.py:158-329`, `agents/question/pipeline.py:511-532`). Tools are dynamically composed like chat, with `rag`, `code_execution`, `reason`, `brainstorm`, `web_search`, `paper_search`, `read_source`, and note-writing kwargs configured as available (`agents/question/pipeline.py:1481-1574`). Each completed question is streamed as a card-like content event, and final payload contains request/analysis/templates/results summary (`agents/question/pipeline.py:1202-1287`).

## `book`: service-level course/book compiler

Book is not a capability; `BookEngine` is a parallel service exposed under `/api/v1/book` REST and `/api/v1/book/ws` (`book/engine.py:1-29`, `api/routers/book.py:198-669`). `create_book` fuses user intent, notebooks, question notebook, past conversations, and knowledge sources via `IdeationContext.render()` and asks `IdeationAgent` for a JSON `BookProposal` (`book/engine.py:200-273`, `book/inputs.py:36-76`, `book/agents/ideation_agent.py:41-67`).

`confirm_proposal` runs `SourceExplorer`: one LLM call designs 4-8 queries, RAG retrieves chunks, and another LLM call synthesizes summary/candidate concepts/notes (`book/engine.py:281-394`, `book/agents/source_explorer.py:181-343`). `SpineSynthesizer` then does draft → critique → revise to produce `Spine` plus concept graph, followed by deterministic coercion/validation (`book/agents/spine_synthesizer.py:1-28`, `114-174`, `249-328`).

`confirm_spine` materializes page shells and starts a compile queue; current source also injects an overview chapter and deterministic overview blocks (`book/engine.py:398-645`, `769-856`). `BookCompiler.compile_page()` optionally uses `SectionArchitect` for a page/block plan, then runs block generators and persists after each block (`book/compiler.py:88-249`, `book/agents/page_planner.py:1-29`, `277-348`). Storage is file-backed under `data/user/workspace/book/book_<book_id>/` with manifest, inputs, exploration, spine, progress, pages, and append-only log JSON (`book/storage.py:1-19`, `112-256`).

## `co_writer`: selection/full-text editing service

Co-Writer is also not a capability. It is a REST/SSE service under `/api/v1/co_writer` with `/edit`, `/edit_react`, `/edit_react/stream`, `/automark`, history/tool-call endpoints, and document CRUD (`api/routers/co_writer.py:379-618`).

`/edit` calls `EditAgent.process(text, instruction, action, source, kb_name)`: if `source` is `rag` or `web`, it gathers reference context first, then builds a prompt from `edit_agent.yaml` with expert-editor system text, action template, optional reference material, and target text (`co_writer/edit_agent.py:122-212`, `co_writer/prompts/en/edit_agent.yaml:1-22`). `/edit_react` and `/edit_react/stream` operate on selected Markdown; `_build_react_edit_prompt()` asks for only the direct replacement snippet, no explanation/prefix/code fences, with optional RAG/Web reference material (`api/routers/co_writer.py:83-171`, `232-377`).

Tools are direct function calls, not ToolRegistry loop calls: RAG calls `rag_search(... only_need_context=True)`, Web calls `web_search` in a thread (`co_writer/edit_agent.py:214-287`). History is capped and stored via `PathService.get_co_writer_history_file()`, tool-call traces are JSON files under `workspace/co-writer/tool_calls/`, and documents live under `workspace/co-writer/documents/doc_<id>/manifest.json` with atomic writes (`co_writer/edit_agent.py:48-91`, `co_writer/storage.py:1-14`, `54-70`, `176-246`).

## `visualize`: route, generate, validate, repair

`visualize` is a capability with render modes `auto`, `svg`, `chartjs`, `mermaid`, `html`, `manim_video`, and `manim_image` (`runtime/request_contracts.py:54-72`, `agents/visualize/capability.py:35-61`). Analysis stage either routes with an LLM or short-circuits for explicit Manim modes; it injects user input, history context, fixed render type when present, and attachments (`agents/visualize/agents/analysis_agent.py:38-93`, `prompts/en/analysis_agent.yaml:1-132`). Code generation then combines shared base rules with only the selected format's rules and asks for fenced output (`agents/visualize/agents/code_generator_agent.py:38-119`, `prompts/en/code_generator_agent.yaml:1-180`).

There is no generic tool surface (`tools_used=[]`). The key “tool” is deterministic validation: SVG XML/root/viewBox, Chart.js strict JSON with `type`/`data`, Mermaid first keyword, and HTML heuristics (`agents/visualize/utils.py:177-231`). Valid outputs ship without repair; invalid HTML gets a deterministic fallback; invalid SVG/Chart/Mermaid gets one targeted `ReviewAgent` repair using the concrete validation error (`agents/visualize/capability.py:146-247`). Manim render types delegate to the Math Animator pipeline (`agents/visualize/capability.py:114-126`, `278-492`). Final output is both a fenced artifact and a structured result with render type, code, analysis, and review metadata (`agents/visualize/capability.py:249-276`).

## `math_animator`: render-backed Manim generation

`math_animator` is a capability with stages `concept_analysis`, `concept_design`, `code_generation`, `code_retry`, `summary`, and `render_output`; it requires the optional `manim` dependency (`agents/math_animator/capability.py:19-47`). Config controls `output_mode`, `quality`, and `style_hint` (`agents/math_animator/request_config.py:10-32`).

The pipeline uses separate agents: concept analysis prompt receives user input, conversation history, output mode, style hint, and image reference count; concept design prompt receives analysis JSON; code generation prompt receives user input, analysis/design JSON, output mode, style, and parsed duration target (`agents/math_animator/agents/concept_analysis_agent.py:39-75`, `concept_design_agent.py:39-67`, `code_generator_agent.py:58-91`). Prompts enforce Manim-specific constraints: video vs image contract, no LaTeX by default, avoid unsupported APIs, pacing/runtime, and repair behavior (`prompts/en/code_generator_agent.yaml:1-95`).

Validation is operational: `ManimRenderService` writes generated code, extracts a `Scene` class for video or image anchor blocks for image mode, runs `python -m manim`, streams stdout/stderr, and checks artifacts (`agents/math_animator/renderer.py:52-94`, `124-220`). `CodeRetryManager` repairs and rerenders up to its retry budget, while non-retriable LaTeX environment errors stop early (`agents/math_animator/retry_manager.py:21-157`). Artifacts are written under the math animator agent directory by turn id, with `source`, `artifacts`, `media`, and `meta` subdirs (`renderer.py:35-50`, `229-243`).

## `geogebra_analysis` / Vision Solver

Vision Solver is not a top-level mode. The chat/solve loop exposes `geogebra_analysis` as a built-in tool; the tool strips image input from the schema shown to the LLM and the pipeline injects the first image attachment server-side (`tools/builtin/__init__.py:460-530`, `agents/chat/agentic_pipeline.py:633-637`, `920-936`). Solve prompt explicitly tells the model to use it for diagram/image geometry (`capabilities/solve/prompts/en/system.md:8`).

`VisionSolverAgent` performs one multimodal LLM call using `prompts/geogebra.md`: it inserts question text, sends `[text, image_url]`, asks for JSON with `image_is_reference`, constraints, geometric relations, and GeoGebra commands, and includes anti-hallucination rules for geometric points plus syntax rules (`agents/vision_solver/vision_solver_agent.py:41-65`, `103-139`, `prompts/geogebra.md:21-85`). It parses tolerant JSON, coerces commands, and runs one repair pass only if no usable commands exist (`vision_solver_agent.py:64-73`, `144-189`). There is no local GeoGebra execution validator in this path; the result is a fenced `ggbscript` block plus metadata stored inside the parent turn (`tools/builtin/__init__.py:532-565`).

## `mastery_path`: chat tutor plus deterministic learning engine

`mastery_path` is another chat-loop extension, not a separate tutor state machine. `MasteryPathCapability` sets `mastery_mode`, resolves a sanitized path id from explicit metadata, book reference, or session id, and calls `AgenticChatPipeline` (`capabilities/mastery/capability.py:1-14`, `29-73`). `MasteryLoopCapability` injects the mastery system block and server-owned `_mastery_path_id` tool kwargs (`capabilities/mastery/loop.py:23-49`).

The prompt requires the tutor to call `mastery_status` first every turn; if there are no objectives, use materials/tools then `mastery_build`; for memory/procedure, ask via `mastery_quiz`, wait for learner, then `mastery_grade`; for concept/design, use explanation plus `mastery_assess` (`capabilities/mastery/prompts/en/system.md:1-14`). Tools are `mastery_status`, `mastery_quiz`, `mastery_grade`, `mastery_assess`, and `mastery_build` (`capabilities/mastery/tools.py:49-57`). `mastery_quiz` stores the expected answer server-side in `PendingQuestion`; `mastery_grade` uses deterministic grading, records the attempt, updates mastery/spaced repetition, clears pending, and returns the next objective (`capabilities/mastery/tools.py:130-294`, `learning/service.py:161-210`).

The learning engine is the durable source of truth. `next_objective()` prioritizes pending questions, due reviews, first non-mastered KP, then completion; memory/procedure use quantitative threshold 0.9, while concept/design use qualitative mastery (`learning/policy.py:31-68`, `158-233`). Mastery score uses recent attempts with evidence caps; scheduler uses type-specific intervals and prioritizes active error records (`learning/mastery.py:15-37`, `learning/scheduler.py:13-101`). State is atomically stored as JSON under the learning workspace with path guards (`learning/storage.py:28-51`).

## Design lesson

DeepTutor's modes differ less by “which LLM” and more by where deterministic responsibility sits. Chat/solve/mastery are the same agent loop with different prompt blocks and owned tools. Research/question/book are staged pipelines with explicit intermediate representations. Visual/math/vision modes use local validators or renderers as truth. Co-Writer is service-scoped editing with direct reference gathering. For a personal learning assistant, the stealable boundary is: LLM for interaction and pedagogical judgment; host code for state, validation, persistence, scheduling, and tool/result provenance.

## Related

- [[deeptutor]]
- [[stealable-pattern-learning-ai-agent-modules]]
- [[evidence-backed-analysis]]
- [[workspace-boundaries]]
