---
title: CodeBurn Turn Classification Engine
created: 2026-06-10
updated: 2026-10-15
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence]
sources:
  - repos/codeburn/src/classifier.ts
  - repos/codeburn/src/bash-utils.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/types.ts
  - repos/codeburn/src/session-cache.ts
  - repos/codeburn/src/behavioral-weight.ts
  - repos/codeburn/src/day-aggregator.ts
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-domain-terminology.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
confidence: high
---
# CodeBurn Turn Classification Engine

검증 기준 checkout: repos/codeburn at 9a40cc603fcd194caca9daa8c5134a61ea7e0e2b (2026-10-15).

[[codeburn]]이 turn(사용자 메시지 하나 + 그 뒤 assistant call들) 하나를 13개 `TaskCategory` 중 하나로 분류하고, 같은 turn의 `retries`·`hasEdits`를 계산하는 방식이다. 용어는 [[codeburn-domain-terminology]], turn이 만들어지는 과정은 [[codeburn-data-ingestion-and-caching]]을 본다.

## 한 문장 요약

LLM 없이 정규식과 도구 이름 집합만 쓰는 규칙 기반 분류기다. 쓴 도구로 1차 분류 → 사용자 메시지 키워드로 세분화 → 도구가 없으면 대화 키워드로 분류한다. (코드 확인, `src/classifier.ts:1-222`)

## `classifyTurn(turn)` — `src/classifier.ts:200-222`

- 입력: `ParsedTurn`. 실제로 쓰는 필드는 `userMessage`와 `assistantCalls[].tools / skills / hasPlanMode / hasAgentSpawn / toolSequence`. (코드 확인)
- 내부 동작:
  1. 모든 call의 `tools`를 평평하게 모은다(`getAllTools`, `:53-55`).
  2. 도구가 0개면 `classifyConversation()`. (`:205-206`)
  3. 도구가 있으면 `classifyByToolPattern()` → 결과가 있으면 `refineByKeywords()`, `null`이면 `classifyConversation()`. (`:207-213`)
  4. `countRetries()`, `turnHasEdits()` 계산. (`:216`)
  5. Skill 이름이 하나라도 있으면 첫 번째를 `subCategory`로. category 조건 없음. (`:218-219`)
- 반환값: `ClassifiedTurn` = 원본 turn + `category`, `retries`, `hasEdits`, `subCategory?`. (코드 확인)

## 1단계: 도구 패턴 `classifyByToolPattern()` — `src/classifier.ts:61-95`

도구 집합 (`:19-23`, 코드 확인):
- `EDIT_TOOLS`: `Edit`, `Write`, `FileEditTool`, `FileWriteTool`, `NotebookEdit`, `cursor:edit|strreplace|write`, 소문자 `edit`, `write`
- `READ_TOOLS`: `Read`, `Grep`, `Glob` + `*Tool` 변형
- `BASH_TOOLS`: `Bash`, `BashTool`, `PowerShellTool`
- `TASK_TOOLS`: `TaskCreate/Update/Get/List/Output/Stop`, `TodoWrite`
- `SEARCH_TOOLS`: `WebSearch`, `WebFetch`, `ToolSearch`; MCP는 `mcp__` 접두어, Skill은 `Skill`

판정 순서 (위에서 먼저 걸리면 끝, 코드 확인):

| 순서 | 조건 | 결과 |
|---|---|---|
| 1 | 어떤 call이든 `hasPlanMode` | `planning` |
| 2 | 어떤 call이든 `hasAgentSpawn` | `delegation` |
| 3 | Bash 있고 edit 없음 + 사용자 메시지가 TEST/GIT/BUILD/INSTALL 패턴 | `testing` / `git` / `build/deploy` |
| 4 | edit 있음 | `coding` |
| 5 | Bash + read | `exploration` |
| 6 | Bash만 | `coding` |
| 7 | search 또는 MCP / read만 | `exploration` |
| 8 | task 도구만 | `planning` |
| 9 | Skill만 | `general` |
| 10 | 그 외 | `null` → 대화 분류로 |

주의: 3번 패턴은 실행된 명령이 아니라 **사용자 메시지**에 대해 검사한다 (`:77-81`, 코드 확인). `hasPlanMode`는 `EnterPlanMode` 도구, `hasAgentSpawn`은 `Agent` 도구 존재로만 설정된다(`Task`는 아님). `src/parser.ts:1573-1574`, `src/parser.ts:3007-3008` (코드 확인)

## 2단계: 키워드 세분화 `refineByKeywords()` — `src/classifier.ts:120-138`

- `coding` → `firstMatchingCategory()`로 REFACTOR / FEATURE / DEBUG 정규식 중 **메시지에서 가장 앞에 매치된 것**을 고른다. 같은 위치면 refactoring > feature > debugging 순. 아무것도 없으면 `coding` 유지. (코드 확인)
- `exploration` → RESEARCH 키워드가 있으면 그대로, 없고 DEBUG 키워드가 있으면 `debugging`. (코드 확인)
- 나머지 category는 그대로.

`firstMatchingCategory()` (`:104-118`): 입력은 텍스트와 `{regex, category}` 후보 배열, 각 regex의 `exec().index`를 비교해 최소 index 후보를 반환, 없으면 `null`. 주석에 따르면 "add error handling"이 debugging으로 잡히던 문제(Issue #196) 수정용이다. (코드 확인 — 의도는 주석 근거)

## 3단계: 대화 분류 `classifyConversation()` — `src/classifier.ts:140-155`

도구가 없거나 1단계가 `null`일 때. 순서: BRAINSTORM → `brainstorming`, RESEARCH → `exploration`, FEATURE/DEBUG 중 먼저 나온 것, 파일 확장자 → `coding`, 스크립트/API 단어 → `coding`, URL → `exploration`, 그 외 `conversation`. (코드 확인)

## Retry 계산 `countRetries()` — `src/classifier.ts:157-194`

- 입력: turn의 call들. `toolSequence`가 있으면 그 step들을, 없으면 `tools`를 파일 정보 없는 step 하나로 쓴다. (`:158-165`)
- 내부 동작: 파일별 마지막 edit step(`lastEditStep`)과 마지막 검증 step(`lastVerifyStep`)을 추적. 같은 파일 edit 사이에 검증 Bash가 있었으면 `retries++`. 파일 경로가 없으면 `'__no_file__'` 하나로 묶인다. (`:167-191`)
- 검증 Bash 제외: `isReadShapedBashCommand(command)`가 true인 읽기 전용 명령(`rg`, `cat`, `ls`, `jq`, `git log/diff/status` 등)은 검증으로 치지 않는다. 명령 문자열이 없으면 예전처럼 검증으로 친다. (`:173-180`, `src/bash-utils.ts:83-127`, 코드 확인)
- 반환값: 정수 retry 횟수.

`toolSequence` 생성: Claude parser가 assistant 메시지의 각 `tool_use` block을 `{tool, file: input.file_path, command: input.command}` 한 step으로 만든다. `src/parser.ts:1533-1541` (코드 확인). 비-Claude provider가 `toolSequence`를 채우는지는 provider마다 다르다(미확인).

`isReadShapedBashCommand()` (`src/bash-utils.ts:105-127`): 입력은 원문 명령. 따옴표 문자열을 지우고 `&&`, `;`, `|`로 나눈 뒤, `sudo`/`npx` 같은 접두어와 `VAR=`를 건너뛰고 기본 명령을 본다. 모든 조각이 읽기 전용이어야 true, 모르는 명령은 false. (코드 확인)

## 분류 결과가 쓰이는 곳

- 호출 지점: 신규 파싱 `turns.map(classifyTurn)` (`src/parser.ts:2062`), 캐시 재생성 `cachedTurnToClassified()` (`src/parser.ts:3046-3059`, 호출 `:2587`, `:4448`, `:4536`). (코드 확인)
- `CachedTurn`에는 category가 없어 캐시에서 읽을 때마다 다시 분류한다. `src/session-cache.ts:97-114` (코드 확인). 따라서 분류 규칙이 바뀌면 캐시 재생성 없이 과거 데이터에도 반영된다 (추론).
- 세션 집계: `categoryBreakdown[category]`에 비용은 항상, `turns`/`editTurns`/`retries`/`oneShotTurns`는 behavioral turn에만 더한다. `subCategory`는 `skillBreakdown` 키. `src/parser.ts:1885-1911` (코드 확인)
- 일별 집계도 같은 규칙(`behavioralTurn && hasEdits && retries === 0`). `src/day-aggregator.ts:136-154` (코드 확인) → [[codeburn-day-aggregation-and-caching]]
- 여러 프로젝트에 걸친 turn의 뒤쪽 조각은 `hasEdits: false`, `retries: 0`으로 덮어써 중복 집계를 막는다. `src/parser.ts:179-185` (코드 확인)

## 설계 해석

- 비용이 드는 LLM 분류 대신 정규식을 쓴 것은 로컬·오프라인·결정적 실행을 위해서로 보인다. (추론)
- 키워드 정규식이 영어 전용이라 한국어 등 다른 언어 메시지는 대부분 도구 패턴 결과(`coding`/`exploration`)나 `conversation`으로 떨어진다. (추론, 정규식 `src/classifier.ts:4-17` 근거)
- 정규식이 넓다: `TEST_PATTERNS`의 `test`, `BUILD_PATTERNS`의 `docker`처럼 메시지에 단어만 있어도 매치된다. (코드 확인, 오분류 빈도는 미확인)

## 미확인

- 비-Claude provider(Codex 등, [[codeburn-codex-provider]])가 `toolSequence`, `skills`, `EnterPlanMode` 계열 정보를 얼마나 채우는지.
- `src/plugins/exporter.ts:17`이 `classifyTurn`을 import하지만 grep상 호출은 없음 — 미사용 import인지 미확인.
- 분류 정확도에 대한 테스트/평가 데이터 (`tests/` 미열람).
- [[codeburn-optimization-engine]], [[codeburn-report-status-export-commands]]가 category를 어떻게 소비하는지는 해당 노트 범위.
