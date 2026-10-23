---
sha: "a201f47d2b17d6cf6a9347f336691b00c98720a1"
created: 2026-10-22
updated: 2026-10-22
sources:
  - packages/core/src/services/evaluation/service.ts
  - packages/core/src/services/evaluation/types.ts
  - packages/core/src/services/evaluation/errors.ts
  - packages/core/src/services/evaluation/structured-compare-prompts.ts
  - packages/core/src/constants/error-codes.ts
  - packages/core/src/constants/storage-keys.ts
  - packages/core/src/services/template/default-templates/evaluation/content.ts
  - packages/core/src/services/template/default-templates/evaluation/builders.ts
  - packages/core/src/services/template/default-templates/evaluation-structured-compare/builders.ts
  - packages/core/src/services/template/default-templates/evaluation-structured-compare/content.ts
  - packages/core/src/services/template/default-templates/evaluation-structured-compare/runtime-copy.ts
  - packages/core/src/services/model/manager.ts
  - packages/ui/src/types/evaluation.ts
  - packages/ui/src/stores/session/useBasicSystemSession.ts
  - packages/ui/src/composables/prompt/useEvaluation.ts
  - packages/ui/src/composables/prompt/useEvaluationHandler.ts
  - packages/ui/src/composables/prompt/compareEvaluation.ts
  - packages/ui/src/composables/model/useFunctionModelManager.ts
  - packages/ui/src/components/basic-mode/BasicSystemWorkspace.vue
  - packages/ui/src/i18n/locales/zh-CN/models.ts
  - packages/core/package.json
  - pnpm-lock.yaml
  - packages/core/tests/unit/evaluation/service.test.ts
depends:
  - ./template-rendering.md
status: ready
reimplementation: 미실행
---

# LLM 평가 (결과 평가·비교 평가·구조화 비교, 요청·응답 계약 포함)

> 프롬프트(와 선택적으로 그 프롬프트를 실제로 실행한 출력 스냅샷)를 담은 평가 요청을 받아, 별도 지정한 "심판" 모델을 1회 또는 (구조화 비교는) 쌍 수 + 1회 호출하고, 그 응답 텍스트를 점수(0-100)·차원 점수·개선 제안·한 줄 요약·패치 계획으로 이뤄진 단일 JSON 응답 구조로 정규화해 돌려준다.

경로 표기: 모든 `파일:줄`은 `repos/prompt-optimizer/` 기준이다. 라이선스는 AGPL-3.0-only(overview 1절)라서 코드·템플릿 본문은 C-ID(위치)로만 가리키고, 템플릿 본문은 구조·규칙만 글로 쓴다. 설치·빌드·실행·모델 호출은 하지 않았다(모든 검증 수준은 읽기 기준이다).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 호출자가 `EvaluationRequest`(유형 `result` / `compare` / `prompt-only` / `prompt-iterate` 중 하나, 심판 모델 key `evaluationModelKey`, 모드 `{functionMode, subMode}`, 선택 `focus`·`variables`)를 `evaluate`(결과 한 번) 또는 `evaluateStream`(토큰 콜백)에 넘긴다.
2. 요청을 검증하고(R-02~R-05), 심판 모델 key가 모델 관리자에 존재하는지 확인한다(R-06).
3. `compare`면 요청을 정규화해 **generic**(템플릿 1회 호출)인지 **structured**(구조화 비교)인지 정한다(R-17, R-18).
4. generic: 템플릿 ID `evaluation-{functionMode}-{subMode}-{type}`로 템플릿을 찾고(R-10), 평가 맥락(R-11~R-16)으로 렌더링해 심판 모델을 1회 호출한다.
   structured: 역할 쌍마다 판정 호출을 병렬로 실행하고(R-19~R-22), 쌍별 결과와 결정론적 힌트(R-23)를 합성 호출 1회에 넘긴다. 호출 수 = 쌍 수 + 1.
5. 심판의 응답 텍스트에서 JSON 후보를 뽑아 복구·파싱하고 점수·차원·개선안·패치 계획을 정규화한다(R-24~R-30). JSON이 없으면 텍스트에서 점수만 추출하는 강등 경로가 있고, 그것도 안 되면 파싱 오류다.
6. 결과에 `type`과 `metadata`(모델·시각·소요시간, compare는 모드·역할·판정·정지 신호·인사이트)를 붙여 반환한다(R-29). 오류의 전달 방식은 호출 방식(`evaluate` / `evaluateStream`)에 따라 다르다(R-01, R-31).
7. (UI 경계) UI는 결과를 워크스페이스 세션 저장소에 "유형별 최신값 하나"로만 보관한다(R-33).

### 1.2 범위·통합 지점 [필수]
- 제공: 평가 요청·응답 데이터 모양, 요청 검증, 평가 맥락 키(템플릿에 넘기는 변수), compare의 generic/structured 결정과 구조화 비교의 판정·합성 호출 구조, 심판 응답 JSON의 파싱·정규화·강등, 패치 계획 정규화, 오류 계열, 심판 모델 지정 규칙(UI 기본 해석 순서 포함), 결과 저장 모양(UI 세션).
- 제외:
  - 평가 결과 기반 재작성(`rewrite-from-evaluation.ts`, UI `createRewriteFromEvaluationHandler`). 경계만: 재작성은 이 스펙의 `EvaluationResponse`(`summary`·`improvements`·`patchPlan`·compare `metadata`)를 읽는 소비자다(C-20). 별도 스펙 iterate-rewrite.
  - 평가 UI 컴포넌트(패널·점수 배지 등).
  - 이미지·멀티모달 평가의 상세. 경계만 R-05에 적었다. 이미지 입력이 있으면 `ImageUnderstandingService.understand`로 한 번 호출하고 generic compare로 강제된다는 것까지만 확인했다.
  - 구조화 비교 보정 스크립트(별도 스펙 calibration-script).
  - 템플릿 렌더링 규칙·평가 템플릿 ID 조립·템플릿 조회: 선행 스펙 [template-rendering](./template-rendering.md)(R-02~R-06, R-16, R-18~R-20)을 따르고 여기서 복제하지 않는다. 이 스펙은 그 스펙이 넘긴 "평가 맥락 키 정의"(1.3, R-11~R-16)를 가진다.
  - 모델 관리·LLM 어댑터, 테스트 영역 실행(스냅샷 만드는 쪽).
- 외부 의존·선행 계약:
  - `ILLMService`: `sendMessage(messages, modelKey) → string`, `sendMessageStream(messages, modelKey, handlers)`. 평가는 응답 본문 텍스트만 쓴다(추론 토큰 제외, `llm/service.ts:115-121`). 호출마다 온도·타임아웃·취소·재시도 인자를 넘기지 않는다(R-22).
  - `IModelManager.getModel(key)`: 심판 모델 존재 확인에만 쓴다(R-06).
  - `ITemplateManager.getTemplate(id)`, `getCurrentBuiltinTemplateLanguage()`: 선행 스펙의 조회 규칙. 언어값 `'en-US'`만 영어, 그 밖에는 중국어로 취급(R-20).
  - JSON 복구 라이브러리 `jsonrepair`(`packages/core/package.json:41` `^3.13.3`, 잠금 파일 `pnpm-lock.yaml:2751` 해석 버전 3.15.0). 함수 하나 `jsonrepair(text) → string`을 R-24 지점에서 호출한다. 내부 복구 범위는 확인 한계.
  - (선택) 이미지 이해 서비스·이미지 저장 서비스: 멀티모달 경계.
  - 원본 호출자: UI 합성 함수 `useEvaluation`(요청 조립·모델 key 해석)과 `useEvaluationHandler`. MCP 서버에는 평가 도구가 없다.
- 소유 상태·부작용: 서비스는 상태가 없다(요청마다 계산, 입력 객체를 바꾸지 않는다). 부작용은 모델 호출과 `console.warn`(파싱 후보 실패·강등 파싱) 뿐이다. 결과 보관은 호출자(UI 세션 저장소) 몫이다(R-33).

### 1.3 인터페이스와 데이터 의미 [필수]

타입은 중립 표현이다. 필드 이름은 외부 계약이라 원문 그대로 쓴다. 정확한 필드 목록은 C-01~C-04.

**연산**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `evaluate(request)` | `EvaluationRequest` → `EvaluationResponse`(async) | 오류는 예외로 던진다(R-01, R-31). |
| `evaluateStream(request, handlers)` | → void(async) | `handlers.onToken(string)`, `onComplete(EvaluationResponse)`, `onError(Error)`. **예외를 던지지 않고** 모든 오류를 `onError`로 보낸다. `onScore`는 선언만 있고 서비스가 호출하지 않는다. 구조화 비교에서는 판정 단계 진행 문구도 `onToken`으로 나간다(R-20). |

**요청(EvaluationRequest)** — 공통 필드(`EvaluationRequestBase`)

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `type` | `'result' \| 'compare' \| 'prompt-only' \| 'prompt-iterate'` | 그 밖의 값은 검증 오류(R-03). |
| `evaluationModelKey` | string | 심판 모델 key. 공백뿐이면 검증 오류. 이 key 하나로 모든 호출(구조화 비교의 판정 N회와 합성)을 보낸다. 평가 대상(스냅샷)의 모델과 달라야 한다는 검사는 없다(R-07). |
| `mode` | `{functionMode: 'basic'\|'pro'\|'image', subMode: string}` | 둘 다 필수(비어 있지 않음)이고 값 집합은 검증하지 않는다. 템플릿 ID 조립에 쓰이고, 없는 조합은 템플릿 조회 실패로만 드러난다(R-10). |
| `focus` | `{content: string, source?: 'user'\|'system', priority?: 'highest'}`? | `content`를 trim해 비어 있지 않을 때만 "포커스 있음"으로 취급한다(R-11). `source`·`priority`는 서비스가 읽지 않는다. |
| `variables` | map<string,string>? | 템플릿 맥락 최상위로 펼쳐진다(R-11). UI는 항상 `{language}`를 넣는다(R-34). |

유형별 추가 필드:

| 유형 | 추가 필드 | 비고 |
|---|---|---|
| `result` | `target`, `testCase`, `snapshot` | 스냅샷 1개를 평가. `snapshot.testCaseId == testCase.id` 필수(R-03). |
| `compare` | `target`, `testCases[≥1]`, `snapshots[≥2]`, `compareHints?` | 스냅샷 N개를 한 번에 비교(R-03, R-17). |
| `prompt-only` | `target` | 실행 출력 없이 프롬프트 설계만 평가. |
| `prompt-iterate` | `target`, `iterateRequirement` | 위와 같되 "반복 개선 요구사항을 만족하는가"를 평가. |

공유 하위 구조: `EvaluationTarget{workspacePrompt(필수), referencePrompt?, designContext?: ContentBlock}`, `EvaluationTestCase{id, label?, input: ContentBlock, settingsSummary?}`, `EvaluationSnapshot{id, label, testCaseId, promptRef{kind:'workspace'|'original'|'version'|'custom', version?, label?, dynamicAlias?:'previous'}, promptText, output, outputBlock?, reasoning?, modelKey?, versionLabel?, executionInput?}`, `ContentBlock{kind:'text'|'variables'|'conversation'|'image'|'json'|'custom', label, content, summary?, media?: [{label, assetId? | b64?, mimeType?}]}`(C-02). `compareHints{mode?:'generic'|'structured', snapshotRoles?: map<snapshotId, role>, hasSharedTestCases?, hasSamePromptSnapshots?, hasCrossModelComparison?}`. 역할 6개: `target`, `baseline`, `reference`, `referenceBaseline`, `replica`, `auxiliary`(C-03).

**응답(EvaluationResponse)** — 모든 유형이 같은 모양이다.

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `type` | 요청의 `type` | 모델 응답이 아니라 요청에서 복사한다. |
| `score.overall` | number | 0~100으로 클램프. 정수 보장은 없다(R-26). |
| `score.dimensions` | list<`{key, label, score}`> | 심판이 준 차원 그대로(키 집합 검증 없음). 항상 1개 이상(R-27). |
| `improvements` | list<string> | 최대 3개(R-28). |
| `summary` | string | 모델이 문자열을 주지 않으면 `""`. |
| `patchPlan` | list<`{op:'insert'\|'replace'\|'delete', oldText, newText, instruction, occurrence?}`> | 최대 3개, 정규화된 것만(R-28). `result`·`compare` 내장 템플릿 계약은 패치 계획을 요구하지 않아 보통 `[]`다(R-32). |
| `metadata` | map? | `model`(심판 key), `timestamp`(ms), `duration`(ms). compare에서는 추가로 `compareMode`, `snapshotRoles`(structured만), `compareJudgements`, `compareStopSignals`, `compareInsights`(R-29). |

**오류 계열**(C-05). 모두 `EvaluationError(code, params?, message?)`의 하위이고 메시지는 `[<code>] <message>` 형식이다.

| 클래스 | 코드 | 언제 |
|---|---|---|
| `EvaluationValidationError` | `error.evaluation.validation` | 요청 검증 실패(R-02~R-05). |
| `EvaluationModelError` | `error.evaluation.model_not_found` | 심판 모델 key가 모델 관리자에 없음. `params.context`=key. |
| `EvaluationTemplateError` | `error.evaluation.template_not_found` | 평가 템플릿이 없거나 `content`가 빔. `params.context`=템플릿 ID. |
| `EvaluationParseError` | `error.evaluation.parse` | 응답에서 점수를 얻지 못함(R-30). |
| `EvaluationExecutionError` | `error.evaluation.execution` | LLM 호출 실패, 그리고 `evaluate`(비스트림)에서 모델 호출 이후의 모든 예외(R-31). `cause`에 원 오류. |

**평가 맥락 키**(템플릿 렌더링에 넘기는 변수; 선행 스펙이 "평가 스펙이 정의"하라고 넘긴 부분). 병합 순서가 곧 우선순위다: `variables` → 포커스 키 → 대상 키 → 유형별 키(뒤가 앞을 덮는다). 정확한 구성은 C-08.

| 그룹 | 키 | 값 |
|---|---|---|
| 변수 | `variables`의 모든 키 | 최상위로 그대로(예: `language`). |
| 포커스(전 유형) | `hasFocus`, `focusBrief` | `focus.content` trim 결과가 있으면 true·그 문자열, 없으면 false·`""`. |
| | `hasUserFeedback`, `userFeedback` | 구 템플릿용 별칭. `hasUserFeedback`=`hasFocus`. `userFeedback`은 포커스가 있을 때만 키가 생긴다. |
| 대상(전 유형, `target`) | `workspacePrompt`, `currentWorkspacePrompt`, `hasWorkspacePrompt` | trim한 워크스페이스 프롬프트(두 이름 같은 값). |
| | `referencePrompt`, `hasReferencePrompt`, `originalPrompt`, `hasOriginalPrompt` | trim한 참조 프롬프트(없으면 `""`). `originalPrompt`는 `referencePrompt`와 같은 값이다(이름만 구 템플릿용). |
| | `hasDesignContext`, `designContextKind`, `designContextLabel`, `designContextContent`, `designContextSummary`, `designContextJson`, `proContext` | `designContext` 블록이 유효(label 있고, content나 media 있음)할 때만 값이 있고 아니면 `false`/`""`. `designContextJson`·`proContext`는 `designContextContent`와 같은 값(구 별칭). |
| `prompt-only` | `optimizedPrompt` | **trim하지 않은** `target.workspacePrompt` 원문. |
| `prompt-iterate` | `optimizedPrompt`, `iterateRequirement` | 둘 다 trim 안 한 원문. |
| `result` | `evaluationTestCase`(정규화 객체), `testCaseLabel`, `hasTestCaseLabel`, `testCaseInputLabel`, `testCaseInputContent`, `testCaseInputSummary`, `hasTestCaseInputSummary`, `testContent`(=입력 content) | 테스트 케이스 입력(전부 trim). |
| | `evaluationSnapshot`(정규화 객체), `prompt`(=스냅샷 promptText), `testResult`(=output), `resultLabel`, `hasResultLabel`, `hasEditableWorkspaceTarget` | `hasEditableWorkspaceTarget`는 `promptRef.kind=='workspace'`이고 trim한 `promptText`가 trim한 `workspacePrompt`와 같을 때만 true. |
| `compare` | `compareMode`, `hasStructuredCompare`, `hasCompareRoleBindings`, `compareRoleBindings[{snapshotId, snapshotLabel, role, roleLabel}]` | structured일 때만 역할 바인딩이 채워진다. |
| | `compareTestCases`/`sharedTestCases`(같은 배열), `compareTestCaseCount`/`sharedTestCaseCount`, `hasCompareTestCases`, `hasSharedCompareInputs`, `hasSharedTestCases` | 증거가 같은 테스트 케이스는 하나로 합친 목록(R-17). `hasSharedTestCases` = 공유 입력이고 목록이 비지 않음. |
| | `compareSnapshots`, `compareSnapshotCount`, `hasCrossModelComparison`, `hasEditableWorkspaceTarget`, `compareHints{mode, snapshotRoles, hasSharedTestCases, hasSamePromptSnapshots, hasCrossModelComparison}` | 정규화된 스냅샷 배열 등. |
| | `compareVariants`, `compareVariantCount` | 구 템플릿용 별칭(스냅샷의 `prompt`·`output` 등 일부 필드). |

정규화 객체(테스트 케이스·스냅샷)는 trim한 값과 `has*` 불리언을 함께 가진다(예: `modelKey`/`hasModelKey`, `reasoning`/`hasReasoning`, 역할 `role`/`roleLabel`/`hasRole`/`isTarget`…, `promptRefLabel`, `promptMatchesWorkspace`, `executionInput*`). 이 필드 목록은 C-08(`NormalizedEvaluationTestCase`·`NormalizedEvaluationSnapshot`, `service.ts:62-111`)이 글보다 짧고 정확하다. `executionInput*`의 구 별칭 `input*`은 공용 테스트 입력을 채우지 않는다(주석: 중복 증거 방지). 내장 평가 템플릿은 `userFeedback`·`hasUserFeedback`·`proContext`·`compareVariants`·`originalPrompt`·`language`를 쓰지 않는다(`default-templates/evaluation*` 검색 결과 없음) — 사용자 정의 템플릿 호환용으로만 남아 있다.

**결과 저장(UI 세션)** — `PersistedEvaluationResults`(C-18)

| 필드 | 타입 | 의미 |
|---|---|---|
| `result` | map<variantId, `EvaluationResponse \| null`> | 결과 평가는 테스트 열 id(variantId, 예 a/b/c/d)별. |
| `compare` | `EvaluationResponse \| null` | 비교 평가 최신 1건. |
| `prompt-only` | `EvaluationResponse \| null` | 최신 1건. |
| `prompt-iterate` | `EvaluationResponse \| null` | 최신 1건. |

이 외에 비교 역할 지정(`compareSnapshotRoles`, `compareSnapshotRoleSignatures`)도 같은 세션에 들어간다. 일시 UI 상태(패널·스트리밍·진행 중)는 저장하지 않는다.

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `evaluate` 처리 순서 | ① 요청 검증 ② 심판 모델 존재 확인 ③ compare면 정규화, structured면 구조화 경로로 분기(템플릿 조회 없음) ④ 템플릿 조회 ⑤ 맥락 생성·렌더링 ⑥ 이미지 증거가 있으면 이미지 이해 서비스, 아니면 `sendMessage` 1회 ⑦ 응답 파싱. ①②④⑤의 예외는 try 밖이라 원래 종류 그대로 던져진다. ⑥⑦(구조화 경로 전체 포함)의 예외는 `EvaluationExecutionError`로 감싸 던진다(R-31). `evaluateStream`은 같은 순서이되 모든 오류(①②④⑤ 포함)를 `onError`로 보내고 반환한다. | 코드 확인 |
| R-02 | 공통 검증 | `evaluationModelKey`가 trim 후 비면, `mode`가 없으면, `mode.functionMode`가 비면, `mode.subMode`가 비면 각각 `EvaluationValidationError`. 값의 종류(basic/pro/image 등)는 보지 않는다. | 코드 확인 |
| R-03 | 유형별 필수 필드 | `result`: `target.workspacePrompt` 비어 있지 않음, 테스트 케이스·스냅샷 유효(R-04), `snapshot.testCaseId == testCase.id`. `compare`: `workspacePrompt` 비어 있지 않음, `testCases` 배열 길이 ≥1, `snapshots` 배열 길이 ≥2, 테스트 케이스 id 유일, 각 스냅샷의 `testCaseId`가 테스트 케이스 id 중 하나. `prompt-only`: `workspacePrompt` 비어 있지 않음. `prompt-iterate`: 같음 + `iterateRequirement` trim 후 비어 있지 않음. 알 수 없는 `type`은 `Unknown evaluation type` 오류. 위반은 모두 `EvaluationValidationError`(첫 위반에서 즉시). 스냅샷 id의 유일성은 검사하지 않는다. | 코드 확인 |
| R-04 | 내용 블록·테스트 케이스·스냅샷 검증 | 테스트 케이스: `id`가 trim 후 비어 있지 않음, `input` 블록 존재, 블록 `label` 비어 있지 않음, `content`가 trim 후 비어 있지 않거나 유효 미디어(`assetId` 또는 `b64`가 비어 있지 않음)가 하나 이상. 미디어 항목: `label` 필수, `assetId`와 `b64` **정확히 하나**. 스냅샷: `id`·`label`·`testCaseId`·`promptText`·`output`이 모두 trim 후 비어 있지 않고 `promptRef.kind`가 있어야 한다(즉 **빈 출력은 평가할 수 없다**). `executionInput`·`outputBlock`이 있으면 같은 블록 검증. 공백만 있는 문자열은 비어 있는 것으로 본다. | 코드 확인 |
| R-05 | 이미지 경계(상세 제외) | `functionMode=='image' && subMode=='text2image'`: `result`는 스냅샷 출력 이미지 증거가 1개 이상 있어야 하고, `compare`는 **모든** 스냅샷이 출력 이미지 증거를 가져야 한다(아니면 검증 오류). 이 모드와 "basic/system 모드에서 테스트 케이스 입력에 이미지가 있는 경우"에는 compare가 항상 generic으로 강제되고(R-18), 호출은 템플릿 렌더링 결과를 system/user로 나눠 이미지 이해 서비스로 보낸다(서비스가 없으면 `EvaluationExecutionError`). | 코드 확인(분기·검증) / 이미지 이해 서비스 본문 미탐색 |
| R-06 | 심판 모델 확인 | `modelManager.getModel(evaluationModelKey)`가 없음(undefined)이면 `EvaluationModelError`. `enabled` 등 모델 상태는 이 서비스가 보지 않는다. 모델 설정 검증은 LLM 서비스 호출 시점의 몫이다(이 스펙 밖). | 코드 확인 / LLM 서비스 쪽 검증은 일부만 읽음 |
| R-07 | 심판 모델 ≠ 평가 대상 모델 강제·경고 | **없다.** 코어는 `evaluationModelKey`를 스냅샷의 `modelKey`와 비교하지 않고, 같아도 오류·경고·표식이 없다(R-02·R-06이 검증의 전부). 구조화 비교의 모든 판정·합성 호출도 같은 key 하나를 쓴다(복수 심판·교차 심판 없음). 코어·UI·MCP에서 "자기 채점·편향"을 다루는 코드·문구는 키워드 검색(self-eval, 편향, same model 등)에서 찾지 못했다. | 코드 확인(서비스·검증 전체) / "어디에도 없다"는 키워드 검색 기반 추론 |
| R-08 | UI의 심판 모델 해석(호출 경계) | 요청의 `evaluationModelKey`는 UI가 평가 실행 시점에 채운다(요청 조립 때는 `''`). 해석 순서: ① 전역 설정 "평가 모델"(설정 키 `app:function-model:evaluation-model`) ② 전역 최적화(프롬프트 개선) 모델 key ③ 호출 워크스페이스가 준 폴백(보통 테스트 모델 key) ④ 활성 모델 중 첫 번째. 각 후보는 **활성 모델 목록에 있을 때만** 채택된다. 이미지 워크스페이스는 별도 `resolveEvaluationModelKey` 훅이 먼저 해석한다. 결과가 `''`이면 R-02로 검증 오류가 나서 `onError`로 간다. 따라서 평가 모델을 따로 고르지 않으면 심판은 기본적으로 **프롬프트를 개선하는 모델**이고, 그 모델은 테스트 대상 모델 중 하나와 같을 수 있다. UI 안내문(`evaluationModelHint`)도 같은 우선순위를 설명하고 독립성 경고는 없다. | 코드 확인 |
| R-09 | 심판에게 보이는 증거 | result·compare 템플릿과 구조화 비교의 판정·합성 payload는 스냅샷의 `modelKey`(있으면)와 `reasoning`(있으면)을 심판에게 그대로 보여 준다(가리지 않음). 구조화 판정의 left/right는 쌍 종류로 고정이다(항상 target이 left). 좌우 순서 교대·재판정은 없다. | 코드 확인 |
| R-10 | 템플릿 조회(generic 경로) | ID `evaluation-{functionMode}-{subMode}-{type}`로 `getTemplate`을 부르고, 실패하거나 `content`가 비면 `EvaluationTemplateError(templateId)`로 바꿔 던진다(조립·유효 조합은 선행 스펙 R-18·R-19). 구조화 비교 경로는 이 조회를 **하지 않는다**(전용 템플릿을 모듈에서 직접 가져옴, 선행 스펙 R-20). | 코드 확인 |
| R-11 | 맥락 기본 키 | `variables`를 얕게 펼친 뒤 `hasFocus`·`focusBrief`·`hasUserFeedback`(·`userFeedback`)를 **덮어쓴다**. 즉 `variables`에 같은 이름이 있어도 서비스 값이 이긴다. 포커스는 `focus.content`를 trim한 결과로만 판정한다. | 코드 확인 |
| R-12 | 대상 키 | 모든 유형이 `buildTargetContext` 결과(1.3 표 "대상")를 펼친다. `workspacePrompt`·`referencePrompt`는 trim하고, `designContext`는 label이 있고 (content 또는 미디어)가 있을 때만 유효로 본다. | 코드 확인 |
| R-13 | result 맥락 | 1.3 표 "result" 키. 스냅샷·테스트 케이스 정규화 객체와 평탄화 키(`prompt`, `testResult`, `testContent` …)를 같이 준다. `evaluationSnapshot.promptRefLabel`은 `promptRef.label`(trim) → `kind=='version'`이고 version이 숫자면 `v{version}` → `kind` 순서. | 코드 확인 |
| R-14 | compare 맥락 | 1.3 표 "compare" 키. 구조화 여부(`hasStructuredCompare`, `compareRoleBindings`), 합쳐진 테스트 케이스, 정규화 스냅샷, `hasCrossModelComparison`, `compareHints` 사본을 준다. 모델 응답이 아니라 요청·정규화 결과에서 오는 값이다. | 코드 확인 |
| R-15 | prompt-only·prompt-iterate 맥락 | 기본 키 + 대상 키 + `optimizedPrompt`(trim 안 한 `workspacePrompt`), prompt-iterate는 `iterateRequirement`(trim 안 한 원문). 출력 관련 키는 없다. | 코드 확인 |
| R-16 | 정규화 방식 | 문자열은 trim하고, 선택 문자열은 비면 `has*`가 false다. `promptMatchesWorkspace`/`hasDistinctPromptText`는 trim한 `promptText`와 `workspacePrompt` 일치 여부다. 역할이 있는 스냅샷만 `role`·`roleLabel`(Target/Baseline/Reference/Reference Baseline/Replica/Auxiliary)을 가진다. 입력 객체는 바꾸지 않는다. | 코드 확인 |
| R-17 | compare 정규화 | ① 테스트 케이스를 증거 키(`inputKind`+`inputLabel`+`inputSummary`+`inputContent`+`settingsSummary`)로 중복 제거해 `renderedTestCases`를 만든다(id가 달라도 내용이 같으면 하나, 처음 것 유지). ② `samePromptAcrossSnapshots` = `compareHints.hasSamePromptSnapshots`가 있으면 그것(`??`, `false`도 존중), 없으면 trim한 `promptText`가 전부 같은지. ③ `sharedCompareInputs` = (`hasSharedTestCases` 힌트 또는 스냅샷 `testCaseId`가 전부 같은지) **또는** 합친 테스트 케이스가 1개. ④ `crossModelComparison` = `hasCrossModelComparison` 힌트가 있으면 그것(`false`도 존중), 없으면 (같은 프롬프트 && 공유 입력 && 스냅샷의 비어 있지 않은 `modelKey`가 서로 다른 값 2개 이상). 이 플래그는 모드를 바꾸지 않고, generic 템플릿의 문구 분기(`hasCrossModelComparison`)와 구조화 합성 payload의 `scenario.crossModelComparison`에만 쓰인다. | 코드 확인 |
| R-18 | generic/structured 결정 | structured가 되려면 **모두** 필요: 이미지 강제(R-05) 아님 && `compareHints.mode=='structured'` && 역할 맵에서 `target`·`baseline`·`reference`·`referenceBaseline` 중 어느 하나도 2개 이상 지정되지 않음(`replica`·`auxiliary`는 여럿 허용) && 판정 계획(R-19)이 1개 이상. 아니면 generic. 역할 맵은 존재하는 스냅샷 id(trim)와 유효한 역할 값만 남긴다. **코어는 역할을 추론하지 않는다**(힌트가 없으면 항상 generic). structured일 때만 응답 `metadata.snapshotRoles`와 `compareRoleBindings`가 생긴다. UI는 역할을 따로 추론·검증해 힌트를 만든다(R-34). | 코드 확인 |
| R-19 | 판정 계획(쌍) | 역할 `target`이 없으면 쌍이 없다. 있으면 순서대로: `baseline`이 있으면 `target-vs-baseline`(pairType `targetBaseline`, 신호 `progress`: improved/flat/regressed/unclear, left=target·right=baseline); `reference`가 있으면 `target-vs-reference`(`targetReference`, `gap`: none/minor/major/unclear); `reference`와 `referenceBaseline`이 둘 다 있으면 `reference-vs-reference-baseline`(`referenceBaseline`, `promptValidity`: supported/mixed/unsupported/unclear, left=reference); `replica`마다 `target-vs-replica`, `target-vs-replica-2`…(`targetReplica`, `stability`: stable/unstable/unclear). `referenceBaseline`만 있고 `reference`가 없으면 그 쌍은 없다. `auxiliary`·역할 없는 스냅샷은 쌍에 들어가지 않는다(코어는 이들을 막지 않고 무시한다; UI는 auxiliary가 있으면 structured를 막는다). 쌍마다 `purpose` 문장이 있고 판정 payload에 들어간다. | 코드 확인 |
| R-20 | 구조화 비교 실행 | 먼저 언어를 정한다(`getCurrentBuiltinTemplateLanguage()`가 `'en-US'`면 영어, 그 밖·실패는 중국어). **쌍마다 판정 호출을 `Promise.all`로 동시에 시작**하고(각각 판정 메시지 → `sendMessage(…, evaluationModelKey)` → 파싱, R-21), 전부 끝나면 합성 메시지를 만들어 `sendMessage` 1회로 최종 응답을 얻고 R-24 이하로 파싱한다. 총 LLM 호출 = 쌍 수 + 1. 판정 메시지의 증거 payload(JSON 문자열로 삽입): `scenario{language, pairKey, pairType, pairLabel, purpose, signalName, allowedSignalValues, focusBrief?}`, `roleBindings`(전체), `testCases`(그 쌍의 두 스냅샷이 참조하는 것, 증거 중복 제거), `leftSnapshot`·`rightSnapshot`(id, label, role, testCaseId, promptRef{kind,label}, promptText, modelKey?, versionLabel?, output, reasoning?, executionInput?). 합성 메시지의 payload: `scenario{language, roleName, subjectLabel, sharedCompareInputs, samePromptAcrossSnapshots, crossModelComparison, focusBrief?}`, `roleBindings`, `deterministicHints{priorityOrder[targetBaseline, targetReference, referenceBaseline, targetReplica], signalSnapshot, derivedStopSignals?, learnableSignals(≤4), overfitWarnings(≤4), conflictSignals[{key, description}]}`, `judgeResults`(쌍별 결과 전체) — **원본 스냅샷 본문은 다시 넣지 않는다**. 입력 크기 제한·잘라내기는 없다. 스트리밍은 판정 시작·완료 문구와 "합성 중" 문구를 `onToken`으로 흘린 뒤 합성 호출만 토큰 스트리밍한다. 구조화 메시지는 모두 `[system, user]` 2개이고, 합성 시스템 프롬프트의 `roleName`·`subjectLabel`만 모드(basic system/user, pro multi/variable, 그 밖)에 따라 바뀐다(판정 프롬프트에는 없음). | 코드 확인 |
| R-21 | 판정 응답 파싱 | R-24의 후보 추출·복구를 쓰되 payload 탐색 조건이 다르다: 중첩 객체를 너비 우선으로 훑어 **`winner`가 left/right/none이고 `confidence`가 low/medium/high이며, `verdict`가 4개 값 중 하나이거나 `pairSignal`이 문자열이고, 보조 필드(pairSignal·analysis·evidence·learnableSignals·overfitWarnings 중 하나)가 있는** 첫 객체를 고른다. 선택되면: ① 쌍 식별(`pairKey`·`pairType`·`pairLabel`·좌우 스냅샷 id·label·role)은 **모델의 에코가 아니라 판정 계획 값**을 쓴다. ② `pairSignal`은 모델이 준 값이 이 쌍의 허용 목록에 있으면 그것, 없으면 `verdict` 문자열이 허용 목록에 있으면 그것, 아니면 `unclear`. ③ `verdict`는 4개 값이면 그대로, 아니면 `pairSignal`에서 도출(targetBaseline: improved→left-better, regressed→right-better, flat→similar; targetReference: minor/major→right-better, none→similar; referenceBaseline: supported→left-better, unsupported→right-better; targetReplica: stable→similar; 그 외 mixed). ④ `winner`는 유효하면 그대로, 아니면 verdict가 left-better→left, right-better→right, 나머지 none. ⑤ `confidence`가 유효하면 그대로(후보 조건상 항상 유효). ⑥ `analysis`는 비어 있지 않은 문자열이면 trim, 아니면 응답 원문 앞 4000자. ⑦ `evidence`·`learnableSignals`·`overfitWarnings`는 문자열 배열을 trim·빈 항목 제거 후 각 **최대 4개**. 선택된 payload가 없으면(또는 모든 후보 파싱 실패) **오류 없이 대체 판정**: verdict `mixed`, winner `none`, confidence `low`, pairSignal `unclear`, analysis=응답 원문 앞 4000자, 나머지 목록은 빈 배열. | 코드 확인 |
| R-22 | 구조화 비교의 실패·부분 실패 | 판정 호출 중 **하나라도 LLM 호출이 실패(reject)하면 전체가 실패**한다(`Promise.all`): 비스트림은 `EvaluationExecutionError`를 던지고, 스트림은 `onError`로 같은 오류를 보낸다. 이미 시작된 다른 판정 호출은 취소되지 않고 계속 돌며(스트림에서는 진행 문구가 이후에도 올 수 있음) 그 결과는 버려진다. 부분 결과(성공한 쌍만으로 합성)는 없다. 판정의 **파싱 실패는 실패가 아니라 대체 판정**(R-21)이다. 합성 호출 실패도 전체 실패다. 재시도·타임아웃·취소·샘플링 설정은 어디에도 없다. | 코드 확인 |
| R-23 | 결정론적 파생 신호 | 파싱된 쌍별 판정 목록(`compareJudgements`)이 있으면 코드가 다음을 계산한다. (a) `signalSnapshot`: progress·gap·promptValidity는 해당 쌍의 `pairSignal`(허용 값일 때), stability는 replica 쌍 중 하나라도 `unstable`이면 unstable, 전부 `stable`이면 stable, 그 외 unclear. (b) 충돌 신호: progress=improved && promptValidity=unsupported → `improvementNotSupportedOnReference`; improved && stability=unstable → `improvementUnstableAcrossReplicas`; progress=regressed → `regressionOutweighsCosmeticGains`; 어떤 판정이라도 `overfitWarnings`가 비어 있지 않으면 `sampleOverfitRiskVisible`. (c) 정지 신호 `{targetVsBaseline, targetVsReferenceGap, improvementHeadroom, overfitRisk, stopRecommendation, stopReasons}`: `overfitRisk`는 unsupported→high; (unstable && 과적합 경고)→high; mixed·unstable·경고→medium; (경고 없음 && supported && stable)→low; 그 외 미정. `improvementHeadroom`은 regressed→high; gap major→high; gap minor→medium; flat→(gap none && risk low ? low : medium); improved && gap none && risk low && validity≠unsupported && stability≠unstable→low; 그 외 미정. `stopRecommendation`은 (regressed 또는 risk high)→`review`; ((improved/flat) && gap none && headroom low && risk low && validity≠unsupported && stability≠unstable)→`stop`; headroom medium/high 또는 gap가 있으면→`continue`; 그 외 미정. `stopReasons`(≤4)는 고정 영어 문구(예: `target regressed vs baseline`, `little evidence for additional broad gains`)를 순위 정렬해 모은다. (d) 인사이트: 판정을 (쌍 종류 우선순위 targetBaseline<targetReference<referenceBaseline<targetReplica, 신뢰도 high 먼저, pairLabel) 순으로 정렬해 상위 4개를 `pairHighlights`로, 쌍 종류별 첫 판정을 `progressSummary`·`referenceGapSummary`·`promptChangeSummary`·`stabilitySummary`로, 증거·학습 가능 신호·과적합 경고는 빈도순(공백 정규화·소문자 키로 중복 제거) 각 최대 6개로, `conflictSignals`와 함께 `compareInsights`에 담는다. (e) **병합**: 최종 응답의 정지 신호는 모델이 합성 JSON에 넣은 `compareStopSignals`와 (c)의 값을 항목별로 **더 보수적인 쪽**으로 합친다(보수 순서: progress improved<flat<regressed, gap none<minor<major, headroom none<low<medium<high, overfitRisk low<medium<high, stopRecommendation stop<continue<review; 한쪽만 있으면 그 값). | 코드 확인 |
| R-24 | 응답 텍스트 → JSON 후보 → 복구·파싱 | **(1) 후보 순서** — 아래 순서로 모은 뒤, trim해서 비거나 200,000자를 넘는 것은 빼고 같은 문자열은 처음 것만 남긴다: ① 모든 코드 펜스 블록(언어 표기 무관) 중 `{`·`[`로 시작하거나 앞 200자에 `"score":`/`'score':`가 있는 것(출현 순) ② 응답에서 처음 나오는 `"score":`/`'score':` 위치에서 앞쪽으로 가장 가까운 `{`부터의 균형 잡힌 객체, 같은 방식의 `[`…`]` 배열 ③ 첫 `{`부터의 균형 객체, 첫 `[`부터의 균형 배열 ④ 응답 전체 문자열. 균형 탐색은 문자열 안의 괄호와 `\` 이스케이프를 건너뛴다(작은따옴표도 문자열 구분자로 취급). 균형이 안 맞으면 그 후보는 없다. **(2) 복구기 호출 조건** — 후보마다 **무조건** `jsonrepair(후보)`를 호출하고(이미 유효한 JSON도 포함) 그 반환 문자열을 `JSON.parse`한다. 그다음 payload 탐색(R-25) → 정규화(R-26~R-29)를 한다. 복구기·`JSON.parse`·정규화 중 **예외가 나면** 메시지만 `console.warn`하고 다음 후보로 간다(정규화가 던진 `EvaluationParseError`도 여기서 삼켜진다). 파싱 결과가 객체가 아니거나(문자열·숫자·null 등) 평가 payload가 없으면 **경고 없이** 다음 후보로 간다. 처음으로 정규화까지 성공한 후보가 결과다. **(3) 강등 진입** — 모든 후보가 위 어느 단계에서든 실패(예외 또는 payload 없음)로 소진되면, 즉 후보 목록이 비어 있어도, R-30의 텍스트 점수 추출로 간다. **(4)** 복구기에 요구되는 최소 계약: 유효한 JSON 문자열은 의미를 바꾸지 않고 돌려주고, 복구할 수 없으면 예외를 던지거나 `JSON.parse`가 실패하는 문자열을 돌려준다(어느 쪽이든 다음 후보로 넘어간다). 어디까지 복구하는지(후행 쉼표·따옴표 없는 키·주석·잘린 JSON 등)는 복구기마다 다르며 같은 라이브러리·버전을 쓰면 원본과 같은 동작이다(확인 한계). | 코드 확인 / 복구기 내부 동작은 확인 한계 |
| R-25 | 평가 payload 탐색 | 파싱된 값에서 너비 우선(최대 1000단계)으로 객체를 훑어 `score`가 정의된 첫 객체 중 평가처럼 보이는 것을 고른다: `score`가 숫자·문자열(단 `{key:string, label:string, score}` 꼴의 차원 항목은 제외)이거나, `score`가 `overall`·`dimensions`를 가진 객체이거나, 같은 객체에 문자열 `summary`·배열 `improvements`·배열 `patchPlan`이 있을 때. 따라서 `{evaluation:{…}}`·`{data:{…}}` 같은 래퍼도 통과한다. 없으면 그 후보는 건너뛴다. | 코드 확인 |
| R-26 | 점수 값 | `score`가 숫자·문자열이면 그 값이 `overall`. 객체면 `score.overall`. 값은 숫자면 그대로, 아니면 `parseInt(String(값))`(예 `"90/100"`→90, `"85.7"`→85)이고 NaN이면 그 항목은 없음으로 취급한다. 유효한 값은 0~100으로 클램프한다. 숫자 타입은 **반올림하지 않는다**(85.5는 85.5). `score`가 null이면 `EvaluationParseError`(R-24에서 삼켜짐). | 코드 확인 |
| R-27 | 차원 정규화 | `score.dimensions`가 배열이면: 객체 항목은 `key`(없으면 `name`)가 비어 있지 않은 문자열일 때만 채택하고 `label`(없으면 `title`, 없으면 key), 점수는 `score ?? value`; 숫자·문자열 항목은 `dim{순번}` 키의 자리표시 차원; 점수가 유효하지 않거나 key가 없는 항목은 **조용히 버린다**. 객체(map)면 `key→점수` 또는 `key→{label?, score|value}`로 읽는다. `dimensions`가 없으면 `score` 객체에 평탄하게 놓인 `goalAchievement`·`outputQuality`·`formatCompliance`·`relevance` 키만 차원으로 읽는다(현행 템플릿의 `constraintCompliance` 등은 이 목록에 없다). `overall`이 없고 차원이 있으면 차원 점수의 반올림 평균을 `overall`로 쓴다. 차원이 없고 `overall`만 있으면 `[{key:'overall', label:'综合评分', score}]` 하나를 만든다. 둘 다 없으면 파싱 오류. 차원 수·키 집합·`overall`과 차원의 일치는 검증하지 않는다. | 코드 확인 |
| R-28 | improvements·summary·patchPlan | `improvements`: 배열이면 각 항목을 `String()`으로 바꾸고 빈 문자열을 제거한 뒤 앞 3개; 비어 있지 않은 문자열이면 그 하나의 배열; 그 외 `[]`. `summary`: 문자열이면 그대로(trim 안 함), 아니면 `""`. `patchPlan`(`data.patchPlan` 또는 `[]`): 배열이 아니면 `[]`; 항목마다 객체가 아니면 버림; `op`가 insert/replace/delete가 아니면 `replace`; `oldText`는 HTML 엔티티(`&lt; &gt; &amp; &quot; &#39; &apos; &nbsp; &sol;`, 16진·10진 숫자 엔티티)를 되돌린 뒤 **빈 문자열이면 항목 버림**(insert도 포함); `newText`는 없으면 `""`이고 같은 엔티티 해제; `instruction`은 `String(값 || '')`(엔티티 해제 안 함); `occurrence`는 유한 **숫자 타입**이고 정수로 내린 값이 >0일 때만 포함. 정규화 **후** 앞 3개만 남긴다. `oldText`가 워크스페이스 프롬프트에 실제로 있는지, 삽입 규약(`newText`=`oldText`+삽입)을 지키는지는 서비스가 검증하지 않는다. | 코드 확인 |
| R-29 | 응답 metadata 조립 | 서비스가 만든 `metadata`(`model`=심판 key, `timestamp`, `duration`; compare는 `compareMode`, structured면 `snapshotRoles`와 `compareJudgements`)가 기준이고, 모델 JSON의 `metadata.compareMode`(또는 최상위 `compareMode`)는 서비스 값이 없을 때만 채택되고(compare에서는 서비스 값이 이긴다), `metadata.compareStopSignals`(또는 최상위)는 서비스가 직접 만들지 않으므로 형식이 맞으면 채택되어 R-23(e)의 병합 입력이 된다(`snapshotRoles`는 모델 값을 읽지 않는다). 정지 신호는 R-23(e)로 병합하고, 쌍별 판정이 있으면 `compareInsights`를 붙인다. 유의: 서비스가 판정을 주지 않는 경우(generic compare, 비compare 유형)에도 모델이 `compareJudgements`를 형식에 맞게 내놓으면 그대로 채택되어 정지 신호·인사이트가 파생된다(모델이 만든 값). 비compare 유형에서도 모델이 낸 `compareMode`가 `metadata`에 남을 수 있다. 정규화 `normalizeCompareJudgements`: `pairKey`·좌우 id·label이 비면 항목 버림, `pairType`이 4개가 아니면 버림, verdict·winner·confidence가 유효하지 않으면 `mixed`·`none`·`low`, 목록은 각 최대 4개. | 코드 확인 |
| R-30 | 강등 파싱과 최종 실패 | 모든 JSON 후보가 실패하면 텍스트에서 점수만 찾는다. 패턴 순서: `"overall": N`, `综合评分 N`, `总分/总评 N`, `评分 N`, `overall (score) N`, `score N`, `N/100`, `N分/点`. 첫 일치 중 0~100인 값을 `overall`로 쓴다(응답 텍스트 전체에서 검색하므로 JSON 밖 문장의 숫자도 잡힐 수 있다). 이때 결과는 차원 `[{key:'overall', label:'综合评分', score}]`, `improvements: []`, `patchPlan: []`, `summary: '评估完成（解析降级）'`(고정 중국어 문구)이고 `metadata`는 서비스가 만든 것 그대로다(**정지 신호 병합·인사이트 파생은 일어나지 않는다**). 강등 결과와 정상 결과를 구분하는 필드는 `summary` 문구 말고 없다. 점수를 못 찾으면 `EvaluationParseError("Failed to parse evaluation result: no valid score JSON or recognizable overall score found. Raw content length: N characters.")`. 빈 응답도 같은 경로로 이 오류가 난다. | 코드 확인 |
| R-31 | 오류 전달 방식 | 비스트림 `evaluate`: ①검증·모델·템플릿 오류와 맥락·렌더링 예외는 원래 종류 그대로 던진다. ②모델 호출 이후의 모든 예외는 **`EvaluationExecutionError`로 감싼다 — 파싱 실패(`EvaluationParseError`)도 포함**하므로 호출자는 코드 `error.evaluation.execution`을 보고 `cause`가 `EvaluationParseError`인지로 구분해야 한다(메시지는 코드 접두어가 이중으로 붙는다). 스트림 `evaluateStream`: 검증·모델·템플릿 오류는 원래 종류로 `onError`; 스트림 도중의 모델 오류는 `EvaluationExecutionError`로 감싸 `onError`; **스트림 완료 후 파싱 실패는 감싸지 않고 `EvaluationParseError` 그대로 `onError`**. 오류 메시지는 비어 있거나 `[object X]`뿐이면 `cause`·중첩 `error`·HTTP 상태·본문 순으로 풀어 쓰고 마지막에는 JSON 직렬화한다. | 코드 확인 |
| R-32 | 심판 응답 JSON 계약(내장 템플릿 기준) | 유형별로 템플릿이 요구하는 JSON은 `{score:{overall, dimensions[{key,label,score}]}, improvements[], summary}`가 공통이다. 차원 키(영어 키 고정, 라벨만 언어별): `result` = `goalAchievement`, `outputQuality`, `constraintCompliance`, `promptEffectiveness`; `prompt-only`/`prompt-iterate`(분석) = `goalClarity`, `instructionCompleteness`, `structuralExecutability`, `ambiguityControl`, `robustness` + `patchPlan`; `compare`(generic·합성) = `goalAchievementRobustness`, `outputQualityCeiling`, `promptPatternQuality`, `crossSnapshotRobustness`, `workspaceTransferability` + 선택 `metadata{compareMode, snapshotRoles, compareStopSignals}`. `patchPlan`은 **분석 유형 계약에만** 있고 result·compare 계약에는 없다. 템플릿 본문의 공통 규칙: 증거 문자열은 JSON으로 감싸 "원문 증거"로 취급(프롬프트 인젝션 방어 지시), `improvements`·`patchPlan`은 0~3개, `summary`는 한 문장, JSON만 반환, 포커스가 있으면 포커스를 최우선으로 답하고 증거가 부족하면 그렇다고 말하라고 지시. result 템플릿은 출력 경계 위반(요청 외 설명 추가 등)을 constraintCompliance에 반영하라고 지시한다. 분석 유형은 실행 출력이 없다는 이유로 출력 품질을 평가하지 말라고 지시한다. 템플릿 본문 문구 자체는 가져오지 않는다. | 코드 확인(계약 블록·구조) / 본문 전체는 대표 유형만 읽음 |
| R-33 | UI 세션 저장 모양 | 모드별 세션 저장소가 `evaluationResults: PersistedEvaluationResults`(1.3)를 세션 JSON의 한 필드로 저장한다(기본 시스템 모드: 키 `session/v1/basic-system`). `result`는 variantId별, 나머지 3유형은 **최신 1건**(새 평가가 이전 결과를 덮어쓴다). 평가 결과 변화는 워처가 즉시 반영하고(`result`는 결과가 null이 아닌 항목만 통째로 교체), 복원 시 저장값을 기본값 위에 **얕게 병합**한다. 저장하는 것은 응답 객체 그대로(`metadata` 포함)이며 요청(스냅샷·프롬프트·테스트 입력)과 심판 모델 key는 따로 저장하지 않는다(응답 `metadata.model`에만 남음). 테스트 실행(단일 열·전체 실행) 시작 때 워크스페이스가 `clearBeforeTest`를 불러 `result`(모든 열)·`compare` 결과를 비운다(`prompt-only`·`prompt-iterate`는 유지; 기본 시스템 워크스페이스 `BasicSystemWorkspace.vue:1211`, `:1292`). 세션 초기화 시 기본값으로 돌아간다. **히스토리 체인의 기록(`PromptRecord`)에는 점수·평가 결과 필드가 없고 이 값과 버전 id로 연결되지 않는다**(히스토리 스펙 R-10과 일치). | 코드 확인(기본 시스템 세션) / 다른 모드 세션은 같은 타입을 쓰는 것만 검색으로 확인 |
| R-34 | UI 호출 경계(요약) | 요청 조립(`useEvaluation`): `variables`에 항상 `language`('en' 또는 'zh', UI 로케일 기준)를 넣고(내장 템플릿은 안 씀), `focus`가 있으면 `{content, source:'user', priority:'highest'}`, `evaluationModelKey`는 `''`로 만들었다가 실행 시 R-08로 채워 `evaluateStream`을 호출한다. 결과 평가는 테스트 열(variant)마다 테스트 케이스 1개(`{variantId}-test-case`)와 스냅샷 1개(id=variantId, `modelKey`=열의 모델)로 조립한다. 비교 평가는 공유 테스트 케이스 1개(`shared-test-case`)와 준비된 열 전부를 스냅샷으로, **워크스페이스 프롬프트를 쓰는 스냅샷이 하나는 있어야** 조립된다(`compareHints`가 없는 코어 호출과 달리 UI는 항상 만든다). UI는 compare 힌트를 항상 계산한다: 같은 입력·같은 프롬프트·서로 다른 모델이면 `hasCrossModelComparison`; 역할은 사용자 지정(시드) 위에 `target`=첫 workspace 스냅샷, `baseline`=같은 모델·다른 프롬프트(버전 우선, '이전' 별칭 우선, 높은 버전), `reference`=다른 모델·같은 프롬프트, `referenceBaseline`=reference와 같은 모델·다른 프롬프트, `replica`=target과 같은 모델·같은 프롬프트, 나머지 `auxiliary`로 추론하고, UI 판정(`analyzeStructuredComparePlan`)이 structured일 때(중복 singleton 없음, target 정확히 1개, auxiliary 없음, 쌍이 1개 이상)만 `mode:'structured'`와 역할을 보낸다. `prompt-iterate`인데 요구사항이 비어 있으면 UI가 `prompt-only`로 대신 호출한다. 응답 상태(`isEvaluating`, 스트림 텍스트, 오류)는 유형·variant 별 일시 상태로 두고, 요청 id로 늦게 도착한 이전 응답을 버린다. | 코드 확인 |

- 불변식: `evaluate`가 값을 반환하면 `score.overall`은 0~100이고 `score.dimensions`는 1개 이상이며 `improvements`·`patchPlan`은 각각 3개 이하다. `type`은 요청의 `type`이다. 입력 요청 객체는 바뀌지 않는다. `evaluateStream`은 예외를 던지지 않고, `onComplete`와 `onError` 중 하나로 끝난다(전제: 호출자 콜백이 예외를 던지지 않음; 구조화 비교에서 판정 실패 후에도 남은 판정의 진행 문구 `onToken`이 올 수 있어 "onError 이후 토큰 없음"은 보장되지 않는다).
- 미결정: 없음. status 근거: 선행 스펙 [template-rendering](./template-rendering.md)이 `ready`(frontmatter `status: ready`, `depends: []` 확인)이고, 구현을 막는 미결정·모순이 없다. 복구기 내부 동작은 라이브러리 버전을 맞추면 정해지므로 확인 한계에 둔다(R-24).
- 확인 한계: 설치·빌드·실행·모델 호출 없이 소스만 읽었다. **`jsonrepair`(선언 `^3.13.3`, 잠금 해석 3.15.0)와 `mustache`의 내부 동작은 소스를 보지 않았다**: 어떤 깨진 JSON을 어디까지 복구하는지는 같은 라이브러리·버전을 쓰면 원본과 같고, 다른 복구기를 쓰면 구제되는 심판 응답이 달라져 파싱 성공률·텍스트 강등 빈도가 달라진다(R-24가 정한 후보 순서·호출 조건·실패 처리는 복구기와 무관하게 지킨다). 원본 테스트에는 복구기가 실제로 고쳐야 하는 입력 사례가 없다(2.1 참조). 원본 테스트(`packages/core/tests/unit/evaluation/*.test.ts`)는 파일명·사례명 검색까지 했고, `service.test.ts`의 `parse robustness` 5개 사례만 열어 읽었으며(T-31·T-32) 통과 여부는 모른다. LLM 서비스의 `sendMessage`(모델 `enabled` 검사·빈 응답 처리)와 이미지 이해 서비스, 패치 적용 로직(UI), 재작성 모듈은 읽지 않았다. UI 호출 경계는 `BasicSystemWorkspace.vue`·`useBasicSystemSession.ts`를 대표로 읽었고 다른 워크스페이스·세션은 같은 타입·같은 훅을 쓴다는 것까지만 검색으로 확인했다. 템플릿 본문은 유형별 계약 블록과 대표(분석·result 시스템/유저, compare 시스템/유저, 구조화 판정·합성) 구조를 읽었으나 pro·image 변형(≈40개)은 열지 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스: AGPL-3.0-only(overview 1절). 아래는 복사본이 아니라 위치다. 재구현자는 해당 범위를 읽고 직접 구현한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/core/src/services/evaluation/types.ts:14-47` `EvaluationType`, `EvaluationModeConfig`, `FocusBrief` | 유형 4개, 모드 설정, 포커스 모양 | R-02, R-11 |
| C-02 | `types.ts:110-206` `EvaluationContentBlock`, `EvaluationMediaItem`, `EvaluationTarget`, `EvaluationTestCase`, `EvaluationPromptRef`, `EvaluationSnapshot` | 요청 하위 구조의 필드 | R-03, R-04, R-13 |
| C-03 | `types.ts:211-322` `CompareAnalysisHints`, `StructuredCompareRole`, `CompareStopSignals`, `CompareJudgementPairType`, `CompareConflictSignal`, `CompareJudgement`, `CompareInsights` | 역할 6개, 판정·정지 신호·인사이트 필드와 허용 값 | R-17~R-23, R-29 |
| C-04 | `types.ts:329-355`, `:362-432`, `:439-523` `PatchOperation`, 요청 4종, `EvaluationScore`, `EvaluationResponse`, `EvaluationStreamHandlers`, `IEvaluationService` | 패치·요청·응답·서비스 인터페이스 | R-01, R-28, R-29 |
| C-05 | `packages/core/src/services/evaluation/errors.ts:12-82`; `packages/core/src/constants/error-codes.ts:11-17` | 오류 클래스 6개와 코드 문자열, 메시지 접두어 | R-31 |
| C-06 | `service.ts:275-327` `evaluate`; `:332-447` `evaluateStream`, `evaluateStreamInternal`; `:203-270` `formatExecutionErrorMessage`, `toError` | 처리 순서, 오류 감싸기 차이, 오류 메시지 풀어쓰기 | R-01, R-31 |
| C-07 | `service.ts:452-551` `validateRequest`; `:556-562` `validateModel`; `:1668-1744` `validateMediaItems`·`validateContentBlock`·`validateTestCase`·`validateSnapshot`; `:660-697` 이미지 모드 판정 | 검증 규칙 전부 | R-02~R-06 |
| C-08 | `service.ts:567-589` `getEvaluationTemplate`, `getTemplateId`; `:594-640` `buildTemplateContext`; `:1746-1789` `normalizeContentBlock`, `buildTargetContext`; `:62-111`·`:1791-1882` 정규화 객체 타입과 `normalizeTestCase`, `normalizeSnapshot`; `:1884-1972` `buildResultTemplateContext`, `buildCompareTemplateContext` | 평가 맥락 키와 정규화 | R-10~R-16 |
| C-09 | `service.ts:906-980` 역할 정규화; `:1974-2086` `normalizeCompareRequest`, `buildCompareTestCaseEvidenceKey`; `:2088-2161` `buildStructuredCompareJudgePlan` | 모드 결정, 공유·교차 모델 판정, 쌍 계획 | R-17~R-19 |
| C-10 | `service.ts:2163-2326` `evaluateStructuredCompare`, `evaluateStructuredCompareStream`, `executeStructuredCompareJudgePlan`, `resolveComparePromptLanguage` | 병렬 판정 → 합성, 스트리밍 진행 문구, 실패 전파 | R-20, R-22 |
| C-11 | `service.ts:2328-2468` `buildStructuredCompareJudgeMessages`, `buildStructuredCompareSynthesisMessages`; `:2510-2605` payload 변환 함수; `structured-compare-prompts.ts:15-184` payload 타입·판정 JSON 계약 생성·메시지 생성 | 판정·합성 요청 payload 구조 | R-20 |
| C-12 | `service.ts:2638-2864` `parseStructuredCompareJudgeResult`, `normalizeStructuredCompareJudgeVerdict`, `…Winner`, `findStructuredCompareJudgePayload`, `isStructuredCompareJudgePayloadCandidate` | 판정 응답 파싱·정규화·대체 판정 | R-21 |
| C-13 | `service.ts:2897-3102` `parseEvaluationResult`, `extractJsonCandidates`, `extractBalancedJsonSubstring`, `extractBalancedFrom` | 후보 추출 순서, payload 탐색, 균형 파서, 실패 시 흐름 | R-24, R-25, R-30 |
| C-14 | `service.ts:3107-3300` `normalizeEvaluationResponse` | 점수·차원·improvements·summary·metadata 정규화 전체 | R-26~R-29 |
| C-15 | `service.ts:3305-3357` `parseTextEvaluation`; `:3362-3430` `normalizePatchPlan`, `unescapeHtmlEntities` | 강등 패턴 목록, 패치 정규화·엔티티 해제 | R-28, R-30 |
| C-16 | `service.ts:982-1135` `normalizeCompareStopSignals`, `normalizeCompareJudgements`; `:1137-1632` `buildCompareInsights`, `buildCompareConflictSignals`, `summarizeStructuredCompareJudgeSignals`, `deriveCompareStopSignalsFromJudgements`, `mergeCompareStopSignals`, `pickConservative*`, `collectRankedCompareStrings` | 결정론적 파생 신호 알고리즘과 보수적 병합 | R-23, R-29 |
| C-17 | `packages/core/src/services/template/default-templates/evaluation/content.ts:867-997` `analysisJsonContract*`, `resultJsonContract*`, `compareJsonContract*`; `:22-200`·`:203-416`·`:418-792` 분석·result·compare 프롬프트 구성; `evaluation-structured-compare/content.ts:14-164` 판정·합성 프롬프트 구성; `…/runtime-copy.ts:73-136`, `:138-233` 모드별 주어 라벨, 쌍별 지침, 충돌 신호 문구 | 심판 JSON 계약(차원 키), 프롬프트 구조·규칙(본문은 복사하지 않음) | R-32, R-20 |
| C-18 | `packages/ui/src/types/evaluation.ts:10-15` `PersistedEvaluationResults`, `:17-46`; `packages/ui/src/stores/session/useBasicSystemSession.ts:104-106`, `:549-551`, `:719-724`; `packages/ui/src/composables/prompt/useEvaluationHandler.ts:297-329`, `:531-536` | 결과 저장 모양, 최신값 덮어쓰기·복원·비우기 | R-33 |
| C-19 | `packages/ui/src/composables/model/useFunctionModelManager.ts:93-105`, `:124-134`, `:154-165`; `packages/ui/src/composables/prompt/useEvaluation.ts:264-274`, `:321-326`; `packages/core/src/constants/storage-keys.ts:52-58` | 심판 모델 해석 순서와 설정 키, 활성 모델 필터 | R-08 |
| C-20 | `packages/core/src/services/evaluation/rewrite-from-evaluation.ts:369-439` `buildRewritePayload`, `buildRewritePromptFromEvaluation` (경계만) | 재작성이 `EvaluationResponse`를 소비하는 입구 | 1.2 제외 |
| C-21 | `packages/ui/src/composables/prompt/useEvaluation.ts:351-452`; `packages/ui/src/composables/prompt/compareEvaluation.ts:308-393`, `:479-606`, `:608-704`; `packages/ui/src/components/basic-mode/BasicSystemWorkspace.vue:1362-1422` | UI의 요청 조립, 역할 추론·structured 판정, 힌트 계산(호출 경계) | R-34 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출. 단 T-31·T-32는 원본 테스트 `packages/core/tests/unit/evaluation/service.test.ts`의 `parse robustness` 사례를 열람해 옮겼다(실행하지 않았으므로 실행 확인 아님; 나머지 `validateRequest`·`buildTemplateContext` 등은 describe 이름만 확인). 모델 호출은 대체물(고정 문자열을 돌려주는 LLM)로 가정하며, 복구기가 실제로 고쳐야 하는 입력은 다루지 않는다(원본 테스트에도 없음). 시간·소요 값은 기대값 조건으로 쓴다(`timestamp`≈현재, `duration`≥0).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | `evaluationModelKey: "  "`로 `evaluate` / 같은 요청으로 `evaluateStream` | 앞은 `EvaluationValidationError`를 던진다. 뒤는 예외 없이 `onError(EvaluationValidationError)` 한 번, 모델·LLM 호출 없음 |
| T-02 | R-03 | `compare`: 스냅샷 1개 / 스냅샷 2개인데 하나의 `testCaseId`가 `testCases`에 없음 / `testCases` id 중복 / `result`에서 `snapshot.testCaseId != testCase.id` | 모두 `EvaluationValidationError`, LLM 호출 없음. 스냅샷 id가 서로 같은 요청은 검증을 통과한다 |
| T-03 | R-04 | 스냅샷 `output: "  "` / 테스트 케이스 입력이 content 빈 문자열 + 유효 이미지 미디어 1개 / 미디어에 `assetId`와 `b64` 둘 다 | 앞은 검증 오류. 가운데는 통과. 뒤는 검증 오류 |
| T-04 | R-06 | 모델 관리자에 없는 key | `EvaluationModelError`(코드 `error.evaluation.model_not_found`, `params.context`=key). 같은 key가 스냅샷 `modelKey`와 같은 요청은 오류·경고 없이 진행(R-07) |
| T-05 | R-07, R-09 | `evaluationModelKey: "m1"`, 스냅샷 2개의 `modelKey`도 "m1"과 "m2" | 평가가 그대로 수행된다. 렌더링된 증거에 `modelKey`("m1"/"m2")가 포함된다 |
| T-06 | R-08 | 활성 모델 [A,B,C], 전역 평가 모델 설정=B, 전역 최적화 모델=A, 워크스페이스 폴백=C → 이어서 설정을 비움 → 설정 비우고 A를 비활성화 | 심판 key는 B → A → C(활성 목록에 있는 첫 후보). 활성 모델이 하나도 없으면 `""`라 `evaluateStream`이 검증 오류를 `onError`로 보낸다(그 전까지는 ④ 첫 활성 모델이 받친다) |
| T-07 | R-10 | 선행 스펙 T-10·T-11(템플릿 ID 조립·없는 조합) 그대로 | 선행 스펙 기대값. 추가: structured compare는 `evaluation-…-compare` 템플릿이 없어도 진행한다 |
| T-08 | R-11, R-12, R-15 | `prompt-only`, `workspacePrompt: "  P  "`, `variables: {language:"en", hasFocus:"x"}`, `focus` 없음 | 맥락: `workspacePrompt:"P"`, `optimizedPrompt:"  P  "`, `hasFocus:false`, `focusBrief:""`, `hasUserFeedback:false`, `userFeedback` 키 없음, `language:"en"`, `originalPrompt:""`, `hasReferencePrompt:false` |
| T-09 | R-11 | 위와 같되 `focus.content: " 속도 "` | `hasFocus:true`, `focusBrief:"속도"`, `hasUserFeedback:true`, `userFeedback:"속도"` |
| T-10 | R-13 | `result`, 스냅샷 `promptRef.kind:"workspace"`, `promptText`가 trim 후 `workspacePrompt`와 같음 / 다름 | `hasEditableWorkspaceTarget` true / false. `prompt`=trim한 `promptText`, `testResult`=trim한 `output` |
| T-11 | R-17 | 스냅샷 2개: 같은 `promptText`, 같은 `testCaseId`, `modelKey` "a"/"b", `compareHints` 없음 / 같은 입력에 `compareHints:{hasCrossModelComparison:false}` / 한쪽 `modelKey` 없음 | 순서대로 `crossModelComparison` true / false / false |
| T-12 | R-17 | 테스트 케이스 2개(id 다름, 입력 내용 같음), 스냅샷은 각각 하나씩 참조 | 합친 테스트 케이스 1개, `sharedCompareInputs` true |
| T-13 | R-18 | 역할 `{s1:target, s2:baseline}` + `mode:'structured'` / `{s1:target, s2:auxiliary}` / `{s1:target, s2:target}` / 힌트 없음 / 이미지 text2image | 앞만 structured(`metadata.compareMode:"structured"`, `snapshotRoles` 포함). 나머지는 generic(`compareMode:"generic"`, `snapshotRoles` 없음), 심판 호출 1회 |
| T-14 | R-19, R-20 | 역할 target·baseline·reference·referenceBaseline·replica·replica | 판정 쌍 키 `target-vs-baseline`, `target-vs-reference`, `reference-vs-reference-baseline`, `target-vs-replica`, `target-vs-replica-2`; LLM 호출 5회(동시 시작) 후 합성 1회 = 총 6회, 모두 같은 `evaluationModelKey`. 합성 입력에 스냅샷 `output` 본문이 직접 들어가지 않는다(판정 결과의 `analysis`·`evidence`만) |
| T-15 | R-21 | 판정 응답이 JSON 없는 산문 | 오류 없이 대체 판정(`mixed`/`none`/`low`/`unclear`, `analysis`=앞 4000자), 합성은 진행 |
| T-16 | R-21 | `targetBaseline` 판정 응답 `{"pairSignal":"improved","winner":"left","confidence":"medium","analysis":"x"}` | `verdict:"left-better"`(신호에서 도출), `winner:"left"`, `pairSignal:"improved"`, `evidence`·`learnableSignals`·`overfitWarnings` 빈 배열 |
| T-17 | R-21 | 판정 응답에 `winner` 누락 `{"verdict":"left-better","confidence":"high","pairSignal":"improved"}` / `pairSignal:"banana"`, `verdict:"left-better"`, winner·confidence 유효 | 앞은 후보 조건 미달이라 대체 판정. 뒤는 채택되며 `pairSignal:"unclear"`, `verdict:"left-better"` |
| T-18 | R-22 | 판정 3개 중 하나의 `sendMessage`가 reject | 비스트림: `EvaluationExecutionError`(원 메시지 포함), 합성 호출 없음, 부분 결과 없음. 스트림: `onError` 1회. 다른 두 판정은 취소되지 않는다 |
| T-19 | R-23 | 판정 1개: targetBaseline `pairSignal:"regressed"`, 경고 없음 | 파생 정지 신호 `{targetVsBaseline:"regressed", improvementHeadroom:"high", stopRecommendation:"review", stopReasons:["target regressed vs baseline"]}`(`overfitRisk`·`targetVsReferenceGap` 없음); `conflictSignals:["regressionOutweighsCosmeticGains"]` |
| T-20 | R-23 | targetBaseline `improved`, targetReference `none`, referenceBaseline `supported`, replica `stable`, 모든 `overfitWarnings` 빈 배열 | `overfitRisk:"low"`, `improvementHeadroom:"low"`, `stopRecommendation:"stop"`, `stopReasons:["little evidence for additional broad gains"]`, `conflictSignals` 없음 |
| T-21 | R-23 | T-19 판정 + 모델 합성 JSON의 `metadata.compareStopSignals.stopRecommendation:"stop"` | 병합 결과 `"review"`(보수적인 쪽) |
| T-22 | R-24, R-25, R-26 | 응답 ① ` ```json\n{"score":{"overall":"90/100","dimensions":[…]}} ``` ` ② `{"evaluation":{"score":{"overall":150}}}` ③ `점수는 다음과 같다 {"score": {"overall": -5}} 끝` ④ `{"score":{"overall":85.5}}` | ① `overall:90` ② 100(래퍼 통과, 클램프) ③ 0(본문 중 균형 객체 추출, 클램프) ④ `85.5`(반올림 없음) |
| T-23 | R-27 | `score:{"overall":70}` / `score:{"dimensions":[80,"60",{"key":"a","score":90},{"score":10}]}` / `score:{"overall":70,"dimensions":{"x":{"label":"X","score":50},"y":"abc"}}` | 앞: 차원 `[{overall,综合评分,70}]`. 가운데: `dim1:80`, `dim2:60`, `a:90`(key 없는 항목 버림), `overall`=평균 round(76.67)=77. 뒤: `[{x,"X",50}]`(`y`는 NaN이라 버림), `overall:70` |
| T-24 | R-28 | `improvements:["a","","b","c","d"]` / `improvements:"하나"` / `improvements:[1,null]` | `["a","b","c"]` / `["하나"]` / `["1","null"]` |
| T-25 | R-28 | `patchPlan` 항목 6개: ①`{op:"x",oldText:"&lt;a&gt;",newText:"&lt;b&gt;",instruction:"i",occurrence:2.7}` ②`{oldText:""}` ③`{op:"delete",oldText:"z"}` ④문자열 `"s"` ⑤`{oldText:"p",occurrence:"2"}` ⑥`{oldText:"q"}` | 정규화로 ②④가 버려진 뒤 앞 3개만 남는다: ①→`{op:"replace", oldText:"<a>", newText:"<b>", instruction:"i", occurrence:2}`, ③→`{op:"delete", oldText:"z", newText:"", instruction:""}`, ⑤→`{op:"replace", oldText:"p", newText:"", instruction:""}`(문자열 `occurrence`는 무시). ⑥은 잘린다 |
| T-26 | R-30 | 응답 `평가 결과입니다. 综合评分：82/100` (JSON 없음) | 강등 결과: `overall:82`, 차원 `[{overall,综合评分,82}]`, `improvements:[]`, `patchPlan:[]`, `summary:"评估完成（解析降级）"` |
| T-27 | R-30, R-31 | 응답 `"좋은 프롬프트입니다."`(숫자·JSON 없음) / 빈 문자열 | 비스트림 `evaluate`: `EvaluationExecutionError`, `cause`는 `EvaluationParseError`. `evaluateStream`: 완료 후 `onError(EvaluationParseError)`(감싸지 않음) |
| T-28 | R-31 | `evaluate`에서 모델 key는 있으나 템플릿이 없음 / `sendMessage`가 `{status:429, body:{message:"rate"}}` 형태의 비 Error 객체로 reject | 앞: `EvaluationTemplateError`가 그대로 던져진다(Execution으로 안 감쌈). 뒤: `EvaluationExecutionError`, 메시지에 `HTTP 429: rate` 계열 문구 |
| T-29 | R-29 | structured compare 성공 | `metadata`: `model`=심판 key, `timestamp`, `duration`, `compareMode:"structured"`, `snapshotRoles`, `compareJudgements`(쌍별, 각 목록 ≤4), 정지 신호(병합), `compareInsights`. generic compare는 `compareMode:"generic"`만 추가 |
| T-30 | R-33 | 열 a·b의 결과 평가 후 compare 평가, 이어서 다시 a를 평가 / 테스트 재실행 / 앱 재시작 | `result:{a:최신,b}`, `compare` 1건(a의 이전 결과는 덮어씀). 테스트 재실행 후 `result`·`compare`는 비고 `prompt-only`·`prompt-iterate`는 유지. 재시작 시 저장된 4개 필드를 기본값 위에 병합해 복원(저장에 없는 필드는 기본값). 저장 객체에 요청·심판 key는 없다 |
| T-31 | R-24, R-25, R-26 | (원본 테스트 사례, 코드 펜스) 심판 응답이 "Here is the result:" 문장 뒤에, 언어 표기가 없는 코드 펜스 하나가 유효한 평가 JSON 문자열을 감싼 형태. JSON: `score{overall:85, dimensions[{clarity,90},{structure,80}]}`, `improvements:["Add more examples"]`, `patchPlan[{replace…}]`, `summary:"Good prompt"` | `score.overall`=85, 차원 2개. 후보 ①(펜스 블록)이 복구기를 거쳐 그대로 파싱된다 |
| T-32 | R-24, R-30 | (원본 테스트 사례, 강등) 심판 응답이 `Overall score: 85/100` 한 줄뿐 | 모든 JSON 후보(응답 전체 1개)가 실패 또는 payload 없음으로 소진된 뒤 텍스트 강등: `score.overall`=85, 차원 `[{overall,综合评分,85}]`, `improvements:[]`, `patchPlan:[]`, `summary:"评估完成（解析降级）"`. 복구기가 예외를 던지든 문자열을 돌려주든 결과가 같다 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-06 (`service.ts:275-327`, `:332-447`) | 코드 읽음. `parseEvaluationResult` 호출이 `try` 안에 있음(`:305`, `:320`)을 확인 |
| R-02, R-03 | C-07 (`service.ts:453-550`) | 코드 읽음. 스냅샷 id 유일성 검사가 없음은 `validateSnapshot`(`:1719-1744`)과 `compare` 분기(`:508-515`)를 읽어 확인 |
| R-04 | C-07 (`service.ts:1668-1744`) | 코드 읽음 |
| R-05 | C-07 (`service.ts:479-483`, `:516-530`, `:660-697`), `:699-725` `executeMultimodalEvaluation`, `:1638-1666` | 분기·검증만 읽음. `resolveEvaluationMedia`(`:759-904`)는 읽지 않음 |
| R-06 | C-07 (`service.ts:556-562`); `model/manager.ts:855-866` `getModel` | `getModel`이 저장소 항목 유무만 보고 `enabled`를 거르지 않음을 확인. `llm/service.ts`의 모델 검증은 `sendMessageStream` 앞부분만 읽음 |
| R-07 | C-07 전체(`validateRequest`·`validateModel`); `git grep`으로 `self-eval`, `same model`, `偏差`, `自评` 등을 `core/src`·`ui/src`·`mcp-server/src`에서 검색 → 평가 편향 관련 코드·문구 없음(UI 문구 `sameModelDifferentPrompt`는 compare 역할 추천 문구) | 검증 코드는 읽음. "없다"는 검색 기반이라 `추론` 성격 |
| R-08 | C-19 (`useFunctionModelManager.ts:93-105`, `:124-134`); `useEvaluation.ts:264-274`; `i18n/locales/zh-CN/models.ts:217`, `en-US/models.ts:217`; `BasicSystemWorkspace.vue:1440-1450`(폴백으로 쓰는 테스트 모델) | 코드·문구 읽음. 워크스페이스별 폴백 식은 4곳 `git grep`으로 위치만 확인(basic-user는 basic-system과 같은 식, pro는 최적화 모델 우선) |
| R-09 | `default-templates/evaluation/content.ts:358-376`(result 유저 프롬프트의 `modelKey`·`reasoning`), `:704-728`(compare 유저 프롬프트); `service.ts:2552-2605` `toStructuredCompareSnapshotPayload`; `:2088-2161`(left=target 고정) | 코드 읽음 |
| R-10 | C-08 (`service.ts:567-589`), `:287`(generic에서만 호출)·`:282-284`(structured 선분기); 선행 스펙 R-18~R-20 | 코드 읽음 |
| R-11~R-16 | C-08 (`service.ts:594-640`, `:1746-1789`, `:1791-1882`, `:1884-1972`); 내장 템플릿의 키 사용은 `default-templates/evaluation/content.ts`의 `{{…}}` 목록 검색(구 별칭 키 사용 없음: `evaluation`·`evaluation-structured-compare` 디렉터리 `git grep` 결과 없음) | 코드 읽음. pro·image 템플릿은 이름 검색 범위에서만 확인 |
| R-17 | C-09 (`service.ts:1974-2074`) | 코드 읽음 |
| R-18 | C-09 (`service.ts:664-671`, `:906-980`, `:2018-2031`); UI 쪽 `compareEvaluation.ts:608-652`(힌트 계산) | 코드 읽음 |
| R-19 | C-09 (`service.ts:2088-2161`); UI 판정 `compareEvaluation.ts:308-393`의 auxiliary 차단 | 코드 읽음 |
| R-20 | C-10 (`service.ts:2163-2326`), C-11 (`:2328-2468`, `:2510-2605`; `structured-compare-prompts.ts:121-184`) | 코드 읽음. `buildStructuredCompareDebugArtifacts`(`:2470`) 결과는 `void`로 버려지는 죽은 호출이다(이식 불필요) |
| R-21 | C-12 (`service.ts:2638-2864`) | 코드 읽음 |
| R-22 | C-10 (`service.ts:2287-2309` `Promise.all`), 파일 전체에서 `retry`·`timeout`·`abort`·`temperature` 검색 결과 없음 | 코드 읽음 + 키워드 검색 |
| R-23 | C-16 (`service.ts:1137-1632`) | 코드 읽음. 사례 T-19~T-21은 손으로 추적한 도출 |
| R-24, R-25 | C-13 (`service.ts:2897-3102`: 후보 모으기 `:2988-3039`, 시도 루프 `:2950-2966`, 강등·최종 실패 `:2968-2977`); `packages/core/package.json:41`, `pnpm-lock.yaml:2751`(`jsonrepair` 3.15.0) | 코드 읽음. `jsonrepair` 내부 동작은 확인 한계. 원본 테스트 `packages/core/tests/unit/evaluation/*.test.ts`·`packages/core/tests`를 `jsonrepair`·`repair`로 검색해 복구기 전용 사례가 없음을 확인. 관련 사례: `service.test.ts`의 `parses JSON inside a fenced code block without a language tag`(T-31), `locates nested payloads that contain a score field`(R-25), `accepts dimensions as an object map`·`falls back to an overall-only dimension when dimensions are missing`(R-27), `extracts overall score from plain text when JSON parsing fails`(T-32). 앞의 네 사례는 입력이 유효한 JSON이라 복구기는 통과만 한다. 사례를 열어 읽음(실행 안 함) |
| R-26, R-27 | C-14 (`service.ts:3107-3235`) | 코드 읽음. 사례의 `85.5`·`"85.7"` 처리는 `parseInt` 분기(`:3125`)에서 도출 |
| R-28 | C-14 (`:3240-3250`), C-15 (`:3362-3430`) | 코드 읽음 |
| R-29 | C-14 (`service.ts:3252-3299`), C-16 (`:982-1135`), `buildResponseMetadata`(`:642-658`) | 코드 읽음. 모델 제공 `compareJudgements` 채택은 `:3267-3274` 병합식에서 도출 |
| R-30 | C-13 (`:2968-2977`), C-15 (`:3305-3357`) | 코드 읽음 |
| R-31 | C-06 (`:321-326`, `:428-446`, `:203-270`) | 코드 읽음 |
| R-32 | C-17 (`content.ts:867-997`, 프롬프트 구성 `:22-200`, `:203-416`, `:418-520`, `:674-745`; 구조화 `content.ts:14-164`) | 영어 본문 중심으로 읽음. 중국어 본문은 구조 동일로 간주(`추론`) |
| R-33 | C-18 (`types/evaluation.ts`, `useBasicSystemSession.ts`, `useEvaluationHandler.ts`); 다른 세션 스토어는 `git grep evaluationResults`로 동일 타입 사용만 확인; 히스토리 스펙 R-10 | 코드 읽음(대표 1개). 세션 저장 키 상수는 `stores/session/imageStorageMaintenance.ts:4` |
| R-34 | C-21 | 대표 워크스페이스(`BasicSystemWorkspace.vue`)와 공용 컴포저블 읽음 |
| T-01~T-30 | 위 R-ID의 근거에서 도출 | 모두 미실행. `service.test.ts`에 같은 취지의 describe 이름이 있음(열람 안 함) |
| 문서와 구현 차이 | ① `types.ts:440-446` 주석 "分数 (0-100)", `:434` 응답 설명은 정수를 암시하나 구현은 숫자 타입을 반올림하지 않음(R-26). ② 개요 기능 지도의 "역할이 주어지면 structured"는 실제로 `compareHints.mode='structured'`(UI가 계산)와 target 역할·쌍 1개 이상이 모두 있어야 한다(R-18). ③ 개요의 "서로 다른 모델 key이면 `crossModelComparison` 자동 판정"은 같은 프롬프트·공유 입력도 필요하고 힌트가 우선하며, 모드가 아니라 템플릿 문구 분기 플래그다(R-17). ④ 개요 Q1의 "결과 JSON에 `patchPlan`"은 파서가 모든 유형에서 받지만 result·compare 내장 계약은 요구하지 않는다(R-32). ⑤ `types.ts:390-391` compare 주석("원본과 최적화본 두 버전")과 달리 구현은 스냅샷 N개(≥2)다. ⑥ `EvaluationResponse` 기본 차원 라벨(`'综合评分'`)과 강등 `summary`는 UI 로케일과 무관한 고정 중국어다 | 구현을 사실로 썼다 |

### 2.2 코드 읽는 순서 [선택]
1. `evaluation/types.ts`(요청·응답 모양) → `service.ts:275-327` `evaluate`(처리 순서)와 `:452-551` `validateRequest`.
2. 맥락: `:594-640` → `:1763-1972`(`buildTargetContext`, 정규화, result·compare 맥락).
3. 구조화 비교: `:1974-2161`(모드·쌍 계획) → `:2163-2310`(병렬 판정 + 합성) → `:2328-2468`(메시지 payload) → `:2638-2864`(판정 파싱).
4. 응답 파싱: `:2897-3102` → `:3107-3300` → `:3305-3430`. 파생 신호는 `:1137-1632`.
5. 템플릿 계약: `default-templates/evaluation/content.ts:867-997`(JSON 계약)과 `evaluation-structured-compare/content.ts`.
6. UI 경계: `useEvaluation.ts:264-452`, `useFunctionModelManager.ts:93-105`, `compareEvaluation.ts`, `useEvaluationHandler.ts:297-329`.
원본의 구현 전략: 서비스 한 클래스에 요청 검증·맥락 조립·구조화 비교·응답 정규화가 모두 들어 있고(3443줄), 모델 응답 파싱은 "후보 여러 개를 관대하게 시도 → 실패하면 점수만 강등 추출"이라는 방어적 구조다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드를 복사하지 않았다.

## 적용 메모 [선택]
목적: 내 스킬(SKILL.md)을 여러 모델에서 평가·개선하고 모델 적합도를 기록하는 환경을 만들 때 가져올 것과 다르게 할 것.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-32, R-26~R-28 | **가져올 핵심**: 심판 응답을 `{score{overall, dimensions[{key,label,score}]}, improvements≤3, summary, patchPlan≤3}` JSON 하나로 받는 계약, 차원 키를 영어 고정·라벨만 언어별로 두는 방식, 점수 0~100 클램프, 증거를 JSON 문자열로 감싸 "원문 증거"로 취급시키는 입력 구성. 템플릿 본문은 직접 쓴다 | 평가 단위가 작고 응답이 기계 처리 가능하다. AGPL이라 문구는 복사하지 않는다 | 차원은 우리 평가 기준(예: 스킬 지시 준수·출력 형식·경계 위반)에 맞춰 새로 정한다. T-22~T-27은 파서 수락 사례로 재사용 |
| R-30, R-31 | 강등 파싱 결과와 정상 결과를 구분하는 필드(예: `parseQuality: 'json'\|'degraded'`)를 둔다. 비스트림에서도 파싱 오류를 `Execution`으로 감싸지 않고 종류를 유지한다. 강등 점수는 모델 적합도 집계에서 제외하거나 표시한다 | 원본은 `summary` 문구 외에 구분이 없고 텍스트 안의 임의 숫자를 점수로 잡을 수 있다. 점수를 기록·비교에 쓰면 오염 위험이 크다 | 응답에 품질 플래그 추가. T-26·T-27 기대값 변경 |
| R-07, R-08, R-09 | **심판 독립성 장치를 직접 만든다**: 심판 모델 ≠ 평가 대상 모델을 강제하거나 최소한 같으면 기록·경고하고, 심판의 모델 id·버전·템플릿 버전·샘플링 설정을 결과에 남긴다. 증거에서 `modelKey`를 가리고(익명 라벨), 쌍 비교는 좌우 순서를 바꿔 두 번 판정하거나 순서를 무작위화한다 | 원본은 강제·경고가 전혀 없고(R-07), 기본 심판이 "프롬프트를 개선한 모델"이며(R-08), 심판이 모델 이름과 고정된 좌우 위치를 본다(R-09) | `EvaluationRequest`에 `judge` 필드(모델 id·설정)와 대상 모델 목록, 검증 규칙 추가. 새 사례: 심판=대상일 때 오류 또는 `selfJudged:true` |
| R-17~R-23, R-29 | **구조화 비교의 구조(쌍별 판정 N회 병렬 → 결정론적 신호 파생 → 합성 1회)는 가져올 만하다.** 다만 원본의 역할(target/baseline/reference/…)은 "프롬프트 개선 정지 판단"용이다. 모델 적합도 비교에는 역할을 "같은 스킬 본문 × 모델 N개" 쌍(예: 기준 모델 대비 후보 모델)으로 다시 정의하고, 쌍별 판정 결과를 모델별로 기록한다 | 원본 compare 응답은 **하나의 전체 점수**이고 스냅샷별 점수가 없다(R-32). "모델 A가 B보다 적합"은 쌍 판정(`winner`·`confidence`·`pairSignal`)에서 읽어야 한다. 모델별 절대 점수는 `result` 평가를 모델×케이스로 반복해 얻는 편이 맞다 | 새 데이터: 모델×케이스×심판 점수 기록(버전 id 외래키; 히스토리 스펙 적용 메모와 연결). 호출 수·비용 상한 필요 |
| R-22 | 쌍별 판정은 `Promise.allSettled` + 쌍당 재시도·타임아웃을 두고, 실패한 쌍은 `failed`로 표시한 채 합성을 계속할지 정책으로 정한다. 취소(AbortSignal)를 지원한다 | 원본은 한 쌍의 호출 실패가 전체를 버리고, 남은 호출은 계속 돌아 비용이 나가며, 재시도·타임아웃이 없다 | 오류 모델·진행 이벤트 변경. T-18 기대값 변경 |
| R-21 | 판정 파싱 실패를 조용히 `unclear`로 대체하지 말고 `parseFailed` 표시를 남긴다 | 대체 판정이 정상 `unclear`와 구분되지 않아 집계가 오염된다 | 판정 결과에 플래그 추가. T-15 기대값 변경 |
| R-33 | 평가 결과를 세션의 "최신 1건"이 아니라 이력으로 저장한다(요청 스냅샷, 심판 설정, 응답 원문, 시각 포함) | 원본은 유형별 최신값만 보관하고 버전과 연결이 없어 모델 적합도 기록에 쓸 수 없다 | 저장 계약 신설(히스토리 스펙 적용 메모 R-10 항목과 동일 방향) |
| R-17~R-18 | 코어가 역할을 추론하지 않고 UI가 추론하는 원본 분담을 가져올 필요는 없다. 호출자가 역할을 명시하게 한다 | 원본의 역할 추론 규칙(R-34)은 프롬프트 개선 UI 전용이다 | `compareHints.snapshotRoles` 필수화 또는 별도 쌍 목록 입력 |
