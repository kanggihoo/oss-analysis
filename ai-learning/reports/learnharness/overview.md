---
sha: "b277ee3e0fa24249c1b2d0f9b7fd6ed485f484b9"
created: 2026-10-25
updated: 2026-10-27
---

# learnharness Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/amosblomqvist/learnharness`
- **기준 SHA**: `b277ee3e` (2026-10-25, `main`), 태그 `v0.3.7`, `package.json` version 0.3.7
- **작업트리 상태**: Clean (`ai-learning/artifacts/learnharness/repo-metadata.txt`, `git status` 변경 없음)
- **분석 목적**: 학습 / 설계 참고 — **Claude Code 같은 에이전트 안에서 쓰는 가벼운 학습 스킬**을 만들기 위한 재료 찾기(2026-10-27 사용자 재정의). 스킬이 할 일: 주제 학습, 학습한 것 추적, 맞춤 자료 수집, 수준별 설명, 지속 관리. 복잡하게 만들지 않는 것이 조건이다. 그래서 2절 "스킬화 관점 지도"를 기능 지도 뒤에 추가했다(제품 전체 지도는 그대로 둔다). (이전 목적: 학습 / 설계 참고 — AI와 함께 배우는 학습 앱의 기능·구조 파악. 특히 **이해도 측정 → 의존 관계 계획 → 가르치기 → 연습** 흐름, **지식 그래프**, **에이전트 도구 구성**. 이번 세션은 기능 지도와 구조도까지.)
- **라이선스**: GNU Affero General Public License v3 (본문 첫 줄 "GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007") — `LICENSE`(661줄, 표준 AGPL 본문과 말미 "How to Apply" 안내만 있고 저작권자 줄은 없다). `skills/learnharness/LICENSE`도 같은 AGPL-3.0 본문이며 `cmp`로 루트 `LICENSE`와 바이트 단위로 같다. `package.json`의 `license` 필드는 `AGPL-3.0-only`, `skills/learnharness/SKILL.md` frontmatter의 `license`도 `AGPL-3.0-only`. 그 밖의 LICENSE 파일은 추적 파일에 없다(`git ls-files`). 코드 확인. (README 마지막 절은 "앱은 영원히 무료… 돈을 받는다면 편의(관리형 키·호스팅)에 대해서일 것"이라고 적었는데, 이는 라이선스 조건이 아니라 운영자의 약속이다 — 미확인.)
- **언어/규모**: TypeScript(ESM, Next.js 16 App Router + React 19) + Electron 44 셸(CommonJS `.cjs`) + Python 스킬 스크립트. 추적 파일 533개(tests 185 / src 135 / components 98 / app 36 / docs 18 / 루트 15 / scripts 11 / build 11 / electron 10 / skills 6 / public 4 / .github 3 / lib 1). 소스 약 5.7만 줄(`src app components electron scripts skills lib`의 `.ts/.tsx/.cjs/.mjs/.py/.md/.js` 합). LLM 엔진은 외부 SDK `@earendil-works/pi-ai`·`pi-agent-core` 1.4.0(`package.json`) — 이 레포 밖. 코드 확인(`package.json`, `git ls-files`).
- **분석 대상 제품**: 루트 패키지 `learnharness`(`private: true`, `main: electron/main.cjs`). 배포 단위는 (1) Next.js 웹 앱(`next build` → `output: "standalone"`, `next.config.ts`), (2) Electron 데스크톱 앱(`electron-builder.yml`: macOS arm64 DMG/ZIP, Windows x64 NSIS, Linux AppImage/deb), (3) 에이전트 스킬 `skills/learnharness`(Python 읽기 전용 리더). 중첩 패키지 매니페스트는 없다.
- **런타임 모양**: 학습 데이터는 `LH_DATA_DIR`(없으면 레포 `data/`) 아래 평문 JSON/JSONL(`config.ts` `PATHS`, `LEDGER_FILES`). 데스크톱에서는 Electron이 Next 스탠드얼론 서버를 자식 프로세스로 띄우고 키 파일(`auth.json`)과 데이터 디렉터리를 `userData`에 둔다(`electron/main.cjs` 앞부분 주석). 코드 확인.
- **스펙 범위**: 2026-10-27 승인(사용자 "1,2 진행", 2절 "스킬화 관점 지도" 기준). 승인 행: 2 이해도 측정, 3 의존 관계 계획, 4 가르치기, 5 연습 세션. 선행 공유 계약 S2(질문·답변)는 `capabilities/question-answer-contract.md`로 쓰고, 행 6(학습자 입력 채널)의 확신도·사고 필드는 여기에 흡수한다. 행 1·7·15·16·18은 각 스펙 1.2에 경계만 쓰고 `미작성`으로 둔다. 제외: 부속 10행 전부(이유: 사용자 제외, 별도 답 없음) · 나머지 핵심 행(이유: 이번 승인에 없음)

---

## 2. 프로젝트 개요

README 첫 줄의 주장: "An agent harness for learning." 학습자의 현재 이해도에서 목표까지 에이전트가 **측정(Measure) → 계획(Plan) → 가르치기(Teach) → 연습(Practice)** 순서로 이끌고, 가르친 내용은 **지식 그래프**(명제와 추론 사슬)로 세션을 넘어 쌓인다(`README.md` "How it works", "Knowledge that carries forward"). 코드 대조는 아래 지도의 진입점에서 했다.

코드로 확인한 핵심 설계 여섯 가지:
1. **같은 대화 기록, 다른 에이전트**: 세션은 하나의 대화 기록(`data/chats/<id>.json`)이고, 매 요청마다 기록에서 에이전트를 새로 만든다. 기록에 `probe_done` 도구 호출이 있으면 교사(teacher), 없으면 프로버(prober)를 만든다. `kind: "practice"` 세션이면 연습 에이전트다(`src/server/chat-handler.ts` `handleChatInput` 343~452줄, `src/core/native-messages.ts` `hasProbeDone`). 코드 확인.
2. **측정은 질문 도구와 평가 문서로 끝난다**: 프로버의 도구는 `probe`(객관식)/`recall`(자유 서술)·`ask_user_question`·학습자 파일 읽기·`research`·`pdf`·(설정으로 열리면) 그래프 지도 읽기·`probe_done`이다. 학습자 답에는 확신도(0~100)와 사고 필드 글이 붙고, 프로버는 가닥(strand)마다 "바닥(확실히 아는 것)과 천장(막히는 곳)"을 `probe_done`의 입력으로 적는다(`src/agent/tools.ts` `createProberTools`, `src/agent/tools/probe.ts` `probeDoneTool`, `src/agent/prompts/prober/10-probe-doctrine.md`, `shared/25-confidence.md`). 이 평가는 **대화 기록 안에만** 있고 그래프에는 들어가지 않는다. 코드 확인.
3. **계획은 한 번 쓰는 mermaid 지도**: 교사는 `plan_init`(mermaid `graph` 블록)으로 5~15개 노드의 선행 관계 지도를 쓰고, 이후 질문은 `nodeId`로 노드를 지목한다. 진행 상태(current/visited/upcoming)는 저장하지 않고 대화 기록의 `nodeId` 태그에서 매번 **파생**한다(`src/agent/tools/plan.ts` `planTools`, `src/core/contracts/plan.ts` `derivePlanStatuses`, `src/agent/tools.ts` `teachQuizToolFor`). 코드 확인(도구 설명·시그니처).
4. **질문은 "도구 호출 → 턴 종료 → 학습자 답이 다음 요청"**: 질문 도구의 `execute`는 입력만 검증하고 "질문 제시됨" 자리표시자(`terminate: true`)를 돌려줘 턴을 끝낸다. 학습자의 답은 `POST /api/chat`의 입력 이벤트(`answer`)로 와서 그 호출의 도구 결과로 기록에 붙는다(`src/agent/tool-execute.ts` `questionResult`, `src/core/input-events.ts` 헤더 주석, `src/agent/teacher-agent.ts` `makeQuestionStopper`). 코드 확인.
5. **지식 그래프는 교사의 설명문만 읽어 만든다**: 추출기 LLM이 보는 입력은 **교사 텍스트 블록뿐**(학습자 메시지·사고 필드·도구 호출·퀴즈 제외)이고, 결과는 명제와 "함께 결론을 함의하는 전제들"의 사슬이다. 감사기 LLM이 기존 노드와 같은 명제인지 판정하고, 결정론적 병합기가 원장에 추가한다(`src/agent/subagents/extraction.ts` `proseView`·`createExtractionPipeline`, `src/core/graph.ts` `mergeFindings`). 그래프에는 이해도 점수가 없다(README 스스로도 "아이디어와 연결을 저장, 능력 평점이 아님"). 코드 확인.
6. **BYOK**: 공장 기본 모델이 없다. 사용자가 모델 슬롯(strong/cheap/vision)과 키를 정해야 하고, 비어 있으면 턴이 503으로 거부된다(`config.ts` 주석, `chat-handler.ts` 185~220줄). 코드 확인.

### 기능 지도

<!--
검증 수준 표기 (이 세션은 지도 단계, 스펙은 R-ID 단위로 다시 붙인다):
- "코드 확인(…)": 괄호 안의 파일·심볼을 직접 읽음.
- "추론": 파일 이름·주석·문서로 판단, 본문은 열지 않음.
- "미확인": 외부 시스템 동작이나 열지 않은 본문.
`파일:줄`은 기준 SHA 기준. 모든 행의 스펙 상태는 미작성(범위 승인 전). 구분: 핵심 / 부속.
-->

> 조사 방식: 서브에이전트 없이 메인 세션(이 작업자)이 `git ls-files` → README·`docs/architecture.md`·`docs/development.md`·`package.json` → 진입점(`chat-handler`, `teacher-agent`, `tools`, 추출 파이프라인, 라우트 30개, Electron 셸, 스킬)을 읽고, 라우트·도구·설정·원장 파일 이름을 등록부 삼아 행을 만들었다. 테스트(185개)·CI·fixture는 열지 않았다. 예외로 연 파일은 아래 "대조한 범위" 끝에 이유와 함께 적었다.

#### A. 수업 흐름 (측정 → 계획 → 가르치기 → 연습)

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 1. 세션 턴 파이프라인 | 학습자 입력 이벤트(`text`/`answer`/`continue`/`thinking`/`next`, 서버 steer) → 모델·키·컴팩션 게이트 → 입력을 기록에 먼저 저장(write-ahead) → 기록으로 에이전트 구성 → 턴을 백그라운드 객체로 실행 → 끝에 기록·사용량 저장, 추출 트리거. 세션당 턴 1개(409), `POST`는 `{ok:true}`만 돌려주고 스트림은 `GET /api/chats/[id]/stream`로 붙는다 | `app/api/chat/route.ts`, `src/server/chat-handler.ts` `handleChatRequest`(146)·`handleChatInput`(175), `src/server/pi/ui-stream.ts` `runPiTurn`(121), `src/server/turn-service.ts` `persistTurn`(50), `turn-liveness.ts` `beginTurn`(44), `turn-runs.ts` | S1, S2, S4, 18 | 핵심 | `capabilities/turn-pipeline.md` · 미작성 | 코드 확인(`handleChatInput` 전체, `persistTurn`) / `runPiTurn` 내부·`record-adapter`는 미확인 |
| 2. 이해도 측정 (프로버) | 목표를 `ask_user_question`으로 구체화 → 가닥(strand)별로 `probe`/`recall` 질문을 이진 탐색(바닥·천장 브래킷) → 확신도·사고 필드로 다음 질문 결정 → `probe_done`(가닥별 평가)로 종료. 질문이 열려 있으면 `probe_done` 거부, 한 번만 호출. 설정이 열리면 `list_sessions`/`list_propositions`로 그래프를 이름만 읽음. 평가는 그래프에 저장하지 않음 | `src/agent/teacher-agent.ts` `createProberAgent`(259), `src/agent/tools.ts` `createProberTools`·`probeQuizTool`·`probeExplainTool`, `src/agent/tools/probe.ts` `probeDoneTool`(48), `src/core/contracts/probe.ts` `probeDoneInputSchema`, `src/agent/tools/graph.ts` `proberGraphTools`(41), `prompts/prober/10-probe-doctrine.md`, `prompts/shared/25-confidence.md` | S2, 6, 7, 8 | 핵심 | [`capabilities/probe-measurement.md`](capabilities/probe-measurement.md) · ready(재구현 검증 완료) | 코드 확인(도구 구성·`probe_done` 전체·그래프 도구 앞부분) / 프롬프트는 앞부분만, 판정 품질은 LLM 몫이라 미확인 |
| 3. 의존 관계 계획 | 프로브 종료 직후 교사가 `plan_init`으로 mermaid 지도(`-->` = "먼저 이해해야 함", 슬러그 id)를 쓰면 파싱·검증해 기록의 `tree`에 저장, 틀리면 다시 호출해 통째로 교체. 학습자는 계획 창에서 지도를 본다. 진행 상태는 저장하지 않고 질문 호출의 `nodeId`에서 파생 | `src/agent/tools/plan.ts` `planTools`(62), `src/agent/tools/mermaid-plan.ts` `parseMermaidPlan`(77), `src/core/plan-tree.ts` `createTree`(112), `src/core/contracts/plan.ts` `derivePlanStatuses`(82), `src/core/plan-blocks.ts`, `components/plan-window.tsx`·`plan-block.tsx` | S1, 2 | 핵심 | [`capabilities/plan-tree.md`](capabilities/plan-tree.md) · ready(재구현 검증 완료) | 코드 확인(도구 설명·시그니처·파생 함수 위치) / DAG 검증 세부·파서 규칙은 추론(`docs/architecture.md` 설명) |
| 4. 가르치기 (교사) | 교사가 계획대로 predict(가르치기 전, 다음 단계 예측) → 설명 → check(가르친 뒤 확인) 사이클을 돌며 `quiz`/`explain`(`nodeId` 필수, 계획에 없으면 거부)로 질문, 틀리면 수리, 필요하면 `research`·`pdf`·`demo`·`visual` 호출. 단계(phase)는 probe → plan(`probe_done` 완료) → teach(첫 `nodeId` 질문 호출)로 파생. `probe_done`이 핸드오프 steer를 큐에 넣어 교사 첫 턴(계획)을 자동으로 깨운다 | `src/agent/teacher-agent.ts` `createTeacherAgent`(269), `src/agent/tools.ts` `createTeacherTools`·`teachQuizToolFor`·`teachExplainToolFor`·`quizMechanics`, `src/core/phases.ts` `phaseAt3Lh`, `src/core/contracts/jobs.ts` `buildProbeHandoffSteer`(432), `prompts/teacher/{05-method,10-planning,20-teaching,28-predictions,30-question-principles,40-jobs,50-demos}.md` | 2, 3, S2, 7, 8, 10 | 핵심 | [`capabilities/teaching-cycle.md`](capabilities/teaching-cycle.md) · ready(재구현 검증 완료) | 코드 확인(도구·phase 주석·nodeId 검증) / 교사 프롬프트는 05·10·28 앞부분만 읽음, 나머지 미확인 |
| 5. 연습 세션 | 홈/새 세션 화면에서 연습 모드로(선택한 명제를 `graphContext`로 함께) 세션 생성 → 첫 턴부터 연습 에이전트(계획·질문 도구 없음). `problem`(진술·모드 recall/discrimination/composition·대상 명제·미리 확정한 `modelSolution`, 턴 종료)과 `conclude`(결과 solved/solvedWithHints/movedOn/surrendered/dismissed·판정·힌트 사다리 R0~R5·실수 유형·재시험 여부)만 사용. 문제가 열려 있으면 새 `problem` 거부, 없으면 `conclude` 거부. 학습자는 사고 필드에 풀이 흔적을 여러 번 제출. 그래프 추출·기록은 하지 않음 | `src/agent/teacher-agent.ts` `createPracticeAgent`(320), `src/agent/tools/practice.ts` `practiceTools`(223)·`problemTool`·`concludeTool`·`createPracticeGate`, `chat-handler.ts` 391~421줄(PRACTICE BRANCH), `src/core/input-events.ts`(`thinking`·`next`), `prompts/practice/{00-base,10-doctrine}.md`, `app/api/chats/route.ts` POST, `components/practice-dock.tsx`·`practice-cards.tsx`·`new-session.tsx` | 15, 16, S1, 6, 7 | 핵심 | [`capabilities/practice-session.md`](capabilities/practice-session.md) · ready(재구현 검증 완료, 선행 15·16은 "명제·연쇄 목록을 받는다"는 경계만 1.2에 씀) | 코드 확인(도구 전체·게이트·핸들러 분기·세션 생성 라우트) / 독트린 본문(이론)은 앞부분만, 생성 UI는 헤더 주석만 |
| 6. 학습자 입력 채널 | 질문 독(선택지·"모르겠음"·Other)에 사고 필드("Your thinking")와 확신도 슬라이더, 읽는 중 사고 필드(`readingThinking`), Esc로 질문 기각(기록에만 쓰고 에이전트를 깨우지 않음), 진행 중인 턴에 끼어드는 메시지(steer 큐), 연습 독. 답 객체는 선택·정오·확신도·사고글을 담음 | `components/question-dock.tsx`, `components/composer.tsx`, `components/session-core.ts`(`POST /api/chat`), `src/core/question-core.ts`(`QuestionAnswerData`, `confidence` 464·492·726줄), `src/core/input-events.ts` `parseChatInput`·`inputAppends`(197), `app/api/chats/[id]/steer/route.ts`, `app/api/chats/[id]/dismiss/route.ts` | S2, 1 | 핵심 | `capabilities/learner-input.md` · 미작성(확신도·사고 필드의 데이터 계약은 [question-answer-contract.md](capabilities/question-answer-contract.md)에 흡수, 질문 독·컴포저 UI는 미작성) | 코드 확인(타입·라우트 주석, 확신도 처리 줄) / 독·컴포저 렌더링 동작은 추론 |
| 7. 프롬프트 조립과 사용자 오버라이드 | 시스템 프롬프트 = 공유 기반(`system-prompt.md`) + 에이전트별 번호 접두 조각(정렬 순) + `shared/` 부록, 연습은 자기 디렉터리 + 선별 공유 조각만. 사용자는 조각 단위로 덮어쓰기 파일을 두고 설정의 스위치로 켠다 | `src/agent/teacher-agent.ts` `composeInstructions`(74), `src/agent/prompt-segments.ts` `effectivePromptSegments`·`listSourceSegments`, `src/store/prompt-overrides.ts`, `src/core/prompt-segments.ts`, `app/api/settings/prompts/route.ts`·`[...segment]/route.ts`, `src/agent/prompts/README.md` | S4, S6 | 핵심 | `capabilities/prompt-composition.md` · 미작성 | 코드 확인(조립 규칙·연습용 선별 목록) / 오버라이드 파일 쓰기·UI는 추론 |
| 8. 도구 레지스트리와 인자 복구 | 에이전트별 도구 묶음(프로버/교사/연습)을 요청마다 조립, 설정으로 끌 수 있는 것은 `research`/`demo`/`visual`/`pdf`뿐, 퀴즈 도구는 설정(`tools.explain`)이 객관식↔자유서술을 바꿈. 약한 모델이 JSON을 문자열로 감싸 보내면(`options`, `mode` 등) 경계에서 복구, 입력 오류는 에러 결과로 돌려줘 같은 턴에 재시도. 학습자 파일은 `read/ls/find/grep` 읽기 전용 | `src/agent/tools.ts` `createProberTools`·`createTeacherTools`·`prepareQuestionArguments`, `src/agent/tools/heal.ts` `healToolRecord`, `src/core/argument-heal.ts`, `src/agent/tool-execute.ts`, `src/core/pending.ts` `TOGGLEABLE_TOOLS`(79)·`filterEnabledTools`(98), `src/agent/tools/{read,ls,find,grep,fs-shared}.ts` | S2, S4 | 핵심 | `capabilities/tool-registry.md` · 미작성 | 코드 확인(구성·토글·heal 헤더) / 학습자 파일 도구 본문과 경로 제한은 미확인 |
| 9. 컨텍스트 컴팩션 | 대화가 임계(설정 기본 150k 토큰, 모델 컨텍스트−16k 중 작은 값)를 넘으면 세션 자신의 대화 모델이 요약을 쓰고 기록에 `compaction` 마커를 추가. 전체 이력은 지우지 않고 모델에 보낼 때만 [요약 + 컷 이후]로 투영. 턴이 끝난 직후 백그라운드로 시작하고 다음 턴 시작에서 기다림. 요약은 이해도 변화·교수 흐름·계획 트리 원문을 담음 | `src/core/compaction.ts`(`KEEP_RECENT_TOKENS` 등), `src/server/compaction.ts` `ensureCompacted`(267)·`kickCompaction`(295), `chat-handler.ts` 222~258·562~584줄, `src/core/native-messages.ts` `toLlmMessages`(512), `src/core/settings.ts` `FACTORY_SETTINGS.compaction` | S1, S4, 18 | 핵심 | `capabilities/compaction.md` · 미작성 | 코드 확인(헤더 주석·호출 지점·기본값) / 컷 알고리즘·요약 프롬프트는 미확인 |

#### B. 비동기 하위 에이전트

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 10. job 프로토콜과 wake 파이프라인 | 교사·프로버가 `research`/`demo`/`visual`/`pdf`를 호출하면 즉시 "접수" 결과로 턴이 계속되고, 백그라운드 러너가 끝나면 결과를 steer 메시지(사용자 역할 마커)로 만들어 전달: 진행 중 턴이 있으면 pi steering 큐로(턴 경계에서 주입), 없으면 세션당 직렬 큐가 질문 미해결·턴 종료를 기다려 서버가 깨움 턴을 실행. job id로 중복 전달 방지, 재시작 후 고아 job 복구, 활동 독에서 중단 | `src/agent/tools/jobs.ts` `jobTools`(131), `src/agent/subagents/runner.ts` `createJobRunner`(127), `src/server/jobs.ts` `deliverJobResult`(198)·`recoverStaleJobs`, `src/core/contracts/jobs.ts` `buildSubagentSteer`(372)·`steerDelivered`(439), `src/store/jobs.ts`, `app/api/jobs/route.ts`, `app/api/activity/abort/route.ts`, `subagents/aborts.ts`·`bg-llm-semaphore.ts` | S1, S5, S4, 22 | 핵심 | `capabilities/job-wake.md` · 미작성 | 코드 확인(헤더 주석·시그니처·핸들러 연결) / `server/jobs.ts` 본문·`store/jobs.ts`는 미확인 |
| 11. 조사 계열 하위 에이전트 (researcher·pdf-reader) | `research`: 격리된 컨텍스트에서 `web_search`(주입된 검색 어댑터)·`web_fetch`(Readability+Turndown, 렌더 필요 시 Jina Reader 폴백 — 주석)·웹 PDF 읽기 도구로 최대 12턴 조사해 출처 붙은 브리프 반환. `pdf`: 학습자가 준 PDF를 페이지 단위로 읽고 인용(페이지 목록) 있는 브리프 반환. 검색 키가 없으면 `web_search`는 정직하게 불가 문자열을 돌려줌 | `src/agent/subagents/researcher.ts` `runResearcherAgent`(94), `src/agent/tools/web.ts`, `src/agent/subagents/pdf-reader.ts` `runPdfReaderAgent`(163), `pdf-ops.ts`, `src/agent/tools/pdf-read.ts`, `subagents/pi-run.ts` `runSubagent` | 10, 20, 18 | 핵심 | `capabilities/research-pdf-agents.md` · 미작성 | 코드 확인(`researcher.ts`·`web.ts` 앞부분) / pdf 읽기 루프·`pdf-ops` 본문은 추론 |
| 12. 산출물 계열 하위 에이전트 (demo-builder·visual-maker) | `demo`: 교사가 설명용 인터랙티브 HTML 데모를 만들고, 전달 전에 앱 자체 Chromium(없으면 시스템 Chrome)에서 실행해 검증. `visual`: SVG를 만들어 resvg로 래스터화하고 비전 모델로 직접 보고 고침(설명·README 기준). 결과는 steer의 `data-subagent-artifact`로 카드에 렌더, 반전(invert) 선택을 기록에 저장 | `src/agent/subagents/demo-builder.ts` `runDemoBuilder`(184), `visual-maker.ts` `runVisualMaker`(130), `headless.ts` `getHeadless`(75)·브라우저 서비스 연결, `components/artifacts/*`, `app/api/chats/[id]/artifact-ui/route.ts` | 10, 18(vision 슬롯), 25(브라우저 서비스) | 핵심 | `capabilities/demo-visual-agents.md` · 미작성 | 코드 확인(시그니처·`artifact-ui` 라우트·헤드리스 구조 주석) / 검증 루프·프롬프트 본문 미확인 |

#### C. 지식 그래프

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 13. 세션 추출 파이프라인 | 턴이 끝날 때 아직 추출 안 된 교사 텍스트가 청크 예산(기본 4096 토큰, 설정으로 변경, 하한 500) 이상이면 비동기로 실행: **추출기**(교사 텍스트만 봄, 이미 추출된 같은 소스의 명제·사슬을 "GRAPH SO FAR"로 보며 새 명제와 사슬 제출, 명제마다 근거 `messageId`) → **감사기**(원본은 못 보고 그래프를 `find`/`list_*` 도구로 탐색해 기존 노드와 같은 명제인지 `linkTo` 판정) → **병합기**(결정론적: 노드·사슬 원장 추가, 같은 논증은 같은 `arg_` id로 합침, 중복 파생 사슬 제거, 배치마다 커버리지 기록). 실패하면 커버리지를 안 남기고 다음 트리거가 재시도. 세션당 단일 실행, 수동 추출 버튼·중단 지원. 연습 세션과 그래프 비활성 설정에서는 실행 안 함 | `src/server/turn-service.ts` `triggerExtraction`(100), `src/agent/subagents/extraction.ts` `createExtractionPipeline`(787)·`proseView`·`EXTRACTION_CORE`, `src/core/coverage.ts` `coverageOf`(115)·`batchRuns`(161), `src/core/graph.ts` `mergeFindings`(148)·`simplifyChains`(300), `app/api/graph/coverage/extract/route.ts`, `app/api/graph/status/route.ts` | S1, S3, S4, 15, 18 | 핵심 | `capabilities/graph-extraction.md` · 미작성 | 코드 확인(트리거·`mergeFindings` 전체·추출기 스키마·교사 텍스트 한정) / 감사기 루프와 두 LLM 프롬프트 본문(`EXTRACTION_CORE`·`AUDITOR_INSTRUCTIONS`)은 미확인, 추출 품질은 미확인 |
| 14. 노트 가져오기 | 임의 형식 텍스트 파일(`*.md`/`*.txt` 등)을 올리면 파일마다 같은 파이프라인을 한 번 실행(3개 병렬), 소스 id는 파일 경로 해시라 재가져오기는 같은 소스로 처리. 명제 출처는 파일(메시지 앵커 없음) | `app/api/graph/import/route.ts`, `extraction.ts` `importNotes`·`NOTES_EXTRACTOR_INSTRUCTIONS`·`NotesImportError`, `src/core/contracts/graph.ts` `NotesSource`, `components/notes-import.tsx`, `scripts/import-notes.ts` | 13, S3 | 핵심 | `capabilities/notes-import.md` · 미작성 | 코드 확인(라우트 전체·계약 주석) / 가져오기 UI는 추론 |
| 15. 그래프 원장·파생 뷰·배치 | 저장: 추가 전용 JSONL(`nodes`/`chains`/`sessions`/`coverage`)+`sources.json`/`positions.json`/`render-settings.json`/`format.json`. 읽기: 같은 id의 줄을 합쳐(첫 줄이 이름·진술·생성일 정의, 별칭·출처는 합집합) 스냅샷 파생 — 사슬마다 함의 노드(`arg_`)와 전제→함의→결론 화살표, 태어난 세션 기준 클러스터(3개 미만은 표시 안 함), 병합 때마다 증분 배치(d3-force) | `src/store/graph.ts` `graphStore`(131), `src/store/graph-format.ts`, `src/core/graph.ts` `getGraph`(405)·`deriveView`(456)·`graphSnapshot`(509)·`graphSessionIndex`(630), `src/core/session-clusters.ts`, `src/core/layout.ts` `incrementalLayout`(542), `src/core/layout-settle.ts` `settleGraphLayout`(26), `app/api/graph/route.ts`·`positions/route.ts`·`render-settings/route.ts` | S3, S6 | 핵심 | `capabilities/graph-ledger.md` · 미작성 | 코드 확인(`config.ts` 원장 정의·스토어 헤더·`mergeFindings`·스킬 문서의 병합 규칙과 교차) / `getGraph`·레이아웃·클러스터 알고리즘 본문은 미확인 |
| 16. 그래프 화면·체인 표·노드 선택 | 홈 = 그래프 화면(Canvas 2D 직접 구현, d3-zoom 카메라, 클러스터 껍질). 노드 상세·출처 이동, 추출 커버리지·상태 표시, 체인 표(클러스터 → 사슬 → 명제 진술, 선택·삭제), 선택한 명제를 새 연습/수업 세션의 컨텍스트로 넘김 | `components/graph-view.tsx`, `components/graph-canvas.ts`, `components/chain-table.tsx`, `components/graph-context-card.tsx`, `components/extraction-coverage.tsx`, `src/core/chains.ts` `chainsForSelection`(34)·`resolveTargetId`(70), `app/api/chats/route.ts` `graphContext` 처리 | 15, 17 | 핵심 | `capabilities/graph-view.md` · 미작성 | 코드 확인(헤더 주석·`chainsForSelection` 호출 라우트) / 렌더링 상호작용은 추론 |
| 17. 삭제와 정리 | 세션 삭제는 두 모드(그래프 보존: 추출 기록만 삭제 / 완전 삭제), 노드 삭제는 그 노드·참조 사슬·위치를 한 번의 원장 재작성으로 제거. 추출이 돌고 있으면 노드 삭제 409 | `src/core/graph-deletion.ts` `deleteChatTraces`(96)·`deleteNodeTraces`(288), `src/server/chats.ts` `deleteChatSession`(68), `src/server/graph.ts` `deleteGraphNode`(104), `app/api/graph/nodes/[id]/route.ts`, `app/api/chats/[id]/route.ts`(DELETE), `components/delete-*-dialog.tsx` | 15, S1 | 핵심 | `capabilities/graph-deletion.md` · 미작성 | 코드 확인(헤더 주석·시그니처·노드 라우트) / 모드별 세부 연쇄는 미확인 |

#### D. 연결·설정·부가 기능

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 18. 모델 슬롯·키·카탈로그 | 최초 실행에서 키 → 모델(strong/cheap/vision) 순으로 설정, 세션은 생성 시 strong 슬롯을 자기 기록에 찍고 이후 세션 안에서 모델·사고 수준을 바꿈. 역할별 모델은 역할 오버라이드 → 슬롯 순으로 결정, 비면 503. 키는 `auth.json`(0600)에 저장하고 서버 env로 반영(env가 우선). 일반 키 제공자 35행(distinct 환경변수 32)+검색·받아쓰기 키 3종 | `src/agent/models.ts` `piModels`·`piEngineForSpec`(101), `src/core/settings-resolution.ts` `resolveConversationSpec`(103)·`resolveRoleSpec`(123), `src/core/settings.ts` `ROLE_SLOT`(220), `src/core/auth-keys.ts` `AUTH_PROVIDER_KEYS`, `src/server/keys.ts` `initAuthEnv`(102), `src/store/auth.ts`, `src/server/model-catalog.ts`, `app/api/{keys,models}/**`, `components/setup-dialog.tsx`·`model-picker.tsx` | S4, S6 | 핵심 | `capabilities/model-config.md` · 미작성 | 코드 확인(`config.ts` 주석·카탈로그 표·`chat-handler` 게이트·`keys.ts` 헤더) / 개별 제공자가 실제로 동작하는지는 외부(pi-ai)라 미확인 |
| 19. 구독 연결 (ChatGPT·GitHub Copilot·Grok) | 데스크톱에서만: 브라우저 OAuth로 구독 계정을 연결해 API 키 없이 모델을 쓰고, "백그라운드 사용 허용" 동의가 꺼져 있으면 자동 후속(steer)·컴팩션·추출을 막음. 다중 ChatGPT 계정 선택·재로그인. API 키로 폴백하지 않음 | `electron/chatgpt.cjs`·`subscriptions.cjs`·`chatgpt-ipc.cjs`·`subscription-ipc.cjs`·`subscription-store.cjs`, `src/agent/chatgpt-bridge.ts`·`subscription-bridge.ts`·`subscription-connections.ts`·`*-request-cycle.ts`·`*-stream.ts`, `src/core/contracts/{chatgpt,subscriptions}.ts`, `components/settings/{chatgpt-connection,subscription-connections}.tsx` | 18, 25 | 부속 | `capabilities/subscription-connections.md` · 미작성 | 코드 확인(계약·`chat-handler`의 게이트 호출·`chatgpt.cjs` 상수) / OAuth·IPC·요청 사이클 내부는 미확인, OpenAI·GitHub·xAI 쪽 동작은 미확인 |
| 20. 웹 검색 어댑터 패밀리 | 키가 있는 엔진이 곧 엔진(둘 다면 Tavily → Brave, `agent.search.engine`으로 고정 가능). 고정했는데 키가 없으면 폴백하지 않고 불가 사유 반환. 상태는 `GET /api/search` | `src/server/search.ts` `tavilyProvider`·`braveProvider`·`searchProvider`·`searchStatus`, `src/core/search.ts`, `app/api/search/route.ts` | 18 | 부속 | `capabilities/search-providers.md` · 미작성 | 코드 확인(Tavily 어댑터·헤더 주석) / Brave 어댑터 본문과 두 서비스의 실제 응답은 미확인 |
| 21. 음성 받아쓰기 | 서버가 5분짜리 Deepgram 접근 토큰을 발급(`/auth/grant`), 브라우저가 AudioWorklet(16kHz mono PCM)으로 Deepgram에 WebSocket 직결해 확정 문장을 입력창에 덧붙임(오디오는 서버를 거치지 않음) | `app/api/stt/token/route.ts`, `components/dictation.tsx`, `public/worklets/pcm-capture.js` | 18 | 부속 | `capabilities/dictation.md` · 미작성 | 코드 확인(라우트 전체·`dictation.tsx` 헤더) / WebSocket 프로토콜·권한 요구는 외부라 미확인 |
| 22. 실시간 알림(SSE)·활동 독·재접속 | 창마다 `GET /api/events` SSE 하나, 이벤트는 "사실만"(turn-started/settled, jobs-changed, activity-changed, chats-changed) 보내고 받는 쪽이 진짜 데이터를 다시 가져옴. 진행 중 턴·job·추출은 활동 독에서 보고 중단. 늦게 연 화면은 `GET /api/chats/[id]/stream`으로 진행 중 턴에 붙음 | `src/core/events.ts` `emit`(99), `src/server/events-stream.ts` `eventsResponse`(30), `app/api/events/route.ts`, `app/api/activity/route.ts`, `src/server/observability.ts`, `components/server-events.tsx`·`activity-dock.tsx` | 1, 10 | 핵심 | `capabilities/events-activity.md` · 미작성 | 코드 확인(두 모듈 헤더 주석·`eventsResponse` 시그니처) / 활동 집계·UI 구독은 추론 |
| 23. 사용량·비용 집계 | 모델 호출마다 토큰(입력·출력·캐시·추론)을 세션 기록의 `turns`/`extractions` 로그와 job 기록에 남기고 가격표로 환산해 상태 막대에 비용 표시. 가격은 pi-ai 카탈로그 기준(문서) | `src/server/pricing.ts` `callCost`(16)·`sessionCost`, `src/core/prices.ts`, `src/core/cost-summary.ts`, `src/core/context-usage.ts`, `components/stats-bar.tsx`·`usage-format.ts`, `app/api/graph/costs/route.ts` | S1, 18 | 부속 | `capabilities/usage-cost.md` · 미작성 | 코드 확인(`chat-handler`의 사용량 수집·`pricing.ts` 시그니처) / 가격표·환산 규칙은 미확인 |
| 24. 세션 관리·찾기·내보내기·단축키·외관 | 사이드바 세션 목록(단계·미해결 질문·busy), 세션 안 텍스트 찾기, 세션 전체를 마크다운 파일로 내보내기, 설정 화면(일반·에이전트·외관·키·단축키), 키보드 액션 표와 사용자 재정의 | `components/sidebar.tsx`, `components/session-find*.ts(x)`, `src/core/session-markdown.ts` `sessionMarkdown`(199), `app/api/chats/[id]/markdown/route.ts`, `src/core/keyboard.ts` `KEYBOARD_ACTIONS`(57), `components/settings/*`, `app/api/settings/**` | S1, S4 | 부속 | `capabilities/session-ux.md` · 미작성 | 코드 확인(마크다운 라우트·키보드 표 위치) / 나머지는 추론 |

#### E. 배포 단위와 개발 도구

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 25. Electron 셸 | 단일 인스턴스 락 → 빈 포트에 Next 스탠드얼론 서버를 `ELECTRON_RUN_AS_NODE`로 자식 프로세스 실행(`127.0.0.1`, `LH_DATA_DIR`·`LH_AUTH_FILE`·실행마다 새 `LH_DESKTOP_API_SECRET`) → 창에서 로드. 모든 `/api/*`는 비밀 헤더 `x-learnharness-desktop` 없으면 403(브라우저 단독 모드는 통과). 같은 바이너리를 `--browser-service`로 띄워 데모 검증용 CDP 포트 제공. 줌·메뉴·창 컨트롤 | `electron/main.cjs`, `electron/desktop-api.cjs`, `electron/preload.cjs`, `electron/server-title-guard.cjs`, `electron/browser-service-readiness.cjs`, `proxy.ts`, `src/server/desktop-access.ts` `desktopAPIAuthorized`(5) | S6 | 부속 | `capabilities/electron-shell.md` · 미작성 | 코드 확인(`main.cjs` 앞 110줄·`serverEntry`·비밀 주입 줄·`proxy.ts`·`desktop-access.ts`) / `main.cjs` 나머지(창·종료·IPC 핸들러 본문)는 미확인 |
| 26. 인앱 업데이트 | 패키지된 앱만: 시작 시와 24시간마다 GitHub Releases 피드 확인, 조용히 내려받고 받은 뒤 배너("Restart"), 앱 종료 시 설치. 메뉴에서 수동 확인. 개발 빌드는 비활성, `LH_UPDATE_FEED`로 피드 재정의(검증용) | `electron/main.cjs` `setupAutoUpdater`(477)·`checkForUpdates`(450)·`installUpdateNow`, `components/update-banner.tsx`, `electron-builder.yml` `publish`(github) | 25, 27 | 부속 | `capabilities/auto-update.md` · 미작성 | 코드 확인(업데이터 구성 전체) / 플랫폼별 실제 설치 동작은 외부라 미확인. 설정의 "Auto-update" 토글은 셸이 읽지 않음(2절 "문서와 구현의 차이" 8번 참조) |
| 27. 패키징·릴리스 | `next build`(standalone) → `build-server.mjs`(키·데이터 유출 검사, 불필요 파일 제거, 프롬프트 자산 확인) → `smoke-server.mjs` 부팅 검사 → `electron-builder`(macOS 서명·공증, Windows 미서명 NSIS, Linux AppImage/deb). 태그 푸시 시 3개 OS가 한 초안 릴리스에 올리고 11개 자산·피드를 검증하는 `verify-release.ts` | `electron-builder.yml`, `next.config.ts`, `scripts/{build-server.mjs,smoke-server.mjs,smoke-provider-runtime.mjs,smoke-demo-runtime.mjs,verify-release.ts,after-pack.cjs,make-icons.mjs}`, `docs/desktop-release.md`, `.github/workflows/{ci,release,notify-website}.yml`(열지 않음) | 25 | 부속 | `capabilities/desktop-packaging.md` · 미작성 | 코드 확인(`electron-builder.yml`·`next.config.ts` 앞부분·`desktop-release.md`) / 스크립트 본문과 워크플로는 미확인(워크플로는 규칙상 열지 않음) |
| 28. 에이전트 스킬 `learnharness` | 외부 에이전트(Claude Code 등)가 사용자 학습 기록을 **읽기 전용**으로 이해하게 하는 스킬: 데이터 폴더 위치(OS별), `sessions.py list/read`, `graph.py sessions/propositions/find/chains`, 형식 설명(메시지·답 상세·연습 마커·그래프 병합 규칙·함정). 데이터 수정·`auth.json` 열람 금지, 표준 라이브러리만 | `skills/learnharness/SKILL.md`, `skills/learnharness/references/data-format.md`, `scripts/sessions.py` `main`(427), `scripts/graph.py` `main`(249), `scripts/_data.py` | S1, S3 | 부속 | `capabilities/agent-skill.md` · 미작성 | 코드 확인(SKILL.md·data-format.md 전체) / Python 스크립트 본문은 미열람(추론) |
| 29. 개발·마이그레이션 스크립트 | 노트 폴더 일괄 가져오기, 모든 채팅을 새 파이프라인으로 재추출(원장 초기화), 레이아웃 재계산, 새 사용자 시뮬레이션 | `scripts/import-notes.ts`, `scripts/backfill-graph.ts`, `scripts/replay-layout.ts`, `scripts/dev-fresh.sh` | 13, 15 | 부속 | `capabilities/dev-scripts.md` · 미작성 | 코드 확인(앞 18줄 헤더) / 본문 미확인 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜. 기능 개수에 넣지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| S1. 세션 기록(대화·마커·플랜·사용량) | 1~6, 9, 10, 13, 17, 23, 24, 28 | `src/core/contracts/chat.ts` `ChatRecord`(30), `src/core/native-messages.ts`(`LhMessage`, `hasProbeDone`·`danglingQuestionOf`·`activeProblemOf`·`toLlmMessages`), `src/core/ports.ts` `ChatStore`, `src/store/chats.ts` `chatStore`(208), `data/chats/<id>.json`(버전 스탬프, 더 새 버전은 거부) | 스펙은 각 기능에 분산 | 코드 확인(필드·포트·스토어 헤더) / `native-messages.ts` 본문(771줄)은 미확인 |
| S2. 질문·답변 계약 | 2, 4, 5, 6, 8 | `src/core/question-core.ts`(입력 스키마 `quizInputObject`·`probeQuizInputSchema`·`explainInput*`·`askInputSchema`, 채점·셔플·`QuestionAnswerData`), `src/core/pending.ts` `QUESTION_TOOLS`(45), `src/core/tool-parts.ts`, `src/core/input-events.ts` | [`capabilities/question-answer-contract.md`](capabilities/question-answer-contract.md) · ready(경로명을 question-contract에서 변경, 행 6의 확신도·사고 필드 흡수) | 코드 확인(스키마 정의·타입 위치) / 채점·셔플 알고리즘은 미확인 |
| S3. 그래프 원장 계약 | 13~17, 28, 2·5(읽기 도구) | `src/core/contracts/graph.ts`(`GraphNode`·`GraphChain`·`ProvenancePoint`·`NotesSource`·`CURRENT_GRAPH_FORMAT_VERSION`), `config.ts` `LEDGER_FILES`·`SOURCES_FILE`·`POSITIONS_FILE`, `src/core/ports.ts` `GraphStore` | 스펙은 각 기능에 분산 | 코드 확인(계약·파일 경로) |
| S4. 설정 레코드와 해석 | 1, 7, 8, 9, 13, 18, 20, 24 | `src/core/settings.ts` `FACTORY_SETTINGS`(397)·`ROLE_SLOT`(220), `src/core/settings-resolution.ts`(`extractionEnabled`·`graphToolsEnabled`·`resolveSettings`), `src/store/settings.ts`, `config.ts` `SETTINGS_FILE`(델타만 저장, 없는 키는 공장값) | `capabilities/settings-record.md` · 미작성 | 코드 확인(공장값·해석 함수 위치) / 각 섹션 정규화 로직은 미확인 |
| S5. job·steer 계약 | 4, 10, 11, 12, 22 | `src/core/contracts/jobs.ts`(`JobRecord`, `buildSubagentSteer`·`buildAbortSteer`·`buildProbeHandoffSteer`, 결정적 steer id, `steerDelivered`), `src/core/ports.ts` `JobStore` | 스펙은 각 기능에 분산 | 코드 확인(함수 위치·`server/jobs.ts` 헤더) |
| S6. 데이터·키 위치 시임 | 7, 15, 18, 25, 28 | `config.ts` `PATHS`·`DATA_ROOT`(`LH_DATA_DIR`)·`AUTH_FILE`(`LH_AUTH_FILE`)·`PROMPTS_OVERRIDE_DIR` | 스펙은 각 기능에 분산 | 코드 확인(`config.ts` 전체) |

**대조한 범위와 미탐색 영역**
- 대조: README의 "How it works"(Measure/Plan/Teach/Practice)·"Knowledge that carries forward"·"Download and get started"·"Your keys, your data"; `docs/architecture.md`(앞 약 230줄)·`docs/development.md`(명령·환경변수·구조·핵심 메커니즘)·`docs/desktop-release.md`(플랫폼·파이프라인); `package.json` scripts·의존성; `app/api/**/route.ts` 30개 전수(경로·메서드 grep); `config.ts`·`src/core/ports.ts`(스토어 포트)·`src/core/settings.ts` 공장값; 도구 정의(`tools.ts`·`tools/{probe,practice,plan,graph,jobs,web}.ts`); 프롬프트 디렉터리 구성(`prompts/**`); Electron 셸 앞부분·업데이터; `electron-builder.yml`·`next.config.ts` 앞부분; `skills/learnharness/SKILL.md`·`references/data-format.md`.
- README 주장별 결과:
  - "30+ provider options": 키 제공자 표 35행(`auth-keys.ts`)+구독 3종은 코드 확인(개수). 각 제공자가 동작하는지는 외부 SDK 몫이라 `미확인`.
  - "Optional dictation and web search use separate service keys": `DEEPGRAM_API_KEY`·`TAVILY_API_KEY`·`BRAVE_API_KEY` 코드 확인(`auth-keys.ts` 34·40·46줄 id).
  - "Local storage… plain files": 코드 확인(`config.ts` `PATHS`, 스토어 헤더).
  - "System prompts are visible and editable": 오버라이드 라우트·스토어·조립 코드 확인, 설정 UI 화면은 미확인.
  - "live cost meter": `pricing.ts`·`stats-bar.tsx` 존재만 확인, 표시 동작은 추론.
  - "All three platforms support in-app updates": 업데이터 코드·빌더 설정 확인, 플랫폼별 실제 동작은 `미확인`.
  - "npm test deterministic, no LLM, no network": `package.json`의 명령만 확인, 테스트 본문은 열지 않아 `미확인`.
  - "signed and notarized DMG", "Windows unsigned": `electron-builder.yml` 주석·`signExecutable: false` 코드 확인, 실제 산출물은 미확인.
  - "AGPL-3.0": 위 라이선스 항목(코드 확인).
- 문서와 구현의 차이 (구현을 사실로 적는다):
  1. **연습(Practice)은 별도 시스템이 아니다.** `docs/architecture.md`(1·3·4절)는 6개 시스템 중 Practice(`data/practice/*.json`, `PracticeStore`, `contracts/practice.ts`, `src/store/practice.ts`, 분할기 → 문제별 생성기 → 채점기 파이프라인)를, `docs/development.md` "Key mechanisms"는 0~10점 채점까지 설명하지만, 추적 파일에 이 파일들이 없고 `ports.ts`의 스토어 포트는 ChatStore·GraphStore·JobStore(+Settings·PromptOverride·Auth)뿐이다. 실제 연습은 `kind:"practice"` 채팅 세션이고 `problem`/`conclude` 두 도구로 진행하며 점수 채점기는 없다(`chat-handler.ts` 391~421, `tools/practice.ts`). 코드 확인.
  2. **질문 도구는 "서버 `execute` 없음 + `addToolOutput`"이 아니다.** `development.md` "Key mechanisms"·`architecture.md` 4절 다이어그램(`addToolOutput`) 서술과 달리 질문 도구는 서버 `execute`가 있고(입력 검증 + `questionResult` 자리표시자, `tools.ts`), 학습자 답은 `POST /api/chat`의 입력 이벤트 `answer`로 온다(`input-events.ts`). `POST`는 스트림을 열어 두지 않고 `{ok:true}`만 돌려주며 스트림은 `GET /api/chats/[id]/stream`(`chat-handler.ts` 593~603). 코드 확인.
  3. **질문 도구 이름**: 문서는 `quiz`/`ask_user_question`로 쓰지만 프로버는 `probe`/`recall`, 교사는 `quiz`/`explain`으로 이름이 다르다(단계 경계를 모델에 드러내려는 의도라고 `tools.ts` 주석에 있다). 코드 확인.
  4. **모델·검색 설정**: `development.md`는 `OPENROUTER_API_KEY`가 필수이고 "모든 LLM 호출이 OpenRouter를 거친다", 검색은 `GOOGLE_SEARCH_API_KEY`+`GOOGLE_CSE_ID`(Google CSE)라고 쓰지만, 코드는 공장 기본 모델이 없는 BYOK이고(`config.ts`) 제공자는 pi-ai 카탈로그 전체, 검색은 Tavily/Brave이며 Google CSE는 "retired"다(`tools/web.ts` 주석, `server/search.ts`). 코드 확인.
  5. **추출 청크 기본값**: `development.md`가 Environment 절에서는 4096, 같은 문서 "Key mechanisms"에서는 8192라고 서로 다르게 쓰지만 코드의 공장값은 4096이다(`settings.ts` `FACTORY_SETTINGS.graph`, 주석에 8192에서 되돌렸다고 있음). 코드 확인.
  6. **그래프 컨텍스트 자동 주입은 없다.** `development.md`의 다이어그램은 "semantic top-K context injection (one-shot steer)" 화살표를 그리지만 코드는 주입 대신 프로버가 도구(`list_sessions`/`list_propositions`)로 읽으며(`chat-handler.ts` 446~449, `settings-body.ts` 주석 "Wave 7 killed the graph-context injection"), 문서가 언급한 임베더도 코드에 없다(`git grep embedd`는 주석·UI 문구뿐). 코드 확인.
  7. **라우트 수**: `architecture.md` 2절 그림은 "28 API route handlers", `development.md` Layout은 "16 thin API route handlers"라 쓰지만 `route.ts`는 30개다. 코드 확인.
  8. **자동 업데이트 토글**: 설정 화면에 "Auto-update" 스위치가 있고 값은 `settings.json`의 `general.autoUpdate`에 저장되지만, 힌트 문구가 "Automatic updates arrive in an upcoming release"이고 `electron/*.cjs`는 `settings.json`·`general`을 읽지 않는다(`git grep`). 업데이터는 토글과 무관하게 패키지된 앱에서 켜진다(`main.cjs` `setupAutoUpdater`). 코드 확인(부재 확인은 `electron/` 파일 grep 한정).
  9. **README의 "이해도 그림이 갱신된다"는 표현**: 코드상 이해도 그림은 구조화된 영속 데이터가 아니다. 프로버의 `probe_done` 평가·확신도·사고글은 대화 기록(과 컴팩션 요약)에만 있고, 그래프는 교사가 설명한 내용에서 추출한 명제·사슬이며(학습자 입력은 추출 입력이 아님) 이해도 점수를 담지 않는다. 다음 세션은 그래프를 도구로 읽어 "무엇을 이미 다뤘는지"를 알 뿐 "얼마나 이해했는지"는 이전 세션 기록을 따로 읽어야 안다(스킬이 그 용도). 코드 확인(`extraction.ts` `proseView`, `contracts/graph.ts` 주석, `tools/graph.ts` 설명).
- 열어서 확인한 예외 파일(규칙상 기본 비열람 범주): `skills/learnharness/references/data-format.md`와 `SKILL.md`는 문서처럼 보이나 데이터 형식·기본값을 정하는 입구이므로 열었다. `electron-builder.yml`·`next.config.ts`·`proxy.ts`는 배포 입구·접근 가드를 정하는 설정이라 열었다. `.github/workflows/*`는 열지 않았다(`notify-website.yml`의 존재는 파일 이름뿐이므로 별도 웹사이트 연동 여부는 미확인).
- 미탐색:
  - 테스트 185개(`tests/`, fixture 포함)는 열지 않았다. 스펙 단계에서 사례명 검색까지만 한다.
  - 열지 않았거나 앞부분만 읽은 본문: `components/chat.tsx`(2,387줄)·`graph-canvas.ts`·`graph-view.tsx`·`plan-block.tsx`·`sidebar.tsx` 등 UI 대부분, `src/core/native-messages.ts`·`question-core.ts`(채점·셔플)·`layout.ts`·`session-clusters.ts`·`compaction.ts` 본문·`math-delims.ts`·`prices.ts`, `src/server/jobs.ts`·`compaction.ts`·`model-catalog.ts`·`pi/ui-stream.ts`·`pi/record-adapter`(추적 파일 목록에 `pi/call-ids.ts`·`ui-stream.ts`만 보임 — `architecture.md`가 말한 `record-adapter.ts`는 이 SHA에 없음, 변환은 `native-messages.ts` `toLlmMessages`가 맡는 것으로 보이나 본문 미확인), `src/agent/subagents/{demo-builder,visual-maker,pdf-reader,pdf-ops,headless,pi-run,submit-agent}.ts` 본문, 프롬프트 `teacher/{20,30,40,50}-*.md`·`shared/{10,15,16,20,30,40}-*.md`·`prober`/`practice` 독트린 본문, `src/store/{jobs,settings,prompt-overrides,render-settings}.ts`, `electron/main.cjs` 나머지·`chatgpt-ipc/subscriptions/subscription-store.cjs`, 스크립트 본문(`verify-release.ts` 등), `skills` Python 본문, `app/*.tsx` 페이지.
  - 열지 않은 문서: `docs/{vision,plan,teaching-methodology,probe-teach-split,pi-engine-swap,compaction-accounting,keyboard,release-0.3}.md`, `docs/archive/`. 후보로만 취급한다. `architecture.md`는 앞 약 230줄(1~4절 앞부분)만 읽었고 이후(Practice 절·불변식·시임 목록 등 약 330줄)는 읽지 않았다. `development.md`는 전부 읽었다.
  - 외부 시스템: pi-ai/pi-agent-core(에이전트 루프·카탈로그·가격), OpenAI·GitHub·xAI OAuth, Deepgram, Tavily, Brave, GitHub Releases, 각 LLM 제공자. 모두 `미확인`.
  - 실행: 코드·서버를 실행하거나 의존성을 설치하지 않았다. `실행 확인` 항목은 없다(archify 검증 명령은 3절).


### 스킬화 관점 지도 (2026-10-27 추가)

분석 목적이 "Claude Code 안의 가벼운 학습 스킬"로 바뀌어, 29행 제품 지도를 **학습 스킬이 하는 일 7가지**에 다시 대 보았다. 위 29행 지도는 코드 기준 제품 지도로 그대로 두고, 이 표는 "이 레포에서 무엇을 가져올 수 있나"만 본다. 승인된 스펙 범위가 아니라 **재구성 제안**이다.

핵심 관찰: 이 레포의 학습 행동은 **프롬프트 마크다운 약 470줄**(`src/agent/prompts/`)에 들어 있다. 이 프롬프트는 도구 호출(`probe`·`quiz`·`plan_init`·`probe_done`·`problem`·`conclude`)을 전제로 쓰였지만, 방법 자체는 Claude Code 스킬 지시문으로 옮길 수 있는 글이다(옮길 수 있다는 판단은 추론).

| 학습 스킬의 일 | 이 레포가 하는 방법 | 가져올 만한 것 (근거 위치) | 원 지도 행 | 검증 수준 |
|---|---|---|---|---|
| 1. 현재 수준 진단 | 프로버: ① 목표를 구체화할 때까지 질문 ② 목표에 필요한 "가닥(strand)"을 도출 ③ 가닥마다 **바닥(확실히 아는 것)과 천장(막히는 곳)을 이진 탐색**: 높은 데서 시작, 맞고 확신하면 크게 올리고, 틀리면 좁힘 ④ 한 번에 질문 하나 ⑤ 가닥별 floor·ceiling·오개념·"여기서부터 쌓을 것"을 `probe_done`에 기록. 오답 하나는 판정이 아니라 좌표 하나 | 진단 절차 전체(39줄), **확신도×정오 해석표**(맞고 확신=단단, 맞고 불안=취약, 틀리고 확신=굳은 오개념) | 2, 6 | 코드 확인(`src/agent/prompts/prober/10-probe-doctrine.md`, `shared/25-confidence.md`, `shared/16-mental-model.md` 전문) |
| 2. 학습 계획 | 교사가 mermaid 지도로 선행 관계를 그린다. **최소 트리**: 학습자가 이미 아는 건 다시 가르치지 않고, 목표 경로 밖은 흥미로워도 안 가르침. 노드는 구조적 이정표이고 진행 상태는 저장하지 않고 질문 태그(`nodeId`)에서 파생. **계획을 제시하고 학습자가 확인하기 전에는 가르치지 않음.** 학습 중 드러난 사고에 따라 지도를 다시 쓴다 | 최소 트리 원칙, 확인 전 가르치지 않기, 뿌리 노드 검증("정말 이 사람에게 무조건적 진실인가?") | 3 | 코드 확인(`prompts/teacher/10-planning.md` 전문, `src/agent/tools/plan.ts` 도구 설명). **프롬프트는 "크기 상한 없음", 도구 설명은 "5–15 노드, 압축"이라 둘이 다르다**(어느 쪽이 강제되는지 미확인) |
| 3. 수준별 설명 | 교사 방법 두 원칙: 원칙 i **무조건적 진실부터**(주의 없이 그대로 받아들일 수 있는 사실에서 시작) 원칙 ii **"어떻게 내가 직접 발견할 수 있었을까?"**(모든 단계에 동기를 붙인다). 단계 규칙: 한 단계 한 사실, 단계마다 이해 확인, 틀리면 진단·보강 후에만 다음. 사이클은 **예측(가르치기 전) → 설명 → 확인(가르친 뒤)**. 확인 문제는 "수업만으로 추론해서 풀 수 있고, 암송이 아니라 적용이며, 오답이 어떤 잘못된 모델인지 드러나야 한다" | 설명 방법 전체: `05-method.md`(44줄), `20-teaching.md`(33줄), `28-predictions.md`(22줄), `30-question-principles.md`(10줄). 수준 적응은 프로브 결과 + 학습자의 "사고 필드"로 계획을 고치는 것 | 4 | 코드 확인(위 4개 프롬프트 전문 읽음) |
| 4. 맞춤 자료 수집 | 조사 하위 에이전트(`researcher`): 격리된 컨텍스트에서 `web_search`·`web_fetch`만 쓰고 질문을 2~4면으로 쪼개 검색해 **출처 인용이 달린 brief**를 돌려준다. 하지만 목적은 **교사가 가르칠 사실을 검증**하는 것이다. 학습자 파일은 `read/ls/find/grep`, PDF는 쪽 인용이 달린 brief | 아이디어: "확실하지 않은 사실은 가르치기 전에 조사로 확인하고 출처를 댄다"(프롬프트 `40-jobs.md`), 격리 컨텍스트 조사 | 11 | 코드 확인(`src/agent/subagents/researcher.ts` 머리, `prompts/teacher/40-jobs.md`). **학습자 수준에 맞춰 읽을 자료를 골라 주는 기능은 없다**(확인한 범위에서) |
| 5. 학습 추적 | ① 세션 기록 JSON: 메시지, 학습자 답, **확신도**, 사고 필드 글(학습자가 소리 내어 생각한 것이 가장 정보가 많은 데이터로 취급됨). ② 지식 그래프 JSONL: 명제(`nodes`)와 **연쇄(전제들이 함께 결론을 함의)**(`chains`). 추출은 **교사가 쓴 설명문만** 보고 한다. 그래프에는 이해도 점수가 없다(아이디어 지도일 뿐 숙달 평가가 아님) | 기록 형식 자체(평문 JSON/JSONL이라 옮기기 쉬움), "점수가 아니라 근거를 기록" 철학 | 13, 15 | 프롬프트·지도 단계 확인은 코드 확인. 파일 형식은 `skills/learnharness/references/data-format.md` 문서 기준이라 **추론**(코드 대조 안 함) |
| 6. 연습 | 연습 세션 독트린 141줄: 모드 3종 **회상 → 변별 → 조합**(앞 층이 약하면 되돌아감), 대상 선택 = 가장 약한 것·가장 많은 연쇄에 쓰이는 것·가장 오래 안 만진 것, 같은 대상 연속 출제 금지(교차), 쉬운 정도는 "회상 한 번당 성공률 약 85%", 출제 전에 직접 풀어 보고 모범 풀이를 먼저 확정, 힌트 사다리 R0~R5(한 요청에 한 단계), 세션 끝 전에 틀린 것은 **다른 표면으로 재시험**. 상태 저장 없음("no state record, no graduation criteria") | 연습 독트린 전체(`practice/10-doctrine.md`, `00-base.md`) | 5 | 코드 확인(`prompts/practice/10-doctrine.md`·`00-base.md` 전문). `docs/architecture.md`의 PracticeStore는 코드에 없다는 기존 확인(handoff)을 따른다 |
| 7. 지속 관리 | **없다.** 복습 일정·망각 모델·"다음에 뭘 할지" 정책이 코드에 없다(`src app lib`에서 `spaced`·`forgetting`·`nextReview`·`fsrs` 검색: 무관한 문자열 2건뿐). 세션 시작 때 프로버가 `list_sessions`·`list_propositions`로 이전 지도를 **이름만** 읽고, 단단한 가닥은 다시 묻지 않는다. 그래프에 점수가 없어서 무엇을 언제 복습할지 정할 데이터도 없다 | 없음. DeepTutor가 채운다([DeepTutor 절](../DeepTutor/overview.md#스킬화-관점-지도-2026-10-27-추가)) | — | 코드 확인(grep 부정 확인이라 다른 이름의 구현을 놓쳤을 가능성은 남는다), `prober/10-probe-doctrine.md` 1절 |

**빠진 일 두 가지(이 레포에서 못 찾음)**: ① 지속 관리(복습 일정) ② 학습자 맞춤 자료 추천.

**재구성한 구분**

| 구분 | 원 지도 행 | 이유 |
|---|---|---|
| 스킬 재료(핵심) | 2 프로버, 3 계획, 4 교사, 5 연습, 6 입력 채널(확신도·사고 필드 부분), 13 추출·15 원장(기록 형식), 28 에이전트 스킬 | 위 1~6번 일. 본체는 프롬프트 글. 28번은 이 레포가 **이미 만든 스킬**(SKILL.md 160줄 + 파이썬 스크립트 3개, 읽기 전용, 표준 라이브러리만)이라 스킬 형식과 읽기 전용 경계를 보는 참고가 된다 |
| 참고만 | 7 프롬프트 조립, 11 조사 에이전트, 14 노트 가져오기, 9 컴팩션 | 프롬프트 파일을 번호순으로 조립하는 규칙, 조사 brief 형식 |
| 제외(제품 기능) | 1(턴 파이프라인)·8(도구 레지스트리)·10·12·16~27·29 | Next.js·Electron 앱을 위한 층. Claude Code가 대신한다(추론) |

**이 레포를 스킬 재료로 읽을 때의 주의**
- 프롬프트는 앱의 도구(퀴즈 카드 UI, 확신도 슬라이더, "확인" 버튼 접힘)를 전제로 쓰였다. 터미널 대화에는 "확신도를 어떻게 받나"를 새로 정해야 한다(추론).
- 수준 진단은 한 번에 질문 하나씩 많이 오가야 해서 대화가 길어진다. 가벼움과 정밀도가 맞바뀐다.
- 라이선스가 **AGPL-3.0**이다(1절). 프롬프트·스킬을 옮겨 쓰거나 배포할 때의 조건은 사용자가 판단할 일이고, 이 문서는 법률 판단을 하지 않는다.


### 대표 흐름: 새 주제 학습 한 바퀴 (스펙 4개와 S2를 잇는 글, 2026-10-27)

각 단계의 근거는 괄호의 스펙 R-ID를 따른다. 검증 수준은 그 R-ID의 것이다.

1. 학습자가 새 세션에서 "무엇을 배우고 싶은지" 말한다. 기록에 `probe_done` 호출이 없으므로 요청마다 **프로버**가 만들어진다(`probe-measurement.md` 1.1-1).
2. 프로버가 `ask_user_question`으로 목표를 구체화하고, 가닥마다 `probe`/`recall`로 질문을 하나씩 낸다. 학습자 답은 정오·**확신도**·사고글이 한 객체로 다음 요청의 도구 결과가 된다(`question-answer-contract.md`). 프로버는 맞고 확신하면 난이도를 크게 올리고 틀리면 좁히며 가닥의 바닥과 천장을 찾는다(권고, 프롬프트).
3. 모든 가닥이 잡히면 프로버가 `probe_done`을 한 번 호출하고(대기 질문이 있으면 거부됨, 강제), 교사의 첫 턴을 일으키는 핸드오프가 큐에 들어간다(발화 시점은 `추론`). 이후 요청은 `probe_done`을 이음새로 **교사**를 만든다.
4. 교사가 `plan_init`으로 선행 관계 지도(mermaid)를 쓰고 접근법 산문과 함께 제시한 뒤 턴을 끝낸다. 학습자가 고치거나 수락한다(`plan-tree.md`). 도구가 막는 것은 형식과 순환이고 노드 수는 막지 않는다.
5. 수락 후 교사는 노드마다 **예측 → 한 단계 설명 → 확인** 사이클을 돈다. 모든 질문은 `nodeId`와 `type`(`predict`/`check`)을 갖고, 지도 위 위치는 이 태그에서 매번 계산한다(`teaching-cycle.md`). 확인에서 틀리면 보강 후에만 진행한다(권고). 학습 중 드러난 사고가 계획과 다르면 `plan_init`을 다시 불러 지도를 고친다.
6. 나중에 학습자가 연습 세션을 열면(지식 지도에서 고른 명제가 있으면 함께) 연습 에이전트가 모범 풀이를 먼저 확정한 문제를 `problem`으로 내고, 힌트는 한 번에 한 단계, `conclude` 뒤 턴을 끝내며 다음 문제는 학습자의 go-ahead에서만 낸다(`practice-session.md`). 세션 끝 전에 틀린 것은 새 표면으로 재시험한다(권고).
7. **이 흐름에는 "다음에 무엇을 언제 복습할지"를 정하는 단계가 없다.** 6번의 연습 대상은 학습자가 고르는 명제이고, 그래프에는 점수가 없다. 이 칸은 DeepTutor `review-scheduler.md`·`mastery-engine.md`가 채울 수 있다(스킬화 판단은 추론).

**통합 검토 결과 (워크플로 4장 5번)**: ① 승인 행 2·3·4·5와 S2가 모두 있고 쓰지 않은 행은 `미작성` ② 기능 사이 경계: `plan_init` 호출자·`nodeId` 검사·질문 도구 입력이 세 스펙에서 같은 용어(S2의 필드명 `confidence`·`thinking`·`dontKnow`)를 쓴다 ③ 모든 C-ID(재구현 검증 반영 후 94건, 줄 범위 표기 151개)가 기준 SHA에 파일·줄 범위로 존재하고 `depends`가 순환하지 않는다(question-answer-contract → probe-measurement → plan-tree → teaching-cycle, practice-session은 S2만) ④ 위 흐름이 처음 입력부터 연습까지 글로 이어진다.

**작업자의 지도 보정 제안과 처리**: (a) 행 6의 확신도·사고 필드를 S2에 흡수 — 반영. (b) 행 8(도구 레지스트리·인자 복구)을 쓸 때 `heal.ts`·`argument-heal.ts`를 소유해야 한다 — 행 8 `미작성`이라 보류. (c) 행 5의 선행 15·16은 경계만으로 충분 — 반영. (d) 행 1(세션 턴 파이프라인)이 다음 후보 — `next.md`에 적음. (e) `probe_done` 핸드오프 발화 시점은 행 10(job·wake) 본문을 읽어야 확정 — `next.md`에 적음.

**문서와 코드의 차이(작업자 확인, 스펙 2.1에 근거)**: 계획 노드 수는 프롬프트 "상한 없음"과 도구 설명 "5–15"가 다르고 **둘 다 코드로 강제되지 않는다**. `docs/architecture.md`의 `PracticeStore`·분할기→생성기 구조는 코드에 없고 실제는 `kind:"practice"` 세션과 `problem`/`conclude`다. 프로버 독트린은 질문 도구를 `quiz`/`explain`이라 부르지만 등록된 이름은 `probe`/`recall`이다. 교사 프롬프트는 `ask_user_question`도 접힌다고 하지만 코드는 `quiz`/`explain`만 접는다. 세부는 각 스펙 2.1.


### 재구현 검증 결과 (2026-10-27, 워크플로 4장 6번)

스펙 1부·선행 스펙·1.5 코드 범위만 받은 독립 에이전트가 Python 3(표준 라이브러리)으로 **[강제] 규칙의 순수 검증·변환·파생 로직**을 다시 구현했다. [권고] 규칙(프롬프트가 요청할 뿐인 것)과 UI, LLM 호출은 구현 대상이 아니다.

| 스펙 | 구현 범위 | 테스트 | 결과 문서 |
|---|---|---|---|
| question-answer-contract, probe-measurement, plan-tree, teaching-cycle | 질문 도구 입력 검증·답 객체 구성, `probe_done` 거부 조건·이음새, `plan_init` 해석·검증·위치 파생, `nodeId`·`type` 검증 | 83개 통과(이 4개 스펙의 1.6 T-ID 전부 + 추가) | [RESULT.md](../../artifacts/learnharness/reimplementation/core/RESULT.md) |
| practice-session | `problem`/`conclude` 게이트, 활성 문제 판정, 마커·입력 처리 | 36개 통과(보강 **전** 스펙 기준) | [RESULT.md](../../artifacts/learnharness/reimplementation/practice/RESULT.md) |

- **원본과 비교하지 않았다.** 원본이 TypeScript라 같은 입력으로 출력을 비교하지 못했다. 통과는 "스펙이 말한 것을 구현자가 테스트로 옮겨 통과했다"는 뜻이고 "원본과 같다"는 뜻이 아니다.
- **드러난 스펙 빈틈은 모두 원본 코드로 확인해 스펙에 반영했다**(실행은 하지 않고 코드 읽기). 보강 뒤의 규칙까지 재구현이 통과하는지는 다시 돌리지 않았다.
- **재구현자의 주장이 코드와 달라 채택하지 않은 것**: `research` 등록이 조건부라는 주장(`jobTools`가 4종을 조건 없이 만들고 `tools.ts:335`의 분기는 항상 참인 죽은 분기), 서버가 정수만 받는다는 근거(검증 코드 없음, 주석뿐), 추출 입력이 "교사 텍스트만"이라는 서술(코드는 assistant 메시지 전부, 프로버 단계 텍스트 포함), `dismiss-problem`을 `POST /api/chat`로 보낸다는 서술(실제 경로 `POST /api/chats/<id>/dismiss`).
- **재구현자가 옳아서 스펙을 고친 것**: "도구를 끌 수 없다"는 서술(실제로는 설정 쓰기 검증의 보장이고 팩토리는 값이 `false`인 도구를 이름 불문 뺀다), `conclude`가 공개하는 풀이(같은 메시지의 뒤 블록을 포함), `parseChatInput`의 빈 글 검사와 `parseDismissInput`이 C-ID에서 빠졌던 것.
- **repo 밖 라이브러리**(pi-ai의 스키마 검증)가 거절할 때의 문구·`isError` 여부는 코드로 정할 수 없다. 미결정이 아니라 1.2 외부 의존과 확인 한계에 경계로 적었다("거절되고 `execute`는 안 불린다"까지만 계약).
- 아직 안 한 것: 시드 섞기(FNV-1a + mulberry32)의 Python 이식이 JS와 같은 순서를 내는지는 원본을 실행하지 않아 미확인이다(스펙 시험 벡터는 코드를 옮긴 계산기 값).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

archify로 도출한 주요 구조도(필수)입니다. 실행 흐름도는 이번 세션에서 그리지 않았다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 학습 UI → API 라우트 → 서버 합성 루트 → 에이전트·추출·하위 에이전트 → LLM·저장소, 그리고 Electron·스킬·외부 서비스 |

검증 구분 (2026-10-25):
- **산출물 검증(`deliver`, `--repo-root` 소스 증거)**: 통과. 산출물 검사 9개 모두 통과(`single_svg`·`finite_svg`·`orthogonal_arrows`·`label_route_clearance`·`relationship_crossings`·`relationship_corridors`·`container_border_runs`·`route_rhythm`·`legend_clearance`), composition showcase 오류 0·경고 0, receipt `evidence.verified: true`(참조 30건). spec SHA-256 `8722a4e2…ae04`, artifact SHA-256 `35850419…f7b0`(724,089 B). 반복 중 검증 실패 두 번(라벨이 노드 위에 겹침, 라벨-경로 간격)은 `labelDy`·변 방향 지정과 간선 1개 삭제(하위 에이전트 → LLM)로 해결했다.
- **브라우저 확인(`visual-check`)**: 통과(exit 0, receipt `status: pass`). 라이트 테마 1440×900·1600×1000·1920×1080·2048×1320에서 가로·세로 넘침 없음, 최소 노드 글자 약 8.3px(1440)·9px(2048). 라이트·다크 스크린샷 4장은 `ai-learning/artifacts/learnharness/structure-visual-check/`(png 4, 접촉 시트 html, receipt json). 이 receipt가 말하는 것은 자동 측정이며 시각 검토는 `pending`이다.
- **시각 검토**: 이미지로 직접 본 것은 두 장뿐이다 — 1440×900 라이트(카드 문구 한 줄을 고치기 전 빌드)와 2048×1320 다크(최종 빌드). 노드·간선·라벨·카드가 겹치거나 잘리지 않고 읽힌다고 판단했다. 나머지 크기·테마(1440 다크, 2048 라이트, 1600·1920)는 자동 측정만이다.
- 구조도 안의 간선 라벨 일부(`fetch /api`, `병합` 등)는 작은 글자(약 9px 안팎)라 낮은 해상도에서는 읽기 어렵다.

### 그림 해설
그림을 열지 않고 이 글만 읽어도 구조와 흐름이 이해되도록 쓴다. 각 설명에 `파일:심볼`과 검증 수준을 붙였다.

**읽는 순서**
1. 왼쪽 열 맨 위 "학습 UI"에서 오른쪽 "API 라우트"로, 거기서 아래 "서버 합성 루트"로 내려온다. 이 한 줄기가 모든 요청의 길이다(`POST /api/chat` 등).
2. 가운데 줄에서 "서버 합성 루트" → 오른쪽 "교사 에이전트 3종"(초록 굵은 화살표)이 수업 턴이고, 거기서 "LLM 엔진"으로 간다. 위쪽의 "추출 파이프라인"(점선)은 턴이 끝난 뒤 비동기로 도는 그래프 쓰기, 아래쪽 "백그라운드 하위 에이전트"(점선)는 에이전트가 만든 job이다.
3. 아래 줄 왼쪽 "저장소·데이터 파일"은 서버가 쓰고 "에이전트 스킬"(점선)이 읽는다. 왼쪽 가운데 "Electron 셸"은 서버를 띄우는 셸이다.

**구조도: 모듈별 역할**
| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 학습 UI | 세션 화면(질문 독·계획 창·활동 독)과 홈(그래프 화면), 설정. 도메인 로직 없이 코어 배럴만 import | 학습자 입력 → `POST /api/chat`(입력 이벤트), `EventSource /api/events`, `fetch /api/graph` 등. 받아쓰기는 브라우저가 Deepgram에 직접 연결(그림에서 생략) | `components/session-core.ts`(`/api/chat` 호출 317줄), `components/server-events.tsx`(`EventSource("/api/events")` 39줄), `components/dictation.tsx`, `components/graph-view.tsx`(`fetch("/api/graph")` 1088줄) | 코드 확인(호출 줄) / "코어 배럴만 import" 규칙은 `docs/architecture.md` 2절의 서술이고 `eslint.config.mjs`는 열지 않아 추론 |
| API 라우트 | 전송만 담당하는 얇은 핸들러 30개와 데스크톱 접근 가드. 서버 배럴 `@/src/server`로 위임 | HTTP 요청 → 서버 함수 호출, 비밀 헤더가 없으면 403 | `app/api/chat/route.ts`, `proxy.ts` `proxy`(`config.matcher: "/api/:path*"`), `src/server/desktop-access.ts` `desktopAPIAuthorized`(5), `src/server/index.ts` | 코드 확인(라우트 파일·가드 전체, `index.ts` 배럴) / 개별 라우트 본문은 일부만 읽음 |
| 서버 합성 루트 | 한 턴을 조립: 게이트 → 입력 저장 → 에이전트 선택·구성 → 턴 실행 → 저장·추출·컴팩션. 스토어와 job 러너·추출 파이프라인을 묶고 wake 파이프라인과 연결 | 입력 이벤트 → 에이전트 인스턴스 + 엔진, 턴 종료 시 기록·사용량·추출 트리거 | `src/server/chat-handler.ts` `handleChatInput`(175), `src/server/stores.ts` `stores`, `src/server/jobs.ts` `deliverJobResult`(198), `src/server/turn-service.ts` | 코드 확인(`chat-handler.ts`·`stores.ts` 앞부분·`turn-service.ts` 전체) / `jobs.ts` 본문 미확인 |
| 교사 에이전트 3종 | prober / teacher / practice 팩토리. 각자의 도구 묶음과 프롬프트를 갖고, 기록에서 매 턴 새로 만들어 쓰고 버림. 질문이 정상 제시되면 턴을 끝내는 규칙 | 기록(`messages`) + 엔진 + 도구 → 에이전트. 질문·`probe_done`·`plan_init`·`problem`/`conclude`·job 호출 | `src/agent/teacher-agent.ts` `createProberAgent`(259)·`createTeacherAgent`(269)·`createPracticeAgent`(320)·`makeQuestionStopper`, `src/agent/tools.ts`, `src/agent/prompt-segments.ts` | 코드 확인 |
| 추출 파이프라인 | 교사 텍스트에서 명제·사슬 추출 → 감사(기존 노드와 동일성 판정) → 결정론적 병합. 세션당 단일 실행, 커버리지로 재시도 | 교사 텍스트(`TEACHER [id]`) → 명제·사슬 → 원장 추가·`coverage.jsonl` | `src/agent/subagents/extraction.ts` `createExtractionPipeline`(787)·`proseView`, `src/core/graph.ts` `mergeFindings`(148), `src/core/coverage.ts` | 코드 확인(구조·병합기) / 감사기 루프·프롬프트 미확인 |
| 백그라운드 하위 에이전트 | research·demo·visual·pdf를 job으로 비동기 실행하고 결과를 steer로 되돌림 | job 기록 + 도구 입력 → 브리프·HTML·SVG, wake로 교사 턴 재개 | `src/agent/subagents/runner.ts` `createJobRunner`(127), `src/agent/tools/jobs.ts` `jobTools`(131), `researcher.ts`, `demo-builder.ts`, `visual-maker.ts`, `pdf-reader.ts` | 코드 확인(러너·도구 시그니처) / 각 에이전트 본문은 일부만 |
| 순수 코어 | 계약·포트·그래프 병합/파생·질문 채점·플랜 트리·단계 파생·컴팩션 등 IO 없는 도메인 로직 | 타입·순수 함수. 저장소 접근은 포트(`ChatStore`/`GraphStore`/`JobStore`) 인자로 받음 | `src/core/graph.ts`, `src/core/ports.ts`, `src/core/question-core.ts`, `src/core/contracts/*.ts` | 코드 확인(`ports.ts`·`graph.ts`·계약 헤더) / "IO 없음"은 헤더 주석과 `architecture.md` 서술 — 모든 core 파일을 열어 확인하지는 않아 추론 |
| 저장소·데이터 파일 | 포트의 fs 어댑터. 채팅은 파일 하나(JSON 전체 읽기-수정-쓰기), 그래프는 추가 전용 JSONL 원장, job·설정·키는 JSON | 포트 호출 ↔ `data/chats/*.json`, `data/graph/*.jsonl` 등 | `src/store/chats.ts` `chatStore`(208), `src/store/graph.ts` `graphStore`(131), `config.ts` `PATHS`·`LEDGER_FILES` | 코드 확인(헤더·객체 정의) / `store/jobs.ts` 등 나머지 미확인 |
| LLM 엔진 (pi-ai) | 모델 슬롯·역할 오버라이드를 해석해 pi-ai 카탈로그의 모델과 스트림 함수로 엔진을 만듦. API 키 제공자 35행과 ChatGPT·Copilot·Grok 구독 경로 | 해석된 모델 사양 → `{model, streamFn, level}` | `src/agent/models.ts` `piEngineForSpec`(101), `src/core/auth-keys.ts` `AUTH_PROVIDER_KEYS`, `src/core/contracts/subscriptions.ts` `NATIVE_SUBSCRIPTIONS` | 코드 확인(엔진 팩토리·표) / pi-ai SDK 내부와 실제 호출 결과는 미확인 |
| 외부 서비스 | Tavily·Brave 검색(서버가 호출), 웹 `fetch`, Deepgram(서버는 토큰만 발급) | 검색 질의 → 결과 목록, 토큰 요청 → 접근 토큰 | `src/server/search.ts` `tavilyProvider`·`braveProvider`, `src/agent/tools/web.ts`, `app/api/stt/token/route.ts` | 코드 확인(Tavily·토큰 라우트) / 서비스 쪽 동작 미확인 |
| Electron 셸 | 서버를 자식 프로세스로 띄우고 접근 비밀·데이터 경로·키 파일 경로를 환경변수로 넘김. 인앱 업데이트·구독 OAuth·브라우저 서비스 | 환경변수·IPC, 창에서 서버 URL 로드 | `electron/main.cjs`(`serverEntry`, `LH_DESKTOP_API_SECRET` 222줄, `setupAutoUpdater` 477), `electron/desktop-api.cjs`, `electron/chatgpt.cjs` | 코드 확인(앞 110줄·비밀 주입·업데이터) / IPC·창 관리 본문 미확인 |
| 에이전트 스킬 | 외부 에이전트가 데이터 폴더를 읽기 전용으로 이해하도록 가이드+Python 리더 | 데이터 폴더 `chats/*.json`·`graph/*` → 텍스트/JSON 출력 | `skills/learnharness/SKILL.md`, `references/data-format.md`, `scripts/sessions.py` `main`(427), `scripts/graph.py` `main`(249) | 코드 확인(문서) / 스크립트 본문 미열람 |

**그림에서 뺀 것과 이유**
- 순수 코어의 사용 간선(에이전트·서버·UI → 코어)은 거의 모든 모듈이 코어를 쓰고 그리면 선이 서로 교차해, 추출 파이프라인 → 코어(`mergeFindings`)만 그렸다. 저장소가 코어의 포트를 구현한다는 관계도 생략했다(`src/core/ports.ts` ↔ `src/store/*`, 코드 확인).
- 하위 에이전트 → LLM 간선은 라우팅 충돌로 뺐다. 실제로는 러너가 역할별 엔진을 `engineFor`로 받아 쓴다(`chat-handler.ts` 82~103줄, 코드 확인).
- 학습 UI → Deepgram 직결, Electron ↔ 서버 사이의 구독 OAuth IPC, 서버 → 외부 LLM 제공자 인증(키 파일)은 그리지 않았다.
- 서버 내부의 wake 파이프라인(하위 에이전트 → 서버로 되돌아오는 steer), 컴팩션, SSE 이벤트 버스, 모델 카탈로그, 사용량 집계는 서버 합성 루트 노드 안에 접어 넣었다(지도 9·10·22·23행).
- 실행 흐름도(요청 한 번의 시간순)는 이번에 그리지 않았다.

**미확인 영역**
- `components/` 안의 구조(채팅 화면과 그래프 화면이 어떻게 나뉘는지)와 UI 상태 머신(`session-core.ts` 776줄, `chat.tsx` 2,387줄).
- `src/server/pi/ui-stream.ts` `runPiTurn`이 pi 에이전트 이벤트를 어떤 와이어 형식으로 스트리밍하는지, `native-messages.ts` `toLlmMessages` 변환 규칙.
- 감사기(auditor)의 탐색 루프와 두 LLM 프롬프트(`EXTRACTION_CORE`, `AUDITOR_INSTRUCTIONS`) 본문.
- 하위 에이전트 4종의 실제 루프, 헤드리스 브라우저 서비스 기동·종료 순서(`headless.ts`, `main.cjs` 브라우저 서비스 분기 일부만 읽음).
- `pi-ai`·`pi-agent-core`의 에이전트 루프(`Agent`, `finishTurn`, steering 큐)와 카탈로그·가격표(외부 패키지).

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸. 범위 승인 전이라 모두 미작성이다.
