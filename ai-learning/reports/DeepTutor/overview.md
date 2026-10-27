---
sha: "a31d82624c27d75f4e771d4fcb78dce16470b383"
created: 2026-10-25
updated: 2026-10-27
sources:
  - repos/DeepTutor/LICENSE
  - repos/DeepTutor/THIRD_PARTY_NOTICES.md
  - repos/DeepTutor/README.md
  - repos/DeepTutor/AGENTS.md
  - repos/DeepTutor/pyproject.toml
  - repos/DeepTutor/deeptutor/__version__.py
  - repos/DeepTutor/deeptutor/api/main.py
  - repos/DeepTutor/deeptutor/api/routers/unified_ws.py
  - repos/DeepTutor/deeptutor/api/routers/capabilities.py
  - repos/DeepTutor/deeptutor/app/service.py
  - repos/DeepTutor/deeptutor/app/facade.py
  - repos/DeepTutor/deeptutor/app/container.py
  - repos/DeepTutor/deeptutor/runtime/turn_engine.py
  - repos/DeepTutor/deeptutor/runtime/orchestrator.py
  - repos/DeepTutor/deeptutor/runtime/bootstrap/builtin_capabilities.py
  - repos/DeepTutor/deeptutor/capabilities/registry.py
  - repos/DeepTutor/deeptutor/tools/builtin_specs.py
  - repos/DeepTutor/deeptutor/tools/builtin/__init__.py
  - repos/DeepTutor/deeptutor/agents/loop/pipeline.py
  - repos/DeepTutor/deeptutor/agents/loop/agent_loop.py
  - repos/DeepTutor/deeptutor/agents/visualize/capability.py
  - repos/DeepTutor/deeptutor/services/session/turns/request_preparer.py
  - repos/DeepTutor/deeptutor/services/session/turns/executor.py
  - repos/DeepTutor/deeptutor/services/partners/runtime.py
  - repos/DeepTutor/deeptutor/learning/policy.py
  - repos/DeepTutor/deeptutor/learning/scheduler.py
  - repos/DeepTutor/deeptutor/capabilities/mastery/capability.py
  - repos/DeepTutor/deeptutor/services/memory/store.py
  - repos/DeepTutor/deeptutor/services/rag/factory.py
  - repos/DeepTutor/deeptutor/knowledge/kb_types.py
  - repos/DeepTutor/deeptutor/services/provider_registry.py
  - repos/DeepTutor/deeptutor/book/engine.py
  - repos/DeepTutor/deeptutor/reading/ingestion.py
  - repos/DeepTutor/deeptutor_cli/main.py
  - repos/DeepTutor/web/proxy.ts
  - repos/DeepTutor/docs/guides/tools-surface.md
---

# DeepTutor Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/HKUDS/DeepTutor`
- **기준 SHA**: `a31d8262` (커밋 날짜 2026-10-19, `main`), `deeptutor/__version__.py`의 버전 1.6.15. 코드 확인.
- **작업트리 상태**: Clean (`ai-learning/artifacts/DeepTutor/repo-metadata.txt`)
- **분석 목적**: 학습 / 설계 참고 — **Claude Code 같은 에이전트 안에서 쓰는 가벼운 학습 스킬**을 만들기 위한 재료 찾기(2026-10-27 사용자 재정의). 스킬이 할 일: 주제 학습, 학습한 것 추적, 맞춤 자료 수집, 수준별 설명, 지속 관리. 복잡하게 만들지 않는 것이 조건이다. 그래서 2절 "스킬화 관점 지도"를 기능 지도 뒤에 추가했다(제품 전체 지도는 그대로 둔다). (이전 목적: 학습 / 설계 참고 — AI와 함께 배우는 학습 앱의 기능·구조 파악. `ai-learning/GUIDE.md`의 비교 축(① 학습자 상태 ② 수업 진행 ③ 자료 연결 ④ 모델·데이터)에 맞춰 읽되, 이번 세션은 기능 지도와 구조도까지(2026-10-25 사용자 요청).)
- **라이선스** (LICENSE 파일 본문을 직접 읽음):
  - `LICENSE` — Apache License 2.0(Version 2.0, January 2004) 전문 202줄. 부록 끝의 `Copyright 2025 Data Intelligence Lab, The University of Hong Kong`와 `Licensed under the Apache License, Version 2.0` 고지가 있다. 부록의 안내 문단(185~188줄)은 표준 Apache 2.0 부록 문구와 달리 `"Alarm or alarm" copyright header … (Alarm is the umbrella trademark …)`로 적혀 있다(조항 본문 1~9와는 별개의 부록 설명이라 허가 조건에는 영향이 없다고 읽지만, 문구가 표준과 다르다는 사실만 기록). `pyproject.toml:18`의 `license = {text = "Apache-2.0"}`와 일치. 코드 확인.
  - `web/vendor/thinking-orbs/LICENSE` — MIT, `Copyright (c) 2026 Jakub Antalik`. `THIRD_PARTY_NOTICES.md`가 출처(`Jakubantalik/Libraries` `packages/thinking-orbs`, 커밋 `3862ffa3`)와 지역 수정 사실을 적는다. 코드 확인.
  - `web/public/provider-icons/LICENSE.lobehub` — MIT, `Copyright (c) 2023 LobeHub`. 코드 확인.
  - `web/public/provider-icons/LICENSE.llama-brand` — Creative Commons Attribution-NonCommercial 4.0 International(CC BY-NC 4.0) 전문. 같은 폴더의 `llama-BRAND-USAGE.txt`가 "CC BY-NC 4.0이지만, ggml-org가 Llama.app·Llama.cpp를 가리키는 용도에 한해 상업적 재배포를 포함해 로고 복제를 허용한다"고 덧붙인다. 코드 확인.
  - `THIRD_PARTY_NOTICES.md` — CSSwitch(MIT, 2026 shanjunjie), Hermes Agent(MIT, 2025 Nous Research), thinking-orbs(MIT)의 개념·소스 차용 고지. LICENSE 이름의 파일은 아니지만 함께 기록. 코드 확인.
  - 추적 파일 중 이름에 LICENSE/COPYING이 들어간 파일은 위 4개뿐이다(`git ls-files`). `web/package.json`에는 `license` 필드가 없고 `package-lock.json` 의존성 라이선스는 열지 않았다(미확인).
- **언어/규모**: Python ≥3.11,<3.15 백엔드(`pyproject.toml` `requires-python`) + TypeScript(Next.js 16·React 19) 웹. 추적 파일 3,875개(web 1,434 / deeptutor 1,261 / tests 881 / assets 173 / deeptutor_cli 24 / scripts 18 / .github 15 / docs-for-user 14 / requirements 10 / examples 8 / docs 7 / packaging 2). `deeptutor/` 비테스트 `.py` 약 29.7만 줄. 코드 확인(`git ls-files`·`wc`).
- **분석 대상 제품**(배포 단위·입구):
  - 루트 패키지 `deeptutor`(`pip install deeptutor`): Python 백엔드 `deeptutor/`와 CLI `deeptutor_cli/`, 콘솔 스크립트 `deeptutor`·`deeptutor-export-frontend-contracts`(`pyproject.toml` `[project.scripts]`). 선택 extras: `server`, `partners`(=`tutorbot`), `matrix`, `parse-*`, `math-animator`, `graphrag`, `rag-lightrag`, `rag-rerank`, `guard`, `video-learning`, `codebuddy` 등.
  - `web/`(npm 이름 `opentutor-web`, Next.js): 별도 프로세스의 프론트엔드. 릴리스 빌드 결과는 `deeptutor_web/`(현재는 빈 패키지 자리표시)에 담긴다.
  - `packaging/deeptutor-cli/`: CLI 전용 배포(`deeptutor-cli`, 웹·FastAPI 서버 의존성 제외).
  - 컨테이너: `Dockerfile`(웹 빌드+백엔드 한 이미지), `docker-compose*.yml`·`compose.yaml`(Podman), `Dockerfile.runner`(샌드박스 사이드카), 선택 사이드카 PocketBase·Redis.
  - 확장 입구: `examples/plugins/learning_echo`(예제 플러그인), 읽기 확장 entry point 5개(`pyproject.toml:105`), 루트 `SKILL.md`(에이전트용 CLI 핸드오버 문서).
  - `tests/`(881개)와 `web/tests/`, `.github/workflows` 4개는 열지 않았다(워크플로 2장 3번).
- **스펙 범위**: 2026-10-27 승인(사용자 "1,2 진행", 2절 "스킬화 관점 지도" 기준). 승인 행: 10 마스터리 엔진 중 학습 상태·게이트·다음 목표·증거 기록(`learning/{models,policy,mastery}.py`와 기록 경로)과 복습 스케줄러(`learning/scheduler.py`). 4장에서 두 스펙 `mastery-engine.md`, `review-scheduler.md`로 나눈다(스케줄러가 독립된 550줄 상태 기계이고, 한쪽이 다른 쪽을 `depends`로 가져 순환하지 않는다). 제외: 부속 20행 전부(이유: 사용자 제외, 별도 답 없음) · 나머지 핵심 행, 경로 생성 `topic_generation.py` 포함(이유: 이번 승인에 없음, `미작성`)

---

## 2. 프로젝트 개요

README 첫 줄의 주장은 "Lifelong Personalized Tutoring"이고, 핵심 특징은 "하나의 런타임에서 Chat·Ask Questions·Quiz·Research·Visualize·Solve·Course Study·Mastery Path·Immersive Reading·Audio Overview를 돌린다"이다(`README.md` "Key Features"; README 주장은 아래 코드 대조 전까지 미확인).

코드로 확인한 구조는 이렇다(전부 코드 확인, 근거는 3절과 지도의 진입점).
1. **한 번의 대화 턴(turn)은 항상 같은 길로 실행된다.** 웹(WebSocket `/ws`)·CLI(`DeepTutorApp`)는 `TurnApplicationService.start_turn`으로 들어가 세션 저장소에 기록하고, 비동기 태스크 `_run_turn`이 `TurnEngine.execute`를 불러 `ChatOrchestrator`가 선택된 **캡빌리티(capability, 턴 전체를 맡는 모드)** 의 `run`을 실행한다. Partner(IM 연동 동료)는 이 길 중 턴 서비스를 거치지 않고 `get_turn_engine().execute`를 직접 부른다.
2. **캡빌리티는 두 겹이다.** 턴 캡빌리티 11개(`BUILTIN_CAPABILITY_CLASSES`)와, 채팅 에이전트 루프에 도구·프롬프트를 얹는 **루프 확장(LoopExtension)** 14개(`BUILTIN_LOOP_CAPABILITY_SPECS`). solve·ask_questions·mastery·reading·course_study·visualize(텍스트 경로)는 별도 파이프라인 없이 "채팅 루프 + 확장"이다. deep_research·deep_question은 별도 파이프라인이고, 두 곳 모두 다른 루프 엔진(`run_agentic_loop`, THINK/TOOL/FINISH 규약)을 쓴다. 채팅 계열은 `AgentLoop`(네이티브 도구 호출 루프, 기본 최대 8라운드).
3. **도구 101종**이 이름→`module:Class` 목록 `BUILTIN_TOOL_SPECS`에 등록돼 있고(정적 AST 집계), 턴마다 사용자 토글·컨텍스트 조건(KB가 붙었는가 등)에 따라 일부만 장착된다.
4. **북(Book)은 턴 캡빌리티가 아닌 병렬 엔진**(`BookEngine`, 제안 → 뼈대 → 페이지 컴파일)이고 API·CLI가 직접 부른다. 마스터리·읽기·코스·실습도 API가 직접 부르는 도메인 엔진을 가진다.
5. **저장은 로컬 파일 중심**이다. 세션·턴·이벤트·문제 노트북은 `data/user/chat_history.db`(SQLite, PocketBase로 교체 가능), 마스터리는 별도 SQLite, 읽기 카탈로그도 SQLite, 메모리는 마크다운·JSONL(`deeptutor/services/path_service.py` 배치 주석).

**비교 축 후보 위치**(코드 확인 수준은 괄호):
- 학습자 상태: 마스터리 `LearningProgress`(지식점별 숙달도·증거·복습 큐·학습자 프로필), 3계층 메모리(L1 trace → L2 surface별 → L3 4슬롯), 학습 저널(mission·세션 노트·인사이트), 연습 복습 상태(SM-2식), 읽기·북 진행. (정의 위치 코드 확인)
- 수업 진행: 마스터리는 "모델이 무엇을 가르칠지 정하고, 진행 가능 여부는 결정적 정책 함수가 판정"(`deeptutor/learning/policy.py` `is_mastered`·`next_objective`, `deeptutor/capabilities/mastery/capability.py` docstring). 코스·북·읽기는 각자 컨테이너가 있다. (마스터리 정책 코드 확인)
- 자료 연결: KB 9종 RAG 엔진 + 연결형 소스(Obsidian·IMA 등), 읽기 자료, 노트북, 웹 검색 14종, GitHub·문서 사이트 동기화. (등록부 코드 확인)
- 모델·데이터: 제공자 스펙 45개(구현 백엔드 6종), 임베딩 어댑터 7, 검색 14, 음성 6, 이미지 3·영상 2. 데이터는 `data/` 아래 로컬, 외부로 나가는 것은 모델·검색·스킬 허브 등 호출. (등록부 코드 확인, 외부 동작 미확인)

### 기능 지도

<!--
조사 방식: 서브에이전트 없이 이 세션이 진입점 파일을 직접 읽었다. 등록부(라우터 장착, BUILTIN_*_SPECS, KNOWN_PROVIDERS, PROVIDERS, 어댑터 디렉터리)는 grep·AST로 전수 집계했다.
검증 수준 (지도 단계):
- "코드 확인(…)": 괄호 안의 부분(진입 함수·등록·상수·docstring)을 직접 읽음.
- "추론": 파일 이름·docstring만 보고 판단, 본문은 열지 않음.
- "미확인": 외부 서비스·README 주장 등.
스펙 단계(4장)에서 R-ID 단위로 다시 붙인다. 모든 행의 스펙 상태는 미작성(범위 승인 전).
구분 기준(제안): 핵심 = 학습·대화 흐름을 이루는 기능과 이를 돌리는 필수 런타임·입구. 부속 = 선택적 통합·확장·배포·개발 단위, 또는 학습 흐름과 독립인 보조 기능(스펙으로 쓸지 사용자에게 따로 묻는다).
경로 표기: `파일:줄 심볼`. 선행의 숫자는 이 표의 행 번호, S는 아래 공유 계약.
-->

#### A. 턴 런타임 (대화 한 번이 실행되는 길)

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 1. 턴 접수·저장·재생 | 메시지·옵션(캡빌리티·도구·KB·참조)을 접수해 세션·사용자 메시지를 저장하고 턴을 비동기 태스크로 실행. 이벤트에 `seq`를 붙여 코디네이터에 발행하고 `after_seq`로 재구독, 취소·재생성·사용자 답변(ask_user)·편집 대체. 다중 워커는 Redis 필수. 캡빌리티 내부는 제외 | `deeptutor/api/routers/unified_ws.py:44 unified_websocket`, `deeptutor/app/service.py:21 TurnApplicationService`, `deeptutor/services/session/turns/request_preparer.py:139 start_turn`(태스크 생성 `:902`), `deeptutor/services/session/turns/executor.py:139 _run_turn`(엔진 호출 `:1031`), `deeptutor/services/session/turns/lifecycle.py:354 subscribe_turn`, `deeptutor/runtime/coordination/settings.py`, `deeptutor/runtime/coordination/protocol.py RuntimeCoordinator` | S1, S3, S8 | 핵심 | `capabilities/turn-lifecycle.md` · 미작성 | 코드 확인(WS→start_turn→태스크→엔진 호출 연결, 코디네이터 backend `memory`\|`redis`) / 저장 스키마 세부·복구 경로 미탐색 |
| 2. 채팅 에이전트 루프 | UnifiedContext를 받아 라운드마다 LLM 호출 → 도구 호출 병렬 디스패치 → 결과 관찰을 반복하고 도구 없는 최종 답을 스트림. `ask_user`로 턴 일시정지, 컨텍스트 창 가드, 강제 종결, 텍스트형 도구 호출 폴백(DSML). 기본 최대 8라운드 | `deeptutor/agents/chat/capability.py ChatCapability`, `deeptutor/agents/loop/pipeline.py:200 AgenticLoopPipeline`(`:106 DEFAULT_MAX_ROUNDS`), `deeptutor/agents/loop/agent_loop.py:300 AgentLoop`(`run :335`, `_run_loop :429`), `deeptutor/runtime/agentic/tool_dispatch.py`, `deeptutor/runtime/agentic/client.py` | S1, S2, 3, 4 | 핵심 | `capabilities/chat-agent-loop.md` · 미작성 | 코드 확인(`AgentLoop.run` 시작부, 파이프라인 설명, 라운드 상수) / `_run_loop` 본문 분기·DSML 폴백 미탐색 |
| 3. 도구 레지스트리·장착 규칙 | 내장 도구 101종을 지연 로드 목록으로 등록하고, 턴마다 사용자 토글 8개(`USER_TOGGLEABLE_TOOL_NAMES`)·컨텍스트 조건 도구·캡빌리티 소유 도구·상시 도구를 조합해 장착. MCP 등 deferred 도구는 `load_tools`로 점진 공개. 도구 본문은 각 기능 행에 둠 | `deeptutor/tools/builtin_specs.py:46 BUILTIN_TOOL_SPECS`, `deeptutor/tools/builtin/__init__.py:2148 USER_TOGGLEABLE_TOOL_NAMES`(`:2173 CONFIGURABLE_BUILTIN_TOOL_NAMES`), `deeptutor/agents/_shared/tool_composition.py:174 compose_enabled_tools`, `deeptutor/agents/loop/pipeline.py:753 _compose_enabled_tools`, `deeptutor/runtime/registry/tool_registry.py:28 ToolRegistry`, `deeptutor/runtime/registry/deferred_tools.py:116 DeferredToolLoader` | S2 | 핵심 | `capabilities/tool-registry.md` · 미작성 | 코드 확인(목록·토글 상수·함수 존재) / 장착 규칙 본문은 `docs/guides/tools-surface.md`를 후보로만 읽음(그 문서 기준 SHA가 다름, 아래 차이 참조), compose 본문 미탐색 |
| 4. 대화 컨텍스트 조립 | 토큰 예산 안에서 대화 기록을 조립·요약하고, 첨부 파싱, 참조(노트북·기록·책·읽기·문제 노트북·파트너 그룹), 학습 저널 주입(턴마다), L3 메모리 주입(사용자가 참조로 고른 턴만), 페르소나 주입, 읽기 전용 사전 탐색(explore_context)을 한 컨텍스트로 만든다 | `deeptutor/services/session/context_builder.py:265 ContextBuilder`, `deeptutor/services/session/turns/context_assembler.py:11 TurnContextAssembler`(마스터리는 `MasteryContextBuilder`), `deeptutor/services/session/turns/executor.py:572 memory_context`(`:579` 저널), `deeptutor/services/session/_turn_runtime_shared.py:410 _extract_memory_references`, `deeptutor/capabilities/explore_context/explorer.py` | 1, S1 | 핵심 | `capabilities/context-assembly.md` · 미작성 | 코드 확인(빌더 선택, L3·저널 주입 조건) / 요약 임계값·예산 계산·explore 내부 미탐색 |

#### B. 딥 모드 (별도 목적의 캡빌리티)

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 5. 딥 리서치 | 질문 → 재서술(ask_user 미니 루프) → 하위 주제 분해 → 블록별 연구 루프(THINK/TOOL/APPEND/FINISH, 큐 스케줄러) → 반복 보고서 작성(인용 관리). 먼저 개요를 돌려주고 사용자가 확정하면 본 단계를 도는 2단계 흐름 | `deeptutor/agents/research/capability.py:37 DeepResearchCapability`, `deeptutor/agents/research/pipeline.py:341 ResearchPipeline`(`run :527`), `deeptutor/agents/research/utils/citation_manager.py`, `deeptutor/agents/research/request_config.py` | 2, 3, 18, 43, S1 | 핵심 | `capabilities/deep-research.md` · 미작성 | 코드 확인(capability·파이프라인 docstring, `run_agentic_loop` 호출 `:815`·`:1017`) / 보고 단계 내부 미탐색 |
| 6. 딥 퀘스천(문제 생성) | 세 경로: 후속 질문(단일 호출) / custom(탐색 → 계획 → 문제별 루프) / mimic(시험지 PDF를 MinerU 계열 파서로 템플릿화, 탐색·계획 건너뜀). 문제 유형·난이도 혼합 보존 | `deeptutor/agents/question/capability.py:29 DeepQuestionCapability`, `deeptutor/agents/question/pipeline.py:369 QuestionPipeline`(`run_agentic_loop` `:681`), `deeptutor/agents/question/mimic_source.py`, `deeptutor/agents/question/agents/followup_agent.py`, `deeptutor/agents/question/history.py` | 2, 3, 19, S1 | 핵심 | `capabilities/deep-question.md` · 미작성 | 코드 확인(capability 라우팅 docstring) / 파이프라인 단계·mimic 추출 본문 미탐색 |
| 7. 딥 솔브·질문 인터뷰 | 별도 파이프라인 없이 채팅 루프 위의 루프 확장. solve: `solve_plan`·`solve_finish_step`·`solve_replan` 도구와 턴 단위 `SolveSession`. ask_questions: `ask_user`를 강제하는 인터뷰 모드 | `deeptutor/capabilities/solve/capability.py:64 DeepSolveCapability`, `deeptutor/capabilities/solve/loop.py`, `deeptutor/capabilities/solve/tools.py:78 SolvePlanTool`, `deeptutor/capabilities/solve/session.py`, `deeptutor/capabilities/ask_questions/capability.py:18 AskQuestionsCapability` | 2, 3, S7 | 핵심 | `capabilities/solve-and-ask.md` · 미작성 | 코드 확인(docstring·등록 `registry.py:49`) / 확장 훅 본문·SolveSession 상태 전이 미탐색 |
| 8. 시각화·수학 애니메이션 | 시각화: 설치된 visualizer 타입(코어·번들·사용자별)을 골라 채팅 루프가 `submit_visualization` 도구로 검증된 payload를 캔버스에 제출. render_mode가 `manim_video`·`manim_image`면 Manim 하위 파이프라인(개념 분석 → 설계 → 코드 생성·재시도 → 요약 → 렌더). `math_animator`는 독립 캡빌리티(manim 선택 설치 필요) | `deeptutor/agents/visualize/capability.py:102 VisualizeCapability.run`(`_run_manim_path :270`), `deeptutor/visualizers/registry.py:13 VisualizerRegistry`, `deeptutor/visualizers/tool.py:22 SubmitVisualizationTool`, `deeptutor/visualizers/loop_capability.py`, `deeptutor/agents/math_animator/pipeline.py:26 MathAnimatorPipeline`, `deeptutor/agents/math_animator/renderer.py` | 2, 3, S7 | 핵심 | `capabilities/visualize-and-animate.md` · 미작성 | 코드 확인(`run` 분기: 텍스트 경로=`AgenticChatPipeline`, manim 경로=서브 파이프라인) / 렌더러·visualizer 번들 본문 미탐색 |
| 9. 오디오 오버뷰 | KB 근거로 host·expert 2화자 대본(2~80 세그먼트, 번갈아 발화, `source_ids` 인용 검증)을 JSON으로 만들고 TTS로 합성해 오디오와 인용 있는 대본을 낸다 | `deeptutor/capabilities/audio_overview/capability.py:21 AudioOverviewCapability`, `deeptutor/capabilities/audio_overview/pipeline.py:311 AudioOverviewPipeline`(`parse_script :199`) | 17, 18, 44, S1 | 핵심 | `capabilities/audio-overview.md` · 미작성 | 코드 확인(대본 모델·검증 규칙) / 합성·렌더(`_render_audio`) 미탐색 |

#### C. 학습 상태와 수업 진행

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 10. 마스터리 엔진 | 학습 경로(`LearningProgress`: 모듈 → 지식점 4유형 memory/concept/procedure/design, 증거, 퀴즈 시도, 오류, 대기 질문, 학습자 프로필)를 SQLite 트랜잭션으로 저장. 순수 정책: memory·procedure는 정량 게이트 0.9, concept·design은 모델의 정성 평가로 게이트, "다음에 할 것"은 숙달 상태에서 계산(단계 카운터 없음). 복습은 유형별 간격표·목표 기억률(기본 0.9, 0.7~0.99)로 스케줄 | `deeptutor/learning/service.py:328 LearningService`(`grade_and_record :535`), `deeptutor/learning/policy.py:150 is_mastered`(`:266 next_objective`, `QUANTITATIVE_GATE`), `deeptutor/learning/scheduler.py:127 SpacedRepetitionScheduler`(`INTERVAL_SEQUENCES`), `deeptutor/learning/storage.py:395 LearningStore`(`:108 LearningTransaction`), `deeptutor/learning/models.py:619 LearningProgress`, `deeptutor/learning/grading.py:13 grade_answer`, `deeptutor/learning/semantic_assessment.py` | S4 | 핵심 | [`capabilities/mastery-engine.md`](capabilities/mastery-engine.md) ready(상태·게이트·증거 기록) + [`capabilities/review-scheduler.md`](capabilities/review-scheduler.md) ready(복습 일정). 2026-10-27에 둘로 분리: 스케줄러 550줄이 독립 상태 기계이고 `depends`가 스케줄러 → 엔진 한 방향이라 순환이 없다. 경로 생성 `topic_generation.py`는 미작성 | 코드 확인(게이트 상수·`next_objective` 시그니처·간격표·저장소 클래스 정의, 스펙에서 `service.py` 증거 기록 경로 추가 확인) / `service.py` 3,355줄·`storage.py` 본문 대부분 미탐색 |
| 11. 마스터리 튜터 루프 | `mastery_path` 캡빌리티가 경로 바인딩·경로 리스(동시 턴 방지)를 정하고 튜터 프롬프트의 `MasteryLoopPipeline`(채팅 루프 엔진)을 실행. 게이트 도구(status·quiz·grade·assess·skip·repair·defer·build·mode·profile·revise)와 경로 이동 도구(paths·switch·leave), 레슨 준비. 카드형 문제 응답은 세션 어댑터가 채점 | `deeptutor/capabilities/mastery/capability.py:57 MasteryPathCapability`, `deeptutor/capabilities/mastery/pipeline.py:64 MasteryLoopPipeline`, `deeptutor/capabilities/mastery/tools.py:1606 MasteryGradeTool`(`:1067 MasteryQuizTool`, `:1946 MasteryAssessTool`, `:2294 MasteryBuildTool`), `deeptutor/capabilities/mastery/loop.py`, `deeptutor/services/session/turns/learning_adapter.py:22 LearningTurnAdapter`, `deeptutor/api/routers/mastery_path.py`, `deeptutor/learning/topic_generation.py` | 10, 2, 3, 4, 17, S7 | 핵심 | `capabilities/mastery-tutor.md` · 미작성 | 코드 확인(capability docstring·도구 클래스 목록·리스 획득 코드) / `tools.py` 3,816줄·`loop.py` 본문 미탐색 |
| 12. 연습·문제 노트북 | 문제(퀴즈·마스터리 시도)를 문제 노트북(항목·북마크·카테고리, 세션 SQLite `notebook_entries`)에 모으고, 연습 큐·요약·분석·정답 확인·복습(SM-2식 again/hard/good/easy)과 CSV·XLSX·JSON 가져오기(비실행 파서), AI 판정 WebSocket(이미지 답안 포함) | `deeptutor/api/routers/question_notebook.py`, `deeptutor/api/routers/practice.py:135 queue`(`:243 review`, `:359 import/commit`), `deeptutor/services/practice/scheduler.py:30 schedule`, `deeptutor/services/practice/storage.py:100 PracticeStore`, `deeptutor/api/routers/quiz_judge.py:231 websocket_quiz_judge`, `deeptutor/tools/question_bank.py` | 1, S8 | 핵심 | `capabilities/practice-and-question-bank.md` · 미작성 | 코드 확인(`schedule` 함수 전문, 라우트 목록, `notebook_entries` 테이블 존재) / 판정 프롬프트·가져오기 파서 본문 미탐색. 마스터리 스케줄러(10)와 별개 상태이고 알고리즘도 다름(SM-2식 vs 유형별 간격표) |
| 13. 코스 컨테이너·코스 스터디 | 코스 = 사용자별 학습 컨테이너(KB·책·노트북·마스터리 경로·읽기 워크스페이스·파트너를 참조 집합으로 보유, 규약, 기본값, 강의 계획 단위). course_study 캡빌리티는 코스 ID가 묶인 턴에서만 활성화되어 `course_overview`·`course_material`·`course_edit`·`course_handoff` 4도구로 상태를 보고 이동을 제안 | `deeptutor/services/courses.py:133 StudyCourse`, `deeptutor/services/courses_state.py`, `deeptutor/capabilities/course_study/mode.py:54 CourseStudyCapability`, `deeptutor/capabilities/course_study/capability.py:380 CourseStudyLoopCapability`, `deeptutor/capabilities/course_study/tools.py:560 CourseOverviewTool`, `deeptutor/api/routers/courses.py` | 2, 3, S7 | 핵심 | `capabilities/courses.md` · 미작성 | 코드 확인(docstring·클래스) / 상태 집계 본문·핸드오프 폐쇄 집합 미탐색 |
| 14. 3계층 메모리 | L1 = 표면(chat·notebook·quiz·kb·book·partner·cowriter)별 일자 JSONL trace와 워크스페이스 스냅샷 어댑터, L2 = 표면별 마크다운(각주 인용), L3 = 4슬롯(recent·profile·scope·preferences). 채팅의 유일한 쓰기는 `write_memory`(선호 add/edit, 도구 설명상 240자 이내, 중복은 건너뜀). 나머지는 Memory 워크벤치 API: LLM 통합(update·audit·dedup) 실행(취소·되돌리기)과 직접 편집. 읽기는 `read_memory` 도구와 L3 참조 주입(4) | `deeptutor/services/memory/store.py:69 MemoryStore`, `deeptutor/services/memory/trace.py:66 append`, `deeptutor/services/memory/paths.py:48 Surface`, `deeptutor/services/memory/snapshot/adapters.py:658 read_entities`, `deeptutor/services/memory/consolidator/runs.py:118 RunManager`, `deeptutor/services/memory/consolidator/modes/update.py:80 run_update`, `deeptutor/tools/builtin/__init__.py:1159 WriteMemoryTool`, `deeptutor/api/routers/memory.py:308 runs/start` | 4, S4, 41 | 핵심 | `capabilities/memory-three-layer.md` · 미작성 | 코드 확인(`write_memory` 전문, 표면·슬롯 상수, `TraceEvent.new` 호출처 grep = write_memory·partner 메모리 도구·RAG 검색 3곳) / `run_update`를 부르는 곳이 `api/routers/memory.py` 밖에서는 grep에 없음(= 자동 통합 호출처 미발견, 사용자 시작으로 추론) / 통합 프롬프트·청킹 미탐색 |
| 15. 학습 저널·시작 제안 | 저널(mission: topic·why·level, 세션 노트, 통찰 레코드)을 `learning_status`·`learning_update` 도구가 읽고 쓰며 매 턴 프롬프트에 주입. 홈 시작 제안(메모리 L3와 최근 활동 기반)과 작성창 힌트 | `deeptutor/services/learning_journal/store.py:58 LearningJournalStore`(`injection_markdown :134`), `deeptutor/tools/learning_journal_tools.py:16 LearningStatusTool`(`:47 LearningUpdateTool`), `deeptutor/services/session/turns/executor.py:579`, `deeptutor/services/suggestions.py`, `deeptutor/api/routers/dashboard.py` | 14, 4 | 핵심 | `capabilities/learning-journal.md` · 미작성 | 코드 확인(저장소 클래스·주입 호출 줄) / 제안 생성 LLM 호출·캐시 정책 미탐색 |
| 16. 노트북 | 사용자 노트북(레코드 유형별 항목, Markdown 가져오기·교체), `list_notebook`·`write_note` 도구, 노트북 참조 | `deeptutor/services/notebook/service.py:92 NotebookManager`, `deeptutor/tools/builtin/__init__.py:1545 WriteNoteTool`(`:1328 ListNotebookTool`), `deeptutor/agents/notebook/analysis_agent.py`, `deeptutor/api/routers/notebook.py`, `deeptutor_cli/notebook.py` | S4 | 핵심 | `capabilities/notebook.md` · 미작성 | 코드 확인(클래스·도구 정의 위치) / 저장 형식·참조 해석 미탐색 |

#### D. 자료 연결

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 17. 지식베이스 수명주기·소스 동기화 | KB 등록·설정(JSON), 문서 업로드 → 파싱 → 색인(진행 이벤트 WS), 증분 추가, 색인 실행 상태, 임베딩 불일치 조정, 기본 KB, 폴더 연결 변경 감지, GitHub 저장소·문서 사이트 크롤 동기화(예약), 삭제. 연결형 KB는 24 | `deeptutor/knowledge/manager.py:325 KnowledgeBaseManager`, `deeptutor/knowledge/initializer.py:35 KnowledgeBaseInitializer`(`process_documents :168`), `deeptutor/knowledge/add_documents.py`, `deeptutor/knowledge/indexing_run.py`, `deeptutor/services/github_source/sync.py`, `deeptutor/services/web_source/sync.py`, `deeptutor/api/routers/knowledge.py`, `deeptutor_cli/kb.py` | 18, 19, 42, S4, S6 | 핵심 | `capabilities/knowledge-base.md` · 미작성 | 코드 확인(매니저 메서드 목록·초기화 시그니처) / 동기화 주기(README 24h)·재색인 복구 미확인 |
| 18. RAG 엔진 패밀리(색인형) | 공통 계약 `RAGPipeline`(initialize·add_documents·search·delete)을 구현한 엔진을 KB가 `rag_provider`로 묶는다. 이 행은 llamaindex(기본, 파일 구성은 리트리버·리랭크·벡터 저장소; 하이브리드·FAISS 세부는 README·`pyproject.toml` 주석 기준이라 미확인), pageindex·pageindex-oss, graphrag, lightrag. `rag` 도구가 `RAGService.search`로 호출, 검색 후 L1 trace 기록. lightrag(15파일)·graphrag(11파일)는 고유 흐름이 커서 스펙 단계에서 분리 후보 | `deeptutor/services/rag/service.py:22 RAGService`(`search :127`), `deeptutor/services/rag/factory.py:49 KNOWN_PROVIDERS`, `deeptutor/services/rag/pipelines/base.py:17 RAGPipeline`, `deeptutor/services/rag/pipelines/llamaindex/pipeline.py`, `deeptutor/tools/rag_tool.py`, `deeptutor/services/rag/index_versioning.py` | S6, 19, 42 | 핵심 | `capabilities/rag-engines.md` · 미작성 | 코드 확인(공급자 상수 9개·프로토콜·`rag_tool`→`RAGService`) / 각 파이프라인 본문·하이브리드 가중치 미탐색 |
| 19. 문서 파싱 엔진 패밀리 | `ParseService.parse`가 설정된 엔진(docling·liteparse·markitdown·mineru(로컬 CLI/클라우드)·pymupdf4llm·text_only·tika)으로 파일을 `ParsedDocument`로 바꾸고, 미지원 형식은 대체 엔진으로, 결과 캐시·서명은 파일 이름(`cache.py`·`signature.py`)으로만 추론 | `deeptutor/services/parsing/service.py:74 ParseService`(`parse :104`), `deeptutor/services/parsing/engines/factory.py:70 _ENGINE_LOADERS`, `deeptutor/services/parsing/engines/mineru/engine.py`, `deeptutor/services/parsing/base.py`, `deeptutor/services/parsing/signature.py` | 없음 | 핵심 | `capabilities/document-parsing.md` · 미작성 | 코드 확인(엔진 로더 7개·서비스 시그니처) / 엔진 본문 미탐색 |
| 20. 몰입형 읽기(Reading) | 자료(문서·URL·영상·오디오)를 수집해 locator 단위로 쪼개고 주석·위치·책갈피를 저장(SQLite 카탈로그). 채팅과 연결: 열린 자료·뷰포트를 아는 `immersive_reading` 캡빌리티(자료 개요·검색·읽기·그림 보기·이동·주석 도구, 근거 인용), 확장 5종(read_aloud·guided_learning·vocabulary·quiz·translation, entry point), 내보내기, 노트북·마스터리로 지식 캡처 | `deeptutor/reading/ingestion.py:151 ReadingIngestionService`, `deeptutor/reading/store.py:161 ReadingStore`, `deeptutor/reading/catalog_store.py:54 ReadingCatalogStore`, `deeptutor/reading/extensions.py:109 ReadingExtensionRegistry`, `deeptutor/capabilities/reading/capability.py:112 ReadingCapability`, `deeptutor/capabilities/reading/mode.py:42 ImmersiveReadingCapability`, `deeptutor/capabilities/reading/tools.py`, `deeptutor/api/routers/reading.py` | 2, 3, 19, S7 | 핵심 | `capabilities/immersive-reading.md` · 미작성 | 코드 확인(클래스·docstring·entry point 선언 `pyproject.toml:105`) / 추출·인제스트·locator 본문 미탐색 |
| 21. 영상 학습(타임드 미디어) | YouTube URL·자막·Invidious 계정 연결, 타임스탬프 노트·마크, 진행 저장. 새 UI는 읽기(20)로 합쳐졌고 `reading_migration`이 옛 기록을 읽기 스토어로 투영하며 `/learning/watching` 페이지는 읽기로 리다이렉트. Bilibili는 읽기 인제스트가 처리 | `deeptutor/video_learning/service.py:307 TimedMediaStore`(`parse_youtube_url :83`), `deeptutor/video_learning/invidious_account.py`, `deeptutor/video_learning/notes.py`, `deeptutor/video_learning/reading_migration.py`, `deeptutor/api/routers/video_learning.py`, `web/app/(workspace)/learning/watching/page.tsx` | 20 | 핵심 | `capabilities/video-learning.md` · 미작성 | 코드 확인(리다이렉트 파일 전문, 마이그레이션 docstring) / 자막 취득 외부 동작 미확인 |
| 22. 북(Book 엔진) | 소스(KB·노트북·문제 노트북·대화)로 책 생성: 제안 → (사용자 확인) → 뼈대 → (확인) → 페이지 셸 → 큐 컴파일. 책마다 백그라운드 워커, 연속 실패 시 일시정지, 블록 19종 편집·재생성, 심화 하위 페이지, KB 드리프트 검사, 독자별 진행·퀴즈. 턴 캡빌리티가 아닌 병렬 엔진 | `deeptutor/book/engine.py:317 BookEngine`(`create_book :467`, `confirm_proposal :560`, `confirm_spine :894`, `compile_page :1213`), `deeptutor/book/compiler.py:133 BookCompiler`, `deeptutor/book/models.py:59 BlockType`, `deeptutor/book/agents/spine_agent.py`, `deeptutor/book/blocks/interactive.py`, `deeptutor/api/routers/book.py`, `deeptutor_cli/book.py` | 17, 18, 8 | 핵심 | `capabilities/book-engine.md` · 미작성 | 코드 확인(엔진 docstring·메서드 목록·블록 타입 정의) / 컴파일러·블록 생성 본문 미탐색 |
| 23. 공동집필(Co-Writer) | Markdown 문서를 저장·미리보기하고, 선택 구간을 KB·웹 근거로 고쳐 쓰는 편집 에이전트(도구 호출 기록, 스트림, 자동 표시), DOCX 가져오기·내보내기 | `deeptutor/co_writer/edit_agent.py:102 EditAgent`(`process :130`), `deeptutor/co_writer/storage.py:96 CoWriterStorage`, `deeptutor/co_writer/docx_converter.py`, `deeptutor/api/routers/co_writer.py:521` | 18, 43 | 핵심 | `capabilities/co-writer.md` · 미작성 | 코드 확인(라우트·클래스 위치) / 편집 프롬프트·충돌 처리 미탐색 |
| 24. 연결형 외부 지식 소스 패밀리 | 로컬 색인 없이 외부 리소스를 가리키는 KB 엔트리: Obsidian 볼트(도구 9개로 탐색·작성), LightRAG Server, Tencent IMA, WeKnora, Kiwix(ZIM). 삭제 시 외부 리소스는 건드리지 않는다 | `deeptutor/knowledge/kb_types.py`(모듈 docstring), `deeptutor/knowledge/manager.py:863 register_obsidian_vault`(`:992 register_lightrag_server_kb`, `:1115 register_ima_kb`, `:1173 register_weknora_kb`, `:1216 register_kiwix_kb`), `deeptutor/capabilities/obsidian/capability.py:25 ObsidianCapability`, `deeptutor/capabilities/ima/capability.py:35 ImaCapability`, `deeptutor/services/rag/pipelines/kiwix/pipeline.py` | 17, S6, S7 | 부속 | `capabilities/connected-sources.md` · 미작성 | 코드 확인(등록부·타입 docstring) / 외부 서비스 동작 미확인, 파이프라인 본문 미탐색 |
| 25. MarginNote 4 브리지 | MN4 애드온(JS)이 `/api/marginnote4/pair`로 기기를 짝짓고 기기 토큰으로 동기화·하트비트, 서버 SQLite 저장소에 쌓인 학습 데이터를 `marginnote_*` 도구 7개로 채팅이 검색·읽기 | `deeptutor/api/routers/marginnote4.py:149 pair`, `deeptutor/capabilities/marginnote4/store.py:147 MarginNoteStore`, `deeptutor/capabilities/marginnote4/capability.py:28 MarginNoteCapability`, `deeptutor/knowledge/manager.py:1042 register_marginnote4_kb` | 17, S7 | 부속 | `capabilities/marginnote4-bridge.md` · 미작성 | 코드 확인(라우터 docstring·스토어 클래스) / 애드온 쪽은 레포 밖이라 미확인 |
| 26. KB 검색 품질 평가 | `deeptutor kb eval`·`eval-diff`: JSONL QA 세트(질의+정답 구절)를 채팅과 같은 검색 경로로 돌려 랭크 지표를 내고 두 보고서를 비교 | `deeptutor/services/rag/eval/runner.py:272 evaluate_dataset`, `deeptutor/services/rag/eval/metrics.py`, `deeptutor/services/rag/eval/diff.py`, `deeptutor_cli/kb.py` | 18 | 부속 | `capabilities/kb-eval.md` · 미작성 | 코드 확인(함수·CLI 명령 존재) / 지표 정의 본문 미탐색 |
| 27. 파일 라이브러리·첨부·미리보기 | 대화 첨부의 영속 저장, 대화 간 재사용 파일 라이브러리, 오피스→PDF 미리보기 | `deeptutor/services/storage/attachment_store.py:66 AttachmentStore`, `deeptutor/services/storage/file_library.py:83 FileLibraryStore`, `deeptutor/services/office_preview.py:62 render_office_pdf`, `deeptutor/api/routers/file_library.py` | 19 | 부속 | `capabilities/files-and-attachments.md` · 미작성 | 추론(클래스 정의 위치·docstring만) |

#### E. 동료·에이전트

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 28. Partner 런타임 | Partner = SOUL.md·모델 정책·라이브러리(KB·스킬·노트북 복사 또는 링크)·기억·채널을 가진 지속 동료. 웹·IM 인바운드 메시지가 `PartnerRunner`에서 일반 턴으로 실행(턴 서비스 미경유). 서버 프로세스 안 asyncio 태스크로 시작·정지, 파트너 기억 도구 3개(`PARTNER_BUILTIN_TOOL_NAMES`), 사용자별 비공개 세션은 README 주장이라 미확인 | `deeptutor/services/partners/manager.py:482 PartnerManager`, `deeptutor/services/partners/runtime.py:137 PartnerRunner`(`process_message :300`, 엔진 호출 `:541`), `deeptutor/services/partners/workspace.py:70 ensure_partner_workspace`(`:121 provision_assets`), `deeptutor/tools/partner_memory.py`, `deeptutor/api/routers/partners.py`, `deeptutor_cli/partner.py` | 2, 3, 14, 17, S1 | 핵심 | `capabilities/partner-runtime.md` · 미작성 | 코드 확인(엔진 직접 호출 줄, 매니저 docstring) / 세션·승인·기억 분리 본문 미탐색 |
| 29. IM 채널 어댑터 패밀리 | 공통 `BaseChannel` 계약 + 패키지 자동 발견(`pkgutil`) + 외부 entry point 플러그인. 내장 채널 16개: dingtalk·discord·email·feishu·matrix·mattermost·mochat·msteams·napcat·qq·slack·telegram·wecom·weixin·whatsapp·zulip. 메시지 버스, 스트림 델타·진행 메시지 병합, 재시도 전송, Feishu·WeCom·WeChat QR 온보딩 | `deeptutor/partners/channels/base.py:38 BaseChannel`, `deeptutor/partners/channels/registry.py:64 discover_all`, `deeptutor/partners/channels/manager.py:193 ChannelManager`, `deeptutor/partners/bus/queue.py:9 MessageBus`, `deeptutor/services/partners/channel_onboarding.py` | 28 | 핵심 | `capabilities/partner-channels.md` · 미작성 | 코드 확인(발견 로직·`name =` 집계 16개) / 채널별 외부 프로토콜 미확인 |
| 30. Partner 그룹 | 여러 파트너가 모드(토론 규약)에 따라 대화하고, 사용자 승인으로 파트너끼리 질문을 주고받는 그룹 | `deeptutor/services/partner_groups/manager.py:132 PartnerGroupManager`, `deeptutor/services/partner_groups/modes.py`, `deeptutor/capabilities/partner_group/capability.py:18 PartnerGroupCapability`, `deeptutor/api/routers/partner_groups.py` | 28, S7 | 부속 | `capabilities/partner-groups.md` · 미작성 | 추론(docstring·클래스 정의 위치) |
| 31. 서브에이전트 상담(My Agents) | 로컬 에이전트 CLI(Claude Code·Codex·Grok·Antigravity·Kimi·opencode·MiMo·Hermes(+원격)·OpenClaw·DeepSeek)와 파트너를 포인터 KB로 연결하고, 채팅의 `consult_subagent`가 실제로 프로세스를 실행해 활동을 스트림. 라운드 예산, 연결 탐지 | `deeptutor/services/subagent/registry.py:29 _BACKENDS`, `deeptutor/services/subagent/base.py:22 SubagentBackend`, `deeptutor/capabilities/subagent/capability.py:32 SubagentCapability`, `deeptutor/capabilities/subagent/tools.py:48 consult_subagent`, `deeptutor/knowledge/manager.py:949 register_subagent_connection`, `deeptutor/api/routers/subagents.py` | 2, 3, 17, S7 | 핵심 | `capabilities/subagent-consult.md` · 미작성 | 코드 확인(백엔드 11개 등록부) / 백엔드별 프로토콜 미탐색, 외부 CLI 동작 미확인 |
| 32. 대화 기록 가져오기 | ChatGPT export·Claude Code·Codex 기록을 브라우저가 읽어 서버로 올리면 다시 열 수 있는 일반 세션으로 저장 | `deeptutor/api/routers/imports.py:75 import_chat_history`, `web/lib/chat-import/chatgpt.ts` | 1 | 부속 | `capabilities/chat-import.md` · 미작성 | 코드 확인(함수·docstring) / 변환 규칙 미탐색 |

#### F. 확장·실행

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 33. 스킬·스킬 허브 | `SKILL.md` 패키지 CRUD(계정 공유·워크스페이스 소유), 모델이 `read_skill`로 읽음, 허브(EduHub·ClawHub, HTTP `/api/v1`)에서 검색·설치(검증 게이트)·게시·업데이트 | `deeptutor/services/skill/service.py:220 SkillService`(`read_skill_file :453`), `deeptutor/services/skill/hub.py:268 ClawHubProvider`(`:71 _EDUHUB_BASE_URL`), `deeptutor/tools/builtin/__init__.py:1878 ReadSkillTool`, `deeptutor_cli/skill.py`, `deeptutor/api/routers/skills.py` | S2 | 부속 | `capabilities/skills-and-hub.md` · 미작성 | 코드 확인(허브 URL 상수·프로바이더 프로토콜) / 허브 서버 동작 미확인, 검증 게이트 본문 미탐색 |
| 34. 페르소나 | `PERSONA.md`로 말투·행동 프리셋을 저장(프리셋 3개: peer·research-assistant·teacher), 턴당 하나를 첫 토큰 전에 주입 | `deeptutor/services/persona/service.py:99 PersonaService`, `deeptutor/services/persona/presets/teacher/PERSONA.md`, `deeptutor/services/session/turns/executor.py:583`, `deeptutor/api/routers/personas.py` | 4 | 부속 | `capabilities/personas.md` · 미작성 | 코드 확인(프리셋 파일·주입 주석) |
| 35. MCP 서비스 | MCP 서버 설정(stdio·sse·streamableHttp 자동 판별), 서버별 전용 연결 태스크(지연 시작·변경분만 재시작), 도구는 deferred 어댑터로 `load_tools` 점진 공개, 큐레이트 카탈로그 46개(원격 우선), OAuth·비밀 저장, 사용자별 서버 | `deeptutor/services/mcp/manager.py:235 MCPConnectionManager`(`:105 MCPToolAdapter`), `deeptutor/services/mcp/config.py:31 MCPServerConfig`, `deeptutor/services/mcp/catalog/loader.py:57 load_catalog`, `deeptutor/services/mcp/oauth.py`, `deeptutor/api/routers/mcp_settings.py`, `deeptutor/api/routers/space_mcp.py` | 3, S2 | 부속 | `capabilities/mcp.md` · 미작성 | 코드 확인(매니저 docstring·설정 모델·카탈로그 JSON 파싱으로 개수 집계) / 서버 실제 연결·OAuth 미확인 |
| 36. CLI 앱(CLI-Anything) | CLI-Anything 카탈로그 스냅샷(101개 앱, 고정 커밋 `bc536c9b`, 2026-07-09)에서 앱을 설치하고(`install_app`) 시간 제한·PATH를 정해 실행(`run_app`), 사용자 선호 | `deeptutor/services/cli_apps/installer.py:87 install_app`, `deeptutor/services/cli_apps/runner.py:37 run_app`, `deeptutor/services/cli_apps/vendor/catalog.json`, `deeptutor/api/routers/space_cli_apps.py` | 3, 37 | 부속 | `capabilities/cli-apps.md` · 미작성 | 코드 확인(함수 위치·카탈로그 메타 JSON) / 설치 본문·샌드박스 마운트 미탐색 |
| 37. 코드 실행 샌드박스 | `exec` 도구가 소스·셸 스크립트를 하나의 계약으로 실행. 백엔드 3종: 러너 사이드카(별도 컨테이너 HTTP, SYSTEM 격리), `bwrap`(Linux), 제한 서브프로세스(관리자 opt-in, APPLICATION 격리). 사용자별 쿼터, 산출물 수집 | `deeptutor/tools/exec_tool.py:36 ExecTool`, `deeptutor/services/sandbox/service.py:33 SandboxService`, `deeptutor/services/sandbox/backends.py:74 RunnerSidecarBackend`(`:139 BwrapBackend`, `:286 RestrictedSubprocessBackend`), `deeptutor/services/sandbox/config.py:66 build_backend`, `deeptutor/services/sandbox/runner/server.py` | S2 | 부속 | `capabilities/exec-sandbox.md` · 미작성 | 코드 확인(백엔드 docstring·클래스 위치) / 격리 강도는 실행 미검증 |
| 38. 플러그인 플랫폼 | 루트 매니페스트 `deeptutor.plugin.json`(스키마 v1, 확장 유형 9종·권한·호환성), 검토된 카탈로그 핀에서 설치·승인·롤백, 격리 환경 워커. 기존 entry point 그룹(`deeptutor.plugins`·`loop_capabilities`·`extensions`·`reading_extensions`·`partners.channels`)은 유지. 예제 플러그인 포함 | `deeptutor/plugins/manifest.py`(`SUPPORTED_EXTENSION_TYPES`), `deeptutor/plugins/lifecycle.py`, `deeptutor/plugins/distribution.py`, `deeptutor/plugins/loader.py:26 ENTRY_POINT_GROUP`, `deeptutor/capabilities/registry.py:21 EXTENSIONS_GROUP`, `deeptutor_cli/plugin.py`, `examples/plugins/learning_echo/learning_echo/worker.py`, `docs/plugin-platform-rfc.md` | S7 | 부속 | `capabilities/plugin-platform.md` · 미작성 | 코드 확인(상수·모듈 docstring) / 설치·워커 격리 본문 미탐색. RFC 문서는 후보로만 읽음 |

#### G. 계정·설정·모델 서비스

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 39. 멀티유저·인증·권한 | 기본은 꺼짐(단일 사용자). 켜면 첫 가입자가 관리자, 사용자별 격리 워크스페이스, 자원 grant(모델·KB·스킬·파트너·도구·exec), 학습자 계정 정책·보호자·기기 자격증명, 감사 기록, 비공개→공개 세션 핸드오프. HTTP 라우터는 `Depends`, WebSocket은 핸들러 안에서 인증 | `deeptutor/api/routers/auth.py:420 require_auth`, `deeptutor/services/auth.py:148 add_user`, `deeptutor/multi_user/identity.py:176 load_users`, `deeptutor/multi_user/grants.py:161 normalize_grant`, `deeptutor/multi_user/guardians.py`, `deeptutor/multi_user/device_credentials.py`, `deeptutor/multi_user/session_handoff.py`, `deeptutor/api/routers/multi_user.py` | S4 | 핵심 | `capabilities/multi-user-auth.md` · 미작성 | 코드 확인(라우터 장착 주석 `api/main.py`·모듈 docstring) / 토큰·비밀 처리·권한 판정 본문 미탐색 |
| 40. 설정·모델 카탈로그·셋업 에이전트 | 설정 원본은 `data/user/settings/*.json`(루트 `.env`는 의도적으로 무시, `deeptutor/services/config/runtime_settings.py:514` docstring). 모델 카탈로그(제공자 프로필·서비스별 모델, 비밀 마스킹·복원), 초안-적용·연결 시험, `deeptutor init` 위저드·`config apply`·`doctor`, 채팅 안에서 설정을 조회·변경하는 setup 캡빌리티(조회·적용·자격 요청·설치 작업) | `deeptutor/services/config/runtime_settings.py:509 RuntimeSettingsService`, `deeptutor/services/config/model_catalog.py:254 ModelCatalogService`, `deeptutor/services/settings/provider_probe.py`, `deeptutor/api/routers/settings.py`, `deeptutor/capabilities/setup/capability.py:39 SetupCapability`, `deeptutor/capabilities/setup/tools.py:66 InspectSetupTool`, `deeptutor_cli/init_cmd.py`, `deeptutor_cli/config_cmd.py` | S5 | 핵심 | `capabilities/settings-and-setup.md` · 미작성 | 코드 확인(클래스 위치·docstring) / README의 "API 키는 모델을 거치지 않는다"는 `deeptutor/capabilities/setup/access.py`·`apply.py` 본문 미확인 |
| 41. LLM 제공자 패밀리 | 제공자 스펙 45개(키워드·환경변수·기본 api_base·게이트웨이/로컬 플래그)가 구현 백엔드 6종(openai_compat 38·anthropic 3·azure_openai·openai_codex·github_copilot·codebuddy 각 1)으로 매핑. 런타임 provider 풀, OAuth(Codex·Copilot·CodeBuddy), 키 풀 회전, 재시도·트래픽 제어·사용량 원장, 추론 파라미터 | `deeptutor/services/provider_registry.py:192 PROVIDERS`(`:775 find_by_model`), `deeptutor/services/llm/provider_factory.py:151 get_runtime_provider`, `deeptutor/services/llm/provider_core/base.py`, `deeptutor/services/llm/config.py:235 get_llm_config`, `deeptutor/services/keypool.py`, `deeptutor/runtime/agentic/client.py` | S5 | 핵심 | `capabilities/llm-providers.md` · 미작성 | 코드 확인(스펙 이름·backend 값 정규식 집계) / 각 제공자 API 호환·OAuth 흐름은 미확인(외부) |
| 42. 임베딩 어댑터 패밀리 | `EmbeddingClient`가 어댑터 7종(openai_sdk·openai_compatible·cohere·dashscope_native·gemini·jina·ollama)으로 임베딩. KB는 임베딩 시그니처에 묶여 모델이 바뀌면 재색인 안내 | `deeptutor/services/embedding/client.py:39 EmbeddingClient`, `deeptutor/services/embedding/adapters/base.py`, `deeptutor/services/embedding/config.py`, `deeptutor/services/rag/embedding_signature.py`, `deeptutor/services/rag/embedding_binding.py` | S5 | 핵심 | `capabilities/embedding-adapters.md` · 미작성 | 코드 확인(디렉터리·클래스 위치) / 어댑터·시그니처 본문 미탐색 |
| 43. 웹 검색 provider 패밀리 | `web_search` 도구의 백엔드 14개(bocha·brave·tavily·qianfan·aliyun_iqs·zhipu·serper·jina·searxng·duckduckgo·serply·perplexity·doubao·firecrawl)를 `@register_provider`로 등록, 소스 필터·결과 통합, 폐기된 이름 3개(exa·baidu·openrouter)는 거부 | `deeptutor/services/search/providers/__init__.py:27 register_provider`(`:170 _register_builtin_providers`), `deeptutor/services/search/base.py`, `deeptutor/services/search/consolidation.py`, `deeptutor/services/search/source_filter.py`, `deeptutor/services/config/provider_runtime.py:126 DEPRECATED_SEARCH_PROVIDERS`, `deeptutor/tools/web_search.py` | S5 | 핵심 | `capabilities/web-search-providers.md` · 미작성 | 코드 확인(데코레이터 grep 14개) / 제공자 본문 미탐색 |
| 44. 음성(TTS·STT) 어댑터 패밀리 | 어댑터 6종(dashscope·gemini·mimo·minimax·openai_compat·volcengine). 설정은 모델 카탈로그의 TTS·STT 서비스, 미리보기·옵션. 읽기 확장 read_aloud·오디오 오버뷰가 사용 | `deeptutor/services/voice/adapters/__init__.py:43 get_tts_adapter`(`:50 get_stt_adapter`), `deeptutor/services/voice/base.py`, `deeptutor/services/voice/config.py`, `deeptutor/api/routers/voice.py` | S5 | 부속 | `capabilities/voice-adapters.md` · 미작성 | 코드 확인(어댑터 파일·팩토리 함수) / 어댑터 본문 미탐색 |
| 45. 이미지·영상 생성 어댑터 패밀리 | imagegen 어댑터 3종(chat_completions·dashscope·openai_compat), videogen 2종(async_task·dashscope). 모델이 설정되지 않으면 `imagegen`·`videogen` 도구는 장착에서 빠진다 | `deeptutor/services/imagegen/base.py:10 BaseImagegenAdapter`, `deeptutor/services/videogen/base.py:15 BaseVideogenAdapter`, `deeptutor/tools/media_gen_tool.py`, `deeptutor/agents/_shared/tool_runtime.py:20 drop_unconfigured_generation_tools` | S5, 3 | 부속 | `capabilities/media-generation.md` · 미작성 | 코드 확인(함수·클래스 위치) / 어댑터 본문 미탐색 |
| 46. 콘텐츠 워크스페이스 | 사용자별 콘텐츠 범위(`workspace_context`)를 정하고, 자원 선택·KB와 대화 이동·데이터 이전(복구 가능 복사)·구성 스냅샷. `deeptutor workspace show/set/reset` | `deeptutor/services/workspace/service.py:80 ContentWorkspaceService`, `deeptutor/services/workspace/context.py:91 workspace_context`, `deeptutor/services/workspace/data_migration.py`, `deeptutor/services/workspace/kb_move.py`, `deeptutor/api/routers/workspace.py`, `deeptutor_cli/workspace_cmd.py` | S4 | 부속 | `capabilities/content-workspace.md` · 미작성 | 코드 확인(클래스·docstring) / 이전·이동 절차 미탐색. 스코프 계약 자체는 공유 계약 S4 |

#### H. 입구·배포·보조

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 47. 웹 UI | Next.js 앱 라우터 62개 페이지·route handler 2개. 그룹: `(workspace)`(chat·co-writer·kanban·learning/{books·mastery·practice·reading}·partners·whisper), `(utility)`(agents·courses·knowledge-bases·memory/{l1·l2·l3·graph}·notebooks·space/*·profile), `(settings)`, `(admin)/admin/users`, `(auth)`. `/api`·`/ws`는 `proxy.ts`가 백엔드로 재작성. 턴은 WS 클라이언트가 전송. 와이어 계약은 백엔드가 소유한 생성 파일 | `web/proxy.ts`, `web/features/chat/transport/UnifiedTurnClient.ts`, `web/features/chat/transport/socket.ts:21`, `web/contracts/README.md`, `web/next.config.js`, `web/package.json` | S3 | 핵심 | `capabilities/web-ui.md` · 미작성 | 코드 확인(라우트 파일 목록·`proxy.ts` 재작성 호출·계약 README) / 컴포넌트 본문(ts/tsx 1,302개) 미탐색, 브라우저 실행 미확인 |
| 48. CLI·SDK 파사드 | `deeptutor` Typer 앱: 최상위 `run`·`start`·`stop`·`serve`·`doctor`·`init`, 하위 `partner`·`chat`·`kb`·`skill`(`skills` 별칭)·`memory`·`plugin`·`config`·`session`·`notebook`·`provider`·`book`·`workspace`. `run --format json`은 NDJSON. 모두 `DeepTutorApp`(파이썬 SDK 파사드)로 턴을 시작. 루트 `SKILL.md`는 에이전트 핸드오버 문서 | `deeptutor_cli/main.py:32 app`(`:83 run_capability`), `deeptutor_cli/common.py`(`run_turn_and_render`), `deeptutor/app/facade.py:60 DeepTutorApp`, `SKILL.md`, `pyproject.toml:101 [project.scripts]` | 1, S1 | 핵심 | `capabilities/cli-and-sdk.md` · 미작성 | 코드 확인(`add_typer` 목록·`@app.command` 이름 집계 = README 명령표와 일치) / REPL·출력 렌더링 본문 미탐색 |
| 49. 실행·배포·업데이트 | `deeptutor start`(런처가 백엔드·프론트 동시 기동, 포트 충돌 처리, 분리 실행·정지), 단일 Docker 이미지(Node 22 빌드 + Python), compose 4종(Podman rootless·읽기 전용 포함), 러너 사이드카 이미지, 선택 PocketBase·Redis 사이드카, 앱 업데이트(PyPI), `doctor`, CLI 전용 패키징, macOS `.command` | `deeptutor/runtime/launcher.py`(`start`), `Dockerfile`, `compose.yaml`, `Dockerfile.runner`, `packaging/deeptutor-cli/pyproject.toml`, `deeptutor/services/app_update.py`, `deeptutor/services/doctor.py`, `start_deeptutor.command` | 48 | 부속 | `capabilities/runtime-and-deploy.md` · 미작성 | 코드 확인(헤더 주석·함수 목록) / 컨테이너 빌드·실행은 하지 않음 |
| 50. 스케줄(cron) | 채팅·파트너가 소유하는 예약 작업(at·every·cron+시간대)을 SQLite에 저장하고, 실행 시각에 소유자 대화로 턴을 실행. `cron` 도구(schedule·list·cancel) | `deeptutor/services/cron/service.py:178 CronService`, `deeptutor/services/cron/repository.py`, `deeptutor/services/cron/executor.py:16 execute_job`, `deeptutor/tools/builtin/__init__.py:2030 CronTool` | 1, 28 | 부속 | `capabilities/cron.md` · 미작성 | 코드 확인(클래스·함수 위치) / 스케줄러 루프·재시작 복구 미탐색 |
| 51. 태스크 보드 | To do·In progress·Done 칸반(노트·보관·복원), 워크스페이스·대화 연결. 모델 설정 불필요 | `deeptutor/services/task_board.py:96 TaskBoardStore`, `deeptutor/api/routers/task_board.py`, `web/app/(workspace)/kanban/page.tsx` | S4 | 부속 | `capabilities/task-board.md` · 미작성 | 코드 확인(클래스·페이지 존재) / 상태 전이 미탐색 |
| 52. Whisper 연습방 UI | 프론트엔드 페이지·컴포넌트만 레포에 있고, 백엔드 캡빌리티 `whisper_visitor`·`whisper_trainee`는 레포 밖(`deeptutor/api/routers/capabilities.py` docstring). 없으면 UI가 가용성 검사로 진입을 막는다 | `web/app/(workspace)/whisper/page.tsx:242`, `web/components/whisper/WhisperComposer.tsx`, `deeptutor/api/routers/capabilities.py:1` | 47 | 부속 | `capabilities/whisper-room-ui.md` · 미작성 | 코드 확인(`git grep`: 파이썬에서는 두 이름이 docstring에만 있음) / 레포 밖 캡빌리티 미확인 |
| 53. 개발·검증 스크립트·CI | `scripts/`(아키텍처 점검·저장소 위생·프런트 계약 내보내기·extras 설치·웹 패키지 준비·docker compose 보조 등), `.importlinter`, `.github/workflows` 4개(tests·pypi-release·docker-release·repository-hygiene), `tests/` 881개·`web/tests/` | `scripts/check_architecture.py`, `scripts/export_frontend_contracts.py`, `.importlinter`, `.github/workflows/tests.yml` | 없음 | 부속 | `capabilities/dev-tooling.md` · 미작성 | 추론(파일 이름만, 본문·테스트는 기본 규칙에 따라 열지 않음) |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜. 기능 개수에 넣지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| S1. 턴 계약: `UnifiedContext`·`StreamEvent`(15종)·`TurnCapability`·`CapabilityManifest`·`TurnRequest` | 1~9, 11, 13, 20, 28, 48 | `deeptutor/core/context.py`, `deeptutor/core/stream.py`, `deeptutor/core/capability_protocol.py`, `deeptutor/core/turn_request.py:127 TurnRequest` | `capabilities/turn-contract.md` · 미작성 | 코드 확인(스트림 이벤트 열거·매니페스트 필드·TurnCapability.run 시그니처) |
| S2. 도구 계약: `BaseTool`·`ToolDefinition`·`ToolResult`(일시정지·모델 전용 메시지) | 2, 3, 5~8, 11, 13, 14, 31, 35~37 | `deeptutor/core/tool_protocol.py:261 BaseTool`(`:78 ToolDefinition`, `:167 ToolResult`) | `capabilities/tool-contract.md` · 미작성 | 코드 확인(클래스 위치) / 필드 의미 대부분 미탐색 |
| S3. 턴 와이어 프로토콜 v2.0(WS 명령·이벤트·실패 코드)과 생성된 프론트 계약 | 1, 47, 48 | `deeptutor/api/contracts/turn_protocol.py:12 PROTOCOL_VERSION`(`:161 ClientCommand`, `:177 StreamEvent`), `web/contracts/README.md`, `scripts/export_frontend_contracts.py` | `capabilities/turn-wire-protocol.md` · 미작성 | 코드 확인(명령 클래스 목록·버전 상수) |
| S4. 계정·워크스페이스 스코프: 현재 사용자, 콘텐츠 워크스페이스, 사용자별 경로 | 거의 모든 저장 기능(1, 10, 12, 14~17, 20, 22, 28, 39, 46, 51) | `deeptutor/multi_user/context.py:22 get_current_user`, `deeptutor/services/workspace/context.py:91 workspace_context`(`:22 WorkspaceScope`), `deeptutor/multi_user/paths.py:102 scope_for_user`, `deeptutor/services/path_service.py` | `capabilities/scope-contract.md` · 미작성 | 코드 확인(함수 정의 위치) / 격리 규칙 본문 미탐색 |
| S5. 설정·모델 카탈로그(`data/user/settings/*.json`, 서비스별 프로필) | 40~45, 2, 5, 9 | `deeptutor/services/config/runtime_settings.py:509 RuntimeSettingsService`, `deeptutor/services/config/model_catalog.py:254 ModelCatalogService`, `deeptutor/services/llm/config.py:235 get_llm_config` | `capabilities/settings-contract.md` · 미작성 | 코드 확인(클래스 위치) / 스키마 미탐색 |
| S6. RAG 파이프라인 계약과 KB 종류 판별(`rag_provider`, 연결형 `type`) | 17, 18, 24, 5, 22, 23 | `deeptutor/services/rag/pipelines/base.py:17 RAGPipeline`, `deeptutor/services/rag/factory.py:49 KNOWN_PROVIDERS`, `deeptutor/knowledge/kb_types.py` | `capabilities/rag-contract.md` · 미작성 | 코드 확인(프로토콜 전문·공급자 상수) |
| S7. 루프 확장 계약: `LoopExtension`·`KnowledgeCapability`·`PromptBlock`·`END_LOOP` | 7, 8, 11, 13, 20, 24, 25, 30, 31, 38, 40 | `deeptutor/capabilities/protocol.py:38 LoopExtension`(`:138 KnowledgeCapability`, `:31 PromptBlock`), `deeptutor/capabilities/registry.py:49 BUILTIN_LOOP_CAPABILITY_SPECS` | `capabilities/loop-extension-contract.md` · 미작성 | 코드 확인(클래스 위치·등록 14개) / 훅 호출 순서 미탐색 |
| S8. 세션 저장소 프로토콜과 스키마(세션·메시지·턴·턴 이벤트·문제 노트북) | 1, 4, 12, 32 | `deeptutor/services/session/protocol.py:150 SessionStoreProtocol`, `deeptutor/services/session/sqlite_store.py:254 SQLiteSessionStore`(`CREATE TABLE` `:290`~), `deeptutor/services/session/__init__.py:15 get_session_store` | `capabilities/session-store-contract.md` · 미작성 | 코드 확인(프로토콜 클래스·테이블 생성문·PocketBase 교체 분기) / 4,720줄 본문 미탐색 |

**집계**: 기능 지도 53행 = 핵심 33 + 부속 20, 공유 계약 8(기능 개수에 넣지 않음). 핵심/부속 구분은 이 세션의 제안이다.

**대조한 범위와 미탐색 영역**
- 대조: `README.md`의 Key Features·Explore(Chat·Partner·My Agents·Co-Writer·Book·Knowledge Center·Learning Space·Memory·Settings·Multi-User)·CLI 명령표, `AGENTS.md`의 아키텍처·캡빌리티·도구 표, `pyproject.toml`의 스크립트·extras·entry point, `api/main.py`의 `include_router` 54개(라우터 모듈 45개, 데코레이터 674개는 정적 grep), 턴 캡빌리티 11·루프 확장 14·도구 101, RAG 공급자 9, LLM 제공자 45, 어댑터 디렉터리(임베딩 7·검색 14·음성 6·이미지 3·영상 2·파싱 7·서브에이전트 11·채널 16), `web/app`의 페이지 62·route handler 2, `deeptutor_cli`의 명령 이름.
- 문서와 구현의 차이(구현이 사실):
  1. `AGENTS.md`는 "사용자 토글 도구 7개" 표를 싣지만 `USER_TOGGLEABLE_TOOL_NAMES`는 8개(`zotero_search` 포함, `deeptutor/tools/builtin/__init__.py:2148`)이고 README는 8개를 적는다. 코드 확인.
  2. `AGENTS.md`의 캡빌리티 표는 10개이고 `BUILTIN_CAPABILITY_CLASSES`는 11개(`audio_overview` 포함, `deeptutor/runtime/bootstrap/builtin_capabilities.py:35`). README `deeptutor run` 표는 11개를 적는다. 코드 확인.
  3. `AGENTS.md`는 `visualize`를 "analyzing → generating → reviewing" 파이프라인으로 표기하지만, 실제 텍스트 경로는 `AgenticChatPipeline`+`submit_visualization` 도구(`deeptutor/agents/visualize/capability.py:141~188`)이고 매니페스트 `stages`에 옛 단계 이름이 남아 있다. 옛 `VisualizePipeline`은 비테스트 코드에서 북의 interactive 블록만 쓴다(`deeptutor/book/blocks/interactive.py:69`). 코드 확인.
  4. `AGENTS.md`는 CLI·WebSocket·SDK 모두가 턴 서비스로 들어간다고 쓰고 이는 맞다(WS `deeptutor/api/routers/unified_ws.py:222`, CLI→`DeepTutorApp.start_turn`→`container.turns.start_turn` `deeptutor/app/facade.py:131~156`). 그러나 `deeptutor/capabilities/mastery/capability.py`의 주석은 "CLI와 SDK 호출은 `TurnRuntimeManager`를 우회한다"고 적어 사실과 다르다(오래된 주석으로 추론). 실제 우회 경로는 Partner(`deeptutor/services/partners/runtime.py:541`)다. 코드 확인.
  5. `docs/guides/tools-surface.md`는 기준을 "origin/dev @ fe003ddce (v1.6.12)"로 적고 도구 이름 94개·내장 21개·`BUILTIN_TOOL_NAMES:207` 같은 줄 번호를 인용하지만, 이 SHA(v1.6.15)의 `BUILTIN_TOOL_SPECS`는 101개 이름이고 `BUILTIN_TOOL_NAMES`는 `deeptutor/tools/builtin_specs.py:224`다. 이 문서는 후보로만 읽어야 한다. 코드 확인(AST 집계).
  6. README의 채널 나열에는 `email`이 없고 코드에는 `deeptutor/partners/channels/email.py`(IMAP 폴링+SMTP 답신)가 있다. `weixin`은 README에서 QR 로그인으로만 언급된다. 코드 확인.
  7. Whisper 연습방은 UI만 포함되고 두 캡빌리티가 레포 밖이다(52행). README는 이를 언급하지 않는다(`README.md`에서 `whisper`를 grep한 결과 0건).
  8. README의 "Memory is tracked across chat, notebook, quiz, kb, book, partner, cowriter surfaces"는 `Surface` 7개와 일치하지만, 자동으로 L1 trace 이벤트를 쓰는 코드는 grep 상 `write_memory`(chat)·파트너 기억 도구·RAG 검색(kb) 3곳이고 나머지 표면은 스냅샷 어댑터가 저장소를 읽어 만든다. L2·L3를 LLM으로 갱신하는 실행의 호출처도 `deeptutor/api/routers/memory.py`뿐이다. README가 자동 통합을 말하는지는 미확인(README는 예산을 "Settings → Memory에서 조정"한다고만 적음). 코드 확인(grep)·해석은 추론.
- 미탐색:
  - 테스트 전부(`tests/` 881개, `web/tests/` 13개 e2e, `deeptutor/learning/tests/` 27개, `.github/tdd/*.md`)와 CI 설정, `CONTRIBUTING`·`CODE_OF_CONDUCT`·이슈/PR 템플릿, 번역, `assets/`(173개 이미지).
  - 대형 본문: `deeptutor/learning/service.py`(3,355줄), `deeptutor/capabilities/mastery/tools.py`(3,816줄), `deeptutor/agents/research/pipeline.py`(3,275줄), `deeptutor/services/session/sqlite_store.py`(4,720줄), `deeptutor/knowledge/manager.py`(2,570줄), `deeptutor/book/engine.py`(2,182줄), `deeptutor/agents/loop/agent_loop.py` 후반, `deeptutor/runtime/launcher.py`(1,715줄), `deeptutor/services/config/runtime_settings.py`(1,684줄)의 세부 분기.
  - 프롬프트 파일(`**/prompts/**` 수백 개)과 `tools/prompting/hints/`, `web/locales`, `web/components` 본문, `docs-for-user/` 14개(사용자 가이드는 후보로도 읽지 않음), `docs/verification/*`.
  - 외부 시스템 동작: 모델 제공자 API, EduHub/ClawHub 서버(`eduhub.deeptutor.info`), Invidious, YouTube·Bilibili 자막, IM 플랫폼, IMA·WeKnora·Kiwix·LightRAG Server·MarginNote4 애드온, PocketBase·Redis, Manim·MinerU·Docling 같은 선택 의존성. 모두 `미확인`.
  - README의 정량·운영 주장(예: 문서 사이트 24시간 재동기화, 테마 4종, 릴리스 이력)은 대조하지 않았다. `미확인`.
  - 하위 LICENSE가 아닌 `package-lock.json`·Python 의존성의 라이선스(`pyproject.toml` 의존성 목록은 읽었지만 각 패키지 라이선스는 미확인).


### 스킬화 관점 지도 (2026-10-27 추가)

분석 목적이 "Claude Code 안의 가벼운 학습 스킬"로 바뀌어, 53행 제품 지도를 **학습 스킬이 하는 일 7가지**에 다시 대 보았다. 위 53행 지도는 코드 기준 제품 지도로 그대로 두고, 이 표는 "이 레포에서 무엇을 가져올 수 있나"만 본다. 승인된 스펙 범위가 아니라 **재구성 제안**이다.

| 학습 스킬의 일 | 이 레포가 하는 방법 | 가져올 만한 것 (근거 위치) | 원 지도 행 | 검증 수준 |
|---|---|---|---|---|
| 1. 현재 수준 진단 | 얕다. 고정 진단 퀴즈 생성 프롬프트(5~8문항, 쉬운 것→어려운 것). 경로 정책은 건드리지 않은 목표에 `probe`(가르치기 전 테스트아웃)를 지시한다 | 거의 없음. 진단은 learnharness 프로버가 훨씬 정교하다 | 10 | 코드 확인(`learning/prompts/en.yaml` `diagnostic`, `learning/policy.py` `NextStep` 독스트링) |
| 2. 학습 계획 | 주제+목표+사용자 자료 → 모듈 3~8개(상한 20), 모듈당 목표 2~7개, 목표 유형 4종(memory/concept/procedure/design), 선행 `prerequisite_ids`. 모듈마다 "끝나면 할 수 있는 것" 한 문장. 사용자 문서는 하나도 빠짐없이 어느 모듈에 배정 | 모듈·목표 구조와 "능력으로 쓴 목표 문장" 규칙, 유형 4종(복습 간격이 유형에 묶임) | 10, 17 | 코드 확인(`learning/topic_generation.py` 상수, `learning/models.py` `KnowledgePoint`, `learning/prompts/en.yaml` `topic`) |
| 3. 수준별 설명 | 얕다. `explain` 프롬프트는 비유 → 정의 → 예 1~2개 → 흔한 오해의 고정 순서이고 **학습자 수준을 입력으로 받지 않는다**(`{knowledge_point}`만). 수준 적응은 "무엇을 다루나"(게이트·다음 목표)에서만 일어난다 | 거의 없음(고정 템플릿). 설명 방법은 learnharness 교사 독트린이 낫다 | 11 | 코드 확인(`en.yaml` `explain`); 튜터 루프 본문 `capabilities/mastery/loop.py`(901줄)는 미읽음 |
| 4. 맞춤 자료 수집 | 사용자가 고른 자료(챕터 단위 최대 24,000자, 책 24만, 총 60만자)를 목록(매니페스트)으로 알려 주고 튜터가 `read_source`로 필요할 때만 읽는다. 웹 조사는 딥 리서치·`web_search`가 따로 있다 | 아이디어: "자료 목록은 매번 알리고 본문은 필요할 때 읽는다". 구현은 제품 전용이라 가져올 코드는 없음 | 5, 17, 43 | 코드 확인(`learning/topic_materials.py` 머리 설명·상수). 마스터리 경로가 딥 리서치와 연결되는지는 미확인. **학습자 맞춤으로 자료를 골라 주는 기능은 확인한 범위에 없다**(추론) |
| 5. 학습 추적 | 시도마다 증거 기록(결과·확신도·힌트 수·시각·피드백) `LearningEvidence`, `QuizAttempt`, 오답 `ErrorRecord`(유형 4종: structural/deviation/application/metacognitive). 숙달도 = 최근 5회 가중 정확도(0.5·0.7·0.85·0.95·1.0), 1회면 상한 0.5, 2회면 0.8 | **`compute_mastery` 40줄**: "한 번 맞았다고 숙달이 아니다"를 구현. 오답 유형 4종 분류 | 10 | 코드 확인(`learning/mastery.py` 전문, `learning/models.py`) |
| 6. 지속 관리: 다음에 뭘 할지 | **`next_objective` 우선순위**: 대기 중인 질문 채점 → 복습 기한이 지난 것 → 첫 미숙달 목표 → 완료. 게이트: memory·procedure는 숙달도 ≥0.9, concept·design은 튜터가 `mastery_assess`(파인만식 설명)로 판정. 이미 증명한 목표는 건너뜀 | 우선순위 규칙과 게이트(순수 함수, I/O·LLM 없음) | 10 | 코드 확인(`learning/policy.py` `next_objective`·`is_mastered`·`QUANTITATIVE_GATE` 전문 읽음) |
| 7. 지속 관리: 복습 일정 | 지수 망각 모델. **다음 복습 간격 = 안정도(stability) × (−ln 목표 기억률)**(목표 기억률 기본 0.9, 허용 0.7~0.99). 성공하면 안정도가 늘고 실패하면 간격을 절반 가까이로 줄인다. 유형별 표(memory 0·1·3·7·14·30·60일, concept 3·7·14·30, procedure 3·7·14, design 14·28)는 **첫 간격·옛 상태 채우기·칸 번호 표시에만** 쓰이고 실제 간격은 표 최댓값을 넘을 수 있다. 코드 주석이 "FSRS로 보정한 것이 아님"이라고 적었다. 직전 복습과 너무 가까운 시도(최대 0.25일)는 복습으로 세지 않는 규칙이 있다 | **망각 모델 수식과 "가까운 시도는 복습 아님" 규칙.** 표를 그대로 간격으로 쓰면 틀린다 | 10 → 스펙 `review-scheduler.md` | 코드 확인(`learning/scheduler.py:148-159`·`249-250`, 스펙 작성 중 줄 단위 재확인). 2026-10-27 초안의 "유형별 간격표를 쓴다"는 표현은 틀려서 고쳤다 |

**빠진 일 두 가지(이 레포에서 못 찾음)**: ① 정교한 수준 진단 ② 수준에 맞춘 설명. 둘은 learnharness가 채운다([learnharness 절](../learnharness/overview.md#스킬화-관점-지도-2026-10-27-추가)).

**재구성한 구분** (제품 전체가 아니라 스킬 재료 관점)

| 구분 | 원 지도 행 | 이유 |
|---|---|---|
| 스킬 재료(핵심) | 10 마스터리 엔진 중 `policy.py`·`mastery.py`·`scheduler.py`·`topic_generation.py`·`models.py` | 위 5·6·7번 일의 본체. 합계 약 1,760줄(`policy` 566 + `mastery` 40 + `scheduler` 550 + `topic_generation` 601)이지만 `service.py` 3,355줄·`storage.py` 2,109줄은 제품 저장·서비스 층이라 제외 |
| 참고만 | 11 튜터 루프, 14 3계층 메모리, 15 학습 저널, 4 컨텍스트 조립, 5 딥 리서치, 43 웹 검색 | 세션 사이에 학습자 정보를 잇는 방법과 자료 수집 아이디어. 본문 미확인이 많다 |
| 제외(제품 기능) | 1~3, 6~9, 12~13, 16~53 | 서버·웹 UI·RAG·멀티유저·파트너·채널 등. Claude Code가 이미 하는 일(턴 관리·도구·파일 읽기)이거나 스킬이 필요로 하지 않는다(추론) |

**이 레포를 스킬 재료로 읽을 때의 주의**
- 스케줄러와 게이트는 순수 로직이라 "상태 파일 한 개 + 짧은 함수"로 옮길 수 있다는 것은 **추론**이다. 모델 클래스(pydantic) 의존을 걷어내는 비용은 확인하지 않았다.
- 설명·진단 프롬프트가 얕아서 이 레포에서 "가르치는 방법"은 얻기 어렵다.
- 라이선스는 Apache-2.0(1절). 코드를 옮기려면 NOTICE·하위 라이선스 확인이 필요하다.


### 대표 흐름: 시도 하나가 다음 할 일을 정하기까지 (스펙 2개를 잇는 글, 2026-10-27)

1. 튜터가 지식점 하나에 문제를 내면 정답 키가 든 `PendingQuestion`이 서버 쪽에 저장된다(`mastery-engine.md` R-17). 이 대기 질문이 있는 동안 `next_objective`는 항상 "채점"을 돌려준다(R-07).
2. 학습자 답이 오면 결정론적 채점 또는 의미 채점으로 정오를 정하고 시도와 증거를 쌓는다. 오답이면 오류 기록을 만들고, 개념·설계형은 튜터의 질적 판정(`record_qualitative`)으로 게이트를 정한다(R-09~R-14).
3. 숙달도는 같은 지식점의 취소되지 않은 독립 시도를 추가 순서대로 읽어 최근 5회 가중 정확도로 다시 계산한다(1회면 상한 0.5, 2회면 0.8, partial은 0.5). 이 숫자와 유형별 게이트(memory·procedure 0.9)로 "숙달"이 정해진다.
4. 같은 증거로 `schedule_review`가 반복 상태를 갱신한다. 정답이면 안정도가 늘고 오답이면 줄며, 직전 복습과 너무 가까우면 일정은 그대로 둔다. 다음 복습 시각은 `안정도 × (−ln 목표 기억률)`일 뒤다(`review-scheduler.md` R-07~R-11). 이어서 `build_review_queue`가 모든 상태에서 망각 위험순 큐를 다시 만든다.
5. 다음 요청에서 `next_objective`가 상태에서 매번 계산한다: 대기 질문 → 기한 지난 복습(`due_reviews`) → 첫 미숙달 지식점 → 완료. 단계 포인터는 저장하지 않는다.

**통합 검토 결과 (워크플로 4장 5번)**: ① 승인 행(10)을 두 스펙으로 나눴고 경로 생성(`topic_generation.py`)은 `미작성` ② 시각 단위·증거 필드·`RepetitionState` 의미가 두 스펙에서 같다 ③ 모든 C-ID(재구현 검증 반영 후 49건)가 기준 SHA에 존재하고 `depends`는 `review-scheduler → mastery-engine` 한 방향 ④ 위 흐름이 이어진다. 두 스펙은 `ready`다: `mastery-engine`의 R-07 미결정(`prerequisite_ids` 강제 여부)은 R-21로 해소(진행을 막지 않음, 모든 사용처 열거)했다.

### 재구현 검증 결과 (2026-10-27, 워크플로 4장 6번)

**원본 순수 모듈 실행(수락 사례)**: 원본의 순수 모듈 7개를 기준 SHA에서 꺼내 임시 폴더에 복사해 호출했다([`run_pure.py`](../../artifacts/DeepTutor/mastery-demos/run_pure.py) 40건, [`run_pure2.py`](../../artifacts/DeepTutor/mastery-demos/run_pure2.py) 33건). 허용오차 ±0.001로 모두 통과했다. 처음에는 허용오차를 0.01로 넉넉히 잡아 스펙의 수치 오류(`28.475`→실제 `28.4737`, `60.902`→`60.8995`)를 가렸다. 재구현자가 지적해 허용오차를 스펙이 말한 ±0.001로 조이고 스펙 수치를 고쳤다. 실행하지 못한 것: `service.py`·SQLite 저장소 경로의 사례(mastery-engine T-04 시도 필터링, T-05, T-15~T-21, T-25~T-28, 그리고 이번에 추가된 T-29~T-46 전부).

**독립 재구현**: 스펙 1부와 C-ID만 받은 에이전트가 Python 3(표준 라이브러리, pydantic 없이, SQLite 대신 메모리 저장소)로 두 스펙의 전 R-ID를 구현해 51개 테스트가 통과했다([RESULT.md](../../artifacts/DeepTutor/reimplementation/RESULT.md)).

**원본과 같은 입력으로 비교**([`diff_test.py`](../../artifacts/DeepTutor/mastery-demos/diff_test.py), 출력 [`diff_test.out`](../../artifacts/DeepTutor/mastery-demos/diff_test.out), 고정 시드): `compute_mastery` 2,000, `grade_answer` 231, 초기 상태 400, `schedule_review` 1,822, `retrievability` 1,822, `replay` 400, `forgetting_risk` 800, `next_objective` 600사례에서 **불일치 0건**. 이 비교가 불일치를 잡아내는지 확인하려고 재구현 복사본에 변이를 넣었다(숙달도 가중치, 연체 가산 상한, 같은 세션 창). 처음 비교는 같은 세션 창 0.25→0.30 변이를 못 잡았고(시간 간격 후보가 경계 사이를 건드리지 않음), 간격 후보를 늘린 뒤에는 잡혔다.

**비교하지 않은 것**: 영수증·저장소·`evidence_id`·`register_question` 등 `service.py` 경로, `review_reason` 문장과 `get_due_tasks`(후자 둘은 원본 실행으로만 확인), `next_objective`의 `reason` 문구와 `pending_question` 투영 필드. 이 부분은 스펙 보강 뒤 재구현을 다시 돌리지 않았다(두 스펙 frontmatter의 "재검증 필요").

**재구현자 주장 중 코드와 달라 채택하지 않은 것**: 대기 질문 공개 투영 필드, `awaiting_input` 전이 경로가 없다는 주장(`mark_question_awaiting`이 설정), 영수증 최소 dict. **재구현자가 옳아서 스펙을 고친 것**: 수치 오류, `evidence_id` 생성식(`uuid5`), `get_due_tasks` 필터, R-22 검사 순서, 예외 계층, 시각 과제 증명 조건(코드는 `hints_used`만 본다, 독스트링은 "Independent"라고 썼으나 다름).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

archify로 도출한 주요 구조도(필수)입니다. 실행 흐름도는 이번 세션에서 그리지 않았다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 웹·CLI·Partner → 턴 서비스·엔진 → 캡빌리티·루프·도구 → 도메인 엔진 → 로컬 저장소, 모델 서비스 |

검증 구분 (2026-10-25, 각각 별개의 주장이다):
- **산출물 검증(deterministic)**: `archify deliver architecture … --quality showcase --repo-root repos/DeepTutor` 통과. 산출물 검사 9개 모두 통과, 구성 오류 0·경고 0, `--repo-root`로 `sources` 35개 참조(경로와 줄 번호)가 기준 SHA의 소스에 맞는지 검증됨(`evidence.verified: true`). 명세 sha256 `6e66d48d…`, HTML sha256 `b7dcfdf9…`. 이것은 파일·기하 검사이며 브라우저 실행이나 시각 검토가 아니다.
- **브라우저 확인(automated-browser)**: `archify visual-check`(Chrome) 통과. 1440×900·1600×1000·1920×1080·2048×1320 light에서 가로·세로 넘침 없음, 노드 글자 투영 크기 최소 8.45px(1440 기준, 기준 6px), 밝은/어두운 스크린샷 4장 생성. 부산물은 `ai-learning/artifacts/DeepTutor/structure-visual-check/`. receipt는 `visualReview: "pending"`을 기록하고 있다.
- **시각 검토(perceptual)**: 1440×900 light 스크린샷 한 장만 이미지로 직접 보았다(노드·간선·카드가 겹치지 않고 읽힘). dark와 2048×1320은 보지 않았고 자동 측정만 있다. 사람의 검토는 받지 않았다.

### 그림 해설
그림을 열지 않고 이 글만 읽어도 구조와 흐름이 이해되도록 쓴다.

**읽는 순서**
1. 왼쪽 위 `웹 앱` → `FastAPI 입구` → `턴 서비스` → `턴 엔진` → 세로로 긴 `캡빌리티·루프·도구`가 한 줄로 이어진다(대화 한 번이 실행되는 주 경로).
2. 왼쪽 가운데 `CLI`는 `FastAPI`를 거치지 않고 같은 프로세스 안에서 `턴 서비스`로 들어간다(위로 올라가는 선, 라벨 `in-process`). 왼쪽 아래 `Partners·IM`은 `턴 서비스`를 건너뛰고 `턴 엔진`으로 직접 들어간다(라벨 `turns 우회`).
3. `캡빌리티·루프·도구`에서 오른쪽 다섯 개 묶음(지식베이스·RAG, 마스터리 엔진, 읽기·북·집필, 메모리·저널, 확장 연결)으로 갈라지고, 아래의 `모델 서비스`로 LLM 호출이 간다. 네 묶음은 맨 오른쪽 `로컬 저장소`로 읽고 쓴다.

**구조도: 모듈별 역할**
| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 웹 앱 | Next.js 프론트. `/api`·`/ws` 요청을 백엔드로 재작성하고 턴을 WebSocket으로 보낸다 | 브라우저 요청 → 백엔드 REST·WS, 턴 이벤트 수신 | `web/proxy.ts`, `web/features/chat/transport/socket.ts:21 new WebSocket` | 코드 확인(재작성 호출·소켓 생성 줄) / 클라이언트 본문 미탐색 |
| CLI | Typer 명령. `run`이 `DeepTutorApp`으로 턴을 시작해 이벤트를 렌더(rich 또는 NDJSON) | argv → `TurnRequest` → `start_turn`, 이벤트 스트림 구독 | `deeptutor_cli/main.py:83 run_capability`, `deeptutor/app/facade.py:131 DeepTutorApp.start_turn` | 코드 확인(호출 연결) |
| FastAPI 입구 | 라우터 45개를 인증 의존성과 함께 장착하고 통합 WebSocket `/ws`를 연다. 도메인 REST(KB·마스터리·북·읽기·메모리·설정 등)를 처리 | HTTP/WS 명령 → `container.turns.start_turn`·구독·취소, REST → 도메인 엔진 | `deeptutor/api/main.py:800 app.include_router(unified_ws`, `deeptutor/api/routers/unified_ws.py:222 turns.start_turn` | 코드 확인(장착·WS→start_turn) / REST→도메인 직접 호출은 라우터별 grep 개수로만 확인 |
| Partners·IM | 파트너 러너가 인바운드 메시지를 일반 턴으로 실행하고 채널 16종이 IM과 주고받음 | IM 메시지 → `UnifiedContext` → `get_turn_engine().execute`, 이벤트 → 채널 발신 | `deeptutor/services/partners/runtime.py:541 get_turn_engine().execute`, `deeptutor/partners/channels/registry.py:64 discover_all` | 코드 확인(엔진 호출 줄·발견 함수) / 채널 외부 동작 미확인 |
| 턴 서비스 | 요청 검증·세션 저장·태스크 시작·이벤트 순번·재구독·취소를 맡는다 | `TurnRequest` → 저장된 턴, `StreamEvent` 재생 | `deeptutor/app/service.py:21 TurnApplicationService`, `deeptutor/services/session/turns/request_preparer.py:902 create_task(self._run_turn`, `deeptutor/services/session/turns/executor.py:1031 turn_engine.execute` | 코드 확인(태스크 생성·엔진 호출 줄) / 세션 DB 쓰기 세부 미탐색 |
| 턴 엔진 | `ChatOrchestrator`가 캡빌리티를 레지스트리에서 찾아 `run`을 실행하고 StreamBus·완료 이벤트를 관리한다. 알 수 없는 캡빌리티는 오류 이벤트로 끝낸다 | `UnifiedContext` → `StreamEvent` 스트림 | `deeptutor/runtime/turn_engine.py:11 TurnEngine`, `deeptutor/runtime/orchestrator.py:53 ChatOrchestrator`, `deeptutor/runtime/registry/capability_registry.py:57 CapabilityRegistry` | 코드 확인(`handle` 앞부분·`capability.run` 호출) |
| 캡빌리티·루프·도구 | 턴 캡빌리티 11, 루프 확장 14, 도구 101. 채팅 에이전트 루프(`AgentLoop`)와 딥 모드 파이프라인이 여기서 돈다 | 컨텍스트 → LLM 호출·도구 호출·최종 답. 도구는 KB·마스터리·읽기·메모리·확장 호출 | `deeptutor/runtime/bootstrap/builtin_capabilities.py:35 BUILTIN_CAPABILITY_CLASSES`, `deeptutor/capabilities/registry.py:49 BUILTIN_LOOP_CAPABILITY_SPECS`, `deeptutor/tools/builtin_specs.py:46 BUILTIN_TOOL_SPECS`, `deeptutor/agents/loop/agent_loop.py:300 AgentLoop` | 코드 확인(등록부 개수·`AgentLoop.run` 시작부) / 루프 라운드 내부 미탐색 |
| 모델 서비스 | LLM 제공자 45 스펙·임베딩·검색 등. 채팅 루프 파이프라인이 `get_llm_config`로 설정을 읽고 런타임 클라이언트로 호출 | 프롬프트·도구 스키마 → 토큰 스트림·도구 호출 | `deeptutor/services/provider_registry.py:192 PROVIDERS`, `deeptutor/services/llm/provider_factory.py:151 get_runtime_provider`, `deeptutor/agents/loop/pipeline.py:245 get_llm_config` | 코드 확인(스펙 집계·호출처 import) / 외부 API 미확인 |
| 지식베이스·RAG | KB 관리·색인과 RAG 엔진 9종·파서 7종. `rag` 도구가 `RAGService.search`로 호출 | 질의 → 근거 구절·출처 | `deeptutor/knowledge/manager.py:325 KnowledgeBaseManager`, `deeptutor/services/rag/factory.py:49 KNOWN_PROVIDERS`, `deeptutor/tools/rag_tool.py:12 RAGService` | 코드 확인(import·상수) / 엔진 본문 미탐색 |
| 마스터리 엔진 | 숙달도·게이트·복습 일정을 순수 정책+SQLite 저장소로 관리. 튜터 도구가 부른다 | 도구 호출 → 진행 상태 갱신·다음 목표 | `deeptutor/learning/service.py:328 LearningService`, `deeptutor/learning/policy.py:266 next_objective`, `deeptutor/capabilities/mastery/tools.py:55 deeptutor.learning` | 코드 확인(클래스·함수 위치, 도구가 `deeptutor.learning` 모델을 import) / 서비스 본문 미탐색 |
| 읽기·북·집필 | 읽기 자료 저장·주석(읽기 도구가 `deeptutor.reading` 호출), 북 엔진, 공동집필 편집 에이전트 | 도구·라우터 호출 → 자료·페이지·문서 | `deeptutor/reading/store.py:161 ReadingStore`, `deeptutor/book/engine.py:317 BookEngine`, `deeptutor/co_writer/edit_agent.py:102 EditAgent` | 코드 확인(클래스 위치·읽기 도구의 import) / 북·집필은 라우터가 직접 부르는 경로(그림에 간선 없음) |
| 메모리·저널 | 3계층 메모리와 학습 저널. 도구가 쓰고, 턴 실행기가 L3·저널을 컨텍스트에 주입 | `write_memory`·`learning_update` → 파일 기록, 컨텍스트 주입 | `deeptutor/services/memory/store.py:69 MemoryStore`, `deeptutor/services/learning_journal/store.py:58 LearningJournalStore`, `deeptutor/services/session/turns/executor.py:572 read_l3_concat` | 코드 확인(주입 호출 줄·도구) |
| 확장 연결 | MCP 연결 관리자, 서브에이전트 레지스트리, 샌드박스 실행 | 도구 호출 → 외부 MCP 서버·에이전트 CLI·격리 실행 | `deeptutor/services/mcp/manager.py:235 MCPConnectionManager`, `deeptutor/services/subagent/registry.py:29 _BACKENDS`, `deeptutor/services/sandbox/service.py:33 SandboxService` | 코드 확인(클래스·등록부) / 외부 시스템 미확인 |
| 로컬 저장소 | `data/` 아래 SQLite·마크다운·JSON. 세션 DB, 마스터리 DB, 읽기 카탈로그, 메모리 | 읽기·쓰기. 세션 저장소는 PocketBase로 교체 가능 | `deeptutor/services/path_service.py`(배치 주석), `deeptutor/services/session/sqlite_store.py:254 SQLiteSessionStore`, `deeptutor/learning/storage.py:395 LearningStore`, `deeptutor/reading/catalog_store.py:54 ReadingCatalogStore` | 코드 확인(저장소 클래스·테이블 생성문) / 파일 레이아웃 전체는 주석 기준 |

**그림에서 뺀 것과 이유**
- 간선 일부는 레이아웃 때문에 생략했다(없다는 뜻이 아니다). ① FastAPI 라우터가 도메인 엔진(KB·마스터리·북·읽기·메모리)을 직접 부르는 경로(`deeptutor/api/routers/book.py`는 `get_book_engine`을 5곳, `deeptutor/api/routers/mastery_path.py`는 `LearningService/LearningStore`를 37곳, `deeptutor/api/routers/knowledge.py`는 `KnowledgeBaseManager`를 9곳에서 쓴다는 grep 개수로 확인). ② 턴 서비스가 세션 DB(`chat_history.db`)에 쓰는 선. ③ 확장 연결→저장소, KB의 임베딩·검색 호출(`모델 서비스`는 캡빌리티에서 오는 선만 그림). 카드의 "그림에 없는 것"에 같은 내용을 적었다.
- 웹 UI 내부(62 페이지·컴포넌트), 플러그인 플랫폼·MarginNote 브리지·스킬 허브·cron·태스크 보드·런처·Docker(지도 24·25·33·38·49~51행), 실행 흐름도는 넣지 않았다.
- 노드 수는 14개로 showcase 권장(12개)을 넘었지만 검증은 통과했다.

**미확인 영역**
- 턴 실행 중 `ChatOrchestrator`가 만드는 StreamBus와 이벤트가 `turn_events`·코디네이터로 영속되는 순서(코드는 읽지 않음).
- 루프 확장 14개가 `AgentLoop`의 어느 훅에서 도구·프롬프트를 얹는지(`deeptutor/capabilities/protocol.py`의 훅 호출 순서).
- 도구가 장착되는 규칙(`compose_enabled_tools` 본문)과 `docs/guides/tools-surface.md`의 서술은 일치하는지.
- 웹 클라이언트가 이벤트 순번·재연결을 처리하는 정확한 규칙(`reconnect-policy.ts`, `command-delivery.ts`).
- 외부 서비스(모델 제공자, 허브, 자막, IM, 선택 의존성) 동작 전부.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸
