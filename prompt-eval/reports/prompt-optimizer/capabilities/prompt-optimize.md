---
sha: "a201f47d2b17d6cf6a9347f336691b00c98720a1"
created: 2026-10-22
updated: 2026-10-22
sources:
  - packages/core/src/services/prompt/service.ts
  - packages/core/src/services/prompt/types.ts
  - packages/core/src/services/prompt/errors.ts
  - packages/core/src/services/llm/service.ts
  - packages/core/src/services/llm/types.ts
  - packages/core/src/services/llm/adapters/abstract-adapter.ts
  - packages/core/src/services/llm/adapters/openai-adapter.ts
  - packages/core/src/services/llm/adapters/anthropic-adapter.ts
  - packages/core/src/services/image-understanding/types.ts
  - packages/core/src/services/image-understanding/service.ts
  - packages/core/src/services/template/manager.ts
  - packages/core/src/services/template/static-loader.ts
  - packages/core/src/services/template/processor.ts
  - packages/core/src/services/template/default-templates/index.ts
  - packages/core/src/services/template/default-templates/optimize/general-optimize_en.ts
  - packages/core/src/services/template/default-templates/optimize/output-format-optimize_en.ts
  - packages/core/src/services/template/default-templates/optimize/analytical-optimize_en.ts
  - packages/core/src/services/template/default-templates/optimize/soul-openclaw-compose_en.ts
  - packages/core/src/services/template/default-templates/optimize/soul-hermes-compose_en.ts
  - packages/core/src/services/template/default-templates/user-optimize/user-prompt-basic_en.ts
  - packages/core/src/services/template/default-templates/user-optimize/user-prompt-professional_en.ts
  - packages/core/src/services/template/default-templates/user-optimize/user-prompt-planning_en.ts
  - packages/mcp-server/src/index.ts
  - packages/mcp-server/src/config/templates.ts
  - packages/mcp-server/src/adapters/parameter-adapter.ts
  - packages/ui/src/composables/workspaces/useWorkspaceTemplateSelection.ts
  - packages/ui/src/composables/prompt/usePromptOptimizer.ts
  - packages/ui/src/composables/workspaces/useBasicWorkspaceLogic.ts
depends:
  - ../capabilities/template-rendering.md
status: ready
reimplementation: 미실행
---

# 프롬프트 최적화

> 사용자 프롬프트 문자열, 모델 키(`modelKey`), 선택적 템플릿 ID(`templateId`), 모드(`optimizationMode`: system/user)를 받아 내장 "메타 프롬프트" 템플릿으로 LLM 메시지를 만들고, LLM을 한 번 호출해 응답 전체를 최적화된 프롬프트로 돌려준다(비스트리밍 문자열 또는 스트리밍 콜백).

경로 표기: 모든 `파일:줄`은 `repos/prompt-optimizer/` 기준이다. 라이선스는 AGPL-3.0-only(overview 1절)라서 코드와 템플릿 본문은 옮기지 않고 C-ID(위치)로만 가리키며, 템플릿은 구조와 규칙을 글로 설명한다. 템플릿 본문은 영어 판을 읽었고 중국어 판은 본문을 읽지 않았다(1.4 확인 한계). 설치·빌드·실행·모델 호출은 하지 않았다.

<!--
작성 메모(삭제하지 않음): 범위는 `PromptService.optimizePrompt`·`optimizePromptStream` 경로다. 제외: 반복 개선(`iteratePrompt`, 별도 스펙 iterate-rewrite), 이미지 생성·이미지 모드, 모델 관리·LLM 어댑터 내부, Pro 모드 메시지 최적화(`optimizeMessage`), MCP 서버 자체. 렌더링 규칙·템플릿 유형·ID 규칙은 선행 스펙 template-rendering을 링크하고 복제하지 않는다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 호출자(UI 합성 함수 또는 MCP 도구)가 `OptimizationRequest`를 만든다: `targetPrompt`, `modelKey`, `optimizationMode`, 선택적 `templateId`.
2. `optimizePrompt`(또는 `optimizePromptStream`)가 입력을 검증하고(빈 프롬프트·빈 모델 키는 오류), 모델 관리자에서 `modelKey`로 모델 설정을 찾는다(없으면 오류).
3. 템플릿을 정한다: `templateId`가 있으면 그것, 없으면 `optimizationMode`에 맞는 유형(`user`→`userOptimize`, 그 밖→`optimize`)의 **목록 첫 번째** 템플릿. 이어서 `getTemplate`로 읽는다.
4. 맥락 객체(`originalPrompt`=`targetPrompt` 등)를 만들어 `TemplateProcessor.processTemplate`로 `Message[]`를 만든다. 시스템 모드 내장 템플릿은 문자열이라 `[system=템플릿 그대로, user=프롬프트 원문]`, 사용자 모드 내장 템플릿은 배열이라 `[system, user]` 두 메시지이고 user 안에 프롬프트가 JSON 문자열로 들어간다.
5. 이미지 입력이 없으면 `llmService.sendMessage`(스트리밍은 `sendMessageStream`)를 **한 번** 호출한다. 이미지 입력이 있으면 같은 메시지를 system/user 두 문자열로 합쳐 이미지 이해 서비스로 보낸다(경계만).
6. 응답이 비어 있거나 공백뿐이면 오류. 아니면 응답 문자열을 가공 없이 반환한다(스트리밍은 토큰이 콜백으로 흐르고 완료 콜백이 불린다).
7. 어느 단계의 실패든 `OptimizationError`("Optimization failed: …")로 감싸서 던진다. 히스토리는 저장하지 않는다(호출자 몫).

### 1.2 범위·통합 지점 [필수]
- 제공: 프롬프트 한 건의 단일 호출 최적화(문자열 반환·스트리밍 두 형태), 모드별 기본 템플릿 선택, 내장 `optimize`(시스템 모드) 5종·`userOptimize`(사용자 모드) 3종 템플릿의 구조와 규칙, MCP 서버가 같은 호출을 노출하는 방식(R-21).
- 제외:
  - 반복 개선 `iteratePrompt`(스펙 iterate-rewrite). 이 스펙은 `DEFAULT_TEMPLATES`의 사용처를 정리하려고 그 한 줄만 언급한다(R-07).
  - 이미지 생성·이미지 모드, 이미지 이해 서비스 내부. 이미지 입력 분기는 R-14에서 경계만 정의한다.
  - Pro 모드 메시지 최적화(`optimizeMessage`·`optimizeMessageStream`)와 `context*`·`conversationMessageOptimize` 유형 템플릿. 같은 `resolveOptimizationMessages`가 `advancedContext`(변수·메시지·도구)를 받는 것까지만 R-08에 쓴다.
  - 모델 관리·LLM 어댑터 내부(아래 경계), 히스토리 저장([history-chain](history-chain.md)), 템플릿 저장·관리 UI.
  - MCP 서버 자체(전송·모델 설정·세션). 최적화 도구 부분만 R-21.
- 외부 의존·선행 계약:
  - 선행 스펙 [template-rendering](template-rendering.md): `getTemplate`, `listTemplatesByType`, `processTemplate`(문자열은 system 하나 + `originalPrompt`가 있으면 user, 배열은 Mustache 렌더링), `createExtendedContext`, `helpers.toJson`. 이 스펙은 그 계약 위에서 "어떤 템플릿을 고르고 어떤 맥락을 넣는가"만 정한다.
  - 모델 관리자 `getModel(modelKey)`: 설정 객체 또는 `undefined`. 내부는 범위 밖.
  - **`llmService.sendMessage(messages, modelKey)`** (경계):
    - 입력: `Message[]`(비어 있지 않은 배열, 각 원소 `role ∈ {system,user,assistant,tool}`, `content`는 비어 있지 않은 문자열)와 `modelKey` 문자열.
    - 정상 결과: 모델 응답 본문 문자열. 추론(reasoning) 내용은 버려진다(구조화 응답 `content`만 반환).
    - 실패: 모델이 없거나 비활성(`enabled` 아님)이거나 메시지 형식이 틀리면 `RequestConfigError`. 어댑터 호출 중 그 밖의 오류는 `APIError`("Failed to send message: …")로 감싸서 던진다. 내용이 빈 메시지가 하나라도 있으면 `RequestConfigError`라서, 렌더링 결과 메시지가 빈 문자열이면 LLM 호출 전에 실패한다(R-10).
    - 스트리밍 `sendMessageStream(messages, modelKey, handlers)`: 같은 검증. 토큰마다 `onToken`(추론은 `onReasoningToken`), 끝나면 `onComplete(응답?)`. 실패하면 서비스가 `handlers.onError(오류)`를 부른 뒤 **같은 오류를 다시 던진다**. 어댑터도 자체로 `onError`를 부르므로 한 실패에 `onError`가 1~3번 불릴 수 있다(R-13, R-22).
  - 이미지 이해 서비스(경계): `understand({modelConfig, systemPrompt, userPrompt, images})` → 응답(`content` 문자열 포함), `understandStream(같은 입력, handlers)`. 내부(어댑터 선택·이미지 변환)는 범위 밖이다.
  - 시계·난수·네트워크: 이 모듈 자체에는 없다.
- 소유 상태·부작용: 없다. 템플릿·모델 설정·히스토리를 바꾸지 않는다. 호출 한 건은 독립이다(이전 호출 결과를 입력으로 쓰지 않는다). 호출자가 만든 스트림 콜백만 호출 중에 변경된다.

### 1.3 인터페이스와 데이터 의미 [필수]
| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `OptimizationRequest` | `optimizationMode: 'system'\|'user'`(필수), `targetPrompt: string`(필수), `modelKey: string`(필수), `templateId?: string`, `inputImages?: {b64: string, mimeType?: string}[]`, `contextMode?`, `advancedContext?: {variables?: map<string,string>, messages?: ConversationMessage[], tools?: ToolDefinition[]}` | C-01. `targetPrompt`·`modelKey`는 공백만 있으면 안 된다(R-01). 길이 제한은 코어에 없다. `templateId`가 빈 문자열이면 없는 것과 같다(R-03). |
| `optimizePrompt(request)` | → `Promise<string>` | 최적화된 프롬프트 한 개. 응답을 trim·코드펜스 제거·재시도하지 않는다. 실패는 모두 `OptimizationError`로 reject(R-12). |
| `optimizePromptStream(request, handlers)` | `handlers: {onToken(string), onReasoningToken?(string), onComplete(응답?), onError(Error)}` → `Promise<void>` | 결과 문자열을 돌려주지 않는다. 호출자가 `onToken`을 이어 붙인다. 오류 전달 규칙은 R-13. |
| 기본 템플릿 선택 | `optimizationMode` → 템플릿 유형 → 목록 첫 번째 ID | `'user'`면 `userOptimize`, 그 밖은 `optimize`. 결론은 R-04~R-06. |
| 내장 `optimize` 템플릿 5종(ID) | `general-optimize`, `output-format-optimize`, `analytical-optimize`, `soul-openclaw-compose`, `soul-hermes-compose` | 모두 **문자열** 내용. 중·영 두 판이 같은 ID(R-16). 목록 순서는 이 순서(R-05). |
| 내장 `userOptimize` 템플릿 3종(ID) | `user-prompt-professional`, `user-prompt-basic`, `user-prompt-planning` | 모두 **배열**(system, user) 내용. 목록 순서는 이 순서(R-05). |
| 템플릿에 들어가는 맥락 | `originalPrompt`, `optimizationMode`, `contextMode`, `renderPhase='optimize'`, `tools`, `hasInputImages`, `inputImageCount`, `inputImagesJson`, 사용자 변수 최상위 펼침, `customVariables`, `conversationMessages`, (있으면) `conversationContext`·`toolsContext` | 내장 `optimize`·`userOptimize` 8종이 실제로 읽는 키는 `originalPrompt`와 `helpers.toJson`뿐이다(R-08). |
| `OptimizationError` | `[error.prompt.optimization] <details>` | `originalPrompt` 필드에 호출 때의 `targetPrompt`를 담는다(C-18). |

### 1.4 행동 규칙과 남은 질문 [필수]
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `targetPrompt`가 비었거나 공백뿐 / `modelKey`가 비었거나 공백뿐 | LLM·템플릿 조회 전에 `OptimizationError`("Target prompt is required" / "Model key is required"). 두 검사는 이 순서. `optimizationMode`·`inputImages`·`templateId`는 검증하지 않는다. | 코드 확인 |
| R-02 | `modelManager.getModel(modelKey)`가 falsy | `OptimizationError("Model not found")`. 비활성 모델은 여기서 걸리지 않고 LLM 호출 단계(`RequestConfigError`)에서 실패한다. | 코드 확인 |
| R-03 | 템플릿 결정 | `templateId`가 truthy면 `getTemplate(templateId)`, 아니면(미지정·빈 문자열) 기본 템플릿 ID(R-04)로 `getTemplate`. 템플릿의 유형을 검사하지 않는다(시스템 모드에 `userOptimize` 템플릿 ID, 그 반대, 심지어 `iterate` 유형 ID도 통과한다). `getTemplate`의 오류(NOT_FOUND, ID 형식 오류)는 그대로 올라가 R-12로 감싸진다. 읽은 템플릿의 `content`가 falsy면 `OptimizationError("Template not found or invalid")`. | 코드 확인 |
| R-04 | **기본 템플릿 선택(결론)** — `templateId` 없이 코어 `optimizePrompt`/`optimizePromptStream`을 부를 때 | 유형(`optimizationMode==='user'` ? `userOptimize` : `optimize`)에 대해 `listTemplatesByType(유형)`을 부르고 **첫 번째 원소의 ID**를 쓴다. 상수 `DEFAULT_TEMPLATES.OPTIMIZE`(`general-optimize`)는 이 경로에서 읽지 않는다. | 코드 확인 |
| R-05 | 목록 순서(R-04의 "첫 번째"가 무엇인지) | `listTemplates` = 내장 먼저, 그다음 사용자 템플릿(`lastModified` 내림차순). 내장끼리는 정렬 비교가 0이라 `ALL_TEMPLATES` 선언 순서가 유지되고, 언어별 집합은 그 선언 순서대로 쌓인다. 결과: `optimize` 목록 = `general-optimize` → `output-format-optimize` → `analytical-optimize` → `soul-openclaw-compose` → `soul-hermes-compose`, `userOptimize` 목록 = `user-prompt-professional` → `user-prompt-basic` → `user-prompt-planning`(중·영 모두 같은 순서). 따라서 기본값은 시스템 모드 `general-optimize`, 사용자 모드 `user-prompt-professional`이고, 사용자 템플릿이 있어도 해당 유형의 내장이 하나라도 있으면 사용자 템플릿이 기본이 되지 않는다. 같은 유형의 `context*`·`conversationMessageOptimize` 템플릿은 유형이 달라 목록에 섞이지 않는다. | 코드 확인(선언 순서·정렬 비교) / 순서 보존은 JS 안정 정렬(ES2019)에 의존해 추론 |
| R-06 | 기본 선택 폴백: 해당 유형의 목록이 비었거나 조회가 던질 때 | 순서대로 시도한다. ① `optimize`→`userOptimize` 목록 첫 번째, `userOptimize`→`optimize` 목록 첫 번째. ② 전체 `listTemplates`에서 `isBuiltin`인 첫 템플릿. ③ 모두 없으면 `ServiceDependencyError("No templates available for type: …")`. `listTemplatesByType`는 내부 오류를 삼키고 `[]`을 주므로 ①이 실제 분기이고, 내장 템플릿이 정상 로드되면 R-04에서 끝나 이 폴백은 도달하지 않는다. 오류는 R-12로 감싸진다. | 코드 확인 / 도달 불가는 추론 |
| R-07 | 기본 선택이 쓰이는 호출처 정리(선행 스펙 template-rendering R-17에서 넘어온 결정) | ① 코어 `optimizePrompt`·`optimizePromptStream`: `templateId` 없을 때만 R-04(목록 첫 번째). ② UI: 항상 `templateId`를 넘긴다. UI는 저장된 선택이 없거나 목록에 없으면 목록 첫 번째로 되돌리고 그 ID를 저장한다(코어와 같은 유형별 목록). ③ MCP: 항상 `templateId`를 넘긴다. 인자 `template`이 없으면 MCP 자체 함수가 같은 방식(유형별 목록 첫 번째)으로 고르고, 목록이 비면 폴백 없이 오류다. ④ `DEFAULT_TEMPLATES`: 값 `ITERATE`(`iterate`)만 `iteratePrompt`(비스트리밍)가 `templateId`가 없을 때 쓴다. `OPTIMIZE`와 `TEST`는 코드 어디에서도 읽지 않는다(검색 결과 사용처 없음). 반복 개선의 스트리밍 경로는 `templateId`가 필수 인자다(iterate-rewrite 스펙에서 확인). | 코드 확인(코어·MCP·UI 선택 로직·상수 검색) |
| R-08 | 메시지 생성: 맥락 구성 | 기본 맥락에 `originalPrompt`(=`targetPrompt`), `optimizationMode`, `contextMode`, `renderPhase`(항상 `'optimize'`), `tools`, `hasInputImages`, `inputImageCount`, `inputImagesJson`(이미지마다 `{index,label,mimeType}` JSON 배열 문자열, 이미지 없으면 `"[]"`)를 넣고, `createExtendedContext`로 `advancedContext.variables`를 최상위로 펼치고(같은 키가 있으면 위 기본 키 우선) `advancedContext.messages`를 `conversationMessages`에 넣는다. 메시지가 있으면 `conversationContext`, 도구가 있으면 `toolsContext` 텍스트도 넣는다. 결과로 `processTemplate(template, 맥락)`을 돌려준다(렌더링 규칙은 선행 스펙). 내장 `optimize` 5종은 문자열이라 맥락을 전혀 읽지 않고, `userOptimize` 3종은 `originalPrompt`만 읽는다. `renderPhase`·`hasInputImages`·`inputImageCount`·`inputImagesJson`은 내장 `optimize`·`userOptimize` 어느 템플릿에서도 쓰지 않는다. | 코드 확인(맥락 구성·템플릿 변수 검색) |
| R-09 | 시스템 모드 내장 템플릿(문자열)으로 만든 메시지 | `[{system, 템플릿 본문 그대로}, {user, targetPrompt 원문 그대로}]`. 프롬프트는 구분자·JSON 래핑 없이 user 메시지가 된다. 템플릿 본문 안의 `{{…}}`(예시 변수)는 치환되지 않는다(선행 스펙 R-02). | 코드 확인 |
| R-10 | 사용자 모드 내장 템플릿(배열)으로 만든 메시지 | 정확히 두 메시지 `[system, user]`. system은 역할·규칙 본문(변수 없음). user는 지시 문장 + 프롬프트를 `{"originalPrompt": <JSON 문자열>}` 블록으로 감싼 부분 + 출력 요청 한 줄. 프롬프트의 큰따옴표·줄바꿈은 JSON으로 이스케이프되고 `<`·`{{…}}`는 그대로 남는다(선행 스펙 R-05~R-07). 렌더링 결과 메시지 중 내용이 빈 것이 있으면 이후 `llmService`가 `RequestConfigError`로 거절한다(내장 8종은 해당 없음). | 코드 확인 |
| R-11 | 비스트리밍 LLM 호출·반환 | 이미지 입력이 없을 때 `llmService.sendMessage(messages, modelKey)`를 정확히 한 번 부르고, 응답이 `!response?.trim()`이면 `OptimizationError("LLM service returned empty result")`, 아니면 응답 문자열을 변경 없이 반환한다. 재시도·후처리(trim, 코드펜스 제거, 머리말 제거)·결과 검증(변수 보존 확인 등)이 없다. | 코드 확인 |
| R-12 | 오류 전달(비스트리밍과, 스트리밍의 사전 단계) | 함수 본문 전체가 `try`로 감싸여 있고, 어떤 오류든 잡아 `OptimizationError(targetPrompt, "Optimization failed: " + 원래 메시지)`로 다시 던진다. 원래 오류가 `PromptError`면 메시지에 코드 접두어(`[error.prompt.…]`)가 안쪽에 중첩되어 남는다. 원인 객체(`cause`)는 보존되지 않는다. 스트리밍 함수에서 LLM 호출 전에 나는 실패(R-01~R-03·R-08)는 `onError`를 부르지 않고 promise reject로만 전달된다. | 코드 확인 |
| R-13 | 스트리밍 `optimizePromptStream` | 검증·모델 조회·메시지 생성은 R-01~R-10과 같다. 이미지가 없으면 `llmService.sendMessageStream(messages, modelKey, h)`를 한 번 부르고, `onToken`·`onReasoningToken`은 호출자 콜백을 그대로 연결한다. `onComplete(응답)`에서 응답이 있으면 `content`가 비었는지 R-11 검사를 하고, 비었으면 호출자 `onComplete` 대신 `onError(OptimizationError("LLM service returned empty result"))`를 부른다(이 경우 바깥 "Optimization failed:" 래핑은 없고 promise는 reject되지 않는다). 통과하면 호출자 `onComplete(응답)`. 응답이 `undefined`면 검증 없이 `onComplete(undefined)`. **LLM 단계 실패의 오류 전달(확정)**: 서비스 계층 `LLMService.sendMessageStream`은 호출 전 검증·모델 조회·어댑터 선택에서 나는 실패와 어댑터가 던진 실패 모두를 `callbacks.onError(오류)`로 **정확히 한 번** 알린 뒤 같은 오류를 다시 던진다. 이어 `optimizePromptStream`이 이를 R-12처럼 `OptimizationError`로 감싸 reject한다. 따라서 호출자는 항상 `onError` ≥ 1번 **그리고** reject를 받는다. 어댑터가 자기 실패에서 `onError`를 추가로 부르는지는 어댑터마다 다르다(R-22). 반환 promise는 `sendMessageStream`의 settle을 따른다. 어댑터의 `doSendMessageStream`은 스트림을 끝까지 소비할 때까지 `await`하므로(R-22) promise는 스트림 종료(정상 `onComplete` 이후 또는 오류) 뒤에 settle한다. | 코드 확인(서비스 계층, 대표 어댑터 2종) |
| R-14 | 이미지 입력 분기(`inputImages` 길이 ≥ 1) — 경계만 | 템플릿 결정·메시지 생성은 같고, `llmService` 대신 이미지 이해 서비스를 부른다. `system` 역할 메시지의 `trim`한 내용을 빈 줄로 이어 `systemPrompt`, 나머지 메시지는 `user`면 내용, 그 밖이면 `ROLE:\n내용`으로 만들어 빈 줄로 이어 `userPrompt`로 보낸다(빈 것은 제외). 서비스가 주입되지 않았으면 `ServiceDependencyError`(R-12로 감싸짐). 이후 빈 응답 검사(R-11·R-13)는 같다. 이 경로에서 `modelConfig`는 `getModel` 결과 그대로 전달된다. 이미지 이해 서비스 내부(변환·비활성 모델 검사 등)는 읽지 않았다. | 코드 확인(분기·합치기) / 서비스 내부 미확인 |
| R-15 | 히스토리·저장 | 이 함수들은 히스토리를 저장하지 않는다(코드 주석이 호출자(UI) 몫임을 밝히고 호출 없음). 호출자가 완료 후 `createNewChain`을 부른다(history-chain). 모델 키·템플릿 ID는 호출자가 기록에 남긴다. | 코드 확인 |
| R-16 | 내장 템플릿 판 | 같은 ID에 중국어·영어 두 판이 있고 현재 내장 언어에 따라 `getTemplate`이 한 판을 돌려준다(선행 스펙 R-12·R-13·R-16). 이 스펙의 8개 ID는 모두 `-en` 접미 없이 두 판이 같은 ID다. 기본 선택 결과(R-05)는 두 언어에서 같다. | 코드 확인(ID·메타·선언 순서) |
| R-17 | **시스템 모드 내장 `optimize` 템플릿 5종의 구조·규칙**(영어 판 본문 읽음) | 공통: 한 덩어리 문자열이라 system 메시지가 되고 사용자 프롬프트는 별도 user 메시지(R-09). 출력은 "새 프롬프트 본문만, 머리말·설명 없이, 코드블록으로 감싸지 않기"를 지시한다(아래 각 항목에 예외 없음). 템플릿별: ⒜ `general-optimize` — 입력 프롬프트를 고정 골격(# Role, Profile, Skills, Rules, Workflows, Initialization 섹션과 각 섹션의 자리표시 항목)으로 **확장·재작성**하라고 지시하고 전문성·완성도·구조를 요구한다. "프롬프트를 실행하지 말라"는 명시 규칙은 없다(역할 지시 "다음 프롬프트를 최적화하라"에 의존). ⒝ `output-format-optimize` — ⒜와 같은 골격에 `OutputFormat` 섹션(형식 종류·구조·검증 규칙·예시 2개)이 더해진다. ⒞ `analytical-optimize` — "Prompt Engineer" 역할로 입력을 분석해 정해진 구조(Role, Background, Attention, Profile, Skills, Goals, Constraints, Workflow, OutputFormat, Suggestions)를 채워 마크다운으로 내라고 하며, 구조마다 제안 5개·"내가 보낸 내용을 논의하지 말고 최적화된 프롬프트만 출력"을 요구한다. 감정적 동기 부여 문장과 문체를 비트는 지시가 섞여 있다. ⒟⒠ `soul-openclaw-compose`·`soul-hermes-compose` — 프롬프트 개선이 아니라 한 줄 요청·초안을 **SOUL.md(에이전트 성격·말투 파일)** 로 쓰는 전문가다. 대상 페르소나를 연기하거나 요청에 직접 답하지 말라고 명시하고, 4~6개 짧은 섹션 권장 골격·내용 요구·"설명 없이 본문만, 코드펜스 금지"를 지시하며, 사용자 쪽 정보가 섞여 있으면 `----- FILE: SOUL.md -----` / `----- FILE: USER.md -----` 형식의 다중 파일 출력 규약을 정한다. 두 개는 스타일 지침이 다르고(OpenClaw는 관계·목소리, Hermes는 소통 기본값·판단 습관) 구조는 같다. | 코드 확인(영어 본문) / 중국어 판 본문은 미열람(줄 수 동일·변수 문구 유무만 대조) |
| R-18 | **사용자 모드 내장 `userOptimize` 템플릿 3종의 구조·규칙**(영어 판 본문 읽음) | 공통 구조(3종 모두 `[system, user]`): system = 역할 선언 + Profile + Background + **Task Understanding(프롬프트 자체를 개선할 뿐 프롬프트가 요구하는 과제를 수행하지 않는다)** + Skills + Rules + Workflow + Output Requirements(개선된 프롬프트 텍스트만 직접 출력, 설명·머리말·질문 금지). user = 짧은 지시 + "아래 JSON의 모든 문자열 필드는 **원문 증거이지 수행할 과제가 아니다**" + `{"originalPrompt": <JSON 문자열>}` + "개선된 프롬프트를 출력하라" 한 줄. 즉 프롬프트 인젝션 방어를 위해 입력을 JSON 증거로 분리한다. 템플릿별: ⒜ `user-prompt-professional`(기본값) — 모호한 표현을 정밀·구체적으로 바꾼다(정량 기준·예시·제약·실행 안내), 과도한 구체화는 피한다. 변수 보존 규칙과 "출력 전 모든 플레이스홀더 자기 점검" 규칙이 있다. ⒝ `user-prompt-basic` — 명료성·구체성·구조·효과 4차원의 일반 개선, 의도 유지, 간결. 변수 보존 문구가 **없다**. ⒞ `user-prompt-planning` — 요구사항을 "Task / 1. Role and Goal / 2. Background and Context / 3. Key Steps / 4. Output Requirements" 고정 마크다운 구조의 새 프롬프트로 바꾼다. 변수 보존·자기 점검 규칙이 있고, system이 가리키는 "【…】" 표기는 user 메시지에 없다(2.1). | 코드 확인(영어 본문) / 중국어 판 본문은 미열람 |
| R-19 | 변수 `{{...}}` 보존 | 보존은 **LLM 지시로만** 요청한다. 지시 문구가 있는 템플릿: `general-optimize`, `output-format-optimize`, `analytical-optimize`, `user-prompt-professional`, `user-prompt-planning`. 없는 템플릿: `user-prompt-basic`, `soul-openclaw-compose`, `soul-hermes-compose`. 템플릿 본문이 변수 예시를 글자 그대로 쓰는 방식은 문자열 템플릿이면 `{{x}}`를 그냥 쓰고, 배열 템플릿이면 구분자 변경(`{{=<% %>=}}`)으로 쓴다(선행 스펙 R-06). 코어에는 결과에서 원본의 `{{…}}`가 남았는지 검사하는 코드가 없다. | 코드 확인(문구 유무·후처리 없음) / 중국어 판은 변수 문구 유무를 줄 검색으로만 대조(추론) |
| R-20 | 모드와 모델의 독립 | `optimizationMode`는 (a) 기본 템플릿 유형 선택(R-04), (b) 맥락 키 `optimizationMode`로만 쓰인다. 템플릿 검증·내용 선택에는 쓰이지 않는다(R-03). 최적화 모델은 호출마다 `modelKey`로 정하며 테스트·평가 모델과 무관하다. | 코드 확인 |
| R-21 | MCP 서버의 노출 | 한 문단: MCP 서버는 코어 `PromptService`를 그대로 가져다 도구 2개 `optimize-user-prompt`·`optimize-system-prompt`로 노출한다. 입력은 `prompt`(필수, 비어 있지 않고 50,000자 이하)와 `template`(선택, 비어 있지 않은 문자열이고 허용 값은 서버 시작 때 각각 `userOptimize`·`optimize` 유형 목록으로 만든 enum, 기본값 표기는 R-05의 첫 번째). 호출은 `optimizePrompt({targetPrompt: prompt, modelKey: 'mcp-default', optimizationMode: 'user'\|'system', templateId: template \|\| 유형별 목록 첫 번째})` 한 번이고, 반환 문자열이 텍스트 콘텐츠 하나로 돌아간다. 스트리밍·이미지·`advancedContext`·모델 선택은 노출하지 않는다. `mcp-default` 모델이 없거나 비활성이면 도구가 오류 콘텐츠를 돌려주고, 그 밖의 모든 예외는 `Tool execution error: <메시지>`(`isError`)로 변환된다. 사용자 템플릿 추가는 서버 메모리 저장소에만 있어 기본으로는 내장 템플릿만 목록에 나온다(추론). | 코드 확인(도구 정의·호출·검증·오류 변환) / 메모리 저장소 부분은 추론 |
| R-22 | **스트림 오류 중복 전달 계약**(R-13의 어댑터 쪽) — LLM 단계(어댑터) 실패 | 추상 어댑터의 `sendMessageStream`은 메시지 검증(실패 시 던지기만, `onError` 없음) 뒤 `doSendMessageStream`을 `await`할 뿐 `onError`를 부르지 않는다. 구체 어댑터가 부른다: ⒜ **OpenAI**: `doSendMessageStream` 전체가 `try`이고 `catch`에서 `callbacks.onError(오류)`를 부른 뒤 `throw`한다(오류가 `Error`가 아니면 `Error(String(오류))`로 바꿔 전달하고 원본을 던진다). `responses` 요청 스타일(`getRequestStyle==='responses'`)은 내부 함수 `sendResponsesMessageStream`도 같은 `catch`(onError 후 throw)를 가져, 그 실패는 어댑터에서 `onError` 2번 + 서비스에서 1번 = **3번**이다. 그 밖에는 어댑터 1번 + 서비스 1번 = **2번**이고 같은 `Error` 객체다. ⒝ **Anthropic**: SDK 스트림 객체의 `error` 이벤트 핸들러가 `onError(error)`를 부르고, `finalMessage()`의 reject를 받은 `catch`가 `onError(handleError(error))`를 부른 뒤 `throw`한다(`handleError`는 `status`가 있는 SDK 오류를 `Anthropic API error (status): message`라는 **새 Error**로 바꾸고 아니면 원본을 쓴다). 스트림 오류에서 이벤트와 reject가 둘 다 일어나면(SDK 동작이라 추론) 어댑터 2번 + 서비스 1번 = 최대 **3번**이고 객체·메시지가 서로 다를 수 있다. `createClient`처럼 `try` 밖에서 나는 실패는 어댑터 `onError` 없이 서비스 1번뿐이다. 두 어댑터 모두 스트림을 끝까지 소비한 뒤(OpenAI `for await`, Anthropic `await finalMessage()`) 반환하므로 반환 promise는 스트림 종료 뒤에 settle한다. ⒞ 어느 경우든 서비스가 마지막으로 받는 오류는 어댑터가 **다시 던진 원본**이라, reject되는 `OptimizationError`의 메시지는 Anthropic이 `onError`에 준 `Anthropic API error (…)` 문구가 아니라 원본 SDK 오류 메시지를 담는다. ⒟ `onComplete`가 불린 뒤의 검증 실패(R-13)는 `onError`만 한 번 부르고 던지지 않는다. **구현 시 맞출 계약**: 호출자의 `onError`는 한 실패에 여러 번(최대 3), 서로 다른 오류 객체로 불릴 수 있다고 보고 멱등으로 만든다. 실패 확정 신호는 반환 promise의 reject이고 `onError`는 첫 호출을 진행 표시용으로만 쓴다. 이미 토큰이 전달된 뒤 실패해도 앞선 `onToken` 내용은 취소되지 않는다. | 코드 확인(추상 어댑터·OpenAI·Anthropic·서비스) / Anthropic SDK의 `error` 이벤트와 `finalMessage()` reject 동시 발생은 추론 / 나머지 어댑터(14종)는 읽지 않음 |

- 불변식: 한 번의 `optimizePrompt` 호출은 LLM(또는 이미지 이해 서비스) 호출을 최대 한 번만 한다(루프·재시도 없음). 반환값은 모델 응답 `content`를 변경 없이 돌려준 것이고, 비어 있거나 공백뿐인 응답은 결코 정상 결과로 반환되지 않는다(비스트리밍과 `response`가 있는 스트리밍 완료 모두). 내장 8종 템플릿에서 사용자 프롬프트는 (시스템 모드) user 메시지 전체이거나 (사용자 모드) user 메시지 안의 JSON 문자열 값이다.
- 미결정: 없음.
- 확인 한계: 설치·빌드·테스트 실행·모델 호출 없이 소스만 읽었다. 중국어 판 템플릿 본문은 읽지 않고 줄 수·`templateType`·변수 문구 검색으로만 영어 판과 대조했다. 추상 어댑터·OpenAI·Anthropic 외 어댑터 14종(스트림 오류 전달은 같은 계약을 따른다고 가정하지 않음, R-22), 이미지 이해 서비스 내부, UI의 스트리밍 소비 로직(토큰 이어 붙이기 외)은 읽지 않았다. 템플릿이 실제로 좋은 결과를 내는지(품질)는 확인하지 않았다. 원본 테스트는 파일·사례 이름(`core/tests/unit/prompt-service-enhanced.test.ts`, `core/tests/unit/prompt/service.test.ts`)만 검색했고 열지 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스: AGPL-3.0-only(overview 1절). 아래는 복사본이 아니라 위치다. 재구현자는 해당 범위를 읽고 직접 구현하며, 템플릿 본문(C-12·C-13)은 구조를 참고해 새로 쓴다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/core/src/services/prompt/types.ts:60-94` `OptimizationMode`, `OptimizationRequest` | 요청 필드와 선택 필드 | R-01, R-08, R-20 |
| C-02 | `packages/core/src/services/prompt/service.ts:86-91` `validateResponse`; `:847-854` `validateOptimizationRequest` | 입력·빈 응답 검증과 검사 순서 | R-01, R-11 |
| C-03 | `packages/core/src/services/prompt/service.ts:133-173` `optimizePrompt` | 비스트리밍 전체 흐름: 검증 → 모델 → 메시지 → 이미지 분기/`sendMessage` → 빈 응답 검사 → 오류 래핑 | R-01~R-03, R-11, R-12, R-14 |
| C-04 | `packages/core/src/services/prompt/service.ts:524-603` `optimizePromptStream` | 스트리밍 흐름, `onComplete` 검증, `onError` 연결, 외곽 래핑 | R-12, R-13, R-14 |
| C-05 | `packages/core/src/services/prompt/service.ts:909-960` `resolveOptimizationMessages` | 템플릿 결정, 맥락 키, `createExtendedContext`·`conversationContext`·`toolsContext`, `processTemplate` 호출 | R-03, R-04, R-08 |
| C-06 | `packages/core/src/services/prompt/service.ts:856-858` `hasInputImages`; `:895-907` `buildInputImagesManifest`; `:962-989` `splitMultimodalMessages` | 이미지 존재 판정, 이미지 목록 JSON, system/user 문자열 합치기 | R-08, R-14 |
| C-07 | `packages/core/src/services/prompt/service.ts:992-1082` `getDefaultTemplateId` | 유형별 목록 첫 번째, 폴백 표, 최종 오류 | R-04, R-06 |
| C-08 | `packages/core/src/services/prompt/service.ts:24-31` `DEFAULT_TEMPLATES`; `:296-306` | 상수 정의와 유일한 사용처(`ITERATE`) | R-07 |
| C-09 | `packages/core/src/services/template/default-templates/index.ts:157-166`, `:181-182`, `:187-190` `ALL_TEMPLATES` 중 optimize·userOptimize 항목 | 선언 순서(= 목록 순서) | R-05 |
| C-10 | `packages/core/src/services/template/static-loader.ts:92-156`, `:194-198`, `:227-229` `loadTemplates`, `loadTemplatesByLanguage`, `getDefaultTemplatesEn` | 언어별 집합에 선언 순서대로 삽입 | R-05, R-16 |
| C-11 | `packages/core/src/services/template/manager.ts:145-171` `listTemplates`; `:209-224` `getBuiltinTemplates`; `:283-293` `listTemplatesByType` | 내장 먼저·사용자 나중 정렬, 유형 필터 | R-05 |
| C-12 | `packages/core/src/services/template/default-templates/optimize/general-optimize_en.ts:1-77`, `output-format-optimize_en.ts:1-109`, `analytical-optimize_en.ts:1-122`, `soul-openclaw-compose_en.ts:1-120`, `soul-hermes-compose_en.ts:1-118` | 시스템 모드 템플릿 5종의 구조·규칙(문자열 내용, `templateType: 'optimize'`) | R-17, R-19 |
| C-13 | `packages/core/src/services/template/default-templates/user-optimize/user-prompt-professional_en.ts:1-86`, `user-prompt-basic_en.ts:1-83`, `user-prompt-planning_en.ts:1-108` | 사용자 모드 템플릿 3종의 `[system, user]` 구조, JSON 증거 블록(`helpers.toJson` + `{{{originalPrompt}}}`), 변수 예시의 구분자 변경 | R-10, R-18, R-19 |
| C-14 | `packages/core/src/services/llm/service.ts:36-54` `validateMessages`; `:59-77` `validateModelConfig`; `:82-121` `sendMessageStructured`·`sendMessage`; `:126-154` `sendMessageStream`; `packages/core/src/services/llm/types.ts:120-126`, `:144-174` | 경계 계약: 입력 검증, 오류 종류, `sendMessage`가 `content`만 돌려줌, 스트림 오류 후 재던짐 | 1.2, R-13 |
| C-15 | `packages/core/src/services/image-understanding/types.ts:5-12`; `service.ts:17-38` | 이미지 이해 서비스 입력·메서드(경계) | R-14 |
| C-16 | `packages/mcp-server/src/index.ts:71-78`, `:86-123`, `:160-262`, `:341-348`; `packages/mcp-server/src/config/templates.ts:12-65`; `packages/mcp-server/src/adapters/parameter-adapter.ts:11-27` | 도구 스키마, `optimizePrompt` 호출 인자, 기본 템플릿 ID, 입력 검증, 오류 변환 | R-07, R-21 |
| C-17 | `packages/ui/src/composables/workspaces/useWorkspaceTemplateSelection.ts:63-110` `refreshOptimizeTemplates`; `packages/ui/src/composables/workspaces/useBasicWorkspaceLogic.ts:195-208`; `packages/ui/src/composables/prompt/usePromptOptimizer.ts:138-150` | UI가 `templateId`를 항상 채워 넘기고 선택이 없으면 목록 첫 번째로 되돌림 | R-07 |
| C-18 | `packages/core/src/services/prompt/errors.ts:14-35`, `:72-80` `PromptError`, `OptimizationError`, `ServiceDependencyError` | 오류 메시지 형식 `[code] details`, `originalPrompt` 필드 | R-12 |
| C-19 | `packages/core/src/services/llm/adapters/abstract-adapter.ts:121-134` `sendMessageStream`; `openai-adapter.ts:1132-1135`(responses 경로), `:1352-1431` `doSendMessageStream`; `anthropic-adapter.ts:541-628` `doSendMessageStream` | 스트림 `onError` 호출 위치(어댑터별)와 재던지기, `handleError` 변환(`anthropic-adapter.ts:868-873`) | R-13, R-22 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출. 원본 테스트는 이름만 확인했고(2.1) 실행하지 않았다. 아래에서 LLM·이미지 서비스·모델 관리자는 호출 인자를 기록하고 고정 응답을 돌려주는 대체물을 쓴다고 가정하며, 따라서 어댑터와 실제 응답 품질은 검증하지 않는다. 내장 템플릿은 영어, 사용자 템플릿 없음.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-04, R-05, R-09, R-11 | `{optimizationMode:'system', targetPrompt:'P', modelKey:'m'}`(`templateId` 없음), 모델 `m` 존재, LLM이 `"X"` 반환 | LLM 호출 1회, 메시지 `[{system, general-optimize 본문}, {user,'P'}]`, 반환 `"X"` |
| T-02 | R-04, R-05, R-10 | 같은 요청이지만 `optimizationMode:'user'`, `targetPrompt: 'say "hi"\n{{x}}'` | 템플릿 `user-prompt-professional`. 메시지 2개 `[system, user]`. user 본문에 `"originalPrompt": "say \"hi\"\n{{x}}"` 형태(이스케이프된 JSON 문자열, `{{x}}` 그대로)가 들어간다 |
| T-03 | R-03, R-17 | `optimizationMode:'system'`, `templateId:'analytical-optimize'` | 그 템플릿 본문이 system, 프롬프트 원문이 user |
| T-04 | R-03 | `optimizationMode:'system'`, `templateId:'user-prompt-basic'` | 오류 없음. 배열 템플릿으로 `[system, user]` 2개 메시지가 만들어진다(유형 검사 없음) |
| T-05 | R-03 | `templateId:''` | 없는 것과 같다: 기본 템플릿(T-01/T-02) 사용 |
| T-06 | R-01 | `targetPrompt:'  '` / `targetPrompt:'P', modelKey:''` | 둘 다 `OptimizationError`("Optimization failed: [error.prompt.optimization] Target prompt is required" / "…Model key is required"). 모델 조회·LLM 호출 없음 |
| T-07 | R-02 | `modelKey`에 해당하는 모델 없음 | `OptimizationError`("…Model not found"), LLM 호출 없음 |
| T-08 | R-03, R-12 | `templateId:'no-such-template'` / `'AB'` | 앞의 것은 NOT_FOUND, 뒤의 것은 ID 형식 오류. 둘 다 "Optimization failed: …"로 감싼 `OptimizationError`. LLM 호출 없음 |
| T-09 | R-11 | LLM이 `""` 또는 `"  \n"` 반환 | `OptimizationError`(메시지에 "LLM service returned empty result"). 반환값 없음 |
| T-10 | R-11 | LLM이 `"  결과  "`(앞뒤 공백 포함) 반환 | 반환값이 정확히 `"  결과  "`(trim 안 함) |
| T-11 | R-19 | 프롬프트가 `{{city}}`를 포함하고 LLM이 `{{city}}` 없는 응답을 반환 | 그대로 정상 반환(보존 검사 없음) |
| T-12 | R-13 | 스트리밍, LLM이 토큰 `"a"`, `"b"` 후 `onComplete({content:'ab'})` | 호출자 `onToken`이 `a`, `b` 순서로 불리고 `onComplete({content:'ab'})`. promise는 값 없이 resolve. 서비스가 결과 문자열을 따로 돌려주지 않음 |
| T-13 | R-13 | 스트리밍, `onComplete({content:''})` | 호출자 `onComplete`는 불리지 않고 `onError`가 `OptimizationError`("LLM service returned empty result")로 불린다 |
| T-14 | R-12, R-13 | 스트리밍, `targetPrompt:''` | `onError` 미호출, promise가 `OptimizationError`로 reject |
| T-15 | R-13, R-22 | 스트리밍, OpenAI 어댑터(chat 스타일)가 요청 중 오류 `e`를 던진다(스트림 도중이면 앞선 토큰은 이미 전달됨) | 호출자 `onError`가 같은 `e`로 **2번**(어댑터, 서비스), promise는 "Optimization failed: …e.message"의 `OptimizationError`로 reject. 호출자 `onComplete`는 불리지 않음 |
| T-16 | R-14 | `inputImages:[{b64:'..',mimeType:'image/png'}]`, 이미지 이해 서비스가 `{content:'Y'}` 반환 | `llmService.sendMessage` 미호출. 서비스에 `{modelConfig, systemPrompt, userPrompt, images}` 전달(`systemPrompt`=system 메시지 합침, `userPrompt`=user 메시지 내용). 반환 `"Y"`. 서비스 미주입이면 "Optimization failed: …ImageUnderstandingService…" |
| T-17 | R-05 | 영어·중국어 각각 `listTemplatesByType('optimize')`, `('userOptimize')` | 순서가 R-05의 두 목록과 같다 |
| T-18 | R-05 | 사용자 템플릿(`userOptimize` 유형, ID `my-tpl`)을 저장하고 `templateId` 없이 사용자 모드 호출 | 템플릿 `user-prompt-professional`(사용자 템플릿 `my-tpl`은 목록 4번째) |
| T-19 | R-06 | `listTemplatesByType('optimize')`→`[]`, `('userOptimize')`→`[{id:'u1'}]` | 기본 선택 `u1`. 두 목록과 `listTemplates`의 내장이 모두 비면 "No templates available for type: optimize"(`ServiceDependencyError`가 감싸짐) |
| T-20 | R-07, R-21 | MCP `optimize-system-prompt`에 `template` 없이 `{prompt:'P'}` | `optimizePrompt({targetPrompt:'P', modelKey:'mcp-default', optimizationMode:'system', templateId:'general-optimize'})`. `prompt`가 50,001자면 `Tool execution error: Prompt must not exceed 50,000 characters` 오류 콘텐츠 |
| T-21 | R-22 | 스트리밍, Anthropic 어댑터에서 상태 코드 429 오류 발생(이벤트와 `finalMessage` reject가 모두 일어난다고 가정) | 호출자 `onError`가 최대 3번: 이벤트의 원본 오류, `Anthropic API error (429): …` 새 오류, 서비스가 받은 원본 오류. reject되는 `OptimizationError` 메시지는 원본 오류 메시지를 담는다 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-02 (`service.ts:847-854`), C-03·C-04 첫 줄 | 코드 읽음 |
| R-02 | C-03 (`service.ts:137-139`), `llm/service.ts:74-76`(비활성) | 코드 읽음. `getModel`이 비활성 모델을 돌려주는지는 모델 관리자 내부라 읽지 않음 |
| R-03 | C-05 (`service.ts:909-923`), `template/manager.ts:58-76` | 코드 읽음. 유형 검사 부재는 `resolveOptimizationMessages` 본문에 `templateType` 참조가 없음으로 확인 |
| R-04 | C-05 (`service.ts:909-915`), C-07 (`:992-1010`); `DEFAULT_TEMPLATES.OPTIMIZE` 검색: 선언 `service.ts:28` 외 사용처 없음(`packages/*/src` 전체 `DEFAULT_TEMPLATES` 검색) | 코드 읽음 + 검색 |
| R-05 | C-09 (`index.ts:157-166, 181-190`), C-10, C-11; 메타 `templateType`은 C-12·C-13 각 파일 | 선언 순서에서 도출. 정렬 안정성은 언어 명세 지식. `context*` 유형 분리는 `optimize/context/*`·`user-optimize/context/*`의 `templateType` 줄(`conversationMessageOptimize`, `contextUserOptimize`)로 확인 |
| R-06 | C-07 (`service.ts:1012-1082`), `template/manager.ts:283-293`(오류 삼킴) | 코드 읽음 |
| R-07 | C-16(`index.ts:196, 248`, `config/templates.ts:12-37`), C-17, C-08(`service.ts:303`), `service.ts:727-750`(스트리밍 반복 개선은 `templateId: string` 필수 인자) | 호출처를 `packages/*/src`에서 `optimizePrompt(Stream)`·`getDefaultTemplateId`·`DEFAULT_TEMPLATES` 검색으로 찾음. UI의 이미지·Pro 워크스페이스 호출자는 열지 않음(같은 `useWorkspaceTemplateSelection` 재사용으로 추정) |
| R-08 | C-05 (`service.ts:924-959`), 선행 스펙 R-08, 템플릿 변수 검색: `default-templates/optimize/*`·`user-optimize/*`의 `{{…}}` 사용은 `helpers.toJson`·`originalPrompt`와 변수 예시뿐, `renderPhase`는 `prompt/service.ts` 외 사용처 없음 | 검색으로 확인. 원본 테스트 이름 `should flatten advancedContext variables for sync optimizePrompt rendering`(`prompt-service-enhanced.test.ts:99`) 확인, 열지 않음 |
| R-09 | 선행 스펙 R-02·T-01, C-12 (문자열 `content`) | 템플릿이 문자열임은 5개 파일 읽음 |
| R-10 | 선행 스펙 R-03·R-05·R-06, C-13 | 3개 파일 읽음. 빈 메시지 거절은 C-14 `validateMessages`(`!msg.content`) |
| R-11 | C-03 (`service.ts:158-164`), C-02 | 코드 읽음. `sendMessage`가 `content`만 돌려줌은 `llm/service.ts:115-121` |
| R-12 | C-03 (`service.ts:165-172`), C-04 (`:595-603`), C-18 | 코드 읽음. 중첩 메시지는 `errors.ts:19`(`[code] details`)와 `OptimizationError` 생성자에서 도출 |
| R-13 | C-04 (`service.ts:571-603`), C-14 (`llm/service.ts:126-154`: `try`가 검증·모델 조회·어댑터 선택·어댑터 호출을 모두 감싸고 `catch`에서 `onError` 후 `throw`) | 코드 읽음 |
| R-14 | C-03 (`service.ts:144-157`), C-04 (`:538-568`), C-06, C-15 | 코드 읽음. 서비스 내부 미확인. 원본 테스트 이름 `should route image-aware optimizePrompt through image understanding service` 등 확인 |
| R-15 | `service.ts:162-163`, `:1084-1086` 주석(저장 호출 없음), 호출자 C-17(`useBasicWorkspaceLogic.ts:206-230`의 `createNewChain`) | 코드 읽음. history-chain과 일치 |
| R-16 | 8개 템플릿 파일의 `id`·`metadata.language`, 중국어 파일 줄 수·`templateType` 검색 | 영어·중국어 파일의 `id:`·`templateType:` 줄을 검색으로 확인. 선행 스펙 R-12 |
| R-17 | C-12 | 영어 본문 5개 파일을 끝까지 읽음. 각 템플릿 이름·`description`은 메타에서 확인. 중국어 `analytical-optimize.ts`는 148줄(영어 122줄)이라 본문 구성이 다를 수 있음, 읽지 않음 |
| R-18 | C-13 | 영어 본문 3개 파일을 끝까지 읽음 |
| R-19 | C-12·C-13에서 "변수·플레이스홀더" 문구 위치: `general-optimize_en.ts:66`, `output-format-optimize_en.ts:98`, `analytical-optimize_en.ts:44`, `user-prompt-professional_en.ts:43,44,55`, `user-prompt-planning_en.ts:39,40,52`; `user-prompt-basic_en.ts`·`soul-*_en.ts`에는 없음(검색 결과) | 검색+읽기. 후처리 부재는 C-03·C-04 본문 |
| R-20 | C-05, C-01 | 코드 읽음 |
| R-21 | C-16: `index.ts:86-123`(도구 정의), `:160-262`(호출), `:341-348`(오류), `parameter-adapter.ts:11-27`(검증), `config/templates.ts:43-65`(옵션 enum) | 코드 읽음. `mcp-default` 모델 구성과 메모리 저장소는 이 스펙 밖(overview 1절 Q2) |
| R-22 | C-19: `abstract-adapter.ts:124-134`, `openai-adapter.ts:1352-1431`(catch `:1427-1431`), `:1132-1135`, `anthropic-adapter.ts:541-628`(`error` 이벤트 `:619-621`, catch `:625-628`, `handleError` `:868-873`) | 대표 2종과 추상 클래스만 읽음. 이벤트+reject 동시 발생은 SDK 동작이라 추론. 14종 나머지는 `sendMessageStream`/`doSendMessageStream` 경로를 읽지 않음 |
| 문서와 구현 차이 ① | `service.ts:25`의 "Default template IDs used by the system" 주석 vs 실제로는 `ITERATE`만 사용(`OPTIMIZE`·`TEST` 미사용). overview 지도의 "기본 선택은 목록 첫 번째, 정렬 규칙 미확인"은 이 스펙에서 선언 순서로 확인됨 | 구현을 사실로 썼다 |
| 문서와 구현 차이 ② | `llm/types.ts:198` `sendMessage`는 `@deprecated`(구조화 응답 사용 권장) 표시인데 `optimizePrompt`가 사용한다(추론 결과 버려짐) | 구현을 사실로 썼다 |
| 문서와 구현 차이 ③ | `user-prompt-planning_en.ts:37,43`의 system 문장은 사용자 요구가 "【…】" 안에 있다고 하지만 user 메시지는 JSON 증거 블록 형식이라 "【…】" 표기가 없다(템플릿 내부 불일치. 동작은 JSON 블록 기준) | 구현을 사실로 썼다 |
| 문서와 구현 차이 ④ | overview 2절 Q2는 "프롬프트를 실행하지 말고 고쳐 쓰기만" 규칙을 `user-prompt-basic`의 특징으로 적었다. 구현에서는 사용자 모드 3종 모두 Task Understanding·Output Requirements에 같은 규칙이 있고(R-18), 시스템 모드는 `analytical`·`soul-*`에만 명시 규칙이 있고 `general-optimize`·`output-format-optimize`에는 없다(R-17). overview 지도 5행의 "analytical-optimize, output-format-optimize" 나열 순서는 목록 순서와 다르다 | 구현을 사실로 썼다 |
| T-01~T-20 | 구현에서 도출. 원본 테스트 사례 이름(`prompt-service-enhanced.test.ts`: should optimize system/user prompt successfully, should throw error for empty target prompt, should throw error for empty model key, should handle missing template gracefully, should route image-aware …, `prompt/service.test.ts`: 모델이 없을 때 오류)과 취지가 겹치지만 사례 본문은 열지 않았다 | 모두 미실행 |

### 2.2 코드 읽는 순서 [선택]
1. `prompt/types.ts:60-94` — 요청 모양.
2. `prompt/service.ts:133-173`(비스트리밍) → `:909-960`(템플릿·맥락) → `:992-1082`(기본 템플릿 선택) → `:524-603`(스트리밍 차이).
3. `template/default-templates/index.ts` 선언 순서 → `static-loader.ts:92-156`·`manager.ts:145-171, 283-293`(목록 순서가 어떻게 정해지는지).
4. 템플릿 본문은 `optimize/general-optimize_en.ts`(문자열)와 `user-optimize/user-prompt-professional_en.ts`(배열, JSON 증거 블록)를 나란히 읽고, 나머지는 차이만 본다.
5. MCP는 `mcp-server/src/index.ts:160-262`와 `config/templates.ts`.
구현 전략: 템플릿은 정적 import로 번들에 넣고 호출 때 렌더링만 한다. 최적화 서비스는 상태가 없다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드·템플릿 본문을 복사하지 않았다.

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-11 | 자동 반복은 이 모듈에 없으므로 "개선 → 평가 → 재개선" 루프는 호출자(우리 환경의 오케스트레이터)가 `optimize`를 여러 번 부르며 만든다. 한 호출 안에서 재시도·결과 검증을 두지 않는 원본 구조를 그대로 가져가도 된다. | 원본은 1호출이고 반복 개선은 별도 함수(iterate-rewrite)다. 평가·반복은 우리 환경의 별도 책임. | 인터페이스 변화 없음. 루프·종료 조건은 새 설계 |
| R-11, R-12 | 반환값 후처리를 호출자 쪽에 둔다: 앞뒤 공백·코드펜스 제거, SKILL.md frontmatter(이름·설명) 유지 확인. 오류는 이중 래핑 없이 원인 객체를 보존한다. | 원본은 응답을 그대로 반환하고 래핑이 중첩된다(R-12). SKILL.md는 frontmatter가 깨지면 쓸 수 없다. | 반환 타입을 `{text, raw}` 같은 구조로 할지는 우리 결정 |
| R-17, R-18 | 시스템 모드의 `general-optimize`류는 "역할극 프롬프트 골격(Role/Profile/Skills…)으로 확장"하는 템플릿이라 지침 문서(SKILL.md) 개선에는 맞지 않을 수 있다. 가져올 것은 구조 아이디어(역할 선언 + 실행 금지 규칙 + 출력은 본문만)이고 본문은 새로 쓴다. 입력은 사용자 모드 방식처럼 JSON 증거 블록으로 감싸 지시와 분리한다. | 시스템 모드 템플릿은 프롬프트를 user 메시지에 원문 그대로 넣어(R-09) 입력 안의 지시가 실행될 수 있다. 사용자 모드는 JSON 증거로 분리한다(R-18). AGPL-3.0-only라 본문 복사도 피한다. | 우리 템플릿은 전부 배열(system+user) 형식. 선행 스펙 적용 메모와 일치. T-01·T-09는 배열 형식으로 대체 |
| R-04, R-05, R-07 | 기본 템플릿은 "목록 첫 번째"라는 암묵 규칙 대신 설정이나 호출 인자에 명시 ID를 둔다. 폴백 체인(R-06)은 만들지 않는다. | 원본의 기본값은 선언 순서에 의존해 템플릿을 추가·재정렬하면 기본이 조용히 바뀐다. 상수 `DEFAULT_TEMPLATES.OPTIMIZE`도 쓰이지 않는 죽은 코드다. | T-17~T-19는 명시 ID 조회 사례로 대체, 폴백 사례(T-19) 생략 |
| R-19 | 변수(`{{…}}`) 보존을 LLM 지시에만 맡기지 말고 호출자가 사후 검사한다: 입력의 플레이스홀더 집합이 결과에 모두 남았는지 확인하고, 빠졌으면 실패로 표시한다. SKILL.md에 변수가 많으면 특히 필요. | 원본은 지시만 하고 검사하지 않으며(T-11), 일부 템플릿은 지시 자체가 없다(R-19). | 새 검사 단계 추가. T-11 반대 사례 추가 |
| R-20 | 모델 적합도 비교를 위해 `modelKey`만 바꿔 같은 템플릿을 여러 모델에서 돌리는 것은 호출자가 한다. 최적화에 쓴 모델·템플릿 ID·버전(`metadata.version`)을 결과와 함께 기록한다. | 원본 서비스는 모델 키만 받고 기록하지 않는다(R-15). 템플릿 본문이 바뀌면 같은 ID라도 결과가 달라진다. | 기록 필드는 우리 설계 |
| R-13, R-22 | 스트리밍 오류는 한 번만 전달한다: 어댑터는 `onError`를 부르지 않고 던지기만 하며, 서비스가 `onError` 한 번 + reject로 알린다(또는 `onError` 없이 reject만). | 원본은 어댑터·서비스가 각각 `onError`를 불러 한 실패가 최대 3번 알려지고 오류 객체도 달라진다. | 호출자 콜백이 멱등이어야 한다는 부담 제거. T-15·T-21은 "`onError` 정확히 1번"으로 대체 |
| R-21 | MCP는 모델을 `mcp-default` 하나로 고정하고 모델 선택·스트리밍을 노출하지 않는다. 우리 환경에서 도구로 노출한다면 `modelKey`를 인자로 받는다. | 모델별 적합도 기록에는 호출마다 모델 지정이 필요하다. | 도구 스키마에 `model` 인자 추가 |
