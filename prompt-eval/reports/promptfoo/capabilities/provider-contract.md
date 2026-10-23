---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/types/providers.ts
  - src/contracts/providers.ts
  - src/contracts/shared.ts
  - src/contracts/prompts.ts
  - src/validators/providers.ts
  - src/providers/registryTypes.ts
  - src/providers/registry.ts
  - src/providers/index.ts
  - src/providers/families/aws.ts
  - src/providers/families/compatible.ts
  - src/providers/families/google.ts
  - src/providers/scriptBasedProvider.ts
  - src/providers/packageParser.ts
  - src/providers/echo.ts
  - src/providers/anthropic/generic.ts
  - src/providers/anthropic/messages.ts
  - src/redteam/providers/registry.ts
  - src/util/providerRef.ts
  - src/util/render.ts
  - src/util/cloud.ts
  - src/envOverrides.ts
  - src/envars.ts
  - src/esm.ts
  - src/validation/fileExtensions.ts
  - src/util/providerResponse.ts
  - src/evaluator.ts
  - src/matchers/providers.ts
  - src/util/config/load.ts
  - src/evaluate.ts
  - src/scheduler/rateLimitRegistry.ts
  - src/providers/providerRegistry.ts
  - src/providers/shared.ts
  - src/util/tokenUsageUtils.ts
  - src/assertions/moderation.ts
  - src/presentation/evalResults.ts
  - src/constants.ts
  - test/providers/index.test.ts
  - site/docs/providers/custom-api.md
depends: []
status: ready
reimplementation: 미실행
---

# 프로바이더 계약 (ApiProvider·ProviderResponse·접두어 디스패치)

> 설정의 provider 항목(문자열 `openai:...`·`file://...`, 객체, 맵, 함수, 이미 만든 인스턴스)을 받아 `id()`와 `callApi(prompt, context, options) → ProviderResponse`를 가진 `ApiProvider`로 바꾸는 규칙과, 그 `ApiProvider`·응답이 모든 소비자(평가기·채점기·최적화·생성·레드팀)와 맺는 공유 계약.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

1. 설정의 `providers`(또는 Node API의 `testSuite.providers`)가 `loadApiProviders(providers, {env, basePath})`로 들어온다. 호출자는 설정 로더(`src/util/config/load.ts:1208`)와 Node API(`src/evaluate.ts:340`)다. 채점기·합성·검증·서버 라우트 등은 문자열 하나를 `loadApiProvider(path, {options, basePath, env})`로 직접 부른다(R-31).
2. 배열의 각 항목을 `normalizeProviderRef`로 분류한다: `file`(YAML/JSON 설정 파일), `named`(문자열), `function`, `options`(`{id, ...}`), `map`(`{ "<id>": {...} }`), `unknown`. 이미 `ApiProvider`인 항목은 손대지 않고 그대로 통과한다(R-30, R-31).
3. 문자열 경로는 `loadApiProvider`가 처리한다. suite env와 provider별 env를 합치고, 경로·`config`·`id`·`label`의 `{{ env.X }}`만 렌더링하며, `create`에 줄 `providerOptions = {id, config(+basePath), env}`를 만든다(R-13, R-14).
4. 경로가 `promptfoo://provider/`로 시작하면 클라우드 target을 가져와 병합한 뒤 다시 3번으로 간다. `file://*.yaml|yml|json`이면 파일을 읽어 그 안의 `id`로 다시 3번으로 간다(R-20, R-21).
5. 그 밖에는 `getProviderFactories(path)`가 돌려준 `ProviderFactory[]`를 순서대로 훑어 `test(path)`가 처음 true인 factory의 `create`만 호출한다. 맞는 것이 없으면 `Could not identify provider` 오류다(R-10~R-12).
6. 만든 인스턴스에 `options`의 `transform`·`delay`·`inputs`·`prompts`를 덮어쓰고 `label`을 채운다(R-15).
7. 평가기는 렌더된 prompt 문자열로 `provider.callApi(prompt, context, options)`를 부르고, 돌려받은 `ProviderResponse`의 `error`·`output`·`cost`·`tokenUsage`·`latencyMs`·`metadata`를 결과 행으로 옮긴다(R-02~R-06).

### 1.2 범위·통합 지점 [필수]
- 제공: ① `ApiProvider`·`ProviderResponse`·`TokenUsage`·`ProviderOptions` 타입과 소비 규칙. ② provider 항목 → `ApiProvider` 변환(`loadApiProvider`·`loadApiProviders`·`resolveProvider`·`normalizeProviderRef`). ③ `ProviderFactory`·`ProviderFamily` 등록부와 선행 순서 규칙, 대표 접두어 규칙(`echo`, `anthropic:`, `openai:`, `file://` JS·스크립트, `package:`, 레드팀 접두어).
- 제외: 개별 provider(약 100개 factory 뒤의 클래스) 내부 호출·재시도·캐시, 에이전트 SDK provider(별도 스펙), 스크립트 브리지 프로토콜(Python·Ruby·Go 워커), `http`·`websocket`·`browser`·MCP 내부, 스케줄러 알고리즘, 클라우드 target 조회 내부(`getProviderFromCloud`), 설정 파일 전체 스키마(config-schema 스펙). 이유: 각각 별도 스펙이거나 이 계약의 소비자 쪽 동작이다. 레드팀 registry는 R-19에서 접두어와 오류 포장만 다룬다.
- 외부 의존·선행 계약: 선행 스펙 없음. 호출자는 `cliState`(`withEnv`·`withBasePath`로 비동기 범위 안에 env와 basePath를 싣는 AsyncLocalStorage 저장소)와 `logger`가 있다고 가정한다. 문자열 `{{ env.X }}` 렌더링에는 Nunjucks 엔진(`getNunjucksEngine`)이 필요하다(R-13의 규칙만 쓰면 되고 엔진 자체는 표준 템플릿 라이브러리로 간주).
- 소유 상태·부작용: 이 기능은 영속 상태가 없다. `loadApiProvider`는 새 인스턴스를 만들고 `options`의 값을 그 인스턴스 필드에 쓴다. 호출 범위 안에서만 `cliState`의 env·basePath를 바꾼다. 인스턴스가 가진 장수 자원(프로세스·브라우저·연결)은 `cleanup`·`cleanupAfterEvaluation`으로 정리한다(R-08).

### 1.3 인터페이스와 데이터 의미 [필수]

타입은 TypeScript 원문(C-01~C-06)이 가장 짧고 정확하므로 여기서는 의미·경계만 쓴다.

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `ApiProvider.id()` | `() → string` | 필수. 결과 행·캐시 키·필터·로그의 식별자. 대부분의 내장 구현은 생성자에 `options.id`가 있으면 그 값을 돌려주도록 덮어쓴다(`EchoProvider`, `AnthropicGenericProvider`, OpenAI 공통). 없으면 구현이 정한 정규형(예: `anthropic:<model>`) |
| `ApiProvider.callApi` | `(prompt: string, context?: CallApiContextParams, options?: CallApiOptionsParams) → Promise<ProviderResponse>` | 필수. `prompt`는 이미 렌더된 문자열. 실패는 `{error}`를 돌려주는 것이 관례이고 throw도 허용된다(R-03) |
| `ApiProvider.label` | `string?` | 사람이 읽는 이름. 평가기 일부 경로가 `label \|\| id()`로 표시에 쓴다(`src/evaluator.ts:3937`). 생성 후 채워진다(R-15) |
| `ApiProvider.config` | `any?` | provider 설정 원문. 소비자(평가기 등)가 읽을 수 있다 |
| `ApiProvider.prompts` / `transform` / `inputs` / `delay` | `string[]?` / `string \| function?` / `Inputs?` / `number(ms)?` | 설정의 `ProviderOptions` 값. `loadApiProvider`가 생성 후 덮어쓴다(R-15). `prompts`는 이 provider가 돌 prompt 라벨 선택자이고 소비는 평가 실행 스펙 몫이다(`src/evaluator.ts:2396`) |
| `handlesOwnDelay`, `handlesOwnRetries` | `boolean?` | 평가기의 사후 지연·스케줄러 재시도를 끄는 신호(R-08) |
| `cleanup()`, `cleanupAfterEvaluation({reason})` | `() → void\|Promise`, `(ctx) → void\|Promise` | 장수 자원 정리 훅(R-08) |
| `callEmbeddingApi`, `callSimilarityApi`, `callClassificationApi`, `callModerationApi` | 모두 선택. `ProviderEmbeddingResponse` 등 반환 | 채점기가 provider **속성 존재 여부**로 용도를 판별한다(R-07) |
| 기타 선택 필드 | `getSessionId`, `getAudioInputFormat`, `toJSON`, `supportsEmbeddingCancellation` | 선언만 확인. 소비처는 개별 기능 몫 |
| `ProviderOptions` | `{id?, label?, config?, prompts?, transform?, delay?, env?, inputs?}` | 설정의 객체형 provider 항목. 이 8개 키 집합이 `normalizeProviderRef`의 맵 판별에 쓰인다(R-30) |
| `CallApiContextParams` | `{vars, prompt, filters?, originalProvider?, test?, logger?, getCache?, repeatIndex?, testIdx?, bustCache?, evaluationId?, testCaseId?, traceparent?, tracestate?, debug?, isGrading?, promptIdx?}` | 평가기가 만드는 호출 문맥(R-02). `vars`는 테스트 변수, `prompt`는 `Prompt` 객체(raw·label·config) |
| `CallApiOptionsParams` | `{abortSignal?, includeLogProbs?, onResponseHeaders?}` | 취소 신호와 스케줄러용 훅. 평가기는 둘 다 없으면 `undefined`를 넘긴다(R-02) |
| `ProviderResponse` | `{output?, error?, tokenUsage?, cost?, incurredCost?, cached?, latencyMs?, metadata?, prompt?, raw?, ...}` | R-03~R-06. 전체 필드 목록은 C-04 |
| `TokenUsage` | `{prompt?, completion?, cached?, total?, numRequests?, completionDetails?, attacker?, assertions?, generation?, incurredTokenUsage?}` | 모두 선택 숫자. `completionDetails`는 `{reasoning, acceptedPrediction, rejectedPrediction, cacheReadInputTokens, cacheCreationInputTokens}`(C-05). 합계가 없으면 집계기가 `prompt+completion`을 쓴다(R-05) |
| `ProviderFactory` | `{test(path) → bool, create(path, providerOptions, context) → Promise<ApiProvider>}` | R-10. `context = {options?, basePath?, env?}`(`LoadApiProviderContext`) |
| `ProviderFamily` | `{canHandle(path) → bool, factories() → Promise<ProviderFactory[]>}` | 지연 로드 묶음. `canHandle`은 로드 게이트일 뿐 디스패치는 각 factory의 `test`(R-11) |
| `loadApiProvider` | `(path: string, context?) → Promise<ApiProvider>` | 문자열 하나만 받는다. 객체·함수는 호출자가 `normalizeProviderRef`로 분류해 `path`와 `context.options`로 나눠 부른다 |
| `loadApiProviders` | `(providers: ProvidersConfig, {basePath?, env?}) → Promise<ApiProvider[]>` | 입력 순서 유지, 파일 하나가 여러 provider면 제자리에서 펼친다(R-31) |
| `resolveProvider` | `(provider: string\|object\|function, resolvedProviders: map, context) → Promise<ApiProvider>` | 단일 항목 해석. 문자열이 이미 만든 provider 맵에 있으면 재사용(R-33) |
| `getProviderIds`, `resolveProviderConfigs` | `(providers) → string[]`, `(providers, {basePath}) → providers` | 인스턴스를 만들지 않고 id를 뽑거나 `file://` 설정 파일만 펼친다(R-34) |

### 1.4 행동 규칙과 남은 질문 [필수]

**A. `ApiProvider`·`ProviderResponse` 계약**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 값이 `ApiProvider`인지 판별 | 값이 비null 객체이고 `id`와 `callApi`가 모두 **함수**이면 `ApiProvider`다(`isApiProvider`). 인스턴스 필드·클래스 여부는 보지 않는다. `ProviderOptions` 판별은 `id`가 문자열인지만 본다(`isProviderOptions`). 최소 표면은 `id()`·`callApi`·선택 `label`(`MinimalApiProvider`) | 코드 확인 |
| R-02 | 평가기가 테스트 1건×prompt 1열을 호출 | 호출 대상은 `test.provider`가 `ApiProvider` 인스턴스면 그것, 아니면 열의 provider다. 인자는 `(renderedPrompt, context, options)`. `context`에는 `vars`, `prompt`, `filters`, `originalProvider`, `test`, `logger`, `getCache`, `repeatIndex`, `testIdx`가 항상 들어가고, 응답 캐시가 꺼져 있으면 `bustCache: true`, 실행 id가 있으면 `evaluationId`, 트레이스가 켜져 있으면 `traceparent`·`evaluationId`·`testCaseId`가 더해진다. `options`는 `abortSignal` 또는 `onResponseHeaders`가 있을 때만 `{abortSignal, onResponseHeaders}`, 둘 다 없으면 `undefined`다. 테스트에 `providerOutput`이 있으면 provider를 부르지 않고 `{output: providerOutput, tokenUsage: 0, cost: 0, cached: false}`를 응답으로 쓴다 | 코드 확인 |
| R-03 | 응답·예외 처리(평가기 쪽) | ① `response.error`가 있으면 그 문자열이 결과 `error`, `failureReason=ERROR`, `success=false`로 남고 어서션은 돌지 않는다. ② `output`이 `null`/`undefined`이고 `error`도 없으면 결과 `error='No output'`(ERROR). `output: ''`는 정상으로 어서션에 간다. ③ `callApi`가 throw하면 그 테스트 행만 `error`(스택 포함)·`ERROR`·`score 0`인 결과로 바뀌고 평가는 계속된다(일시정지 취소는 예외로 빈 결과 반환). 즉 실패의 정규 경로는 `{error}` 반환, throw는 방어선이다 | 코드 확인 |
| R-04 | 응답 필드가 결과 행으로 옮겨질 때 | `cost`·`incurredCost`는 그대로, `latencyMs`는 응답 값이 있으면 응답 값(없으면 평가기가 잰 경과 시간), `metadata`는 `{...test.metadata, ...response.metadata, [파일 메타 키]}` 순(응답이 테스트 메타를 덮어씀). `callApi` 직후 `metadata`는 JSON 직렬화·역직렬화로 정리되므로(직렬화 불가 값 제거) 순수 JSON 값만 남는다. `metadata.sessionId`·`sessionIds`가 없으면 `getSessionId(response, {vars})`로 채운다 | 코드 확인 |
| R-05 | `tokenUsage` 해석 | `tokenUsage`는 필드가 모두 선택이다. 집계기는 `total`이 없으면 `prompt+completion`을 합계로 쓰고, `cached:true` 응답이면 `numRequests`를 최소 1로 세고 `tokenUsage.cached`를 합계 이상으로 맞춘다. `incurredTokenUsage`가 없으면 캐시 응답은 이번 실행에서 발생한 요청 0, 비캐시는 보고값 그대로를 발생분으로 본다. 집계·저장 형식은 eval-records·eval-run 스펙 몫 | 코드 확인(`src/util/tokenUsageUtils.ts:456-496`과 `src/evaluator.ts:1426-1441`은 읽은 범위) |
| R-06 | 응답의 `prompt`·`cached` 등 보조 필드 | `response.prompt`(문자열 또는 chat 메시지 배열)는 provider가 실제로 보낸 prompt로 간주되어, `moderation` 어서션 입력과 결과 표시에서 렌더 prompt보다 먼저 쓰인다(빈 문자열·빈 배열이면 무시, 배열은 JSON 문자열). `cached`가 true면 평가기는 provider `delay` 대기를 건너뛴다. `output`은 문자열 또는 임의 JSON이고 `raw`는 원본 응답이다. `ProviderResponse`의 나머지 필드(`finishReason`, `isRefusal`, `guardrails`, `audio`, `video`, `images`, `conversationEnded` 등)는 형태만 확인했고 소비처는 각 기능 스펙 몫 | 코드 확인(prompt·cached) / 나머지 소비처 미확인 |
| R-07 | 채점기가 특정 용도 provider를 요구 | `embedding`은 `callEmbeddingApi` 또는 `callSimilarityApi` 속성이 있는 provider, `classification`은 `callClassificationApi`, `moderation`은 `callModerationApi`가 있는 provider여야 한다(`in` 연산자 검사). 요구에 안 맞으면 조용히 다른 provider로 대체하지 않고 오류를 던진다. 임베딩 호출에서 세 번째 인자(취소 옵션)는 `supportsEmbeddingCancellation`이 true인 provider에게만 준다 | 코드 확인 |
| R-08 | 지연·재시도·정리 신호 | `runEval` 시작 시 `provider.delay ??= 인자 delay ?? getEnvInt('PROMPTFOO_DELAY_MS', 0)`(`src/evaluator.ts:1794`)로 숫자를 채우며 이미 `provider.delay`가 정해진 인스턴스는 그 값이 우선한다. 도달 경로별로 다르다: `Evaluator`가 단계를 만들 때 `delay: options.delay || 0`(`:3355`)을 넣으므로 `eval`·`retry` 등 평가기 경로에서는 인자가 항상 숫자(0 포함)라 `PROMPTFOO_DELAY_MS` 분기에 도달하지 않는다. 그 숫자는 `doEval`이 `cmdObj.delay ?? commandLineOptions?.delay ?? evaluateOptions.delay ?? 0`(재개 시 저장값 `persisted.delay ?? 0`)으로 정한다(`src/node/doEval.ts:611,624`). 환경변수가 효과를 내는 것은 `delay` 없이 `runEval`을 직접 부르는 경우뿐이다. 문서(`site/docs/configuration/rate-limits.md:85-93`)의 `PROMPTFOO_DELAY_MS`가 `--delay`와 같다는 설명과 다르며 구현이 사실이다([eval-run D-1](./eval-run.md)). 비캐시 응답 뒤에 `delay>0`이고 `handlesOwnDelay`가 아니면 그만큼 쉰다(취소되면 응답은 유지). `handlesOwnRetries`가 true면 스케줄러의 `maxRetries`를 0으로 둔다. `cleanup`/`cleanupAfterEvaluation`은 평가 종료·프로세스 종료 때 provider 레지스트리가 부르며 실패는 경고로 삼킨다(정확한 호출 시점·중복 방지 규칙은 미탐색) | 코드 확인(delay·재시도) / 추론(정리 시점) |

**B. 접두어 디스패치**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-10 | `ProviderFactory` 목록으로 경로 해석 | 목록 순서대로 `test(경로)`를 호출해 **처음 true인 factory의 `create`만** 호출한다. `create`는 자기 `test`가 맞았다고만 가정한다. 따라서 순서가 곧 우선순위다(예: `anthropic:claude-agent-sdk*`/`anthropic:claude-code*` factory가 일반 `anthropic:` factory보다 앞에 있어 에이전트 SDK provider가 선택된다). 같은 목록에서 `exec:`·`golang:`·`python:`·`ruby:` 스크립트 factory가 맨 앞, `anthropic:`는 그 뒤, 파일 확장자 JS factory는 대부분의 접두어 factory 뒤에 있다 | 코드 확인 |
| R-11 | `getProviderFactories(경로)` | `providerFamilies` 중 `canHandle(경로)`가 true인 묶음의 `factories()`를 병렬로 로드해, 그 factory들을 **`providerMap` 앞에** 이어 붙여 돌려준다(묶음 순서 유지). 일치하는 묶음이 없으면 모듈 전역 `providerMap` 배열 자체를 돌려준다(복사 없음, 읽기 전용). 묶음 로드가 실패하면 `Failed to load provider family for '<경로>': <원인>`으로 포장하고 `cause`를 붙여 던진다. 앞에 붙이는 이유: 파일 확장자 JS factory(`.js/.ts` 접미사 일치)가 `vertex:...foo.js` 같은 경로를 가로채지 않게 하기 위함이다. 묶음은 4개: ① `cerebras\|envoy\|litellm\|novita\|nscale\|togetherai` + `:` ② `bedrock:`·`bedrock-agent:`·`sagemaker:` ③ `vertex:`·`google:`·`palm:` ④ `agentic:memory-poisoning`·`promptfoo:redteam:*`(레드팀) | 코드 확인 |
| R-12 | 어떤 factory의 `test`도 true가 아님 | 오류 로그를 남기고 `Could not identify provider: <원래 경로>.` + 설정 점검 안내 + 문서 URL을 담은 `Error`를 던진다(`loadApiProvider`가 reject) | 코드 확인 |
| R-13 | `loadApiProvider(path, context)` 입구 | `env = context.env ?? cliState.env`(복사본), `basePath = context.basePath ?? cliState.basePath`를 만들고 `cliState.withBasePath`·`withEnv` 범위 안에서 `createApiProvider`를 호출한다. env는 두 층이다: 낮은 쪽 suite env(`context.env`), 높은 쪽 provider별 `options.env`. 합칠 때 provider 접두어별 별칭 묶음(예: `google:`의 `GOOGLE_API_KEY`·`GEMINI_API_KEY`·`PALM_API_KEY`, `bedrock:`의 리전 변수)에서 **높은 층이 한 별칭이라도 비어 있지 않게 정하면 낮은 층의 같은 묶음 키를 지운다**(낮은 층의 다른 별칭이 이기지 않게). `{{ env.X }}`로 명시한 템플릿은 별칭 가지치기 없이 완전한 env로 렌더한다. `config.apiKeyEnvar`가 문자열이고 템플릿 env에 그 키가 있으면 합친 env에도 넣는다. `config.linkedTargetId`가 있으면 클라우드에서 존재를 검증한다. `create`는 `cliState.withEnv(mergedEnv)` 안에서 호출되고 `{...context, env: mergedEnv}`를 받는다 | 코드 확인 |
| R-14 | `create`에 줄 `providerOptions` 구성 | `{id: 렌더된 options.id, config: {basePath?, ...렌더된 options.config}, env: mergedEnv}`. `{{ env.… }}` 템플릿만 로드 시점에 렌더되고(경로·`config`·`id`·`label` 대상), `{{ vars.* }}` 같은 나머지 템플릿은 그대로 남아 `callApi` 시점에 쓰인다. 렌더 규칙: 템플릿 안에 `env.` 또는 `env[`가 있는 것만 처리, 필터(`\|`)가 있거나 변수가 정의되어 있을 때만 치환, 정의 안 된 변수·렌더 오류는 원문 유지, `PROMPTFOO_DISABLE_TEMPLATING`이면 전부 생략. 사용자 `config.basePath`가 있으면 주입된 `basePath`보다 우선한다. **`options.label/transform/delay/prompts/inputs`는 `providerOptions`에 들어가지 않는다**(생성자는 못 본다) | 코드 확인 |
| R-15 | `create` 반환 뒤 | 반환 인스턴스에 `transform`·`delay`·`inputs`·`prompts`를 `options` 값으로 **무조건 덮어쓴다**(`options`에 없으면 `undefined`가 되어 생성자가 세팅한 값도 사라진다). `label`은 인스턴스 `label`이 비어 있을 때만 `렌더된 options.label \|\| ''`로 채운다. 반환값이 `ApiProvider`인지는 검사하지 않는다(커스텀 모듈이 `id`·`callApi` 없는 객체를 만들면 이후 호출에서 실패) | 코드 확인 |
| R-16 | 스크립트 접두어·확장자 | `exec:<스크립트>`, `python:`, `golang:`, `ruby:` 접두어이거나, `file://`이면서 경로가 `.py`/`.go`/`.rb`로 끝나거나 `.py:`/`.go:`/`.rb:`를 포함(함수명 접미사)하면 해당 factory가 맞는다(`exec`는 접두어만). 스크립트 경로는 `file://`를 떼거나 첫 `:` 뒤 전체이며, `config.isCloudConfig === true`이고 상대경로면 `cwd` 기준으로 풀고 아니면 **풀지 않고** `new ScriptProvider(경로, providerOptions)`에 그대로 넘긴다(basePath 해석은 스크립트 provider 클래스 몫, 이 스펙 밖) | 코드 확인 |
| R-17 | JS/TS 모듈 provider | 경로 끝이 `.js .cjs .mjs .ts .cts .mts`(대소문자 무시)이면 맞는다. `file://` 접두어는 있어도 없어도 되고 `:함수명` 접미사는 허용되지 않는다(접미사 정규식). 상대경로는 `context.basePath \|\| cwd` 기준. 모듈을 동적 `import`해 `default.default \|\| default \|\| 모듈 전체`를 클래스로 보고 `new Class({...providerOptions, id: providerOptions.id ?? 원래 경로})`를 만든다(`.js`가 ESM 패키지 안의 CJS 구문이면 VM 기반 CJS 폴백). 즉 모듈은 `id()`·`callApi`를 가진 객체를 만드는 **생성자**를 내보내야 하고, `options.id`가 없으면 `id`는 원래 경로 문자열이다 | 코드 확인 |
| R-18 | 모델 문자열 접두어(대표) | 접두어 뒤 모델명은 나머지 전부를 `:`로 다시 이어 붙인 값이다(모델명에 `:`가 있어도 보존, `modelNameFromProviderPath`). `echo`는 정확히 일치할 때만 `EchoProvider`. `anthropic:messages:<모델>`·`anthropic:completion:<모델>`이 명시 형식이고, `anthropic:<모델>`은 모델이 알려진 shorthand이거나 `claude-`+영숫자로 시작하면 Messages API 단축형이다. 그 밖은 형식 3가지를 안내하는 오류. `openai:<type>:<모델>`은 `chat`·`responses`·`completion`·`embedding(s)`·`image`·`video`·`tts/speech`·`transcription`·`realtime`·`moderation`·`assistant`·`agents`·`codex*` 등 type 분기, type 자리에 알려진 모델명이 오면 그 모델의 기본 API로 가고, 알 수 없는 type은 경고 후 chat provider로 만든다. `package:<패키지>:<export>`는 `basePath` 기준으로 패키지를 풀어 export를 가져와 생성자 함수면 `new Export(providerOptions)`(아니면 `Provider malformed` 오류). `http(s):`, `ws(s):`, `websocket`, `browser`, `mcp`, `sequence`, `slack`, `a2a` 등 나머지 접두어는 각자 클래스로 간다(내부 제외) | 코드 확인(anthropic·package·echo·JS·스크립트) / 추론(openai type 분기는 앞부분만 읽음) |
| R-19 | 레드팀 factory | `agentic:memory-poisoning`과 `promptfoo:redteam:<이름>`(authoritative-markup-injection, best-of-n, crescendo, custom[:…], goat, iterative[:image\|tree\|meta], hydra, goblin, indirect-web-pwn, mischievous-user)은 같은 `ProviderFactory` 형식이며 `redteamProviderFactories`로 R-11 ④ 묶음에서만 도달한다. 각 `create`는 동적 import 뒤 `new X(providerOptions.config)`(일부는 `providerOptions`)를 만든다. 모든 `create`는 `Failed to load redteam provider '<경로>': <원인>`으로 오류를 포장한다(`withErrorContext`; 일반 `providerMap` factory에는 이런 포장이 없다) | 코드 확인 |

**C. 설정 항목 형태와 로딩**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | 경로가 `promptfoo://provider/<id>` | 클라우드에서 target을 받아(로그인 필요, 조회 내부는 제외 범위) 그 `id`가 다시 클라우드 경로면 오류. 아니면 `config`는 얕은 병합(로컬이 우선), `label/transform/delay/prompts/inputs`는 `options` 값이 있으면 그것, env는 suite < 클라우드 < 로컬 순으로 병합해 그 `id`로 `createApiProvider`를 다시 호출하고, 결과 `config.linkedTargetId ??= 원래 경로`를 채운다 | 코드 확인(분기 구조) / 클라우드 응답 형식 미확인 |
| R-21 | 경로가 `file://`로 시작하고 `.yaml`/`.yml`/`.json`으로 끝남 | 파일을 읽어(상대경로는 `basePath \|\| cwd` 기준) 외부 `file://` 참조를 펼친 뒤, 단일 객체여야 하고 `id`가 필수다(없으면 `invariant` 오류). 배열 파일이면 `Multiple providers found in <상대경로>. Use loadApiProviders instead of loadApiProvider.` 오류. 단일이면 **파일 내용을 `options`로 삼아** 그 `id`로 `createApiProvider`를 다시 호출한다. env 우선순위는 낮음→높음: 상위 env < 파일의 `env` < 호출자 env < 바깥 `options.env`. 바깥 `options`에서는 `prompts`와 env만 이어받고, 바깥 `config`·`label`·`transform`·`delay`·`inputs`는 버려진다. 읽기·파싱 실패는 `Failed to load provider config <상대경로>: <원인>` | 코드 확인 |
| R-30 | `normalizeProviderRef(항목, {index?})` 분류(파일을 읽지 않는 순수 함수) | 문자열: 빈 문자열은 `unknown`, `file://…yaml\|yml\|json`은 `file`, 나머지는 `named`. 함수: `function`, `id = label ?? 'custom-function'`(배열 안이면 `custom-function-<index>`). 비null·비배열 객체: `id`가 비어 있지 않은 문자열이면 `options`(`loadProviderPath=id`, `loadOptions=객체 자체`). 아니면 키가 정확히 하나이고 그 키가 `ProviderOptions` 키 8개(`id,label,config,prompts,transform,delay,env,inputs`)가 아니며 값이 비배열 객체이면 `map`(`loadProviderPath=키`, `id=값.id(유효 시) ?? 키`, `loadOptions={...값, id}`). 그 밖에 `label`이 비어 있지 않은 문자열이면 `unknown(id=label)`, 아니면 `unknown`(`unknown` 또는 `unknown-<index>`) | 코드 확인 |
| R-31 | `loadApiProviders(providers, {basePath, env})` 입력 형태 | `env = options.env ?? cliState.env`, `basePath = options.basePath ?? cliState.basePath`. 문자열: `file://` 설정 파일이면 안의 각 항목(`id` 필수)을 `loadApiProvider(config.id, {options: config})`로 만들어 배열로, 아니면 `[loadApiProvider(문자열)]`. 단일 함수: 함수 provider 1개(R-32). 단일 `ApiProvider`: 그대로 `[provider]`. 배열: 항목을 **병렬로** 해석하되 결과는 입력 순서로 평탄화한다 — `ApiProvider` 인스턴스는 그대로(옵션 미적용), `file`은 펼침, `named`는 `loadApiProvider`, `function`은 함수 provider, `options`/`map`은 `loadApiProvider(loadProviderPath, {options: loadOptions})`, `unknown`은 `Invalid provider at index <i>: …`(입력은 비밀 값 가림·200자 절단해 메시지에 포함) 오류. 그 외 최상위 값(예: 최상위가 `{id: ...}` 객체 하나)은 `Invalid providers list` 오류 | 코드 확인 |
| R-32 | 함수 항목 → provider | `{id: () => 함수.label ?? 기본 id, callApi(...args) { 함수를 this·args로 호출하되 env 범위 안에서 }}` 객체. 함수에 정의된 `label`·`prompts`·`transform`·`delay`·`inputs`·`config`만 복사한다(`undefined`는 복사 안 함) | 코드 확인 |
| R-33 | `resolveProvider(항목, 이미만든맵, context)` | `null`/`undefined`는 오류. 문자열은 맵에 있으면 그 인스턴스 재사용, 없으면 `loadApiProvider`. 객체는 `options`/`map`만 허용(아니면 `Provider object must have an 'id' field or be a ProviderOptionsMap ...`), 함수는 R-32, 그 밖 타입은 `Invalid provider type` 오류. `ApiProvider` 인스턴스는 이 함수가 따로 받지 않는다(`id`가 함수라 `options`/`map`으로 분류되지 않아 위 `invariant` 오류가 난다). 호출자가 먼저 `isApiProvider`로 걸러야 하며 `src/evaluate.ts:208`이 그렇게 한다 | 코드 확인 |
| R-34 | 인스턴스를 만들지 않는 경로 | `getProviderIds`는 문자열·함수·`ApiProvider`(→`id()`)·배열 항목에서 id를 뽑고 `file://` 설정 파일은 파일을 읽어 `id`들을 뽑는다(`unknown`은 오류). `resolveProviderConfigs`는 `file://` 설정 파일 참조만 `ProviderOptions[]`로 펼치고 문자열·함수·객체는 그대로 둔다(필터링 `--filter-providers` 후 `loadApiProviders`에 넘기기 위함) | 코드 확인 |
| R-35 | 설정 수준 검증 스키마 | `ProvidersSchema` = 문자열 \| 함수 \| 배열(문자열 \| 함수 \| `record<string, ProviderOptions>` \| `ProviderOptions`). `ProviderOptions`·`ApiProvider` 모양의 zod 정의가 `src/validators/providers.ts`에 있다. 설정 스키마 전체는 config-schema 스펙 몫 | 코드 확인 |
| R-36 | `loadApiProvider`를 문자열로 직접 부르는 소비자 | 채점기(`getGradingProvider`: 문자열·`{id,...}`·유형별 맵·`defaultTest` 폴백), 합성(`testCase/synthesis.ts`, `assertions/synthesis.ts`), 테스트 파일 리더, 평가기의 `defaultTest.provider`, 레드팀(`discover`, `providers/shared.ts`), `validate` 명령, 서버 provider 라우트, MCP 도구. 소비자별 동작은 각 스펙 몫이고 이 계약은 모두 같은 `loadApiProvider`를 거친다는 사실만 정의한다 | 코드 확인(호출 위치 grep) |

- 불변식: ① `ApiProvider`는 `id()`와 `callApi`만 있으면 소비자와 통한다. 나머지는 모두 선택이다. ② 한 경로에서 `create`가 호출되는 factory는 최대 하나다. ③ 로드 시점에는 `{{ env.* }}`만 렌더되고 `{{ vars.* }}`는 보존된다. ④ `loadApiProviders`의 결과 순서는 입력 순서다(파일 펼침 포함).
- 미결정: 없음.
- 확인 한계: 네트워크·모델 호출·설치 없이 코드만 읽었고 아무것도 실행하지 않았다. ① 테스트 파일은 이름 검색과 `test/providers/index.test.ts:1664-1700`(여러 provider가 든 YAML/JSON 파일) 열람뿐이라 `실행 확인`이 없다. ② 개별 provider 생성자가 키 없이 만들어지는지(예: Anthropic API 키 없을 때)는 확인하지 않았다. ③ `openai:` factory의 모델 검증(`assertOpenAiApiModel` 등)과 모델별 라우팅은 개별 provider 영역이라 앞부분만 읽었다. ④ 스크립트 provider 클래스의 basePath 해석, 클라우드 target 조회, provider 레지스트리(`providerRegistry.ts`)의 정리 호출 시점은 읽지 않았다. ⑤ `docs`의 UI 표시 주장("Actual Prompt Sent")은 웹 앱 코드를 열지 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스: MIT(overview 1절). 인용·복사 시 저작권·허가 문구를 유지한다. 줄 번호는 모두 기준 SHA의 `repos/promptfoo/` 상대 경로다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/types/providers.ts:28-38,72-133` `ProviderConfig`·`ProvidersConfig`·`ProviderOptions`·`CallApiContextParams`·`CallApiOptionsParams` | 설정 provider 항목 유니온, 옵션 키, 호출 문맥·옵션 필드 | R-02, R-13, R-30 |
| C-02 | `src/types/providers.ts:139-212` `ApiProvider`·`ApiEmbeddingProvider`·`CancellableEmbeddingProvider`·`ApiSimilarityProvider`·`ApiClassificationProvider`·`ApiModerationProvider` | 인스턴스 계약과 용도별 하위 인터페이스(주석이 의미를 설명) | R-01, R-07, R-08 |
| C-03 | `src/types/providers.ts:216-243` `CallApiFunction`·`isApiProvider`·`isProviderOptions` | 호출 시그니처와 덕 타이핑 판별 | R-01 |
| C-04 | `src/contracts/providers.ts:1-165` `ProviderResponse`·`ChatMessage`·`GuardrailResponse`·`ImageOutput`·`ProviderEmbeddingResponse`·`ProviderSimilarityResponse`·`ProviderClassificationResponse`·`ProviderModerationResponse` | 응답 필드 전체 목록과 주석 | R-03~R-07 |
| C-05 | `src/contracts/shared.ts:3-48` `CompletionTokenDetailsSchema`·`TokenUsage`·`NunjucksFilterMap`·`VarValue` | 토큰 사용량 필드, 변수 값 타입 | R-05 |
| C-06 | `src/contracts/prompts.ts:3-8` `MinimalApiProvider` | prompt 함수가 받는 최소 provider 표면 | R-01 |
| C-07 | `src/providers/registryTypes.ts:1-31` `ProviderFactory`·`ProviderFamily` | 등록부 인터페이스와 `test`·`canHandle`의 역할 주석 | R-10, R-11 |
| C-08 | `src/providers/index.ts:88-163` `loadApiProvider`·`createApiProvider` 앞부분 | env·basePath 범위, 템플릿 렌더, `providerOptions` 구성 | R-13, R-14 |
| C-09 | `src/providers/index.ts:232-314` `createApiProvider` 뒷부분 | 설정 파일 분기, factory 순회·`create` 호출, 사후 덮어쓰기, 미식별 오류 | R-12, R-15, R-21 |
| C-10 | `src/providers/index.ts:165-230` `createApiProvider` 클라우드 분기 | 클라우드 target 병합 순서(참고용, R-20) | R-20 |
| C-11 | `src/util/providerRef.ts:14-23,125-132,141-168,184-259` `PROVIDER_OPTION_KEYS`·`isProviderConfigFileReference`·`readProviderConfigFile`·`normalizeProviderRef` | 항목 분류 규칙과 파일 읽기(단일/배열 구분 `wasArray`) | R-21, R-30 |
| C-12 | `src/providers/index.ts:35-68,320-357,446-523,544-572` `createProviderFromFunction`·`resolveProvider`·`loadApiProviders`·`getProviderIds` | 함수 provider, 단일·다중 해석, id 추출 | R-31~R-34 |
| C-13 | `src/providers/registry.ts:1976-2064` `providerFamilies`·`getProviderFactories` 및 `:1950-1974` `isRedteamProviderPath`·`isAwsProviderPath`·`isGoogleProviderPath` | 묶음 게이트와 앞붙이기 병합 | R-11 |
| C-14 | `src/providers/scriptBasedProvider.ts:12-52` `createScriptBasedProviderFactory` | 스크립트 접두어·확장자 판별과 경로 추출 | R-16 |
| C-15 | `src/providers/registry.ts:1685-1706` JS factory, `src/validation/fileExtensions.ts:2-7` `isJavascriptFile`, `src/esm.ts:232-263` `importModule`(정상 경로) | JS 모듈 provider 판별·로딩 | R-17 |
| C-16 | `src/providers/registry.ts:532-589` 두 `anthropic:` factory, `src/providers/shared.ts:87-89` `modelNameFromProviderPath` | 접두어→클래스 매핑의 대표 형태와 모델명 이어붙이기 | R-10, R-18 |
| C-17 | `src/providers/packageParser.ts:9-80` `loadFromPackage`·`parsePackageProvider`, `src/providers/registry.ts:1398-1406` | `package:` provider 로딩과 오류 문구 | R-18 |
| C-18 | `src/providers/registry.ts:135-345` `getProviderEnvAliasGroups`·`getProviderEndpointAliases`·`mergeProviderEnv`, `src/envOverrides.ts:1-20` `setExplicitProviderEnv`·`getExplicitProviderEnv`, `src/envars.ts:500-513` `getProviderEnvString` | env 층 병합과 별칭 가지치기 알고리즘, provider가 키를 읽는 우선순위(명시 층 → 등록 provider 층 → 병합 env) | R-13 |
| C-19 | `src/util/render.ts:11-26,50-130` `replaceTemplates`·`renderEnvOnlyInObject` | 로드 시점 env 전용 렌더링(`_conversation` 키는 건너뜀) | R-14 |
| C-20 | `src/redteam/providers/registry.ts:14-31,138-139` `withErrorContext`·`redteamProviderFactories` | 레드팀 factory 오류 포장 | R-19 |
| C-21 | `src/providers/echo.ts:1-50` `EchoProvider` | 가장 작은 `ApiProvider` 구현(오프라인 사용 가능) | R-01, R-15 |
| C-22 | `src/evaluator.ts:1091-1239,1241-1290` `callActiveProvider`·`buildCallApiContext`, `:1426-1441,1454-1507` 응답 정규화·`error`/`No output` 처리 | 호출 인자 구성과 응답 소비의 경계 | R-02~R-04 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 `test/providers/index.test.ts:1664-1700`만 열람. 실행은 하지 않았다). 아래 사례는 모두 네트워크·API 키 없이 확인할 수 있는 것만 골랐다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-10, R-15, C-21 | `loadApiProvider('echo')` 후 `callApi('hi')` | `id()==='echo'`, `label===''`. 응답 `output==='hi'`, `cost===0`, `cached===false`, `tokenUsage`가 `{total:0, prompt:0, completion:0, numRequests:1}` |
| T-02 | R-14, R-15 | `loadApiProvider('echo', {env:{X:'1'}, options:{id:'my-echo', label:'L {{ env.X }}', delay:5}})` | `id()==='my-echo'`, `label==='L 1'`, `delay===5`. 같은 `label`에 `{{ vars.a }}`가 들어 있으면 그대로 남는다 |
| T-03 | R-12 | `loadApiProvider('nonexistent:foo')` | reject, 메시지가 `Could not identify provider: ` + `nonexistent:foo`로 시작 |
| T-04 | R-30, R-31 | `loadApiProviders([{echo:{label:'a'}}, 'echo', apiProviderInstance, 'file://two.yaml'])`(`two.yaml`은 `id`를 가진 항목 2개 배열) | 길이 5, 입력 순서 유지. 첫 항목 `id()==='echo'`·`label==='a'`(맵 키가 로드 경로), 세 번째는 `apiProviderInstance`와 같은 참조, 4·5번째는 파일 항목 순서 |
| T-05 | R-31 | `loadApiProviders({id:'echo'})`(배열 아님) | reject `Invalid providers list` |
| T-06 | R-21 | `loadApiProvider('file://two.yaml')`(`two.yaml`이 배열) | reject, 메시지에 `Multiple providers found in two.yaml`와 `loadApiProviders` 안내 |
| T-07 | R-32 | `loadApiProviders([Object.assign(async p => ({output:p}), {label:'f'}), async p => ({output:p})])` | 첫째 `id()==='f'`·`label==='f'`, 둘째 `id()==='custom-function-1'`. 둘째 `callApi('x')`는 `{output:'x'}` |
| T-08 | R-10, R-11 | `getProviderFactories('anthropic:claude-agent-sdk')`에서 `test`가 처음 true인 factory | 일반 `anthropic:` factory가 아니라 `claude-agent-sdk`/`claude-code` factory(`registry.ts:532`). 같은 방식으로 `getProviderFactories('vertex:x.js')`는 첫 true factory가 구글 묶음의 `vertex:` factory이고 JS 파일 factory가 아니다 |
| T-09 | R-18 | `loadApiProvider('anthropic:foo')` | reject, 메시지에 `Unknown Anthropic model type or model name: foo`와 3가지 형식 안내 |
| T-10 | R-17 | `loadApiProvider('./p.mjs', {basePath:'/w'})`에서 `p.mjs`가 `export default class { constructor(o){this.o=o} id(){return this.o.id} callApi(p){return {output:p}} }` | `/w/p.mjs`를 불러 `id()==='./p.mjs'`(옵션 id 없음 → 원래 경로). `:함수명`을 붙인 `./p.mjs:fn`은 미식별 오류(R-12) |
| T-11 | R-03 | 평가 중 provider가 `{}`를 반환 / `{output:''}` 반환 / `{error:'boom'}` 반환 / throw | 순서대로 결과 `error==='No output'`(ERROR) / 어서션 평가 진행(정상) / `error==='boom'`(ERROR, 어서션 안 돎) / 그 행만 ERROR(스택 포함)이고 나머지 행은 계속 |
| T-12 | R-21 | `file://p.yaml`(내용 `{id: echo, label: file-label}`)을 `{id:'file://p.yaml', label:'outer'}`로 부름 | `label==='file-label'`(바깥 `label`은 버려짐) |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]

| R-ID / T-ID | 근거 (repo@dfe2d45 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-03 `src/types/providers.ts:225-243`, C-06 | 구현 직접 읽음 |
| R-02 | `src/evaluator.ts:1091-1239` `callActiveProvider`(대상 선택 1121, 인자 구성 1155-1162), `:1241-1290` `buildCallApiContext`, `:958-966` `providerOutput` 단락 | 읽음. `isGrading`·`debug`·`promptIdx`는 이 경로에서 세팅하지 않음(다른 호출자가 세팅할 수 있으나 미탐색) |
| R-03 | `src/evaluator.ts:1454-1507` `applyRunEvalResponseOutcome`(`error`, `No output`), `:1990-2027`(throw → ERROR 행), 문서 `site/docs/providers/custom-api.md`의 "Return an `error` ..." 문단 | 읽음. 문서와 구현이 일치(차이 없음) |
| R-04 | `src/evaluator.ts:1292-1297,987`(`sanitizeResponseMetadata`), `:1358-1424` `createEvaluateResult` | 읽음 |
| R-05 | `src/util/tokenUsageUtils.ts:456-496` `accumulateResponseTokenUsage`, `src/evaluator.ts:1426-1441` `normalizeCachedTargetResponse` | 일부만 읽음(집계 전체는 eval-records·eval-run 몫) |
| R-06 | `src/util/providerResponse.ts:20-67` `getActualPrompt`·`getActualPromptWithFallback`, `src/assertions/moderation.ts:66`, `src/presentation/evalResults.ts:50`, `src/evaluator.ts:1343-1352` | 읽음. 웹 UI 표시는 미확인 |
| R-07 | `src/matchers/providers.ts:318-324`(`getAndCheckProvider`의 `in` 검사), `:58`(`supportsEmbeddingCancellation`) | 읽음 |
| R-08 | `src/evaluator.ts:1794-1798,3355,1335-1352`, `src/node/doEval.ts:600-624`, `src/scheduler/rateLimitRegistry.ts:142`, `src/providers/providerRegistry.ts:325-360` | 호출 지점만 읽음. 정리 호출 시점은 추론 |
| R-10 | C-07, C-09 `src/providers/index.ts:290-302`, C-16 | 읽음. 순서 효과는 `registry.ts:532` vs `:548` 비교 |
| R-11 | C-13 `src/providers/registry.ts:1976-2064`, `src/providers/families/{aws,compatible,google}.ts` | 읽음. 앞붙이기 이유는 `:2046-2062` 주석 |
| R-12 | `src/providers/index.ts:304-313` | 읽음 |
| R-13 | C-08, C-18, `src/providers/index.ts:165-168` | 읽음. 별칭 표(`registry.ts:135-259`)는 통째로 C-18이며 개별 provider 환경변수 의미는 보지 않음 |
| R-14 | C-08 `:156-163`, C-19, `src/providers/index.ts:130-131` | 읽음 |
| R-15 | `src/providers/index.ts:295-300` | 읽음. `ApiProvider` 검사 부재는 코드에 해당 검사가 없다는 것에서 추론이 아니라 확인(`create` 반환값을 바로 사용) |
| R-16 | C-14, `src/providers/registry.ts:432-435` | 읽음. 스크립트 클래스 내부 미탐색 |
| R-17 | C-15, `src/esm.ts:232-312` | 읽음(폴백 상세는 일부) |
| R-18 | C-16, C-17, `src/providers/registry.ts:1152-1393`(openai), `:1672-1684`(http), `:1795-1830`(sequence·ws) | anthropic·package·echo는 전부, openai는 type 분기 위주로 읽음 |
| R-19 | C-20, `src/redteam/providers/registry.ts:33-139` | 읽음. 각 클래스 내부 미탐색 |
| R-20 | C-10 `src/providers/index.ts:165-230`, `src/util/cloud.ts:375-390`, `src/constants.ts:37` | 분기 구조만 읽음. `getProviderFromCloud`·`validateLinkedTargetId` 본문 미탐색 |
| R-21 | C-09 `:232-288`, C-11 `:125-168`, `test/providers/index.test.ts:1664-1700`(여러 provider 파일은 `loadApiProviders`가 펼침) | 읽음. T-12는 코드 논리에서 도출 |
| R-30 | C-11 | 읽음 |
| R-31 | C-12 `:446-523` | 읽음 |
| R-32 | C-12 `:35-68` | 읽음 |
| R-33 | C-12 `:320-357`, `src/evaluate.ts:195-215` | 읽음 |
| R-34 | C-12 `:368-421,529-572` | 읽음 |
| R-35 | `src/validators/providers.ts:14-62` | 읽음 |
| R-36 | `grep -rE '\b(loadApiProviders?\|resolveProvider)\(' src`(호출 위치 목록) | 호출 위치만 확인, 소비자 내부 미탐색 |
| T-01~T-12 | 위 R-ID 근거에서 도출. 실행하지 않음 | 모두 `추론`급(코드 논리 도출). 실제 실행 결과와 대조 안 됨 |

문서와 구현의 차이·특이점:
- `src/providers/echo.ts:24-28`: `callApi(input, _options, context)`로 두 번째·세 번째 인자 이름이 인터페이스(`context`, `options`)와 반대다. 그 결과 응답 `metadata`는 두 번째(실제 `context`)가 아니라 세 번째 인자(`options`)의 `metadata`를 읽는다. 평가기는 `options`를 보통 `undefined`로 넘기므로 `metadata`는 `{}`가 된다. 구현을 사실로 썼고 T-01은 `metadata` 값을 단정하지 않는다.
- overview의 "약 120개 항목"은 provider 클래스/접두어 수 기준으로 보이고, **factory 수는 `providerMap` 75개(`registry.ts:421-1912`의 객체·`configuredProviderFactory`·`createScriptBasedProviderFactory` 줄 패턴 집계) + 가족 11개(compatible 6, aws 3, google 2) + 레드팀 15개 ≈ 101개**다(추론: 줄 패턴 집계).
- 문서 `site/docs/configuration/rate-limits.md:85-93`는 `PROMPTFOO_DELAY_MS=1000 promptfoo eval`이 `--delay`와 같다고 하지만, `eval`·`retry` 경로는 `delay`를 항상 숫자로 넘겨 환경변수 분기에 도달하지 않는다(R-08, eval-run D-1).
- 문서 `site/docs/providers/custom-api.md`가 소개한 JS provider 모양(`id`, `callApi`, 선택 생성자)은 R-17과 일치한다. 문서에 `file://x.js:함수명` 형식은 provider에 대해 쓰여 있지 않고(변환 함수 쪽에만 있음) 구현도 JS provider 접미사를 허용하지 않는다.

### 2.2 코드 읽는 순서 [선택]
1. 계약: `src/types/providers.ts`(C-01~C-03) → `src/contracts/providers.ts`(C-04) → `src/contracts/shared.ts`(C-05).
2. 등록부: `src/providers/registryTypes.ts`(C-07) → `registry.ts`의 `providerMap` 일부(`echo` 808, `anthropic:` 532-589, JS 1685-1706, `package:` 1398)와 `providerFamilies`·`getProviderFactories`(1976-2064).
3. 로딩: `src/util/providerRef.ts`(분류) → `src/providers/index.ts`(`loadApiProviders`→`loadApiProvider`→`createApiProvider`).
4. 소비: `src/evaluator.ts`의 `callActiveProvider`→`createEvaluateResult`→`applyRunEvalResponseOutcome`.
전략: 등록부는 선형 `test` 탐색이고, 느린 import를 피하려고 가족은 `canHandle`(싼 접두어 검사)로 로드를 게이트하며 factory 안에서도 provider 클래스를 지연 import한다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드를 복사하지 않았다(인용만, MIT).

## 적용 메모 [선택]
(목적: 내 SKILL.md를 여러 모델에 평가하고 모델 적합도를 기록하는 환경. 아래는 원본 동작을 바꾸는 제안이 아니라 가져올 부분의 취사선택이다.)

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01, R-03~R-06 | 가져올 최소 계약: `id()`, `callApi(prompt, context, options) → {output, error, tokenUsage{prompt,completion,total}, cost, latencyMs, metadata, cached}`. 나머지 `ProviderResponse` 필드(audio·video·guardrails 등)는 필요할 때 추가 | 모델별 적합도 기록에는 출력·오류·토큰·비용·지연·캐시 여부·메타데이터면 된다. `metadata`가 모델·provider 고유 정보를 싣는 자리다 | 필드 부분집합만 구현. `error` 반환 관례와 "output 없음은 오류" 규칙(R-03)은 유지하는 편이 모델 간 비교에서 실패와 빈 답을 구분해 준다 |
| R-10~R-12, R-18 | 120여 개 접두어 등록부와 가족 지연 로드는 가져오지 않고, 쓸 모델 소수(예: `anthropic:`, `openai:`, `echo`, 에이전트 SDK)만 `{test, create}` 항목으로 둔다. 선택 규칙은 "첫 일치 우선"과 "일치 없음 오류"를 유지 | 대상 모델 목록이 작고 고정적이다 | 등록부 크기만 줄고 `ProviderFactory` 형태는 같다. T-03·T-08 유지 |
| R-14, R-15 | 모델 구분용으로 `id`(구현 정규형)와 `label`(사람 이름)을 분리해 결과 행에 모두 기록. 한 설정 파일에서 같은 모델을 `config`만 바꿔 여러 항목으로 나열하는 형태(R-30 `options`/`map`) | 같은 SKILL.md를 모델·설정별로 비교하려면 열 식별자가 안정적이어야 한다 | `label`은 로드 후 덮어쓰기(R-15)라 생성자가 못 보므로, 라벨에 의존하는 로직은 만든 뒤에 적용해야 한다 |
| R-13, R-14 | env 층 병합과 별칭 가지치기(C-18)는 가져오지 않아도 된다. 필요하면 provider별 API 키 환경변수 하나만 읽기 | 별칭 가지치기는 여러 벤더 키를 한 설정에서 섞는 팀 사용을 위한 복잡성이다 | `{{ env.X }}` 로드 시점 렌더(R-14)만 유지하면 비밀 값을 설정 파일에 안 쓸 수 있다 |
| C-21 | `echo` provider를 오프라인 회귀·테스트용으로 그대로 가져오되, 인자 이름 오류(2.1)는 고친다 | API 호출 없이 평가 파이프라인과 어서션을 검증할 수 있다 | `metadata`를 `context`가 아니라 의도에 맞게 정해야 하며 이 선택은 원본의 미결정이 아니라 원본 오류 수정이다 |
