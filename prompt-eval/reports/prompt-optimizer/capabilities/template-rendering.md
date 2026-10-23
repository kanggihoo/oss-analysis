---
sha: "a201f47d2b17d6cf6a9347f336691b00c98720a1"
created: 2026-10-22
updated: 2026-10-22
sources:
  - packages/core/src/services/template/processor.ts
  - packages/core/src/services/template/types.ts
  - packages/core/src/services/template/manager.ts
  - packages/core/src/services/template/languageService.ts
  - packages/core/src/services/template/static-loader.ts
  - packages/core/src/services/template/minimal.ts
  - packages/core/src/services/template/errors.ts
  - packages/core/src/services/template/default-templates/index.ts
  - packages/core/src/services/template/default-templates/evaluation/builders.ts
  - packages/core/src/services/template/default-templates/evaluation/basic/system/evaluation-result.ts
  - packages/core/src/services/template/default-templates/optimize/general-optimize_en.ts
  - packages/core/src/services/template/default-templates/iterate/iterate_en.ts
  - packages/core/src/services/template/default-templates/evaluation-rewrite/builders.ts
  - packages/core/src/services/evaluation/service.ts
  - packages/core/src/services/evaluation/types.ts
  - packages/core/src/services/evaluation/rewrite-from-evaluation.ts
  - packages/core/src/services/evaluation/structured-compare-prompts.ts
  - packages/core/src/services/prompt/types.ts
  - packages/core/src/services/prompt/service.ts
  - packages/core/src/constants/storage-keys.ts
  - packages/mcp-server/src/adapters/language-service.ts
  - packages/mcp-server/src/adapters/core-services.ts
  - packages/ui/src/services/ImageStyleExtractor.ts
  - packages/core/tests/unit/template/processor.test.ts
  - packages/core/tests/unit/template/builtin-template-id-consistency.test.ts
depends: []
status: ready
reimplementation: 미실행
---

# 템플릿 렌더링 규칙

> `Template`(문자열 또는 메시지 배열 + 메타데이터)과 변수 맥락(context)을 받아 LLM에 보낼 `Message[]`로 바꾸고, 템플릿을 ID·유형·언어로 찾는 공유 계약.

경로 표기: 모든 `파일:줄`은 `repos/prompt-optimizer/` 기준이다. 라이선스는 AGPL-3.0-only(overview 1절)라서 코드는 C-ID(위치)로만 가리키고 템플릿 본문은 옮기지 않는다. 템플릿 본문은 구조만 설명한다.

<!--
작성 메모(삭제하지 않음): 이 스펙은 렌더링 규칙(processTemplate), Template 데이터 모양, 유형·ID 규칙, 내장 등록·언어 선택까지만 다룬다. 사용자 템플릿 저장·가져오기·내보내기(manager.ts 82-139, 173-205, 316-475)와 관리 UI는 제외했다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 호출자(최적화·반복 개선·평가·변수 추출 등 서비스)가 템플릿 ID와 유형(optimize, evaluation 등)으로 `Template` 하나를 정한다. 평가는 ID를 `evaluation-{functionMode}-{subMode}-{type}`로 조립하고, 최적화·반복 개선은 호출자가 준 ID나 기본값(`general-optimize`, `iterate`, 또는 유형별 목록의 첫 번째)을 쓴다. 변수 추출·변수값 생성은 고정 ID를 쓴다.
2. 템플릿 관리자가 ID를 검증하고(소문자·숫자·하이픈 3자 이상), 현재 내장 템플릿 언어(zh-CN/en-US)에 해당하는 내장 집합을 먼저 찾고, 없으면 사용자 템플릿에서 찾는다. 둘 다 없으면 NOT_FOUND 오류다.
3. 호출자가 맥락 객체(`originalPrompt`, `lastOptimizedPrompt`, `iterateInput`, 사용자 변수, 평가용 변수 등)를 만든다. 최적화 경로는 사용자 변수를 맥락 최상위로 펼친다(미리 정한 키 우선).
4. `processTemplate`가 템플릿 내용을 검증한다(비어 있으면 검증 오류).
5. 내용이 문자열이면 `[system=템플릿 그대로]`에 `originalPrompt`가 있을 때만 `user=originalPrompt 그대로`를 붙인다. 치환은 하지 않는다.
6. 내용이 배열이면 각 메시지의 `content`를 Mustache로 렌더링하고 `role`·`content`만 남긴 `Message[]`를 돌려준다. 렌더링 맥락에 `helpers.toJson`(값을 JSON 문자열로 감싸는 람다)이 항상 들어간다.
7. 호출자가 `Message[]`를 LLM에 보낸다(이 스펙 밖).

### 1.2 범위·통합 지점 [필수]
- 제공: `Template`·`MessageTemplate`·`TemplateMetadata` 데이터 모양, `TemplateProcessor.processTemplate` 렌더링 규칙, 맥락 확장·보조 포맷 함수, 템플릿 유형 목록, 내장 템플릿 ID 명명 규칙(평가 ID 조립 규칙 포함), 내장 템플릿 등록 방식(`ALL_TEMPLATES`)과 언어별 선택, 템플릿 조회(`getTemplate`·`listTemplatesByType`)의 의미.
- 제외:
  - 사용자 템플릿 저장·삭제·가져오기·내보내기와 템플릿 관리 UI(범위 승인에서 제외).
  - 개별 템플릿 본문 전부. 대표 3개(`general-optimize`, `iterate`, 평가 템플릿 빌더)만 구조 확인.
  - 최적화·평가 서비스 흐름과 평가 맥락의 전체 키 목록(별도 스펙). 평가 맥락 키 표는 [llm-evaluation](./llm-evaluation.md) 1.3과 그 C-08(`evaluation/service.ts:594-640` 등)에 있다. 기본 템플릿 선택은 [prompt-optimize](./prompt-optimize.md) R-04~R-07, 반복 개선·평가 기반 재작성은 [iterate-rewrite](./iterate-rewrite.md) R-03·R-21·R-24가 맡는다(모두 이 스펙을 선행으로 쓰는 쪽이라 `depends`에는 넣지 않는다).
  - 이미지 모드(참조 이미지 템플릿 `image-prompt-from-reference-image`·`image-prompt-migration`의 호출 서비스 포함, R-21): 승인 범위 밖이라 따라가지 않았다.
- 외부 의존·선행 계약:
  - Mustache 엔진(`mustache` ^4.2.0, `packages/core/package.json`). 이 문서는 엔진 내부를 읽지 않았다(1.4 확인 한계).
  - 설정 저장소(`IPreferenceService`)와 저장소(`IStorageProvider`). 템플릿 관리자는 이 둘을 주입받는다. 이 스펙에서는 "언어 문자열을 돌려주는 서비스"와 "사용자 템플릿 JSON 문자열을 읽는 저장소"로만 쓴다.
  - 선행 스펙: 없음.
- 소유 상태·부작용:
  - `StaticLoader`의 정적 캐시(프로세스 수명, `loadTemplates` 첫 호출에 채움).
  - 언어 서비스의 현재 언어와 설정 키 `app:settings:ui:builtin-template-language`.
  - `processTemplate`는 입력 템플릿·맥락을 바꾸지 않는다(새 배열·새 객체를 만든다).

### 1.3 인터페이스와 데이터 의미 [필수]
| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `Template` | `id: string`, `name: string`, `content: string \| MessageTemplate[]`, `metadata: TemplateMetadata`, `isBuiltin?: bool` | 문자열은 "system 프롬프트 하나", 배열은 "메시지 틀 목록". 스키마상 문자열은 길이 1 이상, 배열은 원소 1개 이상이고 각 `content`도 길이 1 이상(C-05). 스키마 검증은 저장·가져오기 때만 돈다. |
| `MessageTemplate` | `role: 'system'\|'user'\|'assistant'\|'tool'`, `content: string`, `name?`, `tool_calls?`, `tool_call_id?` | 스키마는 `role`·`content`만 검증한다. 렌더링 결과에는 `role`·`content`만 복사되고 `name`·`tool_calls`·`tool_call_id`는 버려진다. |
| `TemplateMetadata` | `version: string`, `lastModified: number(ms)`, `templateType: 16종 중 하나`, `language?: 'zh'\|'en'`, `author?`, `description?`, 임의 추가 필드 | `language`는 내장 템플릿에서 필수(static loader가 없으면 로딩 실패). 추가 필드는 통과(passthrough). |
| `TemplateType`(= `templateType`) | `optimize`, `userOptimize`, `text2imageOptimize`, `image2imageOptimize`, `multiimageOptimize`, `imageIterate`, `iterate`, `conversationMessageOptimize`, `contextUserOptimize`, `contextIterate`, `contextSystemOptimize`, `evaluation`, `variable-extraction`, `variable-value-generation`, `image-prompt-composition`, `image-prompt-migration` | 유형은 조회 필터(`listTemplatesByType`)와 기본 템플릿 선택에만 쓰인다. 렌더링 규칙은 유형을 보지 않는다. |
| `TemplateContext` | `map<string, any>` + 알려진 키: `originalPrompt`, `iterateInput`, `lastOptimizedPrompt`, `optimizationMode('system'\|'user')`, `contextMode`, `customVariables(map<string,string>)`, `tools`, `conversationContext`, `toolsContext`, `messageRole`, `conversationMessages`, `selectedMessage` | 임의 키를 허용한다. 호출자마다 채우는 키가 다르다(R-12). |
| `processTemplate(template, context)` | → `Message[]` | 동기 함수. 검증 실패·형식 오류는 `TemplateValidationError`를 던진다. |
| `createExtendedContext(base, customVariables?, conversationMessages?)` | → `TemplateContext` | `base`를 얕게 복사하고 `customVariables`, `conversationMessages` 키를 넣은 뒤, 사용자 변수 각각을 최상위 키로 펼친다. 단 `base`에 같은 키가 `undefined`가 아닌 값으로 있으면 `base` 쪽이 이긴다. |
| `formatConversationAsText(messages)` | `ConversationMessage[]` → string | 각 줄 `ROLE: content`(role 대문자)를 빈 줄 하나(`\n\n`)로 연결. 비면 빈 문자열. |
| `formatToolsAsText(tools)` | `ToolDefinition[]` → string | 도구마다 `Tool name: …` + 선택적 `Description: …` + 선택적 `Parameters: <들여쓰기 2칸 JSON>`을 줄바꿈으로 잇고 도구 사이는 빈 줄. 비면 빈 문자열. |
| `processConversationMessages(messages, variables)` | `ConversationMessage[]`, `map<string,string>` → `Message[]` | 각 메시지 `content`를 Mustache로 렌더링(`helpers` 없음). 이 스펙에서는 보조 함수로만 다룬다. |
| `getTemplate(id)` | string → `Template` | ID 검증 → 내장(현재 언어) → 사용자 순으로 조회. 못 찾으면 `TemplateError(error.template.not_found)`. |
| `listTemplates()` | → `Template[]` | 내장(현재 언어 집합, 삽입 순서) 뒤에 사용자 템플릿(`lastModified` 내림차순). |
| `listTemplatesByType(type)` | → `Template[]` | `listTemplates` 결과를 `metadata.templateType === type`으로 거른다. 내부 오류는 삼키고 `[]`을 돌려준다. |
| 언어 설정 | `getCurrentBuiltinTemplateLanguage()`, `changeBuiltinTemplateLanguage(lang)`, `getSupportedBuiltinTemplateLanguages()` | 값은 `'zh-CN'`, `'en-US'` 두 가지. 설정 키 `app:settings:ui:builtin-template-language`. |
| 평가 템플릿 ID | `evaluation-{functionMode}-{subMode}-{type}` | `functionMode ∈ {basic, pro, image}`, `subMode`는 basic이면 `system\|user`, pro면 `multi\|variable`, image면 `text2image\|image2image\|multiimage`, `type ∈ {result, compare, prompt-only, prompt-iterate}`. |

### 1.4 행동 규칙과 남은 질문 [필수]
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `template.content`가 falsy(빈 문자열·undefined)이거나 배열 길이 0 | `TemplateValidationError`. 메시지에 템플릿 ID가 들어간다(ID 없으면 "unknown"). 렌더링은 하지 않는다. | 코드 확인 |
| R-02 | `content`가 문자열 | 결과 `[{system, content 그대로}]`. 템플릿 안의 `{{…}}`는 치환하지 않는다. `context.originalPrompt`가 truthy일 때만 `{user, originalPrompt 그대로}`가 뒤에 붙는다(빈 문자열이면 user 메시지 없음). `iterateInput` 등 다른 키는 쓰지 않는다. | 코드 확인 |
| R-03 | `content`가 배열 | 원소마다 `Mustache.render(content, renderContext)`로 `content`만 렌더링하고 `{role, content}`만 가진 새 객체를 만든다. 순서와 개수는 템플릿 그대로다. 빈 문자열이 되는 메시지도 걸러내지 않는다. `name`·`tool_calls`·`tool_call_id`는 결과에 없다. | 코드 확인 |
| R-04 | `content`가 문자열도 배열도 아님(예: 객체) | `TemplateValidationError("Invalid template content format …")`. | 코드 확인 |
| R-05 | 배열 렌더링의 맥락 | `renderContext = {...context, helpers: {toJson}}`. `context.helpers`가 있어도 내장 `helpers`가 덮어쓴다. `toJson`은 `{{#helpers.toJson}}…{{/helpers.toJson}}` 안의 텍스트를 먼저 렌더링한 뒤 `JSON.stringify`한 문자열(따옴표 포함)이다. | 코드 확인(맥락 조립·람다 정의·템플릿 사용 패턴·원본 테스트 기대값) / 엔진 내부의 람다 호출 방식은 확인 한계 |
| R-06 | 값 안에 `{{…}}`가 있는 변수(예: 사용자 프롬프트 `"…{{item}}…"`) | 값은 한 번만 삽입되고 다시 렌더링되지 않는다. 변수 플레이스홀더가 그대로 출력에 남는다. 템플릿 본문이 자기 `{{`를 글자 그대로 출력해야 할 때는 Mustache 구분자 변경(`{{=<% %>=}}` … `<%={{ }}=%>`)을 쓴다. | 코드 확인(주석·템플릿 사용·원본 테스트 사례) / 엔진 내부 동작은 확인 한계 |
| R-07 | 이스케이프 | 엔진의 이스케이프 함수를 바꾸는 코드는 없다. 내장 템플릿은 원문을 넣을 때 `{{{x}}}`(이스케이프 없음)를 쓰고, JSON 안에 넣을 때는 `{{#helpers.toJson}}{{{x}}}{{/helpers.toJson}}`를 쓴다. `{{x}}`(이중 중괄호)는 엔진 기본값(HTML 이스케이프)을 그대로 쓴다. 같은 라이브러리를 쓰면 결과가 같고, 다른 엔진이면 "구현 시 맞출 계약"(아래)을 따른다. | 코드 확인(엔진 이스케이프 미변경·템플릿 사용 패턴) / 기본 이스케이프 문자 집합은 확인 한계 |
| R-08 | `createExtendedContext` | 위 1.3 표의 병합 규칙. 최적화 경로만 이 함수를 쓰고(`prompt/service.ts:909-959`), 반복 개선 경로는 맥락을 직접 만들어 사용자 변수를 `customVariables` 키에만 넣고 최상위로 펼치지 않는다. | 코드 확인 |
| R-09 | 반복 개선(`iteratePrompt`)에서 템플릿 `content`가 문자열 | `processTemplate` 이전에 호출자가 `IterationError`로 거절한다("배열 템플릿이 필요"). 렌더링 자체는 문자열 템플릿도 받는다. | 코드 확인 |
| R-10 | 템플릿 ID 검증(조회·저장·가져오기 공통) | `null`/빈 값 → "Invalid template ID", 정규식 `^[a-z0-9-]{3,}$` 불일치 → 형식 오류, 둘 다 `TemplateValidationError`. 내장 ID는 모두 이 형식을 따른다(소문자·숫자·하이픈, 원본 테스트가 같은 취지를 검사). | 코드 확인 |
| R-11 | 내장 템플릿 등록 | 내장 템플릿은 `default-templates/index.ts`의 `ALL_TEMPLATES`(객체, 120개 항목 = 중국어 60 + 영어 60)에 가져오기(import)로 하나씩 등록한다. 각 템플릿은 자기 `id`·`name`·`content`·`metadata(templateType, language 'zh'\|'en')`·`isBuiltin: true`를 가진다. 로더는 이 객체의 값 전체를 훑어 `language`별로 나눠 캐시한다. `isBuiltin`이 아니거나 `language`가 없는 템플릿은 언어별 집합에 들어가지 않는다. 내장인데 `language`가 없으면 로딩 전체가 `TemplateLoadError`로 실패한다. | 코드 확인 |
| R-12 | ID 공유와 `-en` 접미 | 같은 템플릿의 중·영 버전은 보통 **같은 ID**를 갖고(예: `general-optimize`, `iterate`, `evaluation-basic-system-result`), 현재 언어에 따라 내용이 바뀐다. 예외로 ID에 `-en`이 붙는 묶음이 있다: 문맥(context) 계열 일부(`context-analytical-optimize-en` 등), 이미지 최적화(`image-general-optimize-en` 등), 구조화 비교(`evaluation-structured-compare-*-en`). 이들은 중·영이 서로 다른 ID다. | 코드 확인 |
| R-13 | 현재 언어 → 내장 집합 | `en-US` → 영어 집합, `zh-CN` → 중국어 집합, 그 밖의 값 → 경고 후 영어 집합. `StaticLoader.mapLanguage`는 `zh-CN`/`zh` → `zh`, `en-US`/`en` → `en`, 모르는 값 → 경고 후 `zh`(관리자 경로에서는 위 규칙이 먼저라 도달하지 않음). | 코드 확인 |
| R-14 | 언어 서비스 초기값 | 기본 `en-US`. `initialize`는 저장된 설정 값이 유효하면 쓰고, 아니면 브라우저 `navigator.language`가 `zh`로 시작할 때 `zh-CN`, 그 밖에는 `en-US`로 정한 뒤 설정에 저장한다. `navigator`가 없는 환경은 `en-US`. 초기화 중 예외가 나면 `en-US`로 두고 초기화 완료로 처리한다. `setLanguage`는 지원 목록 밖이면 `TemplateValidationError`. | 코드 확인 |
| R-15 | MCP 서버의 언어 | MCP 서버는 설정 저장 없이 메모리에서만 동작하는 별도 언어 서비스를 쓴다. 기본값은 설정 `defaultLanguage` → 환경변수 `MCP_DEFAULT_LANGUAGE` → `en-US` 순이고, `zh`/`zh-CN`/`chinese`는 `zh-CN`, 나머지 알려진 값과 모르는 값은 `en-US`. | 코드 확인 |
| R-16 | `getTemplate` 조회 순서 | 내장(현재 언어) 먼저, 사용자 템플릿 나중. 같은 ID가 둘 다 있어도 내장이 이긴다. 못 찾으면 NOT_FOUND. 언어를 바꾸면 같은 ID의 내장 내용이 바뀐다. | 코드 확인 |
| R-17 | `listTemplates` 순서 | 내장 → 사용자 순. 내장끼리는 `ALL_TEMPLATES` 선언 순서(정렬 비교가 0이라 안정 정렬에서 그대로)다. 결과적으로 영어 기준 유형별 첫 템플릿은 `optimize`=`general-optimize`, `userOptimize`=`user-prompt-professional`, `iterate`=`iterate`다. **기본 템플릿 선택(확정)**: 최적화 호출에 `templateId`가 없으면(빈 문자열 포함) 서비스가 유형(`optimizationMode==='user'`면 `userOptimize`, 아니면 `optimize`)의 `listTemplatesByType` **첫 번째** ID를 쓴다(시스템 모드 `general-optimize`, 사용자 모드 `user-prompt-professional`; 목록이 비면 서비스의 폴백 체인). 상수 `DEFAULT_TEMPLATES`(`prompt/service.ts:27-31`)는 `ITERATE`(`iterate`)만 비스트리밍 `iteratePrompt`가 `templateId` 없을 때 읽고(`:303`), `OPTIMIZE`·`TEST`는 코드 어디에서도 읽지 않는다. 스트리밍 반복 개선은 `templateId`가 필수 인자다. 자세한 호출처별 규칙은 [prompt-optimize](./prompt-optimize.md) R-04~R-07, [iterate-rewrite](./iterate-rewrite.md) R-03. | 코드 확인(선언 순서·상수 사용처 검색) / 순서 보존은 JS 객체·정렬 의미에 의존해 추론 |
| R-18 | 평가 템플릿 조회 | `evaluationService`는 `evaluation-{mode.functionMode}-{mode.subMode}-{type}`을 문자열로 조립해 `getTemplate`을 부른다. 템플릿이 없거나 `content`가 비면 `EvaluationTemplateError(templateId)`로 감싼다. 서로 어울리지 않는 조합은 사전 검증 없이 이 조회 실패로만 드러난다. | 코드 확인 |
| R-19 | 내장 평가 템플릿 집합 | 4종 `type`(result, compare, prompt-only, prompt-iterate) × basic(system, user), pro(multi, variable)의 16개 ID가 모두 있다. image는 text2image가 4종, image2image·multiimage는 `prompt-only`만 있다(총 22 ID × 2 언어 = 44 항목). 내용은 `[system, user]` 두 메시지 배열이며 `templateType: 'evaluation'`이다(빌더로 만든 것과 image/text2image result·compare 직접 정의 2건은 확인, 나머지 image 템플릿 파일은 빌더 사용을 파일 이름·import로만 추정). | 코드 확인(등록 목록·ID·빌더·샘플 2건) / 나머지는 추론 |
| R-20 | 평가 외 `evaluation` 유형 템플릿 | 평가 ID 규칙을 따르지 않는 `templateType: 'evaluation'` 템플릿이 더 있다: 평가 기반 재작성 `evaluation-rewrite-{basic-system, basic-user, pro-multi, pro-variable, generic}`, 구조화 비교 `evaluation-structured-compare-{pair-judge, synthesis}`(영어는 `-en`). 이들은 `TemplateManager`를 거치지 않고 서비스가 모듈에서 템플릿 객체를 직접 가져온다(사용자 템플릿으로 바꿀 수 없다). 언어 선택은 둘이 다르다. **재작성**: `language`는 호출자 인자이고(`'en'`이면 영어판, 그 밖에는 중국어판), 코어에서 생략하면 `'zh'`다(`rewrite-from-evaluation.ts:292`). UI는 UI 로케일에서 `normalizeRewriteLocaleLanguage`(소문자 로케일이 `en`으로 시작하면 `'en'`, 그 밖과 미지정은 `'zh'`, `:285-287`)로 구해 넘기며 내장 템플릿 언어 설정과 독립이다([iterate-rewrite](./iterate-rewrite.md) R-24). **구조화 비교**: 평가 서비스가 `getCurrentBuiltinTemplateLanguage()`가 `en-US`이면 영어판, 아니면(조회 실패 포함) 중국어판으로 고른다(`evaluation/service.ts:2312-2319`). 평가 맥락 키는 [llm-evaluation](./llm-evaluation.md) 1.3·C-08을 따른다. 재작성은 `functionMode`·`subMode`로 템플릿을 고르고 해당 없으면 `generic`을 쓴다. 재작성 결과는 메시지를 `trim` 후 빈 줄로 이어 문자열 하나로 만든다. | 코드 확인 |
| R-21 | 변수 추출·변수값 생성 등 고정 ID | `variable-extraction`, `variable-value-generation`은 서비스 코드에 ID가 박혀 있고 `TemplateManager.getTemplate`로 조회한다. 참조 이미지용 `image-prompt-from-reference-image`·`image-prompt-migration`도 `templateType`이 있는 내장 템플릿이며, 호출 서비스는 이미지 모드(`ui/src/services/ImageStyleExtractor.ts:38-39`, `:108-112`)라 승인 범위 밖이다. | 코드 확인(ID 고정, 등록, 호출 ID 상수 위치) |
| R-22 | 내장 템플릿 구조 | 대표 확인: `general-optimize`(optimize 유형)는 **문자열** 내용이라 R-02대로 system으로 가고 사용자 프롬프트는 user로 따로 간다. `iterate`(iterate 유형)와 모든 평가 템플릿은 **배열**이며 변수 자리(`{{{lastOptimizedPrompt}}}` 등)를 `helpers.toJson`으로 감싸 JSON 증거 블록을 만든다. 평가 템플릿은 `content.ts`의 빌더 함수가 언어·대상 라벨(subject)을 받아 문자열을 조립한다. | 코드 확인(대표 3건) |
| R-23 | 유형 정규화 불일치 | `StaticLoader`의 `byType` 색인은 camelCase `templateType`을 kebab-case(`user-optimize`, `context-iterate` 등)로 바꿔 쌓지만, 관리자는 이 색인을 쓰지 않고 `metadata.templateType`을 직접 비교한다. 로더의 타입 목록은 `contextSystemOptimize`·`variable-extraction`·`variable-value-generation`을 따로 갖지 않아 `optimize` 칸으로 떨어진다. 외부로 관찰되는 결과는 없다. | 코드 확인 |

- 불변식: 같은 `Template`·같은 `context`에서 `processTemplate`는 같은 `Message[]`를 돌려준다(전제: 시계·난수·I/O 없음, 맥락 값이 같음). 문자열 템플릿은 `{{…}}`를 치환하지 않는다. 결과 메시지에는 `role`·`content`만 있다.
- 구현 시 맞출 계약(렌더러를 바꿀 때): 다음을 모두 지원해야 내장 템플릿 구조가 같은 결과를 낸다.
  1. `{{x}}`·`{{{x}}}`(원문 삽입)·섹션 `{{#a}}…{{/a}}`·반전 섹션 `{{^a}}…{{/a}}`·점 표기 조회(`helpers.toJson`). `{{x}}`는 엔진 기본 HTML 이스케이프를 켠 채로 쓰이고, 원문이 필요한 곳은 `{{{x}}}`로 구분돼 있다.
  2. 함수 값 필드: `helpers.toJson`은 인자 없이 불리면 `(text, render)` 람다를 돌려주는 함수다. 엔진은 섹션 `{{#helpers.toJson}}…{{/helpers.toJson}}`에서 필드가 함수면 호출해 그 결과 람다에 섹션 본문 원문과 `render`를 넘기고, 람다가 돌려준 문자열을 출력에 그대로 넣어야 한다(`toJson`: 본문 렌더링 → `JSON.stringify`).
  3. 구분자 변경 태그 `{{=<% %>=}}` … `<%={{ }}=%>`: 템플릿이 자기 본문에 `{{변수}}`를 글자 그대로 쓸 때 쓴다(`iterate_en.ts:24-25`, `:55`).
  4. 삽입한 값은 다시 렌더링하지 않는다(값 속 `{{…}}`는 그대로 남는다). 없는 변수·`null`·`false`·빈 배열은 섹션이 렌더링되지 않고 반전 섹션이 렌더링되며, 없는 변수 삽입은 빈 문자열이다.
  같은 라이브러리(`mustache` ^4.2.0)를 쓰면 이 동작이 이미 정해져 있다.
- 범위 밖: R-21의 참조 이미지 템플릿 2종 호출 서비스(이미지 모드는 범위 승인에서 제외).
- 미결정: 없음
- 확인 한계: 설치·빌드·실행 없이 소스만 읽었다. `mustache` 패키지 소스(`node_modules` 없음)와 테스트 실행 결과는 보지 않았다. 따라서 R-05·R-07의 "구현 시 맞출 계약" 1~4는 내장 템플릿의 사용 패턴과 원본 테스트 기대값(`processor.test.ts:77-140`, 미실행)에서 도출한 것이고, 라이브러리가 그것을 실제로 어떻게 처리하는지(람다 호출 내부, `{{x}}` 이스케이프 문자 집합, 없는 변수 처리)는 확인하지 못했다. 원본 테스트는 사례만 읽었고 통과 여부는 모른다. 템플릿 본문은 대표 3건만 읽었다. 내장 템플릿 항목 수(120)와 유형별 분포는 `ALL_TEMPLATES` 등록 목록·파일 이름·`templateType` 검색으로 세었고 파일 내용을 전부 열지는 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스: AGPL-3.0-only(overview 1절). 아래는 복사본이 아니라 위치다. 재구현자는 해당 범위를 읽고 직접 구현한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/core/src/services/template/processor.ts:49-76` `processTemplate`, `validateTemplate` | 검증 후 `buildMessages` 호출. 검증 조건과 오류 종류 | R-01 |
| C-02 | `packages/core/src/services/template/processor.ts:81-125` `buildMessages` | 문자열/배열/그 외 분기, `originalPrompt` truthy 조건, `role`·`content`만 복사 | R-02, R-03, R-04, R-06 |
| C-03 | `packages/core/src/services/template/processor.ts:138-177` `createExtendedContext`, `createRenderContext`, `createBuiltInHelpers` | 사용자 변수 병합(미리 정한 키 우선), `helpers` 덮어쓰기, `toJson` 람다 | R-05, R-08 |
| C-04 | `packages/core/src/services/template/processor.ts:183-243` `formatConversationAsText`, `processConversationMessages`, `formatToolsAsText` | 대화·도구 텍스트 포맷(구분자·접두어) | 1.3 표 |
| C-05 | `packages/core/src/services/template/types.ts:9-62`, `:124-165` `TemplateMetadata`, `MessageTemplate`, `Template`, `templateSchema` | 데이터 모양, 16종 `templateType`, 스키마 제약 | R-10, 1.3 |
| C-06 | `packages/core/src/services/template/manager.ts:41-76` `validateTemplateId`, `getTemplate` | ID 정규식, 내장 우선 조회, NOT_FOUND | R-10, R-16 |
| C-07 | `packages/core/src/services/template/manager.ts:145-171`, `:210-224`, `:268-293` `listTemplates`, `getBuiltinTemplates`, `getTemplateSet`, `listTemplatesByType` | 정렬, 내장 표시, 언어→집합, 유형 필터 | R-13, R-16, R-17 |
| C-08 | `packages/core/src/services/template/languageService.ts:28-100` `TemplateLanguageService` | 지원 언어, 기본값, 초기화 순서, 언어 설정 | R-14 |
| C-09 | `packages/core/src/services/template/static-loader.ts:48-60`, `:65-158` `mapLanguage`, `loadTemplates` | 언어 매핑, `language` 필수, 캐시 | R-11, R-13, R-23 |
| C-10 | `packages/core/src/services/template/default-templates/index.ts:156-292` `ALL_TEMPLATES` | 등록 목록과 선언 순서 | R-11, R-17, R-19 |
| C-11 | `packages/core/src/services/evaluation/service.ts:567-589` `getEvaluationTemplate`, `getTemplateId` | 평가 ID 조립, 조회 실패 변환 | R-18 |
| C-12 | `packages/core/src/services/evaluation/types.ts:14-34`, `:527-547`; `packages/core/src/services/prompt/types.ts:62-75` | `EvaluationType`, `functionMode`·`subMode` 값, ID 형식 주석(목록 16개) | R-18, R-19 |
| C-13 | `packages/core/src/services/template/default-templates/evaluation/builders.ts:45-104` `createAnalysisTemplate`, `createResultTemplate`, `createCompareTemplate` | 평가 템플릿이 `[system, user]` 배열이고 `templateType: 'evaluation'`, `isBuiltin: true`로 만들어짐 | R-19, R-22 |
| C-14 | `packages/core/src/services/prompt/service.ts:909-959` `resolveOptimizationMessages` | 최적화 경로의 맥락 키와 `createExtendedContext` 사용 | R-08 |
| C-15 | `packages/core/src/services/prompt/service.ts:296-352` `iteratePrompt` 일부 | 반복 개선의 맥락 구성(변수를 `customVariables`에만), 문자열 템플릿 거절 | R-08, R-09 |
| C-16 | `packages/core/src/services/evaluation/service.ts:594-640` `buildTemplateContext` | 평가 맥락(요청 변수 최상위 펼침, `hasFocus`·`focusBrief`·`hasUserFeedback`·`userFeedback`, type별 키) | R-12 영역(평가 호출자의 맥락) |
| C-17 | `packages/core/src/services/evaluation/rewrite-from-evaluation.ts:260-283`, `:429-437` `resolveRewriteTemplate`, `buildRewritePromptFromEvaluation`; `structured-compare-prompts.ts:140-185` | 관리자를 거치지 않는 직접 import와 언어 선택, 메시지 연결 | R-20 |
| C-18 | `packages/mcp-server/src/adapters/language-service.ts:1-60`; `core-services.ts:270-272` | MCP 기본 언어 해석 | R-15 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출이며, T-01·T-03·T-05·T-06은 같은 사례를 원본 테스트(`packages/core/tests/unit/template/processor.test.ts`)에서도 열람했다(실행은 하지 않았으므로 실행 확인 아님).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | 문자열 템플릿 `"S"`, 맥락 `{originalPrompt: "P"}` | `[{system,"S"},{user,"P"}]` |
| T-02 | R-02 | 같은 템플릿, 맥락 `{}` 또는 `{originalPrompt: ""}` | `[{system,"S"}]` (user 없음) |
| T-03 | R-02, R-06 | 문자열 템플릿 `"A {{originalPrompt}}"`, 맥락 `{originalPrompt: "P"}` | system 내용은 `"A {{originalPrompt}}"` 그대로, user는 `"P"` |
| T-04 | R-03 | 배열 템플릿 `[{user, "X {{{originalPrompt}}} Y"}]`, 맥락 `{originalPrompt: "a<b"}` | `[{user, "X a<b Y"}]` |
| T-05 | R-05, R-06 | 배열 템플릿 `[{user, '{"p": {{#helpers.toJson}}{{{originalPrompt}}}{{/helpers.toJson}}}'}]`, `originalPrompt = 줄바꿈·큰따옴표·`<xml>{{item}}</xml>` 포함 문자열` | `p` 값이 JSON 문자열로 이스케이프되고(`\n`, `\"`), `<xml>`·`{{item}}`은 그대로 남는다 |
| T-06 | R-05 | T-05와 같은 구조에서 맥락에 `helpers: {toJson: "not-a-function"}`를 넣음 | 내장 `helpers.toJson`이 쓰이고 결과는 `"override-check"` 같은 정상 JSON 문자열 |
| T-07 | R-01 | `content: ""` 또는 `content: []` | `TemplateValidationError`(메시지에 템플릿 ID) |
| T-08 | R-03 | 배열 템플릿 메시지에 `name: "n"`, `tool_calls` 포함 | 결과 객체에는 `role`·`content`만 있음 |
| T-09 | R-08 | `base = {originalPrompt: "a"}`, `customVariables = {originalPrompt: "b", x: "1"}` | 결과 `originalPrompt = "a"`, `x = "1"`, `customVariables`도 그대로 포함 |
| T-10 | R-18 | 평가 `type: 'prompt-iterate'`, `mode: {functionMode:'basic', subMode:'system'}` / `{pro, variable}` + `result` / `{image, text2image}` + `compare` | ID `evaluation-basic-system-prompt-iterate`, `evaluation-pro-variable-result`, `evaluation-image-text2image-compare`, 각각 조회 성공 |
| T-11 | R-18, R-19 | 평가 `type: 'compare'`, `mode: {image, image2image}` | ID `evaluation-image-image2image-compare`는 등록되지 않아 `EvaluationTemplateError` |
| T-12 | R-10, R-16 | `getTemplate("AB")`, `getTemplate("Has_Upper")`, `getTemplate("no-such-template")` | 앞의 둘은 형식 오류(`TemplateValidationError`), 셋째는 NOT_FOUND(`TemplateError`) |
| T-13 | R-13, R-16 | 언어 `en-US`에서 `getTemplate("iterate")`, 그다음 `zh-CN`으로 바꿔 다시 호출 | 같은 ID, 각각 `metadata.language`가 `en`, `zh`인 서로 다른 내용 |
| T-14 | R-17 | 언어 `en-US`, `listTemplatesByType` 호출 | `optimize`의 첫 항목 `general-optimize`, `userOptimize`의 첫 항목 `user-prompt-professional`, `iterate`의 첫 항목 `iterate` |
| T-15 | R-14 | 설정에 값 없음, `navigator.language = "zh-TW"` / `"ko"` / `navigator` 없음 | 각각 `zh-CN`, `en-US`, `en-US`, 그리고 설정 키에 저장됨 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 (`processor.ts:63-76`) | 코드 읽음 |
| R-02 | C-02 (`processor.ts:85-97`); 테스트 `processor.test.ts:7-35` | 코드 읽음, 테스트 사례는 열람만 |
| R-03 | C-02 (`processor.ts:99-120`) | 코드 읽음. 메시지 필드가 `role`·`content`로 한정되는 것은 반환 객체 리터럴(`:115-118`)에서 확인 |
| R-04 | C-02 (`processor.ts:122-124`) | 코드 읽음 |
| R-05 | C-03 (`processor.ts:163-177`); 테스트 `processor.test.ts:77-140` | 맥락 조립은 코드로 확인. `helpers.toJson`이 `(text, render)` 람다를 반환하는 구조에서 엔진이 이를 섹션 람다로 부르는 내부 동작은 확인 한계(원본 테스트 기대값으로만 뒷받침) |
| R-06 | `processor.ts:104-112` 주석, 테스트 `processor.test.ts:77-104` 기대값, `iterate/iterate_en.ts:24-25,55`(구분자 변경 사용) | 템플릿·주석은 읽음. "값은 재렌더링되지 않음"은 엔진 동작이라 테스트 기대값(미실행)에 의존, 엔진 내부는 확인 한계 |
| R-07 | `grep`으로 `Mustache.escape` 등 이스케이프 변경 코드가 `core/src`, `ui/src`에 없음을 확인(검색 결과 없음). `evaluation/content.ts:168-174`, `optimize/context/context-analytical-optimize_en.ts:136-156`의 `{{{…}}}` 사용 | 검색+샘플 읽음. 이중 중괄호 이스케이프 문자 집합은 엔진 기본값이며 확인 한계 |
| R-08 | C-03, C-14, C-15 | 호출자 두 곳 비교. 반복 개선은 `prompt/service.ts:339-345`에서 `customVariables: contextData?.variables`만 넣음 |
| R-09 | C-15 (`prompt/service.ts:325-337`; 스트리밍 경로 `:774` 근처에 같은 오류 문구) | 코드 읽음(비스트리밍 경로). 스트리밍 경로는 문구 존재만 확인 |
| R-10 | C-06 (`manager.ts:41-51`); `tests/unit/template/builtin-template-id-consistency.test.ts:9,37-44` | 코드 읽음. 테스트는 열람만 |
| R-11 | C-09 (`static-loader.ts:92-156`), C-10 (`index.ts:156-292`), `general-optimize_en.ts:68-77`(메타·`isBuiltin`) | 등록 항목 수(120, 그중 `_en`·`En` 접미 60)는 `index.ts` 157-291 행을 세어 도출 |
| R-12 | `default-templates/` 전체에서 `id:` 검색. 같은 ID: 예 `iterate/iterate.ts`·`iterate/iterate_en.ts`(둘 다 `iterate`). `-en` 접미 ID: `optimize/context/context-*-optimize_en.ts`, `image-optimize/**/*_en.ts`, `evaluation-structured-compare/*_en.ts` | 검색 결과로 확인. 전 파일을 열지는 않음 |
| R-13 | C-07 (`manager.ts:268-278`), C-09 (`static-loader.ts:48-60`) | 코드 읽음 |
| R-14 | C-08 (`languageService.ts:43-72`) | 코드 읽음. 브라우저 환경 실행은 하지 않음 |
| R-15 | C-18 (`language-service.ts:11-23`, `core-services.ts:270-272`) | 코드 읽음 |
| R-16 | C-06 (`manager.ts:58-76`), C-07 (`:210-224`) | 코드 읽음 |
| R-17 | C-07 (`manager.ts:145-171`), C-10 (`index.ts:156-292`) | 선언 순서에서 도출. 정렬 비교가 내장끼리 0을 돌려줘 순서가 유지된다는 전제(JS 정렬 안정성)는 언어 명세 지식. 기본 선택은 `prompt/service.ts:27-31`(상수), `:303`(`ITERATE` 유일한 사용처), `:909-915`·`:994-1010`(목록 첫 번째), `:745-750`(스트리밍 `templateId` 필수)를 직접 확인했고 `packages/*/src` 검색에서 `DEFAULT_TEMPLATES` 참조는 `:27`·`:303`뿐이다. prompt-optimize·iterate-rewrite의 결론과 일치 |
| R-18 | C-11 (`evaluation/service.ts:567-589`) | 코드 읽음 |
| R-19 | C-10(평가 항목), C-12(`evaluation/types.ts:527-547` 주석 16개 ID), C-13; `default-templates/evaluation/image/` 폴더 목록(text2image: result·compare·prompt-only·prompt-iterate 각 zh/en, image2image·multiimage: prompt-only만) | 등록 목록으로 22 ID × 2 = 44 도출. 주석(16개 ID)과 등록 목록이 일치 |
| R-20 | C-17; `evaluation-rewrite/builders.ts:45-60`(메시지 1개 user), `evaluation-structured-compare/builders.ts:25` | 코드 읽음. 재작성 `language` 처리는 `rewrite-from-evaluation.ts:285-287`, `:292`와 `useEvaluationHandler.ts:502`·`:565`(UI 호출), 구조화 비교는 `evaluation/service.ts:2312-2319`. 구조화 비교 템플릿의 메시지 수는 `evaluation-structured-compare/builders.ts:38-55`로 `[system, user]` 확인 |
| R-21 | `variable-extraction/service.ts:121`, `variable-value-generation/service.ts:111`, `index.ts` 128-153, 287-291 | 호출 ID는 코드 확인. 두 이미지 템플릿은 `ImageStyleExtractor.ts:38-39,108-112`에서 `getTemplate`·`processTemplate`로 쓰이는 것만 확인하고 그 이상은 범위 밖 |
| R-22 | `optimize/general-optimize_en.ts:3-77`, `iterate/iterate_en.ts:3-65`, `evaluation/builders.ts:45-104`, `evaluation/basic/system/evaluation-result.ts:1-15` | 대표 3건만 읽음 |
| R-23 | `static-loader.ts:12-26`, `:104-145` | 코드 읽음. 관리자에서 `staticLoader.getTemplatesByType`·`byType` 사용처를 `core/src`·`ui/src`·`mcp-server/src`에서 검색해 없음을 확인 |
| 문서와 구현 차이 | `evaluation/types.ts:547` 주석 "ID는 `getTemplateId()`가 동적으로 만든다"와 구현(`service.ts:587`)은 같다. `static-loader.ts:12` 주석 "9 類"는 실제 타입 목록(13종)과 다르다. `types.ts:60` `TemplateSourceType`('builtin'\|'localStorage')은 `core/src`·`ui/src`·`mcp-server/src` 검색에서 선언 외 사용처가 없었다 | 구현을 사실로 썼다 |
| T-01~T-15 | 구현에서 도출. T-01·T-03·T-05·T-06은 `processor.test.ts`에도 같은 취지의 사례가 있음(열람만) | 모두 미실행 |

### 2.2 코드 읽는 순서 [선택]
1. `template/types.ts` — `Template`, `TemplateType` 16종.
2. `template/processor.ts:49-125` — 렌더링 핵심. 이어서 `:138-177`(맥락·helpers).
3. `template/default-templates/index.ts` — 등록 목록. 한 개를 골라 `optimize/general-optimize_en.ts`(문자열)와 `iterate/iterate_en.ts`(배열)을 비교.
4. `template/static-loader.ts:65-158` → `template/manager.ts:58-76`, `:210-278` → `template/languageService.ts` — 언어별 집합과 조회.
5. `evaluation/service.ts:567-640` — 평가 ID 조립과 평가 맥락. 평가 템플릿 본문은 `default-templates/evaluation/builders.ts`·`content.ts`.
6. 구현 전략: 정적 import로 모든 템플릿을 번들에 넣고 로더가 한 번 분류해 캐시한다(런타임 파일 읽기 없음).

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드를 복사하지 않았다.

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-02, R-09 | 스킬(SKILL.md) 평가·개선 템플릿은 모두 배열(메시지 목록) 형식으로만 쓴다. 문자열 템플릿(원본 규칙: 템플릿=system, 원문=user)은 "전체 프롬프트 개선"용 단순 경로로만 필요할 때 둔다. | 문자열 템플릿은 변수 치환이 없어 평가 입력(스킬 본문·모델 출력·테스트 사례)을 넣을 수 없다. 원본도 반복 개선은 배열만 허용한다. | 문자열 경로 구현은 생략 가능. T-01~T-03은 필요할 때만 |
| R-05, R-06, R-07 | 모든 입력 삽입에 "이스케이프 없음 + JSON 문자열 삽입" 두 가지만 지원하는 렌더러를 쓰고, 이중 중괄호 이스케이프 동작이 생기지 않게 한다(또는 엔진 이스케이프 함수를 항등으로 바꾼다). | SKILL.md는 `<`, `&`, 따옴표, `{{` 같은 글자를 자주 포함한다. 이스케이프가 걸리면 평가 입력이 바뀐다. | `helpers.toJson`과 구분자 변경은 쓰는 템플릿에서만 필요. T-04~T-06 |
| R-10, R-12, R-18 | 평가 템플릿 ID는 이 앱의 UI 모드(basic/pro/image × 하위 모드)에 묶여 있어 그대로 가져오지 않는다. 우리 환경의 평가 종류(예: 단일 결과, 모델 비교, 스킬 본문만)에 맞춰 `eval-{종류}-{언어}` 같은 자체 규칙을 정하거나 ID를 키로 하는 정적 맵만 둔다. 조합 검증은 조회 실패 전에 미리 한다. | 모드 조합이 많고(22 ID), 어울리지 않는 조합이 조회 실패로만 드러난다(R-18). | 조회 인터페이스와 오류 종류가 바뀐다 |
| R-11, R-13, R-14 | 템플릿 저장소·언어 서비스·설정 키 없이, 코드에 정적 등록한 템플릿 맵과 호출 인자로 받은 언어 하나만 둔다. 처음 언어 기본값은 사용자 환경 언어로 정한다. | 단일 사용자 평가 환경에는 저장소 의존과 브라우저 언어 감지가 필요 없다. | R-14, T-13~T-15 생략·단순화 |
| R-11 | 중·영 템플릿 쌍을 둘지는 우리 사용 언어에 따라 정한다. 두 언어를 둘 때는 원본의 `evaluation-template-guardrails.test.ts`처럼 "두 언어에서 변수 집합이 같은지"를 검사하는 테스트를 같이 둔다(원본 테스트 이름만 확인함). | 번역본 하나만 변수 이름이 어긋나는 사고를 막는다. | 검증 테스트 추가 |
| 전체 | 템플릿 본문(프롬프트 문장)은 가져오지 않고 직접 쓴다. 가져올 것은 구조(시스템·사용자 2메시지, JSON 계약 블록, 변수 이름 체계)다. | AGPL-3.0-only라서 본문 복사 부담이 크다. | — |
