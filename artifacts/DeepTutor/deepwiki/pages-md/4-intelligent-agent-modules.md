# Intelligent Agent Modules

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [README.md](README.md)
- [assets/README/README_AR.md](assets/README/README_AR.md)
- [assets/README/README_CN.md](assets/README/README_CN.md)
- [assets/README/README_ES.md](assets/README/README_ES.md)
- [assets/README/README_FR.md](assets/README/README_FR.md)
- [assets/README/README_HI.md](assets/README/README_HI.md)
- [assets/README/README_JA.md](assets/README/README_JA.md)
- [assets/README/README_PL.md](assets/README/README_PL.md)
- [assets/README/README_PT.md](assets/README/README_PT.md)
- [assets/README/README_RU.md](assets/README/README_RU.md)
- [assets/README/README_TH.md](assets/README/README_TH.md)
- [deeptutor/capabilities/_answer_now.py](deeptutor/capabilities/_answer_now.py)
- [deeptutor/capabilities/deep_research.py](deeptutor/capabilities/deep_research.py)
- [deeptutor/capabilities/deep_solve.py](deeptutor/capabilities/deep_solve.py)
- [deeptutor/capabilities/math_animator.py](deeptutor/capabilities/math_animator.py)
- [tests/capabilities/__init__.py](tests/capabilities/__init__.py)

</details>



This document provides a high-level overview of the specialized intelligent agent modules that form the core of DeepTutor's AI-powered educational capabilities. DeepTutor utilizes an **agent-native architecture** built around a two-layer plugin model (Tools + Capabilities) with multiple entry points including CLI, WebSocket API, and Python SDK [README.md:104-104]().

For details on the underlying runtime, see [Runtime and Orchestration](#3.4). For information about the LLM service abstraction, see [LLM Service and Provider Factory](#5.1).

---

## Module Overview

DeepTutor implements nine primary agent capabilities, each designed for a specific educational workflow. These modules are integrated into a unified workspace via the `ChatOrchestrator` and follow the `BaseCapability` protocol [deeptutor/core/capability_protocol.py:31-31]().

| Module | Core Capability Name | Key Classes / Agents | Purpose |
| :--- | :--- | :--- | :--- |
| **Auto Mode** | `auto` | `AutoPipeline` | Three-stage router (Analyze -> Delegate -> Synthesize) [deeptutor/capabilities/_answer_now.py:19-21]() |
| **Smart Solver** | `deep_solve` | `SolvePipeline` | Multi-agent problem solving (Plan -> ReAct -> Write) [deeptutor/capabilities/deep_solve.py:18-24]() |
| **Deep Research** | `deep_research` | `ResearchPipeline` | Multi-agent research with iterative reporting [deeptutor/capabilities/deep_research.py:38-45]() |
| **Quiz Generation** | `deep_question` | `AgentCoordinator` | Ideation-to-validation quiz lifecycle [deeptutor/capabilities/deep_question.py:1-7]() |
| **Book Engine** | `book_engine` | `BookCompiler` | Multi-agent "living book" compiler with 14 block types [README.md:82-82]() |
| **Idea & Co-Writer** | `co_writer` | `IdeaAgent` | Collaborative Markdown editing and ideation [README.md:120-120]() |
| **Vision & Math** | `math_animator` | `MathAnimatorPipeline` | Visual concept analysis and Manim animation [deeptutor/capabilities/math_animator.py:20-30]() |
| **Visualization** | `visualize` | `VisualizePipeline` | Data visualization (SVG, Chart.js, Mermaid, HTML) [deeptutor/capabilities/visualize.py:48-58]() |
| **Mastery Path** | `mastery_path` | `LearningService` | Spaced repetition and guided learning engine [README.md:47-47]() |

**Sources:** [deeptutor/capabilities/deep_solve.py:18-24](), [deeptutor/capabilities/deep_research.py:37-45](), [deeptutor/capabilities/visualize.py:47-59](), [deeptutor/capabilities/math_animator.py:19-39]()

---

## Core Architecture Patterns

### Unified Context and Capability Protocol
All agent modules implement the `BaseCapability` protocol. They receive a `UnifiedContext` [deeptutor/core/context.py:62-62]() containing user messages, session metadata, knowledge bases, and enabled tools [deeptutor/capabilities/deep_research.py:47-51]().

**Diagram: Agent to Code Entity Mapping**
```mermaid
graph TB
    subgraph "Natural_Language_Space"
        ["Agent_Identity"]
        ["System_Prompt"]
        ["Tool_Usage"]
        ["Capability_Stages"]
    end

    subgraph "Code_Entity_Space"
        ["BaseCapability"] --> ["UnifiedContext"]
        ["BaseCapability"] --> ["CapabilityManifest"]
        ["CapabilityManifest"] --> ["stages"]
        ["ToolRegistry"] --> ["get_tool_registry"]
        ["AgenticChatPipeline"] --> ["run_agentic_loop"]
    end

    ["Agent_Identity"] -.-> ["BaseCapability"]
    ["System_Prompt"] -.-> ["PromptManager"]
    ["Tool_Usage"] -.-> ["ToolRegistry"]
    ["Capability_Stages"] -.-> ["CapabilityManifest"]
```
**Sources:** [deeptutor/core/capability_protocol.py:31-31](), [deeptutor/core/context.py:62-62](), [deeptutor/capabilities/deep_research.py:38-45]()

### Streaming and Event Bus
Agent modules communicate with the frontend via the `StreamBus` [deeptutor/core/stream_bus.py:33-33](). This allows for real-time updates of "thinking" processes, tool observations, and stage transitions [deeptutor/capabilities/deep_research.py:47-47]().

**Diagram: Stream Event Flow**
```mermaid
graph LR
    subgraph "Agent_Pipeline"
        ["BaseCapability"] -- "stream.stage" --> ["StreamBus"]
        ["BaseCapability"] -- "stream.thinking" --> ["StreamBus"]
        ["BaseCapability"] -- "stream.progress" --> ["StreamBus"]
        ["BaseCapability"] -- "stream.result" --> ["StreamBus"]
    end

    subgraph "Communication_Layer"
        ["StreamBus"] -- "AsyncIterator" --> ["DeepTutorApp"]
        ["DeepTutorApp"] -- "StreamEvent" --> ["UnifiedWebSocket"]
    end
```
**Sources:** [deeptutor/capabilities/deep_research.py:96-99](), [deeptutor/core/stream_bus.py:33-33]()

---

## Module Summaries

### Auto Mode
Auto Mode serves as the intelligent router for the system. It uses a three-stage `AutoPipeline` (ANALYZING, DELEGATING, SYNTHESIZING) to determine which specialized capability should handle a user request [deeptutor/capabilities/_answer_now.py:19-21]().
*   **For details, see [Auto Mode](#4.8).**

### Smart Solver
The Smart Solver uses a multi-agent pipeline: **Plan -> ReAct -> Write**. It bridges internal LLM reasoning with external tools like RAG and code execution to solve complex problems [deeptutor/capabilities/deep_solve.py:1-6]().
*   **Key Component:** `SolvePipeline` orchestrates the solver lifecycle [deeptutor/capabilities/deep_solve.py:18-24]().
*   **For details, see [Smart Solver](#4.1).**

**Sources:** [deeptutor/capabilities/deep_solve.py:11-26]()

### Deep Research
A multi-agent pipeline that decomposes complex queries into sub-topics. It performs iterative searching, note-taking, and report generation using tools like `web_search` and `paper_search` [deeptutor/capabilities/deep_research.py:1-7]().
*   **Key Component:** `ResearchPipeline` handles the multi-agent orchestration including a two-stage outline-preview flow [deeptutor/capabilities/deep_research.py:58-61]().
*   **For details, see [Deep Research](#4.2).**

**Sources:** [deeptutor/capabilities/deep_research.py:37-45]()

### Quiz Generation
Automates the creation of high-quality educational content. It moves from high-level "ideation" to "generation" and validation [deeptutor/capabilities/deep_question.py:1-7]().
*   **Key Component:** `AgentCoordinator` manages the generation lifecycle and question bank integration [deeptutor/capabilities/deep_question.py:1-7]().
*   **For details, see [Quiz Generation](#4.3).**

### Book Engine
The Book Engine is a multi-agent "living book" compiler. It generates structured interactive content across 14 block types, including quizzes, flash cards, and animations [README.md:82-82]().
*   **Key Component:** `BookCompiler` orchestrates the compilation queue and block generation [README.md:45-45]().
*   **For details, see [Book Engine](#4.4).**

### Idea Generation and Co-Writer
Provides an AI-assisted environment for collaborative writing. It includes specialized agents for brainstorming and expanding text within a multi-document workspace [README.md:120-120]().
*   **For details, see [Idea Generation and Co-Writer](#4.5).**

### Vision Solver and Math Animator
Focuses on multimodal mathematical education. It leverages `GeoGebra` for geometric analysis and `Manim` for generating animations of mathematical concepts [deeptutor/capabilities/math_animator.py:20-30]().
*   **Key Component:** `MathAnimatorPipeline` handles concept analysis, design, and code generation [deeptutor/capabilities/math_animator.py:20-30]().
*   **For details, see [Vision Solver and Math Animator](#4.6).**

**Sources:** [deeptutor/capabilities/math_animator.py:19-39]()

### Visualization Agent
An agentic pipeline that analyzes data and generates visual representations using `SVG`, `Chart.js`, `Mermaid`, or interactive `HTML` [deeptutor/capabilities/visualize.py:5-9]().
*   **Key Component:** `VisualizePipeline` handles the process: Analyze -> Generate -> Review [deeptutor/capabilities/visualize.py:48-58]().
*   **For details, see [Visualization Agent](#4.7).**

**Sources:** [deeptutor/capabilities/visualize.py:47-59]()

### Mastery Path Learning Engine
A complete learning engine featuring spaced repetition, qualitative grading gates (e.g., Feynman technique), and mastery tracking [README.md:47-47]().
*   **Key Component:** `LearningService` orchestrates the grading pipeline and `SpacedRepetitionScheduler` manages review timing.
*   **For details, see [Mastery Path Learning Engine](#4.9).**
