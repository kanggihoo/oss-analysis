---
type: deepwiki-translation
repo: DeepTutor
source: artifacts/DeepTutor/deepwiki/pages-md/4-intelligent-agent-modules.md
deepwiki_url: https://deepwiki.com/HKUDS/DeepTutor/4-intelligent-agent-modules
section: "4"
order: 9
---

# 지능형 에이전트 모듈

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성할 때 참고한 컨텍스트로 사용되었습니다:

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



이 문서는 DeepTutor의 AI 기반 교육 기능의 핵심을 이루는 특화된 지능형 에이전트 모듈에 대한 고수준 개요를 제공합니다. DeepTutor는 CLI, WebSocket API, Python SDK를 포함한 여러 진입점을 갖춘 **agent-native 아키텍처**를 사용하며, 두 계층 플러그인 모델(Tools + Capabilities)을 기반으로 합니다 [README.md:104-104]().

기본 런타임에 대한 자세한 내용은 [Runtime and Orchestration](#3.4)를 참고하세요. LLM 서비스 추상화에 대한 정보는 [LLM Service and Provider Factory](#5.1)를 참고하세요.

---

## 모듈 개요

DeepTutor는 각기 특정 교육 워크플로를 위해 설계된 아홉 개의 주요 에이전트 기능을 구현합니다. 이 모듈들은 `ChatOrchestrator`를 통해 통합 작업공간에 연결되며 `BaseCapability` 프로토콜을 따릅니다 [deeptutor/core/capability_protocol.py:31-31]().

| 모듈 | 핵심 기능 이름 | 주요 클래스 / 에이전트 | 목적 |
| :--- | :--- | :--- | :--- |
| **Auto Mode** | `auto` | `AutoPipeline` | 3단계 라우터(Analyze -> Delegate -> Synthesize) [deeptutor/capabilities/_answer_now.py:19-21]() |
| **Smart Solver** | `deep_solve` | `SolvePipeline` | 다중 에이전트 문제 해결(Plan -> ReAct -> Write) [deeptutor/capabilities/deep_solve.py:18-24]() |
| **Deep Research** | `deep_research` | `ResearchPipeline` | 반복 보고를 포함한 다중 에이전트 조사 [deeptutor/capabilities/deep_research.py:38-45]() |
| **Quiz Generation** | `deep_question` | `AgentCoordinator` | 아이디어 구상부터 검증까지의 퀴즈 생명주기 [deeptutor/capabilities/deep_question.py:1-7]() |
| **Book Engine** | `book_engine` | `BookCompiler` | 14가지 블록 타입을 지원하는 다중 에이전트 "living book" 컴파일러 [README.md:82-82]() |
| **Idea & Co-Writer** | `co_writer` | `IdeaAgent` | 협업 Markdown 편집과 아이디어 구상 [README.md:120-120]() |
| **Vision & Math** | `math_animator` | `MathAnimatorPipeline` | 시각적 개념 분석 및 Manim 애니메이션 [deeptutor/capabilities/math_animator.py:20-30]() |
| **Visualization** | `visualize` | `VisualizePipeline` | 데이터 시각화(SVG, Chart.js, Mermaid, HTML) [deeptutor/capabilities/visualize.py:48-58]() |
| **Mastery Path** | `mastery_path` | `LearningService` | 간격 반복과 안내형 학습 엔진 [README.md:47-47]() |

**Sources:** [deeptutor/capabilities/deep_solve.py:18-24](), [deeptutor/capabilities/deep_research.py:37-45](), [deeptutor/capabilities/visualize.py:47-59](), [deeptutor/capabilities/math_animator.py:19-39]()

---

## 핵심 아키텍처 패턴

### 통합 컨텍스트와 기능 프로토콜
모든 에이전트 모듈은 `BaseCapability` 프로토콜을 구현합니다. 이 모듈들은 사용자 메시지, 세션 메타데이터, 지식 베이스, 활성화된 도구를 담고 있는 `UnifiedContext`를 받습니다 [deeptutor/core/context.py:62-62](), [deeptutor/capabilities/deep_research.py:47-51]().

**다이어그램: 에이전트에서 코드 엔티티로의 매핑**
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

### 스트리밍과 이벤트 버스
에이전트 모듈은 `StreamBus`를 통해 프론트엔드와 통신합니다 [deeptutor/core/stream_bus.py:33-33](). 이를 통해 "thinking" 과정, 도구 관찰, 단계 전환을 실시간으로 업데이트할 수 있습니다 [deeptutor/capabilities/deep_research.py:47-47]().

**다이어그램: 스트림 이벤트 흐름**
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

## 모듈 요약

### Auto Mode
Auto Mode는 시스템의 지능형 라우터 역할을 합니다. 이 모듈은 세 단계의 `AutoPipeline`(ANALYZING, DELEGATING, SYNTHESIZING)을 사용해 사용자 요청을 처리할 특화된 기능을 결정합니다 [deeptutor/capabilities/_answer_now.py:19-21]().
*   **자세한 내용은 [Auto Mode](#4.8)를 참고하세요.**

### Smart Solver
Smart Solver는 **Plan -> ReAct -> Write**의 다중 에이전트 파이프라인을 사용합니다. 이 모듈은 내부 LLM 추론과 RAG 및 코드 실행 같은 외부 도구를 연결해 복잡한 문제를 해결합니다 [deeptutor/capabilities/deep_solve.py:1-6]().
*   **핵심 구성 요소:** `SolvePipeline`이 solver 생명주기를 오케스트레이션합니다 [deeptutor/capabilities/deep_solve.py:18-24]().
*   **자세한 내용은 [Smart Solver](#4.1)를 참고하세요.**

**Sources:** [deeptutor/capabilities/deep_solve.py:11-26]()

### Deep Research
복잡한 질의를 하위 주제로 분해하는 다중 에이전트 파이프라인입니다. `web_search`와 `paper_search` 같은 도구를 사용해 반복 검색, 노트 작성, 보고서 생성을 수행합니다 [deeptutor/capabilities/deep_research.py:1-7]().
*   **핵심 구성 요소:** `ResearchPipeline`은 2단계 개요-미리보기 흐름을 포함한 다중 에이전트 오케스트레이션을 처리합니다 [deeptutor/capabilities/deep_research.py:58-61]().
*   **자세한 내용은 [Deep Research](#4.2)를 참고하세요.**

**Sources:** [deeptutor/capabilities/deep_research.py:37-45]()

### Quiz Generation
고품질 교육 콘텐츠 생성을 자동화합니다. 이 모듈은 고수준 "ideation"에서 "generation"과 검증으로 이동합니다 [deeptutor/capabilities/deep_question.py:1-7]().
*   **핵심 구성 요소:** `AgentCoordinator`는 생성 생명주기와 문제 은행 통합을 관리합니다 [deeptutor/capabilities/deep_question.py:1-7]().
*   **자세한 내용은 [Quiz Generation](#4.3)를 참고하세요.**

### Book Engine
Book Engine은 다중 에이전트 "living book" 컴파일러입니다. 퀴즈, 플래시카드, 애니메이션을 포함한 14가지 블록 유형 전반에 걸쳐 구조화된 대화형 콘텐츠를 생성합니다 [README.md:82-82]().
*   **핵심 구성 요소:** `BookCompiler`가 컴파일 큐와 블록 생성을 오케스트레이션합니다 [README.md:45-45]().
*   **자세한 내용은 [Book Engine](#4.4)를 참고하세요.**

### 아이디어 생성과 Co-Writer
협업 저작을 위한 AI 지원 환경을 제공합니다. 이 모듈은 다중 문서 작업공간 내에서 브레인스토밍과 텍스트 확장을 위한 특화 에이전트를 포함합니다 [README.md:120-120]().
*   **자세한 내용은 [Idea Generation and Co-Writer](#4.5)를 참고하세요.**

### Vision Solver와 Math Animator
멀티모달 수학 교육에 초점을 둡니다. `GeoGebra`를 활용해 기하학적 분석을 수행하고 `Manim`을 사용해 수학 개념의 애니메이션을 생성합니다 [deeptutor/capabilities/math_animator.py:20-30]().
*   **핵심 구성 요소:** `MathAnimatorPipeline`이 개념 분석, 설계, 코드 생성을 처리합니다 [deeptutor/capabilities/math_animator.py:20-30]().
*   **자세한 내용은 [Vision Solver and Math Animator](#4.6)를 참고하세요.**

**Sources:** [deeptutor/capabilities/math_animator.py:19-39]()

### Visualization Agent
데이터를 분석하고 `SVG`, `Chart.js`, `Mermaid`, 또는 대화형 `HTML`을 사용해 시각적 표현을 생성하는 에이전틱 파이프라인입니다 [deeptutor/capabilities/visualize.py:5-9]().
*   **핵심 구성 요소:** `VisualizePipeline`이 Analyze -> Generate -> Review 과정을 처리합니다 [deeptutor/capabilities/visualize.py:48-58]().
*   **자세한 내용은 [Visualization Agent](#4.7)를 참고하세요.**

**Sources:** [deeptutor/capabilities/visualize.py:47-59]()

### Mastery Path 학습 엔진
간격 반복, 정성적 채점 게이트(Feynman 기법 등), 숙달 추적을 갖춘 완전한 학습 엔진입니다 [README.md:47-47]().
*   **핵심 구성 요소:** `LearningService`가 채점 파이프라인을 오케스트레이션하고 `SpacedRepetitionScheduler`가 복습 시점을 관리합니다.
*   **자세한 내용은 [Mastery Path Learning Engine](#4.9)를 참고하세요.**
