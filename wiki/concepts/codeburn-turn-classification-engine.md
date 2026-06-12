---
title: CodeBurn Turn Classification Engine
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence, deepwiki]
sources:
  - artifacts/codeburn/deepwiki/pages-md/2.2-turn-classification-engine.md
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-domain-terminology.md
  - repos/codeburn/src/classifier.ts
  - repos/codeburn/src/bash-utils.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/types.ts
confidence: high
---
# CodeBurn Turn Classification Engine

이 페이지는 [[codeburn]]이 하나의 `ParsedTurn`을 보고 "이 turn은 coding/debugging/testing/git/build/deploy 중 무엇인가"를 어떻게 분류하는지 정리한다. DeepWiki `2.2 Turn Classification Engine`을 baseline으로 삼았지만, 현재 동작은 `repos/codeburn` source 기준으로 검증했다. 앞단에서 turn이 어떻게 만들어지는지는 [[codeburn-data-ingestion-and-caching]], 용어 정의는 [[codeburn-domain-terminology]]를 참조한다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## 한 문장 요약
CodeBurn의 classifier는 LLM 분류기가 아니라 deterministic rule engine이다. 한 turn의 `assistantCalls[].tools`, `toolSequence`, `bashCommands`, `userMessage`를 보고 tool pattern → keyword refinement → conversation fallback 순서로 `TaskCategory`를 붙이고, edit-test-edit 패턴을 retry로 센다.

## 입력과 출력
| 구조 | 의미 | Evidence |
|---|---|---|
| `ParsedTurn` | user message 1개와 이어지는 assistant API call 묶음 | `repos/codeburn/src/types.ts:65-70` |
| `ParsedApiCall.tools` | assistant call에서 관측된 tool 이름들 | `repos/codeburn/src/types.ts:72-88`, `repos/codeburn/src/parser.ts:1095-1139` |
| `ParsedApiCall.bashCommands` | Bash tool 입력에서 뽑은 command base name 목록 | `repos/codeburn/src/types.ts:85`, `repos/codeburn/src/parser.ts:1110-1135` |
| `ParsedApiCall.toolSequence` | retry detection용 tool/file/command 순서 | `repos/codeburn/src/types.ts:98-102`, `repos/codeburn/src/parser.ts:1112-1138` |
| `ClassifiedTurn` | `ParsedTurn` + `category`, `subCategory`, `retries`, `hasEdits` | `repos/codeburn/src/types.ts:119-124` |

최종 category는 `coding`, `debugging`, `feature`, `refactoring`, `testing`, `exploration`, `planning`, `delegation`, `git`, `build/deploy`, `conversation`, `brainstorming`, `general` 중 하나다. (`repos/codeburn/src/types.ts:104-117`)

## 분류 흐름
```text
classifyTurn(turn)
→ tools가 없으면 classifyConversation(userMessage)
→ tools가 있으면 classifyByToolPattern(turn)
→ tool category가 나오면 refineByKeywords(category, userMessage)
→ tool category가 없으면 classifyConversation(userMessage)
→ retries=countRetries(turn), hasEdits=turnHasEdits(turn) 추가
```

근거: `repos/codeburn/src/classifier.ts:193-217`.

## 1. Tool pattern: 어떤 도구를 썼는지가 1차 기준이다
`classifyByToolPattern()`은 turn 전체의 tool 이름을 모아 1차 category를 고른다. (`repos/codeburn/src/classifier.ts:52-94`)

| Tool set | 현재 member | 기본 해석 |
|---|---|---|
| `EDIT_TOOLS` | `Edit`, `Write`, `FileEditTool`, `FileWriteTool`, `NotebookEdit`, `cursor:edit` | 파일 수정이므로 `coding` |
| `READ_TOOLS` | `Read`, `Grep`, `Glob`, `FileReadTool`, `GrepTool`, `GlobTool` | 읽기/검색이므로 `exploration` |
| `BASH_TOOLS` | `Bash`, `BashTool`, `PowerShellTool` | 단독이면 user message regex로 testing/git/build/deploy를 먼저 시도, 아니면 `coding` |
| `TASK_TOOLS` | `TaskCreate`, `TaskUpdate`, `TaskGet`, `TaskList`, `TaskOutput`, `TaskStop`, `TodoWrite` | `planning` |
| `SEARCH_TOOLS` | `WebSearch`, `WebFetch`, `ToolSearch` | `exploration` |
| MCP tools | `mcp__` prefix | `exploration` |
| `Skill` | literal `Skill` | `general`; skill name이 있으면 `subCategory`로 저장 |

우선순위도 중요하다. `hasPlanMode`가 있으면 `planning`, `hasAgentSpawn`이 있으면 `delegation`이 먼저 반환된다. edit tool이 하나라도 있으면 bash/read가 함께 있어도 기본은 `coding`이다. (`repos/codeburn/src/classifier.ts:60-94`)

## 2. Bash command는 두 가지 방식으로 쓰인다
Bash 관련 정보는 classification과 reporting에서 역할이 다르다.

1. Category 분류에서는 실제 extracted command list보다 `userMessage` regex가 주로 쓰인다. `BASH_TOOLS`가 있고 edit tool이 없을 때 `TEST_PATTERNS`, `GIT_PATTERNS`, `BUILD_PATTERNS`, `INSTALL_PATTERNS`를 user message에 적용해 `testing`, `git`, `build/deploy`를 결정한다. (`repos/codeburn/src/classifier.ts:3-6`, `repos/codeburn/src/classifier.ts:75-81`)
2. 어떤 명령어를 썼는지 집계하는 `bashBreakdown`은 `parser.ts`에서 Bash tool input을 `extractBashCommands()`로 분해해 `ParsedApiCall.bashCommands`에 저장한 뒤, `buildSessionSummary()`가 command별 call count를 누적한다. (`repos/codeburn/src/parser.ts:1110-1135`, `repos/codeburn/src/parser.ts:1353-1356`)

즉, "이 turn이 testing인가"는 현재 주로 user request 문구와 Bash tool presence로 판단하고, "어떤 command를 썼나"는 별도 breakdown으로 집계한다.

## 3. Bash command 추출 방식
`extractBashCommands(rawCommand)`는 command string을 그대로 split하지 않는다.

```text
strip ANSI
→ 따옴표 안 문자열을 공백으로 치환
→ &&, ;, | 기준으로 segment 분리
→ 각 segment의 환경변수 할당 prefix 제거
→ basename(command)만 저장
→ cd/true/false 같은 noise 제거
```

예를 들어 `NODE_ENV=test npm test && cd app && git status` 같은 입력은 환경변수 prefix와 `cd` noise를 제외하고 `npm`, `git` 같은 base command 중심으로 집계된다. 근거: `repos/codeburn/src/bash-utils.ts:1-46`.

## 4. Keyword refinement: coding/exploration을 더 구체화한다
Tool pattern이 `coding` 또는 `exploration`을 반환하면 `refineByKeywords()`가 user message를 다시 본다. (`repos/codeburn/src/classifier.ts:119-137`)

- `coding`이면 `REFACTOR_KEYWORDS`, `FEATURE_KEYWORDS`, `DEBUG_KEYWORDS`를 first-match 방식으로 비교해 `refactoring`, `feature`, `debugging`으로 세분화한다.
- `exploration`이면 research keyword는 그대로 `exploration`, debug keyword는 `debugging`으로 보정한다.

`firstMatchingCategory()`는 regex match 위치가 가장 앞선 category를 고른다. 같은 위치면 caller가 넘긴 후보 순서가 tie-breaker다. 이 때문에 "add error handling"처럼 feature 단어와 debug 단어가 함께 있어도 문장 앞쪽 단어가 우선된다. (`repos/codeburn/src/classifier.ts:96-117`)

## 5. Tool이 없거나 애매하면 conversation heuristic으로 간다
`classifyConversation()`은 tool이 없거나 tool pattern이 category를 만들지 못한 경우 user message만 보고 분류한다. 순서는 brainstorming → research/exploration → feature/debug first-match → file/script pattern → URL → conversation이다. (`repos/codeburn/src/classifier.ts:139-154`)

이 fallback 덕분에 tool을 쓰지 않은 질문도 `conversation`으로만 뭉개지지 않고, "이 파일 구조 설명해줘"는 exploration, "새 기능 만들어줘"는 feature, "에러 고쳐줘"는 debugging처럼 coarse category를 얻을 수 있다.

## 6. Retry detection: edit → verify → edit를 센다
`countRetries()`는 turn 내부 tool 순서를 보고 retry를 센다. `toolSequence`가 있으면 그것을 사용하고, 없으면 call의 `tools` 배열을 step으로 변환한다. (`repos/codeburn/src/classifier.ts:156-187`)

핵심 규칙은 다음과 같다.

```text
파일 A를 edit
→ Bash/PowerShell verify step 발생
→ 같은 파일 A를 다시 edit
= retry +1
```

구현은 file key별 마지막 edit step을 저장하고, 마지막 bash verify step이 이전 edit 이후이면서 현재 edit 전이면 retry를 증가시킨다. file path가 없으면 `__no_file__` bucket을 쓴다. (`repos/codeburn/src/classifier.ts:166-184`)

## 7. Session summary에서 어떻게 쓰이나
`classifyTurn()` 결과는 `buildSessionSummary()`에서 비용/절감액/turn 수와 함께 category별로 누적된다. Category breakdown은 `turns`, `costUSD`, `savingsUSD`, `retries`, `editTurns`, `oneShotTurns`를 가진다. Tool, MCP server, bash command, subagent breakdown도 같은 session summary에서 같이 누적된다. (`repos/codeburn/src/parser.ts:1263-1390`, `repos/codeburn/src/types.ts:126-149`)

## 현재 source 기준 주의점
- 이 engine은 deterministic regex/tool-set 기반이며 LLM을 호출하지 않는다.
- Bash category refinement는 실제 shell command AST 분석이 아니라 `userMessage` regex 중심이다.
- 실제 command 사용량은 `bashBreakdown`으로 따로 집계된다.
- Retry는 모든 실패를 의미하지 않고, turn 안에서 관측된 edit→bash verify→same-file edit 패턴의 근사치다.
- Tool 이름 set은 provider adapter가 어떤 tool identifier를 넣는지에 의존한다.

관련 페이지: [[codeburn]], [[codeburn-data-ingestion-and-caching]], [[codeburn-domain-terminology]], [[evidence-backed-analysis]].
