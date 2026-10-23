---
sha: "a201f47d2b17d6cf6a9347f336691b00c98720a1"
created: 2026-10-22
updated: 2026-10-22
sources:
  - packages/core/src/services/prompt/service.ts
  - packages/core/src/services/prompt/types.ts
  - packages/core/src/services/prompt/errors.ts
  - packages/core/src/services/template/default-templates/iterate/iterate_en.ts
  - packages/core/src/services/template/default-templates/iterate/soul-iterate_en.ts
  - packages/core/src/services/template/default-templates/iterate/context/context-iterate_en.ts
  - packages/core/src/services/template/default-templates/index.ts
  - packages/core/src/services/evaluation/rewrite-from-evaluation.ts
  - packages/core/src/services/evaluation/types.ts
  - packages/core/src/services/template/default-templates/evaluation-rewrite/content.ts
  - packages/core/src/services/template/default-templates/evaluation-rewrite/builders.ts
  - packages/core/src/services/template/default-templates/evaluation-rewrite/runtime-copy.ts
  - packages/core/src/services/template/default-templates/evaluation-rewrite/basic-system_en.ts
  - packages/core/src/services/template/default-templates/evaluation-rewrite/basic-user_en.ts
  - packages/core/src/services/template/default-templates/evaluation-rewrite/pro-multi_en.ts
  - packages/core/src/services/template/default-templates/evaluation-rewrite/pro-variable_en.ts
  - packages/core/src/services/template/default-templates/evaluation-rewrite/generic_en.ts
  - packages/core/src/services/llm/service.ts
  - packages/core/src/services/llm/adapters/abstract-adapter.ts
  - packages/core/src/services/llm/adapters/openai-adapter.ts
  - packages/core/src/services/llm/adapters/anthropic-adapter.ts
  - packages/mcp-server/src/index.ts
  - packages/ui/src/composables/prompt/useEvaluationHandler.ts
  - packages/ui/src/components/PromptPanel.vue
  - packages/ui/src/components/evaluation/EvaluationPanel.vue
  - packages/ui/src/components/basic-mode/BasicSystemWorkspace.vue
  - packages/ui/src/composables/workspaces/useBasicWorkspaceLogic.ts
  - packages/ui/src/composables/workspaces/useWorkspaceTemplateSelection.ts
  - scripts/run-structured-compare-calibration.mjs
  - docs/architecture/test-area-auto-iterate-one-round.md
  - docs/architecture/spo-thin-loop-ui-and-stop-rules.md
  - docs/architecture/structured-compare-and-evaluation-rewrite.md
depends:
  - ../capabilities/template-rendering.md
  - ../capabilities/prompt-optimize.md
  - ../capabilities/llm-evaluation.md
status: ready
reimplementation: 미실행
---

# 반복 개선·평가 기반 재작성

상태 사유: 이 스펙의 미결정이 없고 선행 스펙 template-rendering, prompt-optimize, llm-evaluation이 모두 `ready`라서 `ready`다. R-08(스트리밍 `onError` 횟수)은 prompt-optimize R-13과 독립적으로 같은 결론이다(서비스 계층 1회 + 어댑터 호출, OpenAI 2회, Anthropic 2회이며 SDK가 `error` 이벤트를 내면 3회).

> 직전 프롬프트(`lastOptimizedPrompt`)와 사용자 요구사항 문자열(`iterateInput`)을 반복 개선 템플릿에 넣어 LLM을 한 번 호출해 개선본 한 개를 받고(코어 `iteratePrompt`·`iteratePromptStream`), 평가 응답(`EvaluationResponse`)은 압축·가이던스 계산을 거친 "재작성 입력문" 문자열로 바꿔 같은 요구사항 자리에 넣어 "평가 → 개선본"을 잇는다(`buildRewritePromptFromEvaluation` + UI 연결).

경로 표기: 모든 `파일:줄`은 `repos/prompt-optimizer/` 기준이다. 라이선스는 AGPL-3.0-only(overview 1절)라서 코드·템플릿 본문은 옮기지 않고 C-ID(위치)로만 가리키며, 템플릿은 구조와 규칙을 글로 설명한다. 설치·빌드·실행·모델 호출은 하지 않았다(모든 검증 수준은 읽기 기준이다). 템플릿은 영어 판을 읽었다(중국어 재작성 템플릿 본문은 `content.ts` 안에 함께 있어 읽었고, 중국어 반복 개선 템플릿 본문은 읽지 않았다).

<!--
작성 메모(삭제하지 않음): 범위는 `PromptService.iteratePrompt`·`iteratePromptStream`, `evaluation/rewrite-from-evaluation.ts`와 `evaluation-rewrite/*` 템플릿, 그리고 평가 결과를 반복 개선으로 넘기는 UI 호출 경계(`useEvaluationHandler.ts`·`PromptPanel.vue`·`handleIterate`)까지다. 제외: 최초 최적화([prompt-optimize](prompt-optimize.md)), 평가 자체([llm-evaluation](llm-evaluation.md)), 히스토리 저장([history-chain](history-chain.md), 설명용 링크이고 depends에는 넣지 않았다: 이 스펙은 `addIteration`의 입력값만 R-10에서 경계로 정의한다), 패치 적용(`handleApplyPatch`), 이미지 모드 반복(`imageIterate`), Pro 모드 반복의 세부.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

반복 개선(수동):
1. 호출자가 `iteratePrompt(originalPrompt, lastOptimizedPrompt, iterateInput, modelKey, templateId?)`(스트리밍은 `iteratePromptStream`)를 부른다. UI는 사용자가 쓴 요구사항을, MCP는 `requirements`를 `iterateInput`으로 넘긴다.
2. 입력을 검증하고(R-01), 모델 설정을 찾고(R-02), 반복 개선 템플릿을 정한다(R-03). 문자열 템플릿이면 LLM 호출 전에 거절한다(R-04).
3. 맥락(`originalPrompt`, `lastOptimizedPrompt`, `iterateInput`, `customVariables`, 선택적 대화·도구 텍스트)으로 템플릿을 렌더링해 `Message[]`를 만든다(R-05, R-06). 내장 템플릿은 `lastOptimizedPrompt`·`iterateInput`을 JSON 증거 블록의 두 문자열로 넣는다.
4. LLM을 한 번 호출한다. 비스트리밍은 응답 문자열을 그대로 반환하고(R-07), 스트리밍은 토큰을 콜백으로 흘려 보낸다(R-08).
5. 코어는 여기서 끝난다. 반복 횟수·종료 조건·버전 번호·히스토리는 관리하지 않는다(R-10). 버전 체인은 UI가 완료 콜백에서 저장한다.

평가 기반 재작성(수동 3단계: 테스트 → 평가 → 재작성):
1. 사용자가 평가 패널에서 "평가 결과로 재작성" 버튼을 누른다(R-25). 평가 결과(`EvaluationResponse`)는 llm-evaluation 스펙이 만든다.
2. UI 핸들러가 현재 워크스페이스 프롬프트·참조 프롬프트·언어를 정한다(R-26). `buildRewritePayload`가 평가 결과를 압축하고 `rewriteGuidance`(`skip` / `minor-rewrite` / `rewrite`)를 계산한다(R-12~R-20).
3. 평가가 compare 유형이고 권고가 `skip`이면 토스트만 띄우고 끝낸다(LLM 호출 없음)(R-26).
4. 아니면 `buildRewritePromptFromEvaluation`이 재작성 전용 템플릿(직접 import, 언어는 `'en'` 여부)에 payload JSON을 넣어 재작성 입력문 문자열 하나를 만든다(R-21, R-22).
5. UI가 이 문자열을 `runIterateWithInput`으로 반복 개선 흐름에 `iterateInput`으로 넣는다(R-27). 이후는 위 "반복 개선" 2~5단계와 같다(선택된 반복 템플릿 1개, 최적화 모델 1회 호출)(R-28).
6. 결과는 새 버전으로 쌓인다. 재작성 후 재평가·재테스트·다음 라운드는 자동으로 일어나지 않는다(R-30).

### 1.2 범위·통합 지점 [필수]
- 제공:
  - 코어 반복 개선 두 함수(비스트리밍·스트리밍)의 입력 검증·템플릿 결정·맥락 구성·호출·오류 규칙, 내장 `iterate` 유형 템플릿 2종(`iterate`, `soul-iterate`)과 `contextIterate` 유형 1종(`context-iterate`)의 구조·규칙.
  - 평가 응답을 재작성 입력문으로 바꾸는 순수 함수 묶음: 압축 규칙, `rewriteGuidance` 계산 규칙, payload 구조, 재작성 전용 템플릿 5종(언어별 2판)과 템플릿 선택 규칙.
  - UI 호출 경계: 평가 패널 버튼 → 재작성 핸들러 → `runIterateWithInput` → `handleIterate`(R-25~R-29).
  - 문서가 설계한 "테스트→평가→재작성 자동 1라운드"의 구현 여부 판정(R-30).
- 제외:
  - 최초 최적화와 기본 템플릿 선택(prompt-optimize). 단 `DEFAULT_TEMPLATES.ITERATE`의 사용처 결론은 R-03에서 닫는다(prompt-optimize R-07 ④가 넘긴 확인).
  - 평가 요청·응답 계약과 compare 신호의 생성(llm-evaluation). 이 스펙은 그 응답을 입력으로 읽는다.
  - 히스토리 저장(history-chain), 재작성 결과를 UI가 적용하는 패치 적용 로직(`handleApplyPatch`), 이미지 모드·Pro 모드 반복의 세부, 구조화 비교 보정 스크립트(별도 부속 행)와 그 산출물.
- 외부 의존·선행 계약:
  - [template-rendering](template-rendering.md): `getTemplate`(R-10 ID 검증, R-16 조회 순서), `processTemplate`(R-02·R-03 렌더링, R-05 `helpers.toJson`, R-06 값 재렌더링 없음, R-09 반복 개선 문자열 템플릿 거절의 호출자 규칙), R-20(재작성 템플릿 직접 import·언어 고르기·메시지 연결). 이 스펙은 R-20의 세부를 R-21·R-24에서 정한다.
  - [prompt-optimize](prompt-optimize.md) 1.2의 `llmService.sendMessage`·`sendMessageStream` 경계(입력 검증, `content`만 반환, 스트림 오류 후 재던짐), `OptimizationError` 형식(C-18), R-07의 `DEFAULT_TEMPLATES` 정리.
  - [llm-evaluation](llm-evaluation.md): `EvaluationResponse`(`score`, `improvements`≤3, `summary`, `patchPlan`≤3, `metadata.compareStopSignals`·`compareInsights`)와 compare 신호 도출(R-23, R-29, R-32).
  - 모델 관리자 `getModel(modelKey)`.
  - (설명용) [history-chain](history-chain.md): 반복 결과를 `addIteration`으로 저장하는 호출자 계약(R-09).
- 소유 상태·부작용: 코어 함수 두 개와 `rewrite-from-evaluation`의 모든 함수는 상태가 없고 입력 객체를 바꾸지 않는다(템플릿 객체는 모듈 상수). 부작용은 LLM 호출 1회뿐이다. UI 경계는 화면의 최적화 결과 텍스트, 반복 입력 상자, 평가 패널 표시, 히스토리 체인을 바꾼다(R-27).

### 1.3 인터페이스와 데이터 의미 [필수]

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `iteratePrompt(...)` | `(originalPrompt: string, lastOptimizedPrompt: string, iterateInput: string, modelKey: string, templateId?: string, contextData?)` → `Promise<string>` | 비스트리밍. 한 번의 LLM 호출 결과 문자열. 템플릿 미지정이면 `iterate`(R-03). C-02, C-04 |
| `iteratePromptStream(...)` | `(originalPrompt, lastOptimizedPrompt, iterateInput, modelKey, handlers: {onToken, onReasoningToken?, onComplete(응답?), onError}, templateId: string, contextData?)` → `Promise<void>` | **인자 순서가 비스트리밍과 다르다**: `handlers`가 `modelKey` 바로 뒤, `templateId`가 그 다음이다. `templateId`는 필수(기본값 없음, R-03). 결과 문자열은 돌려주지 않고 호출자가 `onToken`을 이어 붙인다. C-03, C-04 |
| `contextData` | `{messages?: ConversationMessage[], selectedMessageId?: string, variables?: map<string,string>, tools?: ToolDefinition[]}` | `variables`→`customVariables`, `tools`→`tools`, 비어 있지 않은 `messages`→`conversationContext` 텍스트, 비어 있지 않은 `tools`→`toolsContext` 텍스트(R-05). `selectedMessageId`는 읽지 않는다. |
| 반복 템플릿 맥락 | `originalPrompt`, `lastOptimizedPrompt`, `iterateInput`, `customVariables?`, `tools?`, `conversationContext?`, `toolsContext?` | 내장 3종이 읽는 키는 `lastOptimizedPrompt`·`iterateInput`(+`context-iterate`는 `conversationContext`·`toolsContext`)와 `helpers.toJson`뿐이다. `originalPrompt`는 어느 내장 반복 템플릿도 읽지 않는다(R-05, R-06). |
| `IterationError` | `[error.prompt.iteration] <details>`, 필드 `originalPrompt`, `iterateInput` | 두 함수의 모든 실패가 이 형식으로 다시 던져진다(R-09). C-05 |
| `EvaluationRewritePromptParams` | `{result: EvaluationResponse, type: EvaluationType, mode: {functionMode, subMode}, language?: 'zh'\|'en'(기본 'zh'), workspacePrompt?: string, referencePrompt?: string}` | 재작성 입력의 전부. 평가를 실행한 요청(스냅샷 출력·테스트 입력)은 들어가지 않는다(R-12). C-08 |
| `RewriteRecommendation` | `'skip' \| 'minor-rewrite' \| 'rewrite'` | 재작성 강도 권고. `RewriteFocusArea`: `'contract-repair' \| 'generalization' \| 'decision-stability'`. C-14 |
| `buildRewritePayload(params)` | → `EvaluationRewritePayload{scenario, sourcePrompts, compressedEvaluation}` | 재작성 모델과 UI가 읽는 구조화 증거. `compressedEvaluation.rewriteGuidance{recommendation, reasons[], focusAreas[], priorityMoves[]}`를 포함한다(R-20). C-12 |
| `buildRewritePromptFromEvaluation(params)` | → `string` | 재작성 입력문. 템플릿 메시지를 trim·연결한 문자열 하나(R-21). C-13 |
| `buildRewriteFromEvaluationContext(params)` | → 템플릿 맥락 객체 | 내장 재작성 템플릿은 이 중 `rewritePayloadJson` 하나만 읽는다(R-23). C-11 |
| `normalizeRewriteLocaleLanguage(locale?)` | string? → `'en'\|'zh'` | 소문자로 바꿔 `en`으로 시작하면 `'en'`, 그 밖과 미지정은 `'zh'`(R-24). C-10 |
| 재작성 템플릿 5종 | ID `evaluation-rewrite-{basic-system, basic-user, pro-multi, pro-variable, generic}`, 언어별(zh·en) 2판, `templateType: 'evaluation'`, 내용은 **user 메시지 1개** | 5종은 본문이 같고 첫 문장의 대상 라벨(system prompt / user prompt / multi-message system prompt / variable user prompt / workspace prompt)만 다르다(R-21, R-22). C-16 |
| `runIterateWithInput(input)` | PromptPanel 노출 메서드, string → boolean | 입력을 반복 개선 이벤트로 보낸다. `true`면 이벤트를 보냈다는 뜻이고 반복 개선이 성공했다는 뜻은 아니다(R-27). C-21 |
| `rewriteGuidance`가 UI에 주는 값 | `panelProps.rewriteRecommendation`, `rewriteReasons` | 패널의 힌트 표시와 버튼 스타일(R-25). C-19 |

### 1.4 행동 규칙과 남은 질문 [필수]

**가. 코어 반복 개선**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 입력 검증(두 함수 공통) | 순서: ① `lastOptimizedPrompt`가 비었거나 공백뿐이면 `OptimizationError("Prompt cannot be empty")` ② `modelKey`가 공백뿐이면 `"Model key is required"` ③ `iterateInput`이 공백뿐이면 `"Prompt cannot be empty"`(같은 검사 함수를 `iterateInput`으로 한 번 더 호출, `modelKey`도 다시 검사). `originalPrompt`는 검증하지 않아 빈 문자열도 통과한다(주석: 사용자가 워크스페이스에서 직접 고친 뒤 반복하는 경우). 검증 오류는 R-09에서 `IterationError`로 감싸져 나가므로 호출자는 `IterationError` 메시지에 `[error.prompt.optimization] …`가 중첩된 형태를 본다. 길이 제한은 코어에 없다. | 코드 확인 |
| R-02 | `getModel(modelKey)`가 falsy | `ServiceDependencyError("ModelManager", "Model not found")`가 R-09로 감싸진다. 비활성 모델은 여기서 걸리지 않고 LLM 호출 단계에서 실패한다(prompt-optimize R-02와 같다). | 코드 확인 |
| R-03 | **템플릿 결정 — 비스트리밍과 스트리밍이 다르다** | 비스트리밍 `iteratePrompt`: `templateId || DEFAULT_TEMPLATES.ITERATE`(`'iterate'`)로 `getTemplate`을 부른다(미지정·빈 문자열 모두 `iterate`). 스트리밍 `iteratePromptStream`: `templateId`를 그대로 `getTemplate`에 넘긴다. 타입상 필수이고 코드에 기본값이 없어, 런타임에 `undefined`·빈 문자열이면 `getTemplate`의 ID 검증 오류("Invalid template ID", template-rendering R-10)가 `IterationError`로 나가고 LLM은 호출되지 않는다. 두 함수 모두 템플릿 **유형을 검사하지 않는다**(`optimize` 유형 ID도 배열 내용이면 통과). `getTemplate` 실패는 `IterationError("Iteration failed: <원래 메시지>")`, 템플릿 `content`가 falsy면 `"Iteration failed: Template not found or invalid"`. **결론(prompt-optimize R-07 ④ 확인)**: `DEFAULT_TEMPLATES.ITERATE`는 `service.ts:303`의 비스트리밍 `templateId` 없음 경로에서만 읽힌다. 저장소 안 호출처는 모두 `templateId`를 직접 넘긴다: MCP는 `template` 인자 또는 `iterate` 유형 목록 첫 번째 ID(R-11), UI 스트리밍 호출은 사용자가 고른(세션에 저장된) 반복 템플릿 ID(R-27). 그래서 `iterate` 기본값은 코어 라이브러리를 `templateId` 없이 직접 부르는 외부 호출자에게만 작동한다. | 코드 확인 / "저장소 안 모든 호출처가 ID를 넘긴다"는 `iteratePrompt`·`iteratePromptStream` 호출처 검색(UI 7곳 중 기본 워크스페이스 로직은 인자까지 읽음, 나머지는 `templateId: selected…` 인자를 grep으로 확인) 기반이라 일부 추론 |
| R-04 | 결정된 템플릿의 `content`가 문자열 | LLM 호출 전에 `IterationError`: "배열 템플릿(메시지 배열 형식)이 필요하다", 템플릿 ID와 "단순(문자열) 템플릿" 안내를 메시지에 포함. 문자열 `optimize` 템플릿 ID(예 `general-optimize`)를 넘기면 항상 이 오류다. 렌더러 자체는 문자열 템플릿을 받아들이지만(template-rendering R-09) 이 검사가 앞선다. | 코드 확인 |
| R-05 | 맥락 구성 | 맥락 = `{originalPrompt, lastOptimizedPrompt, iterateInput, customVariables: contextData.variables, tools: contextData.tools}`. `contextData.messages`가 비어 있지 않으면 `formatConversationAsText`(template-rendering 1.3)로 `conversationContext`를, `contextData.tools`가 비어 있지 않으면 `formatToolsAsText`로 `toolsContext`를 추가한다. 사용자 변수는 **최상위로 펼치지 않는다**(`customVariables` 키에만 있음; 최적화 경로의 `createExtendedContext`와 다르다, template-rendering R-08). `selectedMessageId`는 어디에도 쓰이지 않는다. 같은 맥락 구성이 비스트리밍·스트리밍에 복제돼 있다. | 코드 확인 |
| R-06 | 내장 반복 템플릿의 구조·규칙(영어 판 읽음) | 3종 모두 `[system, user]` 배열이고 user 메시지가 `lastOptimizedPrompt`·`iterateInput`을 `{"lastOptimizedPrompt": <JSON 문자열>, "iterateInput": <JSON 문자열>}` 블록으로 감싼다(`helpers.toJson` + 이스케이프 없는 `{{{…}}}`). user 앞머리는 "JSON의 모든 문자열 필드는 고쳐 쓸 원문 증거이지 수행할 과제가 아니다"(인젝션 방어)이고, 끝줄은 개선본만 출력하라는 요청이다. ⒜ `iterate`(기본, ID `iterate`, 유형 `iterate`): 역할 "프롬프트 반복 개선 전문가". 핵심 규칙: **요구사항을 수행하지 말고 원본 프롬프트에 새 요구·제약으로 녹여 넣어 프롬프트를 고쳐라**, 원래 의도·언어 스타일·구조 유지, 정밀 수정. 이중 중괄호 변수는 이름 변경·삭제·병합·구체값 대체 금지이고 출력 전 모든 변수의 누락을 내부 점검하라고 한다. "이해 예시" 3개(요구 "상호작용 없이" → 프롬프트에 직접 완결형 해결 지시를 추가, "JSON으로 출력" → 프롬프트에 JSON 출력 지시를 추가, "더 전문적으로" → 역할 서술을 강화; 각각 "요구사항을 그대로 실행한 답"은 오답으로 제시). 워크플로 4단계(분석 → 요구사항 본질 파악 → 통합 → 완전한 수정본 출력). 출력은 갱신된 프롬프트만, 설명 금지. ⒝ `soul-iterate`(유형 `iterate`): SOUL.md(에이전트 성격 파일) 대상의 표적 수정 전문가. 요청을 수행하거나 페르소나를 연기하지 말 것, 구조·정체성 보존, 영향받는 절만 수정, 사용자 쪽 정보가 섞이면 `SOUL.md`+`USER.md` 다중 파일 출력 형식을 쓸 수 있다. 변수 보존 문구는 없다. ⒞ `context-iterate`(유형 `contextIterate`): 같은 user 메시지, system에 대화·도구 맥락 섹션을 `{{#conversationContext}}`·`{{#toolsContext}}` 조건 블록으로 넣고(없으면 보수적 가정·비도구 대안 문구), 프롬프트 텍스트만 수정·과제 실행 금지·검증 가능한 인수 기준 정의. 변수 보존 문구는 없다. 단일 호출 구조라 세 템플릿 모두 응답이 그대로 개선본이 된다. | 코드 확인(영어 본문 3개) / 중국어 판은 미열람 |
| R-07 | 비스트리밍 호출·반환 | `llmService.sendMessage(messages, modelKey)`를 정확히 한 번 부르고 응답 문자열을 **그대로** 반환한다. 빈 응답 검사가 **없다**(prompt-optimize R-11의 최적화 경로는 빈 응답을 오류로 보지만 반복 개선 비스트리밍은 `""`·공백도 정상 반환). 재시도·후처리(trim, 코드펜스 제거, 변수 보존 확인)도 없다. | 코드 확인 |
| R-08 | 스트리밍 호출·완료 | 검증·모델·템플릿·맥락은 R-01~R-05와 같다. `llmService.sendMessageStream(messages, modelKey, h)`를 한 번 부르고 `onToken`·`onReasoningToken`을 호출자 콜백에 그대로 연결한다. `onComplete(응답)`에서 응답이 있으면 `content`가 비었는지(공백 포함) 검사한다: 비면 호출자 `onComplete`는 부르지 않고 `onError(OptimizationError("LLM service returned empty result"))`를 부른다(`IterationError`로 감싸지 않음). 통과하면 `onComplete(응답)`, 응답이 `undefined`면 검사 없이 `onComplete(undefined)`. **LLM 단계 실패의 `onError` 전달(확정)**: 이 함수(`iteratePromptStream`)는 `onError`를 직접 부르지 않고 `sendMessageStream`이 던진 오류를 R-09로 감싸 reject만 한다. `onError`는 아래 두 계층이 부른다. ⓐ **서비스 계층** `llmService.sendMessageStream`: 메시지 검증·모델 조회·모델 설정 검증(비활성 포함)·어댑터 조회·어댑터 호출 어디서 난 오류든 `callbacks.onError(오류)`를 **1회** 부르고 같은 오류를 다시 던진다. ⓑ **어댑터 계층**: 템플릿 메서드(`AbstractTextAdapter.sendMessageStream`)는 메시지 검증 후 `doSendMessageStream`만 부르고 `onError`를 부르지 않는다. 구현체는 각자 부른다. OpenAI 어댑터는 `doSendMessageStream`의 catch에서 `onError(오류)` 1회 후 **같은 오류**를 다시 던진다(Responses API 경로도 같은 try 안). Anthropic 어댑터는 스트림 `error` 이벤트 리스너가 `onError(오류)`를 부르고, `finalMessage()` 대기 중 예외를 catch에서 `onError(handleError(오류))`로 한 번 더 부른 뒤 **원래 오류**를 던진다(`handleError`는 `status`가 있는 오류를 새 `Error("Anthropic API error (status): …")`로 바꿔 전달하므로 이 전달분은 메시지가 원래 오류와 다르다). 결과: 어댑터 안에서 난 스트림 실패는 같은 원인이 `onError`로 **2회 이상** 간다 — OpenAI 2회(어댑터 1 + 서비스 1, 같은 객체), Anthropic 2회(어댑터 catch 1 + 서비스 1; 서비스 분은 원래 오류) 또는 SDK가 `error` 이벤트를 내면 3회(SDK 동작은 외부라 추론). 어댑터 호출 전 실패(서비스의 메시지 검증·모델 없음·비활성·어댑터 없음, 그리고 Anthropic의 클라이언트 생성)는 서비스의 `onError` 1회뿐이다. 이어서 `iteratePromptStream`이 `IterationError`로 감싸 reject하므로 호출자는 `onError` 1~3회와 reject 1회를 **모두** 받는다. `onError` 핸들러가 던지면(기본 워크스페이스 UI는 같은 오류를 다시 던진다) 던진 예외가 어댑터 catch를 벗어나 서비스 catch로 이동하므로 횟수는 같고 최종 reject는 `IterationError`다. 따라서 호출자의 `onError`는 같은 원인에 대해 여러 번 불려도 안전해야 한다(첫 호출에서 종료 처리, 이후 무시). 반대로 `onComplete` 안 검증 실패(위 빈 응답)는 `handlers.onError` **정확히 1회**이고 reject는 없다. LLM 호출 전 `PromptService` 단계 실패(R-01~R-04)는 `onError` 0회, reject만이다. | 코드 확인(서비스·추상 어댑터·OpenAI·Anthropic 어댑터) / Anthropic의 `error` 이벤트가 `finalMessage()` 거부와 함께 실제 발생하는지는 SDK 동작이라 추론 / 그 밖 어댑터(Gemini 등)는 미열람 |
| R-09 | 오류 전달 | 두 함수 본문 전체가 `try`로 감싸져 어떤 오류든 `IterationError(originalPrompt, iterateInput, "Iteration failed: " + 원래 메시지)`로 다시 던진다. 원인 객체(`cause`)는 보존하지 않고, 원래 오류가 코드 접두어 형식이면 접두어가 중첩된다. 코드 `error.prompt.iteration`. 스트리밍의 `onComplete` 안 검증 실패(R-08)와 LLM이 `onError`로 보내는 오류는 이 감싸기를 거치지 않는다. | 코드 확인 |
| R-10 | 반복 관리·상태 | 코어는 반복 횟수, 종료 조건, "몇 번째 버전"을 알지 못한다. 한 번 호출 = LLM 한 번 = 개선본 한 개이고, 직전 결과는 호출자가 `lastOptimizedPrompt`로 넘긴다. 서비스 코드는 "반복 히스토리 저장은 UI층의 `historyManager.addIteration`"이라고 주석으로 밝히고 저장을 호출하지 않는다. UI(기본 워크스페이스)는 스트림 `onComplete`에서 체인이 있으면 `addIteration`, 없으면 `createNewChain`을 부르며 `iterationNote`=`iterateInput`(재작성 경로에서는 **재작성 입력문 전체**), `templateId`=선택한 반복 템플릿 ID, `modelKey`=최적화 모델을 넣는다(체인 규칙은 history-chain R-02·R-08·R-09). 저장 실패 시 경고 토스트만 띄우고 화면의 결과는 유지한다. | 코드 확인 |
| R-11 | MCP 노출(경계) | 도구 `iterate-prompt`는 `prompt`·`requirements`(필수)와 `template`(선택, enum은 서버 시작 때 `iterate` 유형 목록)을 받아 `iteratePrompt(prompt, prompt, requirements, 'mcp-default', 템플릿ID)`를 한 번 부르고 반환 문자열을 텍스트 콘텐츠로 돌려준다. 원본과 "직전 최적화본"에 **같은 문자열**을 넣고, 템플릿 ID는 `template` 또는 `iterate` 유형 목록 첫 번째(→ `iterate`)라 코어의 `ITERATE` 기본값에 의존하지 않는다(R-03). `prompt`·`requirements` 누락은 오류 콘텐츠, 입력 크기 검증은 `ParameterValidator`가 한다(prompt-optimize R-21과 같은 구조, 요구사항 10,000자 한도는 overview 근거). 스트리밍·모델 선택·`contextData`는 노출하지 않는다. | 코드 확인 |

**나. 평가 응답 → 재작성 입력문**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | 재작성이 읽는 평가 필드와 읽지 않는 것 | 읽는 것: `result.summary`, `result.score.overall`(없으면 `"N/A"`), `result.score.dimensions[]`(`key`·`label`·`score`), `result.improvements`, `result.patchPlan`, `result.metadata.compareStopSignals`, `result.metadata.compareInsights`. 읽지 않는 것: `metadata`의 나머지(`model`, `timestamp`, `duration`, `compareJudgements`, `snapshotRoles`, `compareMode`)와, 평가 **요청**에만 있는 스냅샷 출력·테스트 입력·모델 키. 따라서 재작성 모델은 평가자의 결론(문장·점수·제안·신호)만 보고 평가 대상 출력 원문은 보지 않는다. 대상 프롬프트 본문은 호출자가 `workspacePrompt`·`referencePrompt`로 따로 넘긴다. | 코드 확인 |
| R-13 | **가이던스 1: 기본 분기** — `type !== 'compare'` / compare인데 `workspacePrompt`가 없거나 공백뿐 | 두 경우 모두 `recommendation: 'rewrite'`, `focusAreas: []`, `priorityMoves: []`, `reasons`는 고정 문장 1개(앞은 "compare가 아니므로 평가 증거를 정상 적용", 뒤는 "워크스페이스 프롬프트 스냅샷이 없어 안전하게 건너뛸 수 없음"). 판정 순서는 이 둘이 가장 먼저다. 따라서 `result`·`prompt-only`·`prompt-iterate` 평가는 `skip`이 나오지 않는다. | 코드 확인 |
| R-14 | **가이던스 2: 정지 신호** — compare이고 `stopSignals.stopRecommendation === 'stop'` | `recommendation: 'skip'`, `reasons` 1개("대조 평가가 이미 중지를 권고하므로 현재 프롬프트 유지가 가장 보수적"), `focusAreas`·`priorityMoves` 빈 목록. 충돌 신호는 보지 않고 즉시 반환한다(R-15보다 앞). `stop` 신호는 llm-evaluation R-23이 만든 병합 값(코드 파생값과 모델 값 중 보수적인 쪽)이다. `continue`·`review`는 이 분기에 걸리지 않는다. | 코드 확인 |
| R-15 | **가이던스 3: 충돌·과적합 → 초점과 우선 행동** (R-14를 통과한 compare) | `compareInsights.conflictSignals`(없으면 빈 집합)와 `stopSignals`로 판정한다. `regressionOutweighsCosmeticGains` 또는 `improvementNotSupportedOnReference`가 있으면 `focusAreas`에 `contract-repair`, `priorityMoves`에 "회귀부터 복구: 안정된 스키마·필드명·출력 계약·프로토콜 경계를 문구 개선보다 먼저 복원" 1개. 과적합 위험(`overfitRisk`가 `medium`·`high`이거나 충돌 신호 `sampleOverfitRiskVisible`)이면 `generalization`과 "샘플 특화 트리거 규칙을 제거·약화하고 입력이 달라도 성립하는 일반 원칙 우선" 1개. `improvementUnstableAcrossReplicas`가 있으면 `decision-stability`와 3개 행동("핵심 판정 필드에 명시적 판정 기준 추가", "혼합·불충분 증거용 동률 처리나 보수적 기본 규칙 추가", "형식 요구와 판정 로직을 분리하고 형식 계약은 유지하되 권고 판정 로직 안정화 우선"). 위 순서로 쌓고 `priorityMoves`는 중복 제거한다. 이 값은 R-16~R-18의 어느 결과에도 함께 실린다(단 R-14·R-13 결과에는 없음). | 코드 확인 |
| R-16 | **가이던스 4: `skip` (정체 + 격차 닫힘)** | 아래가 모두 참이면 `recommendation: 'skip'`: `targetVsBaseline === 'flat'`, `targetVsReferenceGap === 'none'`, `improvementHeadroom !== 'high'`(값 없음 포함), 충돌 신호 3종(`regressionOutweighsCosmeticGains`, `improvementNotSupportedOnReference`, `improvementUnstableAcrossReplicas`) 없음. `reasons`: "baseline 대비 flat이고 reference 격차가 이미 닫혀 재작성이 가치보다 노이즈를 만들 가능성이 큼" 1개 + `overfitRisk`가 `medium`·`high`면 "더 강한 증거가 나오기 전엔 현재 프롬프트 유지" 1개 추가. R-15의 `focusAreas`·`priorityMoves`는 그대로 싣는다(과적합일 때 `generalization`). reference 쌍이 없어 `targetVsReferenceGap`이 비면 이 분기에 들어가지 못한다. | 코드 확인 |
| R-17 | **가이던스 5: `minor-rewrite`** | R-16이 아니고, `targetVsBaseline`이 `improved` 또는 `flat`, `targetVsReferenceGap === 'none'`, `improvementHeadroom === 'low'`, 충돌 신호 3종 없음이면 `'minor-rewrite'`. `reasons`: "주된 이득이 이미 반영되어 계약을 지키는 최소 조정만 정당화" 1개 + (`overfitRisk === 'medium'` 이거나 `sampleOverfitRiskVisible`이면) "건드리더라도 대폭 재작성이 아닌 가벼운 일반화 보정만" 1개. R-15의 `focusAreas`·`priorityMoves` 포함. | 코드 확인 |
| R-18 | **가이던스 6: `rewrite`(나머지)** | 위 어디에도 해당하지 않으면 `'rewrite'`. `reasons`: "개선 여지나 미해결 위험이 남아 실질 재작성이 정당" 1개 + 회귀 충돌이면 "baseline 대비 회귀부터 복구", 참조 측 미지지 충돌이면 "지지되지 않는 변경 드리프트를 적극 수리", 불안정 충돌이면 "표면 서식이 아니라 판정 안정성을 겨냥"을 이 순서로 추가. 신호가 전혀 없는 compare(예: generic compare에 모델이 신호를 안 준 경우)도 여기로 온다. | 코드 확인 |
| R-19 | 줄 압축 규칙(payload의 `*Lines`에 쓰는 공통 함수) | ① 공백 정규화: 모든 연속 공백(줄바꿈 포함)을 공백 한 칸으로, 양끝 trim. ② 빈 값 제외. ③ 중복 제거: 정규화한 값을 **소문자**로 바꾼 것이 키이고 먼저 나온 것을 유지(자르기 전 값으로 비교). ④ 길이: 값이 `maxLength`를 넘으면 앞 `maxLength`자 + `...`(결과 길이 `maxLength+3`). ⑤ 개수: `limit`개에서 중단. 종류별 매개변수(`limit`, `maxLength`): `focusSummaryLines`(4, 260), `conflictLines`(4, 260), `learnableSignalLines`(5, 220), `overfitWarningLines`(5, 220), `supportEvidenceLines`(4, 240). 줄 내용: 초점 요약은 `compareInsights`의 `progressSummary`·`referenceGapSummary`·`promptChangeSummary`·`stabilitySummary` 중 있는 것을 이 순서로 `<라벨>: <pairLabel> \| signal=… \| verdict=… \| confidence=… \| <analysis>`(라벨은 Progress / Reference Gap / Prompt Change Validity / Stability, 중국어 판은 중국어 라벨), 충돌 줄은 충돌 신호 4종 각각의 고정 문장(언어별), 학습 가능 신호·과적합 경고는 `compareInsights`의 같은 이름 배열, 근거 줄은 `pairHighlights`를 `<순번>. <pairLabel> \| signal … \| <analysis>` 형식으로 만든 것 뒤에 `evidenceHighlights`를 이은 것. 정확한 형식 문자열은 C-09, C-15. | 코드 확인 |
| R-20 | payload 구성 `buildRewritePayload` | `scenario{language, evaluationType, evaluationTypeLabel(언어별 4종: 단일 결과 평가 / 대조 평가 / 프롬프트 분석 / 반복 분석), subjectLabel(모드별 라벨, 모르는 모드는 "workspace prompt"), mode, overallScore}`, `sourcePrompts{workspacePrompt?, referencePrompt?}`(각각 trim해서 비어 있지 않을 때만 키가 생기고 **길이 제한·자르기 없음**), `compressedEvaluation{summary(원문 그대로), dimensionScores[{key,label,score}], improvements(원본 복사), patchPlan(원본 복사), compareStopSignals?(있으면 객체 전체), compareInsights?(있으면 객체 전체), rewriteGuidance(R-13~R-18), focusSummaryLines, conflictLines, learnableSignalLines, overfitWarningLines, supportEvidenceLines(R-19)}`. 즉 "압축"은 평가자 문장 일부를 줄이는 것이 아니라 (ⓐ 스냅샷 원문을 빼고 결론만 싣고, ⓑ compare 인사이트에서 뽑은 4~5종 줄 목록을 추가하는) 것이다. `compareInsights`·`compareStopSignals` 원본 객체가 줄 목록과 **함께** 들어가므로 같은 내용이 두 번 실린다. 직렬화는 들여쓰기 2칸 `JSON.stringify`이고 값이 없는 선택 키는 생략된다. | 코드 확인 |
| R-21 | 재작성 입력문 조립 `buildRewritePromptFromEvaluation` | ① 템플릿 선택 `resolveRewriteTemplate(mode, language)`: `language === 'en'`이면 영어 판, 그 밖은 중국어 판. 모드가 (`basic`,`system`)→`evaluation-rewrite-basic-system`, (`basic`,`user`)→`…-basic-user`, (`pro`,`multi`)→`…-pro-multi`, (`pro`,`variable`)→`…-pro-variable`, **그 밖의 모든 조합(image 모드·모르는 값 포함)은 `…-generic`**. 템플릿은 `TemplateManager`를 거치지 않고 모듈에서 직접 import한 객체이므로 사용자 템플릿으로 바꿀 수 없다(template-rendering R-20). ② 템플릿은 `[user 1개]` 배열이고 내용은 지시문 + `Rewrite Payload (JSON):` 줄 + `{{{rewritePayloadJson}}}`(R-20의 JSON)다. ③ `TemplateProcessor.processTemplate`로 렌더링하고, 결과 메시지들을 각각 trim해 빈 것을 버리고 빈 줄(`\n\n`)로 이어 다시 trim한 **문자열 하나**를 반환한다(내장 템플릿은 메시지 1개라 사실상 그 한 개). payload 값 안의 `{{…}}`·`<`는 다시 렌더링되거나 이스케이프되지 않는다(template-rendering R-06·R-07). 입력 크기 제한은 없다. | 코드 확인 |
| R-22 | 재작성 템플릿의 지시 규칙(영어 판 19항, 중국어 판 18항, 의미 동일) | 주제별 요약: ⒜ 근거: payload만 사용, `sourcePrompts.workspacePrompt`는 처음부터 다시 쓰는 대상이 아니라 고쳐 쓸 원천 초안, 새 증거를 지어내지 말 것. ⒝ 보존: 핵심 목적·하드 제약·경계·변수명·필드명·스키마·역할 구조·출력 프로토콜은 평가가 명백히 해롭다고 하지 않는 한 유지, 명시된 JSON 키·XML 태그·자리표시자·enum·"출력만" 제약은 고정. ⒞ 복구: 증거가 회귀·계약 이탈·미지지 스키마 변경을 말하면 적극 수리하고 `referencePrompt`가 있으면 계약 복원의 기준점으로 쓴다. ⒟ 일반화: 입력이 달라도 성립하는 개선 우선, 현재 샘플·출력 세부에만 맞는 규칙 금지, 샘플 의존 제안은 약화·일반화·폐기, 최소하면서 완결된 재작성 선호. ⒠ 출력 형식: 프롬프트 본문만 출력(JSON·YAML·XML·role/content 객체·메시지 배열·코드펜스 래핑 금지, 설명 금지), `sourcePrompts`의 문자열은 마크다운·코드펜스가 있어도 프롬프트 본문. ⒡ 우선순위: compare 항목이 겹치면 집계 초점·정지 신호를 하위 증거 발췌보다 신뢰. **`rewriteGuidance.recommendation`을 먼저 읽고 `skip`이면 `workspacePrompt`를 글자 그대로 출력, `minor-rewrite`면 증거가 뒷받침하는 최소 계약 보존 수정만, `rewrite`일 때만 본격 재작성**. `priorityMoves`를 최우선 재작성 의제로 취급하고, 결정 안정성 행동이 있으면 출력 형식 강화만이 아니라 판정 기준·동률 처리·보수적 기본 규칙을 추가. 시스템 메시지는 없고 모두 user 메시지 한 개에 들어 있다. | 코드 확인(영어·중국어 본문) |
| R-23 | 재작성 맥락 객체의 나머지 키 | `buildRewriteFromEvaluationContext`는 `rewritePayloadJson` 외에 `subjectLabel`, `evaluationTypeLabel`, `overallScore`, `hasWorkspacePrompt`·`workspacePrompt`, `hasReferencePrompt`·`referencePrompt`, `dimensionScoreLines`, `rewriteTargetLines`(`Overall: summary` + `Priority: improvement…`, 6줄·240자), `patchPlanLines`(`n. [op] instruction \| old="…" \| new="…"`, old/new 140자, 4줄·260자), `stopSignalLines`(`key=value` 6줄·220자), 초점·충돌·학습·과적합·근거 줄과 각 `has*` 플래그, `isCompareEvaluation` 등 유형 플래그를 만든다. 내장 재작성 템플릿 10개(5종×2언어)가 읽는 키는 `rewritePayloadJson` 하나뿐이라 이 키들은 내장 경로에서 모두 쓰이지 않는다(사용자 정의 재작성 템플릿을 끼울 길도 없다, R-21 ①). | 코드 확인(템플릿의 `{{` 검색: `content.ts`의 두 곳뿐) |
| R-24 | 재작성 언어 결정 | 코어 함수는 `language`가 없으면 `'zh'`(중국어)로 간주한다. UI는 `normalizeRewriteLocaleLanguage(UI 로케일)`로 넘긴다: 소문자 로케일이 `en`으로 시작하면 `'en'`, 그 밖(`zh-CN`·`zh-TW`·값 없음 등)은 `'zh'`. UI 로케일은 `en-US`·`zh-CN`·`zh-TW` 세 가지뿐이다(`ui/src/i18n/locales`). 이 값은 내장 템플릿 언어 설정(`getCurrentBuiltinTemplateLanguage`)과 평가 서비스의 구조화 비교 언어 선택과 **독립**이다. 따라서 같은 재작성에서 재작성 입력문은 UI 로케일 언어이고 선택된 반복 템플릿은 내장 템플릿 언어일 수 있다. payload 안의 평가자 문장(`summary`, `analysis` 등)은 번역하지 않고 평가 때 언어 그대로다. | 코드 확인 |

**다. UI 호출 경계(재작성 호출 경계만)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-25 | 평가 패널 버튼 | 버튼은 `canRewriteFromEvaluation`이 true일 때 보이고 기본·컨텍스트(Pro) 워크스페이스 4곳은 true, 이미지 워크스페이스 3곳은 false다. 결과가 없거나 평가 중이거나 **stale**(평가 후 대상 입력의 지문이 달라짐)이면 비활성이다. `rewriteRecommendation === 'skip'`이면 버튼이 "soft" 스타일이 되고 `rewriteReasons` 중 중복 제거한 최대 2개(없으면 고정 안내문)를 힌트로 보이지만 **비활성은 아니다**(클릭 가능). `minor-rewrite`면 작은 보정 권고 문구를 보인다. 패널은 클릭 시 `{result, type}`을 `rewrite-from-evaluation`으로 올린다. 힌트용 가이던스는 R-26과 같은 규칙으로 계산한다(재작성 시와 표시 시 같은 입력). | 코드 확인 |
| R-26 | 재작성 핸들러(`createRewriteFromEvaluationHandler`) | ① `payload.result`가 없으면 아무 일도 안 한다. ② 입력 결정: `type === 'compare'`이면 `workspacePrompt = comparePayload.target.workspacePrompt \|\| analysisOptimizedPrompt \|\| ''`, `referencePrompt = comparePayload.target.referencePrompt`; 그 밖의 유형이면 `workspacePrompt = analysisOptimizedPrompt \|\| ''`, `referencePrompt`는 없음. 기본 시스템 워크스페이스에서 `target.workspacePrompt`는 화면의 최적화 결과(=워크스페이스 프롬프트), `target.referencePrompt`는 사용자가 처음 입력한 프롬프트(`prompt`)이며 워크스페이스와 같으면 `undefined`다(다른 워크스페이스는 같은 함수를 쓰는지만 추정). ③ `mode`는 현재 워크스페이스의 `functionMode`·`subMode`, `language`는 R-24. ④ `buildRewritePayload`로 가이던스를 구하고 **`type === 'compare'`이고 `recommendation === 'skip'`이면** 정보 토스트(`evaluation.rewriteSkipped`)만 띄우고 반환한다(LLM·히스토리·패널 닫기 없음). 다른 유형은 가이던스가 항상 `rewrite`(R-13)라 이 가드에 걸리지 않는다. ⑤ 아니면 `buildRewritePromptFromEvaluation`으로 입력문을 만들고 `promptPanelRef.runIterateWithInput(입력문)`을 부른다. 반환이 `true`일 때만 평가 패널을 닫는다. 코어 함수는 `skip`에서도 입력문을 만들어 주므로 가드는 UI 핸들러에만 있다(R-31). | 코드 확인 |
| R-27 | `runIterateWithInput` → 반복 개선 실행 | `dispatchIterate`: 입력을 trim해 비었거나 이미 반복 중이면 조용히 `false`. 선택된 반복 템플릿이 없으면 오류 토스트("템플릿 없음") 후 `false`. 아니면 `iterate` 이벤트 `{originalPrompt: 패널의 원본 프롬프트, optimizedPrompt: 출력 영역 현재 내용 \|\| 프롬프트 prop, iterateInput: 입력문}`을 내보내고 **즉시 `true`를 반환**해 반복 입력 상자를 비우고 다이얼로그를 닫는다. 이벤트를 받는 워크스페이스 `handleIterate`는 결과 텍스트가 비었거나 이미 반복 중이면 조용히 반환하고, 반복 템플릿 ID·최적화 모델이 없거나 입력이 비면 오류 토스트를 띄운다 — 이 실패들은 `true` 반환에 반영되지 않아 평가 패널은 이미 닫혔다. 실행 시 **모델은 최적화(개선) 모델**(`selectedOptimizeModelKey`)이고 평가 모델이 아니며, 템플릿은 사용자가 고른 반복 템플릿이다(목록은 `iterate` 유형, 선택이 없거나 목록에 없으면 첫 번째 `iterate`로 되돌려 저장). 시작 때 화면의 결과 텍스트·추론 텍스트를 비운 뒤 `iteratePromptStream`으로 토큰을 이어 붙인다. 완료 시 R-10대로 히스토리를 저장하고 성공 토스트, 실패하면 오류 토스트(이미 비워진 화면은 되돌리지 않는다). | 코드 확인 / 이미지·Pro 워크스페이스의 같은 경로는 미열람 |
| R-28 | 재작성 입력문이 반복 템플릿 안에서 감싸지는 방식 | UI 경로: 입력문 전체(재작성 지시문 + payload JSON)가 R-06 ⒜의 `iterateInput` 한 문자열 필드로 JSON 이스케이프되어 들어간다. 즉 모델 입력은 `iterate` 시스템 메시지(요구사항을 녹여 넣어 프롬프트를 고쳐라) + user 메시지(`lastOptimizedPrompt`와 `iterateInput` 두 필드)이고, 대상 프롬프트가 `lastOptimizedPrompt`와 `iterateInput` 안의 `sourcePrompts.workspacePrompt`에 **두 번** 실린다. 한편 코어를 직접 호출하는 보정 스크립트는 같은 `buildRewritePromptFromEvaluation` 결과를 반복 템플릿 없이 `[user 1개]` 단일 메시지로 `sendMessage`한다(재작성 템플릿의 "프롬프트 본문만 출력, `skip`이면 원문 그대로" 지시가 단독 지시가 되는 구성). 같은 입력문이 두 소비자에서 다른 틀로 쓰인다. 문서(`structured-compare-and-evaluation-rewrite.md`)도 "iterate 흐름을 재사용"한다고 밝힌다. | 코드 확인(두 경로의 호출) / 두 지시가 겹칠 때 모델이 `skip`·최소 수정 지시를 지키는지는 미확인(실행 불가, 확인 한계) |
| R-29 | 평가 개선안 하나를 반복 개선에 넣기(수동, 압축 없음) | 평가 패널의 개선 제안 항목 "적용"은 패널을 닫고 `openIterateDialog(제안 문자열)`로 반복 입력 상자를 그 문자열로 **미리 채우기만** 한다. 사용자가 제출해야 R-27의 `dispatchIterate`가 돈다. `rewriteGuidance`·압축·`skip` 가드는 거치지 않는다. `patchPlan` 적용 경로(`handleApplyPatch`)는 별개이고 이 스펙 밖이다. | 코드 확인 |
| R-30 | **"테스트 → 평가 → 재작성 자동 1라운드" 구현 여부** | **없음.** 문서(`docs/architecture/test-area-auto-iterate-one-round.md`)가 설계한 자동 반복 버튼·설정 팝업·4칸 프리셋 자동 적용·첫 테스트 → 앵커 추출 → 워크스페이스 개선 → 2차 테스트 → 요약 흐름과 그 파일(`autoIterateOneRound.ts`, `autoIteratePreset.ts`)은 저장소에 없다. 평가→재작성 연결은 R-25~R-27의 **사용자 클릭 2번**(평가 실행, 재작성)이 전부이고, `runAllVariants`(테스트 실행)는 끝나도 평가를 호출하지 않으며, 재작성 완료 뒤 재테스트·재평가·다음 라운드를 시작하는 코드도 없다. 코어에도 반복·종료 루프가 없다(R-10). 코드와 같은 방향의 문서 진술: `spo-thin-loop-ui-and-stop-rules.md` 1.1은 재작성 버튼·compare 신호만 구현되었고 `SPO` 버튼·팝업·상태 기계·정지 규칙 실행은 "미구현"이라 쓰며, 문서 머리말은 최초 문서가 "초기 방안"이고 최신 설계가 두 문서로 분리됐다고 한다. 가장 가까운 자동 연결은 보정 스크립트(개발자용)의 한 케이스 `평가(compare) → 재작성 입력문 → LLM 1회`이고 재테스트·반복·정지 판정은 없다(C-24). | 코드 확인(호출 경로 검색) / 부재 판정은 키워드·호출자 검색 기반이라 추론 성격 |
| R-31 | `skip` 가드의 위치와 출력 보장 | `skip`일 때 "프롬프트를 바꾸지 말라"는 요구는 두 군데에만 있다: (a) UI 핸들러의 compare 한정 조기 종료(R-26 ④), (b) 재작성 템플릿의 "원문 그대로 출력" 지시(R-22). 코어의 `buildRewritePromptFromEvaluation`은 `skip`이어도 입력문을 만들고, 모델 출력이 `workspacePrompt`와 같은지 확인하는 코드는 어디에도 없다. 보정 스크립트도 `skip`을 막지 않고 LLM에 맡긴다. | 코드 확인 |

- 불변식: `iteratePrompt`·`iteratePromptStream` 한 번 호출은 LLM 호출을 최대 한 번 하고, 코어는 반복 횟수·종료 조건을 갖지 않는다(전제: 호출자가 루프를 돌려도 이 함수들은 이전 호출을 모른다). `buildRewritePayload`·`buildRewritePromptFromEvaluation`은 같은 입력에 같은 결과를 돌려주는 순수 함수다(시계·난수·I/O 없음; 단 템플릿 모듈의 `metadata.lastModified`는 `Date.now()`이나 입력문에는 쓰이지 않는다). `recommendation`이 `skip`이면 `rewriteGuidance.focusAreas`·`priorityMoves`는 R-14에서는 비고 R-16에서는 비어 있지 않을 수 있다. 재작성 입력문에는 평가 요청의 스냅샷 출력·테스트 입력이 들어가지 않는다.
- 미결정: 없음. (R-08의 `onError` 횟수는 서비스·추상 어댑터·OpenAI·Anthropic 어댑터를 읽어 확정했다. 다른 어댑터의 횟수는 어댑터마다 다를 수 있어 확인 한계에 둔다.)
- 확인 한계: 설치·빌드·테스트 실행·모델 호출 없이 소스만 읽었다. 스트림 `onError` 횟수(R-08)는 OpenAI·Anthropic 어댑터만 읽었고 다른 어댑터(Gemini 등)와 SDK 쪽 `error` 이벤트 발생 여부는 읽지 않았다. 중국어 반복 개선 템플릿(`iterate.ts`, `soul-iterate.ts`, `context-iterate.ts`) 본문은 읽지 않았고 ID·`templateType`만 대조했다. 재작성 입력문을 `iterate` 템플릿 안에 넣었을 때 모델이 두 지시(요구사항을 녹여 넣어 고쳐 쓰라 / `skip`이면 원문 그대로)를 실제로 어떻게 따르는지, 그 결과 품질은 확인하지 못했다. UI 호출 경계는 기본 시스템 워크스페이스(`BasicSystemWorkspace.vue`, `useBasicWorkspaceLogic.ts`)를 대표로 읽었고 기본 사용자·Pro·이미지 워크스페이스는 같은 함수(`createRewriteFromEvaluationHandler`, `useWorkspaceTemplateSelection`)를 쓰는 것을 검색으로만 확인했다. 원본 테스트는 파일·사례 이름(`core/tests/unit/evaluation/rewrite-from-evaluation.test.ts`, `core/tests/unit/prompt-service-enhanced.test.ts`의 `iteratePrompt`·`iteratePromptStream` 항목)만 검색했고 사례는 열지 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스: AGPL-3.0-only(overview 1절). 아래는 복사본이 아니라 위치다. 재구현자는 해당 범위를 읽고 직접 구현하며, 템플릿 본문(C-06, C-16)은 구조를 참고해 새로 쓴다. 규칙마다 글로 풀 수 있는 것은 1.4에 풀었고, 아래는 짧고 자기완결적인 분기·형식 문자열만 가리킨다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/core/src/services/prompt/service.ts:24-31` `DEFAULT_TEMPLATES`; `:74-82` `validateInput`; `:87-91` `validateResponse` | 상수와 유일한 `ITERATE` 사용처(`:303`), 입력·빈 응답 검사 | R-01, R-03, R-08 |
| C-02 | `service.ts:274-380` `iteratePrompt` | 비스트리밍 전체: 검증 → 모델 → 템플릿 → 배열형 확인 → 맥락 → `processTemplate` → `sendMessage` 1회 → 반환, 오류 래핑 | R-01~R-05, R-07, R-09, R-10 |
| C-03 | `service.ts:721-840` `iteratePromptStream` | 스트리밍 전체: 같은 흐름 + `onComplete` 빈 응답 검사, `onError` 연결, 외곽 래핑 | R-01~R-05, R-08, R-09 |
| C-04 | `packages/core/src/services/prompt/types.ts:139-150`, `:181-195` `IPromptService.iteratePrompt`, `iteratePromptStream` | 두 시그니처(인자 순서 차이, `templateId` 선택/필수, `contextData` 모양) | 1.3, R-03 |
| C-05 | `packages/core/src/services/prompt/errors.ts:42-52` `IterationError` | 코드 `error.prompt.iteration`, `originalPrompt`·`iterateInput` 필드(메시지 형식은 prompt-optimize C-18) | R-09 |
| C-06 | `packages/core/src/services/template/default-templates/iterate/iterate_en.ts:1-82`, `iterate/soul-iterate_en.ts:1-121`, `iterate/context/context-iterate_en.ts:1-73` | 반복 템플릿 3종의 `[system, user]` 구조, JSON 증거 블록(`helpers.toJson` + `{{{lastOptimizedPrompt}}}`·`{{{iterateInput}}}`), 변수 예시를 글자 그대로 쓰는 구분자 변경 | R-05, R-06 |
| C-07 | `packages/core/src/services/template/default-templates/index.ts:183-186` | `iterate` 유형 내장 선언 순서(`iterate` → `soul-iterate`; UI 기본 선택의 "목록 첫 번째") | R-03, R-27 |
| C-08 | `packages/core/src/services/evaluation/rewrite-from-evaluation.ts:38-121` | `EvaluationRewritePromptParams`·`EvaluationRewriteContext`·`EvaluationRewritePayload` 필드 | 1.3, R-12, R-20 |
| C-09 | `rewrite-from-evaluation.ts:123-257` | 줄 압축 함수(`normalizeInlineText`, `truncateInline`, `collectUniqueLines`)와 줄 포맷(`buildPatchPlanLines`, `buildDimensionLines`, `buildStopSignalLines`, `buildCompareSupportLines`, 충돌·초점 줄 래퍼) | R-19, R-23 |
| C-10 | `rewrite-from-evaluation.ts:260-287` `resolveRewriteTemplate`, `normalizeRewriteLocaleLanguage` | 모드 5분기 + generic, `'en'` 여부 선택, 로케일 정규화 | R-21, R-24 |
| C-11 | `rewrite-from-evaluation.ts:289-367` `buildRewriteFromEvaluationContext` | 맥락 키 목록, 줄 줄 수·길이 매개변수 | R-19, R-23 |
| C-12 | `rewrite-from-evaluation.ts:369-428` `buildRewritePayload` | payload 구성, 원본 객체 동봉, 선택 키 생략 | R-12, R-20 |
| C-13 | `rewrite-from-evaluation.ts:430-439` `buildRewritePromptFromEvaluation` | 템플릿 선택 → 렌더링 → trim·연결 | R-21 |
| C-14 | `packages/core/src/services/template/default-templates/evaluation-rewrite/runtime-copy.ts:10-15`, `:137-339` `buildEvaluationRewriteGuidance` | `RewriteRecommendation`·`RewriteFocusArea` 타입, 가이던스 판정 순서·조건·`reasons`·`priorityMoves` 의미 | R-13~R-18 |
| C-15 | `runtime-copy.ts:17-57`, `:59-135`, `:341-377` | 줄 압축 헬퍼(같은 규칙의 복제본), 모드·유형 라벨, 충돌 신호 문장, 초점 요약·목표 줄 | R-19, R-20, R-23 |
| C-16 | `packages/core/src/services/template/default-templates/evaluation-rewrite/content.ts:17-73` `buildRewriteUserPrompt`; `builders.ts:30-44`; `basic-system_en.ts:1-14`, `basic-user_en.ts`, `pro-multi_en.ts`, `pro-variable_en.ts`, `generic_en.ts` | 재작성 지시 규칙(영어 19항·중국어 18항), 단일 user 메시지, 템플릿 5종의 ID·대상 라벨 | R-21, R-22 |
| C-17 | `default-templates/index.ts:135-144`, `:273-282` | 재작성 템플릿 10개의 등록(재작성 코드는 이 등록을 읽지 않고 직접 import) | R-21 |
| C-18 | `packages/core/src/services/evaluation/types.ts:224-322` `StructuredCompareRole`, `CompareStopSignals`, `CompareConflictSignal`, `CompareJudgement`, `CompareInsightHighlight`, `CompareInsights` | 재작성이 읽는 신호의 필드와 허용 값 | R-12~R-20 |
| C-19 | `packages/ui/src/composables/prompt/useEvaluationHandler.ts:487-529` `panelProps`; `:538-548` `createApplyImprovementHandler`; `:550-605` `createRewriteFromEvaluationHandler` | 힌트용 가이던스, 개선안 미리 채우기, 재작성 핸들러(입력 결정·compare `skip` 가드·`runIterateWithInput` 호출) | R-25, R-26, R-29 |
| C-20 | `packages/ui/src/components/evaluation/EvaluationPanel.vue:542-575`, `:1174-1188` | 버튼 가용성(결과 없음·평가 중·stale), `skip`의 soft 표시·힌트, 이벤트 방출 | R-25 |
| C-21 | `packages/ui/src/components/PromptPanel.vue:783-806` `dispatchIterate`, `submitIterate`; `:875-889` `openIterateDialog`, `runIterateWithInput` | 이벤트 payload 구성·템플릿 미선택 거절·즉시 `true` 반환 | R-27, R-29 |
| C-22 | `packages/ui/src/composables/workspaces/useBasicWorkspaceLogic.ts:290-419` `handleIterate`; `packages/ui/src/composables/workspaces/useWorkspaceTemplateSelection.ts:110-150` `refreshIterateTemplates` | 반복 실행 가드·모델·템플릿 ID·화면 비우기·히스토리 호출, 반복 템플릿 목록과 폴백 | R-10, R-27 |
| C-23 | `packages/mcp-server/src/index.ts:126-147`, `:264-330` | `iterate-prompt` 도구 정의와 `iteratePrompt` 호출 인자 | R-11, R-03 |
| C-24 | `scripts/run-structured-compare-calibration.mjs:1312-1345` | 같은 재작성 입력문을 반복 템플릿 없이 단일 user 메시지로 보내는 호출 | R-28, R-30 |
| C-25 | `packages/ui/src/components/basic-mode/BasicSystemWorkspace.vue:480-500`, `:1320-1335`, `:1402-1421`, `:1697` | 재작성 이벤트 연결, `target.workspacePrompt`·`referencePrompt` 채우기, `comparePayload` | R-26 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트 사례는 이름만 확인했고 열지 않았으며 실행하지 않았다). LLM·모델 관리자·템플릿 관리자는 호출 인자를 기록하고 고정 응답을 돌려주는 대체물을 쓴다고 가정하며, 그래서 어댑터와 실제 응답 품질은 검증하지 않는다. UI 사례(T-24~T-27)는 컴포넌트 이벤트를 가짜로 대체한 경계 사례다. 내장 템플릿은 영어, 사용자 템플릿 없음.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-05~R-07 | `iteratePrompt('O','P','I','m')`(템플릿 미지정), 모델 `m` 존재, LLM이 `"X"` 반환 | `getTemplate('iterate')` 사용. LLM 호출 1회, 메시지 `[system(iterate 본문), user]`이고 user에 `"lastOptimizedPrompt": "P"`, `"iterateInput": "I"` 형태의 이스케이프된 JSON 문자열 두 개. 반환 `"X"`(공백이 있어도 그대로) |
| T-02 | R-03 | `iteratePromptStream('O','P','I','m', handlers, templateId)`에서 `templateId`가 `undefined` / `''`(비스트리밍 `iteratePrompt`는 같은 값에서 `iterate`로 동작) | 스트리밍: `IterationError`("Iteration failed: …Invalid template ID…")로 reject, LLM 호출 없음, `handlers.onError` 미호출. 비스트리밍: T-01과 같은 결과 |
| T-03 | R-03, R-04 | `templateId: 'general-optimize'`(문자열 내용) | 두 함수 모두 `IterationError`(메시지에 "message array" 요구와 `Template ID: general-optimize`), LLM 호출 없음 |
| T-04 | R-03 | `templateId: 'user-prompt-basic'`(배열, `userOptimize` 유형) | 유형 검사가 없어 오류 없이 렌더링한다(그 템플릿은 `lastOptimizedPrompt`·`iterateInput`을 읽지 않아 입력이 메시지에 들어가지 않을 수 있음) |
| T-05 | R-01 | ① `lastOptimizedPrompt:'  '` ② `lastOptimizedPrompt:'P', modelKey:''` ③ `iterateInput:'  '` ④ `originalPrompt:''` + 나머지 정상 | ①③ `IterationError`("Iteration failed: [error.prompt.optimization] Prompt cannot be empty") ② `…Model key is required` ④ 통과. 세 오류 모두 모델·템플릿 조회와 LLM 호출 전 |
| T-06 | R-02 | `getModel`이 `undefined` | `IterationError`("…Model not found"), LLM 호출 없음 |
| T-07 | R-07 | 비스트리밍, LLM이 `""` 또는 `"  \n"` 반환 | 오류 없이 그 문자열 반환(`optimizePrompt`와 달리 빈 응답을 거절하지 않음) |
| T-08 | R-08 | 스트리밍, LLM이 토큰 `"a"`,`"b"` 후 `onComplete({content:'ab'})` / `onComplete({content:'  '})` / `onComplete(undefined)` | `onToken`이 a,b 순으로 불리고 첫째는 `onComplete({content:'ab'})`. 둘째는 `onComplete` 미호출, `onError(OptimizationError "LLM service returned empty result")`. 셋째는 `onComplete(undefined)` |
| T-09 | R-08, R-09 | 스트리밍, 모델 `m`의 OpenAI 계열 어댑터에서 스트림 생성이 오류 `e`로 실패 | 호출자 `onError`가 `e`로 **2회**(어댑터 1, 서비스 1, 같은 객체), promise는 "Iteration failed: …e.message"의 `IterationError`로 reject. `PromptService` 단계 사전 검증 실패(R-01~R-04)는 `onError` 0회, reject만. 모델 비활성(`llmService` 검증 실패)은 `onError` 1회 + reject |
| T-10 | R-05, R-06 | `contextData:{variables:{x:'1'}, messages:[{role:'user',content:'hi'}], tools:[…]}`를 `iterate`(내장)에 / `context-iterate`에 | 맥락에 `customVariables:{x:'1'}`, `conversationContext`("USER: hi" 형태), `toolsContext`가 들어가고 `x`는 최상위 키가 아니다. `iterate`는 이 키들을 읽지 않아 메시지가 T-01과 같고, `context-iterate`는 대화·도구 텍스트가 JSON 문자열로 system에 들어간다 |
| T-11 | R-11 | MCP `iterate-prompt` `{prompt:'P', requirements:'R'}` / `requirements` 없음 | `iteratePrompt('P','P','R','mcp-default','iterate')` 호출(원본·직전 최적화본이 같은 `'P'`, 템플릿은 `iterate` 유형 목록 첫 번째). 둘째는 "Error: Missing required parameter 'requirements'" 오류 콘텐츠 |
| T-12 | R-13 | `type:'result'`(또는 `prompt-only`·`prompt-iterate`), 어떤 신호든 / `type:'compare'`, `workspacePrompt:'  '` | 둘 다 `recommendation:'rewrite'`, `focusAreas:[]`, `priorityMoves:[]`, `reasons` 1개 |
| T-13 | R-14 | `compare`, `workspacePrompt:'P'`, `stopSignals.stopRecommendation:'stop'`, 충돌 신호 `regressionOutweighsCosmeticGains`도 있음 | `recommendation:'skip'`, `reasons` 1개, `focusAreas:[]`, `priorityMoves:[]`(충돌 신호보다 `stop`이 먼저) |
| T-14 | R-16 | `compare`, `workspacePrompt:'P'`, 신호 `{targetVsBaseline:'flat', targetVsReferenceGap:'none', improvementHeadroom:'medium'}`, 충돌 없음 | `'skip'`, `reasons` 1개. 같은 신호에 `overfitRisk:'medium'`을 더하면 `reasons` 2개이고 `focusAreas:['generalization']`, `priorityMoves` 1개 |
| T-15 | R-16, R-18 | T-14 입력에 `improvementHeadroom:'high'`로 바꿈 / `targetVsReferenceGap`을 비움 | 둘 다 `skip`이 아니다(앞은 헤드룸 high, 뒤는 격차 값 없음) → R-17 조건도 불충족이라 `'rewrite'` |
| T-16 | R-17 | `compare`, `workspacePrompt:'P'`, 신호 `{targetVsBaseline:'improved', targetVsReferenceGap:'none', improvementHeadroom:'low'}`, 충돌 없음 | `'minor-rewrite'`, `reasons` 1개. `overfitRisk:'medium'`을 더하면 `reasons` 2개, `focusAreas:['generalization']` |
| T-17 | R-15, R-18 | T-16 신호 + `conflictSignals:['regressionOutweighsCosmeticGains']` / `['improvementUnstableAcrossReplicas']` | 앞: `'rewrite'`, `focusAreas:['contract-repair']`, `priorityMoves` 1개, `reasons` 2개(기본 + 회귀 복구). 뒤: `'rewrite'`, `focusAreas:['decision-stability']`, `priorityMoves` 3개, `reasons` 2개 |
| T-18 | R-18 | `compare`, `workspacePrompt:'P'`, `stopSignals`·`compareInsights` 모두 없음 | `'rewrite'`, `reasons` 1개("개선 여지·미해결 위험 남음"), `focusAreas:[]` |
| T-19 | R-12, R-20 | 결과 `{summary:'S', score:{overall:70, dimensions:[{key:'k',label:'L',score:60}]}, improvements:['a','b','c'], patchPlan:[3개]}`, `type:'result'`, `workspacePrompt:'  P  '`, `referencePrompt:'  '` | payload `sourcePrompts`는 `{workspacePrompt:'P'}`(`referencePrompt` 키 없음), `compressedEvaluation.summary:'S'`, `dimensionScores:[{key:'k',label:'L',score:60}]`, `improvements`·`patchPlan` 원본 그대로, `compareStopSignals`·`compareInsights` 키 없음. `score`가 없으면 `scenario.overallScore:'N/A'` |
| T-20 | R-19 | `compareInsights.learnableSignals`에 7개: `"A  b"`, `"a B"`(소문자·공백 정규화 후 중복), 300자 문자열 포함 | `learnableSignalLines`는 중복 제거 후 최대 5개이고 300자 항목은 220자 + `...`(223자). `compressedEvaluation.compareInsights.learnableSignals`에는 원본 7개가 그대로 남는다 |
| T-21 | R-19, R-20 | `compareInsights.pairHighlights` 6개(각 analysis 300자) + `evidenceHighlights` 3개 | `supportEvidenceLines`는 4개, 각 240자 이내(`...` 포함 243), 앞 4개는 `1. <pairLabel> \| signal=… \| verdict=… \| confidence=… \| …` 형식. `compareInsights` 원본에는 전부 남는다 |
| T-22 | R-21, R-24 | `mode:{functionMode:'basic', subMode:'system'}`, `language:'en'` / 생략 / `mode:{functionMode:'image', subMode:'text2image'}`, `language:'en'` / `mode:{functionMode:'basic', subMode:'other'}` | 순서대로 영어 판 `evaluation-rewrite-basic-system`(첫 문장에 "system prompt") / **중국어 판**(기본 `zh`) / `generic` 영어 판("workspace prompt") / `generic`. 결과는 메시지 1개를 trim한 문자열이고 끝은 `Rewrite Payload (JSON):` 줄과 들여쓰기 2칸 JSON |
| T-23 | R-21 | `workspacePrompt`가 `{{x}}`와 `<b>` 포함 | 결과 문자열의 JSON 안에 `{{x}}`·`<b>`가 이스케이프·치환 없이 남는다(JSON 문자열로서의 `"`·줄바꿈 이스케이프만) |
| T-24 | R-24 | `normalizeRewriteLocaleLanguage` 입력 `'en-US'`, `'EN'`, `'en'`, `'zh-CN'`, `'zh-TW'`, `'ko'`, `undefined` | `'en'`, `'en'`, `'en'`, `'zh'`, `'zh'`, `'zh'`, `'zh'` |
| T-25 | R-26 | `type:'compare'`, 가이던스가 `skip`(T-14 입력)인 상태에서 재작성 이벤트 | 정보 토스트 1회, `runIterateWithInput` 미호출, `iteratePromptStream` 미호출, 평가 패널 유지 |
| T-26 | R-26, R-27 | 가이던스가 `rewrite`인 compare 평가에서 재작성 이벤트. `runIterateWithInput`이 `true` / `false`(반복 템플릿 미선택 → 오류 토스트) | 앞: 입력문 한 번 전달 후 평가 패널 닫힘, `iterate` 이벤트의 `iterateInput`=입력문(trim), `optimizedPrompt`=출력 영역의 현재 내용. 뒤: 오류 토스트, 이벤트 없음, 평가 패널 유지 |
| T-27 | R-27, R-28 | T-26 앞 경우의 `iteratePromptStream` 호출 | 모델 key = 최적화 모델(평가 모델 아님), `templateId` = 선택된 반복 템플릿 ID, `lastOptimizedPrompt` = 출력 영역 내용, `iterateInput` = 재작성 입력문 전체(이 문자열이 `iterate` user 메시지에서 JSON 문자열 필드가 됨). 완료 시 `addIteration`(체인 없으면 `createNewChain`)의 `iterationNote`가 입력문 전체 |
| T-28 | R-30 | 저장소에서 `autoIterate`·`auto-iterate`·`oneRound`·`thinLoop`·단어 `SPO`(코드 주석 제외)와 파일 `autoIterateOneRound.ts`·`autoIteratePreset.ts`를 검색 / compare 평가를 끝낸 뒤 사용자 입력 없이 대기 | 코드에 일치 없음(`types.ts`의 "SPO" 주석 2곳 제외). 평가 완료 후 사용자가 재작성 버튼을 누르지 않으면 `runIterateWithInput`·`iteratePromptStream`이 호출되지 않는다 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 (`service.ts:74-82`), C-02 (`:290-291`), C-03 (`:738-739`) | 코드 읽음 |
| R-02 | C-02 (`service.ts:293-297`), C-03 (`:741-745`) | 코드 읽음. `getModel`이 비활성 모델을 거르는지는 모델 관리자 내부(prompt-optimize 2.1 R-02와 같음) |
| R-03 | C-02 (`service.ts:300-312`, 특히 `:302-303`), C-03 (`:747-759`, 특히 `:750`), C-01 (`:24-31`), C-23 (`mcp-server/src/index.ts:314-321`), C-22 (`useBasicWorkspaceLogic.ts:299-308`, `:406`), `useWorkspaceTemplateSelection.ts:110-150` | 코드 읽음. 저장소 전체 호출처는 `git grep "iteratePromptStream\|iteratePrompt("`(core 정의·타입·`electron-proxy.ts`·`desktop/main.js`·MCP·UI 7곳)로 찾음. UI 7곳 중 기본 워크스페이스는 호출 인자까지, 나머지는 `templateId: selected…` 인자를 grep으로 확인. `DEFAULT_TEMPLATES.ITERATE` 참조는 `service.ts:303` 하나(prompt-optimize 2.1 R-04 검색과 같은 결과) |
| R-04 | C-02 (`service.ts:324-334`), C-03 (`:770-780`); template-rendering R-09 | 코드 읽음 |
| R-05 | C-02 (`service.ts:336-360`), C-03 (`:782-806`); template-rendering R-08·`createExtendedContext` 설명; `iterate/*`·`context/*` 템플릿의 `{{` 검색: `originalPrompt` 참조 없음 | 코드 읽음 + 검색 |
| R-06 | C-06 (`iterate_en.ts:1-82`, `soul-iterate_en.ts:1-121`, `context/context-iterate_en.ts:1-73`), C-07 (`index.ts:167-168`·`:183-186`); `templateType` 줄 `iterate_en.ts:77`, `soul-iterate_en.ts:116`, `context-iterate_en.ts:67` | 영어 본문 3개를 끝까지 읽음. 변수 보존 문구 유무는 `{{=<% %>=}}` 검색으로 확인 |
| R-07 | C-02 (`service.ts:363-370`) | 코드 읽음. 최적화 경로와의 차이는 prompt-optimize R-11·`service.ts:158-164`와 대조 |
| R-08 | C-03 (`service.ts:809-839`: `onError: handlers.onError` 연결 `:829`, 외곽 catch는 `onError` 미호출); 서비스 계층 `llm/service.ts:126-154`(`:149-153` catch: `onError` 후 `throw`); 추상 어댑터 `llm/adapters/abstract-adapter.ts:124-135`(검증 후 `doSendMessageStream`, `onError` 없음); OpenAI `llm/adapters/openai-adapter.ts:1352-1431`(`:1427-1430` catch: `onError` 후 `throw`); Anthropic `llm/adapters/anthropic-adapter.ts:541-630`(`createClient`는 try 밖 `:546`, `error` 리스너 `:619-621`, catch `:625-628`: `onError(handleError(오류))` 후 원래 오류 `throw`, `handleError` `:868-873`); UI `useBasicWorkspaceLogic.ts:402-404`(`onError`가 같은 오류를 다시 던짐) | 코드 읽음. 호출 순서와 횟수는 코드 도출. Anthropic SDK의 `error` 이벤트 발생은 외부 동작이라 추론. 다른 어댑터는 읽지 않음 |
| R-09 | C-02 (`service.ts:371-379`), C-03 (`:830-839`), C-05 | 코드 읽음 |
| R-10 | C-02 (`service.ts:365-366` 주석), C-22 (`useBasicWorkspaceLogic.ts:329-362`의 `onComplete`), history-chain R-02·R-08·R-09 | 코드 읽음 |
| R-11 | C-23 (`mcp-server/src/index.ts:126-147`, `:264-330`); `adapters/parameter-adapter.ts`의 `validateRequirements` 한도는 overview 근거(이 스펙에서는 파일을 다시 열지 않음) | 코드 읽음 |
| R-12 | C-12 (`rewrite-from-evaluation.ts:369-428`), C-11 (`:289-367`), C-18 (`types.ts:224-322`); llm-evaluation R-23·R-29 | 코드 읽음 |
| R-13 | C-14 (`runtime-copy.ts:149-179`) | 코드 읽음. 원본 테스트 사례 이름 확인만: `rewrite-from-evaluation.test.ts:125` "emits English rewrite guidance for design-only analysis" |
| R-14 | C-14 (`runtime-copy.ts:181-194`) | 코드 읽음 |
| R-15 | C-14 (`runtime-copy.ts:196-239`) | 코드 읽음 |
| R-16 | C-14 (`runtime-copy.ts:241-270`) | 코드 읽음. 사례 이름: `:220` "marks flat no-gap compare results as skip for rewrite gating" |
| R-17 | C-14 (`runtime-copy.ts:272-301`) | 코드 읽음. 사례 이름: `:252` "marks low-headroom closed-gap compare results as minor rewrite" |
| R-18 | C-14 (`runtime-copy.ts:303-339`) | 코드 읽음. 사례 이름: `:284` "adds decision-stability guidance when compare detects replica instability" |
| R-19 | C-09 (`rewrite-from-evaluation.ts:123-257`), C-11 (`:297-331`), C-12 (`:403-426`), C-15 (`runtime-copy.ts:17-57`, `:341-377`) | 코드 읽음. 줄 압축 헬퍼가 두 파일에 복제돼 있다는 점은 두 정의를 대조해 확인 |
| R-20 | C-12 (`rewrite-from-evaluation.ts:369-428`), C-15 (`runtime-copy.ts:59-135`) | 코드 읽음. 사례 이름: `:34` "builds a JSON-payload compare rewrite brief in Chinese", `:180` "builds a structured rewrite payload object" |
| R-21 | C-10 (`rewrite-from-evaluation.ts:260-283`), C-13 (`:430-439`), C-16 (`content.ts:87-101`, `builders.ts:30-44`), C-17 (`index.ts:135-144`, `:273-282`); template-rendering R-20·C-17 | 코드 읽음. 5종 템플릿 파일의 ID·`subjectLabel` 줄 확인(`basic-system_en.ts`, `basic-user_en.ts`, `pro-multi_en.ts`, `pro-variable_en.ts`, `generic_en.ts`). 사용처 검색: `evaluation-rewrite` 문자열은 `rewrite-from-evaluation.ts`·`index.ts` 외에 코어 소스에 없음(조회 경로는 직접 import만) |
| R-22 | C-16 (`content.ts:17-73`) | 영어·중국어 본문을 끝까지 읽음. 두 판의 항목 수 차이(19/18)는 영어가 "샘플 특화 금지"와 "특화 제안 약화"를 두 항목으로, 중국어가 한 항목으로 나눈 것(+ 출력 형식 두 항목 병합)으로 의미 대조(추론) |
| R-23 | C-11 (`rewrite-from-evaluation.ts:289-367`); `evaluation-rewrite/*.ts`의 `{{` 검색: `content.ts:46`, `:72`의 `{{{rewritePayloadJson}}}`뿐 | 코드 읽음 + 검색 |
| R-24 | C-10 (`rewrite-from-evaluation.ts:285-287`), C-12 (`:372`), C-19 (`useEvaluationHandler.ts:565`); `packages/ui/src/i18n/locales/{en-US,zh-CN,zh-TW}`(`_legacy` 제외); llm-evaluation R-20(구조화 비교의 언어 선택과 대비) | 코드 읽음. 사례 이름: `:321` "normalizes locale into supported rewrite languages" |
| R-25 | C-20 (`EvaluationPanel.vue:542-575`, `:1174-1188`); 이미지 워크스페이스 `:can-rewrite-from-evaluation="false"`(`ImageImage2ImageWorkspace.vue:709`, `ImageMultiImageWorkspace.vue:577`, `ImageText2ImageWorkspace.vue:873`), 기본·컨텍스트 4곳 `"true"`; stale 정의 `BasicSystemWorkspace.vue:1124-1138`, `:1476-` | 코드 읽음. stale 지문의 세부 구성은 읽지 않음 |
| R-26 | C-19 (`useEvaluationHandler.ts:550-605`), C-25 (`BasicSystemWorkspace.vue:1320-1335`, `:1402-1421`) | 코드 읽음. 다른 워크스페이스의 `target` 채우기는 검색으로 같은 핸들러를 쓰는 것만 확인 |
| R-27 | C-21 (`PromptPanel.vue:783-806`, `:875-889`), C-22 (`useBasicWorkspaceLogic.ts:290-419`), `BasicSystemWorkspace.vue:186`·`:1592-1594` | 코드 읽음. 이미지·Pro 워크스페이스는 읽지 않음 |
| R-28 | C-24 (`run-structured-compare-calibration.mjs:1312-1345`), C-03·C-06 (`iterate_en.ts:58-69`의 user 메시지), `docs/architecture/structured-compare-and-evaluation-rewrite.md:381-385`(문서의 "复用 iterate 流程" 진술); `docs/architecture/spo-thin-loop-ui-and-stop-rules.md:1.1` | 코드 읽음. 모델 반응은 미확인 |
| R-29 | C-19 (`useEvaluationHandler.ts:538-548`), `BasicSystemWorkspace.vue:1692-1695` | 코드 읽음 |
| R-30 | 검색: `git grep -i -e autoIterate -e auto-iterate -e oneRound -e thinLoop -- packages scripts`(코드 일치 없음), `git grep -w -e SPO -- packages scripts`(`evaluation/types.ts:257`, `:270` 주석 2건만), `git ls-files | grep -i autoiterate`(문서 폴더 파일만), `runIterateWithInput`·`createRewriteFromEvaluationHandler`·`buildRewritePromptFromEvaluation` 호출자 검색(UI 클릭 경로와 보정 스크립트뿐); 설계 문서 `docs/architecture/test-area-auto-iterate-one-round.md:1-379`, 상태 진술 `docs/architecture/spo-thin-loop-ui-and-stop-rules.md` "1.1 当前实现状态", `docs/workspace/test-area-auto-iterate-one-round/progress.md`("设计已收口，尚未开始代码实现") | 검색 기반이라 "없음"은 추론 성격. 재확인 방법은 위 `git grep`·`git ls-files` 명령과 `runAllVariants`(`BasicSystemWorkspace.vue:1277-1318`)가 평가를 호출하지 않는 것을 읽는 것이다 |
| R-31 | C-19 (`useEvaluationHandler.ts:577-584`, `:597`), C-13, C-24 (`:1341-1343`: `skip`에서도 `sendMessage`) | 코드 읽음 |
| T-01~T-28 | 위 R-ID의 근거에서 도출. 사례 이름이 겹치는 원본 테스트: `core/tests/unit/evaluation/rewrite-from-evaluation.test.ts`(T-12~T-24 취지), `core/tests/unit/prompt-service-enhanced.test.ts:574`·`:634` `iteratePrompt`·`iteratePromptStream`, `core/tests/integration/prompt/service.integration.test.ts:186`(T-01·T-03 취지) | 모두 미실행. 테스트 사례 본문은 열지 않았다 |
| 문서와 구현 차이 ① | `docs/architecture/test-area-auto-iterate-one-round.md`는 자동 1라운드(버튼·팝업·4칸 프리셋·자동 재테스트)를 설계하지만 구현은 없다. 문서 머리말이 "최초 방안, 최신 설계는 `structured-compare-and-evaluation-rewrite.md`·`spo-thin-loop-ui-and-stop-rules.md`"라고 밝히고, 후자의 1.1이 `SPO` 실행부를 "未落地"로 적는다 | 구현을 사실로 썼다(R-30) |
| 문서와 구현 차이 ② | `structured-compare-and-evaluation-rewrite.md`는 재작성 능력이 "아직 독립 템플릿 프로토콜 층이 아니다"(`:381-386`), "더 강한 프로토콜과 독립 템플릿"을 후속 항목으로 둔다(`:65`). 구현에는 이미 `evaluation-rewrite/*` 전용 템플릿 5종×2언어와 JSON payload 프로토콜이 있고(R-20~R-22), 문서는 이 부분에서 뒤처져 있다. 같은 문서 `:238-244` "재작성은 자동 compare·재테스트·다중 라운드를 맡지 않는다"는 구현과 일치한다 | 구현을 사실로 썼다 |
| 문서와 구현 차이 ③ | overview Q2 "평가가 `skip`을 권고하면 재작성하지 않는다"는 정확히는 (a) compare 유형에서, (b) 평가자의 `stopRecommendation`을 그대로 쓰는 것이 아니라 `stop` 신호·충돌 신호·정지 신호 값을 코드가 조합해 낸 `rewriteGuidance.recommendation`이 `skip`일 때, (c) UI 핸들러만 막는다(R-14~R-16, R-26, R-31). 코어 함수는 막지 않는다 | 구현을 사실로 썼다. overview는 고치지 않는다 |
| 문서와 구현 차이 ④ | template-rendering R-20은 "언어를 `'en'` 여부로 고른다"고 적었다. 구현에서 그 `language`는 호출자 인자(UI는 로케일에서 유도, 코어 기본 `'zh'`)이고 `getCurrentBuiltinTemplateLanguage()`를 읽는 구조화 비교와 다르다(R-24) | 구현을 사실로 썼다. 선행 스펙은 고치지 않는다 |
| 문서와 구현 차이 ⑤ | `service.ts:25` 주석 "Default template IDs used by the system"과 달리 실제로 읽히는 것은 `ITERATE` 하나이고, 그것도 비스트리밍 `templateId` 없음 경로에서만이다(R-03, prompt-optimize 2.1 ① 참조) | 구현을 사실로 썼다 |
| 문서와 구현 차이 ⑥ | `service.ts` 주석 "迭代模板只需要 lastOptimizedPrompt 和 iterateInput"은 맞지만, `iteratePrompt`는 `originalPrompt`를 맥락·오류 필드에 넣을 뿐 내장 템플릿 3종이 읽지 않는다(R-05). MCP는 `originalPrompt`와 `lastOptimizedPrompt`에 같은 값을 넣는다(R-11) | 구현을 사실로 썼다 |

### 2.2 코드 읽는 순서 [선택]
1. `prompt/service.ts:274-380`(비스트리밍) → `:721-840`(스트리밍 차이: 인자 순서, `templateId` 기본값 없음, `onComplete` 검사) → `iterate/iterate_en.ts`(JSON 증거 블록과 "녹여 넣기" 규칙).
2. `evaluation-rewrite/runtime-copy.ts:137-339`(가이던스 판정 순서) → `rewrite-from-evaluation.ts:369-439`(payload, 입력문) → `evaluation-rewrite/content.ts:17-73`(지시문 19항).
3. UI: `useEvaluationHandler.ts:550-605` → `PromptPanel.vue:783-806`·`:875-889` → `useBasicWorkspaceLogic.ts:290-419`.
4. 자동 1라운드 확인: 설계 문서 → `spo-thin-loop-ui-and-stop-rules.md` 1.1 → 위 `git grep`.
구현 전략: 재작성 입력문 생성은 모듈 상수 템플릿에 JSON 문자열을 끼워 넣는 순수 함수이고(상태·I/O 없음), 호출 한 번의 LLM 호출은 기존 반복 개선 경로를 재사용한다. 가이던스는 모델 호출이 아니라 코드 규칙이다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드·템플릿 본문은 복사하지 않았다.

## 적용 메모 [선택]
목적: 내 스킬(SKILL.md)을 여러 모델에서 평가·개선하고 모델 적합도를 기록하는 환경을 만들 때 가져올 것과 다르게 할 것.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-12, R-20, R-30 | **가져올 핵심**: "평가 응답 → 재작성 입력" 고리의 설계 — 평가자의 결론(요약·점수·차원·개선안·패치 계획·정지 신호·충돌 신호)만 구조화 payload로 모으고, 대상 프롬프트 원문은 별도 필드로 싣고, 강도 권고(`skip`/`minor-rewrite`/`rewrite`)와 우선 행동 목록을 **코드로** 계산해 payload에 넣는 방식. 템플릿 본문은 새로 쓴다. | 원본에서 이 연결은 수동 클릭이고(R-30), 압축·가이던스 계산이 순수 함수라 그대로 오케스트레이터에서 재사용하기 쉽다. | 우리 환경의 오케스트레이터가 `evaluate → guidance → rewrite → re-evaluate`를 직접 돈다. 라운드 상한·점수 정체·`stopRecommendation`·`improvementHeadroom` 기반 종료 조건과 라운드별 기록은 새 설계(원본은 `iteratePrompt`를 몇 번 부를지 모른다, R-10) |
| R-31, R-14~R-16 | `skip` 가드를 UI가 아니라 호출 함수 안에 둔다: 권고가 `skip`이면 LLM을 부르지 않고 입력 프롬프트를 그대로 반환하고, `minor-rewrite`/`rewrite`일 때만 호출한다. 호출 후에는 출력이 입력과 같아야 하는 경우(`skip`)와 변수·SKILL.md frontmatter 보존 여부를 코드로 검사한다. | 원본은 `skip` 보장을 UI 조기 종료와 모델의 순응에만 맡긴다(R-31). 반복 루프에서는 가드가 호출 경계에 없으면 불필요한 호출·변경이 생긴다. | 새 반환 구조(예: `{text, action: 'skipped'\|'rewritten', guidance}`). T-13~T-18 기대값은 유지하고, `skip` 시 LLM 미호출 사례 추가 |
| R-13, R-15 | 원본의 `skip`·`minor-rewrite`는 compare 평가의 `compareStopSignals`가 있을 때만 의미가 있고, `result`·`prompt-only` 평가는 항상 `rewrite`다(R-13). 모델 적합도 비교 환경에서는 compare의 역할 구조(target/baseline/reference/…)가 "프롬프트 개선 정지 판정"용이므로 그대로 쓰지 말고, 모델별 `result` 점수·차원 점수의 변화(개선폭, 정체, 퇴보)를 입력으로 하는 종료·강도 규칙을 새로 정한다. | 신호 체계는 "같은 프롬프트의 두 버전 × 두 모델" 구성(llm-evaluation 적용 메모)에 묶여 있어서 단일 스킬 × 모델 N개 구성에는 맞지 않는다. | 가이던스 입력을 `EvaluationResponse` 전체가 아니라 우리가 정의한 "개선 판단 요약"으로 바꾸는 별도 함수. T-12~T-18 대체 |
| R-28 | 재작성은 반복 개선 템플릿에 요구사항으로 끼워 넣지 말고 **전용 단일 호출**로 한다: 재작성 전용 템플릿을 system(규칙)+user(JSON 증거 블록, 대상 프롬프트 1회)로 분리하거나, 원본 보정 스크립트처럼 입력문을 단일 user 메시지로 보낸다. | UI 경로는 반복 템플릿의 지시("요구사항을 녹여 넣어라")와 재작성 지시("`skip`이면 원문 출력")가 한 호출 안에 겹치고 대상 프롬프트가 두 번 실린다(R-28). 두 지시의 충돌 여부는 확인하지 못했다. | 호출 구성이 바뀌고 `iterateInput` 개념이 없어진다. 우리 평가 JSON 계약·SKILL.md 보존 규칙은 우리 템플릿에 직접 쓴다(AGPL이라 문구는 복사하지 않는다) |
| R-12 | 재작성 입력에 평가 증거의 최소 발췌(예: 실패한 케이스의 입력·출력 일부, 어느 모델에서 깨졌는지)를 **선택적으로** 넣을지 정한다. 원본은 평가자 결론만 보여 주어 샘플 과적합을 막는 대신, 재작성 모델이 평가자의 요약에만 의존한다. | 모델별 적합도 기록에서는 "어느 모델이 무엇에서 틀렸는지"가 개선 입력으로 가치가 있을 수 있다. 다만 원본이 일부러 증거를 뺀 설계(R-22 ⒟)라 과적합 방지 장치와 같이 정해야 한다. | payload에 `evidenceExcerpts` 같은 필드를 추가할지는 우리 결정. 사례 추가 필요 |
| R-24 | 재작성 언어는 UI 로케일·기본 `'zh'`에 맡기지 말고 호출 인자로 명시한다(스킬 언어에 맞춘다). 재작성 입력문의 언어와 개선 템플릿 언어를 같은 값에서 정한다. | 원본은 로케일이 `en`이 아니면 한국어를 포함해 모두 중국어 판이 선택되고, 템플릿 언어와 독립이다(R-24). | `language` 필수 인자. T-22·T-24 기대값 변경 |
| R-10, R-27 | 라운드마다 "무엇에 근거해 재작성했는지"를 기록한다: 재작성 입력문 전체를 노트에 넣는 원본 방식(`iterationNote`에 긴 문자열) 대신, 평가 ID·모델·템플릿 버전·가이던스 권고를 필드로 남긴다. 개선 모델·평가 모델·대상 모델을 분리해 기록한다(원본의 재작성 모델은 "프롬프트를 개선하는 모델"이고 평가 모델과 별개 해석 경로다). | 원본 히스토리 기록에는 점수·평가 연결이 없고(history-chain R-10) 재작성 노트가 길고 비구조적이다. 모델 적합도 기록에는 라운드 계보가 필요하다. | 기록 스키마 신설(history-chain 적용 메모와 같은 방향). 라운드 번호·종료 이유 필드 추가 |
| R-07, R-08 | 반복 개선 결과의 빈 응답·공백 응답을 호출자 쪽에서 오류로 처리한다(`iteratePrompt`는 거르지 않는다, R-07). | 원본 비스트리밍 경로는 빈 문자열을 정상 반환해, 자동 루프에서는 빈 프롬프트가 다음 라운드의 입력이 될 수 있다. | T-07 기대값 변경(오류로 처리) |
