---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/assertions/index.ts
  - src/assertions/assertionsResult.ts
  - src/assertions/utils.ts
  - src/assertions/validateAssertions.ts
  - src/assertions/AGENTS.md
  - src/assertions/contains.ts
  - src/assertions/equals.ts
  - src/assertions/regex.ts
  - src/assertions/startsWith.ts
  - src/assertions/json.ts
  - src/assertions/cost.ts
  - src/assertions/latency.ts
  - src/assertions/levenshtein.ts
  - src/assertions/wordCount.ts
  - src/assertions/finishReason.ts
  - src/assertions/perplexity.ts
  - src/assertions/bleu.ts
  - src/assertions/rouge.ts
  - src/assertions/guardrails.ts
  - src/assertions/normalize.ts
  - src/assertions/javascript.ts
  - src/assertions/python.ts
  - src/assertions/ruby.ts
  - src/assertions/scriptBody.ts
  - src/assertions/scriptResultNormalization.ts
  - src/assertions/webhook.ts
  - src/assertions/llmRubric.ts
  - src/assertions/factuality.ts
  - src/assertions/geval.ts
  - src/assertions/similar.ts
  - src/assertions/classifier.ts
  - src/assertions/pi.ts
  - src/assertions/searchRubric.ts
  - src/assertions/agentRubric.ts
  - src/assertions/ragDefaults.ts
  - src/assertions/contextUtils.ts
  - src/matchers/shared.ts
  - src/matchers/rubric.ts
  - src/matchers/llmGrading.ts
  - src/matchers/comparison.ts
  - src/types/index.ts
  - src/evaluator.ts
  - src/util/transform.ts
  - src/util/caseMapping.ts
  - src/util/json.ts
  - src/util/safeMode.ts
  - src/util/invariant.ts
  - src/util/functions/loadFunction.ts
  - src/util/fetch/index.ts
  - src/validation/parseCommaSeparatedValues.ts
  - src/providers/packageParser.ts
  - src/python/pythonUtils.ts
  - site/docs/configuration/expected-outputs/index.md
depends:
  - ./provider-contract.md
  - ./skill-calls-metadata.md
status: ready
reimplementation: 미실행
---

# 어서션 패밀리와 어서션 핸들러 계약

> 테스트 케이스의 `assert` 항목(`type`·`value`·`threshold`·`weight`·`metric`·`transform` …)이 provider 출력 하나를 채점해 `GradingResult`(pass, score, reason, namedScores, componentResults …)를 만들고, 여러 어서션의 결과가 가중 평균·임계값·`metric`·`assert-set`·`assertScoringFunction`으로 한 행의 결과로 모이는 규칙 전체의 뼈대를 정의한다.

경로 표기: 이 문서의 `파일:줄`은 모두 `repos/promptfoo/` 기준이다. 설치·빌드·실행을 하지 않았으므로 `실행 확인`은 없다. 공유 계약 `assertion-contract`는 이 스펙에 합쳤다(별도 파일 없음).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

테스트 1건 × prompt 1열의 응답 하나를 기준으로 쓴다.

1. 평가기가 provider 응답을 받는다. `error`나 null `output`이면 어서션 없이 ERROR 행이 된다(provider-contract R-03). 정상이면 `provider.transform` → `test.options.transform`(별칭 `postprocess`) 순으로 출력을 바꾼 `providerResponse`를 만든다(R-06).
2. 평가기가 `runAssertions({prompt, provider, providerResponse, test, vars, latencyMs, assertScoringFunction, traceId})`를 부른다. `test.assert`는 이미 `defaultTest.assert` 뒤에 테스트 자신의 `assert`를 이은 목록이다(R-23).
3. `runAssertions`가 `assert-set`을 한 단계 펼쳐 어서션마다 `runAssertion`을 부른다(동시 실행 기본 3). `select-best`·`max-score`는 여기서 건너뛴다(R-14, R-49).
4. `runAssertion`이 어서션별 `transform`을 적용하고, `value`를 해석(`file://`·`package:`·Nunjucks)해 `AssertionParams`를 만들고, `type`(`not-` 제거)으로 `ASSERTION_HANDLERS`의 핸들러를 찾아 부른다(R-06~R-10).
5. 핸들러의 `GradingResult`는 `weight`·`metric`과 함께 `AssertionsResult`에 쌓인다. `assert-set`은 자기 `AssertionsResult`로 먼저 집계되어 부모에 어서션 하나처럼 들어간다(R-13~R-18).
6. `AssertionsResult.testResult()`가 가중 평균 `score`, `pass`(실패 어서션이 없을 때 true, 테스트 `threshold`가 있으면 점수로 덮어씀), `namedScores`, 평탄화한 `componentResults`를 만들고, `assertScoringFunction`이 있으면 그 반환으로 덮는다(R-19~R-21).
7. 평가기가 행에 `success`·`score`·`namedScores`·`gradingResult`를 쓴다(R-24). 그 테스트의 모든 열이 끝난 뒤 `select-best` → `max-score`가 열 사이 비교를 해 결과를 병합한다(R-49~R-52).

스킬 평가에서의 대표 흐름: `skill-used`(스킬을 불렀나, 결정적) + `javascript`/`python`(출력 형식·내용을 맞춤 코드로 채점) + `llm-rubric`(모델이 품질 채점)을 한 `assert` 목록에 `weight`·`metric`과 함께 두면, 한 행의 `score`와 항목별 `namedScores`가 위 6단계로 나온다.

### 1.2 범위·통합 지점 [필수]

- 제공: ① 핸들러 계약과 등록부(68키)의 분류, ② `not-` 반전·`weight`·`threshold`(어서션·assert-set·테스트 세 층)·`metric`·`assert-set`·`transform`·`assertScoringFunction`의 집계 규칙, ③ 결정적 계열 대표 규칙과 전체 키 목록, ④ 코드 계열(`javascript`·`python`·`ruby`·`webhook`)의 입력·출력 계약, ⑤ `skill-used` 연결, ⑥ 모델 채점 계열의 호출 경계와 `GradingResult` 형태, ⑦ 열 사이 비교 어서션(`select-best`·`max-score`)의 평가기 쪽 규칙.
- 제외(범위 밖, 존재만 표시):
  - `trace-*`·`trajectory:*` 8개 키(트레이싱 제외 승인). 키 목록에만 있다. `javascript`·`python`·`ruby` 어서션 컨텍스트의 `trace` 필드도 트레이싱이 켜졌을 때만 채워지는 선택 필드로만 취급한다.
  - 레드팀: `promptfoo:redteam:*` 어서션 타입(`handleRedteam`)과 플러그인의 `getAssertions`, `guardrails`의 redteam 특수 집계(R-19에 한 줄).
  - 웹 UI의 어서션 입력 폼과 `human` 타입(UI가 결과에 붙이는 값).
  - 설정 로딩 쪽: `type:value` 문자열 약식 문법, CSV `__expected`, `assertionTemplates`(`src/csv.ts` 등, config-schema 소관).
  - 모델 채점 내부: grader provider 선택(기본 grader 포함)·채점 프롬프트 본문·JSON 파싱·임베딩 계산은 별도 스펙 `model-graded-matchers` 소관이다. 이 스펙은 호출 경계와 반환 형태만 쓴다(R-45~R-48).
  - 스크립트 프로세스 전송(임시 JSON 파일, 프로세스 수명)은 `script-bridges` 소관이다. 이 스펙은 `runPython(경로, 함수, [output, context])`가 JSON 값을 돌려주거나 던진다는 경계만 쓴다.
  - 결정적 계열 중 `xml`·`html`·`sql`·도구 호출 형식·`tool-call-f1`·`gleu`·`meteor`·`bleu`/`rouge` 점수 계산 본문, `is-refusal`의 휴리스틱 목록은 키 목록 수준이다.
  - 결과 저장·프롬프트별 지표 집계(`metrics.namedScores` 등)는 eval-run·eval-records 소관이다.
- 외부 의존·선행 계약: `ProviderResponse`(`output`, `cost`, `latencyMs`, `logProbs`, `metadata`, `finishReason`, `guardrails`, `isRefusal`)는 [provider-contract](./provider-contract.md)(R-03~R-06)를 따른다. `skill-used`의 소비 규칙은 [skill-calls-metadata](./skill-calls-metadata.md) R-14~R-21을 따르고 여기서 복제하지 않는다.
- 소유 상태·부작용: 어서션 실행은 대체로 읽기 전용이다. 예외: `llm-rubric`·`agent-rubric` 핸들러는 입력 객체를 바꾼다(`assertion.value`를 rubricPrompt로 채움, 객체 `rubricPrompt`를 문자열로 직렬화; R-45). 결과 객체의 `assertion`은 원 어서션 참조다. 외부 효과는 코드 계열(프로세스·함수 실행)·`webhook`(HTTP)·모델 채점(grader 호출)에서만 생긴다.

### 1.3 인터페이스와 데이터 의미 [필수]

**설정 키(외부 계약, 원문 이름)**

| 위치 | 키 | 타입 | 의미·제약 |
|---|---|---|---|
| 어서션 | `type` | string | 필수. 등록부 키, `not-<키>`, `assert-set`, `select-best`, `max-score`. 이 밖은 R-05. |
| | `value` | string \| string[] \| number \| object \| function | 기대값·코드·규칙. 해석은 R-08. 함수 값은 Node API 전용(설정 파일로는 못 씀). |
| | `config` | map | 스크립트·함수에 `context.config`로 복사 전달(R-10). |
| | `threshold` | number | 핸들러마다 뜻이 다르다(최대 비용·최대 ms·최소 점수 등, 1.4 표). 숫자 아니면 무시되는 곳이 많다. |
| | `weight` | number | 집계 가중치, 기본 1. 0이면 측정 전용(R-11, R-16). |
| | `metric` | string | 이름 붙은 점수. Nunjucks 렌더(변수 `vars`), 렌더 실패 시 원문(R-17). |
| | `provider`, `rubricPrompt` | provider 참조, prompt | 모델 채점용 grader·프롬프트 덮어쓰기. `test.options.provider`보다 우선(R-10). |
| | `transform` | 문자열(인라인 JS \| `file://…`) | 이 어서션에만 적용할 출력 변환(R-06). |
| | `contextTransform` | 위와 같음 | `context-*` 모델 채점 전용(출력에서 context 추출). 이 스펙 밖. |
| | `normalizeUnicode` | boolean \| `NFC`\|`NFD`\|`NFKC`\|`NFKD` | `equals`·`contains`만. `true`=NFC. |
| `assert-set` | `type: assert-set`, `assert`(어서션 목록), `weight`, `metric`, `threshold`, `config` | | 한 단계 묶음(R-15). `config`는 스키마에만 있고 하위로 전달되지 않는다(2.1). |
| 테스트 | `assert`, `threshold`, `assertScoringFunction`, `options.transform`(`postprocess`), `options.provider`, `options.rubricPrompt`, `options.disableDefaultAsserts` | | `assertScoringFunction`은 `file://*.js\|ts…\|py[:함수]` 문자열 또는 함수(R-21). |

**`AssertionParams` — 핸들러 입력(C-03)**

| 필드 | 의미 |
|---|---|
| `assertion` | 원 어서션 객체(결과의 `assertion`으로 되돌려 보냄) |
| `baseType` | `not-` 제거한 type. `rouge-*`·`similar:*`처럼 type 문자열로 변형을 고를 때 사용 |
| `inverse` | `not-` 접두어 여부 |
| `output` / `outputString` | 어서션 `transform` 적용 후 출력(문자열 또는 객체) / `string`이면 그대로, 객체면 `JSON.stringify` |
| `renderedValue` | R-08로 해석한 `value`. 스크립트 값이면 스크립트 결과 |
| `valueFromScript` | `file://`·`package:` 값을 실행한 결과(없으면 undefined) |
| `prompt` | 렌더된 prompt 문자열 |
| `provider` | 테스트 대상 provider(채점 provider 아님) |
| `providerResponse` | 평가기가 만든 응답(`output`은 test.options.transform까지 적용됨, `providerTransformedOutput`은 provider.transform까지만) |
| `cost`, `latencyMs`, `logProbs` | 응답에서 꺼낸 값(`latencyMs`는 `response.latencyMs ?? 평가기가 잰 값`) |
| `test` | 깊은 복사 후 얼린 `AtomicTestCase`. `options.provider`=`assertion.provider \|\| test.options.provider`, `options.rubricPrompt`=`assertion.rubricPrompt \|\| options.rubricPrompt`(R-10) |
| `providerCallContext` | `provider`가 있을 때만 `{originalProvider, prompt:{raw, label:''}, vars, traceparent?}`. 모델 채점 호출에 그대로 전달 |
| `assertionValueContext` | 스크립트·함수에 주는 `context`(아래 표) |

**`context`(`AssertionValueFunctionContext`, 스크립트·함수 어서션이 받음)**: `{prompt, vars, test, logProbs, config?(어서션 config 복사), provider, providerResponse, trace?, metadata?(=providerResponse.metadata)}`. 스크립트에는 `(output, context)` 두 인자가 JSON으로 간다(`provider` 함수 필드는 직렬화에서 빠진다).

**`GradingResult` — 모든 핸들러의 출력(C-01)**

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `pass` | boolean | 필수 |
| `score` | number | 필수. 보통 0~1이지만 강제하지 않는다(음수·1 초과 가능). 사용자 코드가 돌려줄 때는 유한한 수여야 한다. |
| `reason` | string | 필수. 사람이 읽는 설명 |
| `namedScores` | map<string, number> \| null | 항목별 점수. 값은 유한한 수 |
| `namedScoreWeights` | map<string, number> \| null | 항목별 가중치 합 |
| `tokensUsed` | `TokenUsage` | 이 어서션이 쓴 토큰(모델 채점 시) |
| `componentResults` | list<GradingResult> \| null | 하위 결과. 중첩 가능(`assert-set`, 사용자 코드가 돌려준 값) |
| `assertion` | Assertion | 채점한 어서션 |
| `comment`, `suggestions`, `metadata` | | 부가 정보. `metadata`: `renderedAssertionValue`, `renderedGradingPrompt`, `cachedResponse`, `graderError`(true만), `assertionSet` 등 |

사용자 코드(JS 객체·Python dict)가 돌려준 값의 유효성은 `isGradingResult`(C-01)가 정한다: `pass` boolean, `score` 유한 수, `reason` string, `namedScores`·`namedScoreWeights`는 없거나 유한 수 map, `componentResults`는 없거나 배열(빈 칸 없는 배열, 순환 없음), `comment`는 없거나 string.

**집계 입력·출력 시그니처**: `runAssertion({prompt, provider, assertion, test, vars, providerResponse, latencyMs, traceId, traceData, …}) → GradingResult`(어서션 1개), `runAssertions({assertScoringFunction, latencyMs, prompt, provider, providerResponse, test, vars, traceId}) → GradingResult`(테스트 1건 전체), `runCompareAssertion(test, assertion, outputs[], context) → GradingResult[]`(`select-best`, 열마다 하나). 이 함수들은 라이브러리 export에도 들어 있다(`assertions` 객체, 이 스펙은 Node API를 다루지 않는다).

**`ScoringFunction`**: `(namedScores: map<string,number>, context?: {threshold?, parentAssertionSet?, componentResults?, tokensUsed?}) → GradingResult | Promise<GradingResult>`(C-04).

**등록부 68키 분류**(C-05). 키 집합은 `BaseAssertionTypes`와 같다. 각 키에는 `not-` 변형이 있다.

| 분류 | 키 | 비고 |
|---|---|---|
| 문자열 비교(결정적) | `contains` `contains-all` `contains-any` `icontains` `icontains-all` `icontains-any` `equals` `starts-with` `regex` `word-count` `levenshtein` | 대표 규칙 R-27~R-31 |
| 구조 검사(결정적) | `is-json` `contains-json` `is-xml` `contains-xml` `is-html` `contains-html` `is-sql` `contains-sql` | JSON만 R-28. 나머지 본문 미탐색 |
| 응답 필드·성능 | `cost` `latency` `finish-reason` `perplexity` `perplexity-score` `is-refusal` `guardrails` | R-29, R-30. `is-refusal`은 휴리스틱 목록 미탐색 |
| 도구 호출 형식 | `is-valid-function-call` `is-valid-openai-function-call` `is-valid-openai-tools-call` `tool-call-f1` | 본문 미탐색 |
| 텍스트 유사도 지표(결정적 계산) | `bleu` `gleu` `meteor` `rouge-l` `rouge-n` `rouge-s` | 점수 규약만 R-31 |
| 코드 | `javascript` `python` `ruby` `webhook` | R-34~R-43 |
| 스킬 | `skill-used` | R-44 → skill-calls-metadata |
| 모델·외부 서비스 채점 | `llm-rubric` `factuality` `model-graded-factuality` `model-graded-closedqa` `g-eval` `similar` `similar:cosine` `similar:dot` `similar:euclidean` `answer-relevance` `context-faithfulness` `context-recall` `context-relevance` `conversation-relevance` `search-rubric` `agent-rubric` `classifier` `moderation` `pi` | 호출 경계만 R-45~R-48 |
| 트레이스·궤적(범위 밖) | `trace-error-spans` `trace-span-count` `trace-span-duration` `trajectory:goal-success` `trajectory:step-count` `trajectory:tool-args-match` `trajectory:tool-sequence` `trajectory:tool-used` | 존재만. `trajectory:goal-success`는 모델 채점이기도 함 |
| 등록부 밖 특수 타입 | `assert-set` `select-best` `max-score` `human` | R-15, R-49~R-52 / `human`은 UI 전용 |

### 1.4 행동 규칙과 남은 질문 [필수]

**A. 등록·타입·반전**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 핸들러 등록 | `ASSERTION_HANDLERS`는 `Record<BaseAssertionTypes, (AssertionParams) => GradingResult \| Promise<GradingResult>>`이고 키가 정확히 68개, `BaseAssertionTypes`와 같은 집합이다(타입이 누락을 막음). 한 함수를 여러 키가 공유한다: `is-valid-function-call`·`is-valid-openai-function-call`, `similar`·`similar:cosine\|dot\|euclidean`(type 문자열 뒤 접미사로 metric 선택, 모르는 접미사는 오류), `rouge-l\|n\|s`(baseType 끝 글자), `factuality`·`model-graded-factuality`, `is-xml`·`contains-xml`(둘 다 `handleIsXml`). `meteor`는 지연 로드하고 `natural` 패키지가 없으면 던지지 않고 `pass:false, score:0, reason:'METEOR assertion requires the natural package…'`를 돌려준다. | 코드 확인 |
| R-02 | 특수 타입 | `select-best`·`max-score`·`human`은 등록부 키가 아니다. `runAssertions`는 type이 `select-`로 시작하거나 `max-score`인 어서션을 실행하지 않고 건너뛴다(결과·가중치 기여 없음). `human`을 `runAssertion`에 넘기면 R-05 오류다. | 코드 확인 |
| R-03 | `not-` 접두어 | `inverse = type.startsWith('not-')`, `baseType`은 앞 4글자를 뺀 값이다. 핸들러 조회는 `baseType`으로 한다. 공통 반전 계층은 없고 **각 핸들러가 `inverse`를 받아 스스로 반전한다**. 스키마는 모든 등록 키의 `not-` 변형을 허용한다. | 코드 확인 |
| R-04 | 반전 규약(핸들러군별) | 결과를 반전할 때 관찰되는 모양은 세 가지다. ① 정확 일치류(contains·equals·regex·starts-with·is-json·cost·latency·levenshtein·word-count·finish-reason·guardrails …): `pass = (원래 판정) !== inverse`, `score = pass ? 1 : 0`. ② 점수형(bleu·rouge·perplexity-score·similar·g-eval·classifier·llm-rubric 계열): `pass`를 뒤집고 `score`를 `1 - score`로 바꾼다(`llm-rubric` 계열의 `finalizeGradedAssertion`과 `search-rubric`은 `[0,1]`로 clamp한 `invertScore`, bleu·rouge·perplexity-score·g-eval·classifier는 clamp 없는 `1 - score`, `similar`는 매처 안에서 반전하며 `euclidean`은 `1 - 1/(1+거리)`). ③ 스크립트(javascript·python·ruby): boolean은 ①처럼, 숫자는 `score`를 **그대로** 두고 `pass`만 뒤집으며, 객체는 R-35·R-36을 따른다. `webhook`은 `score = 1 - score`. 예외: 모델 채점 결과가 `metadata.graderError === true`(전송·파싱 실패)이면 반전하지 않고 실패 그대로 둔다(R-46). `pi`와 `trace-*`는 `inverse`를 읽지 않아 `not-` 접두어가 효과 없다(`src/assertions/` 파일별 `inverse` 검색). | 코드 확인 |
| R-05 | 알 수 없는/잘못된 type | `type`이 비어 있으면 `Assertion must have a type: <JSON>` 오류. `promptfoo:redteam:`으로 시작하는 baseType은 `handleRedteam`으로 간다(범위 밖). 그 밖에 등록부에 없으면 `Unknown assertion type: <type>`을 던진다. `AssertionTypeSchema`의 마지막 유니온 멤버가 `z.custom`(검사 함수 없음)이라 스키마는 임의 문자열을 받아들일 수 있고(추론: zod의 `z.custom` 기본 동작), 그 경우 설정 로드가 아니라 실행 시점에 이 오류가 난다. 설정 로드 시 `validateAssertions`는 `type` 누락, 객체가 아닌 항목, 테스트당 10000개 초과, `assert-set`의 `assert`가 배열이 아닌 경우를 `AssertValidationError`로 막는다. | 코드 확인 / zod 동작은 추론 |

**B. 입력 준비(`runAssertion`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | 변환(`transform`) 순서 | 출력은 세 단계로 바뀐다. ① `provider.transform`(평가기, 응답 하나에 한 번) → ② `test.options.transform`(없으면 `options.postprocess`)(평가기, 한 번) → ③ 어서션의 `transform`(어서션마다 `runAssertion` 안에서 ②의 결과 `output`에 적용). ①②는 `providerResponse.output`을 바꾸고 ①의 결과는 `providerTransformedOutput`에 따로 남는다. ③은 핸들러에 주는 `output`·`outputString`만 바꾸고 `providerResponse`와 `context.providerResponse.output`은 바꾸지 않는다. ③의 컨텍스트는 `{vars, prompt:{label: prompt}, metadata?}`(②는 `prompt`가 prompt 객체). 변환이 `null`/`undefined`를 돌려주면 `Transform function did not return a value`, 변환 안에서 예외가 나면 `Transform failed (<label>): <메시지>`를 던진다. 둘 다 `runAssertion`에서 전파된다(R-24 오류 행). | 코드 확인 |
| R-07 | 컨텍스트 구성 | `context = {prompt, vars: 해석된 vars, test: 원 test, logProbs, provider, providerResponse, config?: structuredClone(assertion.config), metadata?: providerResponse.metadata}`. `traceId`가 있고 어서션이 트레이스를 쓸 수 있을 때만 `trace`를 더한다(범위 밖). `vars`는 호출자가 준 해석된 vars이고, 없으면 `test.vars \|\| {}`. | 코드 확인 |
| R-08 | `value` 해석 | 기준 경로는 `cliState.basePath`(없으면 현재 디렉터리). **문자열**: (a) `file://`로 시작 → 첫 `:` 앞이 경로, 뒤가 함수 이름(Windows 드라이브 문자 `C:`가 있으면 잘못 쪼개진다). 경로가 JS/TS 확장자면 `loadFromJavaScriptFile(경로, 함수, [output, context])`(함수 우선순위: 이름 붙은 export → 모듈 자체가 함수 → default export, 없으면 `Assertion malformed: … must export a function`), `.py`면 `runPython(경로, 함수 \|\| 'get_assert', [output, context])`, `.rb`면 `runRuby(…, 'get_assert', …)`; Python·Ruby 실행 예외는 던지지 않고 `{pass:false, score:0, reason:<예외 메시지>, assertion}`을 즉시 돌려준다(JS 파일 로드·실행 예외는 던져 전파). 그 밖의 확장자는 `processFileReference`: `.json`·`.yaml`·`.yml`은 파싱한 객체, `.txt`는 trim한 문자열, 그 외는 `Unsupported file type`. (b) `package:<패키지>:<export>` → `loadFromPackage` 결과가 함수여야 하고(아니면 `Assertion malformed: … must be a function`) `(output, context)`로 호출한 결과가 `valueFromScript`. (c) 그 밖의 문자열 → `vars`로 Nunjucks 렌더. **배열**: 각 문자열 원소가 `file://`면 `processFileReference`, 아니면 Nunjucks 렌더(비문자열 원소는 그대로). **그 밖**(객체·숫자·함수): 렌더하지 않는다. | 코드 확인 |
| R-09 | 스크립트 결과의 쓰임 | `valueFromScript`가 정의되었고 baseType이 `javascript`·`python`·`ruby`가 아니면: 함수·boolean·`pass` 키가 있는 비배열 객체이면 `Script for "<type>" assertion returned a function\|boolean\|GradingResult…` 오류를 던지고, 그 밖의 값(문자열·숫자·배열·객체)은 `renderedValue`를 대체한다. `javascript`·`python`·`ruby`에서는 그 값이 채점 결과 후보가 된다(R-31, R-35). | 코드 확인 |
| R-10 | 핸들러 입력 구성 | `output`은 R-06 ③ 이후 값, `outputString`은 `coerceString(output)`. `test`는 `getFinalTest`(깊은 복사 후 `Object.freeze`; `options.provider = assertion.provider \|\| test.options.provider`, `options.rubricPrompt = assertion.rubricPrompt \|\| options.rubricPrompt`; `test.provider`는 복사본에서 비우고 원 인스턴스를 되돌려 놓음). `provider`가 있을 때만 `providerCallContext = {originalProvider: provider, prompt:{raw: prompt \|\| '', label:''}, vars, traceparent?}`를 만든다. | 코드 확인 |
| R-11 | 핸들러 호출 직후 | 핸들러가 던지면 그대로 전파된다(스크립트·webhook 핸들러는 내부에서 잡아 실패 결과로 바꿈, R-34~R-43). 결과에 대해: ① `renderedValue`가 문자열이고 원 `assertion.value`와 다르면 `result.metadata.renderedAssertionValue`에 기록. ② `assertion.weight === 0`이면 `pass`를 `true`로 강제한다(`score`·`reason`은 그대로). | 코드 확인 |

**C. 집계(`runAssertions` / `AssertionsResult`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | `test.assert`가 없거나 비어 있음 | `{pass:true, score:1, reason:'No assertions', tokensUsed:{total:0, prompt:0, completion:0, cached:0, numRequests:0}}`. `assert`에 `select-best`·`max-score`만 있으면 목록은 비지 않으므로 이 경로가 아니라 R-13을 따르고 어서션 결과가 하나도 없는 `score:0, pass:true`가 된다(R-14). | 코드 확인 |
| R-13 | 실행 방식 | 어서션들은 `PROMPTFOO_ASSERTIONS_MAX_CONCURRENCY`(기본 3, 최소 1)개씩 동시에 실행한다. 공급자 호출 큐가 켜져 있으면(모델 채점 그룹화, R-26) 1개씩이다. 한 어서션이 던지면 새 실행을 멈추고 진행 중인 것이 끝나길 기다린 뒤 그 오류가 `runAssertions`에서 전파된다. 결과는 완료 순서가 아니라 어서션 위치(`index`)에 놓인다. | 코드 확인 |
| R-14 | 건너뛴 어서션의 영향 | `select-*`·`max-score`는 `addResult`를 부르지 않는다: `totalWeight`에 들지 않고 `componentResults`에는 빈 칸이 생겨 평탄화에서 빠진다. 결과가 하나도 없으면 `score = totalWeight>0 ? … : 0`이므로 0, 실패 없음이므로 `pass:true`, `reason:'All assertions passed'`다. | 코드 확인 |
| R-15 | `assert-set` | 최상위 목록의 `assert-set` 항목은 `assert`의 하위 어서션으로 펼쳐지고, 하위 어서션은 **그 세트 전용** `AssertionsResult`(`threshold = 세트의 threshold`)에 쌓인다(하위 `index`는 세트 안 위치). 모든 하위 실행이 끝나면 세트 결과 `testResult()`가 어서션 하나처럼 부모에 `addResult`된다(`index` = 세트 위치, `weight`·`metric` = 세트의 값, `metric`은 R-17처럼 렌더). 세트 결과에는 `metadata.assertionSet = {type, assertionCount, metric?, threshold?, weight?}`가 붙는다. 한 단계만 펼치므로 세트 안의 `assert-set`은 `Unknown assertion type: assert-set`이 된다(실행 흐름으로 도출). 세트에는 `assertScoringFunction`이 적용되지 않는다. | 코드 확인 |
| R-16 | `addResult`: 점수·가중치 | `weight` 기본 1(`undefined`일 때만; 0과 음수는 그대로). `totalScore += score*weight`, `totalWeight += weight`, `componentResults[index] = result`. 실패(`!pass`)이면 `failedReason = result.reason`(마지막으로 기록된 실패의 이유; 동시 실행이라 기록 순서가 완료 순서에 달려 있다 — 추론). `PROMPTFOO_SHORT_CIRCUIT_TEST_FAILURES`가 참이면 첫 실패 기록 시 그 이유로 `Error`를 던진다. | 코드 확인 / 순서 영향은 추론 |
| R-17 | `namedScores`·`namedScoreWeights` | `metric`이 있으면(`renderMetricName`: Nunjucks로 렌더, 렌더 예외면 원문 유지, 빈 문자열이면 그대로 빈 값) `metricWeight = weight===0 ? 1 : weight`로 `namedScores[metric] += score*metricWeight`, `namedScoreWeights[metric] += metricWeight`. 즉 `weight:0` 어서션은 총점에는 안 들지만 `metric` 값은 기록한다. 하위 결과가 자체 `namedScores`(스크립트 반환, `assert-set`의 집계)를 가지면, 이름이 이 어서션의 `metric`과 같지 않은 것들을 `(하위 가중치 ?? 1) × metricWeight`로 같은 방식으로 더한다. 최종 `namedScores[m] = 합 / 가중치 합`(가중치 합이 0 이하면 0)이고 `namedScoreWeights`는 하나라도 있을 때만 결과에 넣는다. 맵은 프로토타입 없는 객체다. | 코드 확인 |
| R-18 | `tokensUsed` 합산 | 결과의 `tokensUsed`는 하위 결과 `tokensUsed`의 합이다(`total·prompt·completion·cached·numRequests`, `completionDetails`, `incurredTokenUsage`). `metadata.cachedResponse === true`인 하위 결과는 `cached`로 환산해 더하고 `incurredTokenUsage`는 0으로 둔다. 모든 하위 결과가 `cachedResponse`이면 집계 결과 `metadata.cachedResponse = true`. 상세 식은 C-10. | 코드 확인 |
| R-19 | `testResult()`: 점수·통과·reason | `score = totalWeight>0 ? totalScore/totalWeight : 0`(둘 중 하나가 유한하지 않으면 `NaN`). `pass = (failedReason === undefined)`, `reason = failedReason ?? 'All assertions passed'`. **`threshold`(이 `AssertionsResult`의 것: 테스트 최상위 또는 세트)가 숫자이면** `pass = score >= threshold`로 덮고 `reason = 'Aggregate score <score.toFixed(2)> ≥\|< <threshold> threshold'`가 된다(개별 어서션 실패는 무시된다. `threshold: 0`도 덮어쓰며 음수 점수면 실패. `null`·`NaN`이면 덮지 않음). 예외: `type:'guardrails'`이고 `config.purpose === 'redteam'`인 결과가 실패하면 `pass:true`, `reason:'Content failed guardrail safety checks'`로 강제한다(레드팀 특수 집계). | 코드 확인 |
| R-20 | 결과 모양 | `{pass, score, reason, namedScores: 정규화된 맵, namedScoreWeights?, tokensUsed, componentResults, metadata?}`. `componentResults`는 한 단계 평탄화한다: 어서션 결과가 자기 `componentResults`를 가지면(`assert-set`, 또는 사용자 코드가 중첩 결과를 반환) `[그 결과, …하위 결과(자기 `assertion`이 없으면 부모의 것을 채움)]`로 펼친다. 하위 결과에도 하위가 있으면 더 펼치지 않는다. `metadata`는 세트이면 `assertionSet`, 전체가 cachedResponse이면 `cachedResponse:true`일 때만 있다. | 코드 확인 |
| R-21 | `assertScoringFunction` | 테스트 최상위 `AssertionsResult`에만 적용한다. 함수는 `(정규화된 namedScores, {threshold, parentAssertionSet, componentResults(평탄화), tokensUsed})`로 호출되고, 반환값은 `asGradingResult`로 검증한다(검증 실패나 예외 → `pass:false, score:0, reason:'Scoring function error: <메시지>'`로 이 행의 결과를 바꿈). 성공하면 `{...기본 결과, ...반환값}`이다. 반환에 없는 필드(예: `namedScores`)는 기본 값이 남고 `tokensUsed`·`metadata`는 합쳐진다. 문자열 `file://…(.js\|.ts…\|.py)[:함수]`는 테스트 준비 때 `loadFunction`으로 함수로 바뀐다(R-23). | 코드 확인 |
| R-22 | 최종 유한성 검사 | 모든 처리 뒤 `score`가 유한하지 않거나 `namedScores`/`namedScoreWeights`에 유한하지 않은 값이 있으면 `pass:false, score:0, reason:'Assertion aggregation error: scores or weights must remain finite'`로 바꾸고 그 metric 항목은 맵에서 뺀다. 맵을 읽다 예외가 나면 reason `Assertion aggregation error: unable to read scores or weights`와 빈 맵. | 코드 확인 |

**D. 평가기 연결**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-23 | 테스트 준비(`prepareTestCaseForEval`) | `test.assert = [...(options.disableDefaultAsserts === true ? [] : defaultTest.assert), ...test.assert]`(기본 어서션이 앞). `threshold = test.threshold ?? defaultTest.threshold`, `assertScoringFunction = test ‖ defaultTest`(문자열이면 함수로 로드), `options`는 `{...defaultTest.options, ...test.options}`. `assert`가 배열이 아니면 `invariant` 오류. | 코드 확인 |
| R-24 | 채점 결과의 행 반영 | 채점 성공: `row.success = pass`, `row.score = score`, `row.namedScores = namedScores \|\| {}`, `row.gradingResult = 결과 전체`. `!pass`이면 `row.error = reason`, `failureReason = ASSERT`. 채점 중 예외(R-05·R-06·R-08·R-11 오류, 핸들러 invariant, 모델 채점 provider 예외; 스코어링 함수의 오류는 R-21처럼 결과로 바뀌므로 제외): 행은 `error = 스택 또는 메시지`, `failureReason = ERROR`, `success=false`, `score=0`, `namedScores={}`가 된다(중단 신호로 인한 예외는 `error = 'Aborted: …'`). 한 행의 오류는 다른 행을 멈추지 않는다. | 코드 확인 |
| R-25 | 어서션에 전달되는 응답 | 평가기는 `{...processedResponse, providerTransformedOutput}`을 `providerResponse`로 넘기고, `latencyMs = response.latencyMs ?? 측정 지연`, `prompt = 렌더된 prompt`, `vars`는 해석된 변수다. | 코드 확인 |
| R-26 | 모델 채점 포함 시 실행 시점 | `MODEL_GRADED_ASSERTION_TYPES`(`agent-rubric`·`answer-relevance`·`context-*`·`factuality`·`llm-rubric`·`model-graded-closedqa`·`model-graded-factuality`·`search-rubric`·`trajectory:goal-success`)와 `conversation-relevance`·`g-eval`이 어서션(세트 안 포함)에 하나라도 있는 테스트는 채점을 미루고 provider 호출 큐로 judge별 그룹화해 실행할 수 있다. 이때 R-13의 동시 실행은 1이다. 그룹화·미룸의 스케줄은 eval-run 소관이다. | 코드 확인(조건만) |

**E. 결정적 계열(대표)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-27 | `contains` 계열 | `contains`: `value`는 비지 않은 문자열이거나 NaN 아닌 숫자(아니면 `"<type>" assertion type must have a string or number value`를 던짐). `outputString`이 `String(value)`를 부분 문자열로 포함하는지(`normalizeUnicode`가 있으면 양쪽을 그 정규화로). `icontains*`는 양쪽 `toLowerCase()`(`normalizeUnicode` 무시). `*-any`/`*-all`: `value`가 문자열이면 `parseCommaSeparatedValues`(쉼표 구분, 앞뒤 공백 제거, 따옴표 필드 지원, 빈 필드 무시; C-12)로 목록이 되고 아니면 배열이어야 한다. `any`는 하나라도, `all`은 모두 포함. `pass = 일치 !== inverse`, `score = pass?1:0`, 실패 reason은 `Expected output to [not ]contain …`(`all`이면 `Missing: [...]` 목록 포함). | 코드 확인 |
| R-28 | `equals`·`starts-with`·`regex`·`is-json`·`contains-json` | `equals`: `value`가 객체이면 `JSON.parse(outputString)`과 깊은 엄격 동등 비교(파싱 실패는 "같지 않음"으로 처리해 `pass = inverse`), 아니면 `String(value) === outputString`(`normalizeUnicode` 적용). `starts-with`: `value`가 비지 않은 문자열이어야 하고 `outputString.startsWith`. `regex`: 문자열 패턴을 플래그 없이 `new RegExp`로 컴파일, 잘못된 패턴이면 던지지 않고 `pass:false, score:0, reason:'Invalid regex pattern: …'`(`not-`여도 실패), 그 외 `test(outputString) !== inverse`. `is-json`: `JSON.parse(outputString)`이 되면 통과(배열·원시값 포함), `value`(YAML/JSON 스키마 텍스트·객체·`file://` 스키마)가 있고 파싱됐다면 ajv로 검증하고 비적합이면 `score:0, reason:'JSON does not conform to the provided schema. Errors: …'`(반전이면 적합할 때 실패). `contains-json`: 출력에서 JSON 객체 후보를 모두 뽑아(`extractJsonObjects`, 객체만) 하나라도 있으면 통과, 스키마가 있으면 하나라도 적합해야 통과. | 코드 확인 |
| R-29 | `cost`·`latency` | `cost`: `threshold`가 없고 `metric`이 있고 `weight===0`이고 `not-`가 아니면 측정 전용이다: `cost`(`providerResponse.cost`)가 유한한 0 이상이 아니면 `Cost metric requires a finite, non-negative provider cost`를 던지고, 맞으면 `score = cost`, `reason:'Cost: $<cost>'`, `pass:true`. 그 밖에 `threshold`가 없으면 `Cost assertion must have a threshold`를 던진다. `threshold`가 있는데 `cost === undefined`이면 `Cost assertion does not support providers that do not return cost`를 던진다. `pass = (cost <= threshold) !== inverse`, `score = pass?1:0`. `latency`: `threshold`(ms) 필수, `latencyMs === undefined`면 `Latency assertion does not support cached results. Rerun the eval with --no-cache`를 던진다. `pass = (latencyMs <= threshold) !== inverse`. | 코드 확인 |
| R-30 | 응답 필드·로그확률 | `finish-reason`: `value`는 문자열. `providerResponse.finishReason`이 없으면 `pass = inverse`(reason `Provider did not supply stop/finish reason`), 있으면 소문자 비교. `perplexity`·`perplexity-score`: `logProbs`가 없거나 비면 던진다. 평균 로그확률의 `exp(-평균)`이 perplexity, `perplexity-score`는 `1/(1+perplexity)`이고 이것이 `score`(반전이면 `1-`). `threshold`가 없으면 `pass:true`. `guardrails`: `providerResponse.guardrails.flagged`(없으면 redteam 이력의 마지막 값, 그것도 없으면 flagged 아님)이면 `pass = inverse`, 아니면 `pass = !inverse`. | 코드 확인 |
| R-31 | 점수형 결정적 지표의 규약 | `levenshtein`: `value` 문자열, `threshold` 기본 5, 편집 거리 `<= threshold`면 통과(이진 점수). `word-count`: `value`가 숫자(또는 숫자 문자열)이면 단어 수(공백 구분 `\S+` 개수)가 같아야 하고, `{min?, max?}` 객체이면 범위(둘 다 없으면 오류, `min > max`이면 오류). `bleu`(threshold 기본 0.5)·`rouge-l\|n\|s`(기본 0.75): `score`는 지표 값 자체(이진 아님), `pass = score >= threshold !== inverse`, 반전이면 `score = 1 - 지표`. 지표 계산식은 범위 밖. | 코드 확인 |

**F. 코드 계열(맞춤 채점)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-32 | 입력 공통 | 코드는 `(output, context)`를 받는다(`output` = R-06 ③ 이후 값으로 문자열 또는 객체, `context`는 1.3 표). 반환값 종류: boolean / 수 / `GradingResult` 객체(Python은 dict 또는 JSON 문자열도). 반환값이 채점 결과가 되고 `weight`·`metric`은 어서션 값이 집계에 쓰인다(R-16, R-17). | 코드 확인 |
| R-33 | 코드가 오는 길 | `value`가 인라인 코드 문자열(Nunjucks 렌더됨, R-08 (c)) 또는 `file://파일[:함수]`(R-08 (a)) 또는 `package:` 함수(R-08 (b)). 함수 기본 이름: Python·Ruby `get_assert`. 파일이 JS면 `(output, context)` 호출, 함수 이름이 없으면 모듈 자체가 함수 → default 순. | 코드 확인 |
| R-34 | `javascript` 인라인 | `value`는 문자열이어야 하고(아니면 `javascript assertion must have a string value`) `trimEnd()`한다. 한 줄이면 `buildFunctionBody`: 앞이 `const\|let\|var `로 시작하면 마지막 "문장 구분" 세미콜론 뒤에 `return `을 끼우고(문자열·괄호 안 세미콜론은 구분자가 아님; acorn 토큰으로 판별), 아니면 `return ` + 코드. 여러 줄이면 코드를 그대로 쓴다(직접 `return`해야 함). `new Function('output','context','process', 본문)`으로 만들어 `(output, context, processShim)`으로 호출하고 `await`한다. safe mode(`--safe-mode`, `PROMPTFOO_SAFE_MODE`)에서는 실행하지 않고 `pass:false, score:0, reason:'Inline JavaScript execution is disabled in safe mode…'`를 돌려준다. 함수 값(Node API)이면 `(outputString, context)`로 호출한다(인라인과 달리 문자열). | 코드 확인 |
| R-35 | JS 반환 정규화 | 반환(await 후)은 boolean, 유한한 수, 유효한 `GradingResult` 중 하나여야 한다(아니면 `Custom function must return a boolean, a finite number, or a GradingResult object with finite scores and weights. Got type …`). boolean: `pass = 반환 !== inverse`, `score = pass?1:0`, 실패 reason `Custom function returned true\|false`(인라인 코드가 줄로 덧붙음). 수: `rawPass = threshold===undefined ? 수>0 : 수>=threshold`, `pass = rawPass !== inverse`, **`score = 그 수`(반전과 무관)**. 객체: `pass = 반환.pass !== inverse`이고 나머지 필드(`score`, `namedScores`, `componentResults`, `reason` …)는 반환값 그대로이며 `reason`은 빈 문자열이어도 보존한다. 어서션의 `threshold`는 객체 반환에는 적용되지 않는다. 결과 `assertion = 반환.assertion ?? assertion`(함수 값은 50자로 줄여 직렬화). | 코드 확인 |
| R-36 | JS 파일·오류 | `file://x.js[:fn]`이면 R-08 (a)로 함수를 호출한 결과(`valueFromScript`)가 R-35의 반환이다(문자열 반환은 `Javascript assertion script must return a boolean, number, or object` 오류로 실패 결과가 됨). 파일 로드 실패·내보낸 함수 없음은 `runAssertion`에서 던져 R-24의 오류 행이 된다. 함수 본문 실행 예외와 반환 검증 실패는 던지지 않고 `pass:false, score:0, reason:'Custom function threw error: <메시지>\nStack Trace: <스택>'`(검증 실패가 아니면 인라인 코드가 뒤에 덧붙음)이다. | 코드 확인 |
| R-37 | `python`·`ruby` 인라인 | `value`는 문자열(아니면 `python\|ruby assertion must have a string value`). 한 줄이면 `return <value>`, 여러 줄이면 첫 들여쓰기 줄의 들여쓰기로 모든 줄을 감싼다(C-19). Python은 `import json` + `def main(output, context):` 본문, Ruby는 `require 'json'` + `def main(output, context) … end` 본문으로 만든 코드의 `main`을 `[output, context]`로 호출한다. 예외는 던지지 않고 `pass:false, score:0, reason:'Python code execution failed: <메시지>'`(Ruby는 `Ruby code execution failed: …`)다. `file://x.py\|x.rb`는 R-08 (a)로 같은 인자로 호출하고, 그 예외는 접두어 없이 `reason = <메시지>`다. | 코드 확인 |
| R-38 | Python·Ruby 반환 정규화(`normalizeScriptResult`) | `true`/`"true"`(대소문자 무시) → 통과 판정, `false`/`"false"` → 실패 판정, 그 판정에서 boolean 규칙(R-35)과 같이 `inverse` 적용. 문자열이 `{`로 시작하면 JSON 파싱(실패 시 `Invalid JSON: …`)한 객체로 처리. 객체(또는 위 JSON)는 `mapSnakeCaseToCamelCase`(`pass_`→`pass`, `named_scores`→`namedScores`, `named_score_weights`, `component_results`, `tokens_used`; 대응하는 camelCase가 이미 있으면 안 덮음; `componentResults`는 재귀)한 뒤 `asGradingResult`로 검증한다(실패: `<Python\|Ruby> assertion must return a boolean, number, or {pass, score, reason} object with finite scores and weights. Got type object.`). 그 다음 `threshold`가 있고 `score < threshold`이면 `pass=false`, `reason = "<Python\|Ruby> score <score> is less than threshold <threshold>: <원래 reason>"`(원래 reason이 없으면 앞 문장만). 이어서 `inverse`: `pass = 객체.pass !== inverse`이고 `reason`은 반전일 때 통과면 `Assertion passed`, 실패면 `원래 reason \|\| '<Python\|Ruby> code returned true'`, 비반전이면 원래 reason. 객체의 `score` 등은 그대로다. 그 밖(숫자 또는 숫자 문자열)은 `parseFloat`, NaN이면 `… must return a boolean, number, or {pass, score, reason} object. Instead got: …`. 수는 JS와 같다(`threshold` 없으면 `>0`, `score = 그 수`). 이 모든 예외는 R-37의 `execution failed` 실패 결과가 된다. | 코드 확인 |
| R-39 | 사용자 코드의 `GradingResult` 유효성(`asGradingResult`) | 위 R-35·R-38의 "유효한 GradingResult"는 `isGradingResult`(C-01)를 통과해야 하며, 옛 형태 몇 가지는 변환해 받아들인다. 순수 객체(plain object)에 한해: `namedScores` 값이 boolean·null·숫자 문자열이면 숫자로(`true`=1, `false`·`null`=0), `undefined` 값은 뺀다. 중첩 `componentResults` 항목은 `pass`가 boolean이면 `reason` 누락을 `''`, `score` 누락을 `pass?1:0`으로 채운다. 최상위의 `reason` 누락, `NaN`·무한대 점수, 배열의 빈 칸, 순환 참조는 거부한다. | 코드 확인 |
| R-40 | `webhook` | `value`는 URL 문자열(렌더됨; 아니면 invariant 오류, 이 오류는 아래 try 밖이라 던져짐). `fetchWithRetries(url, {POST, Content-Type: application/json, body: JSON.stringify({output, context:{prompt, vars: test.vars \|\| {}}})}, WEBHOOK_TIMEOUT 기본 5000ms)`. 응답은 `response.ok`여야 하고(아니면 `Webhook response status: <코드>`) JSON `{pass: boolean(필수), score?: 0~1 수, reason?: string}`이어야 한다. `pass = 응답.pass !== inverse`, `score = 응답.score ?? (응답.pass ? 1 : 0)`(반전이면 `1 - score`), `reason = 응답.reason \|\| (pass ? 'Assertion passed' : 'Webhook returned <inverse?true:false>')`. 요청·응답 단계의 어떤 오류도(타임아웃, 비 JSON, 검증 실패) 던지지 않고 `pass:false, score:0, reason:'Webhook error: <메시지>'`가 된다(`not-`여도 실패). 재시도 횟수·조건은 `fetchWithRetries` 소관(기본 최대 4회 재시도, 조건은 미탐색). | 코드 확인(호출 인자) / 재시도 조건 미탐색 |
| R-41 | 코드 어서션의 보안·실행 경계 | 인라인 JS는 `new Function`으로 호스트 프로세스에서 실행되고 샌드박스가 아니다(`safeMode`도 인라인 문자열만 막고 파일 참조는 막지 않는다는 주석이 있다). Python·Ruby·JS 파일·`package:`·변환 파일은 사용자 코드를 실행한다. 어서션 이유에 비밀·전체 응답을 넣지 말라는 원본 지침(`src/assertions/AGENTS.md`)은 코드가 강제하지 않는다. | 코드 확인(주석) |
| R-42 | 코드 어서션의 `weight`·`metric` 활용 | 코드가 돌려준 `namedScores`는 어서션의 `metric`이 아닌 이름에 한해 R-17로 부모에 합쳐진다. 따라서 한 Python 어서션이 `named_scores`로 여러 항목 점수를 내고 `weight`로 비중을 줄 수 있다. 코드가 `componentResults`를 돌려주면 R-20 평탄화로 `componentResults`에 펼쳐진다. | 코드 확인 |
| R-43 | 코드 어서션의 컨텍스트 형태 | Python·Ruby로 가는 인자는 `[output, context]`가 `safeJsonStringify`로 직렬화되어 전달된다(함수는 빠짐). 프로세스·타임아웃·종료 코드 처리는 script-bridges 소관이다. 이 스펙이 가정하는 경계: `runPython/runRuby(경로, 함수, 인자) → JSON 값` 또는 던짐. | 코드 확인(직렬화 호출) / 이후는 script-bridges |

**G. 스킬 어서션**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-44 | `skill-used`·`not-skill-used` | `ASSERTION_HANDLERS['skill-used'] = handleSkillUsed`. `not-skill-used`는 같은 핸들러에 `inverse:true`가 간다. `value` 문자열·문자열 배열은 R-08로 Nunjucks 렌더되고 객체는 렌더되지 않는다. 입력 선별, `value` 해석, 일치, 반전, 결과 모양은 [skill-calls-metadata](./skill-calls-metadata.md) R-14~R-21을 따른다(`score`는 0 또는 1). `skillCalls`를 채우는 provider는 같은 문서 R-02~R-13. | 코드 확인(등록·렌더) / 본문 규칙은 선행 스펙 |

**H. 모델 채점 계열: 호출 경계와 반환 형태**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-45 | 핸들러→매처 호출 | 모델 채점 핸들러(`llm-rubric`·`factuality`·`g-eval`·`similar`·`classifier`·`search-rubric`·`agent-rubric`·`answer-relevance` 등)는 `src/matchers/*`의 매처를 `(기대값/rubric, outputString, test.options(grader provider·rubricPrompt 포함), test.vars, [assertion], providerCallContext)`로 부르고 매처의 `GradingResult`(assertion 제외)를 받아 `assertion`을 붙여 돌려준다. grader는 `assertion.provider`가 `test.options.provider`보다 우선한다(R-10). grader가 없을 때의 기본 선택·프롬프트 본문은 model-graded-matchers 소관이다. `llm-rubric`·`agent-rubric` 핸들러는 호출 전에 객체 `rubricPrompt`를 문자열로 직렬화하고 `assertion.value`가 비면 `test.options.rubricPrompt`로 채운다(UI 표시용 변경). `factuality`는 문자열 `value`와 prompt가 필요하다(없으면 invariant 오류). | 코드 확인 |
| R-46 | 반환 형태와 반전 | 매처 결과는 `{pass, score, reason, tokensUsed, metadata:{renderedGradingPrompt, cachedResponse?, …}}`다. 전송 실패·빈 출력·파싱 실패·판정 없음은 던지지 않고 `pass:false, score:0, metadata.graderError:true`(`graderFail`)로 돌려준다. `not-`일 때 핸들러(`finalizeGradedAssertion`)는: 일반 결과는 `pass`를 뒤집고 `score = invertScore(score)`(`clamp(1 - score, 0, 1)`, 유한하지 않으면 1), `graderError` 결과는 그대로(실패 유지). `classifier`·`search-rubric`·`g-eval`은 같은 원칙을 각자 구현한다(`g-eval`·`classifier`는 `1 - score`). `pi`는 반전을 무시한다. 매처가 예외를 던지는 경우(예: `llm-rubric`의 grader provider 오류)는 전파되어 R-24의 오류 행이 된다. | 코드 확인 |
| R-47 | 임계값·배열 값 변형 | `threshold`의 기본·의미는 어서션마다 다르다: `g-eval` 0.7(`score >= threshold`), `similar` 0.75, RAG 계열 문서상 0.5. `llm-rubric` 계열은 grader JSON `{pass?, score?, reason}`에서 판정한다: 숫자 `threshold`가 있으면 `pass = grader.pass && score >= threshold`(grader가 `pass`를 안 주면 `score >= threshold`), 없으면 grader의 `pass`(없으면 `score > 0`). `reason`은 grader의 값 또는 `Grading passed`/`Score <s> below threshold <t>`. `g-eval`의 `value`가 배열이면 기준마다 순서대로 채점해 평균하고 첫 grader 실패에서 멈춘다(`G-Eval criterion i/n (…) failed: …`). `similar`의 `value`가 배열이면 하나라도 임계 이상이면 통과(반전이면 모든 값과 비슷하지 않아야 통과). | 코드 확인(`llm-rubric` 판정·g-eval·similar 핸들러) / 매처 내부 계산은 model-graded-matchers |
| R-48 | 모델 채점의 비용·결정성 경계 | 어서션 하나가 grader를 최소 1회 부른다(`g-eval` 배열은 기준 수만큼). 결과 `tokensUsed`가 R-18로 합산되고 `metadata.cachedResponse`는 grader 응답이 캐시에서 왔다는 표시다. 같은 출력·같은 rubric이라도 grader 응답이 비결정적이면 `score`가 달라질 수 있다(추론: LLM 응답의 일반 성질). | 코드 확인 / 비결정성은 추론 |

**I. 열 사이 비교 어서션(평가기)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-49 | 실행 시점·순서 | 같은 테스트(`testIdx`)의 모든 열(provider×prompt)이 채점된 뒤, `select-best`를 가진 테스트마다 먼저, 그다음 `max-score`를 가진 테스트마다 한 번씩 평가기가 처리한다. 열 결과는 `testIdx`로 모아 `promptIdx` 순으로 읽는다. `ERROR` 행: `max-score`는 "사용 불가"로 승자 계산에서 빼고(`Target response unavailable for comparison`), `select-best`는 그 행의 출력이 빈 문자열로 grader에 들어가며 비교 결과는 그 행에 병합되지 않는다(`restoreComparisonResult`가 거짓을 돌려줌). 열이 2개 미만이면 `… must have at least two outputs to compare between` 오류(R-50, R-51에서 처리 방식이 다르다). | 코드 확인 |
| R-50 | `select-best` 호출 | `value`는 문자열(기준 문장, Nunjucks 렌더되지 않고 `invariant`로 확인)이다. 열별 출력 문자열(`output \|\| ''`)을 모아 `runCompareAssertion(test(assert 비움), assertion, outputs, ctx)`를 한 번 부르고 grader가 가장 좋은 출력의 번호를 돌려주면 열마다 `{pass: 선택됨, score: 선택됨?1:0, reason:'Output selected as the best: …' \| 'Output not selected: …'}`(`tokensUsed` 공유)를 받는다. grader 응답의 첫 정수가 범위를 벗어나거나 오류면 모든 열이 `pass:false, score:0`이고 reason이 오류 문구다. grader 호출이 던지면(열 2개 미만 invariant 포함, 이 호출은 `try` 안이다) `ERROR` 아닌 열은 `error = 'Error grading select-best (<graderId>): …'`, `failureReason = ERROR`, `success=false`, `score=0`이 된다. grader 선택·프롬프트는 model-graded-matchers 소관. | 코드 확인 |
| R-51 | `max-score` 규칙 | 모델을 부르지 않는다. `value`(없으면 `{}`) = `{method?: 'average'\|'sum'(기본 average), weights?: {<어서션 type>: 수}, threshold?: 수}`. 각 열에서 `gradingResult.componentResults` 중 `assertion`이 있고 type이 `max-score`·`select-best`가 아닌 것을 모아(없으면 `max-score requires at least one other assertion …` 오류를 던짐), 가중치 = `weights[그 결과의 어서션 type] ?? 1`(어서션 자신의 `weight` 필드가 아님)로 `score`를 합한다. `average` = 가중 합 / 가중치 합(합이 0이면 0), `sum` = 가중 합. 최고 점수 열이 승자(동점이면 앞 열, 사용 불가 열 제외), `threshold`가 있고 최고 점수가 그 미만이면 승자 없음. 열 결과: `pass: 승자인가`, `score: 승자?1:0`, `namedScores:{maxScore, assertionCount, totalWeight}`, reason(`Selected as highest scoring output (score: x.xxx)` / `Not selected (score: x, max: y)` / threshold 미달 문구), 사용 불가 열은 `Target response unavailable for comparison`. 사전 조건 위반(출력 2개 미만, 다른 어서션 결과 없음)은 이 경로에 `try`가 없어 행 오류가 아니라 예외로 전파된다(이 함수 `processComparisonAssertions` 안에는 중단 신호 외 `catch`가 없고 상위 호출자는 미탐색). | 코드 확인 |
| R-52 | 비교 결과의 행 병합 | 비교 결과 `g`를 행에 병합한다. 행의 기존 `gradingResult`가 있으면: `success = gradingResult.pass = 기존 pass && g.pass`, `componentResults`에 `g`를 추가한다. `g.pass`가 false이면 `reason = g.reason`, 행 `score = g.score`(0)로 바꾼다(승자의 `score`는 바뀌지 않는다). 처음 `success`였다가 false가 된 행은 `failureReason = ASSERT`, `error = g.reason`이 되고 통계가 보정된다. `max-score`는 `namedScores`를 합치고 `tokensUsed`는 기존 것을 유지한다. 비교 어서션만 있는 테스트의 행은 비교 전 `score:0, pass:true`이다(R-14)이므로 승자 행의 `score`는 0으로 남는다. | 코드 확인 |

- 불변식: ① 최종 `score`는 어서션 점수의 가중 평균(`totalWeight`가 0이면 0)이며, `weight:0` 어서션과 비교 어서션은 거기에 들지 않는다. ② `pass`는 개별 판정의 AND이지만 테스트(또는 세트) `threshold`가 숫자이면 점수 비교가 대신한다. ③ `score`는 0~1이라는 보장은 없다(스크립트 반환값과 `max-score` `sum`이 범위를 넘을 수 있음). ④ `componentResults`는 어서션 위치 순서를 유지한다(실행 완료 순서가 아님).
- 미결정: 없음.
- 확인 한계: 읽기만으로 확인했고 어서션 실행·평가·모델 호출은 하지 않았다. ① `pi`·`classifier`·`moderation`·`similar`는 외부 서비스·임베딩 provider를 쓰고 그 동작은 확인하지 못했다. ② `webhook`의 재시도 조건(`fetchWithRetries`의 어떤 응답·오류를 재시도하는지)은 읽지 않았다. ③ Python·Ruby로 가는 `context`의 JSON 직렬화 결과(특히 `provider` 객체)의 정확한 모양은 확인하지 않았다. ④ `is-refusal`의 문자열 목록, `xml`·`html`·`sql`·도구 호출 계열·`gleu`·`meteor`의 본문은 읽지 않았다(키 목록과 문서의 한 줄 설명 수준). ⑤ zod `z.custom`이 검사 함수 없이 임의 값을 받아들인다는 점은 라이브러리 동작에 대한 추론이다. ⑥ 원본 테스트(`test/assertions/*.test.ts`, `test/evaluator/assertions.test.ts`)는 파일명만 확인했고 열지 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스는 MIT(overview 1절)라 인용·복사에 제약이 없다. 복사하면 저작권 고지를 유지한다. 모든 줄 범위는 SHA `dfe2d45`이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/types/index.ts:546-673` `GradingResult`, `isFiniteNumberRecord`, `hasValidGradingResultFields`, `isGradingResult` | 결과 필드와 사용자 코드가 돌려준 결과의 유효성 판정(순환·빈 칸 거부) | R-35, R-38, R-39 |
| C-02 | `src/types/index.ts:675-770` `BaseAssertionTypesSchema`, `SpecialAssertionTypes`, `AssertionTypeSchema` | 68개 키 목록, 특수 타입, `not-` 변형, `z.custom` 꼬리 | R-01, R-02, R-05 |
| C-03 | `src/types/index.ts:772-877` `AssertionSetSchema`, `AssertionSchema`, `AssertionValueFunctionContext`, `AssertionParams` | 어서션·세트 필드, 컨텍스트·핸들러 입력 | R-03, R-10 |
| C-04 | `src/types/index.ts:925-943,966-977,1005-1006` `ScoringFunction`, `TestCaseSchema`의 `assert`·`assertScoringFunction`·`threshold` | 스코어링 함수 시그니처, 테스트 수준 키 | R-21, R-23 |
| C-05 | `src/assertions/index.ts:125-137,229-322` `MODEL_GRADED_ASSERTION_TYPES`, `ASSERTION_HANDLERS` | 등록부 전체와 모델 채점 집합 | R-01, R-26 |
| C-06 | `src/assertions/index.ts:332-372` `renderMetricName`, `isAssertionInverse`, `getAssertionBaseType` | `metric` 렌더, `not-` 판별 | R-03, R-17 |
| C-07 | `src/assertions/index.ts:412-686` `runAssertionInternal`(변환 444-450, 컨텍스트 452-461, 값 해석 481-611, 호출 문맥·params 613-652, 디스패치 654-685) | 한 어서션의 처리 순서 | R-05~R-11 |
| C-08 | `src/assertions/index.ts:757-912` `runAssertions` | 펼치기, 동시성, 건너뛰기, 집계 호출 | R-12~R-15 |
| C-09 | `src/assertions/assertionsResult.ts:205-456` `normalizeWeightedScore`, `AssertionsResult`(`noAssertsResult`, `addResult`, `testResult`) | 가중 평균, 임계값, namedScores, 평탄화, 스코어링 함수, 유한성 검사 | R-12, R-16~R-22 |
| C-10 | `src/assertions/assertionsResult.ts:11-203` `DEFAULT_TOKENS_USED`, `normalizeAssertionTokenUsage`, `accumulateNormalizedAssertionTokenUsage`, `cloneAssertionTokenUsage`, `mergeScoringMetadata`, `mergeScoringTokenUsage`, `mergeMetadata` | 토큰 합산·캐시 표시·스코어링 결과 병합 | R-18, R-21 |
| C-11 | `src/assertions/utils.ts:12-93` `getFinalTest`, `loadFromJavaScriptFile`, `processFileReference`, `coerceString` | 테스트 복사·grader 덮어쓰기, JS 함수 찾기, 값 파일 읽기, 출력 문자열화 | R-08, R-10 |
| C-12 | `src/assertions/contains.ts:1-75`, `src/validation/parseCommaSeparatedValues.ts:1-83`, `src/assertions/normalize.ts:1-10` | contains 계열 전체, 쉼표 파서, 유니코드 정규화 | R-27 |
| C-13 | `src/assertions/equals.ts:1-43`, `regex.ts:1-33`, `startsWith.ts:1-25` | 핵심 결정적 핸들러 3종 | R-28 |
| C-14 | `src/assertions/json.ts:1-113`, `src/util/json.ts:18-29,249-416` `getAjv`, `findJsonObjectEnd`, `extractJsonObjects` | JSON 검사·스키마 검증, 본문에서 JSON 객체 추출 | R-28 |
| C-15 | `src/assertions/cost.ts:1-28`, `latency.ts:1-27`, `levenshtein.ts:1-29`, `finishReason.ts:1-37`, `perplexity.ts:1-55`, `wordCount.ts:1-97`, `guardrails.ts:1-41` | 응답 필드·성능·단어 수 핸들러 | R-29~R-31 |
| C-16 | `src/assertions/bleu.ts:175-203` `handleBleuScore`, `src/assertions/rouge.ts:1-65` | 점수형 지표의 임계값·반전 규약(계산 본문은 범위 밖) | R-31 |
| C-17 | `src/assertions/javascript.ts:21-157` `assertionParser`, `insertReturnAfterSemicolon`, `findLastStatementSemicolon`, `buildFunctionBody` | 한 줄 코드의 `return` 삽입 | R-34 |
| C-18 | `src/assertions/javascript.ts:164-314` `validateResult`, `serializeFunctionAssertion`, `normalizeResultAssertion`, `normalizeJavascriptAssertionResult`, `handleJavascript` | JS 어서션 실행·검증·정규화·오류 | R-34~R-36 |
| C-19 | `src/assertions/scriptBody.ts:1-18`, `python.ts:1-46`, `ruby.ts:1-47` | 인라인 코드 감싸기, Python·Ruby 핸들러 | R-37 |
| C-20 | `src/assertions/scriptResultNormalization.ts:1-274`, `src/util/caseMapping.ts:1-39` | 반환 정규화·임계값·반전·snake_case 매핑·옛 형태 변환 | R-35, R-38, R-39 |
| C-21 | `src/assertions/webhook.ts:1-70` | webhook 요청·응답 규약 | R-40 |
| C-22 | `src/assertions/llmRubric.ts:1-42`, `factuality.ts:1-34`, `geval.ts:1-116`, `similar.ts:1-108`, `ragDefaults.ts:1-49`, `classifier.ts`, `searchRubric.ts`, `agentRubric.ts`, `pi.ts`, `src/matchers/shared.ts:35-71` `fail`, `graderFail`, `invertScore` | 모델 채점 핸들러의 호출 경계·반전·grader 실패 처리 | R-45~R-47 |
| C-23 | `src/matchers/rubric.ts:837-958` `deriveVerdictFromGrader`, `runJsonGradingPrompt` | grader JSON → `{pass, score, reason}`·결과 `metadata` 형태 | R-46, R-47 |
| C-24 | `src/matchers/comparison.ts:16-92` `matchesSelectBest`, `src/assertions/index.ts:914-943` `runCompareAssertion` | `select-best` 호출과 열별 결과 | R-50 |
| C-25 | `src/matchers/comparison.ts:94-209` `selectMaxScore` | `max-score` 규칙 전체 | R-51 |
| C-26 | `src/evaluator.ts:624-684` `applyGradingResult`, `applyGradingError`; `:1532-1697` `gradeRunEvalResponse`, `transformRunEvalResponse`; `:3044-3085` `prepareTestCaseForEval` | 변환 ①②, `runAssertions` 호출, 행 반영, 기본 어서션 병합 | R-06, R-23~R-25 |
| C-27 | `src/evaluator.ts:2310-2375` `mergeSelectBestGradingResult`, `mergeMaxScoreGradingResult`; `:4962-5030` `processComparisonAssertions`; `:5112-5261` `processSelectBestAssertionForTest`; `:5303-5372` `processMaxScoreAssertionForTest`; `:5503-5540` | 비교 단계의 순서와 행 병합 | R-49~R-52 |
| C-28 | `src/util/transform.ts:55-196,231-290` `getTransformFunction`, `transform`; `src/util/safeMode.ts:1-30` | 변환 함수 해석(인라인·파일)·반환 검증·오류 포장, safe mode | R-06, R-34 |
| C-29 | `src/assertions/validateAssertions.ts:1-124` | 설정 로드 시 어서션 검증 | R-05 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 어서션 외 모든 입력은 최소 가짜 값이다. 모델 채점 사례의 grader는 "고정 JSON을 돌려주는 대체 provider"를 가정하며, 이 사례들은 반전·집계 규칙만 검증하고 실제 grader 품질·프롬프트는 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-12, R-16, R-19 | `assert: [{type:'contains', value:'4'}, {type:'regex', value:'^The'}]`, 출력 `The answer is 4` | `pass:true, score:1, reason:'All assertions passed'`, `componentResults` 2개. `assert` 없음이면 `{pass:true, score:1, reason:'No assertions'}` |
| T-02 | R-16, R-19 | `threshold:0.5`, `[equals 'Hello world' weight 2, contains 'world' weight 1]`, 출력 `Goodbye world` | `score = (0*2+1*1)/3 ≈ 0.333`, `pass:false`, `reason:'Aggregate score 0.33 < 0.5 threshold'`. `threshold:0.2`이면 `pass:true`, `reason:'Aggregate score 0.33 ≥ 0.2 threshold'` |
| T-03 | R-03, R-04, R-27 | `[{type:'not-contains', value:'error'}]`, 출력 `ok` / 출력 `an error` | 각각 `pass:true, score:1` / `pass:false, score:0, reason:'Expected output to not contain "error"'` |
| T-04 | R-11, R-17 | `[{contains 'x', weight:0, metric:'has_x'}, {contains 'a'}]`, 출력 `a` | 첫 어서션은 원래 실패지만 `pass`가 강제로 true, 총점 `(0*0+1*1)/(0+1)=1`, `pass:true`, `namedScores:{has_x:0}`, `namedScoreWeights:{has_x:1}` |
| T-05 | R-17 | `[{contains 'a', metric:'acc', weight:2}, {contains 'b', metric:'acc'}]`, 출력 `a` | `namedScores.acc = (1*2+0*1)/3 ≈ 0.667`, `namedScoreWeights.acc = 3`, `score ≈ 0.667`, `pass:false`(`b` 실패) |
| T-06 | R-15, R-20 | `[{type:'assert-set', threshold:0.5, assert:[{contains 'a'},{contains 'b'}]}]`, 출력 `a` | 세트 `score 0.5 ≥ 0.5`로 통과, 전체 `score 0.5, pass:true`, `componentResults` 3개(세트 결과 + 하위 2개), 세트 결과 `metadata.assertionSet.assertionCount === 2` |
| T-07 | R-06 | provider 원출력 `hi`, `provider.transform:'output + "!"'`, `test.options.transform:'output + "?"'`, 어서션 `{type:'equals', value:'hi!?#', transform:'output + "#"'}` | 어서션이 보는 출력 `hi!?#`로 통과. `providerResponse.output`은 `hi!?`, `providerTransformedOutput`은 `hi!` |
| T-08 | R-34 | `javascript` 한 줄 `output.length > 3`, 출력 `abcd` / `const n = JSON.parse(output).n; n > 1`, 출력 `{"n":2}` | 둘 다 `pass:true, score:1` |
| T-09 | R-35 | `javascript` `output.length / 10`, `threshold:0.5`, 출력 `abcdef` / 같은 어서션을 `not-javascript`로 | `pass:true, score:0.6` / `pass:false, score:0.6`(반전해도 점수 불변), reason `Custom function returned true` 뒤에 인라인 코드 줄 |
| T-10 | R-35, R-17 | `javascript` `({pass:true, score:0.4, reason:'meh', namedScores:{tone:0.4}})` | 결과가 그대로 `pass:true, score:0.4, reason:'meh'`; 한 어서션이면 행 `namedScores:{tone:0.4}` |
| T-11 | R-38 | `file://g.py`, `get_assert`가 `{"pass_": True, "score": 0.7, "reason": "ok", "named_scores": {"a": 1}}` 반환, `threshold:0.8` / `threshold` 없음 / 후자를 `not-python`으로 | `pass:false, reason:'Python score 0.7 is less than threshold 0.8: ok', namedScores:{a:1}` / `pass:true` / `pass:false, reason:'ok'` |
| T-12 | R-08 | 같은 `g.py`에서 예외가 남 | 던지지 않고 `{pass:false, score:0, reason:<예외 메시지>}`. 반면 `file://x.js`가 없는 경로면 `runAssertion`이 던져 행이 ERROR |
| T-13 | R-40 | webhook이 `{"pass":true}` / `{"pass":true}`를 `not-webhook`으로 / 응답 `{"pass":"yes"}` / 비 2xx 응답 또는 연결 실패 | `pass:true, score:1` / `pass:false, score:0` / `pass:false, reason`에 `Webhook error: Invariant failed: Webhook response must be a JSON object with a boolean "pass" property` / `pass:false, score:0`, reason이 `Webhook error: `로 시작(비 2xx가 응답으로 돌아온 경우 `Webhook response status: <코드>`) |
| T-14 | R-05, R-24 | `type:'foo'` | `Unknown assertion type: foo`가 던져져 그 행은 `failureReason:ERROR, success:false, score:0, namedScores:{}` |
| T-15 | R-29 | `cost` `threshold:0.01`, 응답 `cost:0.02` / `cost` 없음 / `threshold`·`metric:'c'`·`weight:0`, 응답 `cost:0.02` | `pass:false, reason:'Cost 0.020 is greater than threshold 0.01'` / 던짐(`…does not support providers that do not return cost`) / `pass:true, score:0.02`, `namedScores:{c:0.02}` |
| T-16 | R-46 | `llm-rubric`을 grader 대체물이 `{"pass":true,"score":1,"reason":"ok"}`로 응답: 비반전 / `not-llm-rubric` / grader가 오류 응답: 비반전, `not-` | `pass:true, score:1` / `pass:false, score:0` / 둘 다 `pass:false, score:0, metadata.graderError:true`(반전해도 통과 안 됨) |
| T-17 | R-21 | `[{equals 'a', metric:'x'}, {contains 'b', metric:'y'}]`, 출력 `a`, 스코어링 함수 `ns => ({pass: ns.x>0 && ns.y>0, score:0.5, reason:'both needed'})` / 함수가 예외 | `pass:false, score:0.5, reason:'both needed'` / `pass:false, score:0, reason:'Scoring function error: <메시지>'` |
| T-18 | R-19 | 테스트 `threshold:0`, 모든 어서션 실패(점수 0) | 점수 0 ≥ 0이므로 `pass:true, reason:'Aggregate score 0.00 ≥ 0 threshold'`. 점수가 음수이면 실패 |
| T-19 | R-49, R-51, R-52 | 같은 테스트의 두 열 A·B, 어서션 `[contains, regex, {type:'max-score'}]`, A는 둘 다 통과(점수 1,1), B는 `contains`만 통과(1,0) | A: 평균 1, `pass:true, score:1`(행 기존 상태 유지). B: 평균 0.5, 비교 결과 `pass:false, score:0, reason:'Not selected (score: 0.500, max: 1.000)'`이고 행은 `success:false, score:0, failureReason:ASSERT`. 열이 1개면 `max-score`는 `max-score assertion must have at least two outputs to compare between`을 던지고 행 오류가 아닌 예외로 전파된다 |
| T-20 | R-44 | `not-skill-used` `value:'x'`, `providerResponse.metadata`에 `skillCalls` 없음(비에이전트 provider) | skill-calls-metadata R-13·R-17대로 `pass:true`(`(none)`) |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]

문서(코드 주석·`site/docs`)와 구현의 차이:

- `src/assertions/index.ts:715-718` `runAssertions` JSDoc은 "Nested assertion-sets with logical operators"를 말하지만 구현에는 논리 연산자가 없다. 집계는 가중 평균과 `threshold`뿐이고 `assert-set`은 한 단계다(R-15, R-19).
- `src/types/index.ts:783-785` `AssertionSetSchema.config` 주석은 "세트의 모든 어서션에 전달"이라 하지만 `runAssertions`(`index.ts:789-812`)는 세트의 `config`를 하위 어서션에 합치지 않는다(`src/`에서 `assert-set` 처리 위치를 검색해 확인: `evaluator.ts`, `evaluate.ts`, `share.ts`, `validateAssertions.ts`, `assertionsResult.ts` — 어디에도 세트 `config` 전파가 없다).
- `site/docs/configuration/expected-outputs/index.md`는 `max-score`를 "Model-assisted" 표에 올리지만 구현(`selectMaxScore`)은 모델을 부르지 않고 이미 계산된 결과를 합산한다(R-51).
- 개요(overview) 지도는 `ASSERTION_HANDLERS`를 `src/assertions/index.ts:297`이라 적었으나 이 SHA에서는 `:229-322`이다. "약 68개 키"는 정확히 68개다(R-01). 개요 지도의 `skill.ts` 설명과 별개로 이 스펙은 `skill.ts` 본문을 읽지 않았다(R-44는 선행 스펙을 따름).
- 문서의 `threshold` 설명("`similar`·`cost`·`javascript`·`python`·`ruby` 등 일부 타입에만 적용")보다 실제로는 `levenshtein`·`bleu`·`rouge`·`g-eval`·`perplexity`·`latency`·모델 채점 계열 등 다수가 `threshold`를 쓴다(R-29~R-31, R-47). 어서션 `threshold`는 타입별 의미라 문서가 모두를 열거하지 않는 것으로 보인다(추론).

| R-ID / T-ID | 근거 (repo@dfe2d45 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-02 `types/index.ts:675-746`, C-05 `index.ts:229-322`; `index.ts:270-291` meteor 지연 로드; `similar.ts:33-51`(접미사); `rouge.ts:35-45` | 키 집합은 두 목록의 정렬 diff로 비교(68=68, 같음) |
| R-02 | `index.ts:853-856`; `types/index.ts:755-757` | 읽음 |
| R-03 | C-06 `index.ts:359-372`, `:641` | 읽음 |
| R-04 | `contains.ts:45`, `equals.ts:15-30`, `bleu.ts:175-203`, `rouge.ts:35-65`, `perplexity.ts:44-49`, `webhook.ts:53-54`, `scriptResultNormalization.ts:142-189`, `ragDefaults.ts:25-49`, `matchers/shared.ts:69-71`, `geval.ts:99-115`, `classifier.ts` 반전부; `pi.ts:5-15`; `src/assertions/*.ts`에서 `inverse` 미사용 파일 검색(결과: `pi.ts`, `trace*.ts` 외 헬퍼) | 읽음. 모든 핸들러를 읽지는 않아 "세 가지"는 읽은 핸들러 기준(xml·html·sql·도구 호출·gleu·meteor는 미확인) |
| R-05 | `index.ts:442,659-685`, `types/index.ts:763-768`, `validateAssertions.ts:36-124`; `util/config/load.ts:1325`(호출 위치) | `z.custom` 동작은 추론 |
| R-06 | C-26 `evaluator.ts:1646-1697`, `index.ts:444-450`, C-28 `util/transform.ts:231-290`; `refusal.ts:7-12`(provider.transform 참조) | 읽음. T-07은 코드 논리에서 도출 |
| R-07 | `index.ts:452-479`, `:437` | 읽음. 트레이스 로드는 범위 밖 |
| R-08 | C-07 `index.ts:481-566`, C-11 `utils.ts:54-86`, `providers/packageParser.ts:13-30` | 읽음. 첫 `:` 분리는 코드 그대로(Windows 경로 영향은 추론) |
| R-09 | `index.ts:568-611` | 읽음 |
| R-10 | `index.ts:613-652`, `utils.ts:12-52` | 읽음 |
| R-11 | `index.ts:659-683` | 읽음 |
| R-12 | `assertionsResult.ts:214-221`, `index.ts:776-778` | 읽음 |
| R-13 | `index.ts:826-835,880-894` | 읽음. 동시 실행 순서 효과는 추론 |
| R-14 | `index.ts:853-856`, `assertionsResult.ts:319-323,340` | 읽음 |
| R-15 | `index.ts:786-812,896-909`, `assertionsResult.ts:27-35,374-381` | 읽음 |
| R-16 | `assertionsResult.ts:252-312` | 읽음 |
| R-17 | `assertionsResult.ts:274-296,354-359`, `index.ts:332-351,875,906` | 읽음. 테스트: `test/assertions/assertionsResult.test.ts`에 같은 이름의 사례들이 있음(파일명만 확인) |
| R-18 | C-10 `assertionsResult.ts:11-203,298-301,362-364` | 식 전체를 따라가지는 않고 구조만 읽음 |
| R-19 | `assertionsResult.ts:314-337` | 읽음 |
| R-20 | `assertionsResult.ts:339-382` | 읽음 |
| R-21 | `assertionsResult.ts:384-414`; `evaluator.ts:3075-3085`; docs `index.md` "Custom scoring functions" | 읽음 |
| R-22 | `assertionsResult.ts:416-452` | 읽음 |
| R-23 | C-26 `evaluator.ts:3044-3085` | 읽음 |
| R-24 | `evaluator.ts:624-684,1532-1644,1826-1990`(grading이 `runEvalInternal`의 `try`/`catch` 안) | 읽음. 중단 신호 분기는 이름만 |
| R-25 | `evaluator.ts:1580-1632` | 읽음 |
| R-26 | `index.ts:125-137`, `evaluator.ts:537-560`, `index.ts:830-835` | 조건만 읽음. 스케줄은 eval-run 소관 |
| R-27 | C-12 | 읽음 |
| R-28 | C-13, C-14 | 읽음. `extractJsonObjects` 세부(YAML 허용 변환 등)는 코드 그대로 인용 |
| R-29 | C-15 `cost.ts`, `latency.ts` | 읽음 |
| R-30 | C-15 `finishReason.ts`, `perplexity.ts`, `guardrails.ts` | 읽음 |
| R-31 | C-15 `levenshtein.ts`, `wordCount.ts`, C-16 | 읽음. bleu·rouge 계산 본문은 범위 밖 |
| R-32 | `javascript.ts:239-314`, `python.ts`, `ruby.ts`, `index.ts:501,507,525` | 읽음 |
| R-33 | `index.ts:485-554`, `utils.ts:54-72` | 읽음 |
| R-34 | C-17, C-18 `javascript.ts:21-157,239-314`, C-28 `safeMode.ts` | 읽음 |
| R-35 | `javascript.ts:164-237`, `scriptResultNormalization.ts:142-189` | 읽음 |
| R-36 | `index.ts:500-502`, `javascript.ts:289-313` | 읽음 |
| R-37 | C-19, `index.ts:503-537` | 읽음. 일회성 프로세스 세부는 script-bridges(R-17·R-23) |
| R-38 | C-20 `scriptResultNormalization.ts:191-274`, `caseMapping.ts` | 읽음. T-11은 script-bridges T-11과 같은 사례 |
| R-39 | C-01 `types/index.ts:603-673`, `scriptResultNormalization.ts:21-129` | 읽음 |
| R-40 | C-21 | 읽음. 재시도 조건 미탐색(`util/fetch/index.ts:783-808`은 인자 기본값만) |
| R-41 | `javascript.ts:239-313`, `safeMode.ts:12-18`, `assertions/AGENTS.md` | 주석·지침 읽음 |
| R-42 | `assertionsResult.ts:281-296,340-352` | 읽음 |
| R-43 | `python/pythonUtils.ts:246-270` | 직렬화 호출만 읽음 |
| R-44 | `index.ts:305`, 선행 스펙 R-14~R-21 | `skill.ts` 본문은 읽지 않음(선행 스펙이 읽음) |
| R-45 | C-22 `llmRubric.ts`, `factuality.ts`, `geval.ts`, `similar.ts`, `classifier.ts`, `searchRubric.ts`, `agentRubric.ts` | 핸들러만 읽음. 매처 본문은 `llmGrading.ts:181-250`, `rubric.ts:876-958`만 |
| R-46 | `matchers/shared.ts:35-71`, `ragDefaults.ts:25-49`, `llmGrading.ts:230-262,451-452`, `rubric.ts:925-958` | 읽음 |
| R-47 | `geval.ts:15-116`, `similar.ts:21-108`, C-23 `rubric.ts:837-874`; docs `index.md`(RAG 기본 임계 0.5) | `llm-rubric` 판정식은 코드, RAG 기본 임계는 문서(미확인) |
| R-48 | `geval.ts`, `assertionsResult.ts:11-203` | 읽음. 비결정성은 추론 |
| R-49 | C-27 `evaluator.ts:4962-5030,5112-5140,5303-5372,5373-5410`; `matchers/comparison.ts:25-28,102-105` | 읽음 |
| R-50 | `evaluator.ts:5167-5226`, C-24 | 읽음 |
| R-51 | C-25 | 읽음. 원본 테스트 `test/assertions/max-score.test.ts` 존재(열지 않음) |
| R-52 | `evaluator.ts:2310-2375,5503-5540,4127-4150` | 읽음. T-19는 코드 논리에서 도출 |
| T-01~T-20 | 위 R-ID의 근거 | 모두 코드 논리에서 도출하고 실행하지 않았다. T-02는 docs `index.md`의 예(0.33 < 0.5)와 같은 결과 |

### 2.2 코드 읽는 순서 [선택]
`types/index.ts:546-877`(결과·어서션·params 타입) → `assertions/index.ts:229-372`(등록부, 반전) → `index.ts:412-686`(한 어서션) → `index.ts:757-912`(여러 어서션) → `assertionsResult.ts:252-455`(집계) → 대표 핸들러 `contains.ts`·`cost.ts` → 코드 계열 `javascript.ts`·`scriptResultNormalization.ts` → `evaluator.ts:624-684,1532-1697,3044-3085`(연결) → 비교 `matchers/comparison.ts:94-209`와 `evaluator.ts:5112-5372`. 원본 구현 전략: 핸들러는 순수 함수이고 반전·점수 규약은 핸들러 안에서 처리, 집계는 한 클래스(`AssertionsResult`)에 모은다. 어서션 간 순서 의존이 없어 동시에 돌리고 결과를 위치 인덱스로 합친다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다.

## 적용 메모 [선택]

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01, R-04 | 가져올 최소 집합: 핸들러 계약 `(params) → {pass, score, reason, namedScores?, componentResults?}`, 집계기(R-16~R-20), 결정적 핸들러 몇 개(`contains`·`regex`·`equals`·`is-json`), 코드 핸들러(`javascript` 파일, `python` 파일), 모델 채점 핸들러 형태(`llm-rubric`). 68키 등록부를 그대로 옮기지 않는다. | 스킬 평가는 "결정적 규칙 + 맞춤 코드 + 모델 채점" 세 종류의 조합과 점수 집계가 핵심이다 | 반전(`not-`)을 지원한다면 R-04의 세 규약을 하나로 통일(pass 반전, 점수형은 `clamp(1 - score)`, grader 실패는 반전하지 않음)할 수 있다. 원본은 핸들러마다 다르다 |
| R-16, R-17, R-42 | 모델 적합도 기록에는 `metric`별 가중 평균(`namedScores`)과 `namedScoreWeights`를 그대로 쓰고, Python `named_scores`로 항목별 점수를 한 어서션에서 낸다. 측정만 하고 통과 여부는 안 보는 항목은 `weight:0` + `metric`으로 둔다(비용 `cost`도 이 형태) | 원본이 이미 "측정 전용"과 "항목 점수"를 같은 구조로 지원한다 | 바뀌는 것 없음 |
| R-19 | `threshold`를 한 곳(테스트 수준)으로 줄이는 것을 고려한다. 어서션 `threshold`는 타입별 의미, 세트·테스트 `threshold`는 점수 임계로 의미가 겹쳐 혼동하기 쉽다 | 규칙 수를 줄여 재구현·설명을 단순하게 | 세트 `threshold`를 빼면 R-15의 세트 임계 처리와 T-06이 바뀐다 |
| R-34, R-41 | 인라인 JS(`new Function`)·인라인 Python은 가져오지 않고 파일 참조(`file://x.js`, `file://x.py:get_assert`)만 지원한다 | 인라인 코드는 호스트 프로세스에서 임의 코드를 실행하고(R-41), 스킬 평가에서 쓸 이유가 약하다 | R-34·R-37의 인라인 경로와 T-08 제거 |
| R-44, R-49, R-51 | 여러 모델·스킬 버전을 같은 케이스로 돌릴 때 열 비교는 모델을 부르지 않는 `max-score`(R-51)를 우선 가져온다. 단 가중치는 어서션 type별(`weights[type]`)이라 같은 type의 어서션을 구분하려면 `metric`별 가중치로 바꾸는 것을 고려한다 | 원본은 type 키라 `llm-rubric` 둘을 구분하지 못한다 | R-51의 `weights` 키를 `metric`으로 바꾸면 사례 T-19와 가중치 규칙이 바뀐다 |
| R-45~R-48 | 모델 채점 호출 형태는 원본과 같이 "grader provider + rubric → `{pass, score, reason}`"로 두고 grader 실패를 `graderError` 표시로 구분해 반전·집계에 섞이지 않게 한다 | grader 오류를 점수 0으로 기록하면 모델 간 비교가 왜곡된다 | 바뀌는 것 없음 |
