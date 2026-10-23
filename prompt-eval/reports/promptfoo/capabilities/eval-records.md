---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/types/index.ts
  - src/types/results.ts
  - src/contracts/shared.ts
  - src/contracts/completionDetails.ts
  - src/contracts/providers.ts
  - src/database/tables.ts
  - drizzle/0000_lush_hellion.sql
  - src/models/eval.ts
  - src/models/evalResult.ts
  - src/models/prompt.ts
  - src/prompts/utils.ts
  - src/evaluator.ts
  - src/evaluator/runtime.ts
  - src/evaluator/inMemoryStore.ts
  - src/node/evaluationStore.ts
  - src/node/evaluatorRuntime.ts
  - src/node/retry.ts
  - src/util/tokenUsageUtils.ts
  - src/util/eval/promptMetrics.ts
  - src/util/namedMetrics.ts
  - src/util/calculateFilteredMetrics.ts
  - src/util/provider.ts
  - src/util/createHash.ts
  - src/assertions/assertionsResult.ts
  - src/assertions/index.ts
  - src/assertions/cost.ts
  - src/assertions/latency.ts
  - src/presentation/evalResults.ts
  - src/providers/anthropic/messages.ts
  - src/providers/constants.ts
  - src/server/routes/eval.ts
  - src/commands/import.ts
  - src/app/src/pages/eval/components/hooks.ts
  - src/app/src/pages/eval/components/ResultsTable.tsx
  - src/app/src/pages/eval/components/utils.ts
depends: []
status: ready
reimplementation: 미실행
---

# 평가 결과 레코드 (`Eval`, `EvalResult`, `EvaluateResult`, `CompletedPrompt.metrics`)

> 평가 한 번이 남기는 데이터(실행 단위 `Eval` 1건, 열 `CompletedPrompt`+`PromptMetrics` N개, 결과 한 칸 `EvaluateResult`/`EvalResult` M개)의 필드·단위·누락 값·식별자·인덱스 관계·집계 규칙을 정의해, 평가 실행(생산자)과 저장·서버·UI(소비자)가 같은 모양을 공유하게 한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

행(`EvaluateResult`)은 provider 호출이 병렬로 끝나는 순서대로 만들어지므로 완료 순서는 정해져 있지 않고, 아래 순서는 "한 칸"이 겪는 단계다.

1. 평가가 시작되면 provider별로 허용된 prompt마다 **열**(`CompletedPrompt`, 빈 `metrics`)을 하나씩 만들어 `Eval.prompts`에 둔다. 열의 배열 위치가 `promptIdx`다(R-01).
2. 테스트 케이스를 변수 조합·repeat로 펼친 항목마다 `testIdx`(0부터)를 매긴다. 한 칸 = `(testIdx, promptIdx)`(R-02, R-03).
3. 칸마다 provider를 호출해 응답과 지연을 얻고 `EvaluateResult` 한 행을 만든다. 응답 오류·출력 없음·예외·타임아웃은 각각 오류 행이 된다(R-04, R-05, R-08).
4. 오류가 아니면 어서션이 채점해 `success`·`score`·`namedScores`·`gradingResult`·`failureReason`을 정한다(R-06, R-07).
5. 행을 저장소에 추가한 뒤(`appendResult`) 그 열의 `metrics`에 행을 접어 넣는다(R-16). 열 목록(`prompts`)은 평가 시작 직후, 이후 최대 1초 간격, 끝에 통째로 다시 저장한다(R-19).
6. 같은 `testIdx`의 칸이 모두 끝난 뒤, 비교 어서션(`select-best`, `max-score`)이 있으면 그 행들의 `gradingResult`·`success`·`score`와 열 `metrics`를 사후 수정한다(R-17).
7. 읽는 쪽은 `eval_results` 행을 `EvalResult`로 읽어 `toEvaluateResult()`로 `EvaluateResult`를 복원하고(R-22), 요약 `EvaluateSummaryV3`·`EvaluateStats`는 저장하지 않고 그때그때 계산한다(R-23).

### 1.2 범위·통합 지점

- 제공: 위 레코드의 필드, 단위, 누락 값, 식별자, 열·행 인덱스 관계, 점수·pass/fail·토큰·비용·지연·metadata가 놓이는 자리, 행에서 열 `metrics`와 `EvaluateStats`로 접는 규칙, 저장·복원 때 바뀌는 점.
- 제외: 평가 실행 순서·동시성·재개·필터·재시도(`eval-run`), 저장 명령·출력 파일 포맷·공유·삭제·복사·임포트(`results-store`), 어서션 핸들러별 채점과 `GradingResult` 집계 알고리즘(`assertion-family`·`assertion-contract`), `ProviderResponse` 전체 필드(`provider-contract`), 필터·검색 SQL(`buildFilterWhereSql`), 트레이스·blob·레드팀 전용 필드(`metrics.redteam`, `tokenUsage.attacker`/`generation`), `repeatStability` 계산(`src/util/eval/repeatStability.ts`, 미탐색).
- 외부 의존·선행 계약: 선행 스펙은 없다. 평가기는 저장소를 `EvaluationStore` 인터페이스로만 만난다(R-26). `ProviderResponse`는 `output`·`error`·`cost`·`incurredCost`·`cached`·`latencyMs`·`tokenUsage`·`metadata`만 쓰고, 그 의미는 [provider-contract](provider-contract.md)가 정한다. 어서션은 `GradingResult`를 돌려주고 평가기는 이를 행에 옮긴다.
- 소유 상태·부작용: SQLite 테이블 `evals`·`eval_results`·`prompts`·`evals_to_prompts`·`datasets`·`evals_to_datasets`·`tags`·`evals_to_tags`(C-04). `persisted=false`인 `Eval`은 DB에 아무것도 쓰지 않고 행을 메모리 `results`에 쌓는다(R-20).

### 1.3 인터페이스와 데이터 의미

**레코드 지도**

| 레코드 | 코드 이름 | 저장 위치 | 키 |
|---|---|---|---|
| 평가 실행 | `Eval` | `evals` 1행 | `id` |
| 열(한 provider × 한 prompt) | `CompletedPrompt` | `evals.prompts` JSON 배열의 원소 | **배열 위치 = `promptIdx`** (`id`는 열의 키가 아님) |
| 열 집계 | `PromptMetrics` | `CompletedPrompt.metrics` | 열과 같음 |
| 결과 한 칸 | 값 객체 `EvaluateResult`, 저장 모델 `EvalResult` | `eval_results` 1행 | 행 `id`(UUID), 의미상 유일 키 `(evalId, testIdx, promptIdx)` |
| 요약 | `EvaluateSummaryV3`, `EvaluateStats` | 저장 안 함(읽을 때 계산) | — |

`eval_results`에는 `(eval_id, test_idx, prompt_idx)` 유일 제약이 없다(C-04). 유일성은 쓰는 쪽의 관례다.

**`Eval`** (C-17)

| 필드 | 타입 | 의미·누락 |
|---|---|---|
| `id` | string | `eval-` + 영숫자 3자 + `-` + UTC ISO 일시(초 단위, `Z` 없음). 예 `eval-aB3-2026-10-22T01:02:03` |
| `createdAt` | int, epoch **ms** | `evals.created_at`. 결과 파일의 `createdAt`·요약의 `timestamp`는 ISO 문자열이다 |
| `author` | string 또는 null | |
| `description` | string, optional | `config.description` 복사 |
| `config` | map | 평가 설정 스냅샷. 저장 때 추적(tracing) 자격증명만 정제한다 |
| `prompts` | list&lt;CompletedPrompt&gt; | 열 목록. 생성 직후는 `[]` |
| `vars` | list&lt;string&gt; | 변수 이름의 표시 순서. 비어 있으면 읽을 때 `testCase.vars` 키를 사전순으로 채워 저장한다 |
| `runtimeOptions` | map, optional | 재개·재시도용 실행 옵션(`abortSignal`·함수 값 제거) |
| `isRedteam` | bool | `config.redteam` 존재 여부 |
| `datasetId` | string | `sha256(JSON(config.tests ?? []))`. 테스트가 파일 참조면 참조 문자열이 해시된다 |
| `durationMs` | float ms, optional | 일반 평가에서는 `evaluationDurationMs`와 같다(`generationDurationMs`는 레드팀 전용). v4에서는 `evals.results` JSON의 키로 저장 |
| `results` | list&lt;EvalResult&gt; | `persisted=false`일 때만 채워진다. 저장된 Eval은 `loadResults()` 전까지 빈 목록 |
| `persisted` / `resultPersistenceFailed` | bool | 후자는 행 저장 예외가 한 번이라도 났는지 |

**`CompletedPrompt` (열)** (C-01)

| 필드 | 타입 | 의미·누락 |
|---|---|---|
| `id` | string, optional | `label`, 없으면 `id`, 그것도 없으면 `raw` 중 처음 있는 값의 sha256(R-01). 같은 prompt는 provider가 달라도 같은 `id` |
| `raw` | string | 렌더 전 프롬프트 템플릿 원문 |
| `label` | string | 표시 이름 |
| `provider` | string | `provider.label`, 없으면 `provider.id()`. 모델 이름은 별도 필드가 아니라 이 문자열(과 `config` 스냅샷의 provider 설정)에 있다 |
| `config` | any, optional | provider 설정에 병합되는 prompt 설정 |
| `metrics` | PromptMetrics, optional | 열 집계 |

**`PromptMetrics`** (C-01, C-08, C-10)

| 필드 | 타입 | 의미 |
|---|---|---|
| `score` | float | 열의 모든 행 `score`의 **합**(평균이 아님) |
| `testPassCount` / `testFailCount` / `testErrorCount` | int | R-09의 pass / fail / error 개수 |
| `testCacheHitCount` | int, optional | `response.cached`가 참인 행 수 |
| `assertPassCount` / `assertFailCount` | int | 행의 평탄화된 `gradingResult.componentResults` 중 통과·실패 개수 |
| `totalLatencyMs` | float, ms | 행 `latencyMs`의 합. 타임아웃 행도 더한다(R-08) |
| `tokenUsage` | TokenUsage | 행 토큰의 합(아래 표) |
| `namedScores` / `namedScoresCount` / `namedScoreWeights` | map&lt;string, float\|int&gt; | R-15 |
| `cost` | float | 행 `cost`의 합. 단위는 타입에 주석이 없고 UI가 `$`로 표시하며 `cost` 어서션 이유 문장도 `$`를 쓴다(추론: USD) |
| `incurredCost` | float, optional | 이번 실행에서 실제 발생한 비용의 합(R-11) |

**`EvaluateResult` (결과 한 칸)** (C-02)

| 필드 | 타입 | 의미·누락 |
|---|---|---|
| `id` | string, optional | 저장된 행의 UUID. 평가기가 만든 라이브 행에는 없다 |
| `promptIdx` / `testIdx` | int | 열 위치 / 펼친 테스트 위치. 둘 다 0부터 |
| `promptId` | string | 열의 `id`(라이브 행은 `prompt.id ?? ''`) |
| `provider` | `{id, label}` | 라이브 행에는 `config`도 실려 있으나, 저장 후 복원한 행은 `id`·`label`만 가진다 |
| `prompt` | `{raw, label, config}` | `raw`는 **변수를 채운 뒤의 최종 프롬프트**. 열의 `id`·`template`은 없다. `config`는 prompt 설정에 테스트 `options`(`repeat` 제외)를 병합한 값 |
| `vars` | map | 이 행의 변수 값. 평가기 내부용 `__evalId`·`__evalStepId`·`__repeatIndex`는 뺀다 |
| `testCase` | AtomicTestCase | 이 행에 쓰인 테스트(기본 테스트 병합 후). `description`은 여기서 읽는다 |
| `response` | ProviderResponse, optional | 응답 원문. 예외·타임아웃 행에는 없다. 비용·토큰·지연·캐시 여부의 1차 출처 |
| `error` | string 또는 null | **오류와 어서션 실패 둘 다** 채운다(R-09). 오류가 났는지는 `failureReason`으로 판단 |
| `failureReason` | int enum | `0 NONE`, `1 ASSERT`, `2 ERROR`(C-03) |
| `success` | bool | 통과 여부. 어서션이 없으면 응답이 있는 한 true |
| `score` | float | 보통 0~1이지만 범위가 강제되지 않는다. 오류 행은 0 |
| `latencyMs` | float, ms | R-10 |
| `gradingResult` | GradingResult 또는 null | 채점 결과 전체. 오류 행은 없음(R-05) |
| `namedScores` | map&lt;string, float&gt; | `metric` 이름별 행 점수(가중 평균). 오류 행은 `{}` |
| `cost` / `incurredCost` | float, optional | R-11 |
| `tokenUsage` | NormalizedTokenUsage | R-12, R-13 |
| `metadata` | map, optional | R-14 |
| `traceId` / `evaluationId` | string, optional | 추적이 켜진 행에만 |
| `repeatIndex` / `repeatGroupId` | int / string, optional | repeat가 2 이상일 때만 |

`description`은 타입에 있지만 `EvalResult` 모델이 통과시키지 않아 복원한 행에서는 항상 비어 있다(2.1).

**`GradingResult`** (`gradingResult`의 모양, 집계 알고리즘은 assertion 스펙 몫)

| 필드 | 의미 |
|---|---|
| `pass` / `score` / `reason` | 행 전체 판정·점수·이유(필수) |
| `namedScores`, `namedScoreWeights` | metric별 가중 평균과 그 가중치 합 |
| `tokensUsed` | 채점에 쓴 모델 토큰(`TokenUsage`) |
| `componentResults` | 어서션별 결과. assert-set은 부모 뒤에 자식이 한 단계 평탄화되어 붙는다 |
| `assertion`, `comment`, `suggestions`, `metadata` | 어서션 정의, 사용자 코멘트, 개선 제안, 어서션 고유 메타(`cachedResponse` 등) |

**`TokenUsage`** (C-05)

| 필드 | 의미 |
|---|---|
| `prompt` / `completion` / `total` / `cached` / `numRequests` | 대상 provider의 입력·출력·합계·캐시 재생분 토큰, 요청 수. 모두 optional이며 행·열 집계에서는 0으로 채운 `NormalizedTokenUsage`가 된다 |
| `completionDetails` | `reasoning`·`acceptedPrediction`·`rejectedPrediction`·`cacheReadInputTokens`·`cacheCreationInputTokens` |
| `assertions` | **채점 모델**의 같은 항목들. 루트 값에 섞이지 않는다 |
| `incurredTokenUsage` | 루트와 같은 구조로, 이번 실행에서 실제로 실행된 호출분만. 캐시 응답이거나 provider가 보고했을 때만 생긴다. 없으면 루트 전체가 실제 실행분이다 |

**metadata가 놓이는 자리** (R-14)

| 위치 | 내용 |
|---|---|
| `EvaluateResult.metadata` (`eval_results.metadata`) | 테스트 metadata + 응답 metadata + `_promptfooFileMetadata` + `sessionId`. 오류 행은 테스트 metadata + `errorContext` |
| `EvaluateResult.response.metadata` | provider가 응답에 실은 값(예 `http.status`, `skillCalls`). JSON으로 정리된 값 |
| `EvaluateResult.testCase.metadata` | 테스트 정의의 metadata(기본 테스트 병합 후) |
| `gradingResult.metadata`, `componentResults[].metadata` | 어서션 고유(`renderedGradingPrompt`, `cachedResponse` …) |
| `Eval.config.metadata` | 평가 전체 metadata |
| `metadata.__promptfoo` | 예약 이름공간. 저장할 때만 쓰이고 읽을 때 걷어 낸다(R-21, R-22) |

**식별자**

| ID | 만드는 법 | 안정성 |
|---|---|---|
| `Eval.id` | `createEvalId`(C-17) | 임포트가 기존 id를 유지할 수도 있다 |
| 행 `id` | 저장 때 `crypto.randomUUID()` | 임포트·복사 때 새로 매겨진다. 실행 간 비교 키로 쓸 수 없다 |
| `CompletedPrompt.id` / `promptId` | `sha256(label)`, label이 없으면 `sha256(id)`, 그것도 없으면 `sha256(raw)`(C-14) | provider와 무관하다. 열의 키는 `promptIdx` |
| `testIdx` | 평가 시작 때 확장 순서대로 | 같은 설정이라도 변수 조합·repeat·테스트 목록이 바뀌면 달라진다 |
| `repeatGroupId` | `test-<테스트 목록 위치>-vars-<변수 조합 위치>` | repeat가 2 이상일 때만 |
| 칸 키 문자열 | `` `${testIdx}:${promptIdx}` `` | 재개·중복 제거·비교 어서션이 쓴다 |

**`eval_results` 컬럼과 모델의 대응** (C-04): `id`, `eval_id`, `prompt_idx`, `test_idx`, `test_case`(JSON), `prompt`(JSON), `prompt_id`, `provider`(JSON, `config`는 정제됨), `latency_ms`, `cost`(둘 다 nullable), `response`(JSON), `error`(text), `failure_reason`(int, 기본 0), `success`, `score`, `grading_result`(JSON), `named_scores`(JSON), `metadata`(JSON), `created_at`, `updated_at`. **행 단위 `tokenUsage`·`incurredCost`·`traceId`·`repeatIndex` 컬럼은 없다**(R-13, R-21).

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 열 만들기 | provider를 설정 순서대로 돌며, 그 provider에 허용된 prompt마다 열 하나를 `prompts`에 추가한다. 따라서 `promptIdx`는 (provider 순서, 허용된 prompt 순서)의 전역 연속 번호이고 provider·prompt 라벨이 겹쳐도 열은 합쳐지지 않는다. 열 `id` = `generateIdFromPrompt`, `provider` = `label \|\| id()`, `metrics` = 0으로 채운 기본값(`createDefaultPromptMetrics`). 재개 때는 저장된 열 위치·`metrics`를 그대로 되살린다 | 코드 확인 |
| R-02 | 테스트 펼치기 | 테스트 케이스를 목록 순서로 돌고, 각 케이스에서 **repeat가 바깥 루프, 변수 조합이 안쪽 루프**이며 한 번 돌 때마다 `testIdx`를 1씩 올린다. 그 `testIdx`로 (provider 필터·prompt 필터를 통과한) 모든 열에 칸이 생긴다. `repeatGroupId`는 repeat > 1일 때만 `test-<케이스 위치>-vars-<조합 위치>`이고 `repeatIndex`와 함께 행에 실린다. 필터로 일부 열이 빠지면 그 `testIdx`의 행 수가 열 수보다 적다 | 코드 확인 |
| R-03 | 칸의 유일성 | 의미상 칸의 키는 `(testIdx, promptIdx)`다. `provider`·`promptId`는 유일 키가 아니다(둘 다 겹칠 수 있다고 코드 주석이 밝힌다). DB는 이를 강제하지 않는다 | 코드 확인 |
| R-04 | provider 호출이 응답을 돌려줌 | 행 초기값: `success=false`, `failureReason=NONE`, `score=0`, `namedScores={}`, `latencyMs = response.latencyMs ?? 호출 전후 경과 ms`, `cost = response.cost`, `incurredCost`는 응답에 있을 때만, `metadata`는 R-14, `tokenUsage` = 0으로 채운 값. 응답이 `cached`이거나 `tokenUsage`를 가지면 평가기가 먼저 응답을 정규화한다: `response.tokenUsage`를 R-12 규칙으로 다시 쌓고, `cost`가 있고 (캐시 응답이거나 `incurredCost`가 이미 있으면) `response.incurredCost = incurredCost ?? (cached ? 0 : cost)`를 넣는다. 응답에 `cost`가 없으면 `cost`는 `undefined`로 남는다. 테스트에 `providerOutput`이 있으면 provider를 부르지 않고 `{output, tokenUsage: 0, cost: 0, cached: false}`가 응답이다 | 코드 확인 |
| R-05 | 오류 행 3종 | (a) `response.error`가 있음: `error = response.error`. (b) `response.output`이 `null`/`undefined`: `error = 'No output'`(빈 문자열 출력은 오류가 아니라 채점으로 간다). 둘 다 `success=false`, `failureReason=ERROR`, `score=0`이고 `gradingResult`는 없으며 **응답·비용·토큰·지연은 그대로 행에 남는다**. (c) 호출·렌더 중 예외: 응답 없는 행을 새로 만든다. `error` = 스택(없으면 메시지), `failureReason=ERROR`, `score=0`, `namedScores={}`, `latencyMs` = 호출이 끝난 적이 있으면 그 시간, 아니면 `0`, `metadata` = 테스트 metadata + `errorContext{providerId, providerLabel, status, statusText, responseSnippet(500자 제한)}`, `cost`·`tokenUsage`·`response`는 없음 | 코드 확인 |
| R-06 | 응답이 있고 오류가 아님 | 어서션 결과를 행에 옮긴다: `success = pass`, `score`, `namedScores = result.namedScores ?? {}`, `gradingResult` = 결과 전체. `pass`가 거짓이면 `error = reason`, `failureReason = ASSERT`. 어서션이 하나도 없으면 `{pass: true, score: 1, reason: 'No assertions'}`다. 집계 규칙: `score` = Σ(구성 점수 × `weight`) / Σ`weight`(기본 1), `pass` = 실패한 구성 어서션이 없음, 테스트 `threshold`가 숫자면 `pass = score ≥ threshold`가 이를 덮어씀, `error`(=`reason`)는 실패한 구성 중 **마지막으로 기록된 것**(어서션은 동시 실행이라 순서 비결정). 행 토큰에 채점 토큰이 `tokenUsage.assertions`로 더해진다 | 코드 확인 |
| R-07 | 채점 중 예외 | `error` = 스택, `failureReason=ERROR`, `success=false`, `score=0`, `namedScores={}`. 평가를 취소해서 난 중단이면 `error`가 `Aborted: ` 접두어를 갖는다 | 코드 확인 |
| R-08 | 타임아웃 행 2종 | 단계별 타임아웃(`timeoutMs`)이면 `error = 'Evaluation timed out after <ms>ms: <원인>'`, `latencyMs = timeoutMs`. 전체 최대 시간(`maxEvalTimeMs`)이 지나 시작하지 못한 칸이면 `error = 'Evaluation exceeded max duration of <ms>ms'`, `latencyMs` = 평가 시작 이후 경과 시간이다. 둘 다 `success=false`, `failureReason=ERROR`, `score=0`, `namedScores={}`이고 **`response`·`cost`·`tokenUsage`·`metadata`가 없다**. 열 `metrics`에는 `testErrorCount += 1`, `totalLatencyMs += latencyMs`만 반영되고 `score`·`cost`·`tokenUsage`·`testCacheHitCount`·`namedScores`는 바뀌지 않는다 | 코드 확인 |
| R-09 | pass / fail / error 구분 | pass = `success`. error = `!success && failureReason == ERROR`. fail = `!success && failureReason != ERROR`. 열 카운트와 SQL 필터가 이 정의를 쓴다. `failureReason`이 0·1·2 밖의 정수이면 **읽을 때 `NONE`으로 바뀐다**. `error` 필드가 채워져 있다고 오류 행은 아니다(ASSERT 행도 `error`가 있다) | 코드 확인 |
| R-10 | `latencyMs` | provider 응답이 `latencyMs`를 주면 그 값, 아니면 평가기가 `callApi` 앞뒤로 잰 벽시계 ms. 저장 컬럼이 비어 있으면 읽을 때 `0`이다. 캐시에서 읽은 응답의 지연 값은 provider가 `latencyMs`를 채우는지에 달려 있다(채우지 않으면 캐시 조회 시간) | 코드 확인 / 캐시 적중 값은 추론 |
| R-11 | `cost`, `incurredCost` | 행 `cost`는 **대상 provider 응답의 `cost` 그대로**다(채점 모델 비용은 레코드 어디에도 없고 토큰만 `assertions`에 남는다). 캐시 응답도 `cost`는 다시 계산된 전체 비용이고, 이번 실행의 실제 비용은 `incurredCost`(캐시면 0)다. 저장 컬럼이 비면 읽을 때 `cost = 0`이 되므로 "provider가 비용을 보고하지 않음"과 "0"은 행 `cost`로는 구분되지 않고 `response.cost`의 유무로만 구분된다. 열 `metrics.cost`는 행 `cost ?? 0`의 합이고, `metrics.incurredCost`는 어떤 행이든 `incurredCost`가 있거나 이미 값이 있으면 `(기존 incurredCost ?? 그때까지의 cost) + (행 incurredCost ?? 행 cost ?? 0)`으로 이어진다 | 코드 확인 |
| R-12 | 토큰 집계 | 루트 `prompt/completion/total/cached/numRequests`는 **대상 provider 응답만** 센다. `total`이 없으면 `prompt+completion`. 응답이 `cached`이면 `cached = max(보고된 cached, 합계)`, `numRequests = max(보고된 값 ?? 0, 1)`이고 실제 실행분(`incurredTokenUsage`)은 요청 0·토큰 0으로 둔다. 비캐시 응답은 `incurredTokenUsage`를 만들지 않는다(루트가 곧 실제분). 채점 토큰은 `assertions` 아래에만 더해지며, 결정적 어서션(보고 `numRequests = 0`이고 토큰 0)은 요청으로 세지 않는다. 캐시된 채점(`gradingResult.metadata.cachedResponse`)은 루트 `assertions`에는 논리적 요청으로 세고 `incurredTokenUsage.assertions`에는 0을 둔다. 알고리즘은 C-06, C-07 | 코드 확인 |
| R-13 | 행 `tokenUsage`의 출처 | 저장 행에는 `tokenUsage` 컬럼이 없다. 읽을 때(`toEvaluateResult`) 0으로 채운 값에 `response`(응답이 있으면 `tokenUsage`가 없어도 **요청 1건**으로 셈)와 `gradingResult.tokensUsed`(`metadata.cachedResponse` 반영)를 R-12 규칙으로 더해 재구성한다. 평가기가 만든 라이브 행의 `tokenUsage`는 `response.tokenUsage`가 있을 때만 응답분을 더하므로, 응답이 토큰을 보고하지 않으면 라이브는 `numRequests=0`, 복원본은 `1`이다. 열 `metrics.tokenUsage`는 R-16대로 응답 자체에서 쌓는다 | 코드 확인 |
| R-14 | 행 `metadata` 합성 | `{...test.metadata, ...response.metadata, _promptfooFileMetadata: {변수 이름: {path, type, format}}}`(`file://`로 가리킨 이미지·영상·오디오 변수만, 없으면 `{}`). **키가 겹치면 응답 metadata가 테스트 metadata를 덮는다.** 여기에 `metadata.sessionIds`·`sessionId`가 둘 다 없을 때만 `sessionId`(응답 `sessionId` → 변수 `sessionId`)가 들어간다. 응답 metadata는 호출 직후 JSON 왕복으로 정리된다(직렬화 불가 값 제거). `afterEach` 확장 훅은 저장 직전에 `namedScores`·`metadata`·`response.metadata`를 바꿀 수 있다. 오류 행은 R-05(c), 타임아웃 행은 metadata가 없다. 이 값은 `response.metadata`에도 그대로 남아 **같은 키가 두 곳에 중복**된다(예 `skillCalls`) | 코드 확인 |
| R-15 | `namedScores` | 행: 어서션의 `metric` 이름(변수 템플릿 렌더 후)별로 `Σ(score × w) / Σw`. `weight = 0`인 어서션은 aggregate 점수에는 안 들어가지만 metric에는 가중치 1로 들어가 "측정값" 기록으로 쓸 수 있다(`cost` 어서션은 `metric`과 `weight: 0`이면 `score = cost`). 열 `metrics`: 행의 각 metric 값을 `namedScores[m] += 값 × 행 가중치`, `namedScoreWeights[m] += 행 가중치`, `namedScoresCount[m] += 그 metric을 가진 구성 어서션 수(최소 1)`로 쌓는다(행에 가중치가 없으면 값 그대로 더하고 가중치는 구성 수). **열의 metric 평균 = `namedScores[m] / (namedScoreWeights[m] ?? namedScoresCount[m])`**(UI가 이 분모를 쓴다). 설정에 `derivedMetrics`가 있으면 행을 접을 때마다 같은 `namedScores` 맵에 파생 값이 **덮어쓰기**로 들어가고, 수식 변수에 `__count`(그 열에서 지금까지 접은 행 수)가 더해진다 | 코드 확인 |
| R-16 | 행 → 열 `metrics` | 행이 저장소에 추가된 **뒤** 다음을 더한다: `score += score`, R-15, pass/fail/error 카운트(R-09), `response.cached`이면 `testCacheHitCount += 1`, `assert*Count += 평탄화된 componentResults의 통과/실패 수`(assert-set은 부모와 자식이 모두 센다), `totalLatencyMs += latencyMs ?? 0`, 토큰은 `response`(R-12) + `gradingResult.tokensUsed`, `incurredCost`·`cost`(R-11). 행 저장이 예외로 실패해도 평가는 멈추지 않고 이 접기는 그대로 수행되며 `Eval.resultPersistenceFailed = true`가 되고 행은 메모리에 보관된다 | 코드 확인 |
| R-17 | 비교 어서션 | 같은 `testIdx`의 칸이 모두 끝난 뒤 `select-best`·`max-score`가 각 행에 결과를 **합친다**: 행의 `success`를 기존 `pass`와 비교 결과의 AND로 바꾸고, 비교 결과가 실패이면 `score`와 `reason`을 비교 결과로 교체하고(`max-score`는 이전에 통과였을 때만 `reason`을 교체) `componentResults`에 그 결과를 추가한다. 통과→실패로 바뀌면 `failureReason = ASSERT`, `error = reason`, 열 `testPassCount -1`·`testFailCount +1`이고, 비교 어서션 수와 토큰이 열 `metrics`에 더해진다. 실패→통과로는 바뀌지 않는다. 변경된 행은 `EvalResult.save()`로 다시 쓰인다 | 코드 확인 |
| R-18 | `Eval` 생성(`Eval.create`) | `evals` 행(`id`, `created_at = ms`, `author`, `description`, 정제된 `config`, `results = {…duration}`, `vars`, `runtime_options`, `prompts`, `is_redteam`)을 넣고, 렌더된 prompt마다 `prompts`(`id = hashPrompt`, 본문 = `label \|\| display \|\| raw`)와 `evals_to_prompts`를, `datasets`·`evals_to_datasets`(`datasetId`)를, `config.tags`마다 `tags`(`id = sha256("키:값")`)·`evals_to_tags`를 **한 트랜잭션**으로 넣는다. `author`는 옵션으로 명시하지 않았을 때만 전역 해석 체인(`getAuthor()`)을 쓴다. 평가기가 만드는 일반 실행에서 `prompts` 열은 이때 `[]`다 | 코드 확인 |
| R-19 | 열 목록·부가값의 저장 시점 | `appendPrompts`는 `evals.prompts` 전체를 덮어쓴다. 평가기는 시작 직후 한 번, 행을 처리하는 동안 최대 1초에 한 번(`PROMPTS_FLUSH_INTERVAL_MS = 1000`), 끝에 한 번 호출한다. `vars`는 끝에 `setVars`, `durationMs`는 끝에 `setDurationMs`로 정하고 `save()`가 `evals`를 갱신한다(`persisted`일 때만). 따라서 **진행 중 읽은 `metrics`는 최대 1초 늦다**. 취소·대상 불가로 일찍 끝나는 경로도 `setVars`와 `appendPrompts`까지는 하며(`:4928-4934`, `:4954-4960`) 그 뒤 `save()`가 불리는지는 호출자 몫이라 확인하지 않았다 | 코드 확인 |
| R-20 | `persisted` | `persisted=true`: 행은 곧바로 `eval_results`에 쓰이고 `Eval.results`는 비어 있다(`loadResults`·`getResults`가 전부 읽어 옴, 읽기 전용 일괄 순회는 `fetchResultsBatched`). `persisted=false`: DB를 건드리지 않고 `EvalResult`를 메모리 `results`에 쌓는다(최적화 `optimize`가 이 방식). 어느 쪽이든 행 `id`는 UUID로 매겨진다 | 코드 확인 |
| R-21 | `EvaluateResult` → `EvalResult` 저장 | `id = randomUUID()`, `score ?? 0`, `error → 문자열`, `promptId = hashPrompt(prompt)`로 **다시 계산**(`prompt.label`이 있으면 열 `id`와 같음), `provider = {id, label, config(정제)}`(임포트 경로 `createManyFromEvaluateResult`는 `promptId`를 다시 계산하지 않고 새 UUID만 매긴다). `testCase`·`prompt`는 provider 설정의 비밀 값을 마스킹하고 `response`·`gradingResult`·`metadata`는 순환 참조·직렬화 불가 값을 제거하고 인증·세션 계열 HTTP 헤더를 가린다. `traceId`·`evaluationId`는 `metadata.__promptfoo.traceLinkage`로, `repeatIndex`·`repeatGroupId`는 `metadata.__promptfoo.repeatLinkage`로 넣어 저장한다(전용 컬럼이 없기 때문). blob 저장이 켜져 있으면 응답의 이진 데이터를 blob 참조로 바꿔 저장한다 | 코드 확인 / `promptId` 일치는 `label`이 비어 있지 않다는 전제(추론) |
| R-22 | `EvalResult` → `EvaluateResult` 복원 | `provider = {id, label}`, `vars = testCase.vars ?? {}`, `description`은 항상 `undefined`, `cost`·`latencyMs`의 null → 0, `failureReason` 범위 밖 → `NONE`, `namedScores`·`metadata`의 null → `{}`(타임아웃 행도 복원하면 `metadata = {}`), `metadata`에서 `__promptfoo` 연결 정보를 분리해 `traceId`/`evaluationId`/`repeatIndex`/`repeatGroupId` 필드로 올리고 `metadata`에서는 지운다, `incurredCost = response.incurredCost`, `tokenUsage` = R-13. 환경변수 `PROMPTFOO_STRIP_PROMPT_TEXT`·`_RESPONSE_OUTPUT`·`_TEST_VARS`·`_GRADING_RESULT`·`_METADATA`가 참이면 해당 필드를 `[prompt stripped]`·`[output stripped]`·`{}`·`null`·`{}`로 바꿔 내보낸다 | 코드 확인 |
| R-23 | 요약과 호환 | `Eval.version()`은 레거시 `oldResults.table`이 있으면 3(비정규화), 없으면 4(결과를 `eval_results`에 정규화)다. v4의 `toEvaluateSummary()`는 `{version: 3, timestamp = createdAt의 ISO, prompts, results = 모든 행의 EvaluateResult, stats, repeatStability?}`이고 `stats`는 열 `metrics`의 합이다: `successes/failures/errors` = 열 `testPass/Fail/ErrorCount` 합, `cacheHits`는 0보다 클 때만, `tokenUsage` = 열 `tokenUsage` 합, `durationMs`류는 `Eval` 값. 레거시(`version: 2`)는 `table`을 함께 든다. 표(`EvaluateTable`) 변환은 `row = testIdx`, `outputs[promptIdx]`, `pass = success`, `cost = cost ?? 0`이다 | 코드 확인 |
| R-24 | 소비자 재집계가 읽는 필드 | 열 `metrics`는 행들의 접기이므로 재계산할 수 있다. 재시도 후 재계산(`recalculatePromptMetrics`)과 필터 적용 시 SQL 재집계(`calculateFilteredMetrics`)는 `success`·`failure_reason`·`score`·`latency_ms`·`cost`·`response.tokenUsage`·`response.incurredCost`·`response.cached`·`gradingResult.tokensUsed`·`namedScores`를 쓴다. 단 재시도 재계산은 `derivedMetrics`를 다시 적용하지 않는다. **UI의 평균**(비용·지연·토큰·통과율)은 분모를 `testPassCount + testFailCount`(오류 행 제외)로 쓰는 반면 분자인 `cost`·`totalLatencyMs`·`tokenUsage`에는 오류 행(타임아웃 행의 지연 포함)이 들어 있다 | 코드 확인 |
| R-25 | 사람 평점 | `POST /api/eval/:evalId/results/:id/rating`은 행의 `gradingResult`·`success`·`score`를 요청 값으로 바꾸고 열 `metrics`의 pass/fail·assert 카운트와 `score`를 차이만큼 증감한 뒤 행과 `Eval`을 저장한다. **`failureReason`과 `error`는 바꾸지 않고**, 증감은 "이전 상태가 fail"이라고 가정한다(오류 행을 통과로 바꿔도 `testErrorCount`는 안 줄어든다) | 코드 확인 |
| R-26 | 저장소 경계 | 평가기(`evaluate(testSuite, evalRecord, options[, runtime])`)는 `EvaluationStore`(`appendResult`, `appendPrompts`, `readResults`, `readResultsByTestIdx`, `readCompletedIndexPairs`, `saveResult`, `setVars`, `setDurationMs`, `save`, `recordResultPersistenceFailure`, `toEvaluateResult` …)만 안다. 행 단위 최소 계약은 `EvaluationStoreResult = {cost, error, failureReason, gradingResult, latencyMs, metadata, namedScores, prompt, promptIdx, provider, response, score, success, testCase, testIdx}`(`id`·`tokenUsage`·`vars`는 계약에 없다). 기본 구현은 `Eval` 위의 `EvalEvaluationStore`(DB)이고, 메모리 구현 `InMemoryEvaluationStore`가 같은 인터페이스로 있으나 `src` 안에서는 아무도 쓰지 않는다(원본 테스트와 아키텍처 문서에서만 언급) | 코드 확인 |

- 불변식:
  - 열 `metrics`는 그 열의 행들을 R-16·R-17·R-08대로 접은 값이다. 단 비교 어서션·사람 평점·타임아웃 행은 증분 보정이라 필드마다 접기 규칙이 다르고(R-08, R-17, R-25), 재계산 결과가 항상 같다고 보장되지는 않는다(추론: 재계산 코드는 파생 지표·비교 보정을 따로 다루지 않음).
  - 한 `testIdx`의 칸은 모두 같은 `testCase.vars`와 `repeatGroupId`를 가진다(R-02). 다른 열은 다른 provider·prompt일 수 있다.
  - 오류 행(R-05, R-07, R-08)은 항상 `success=false`, `score=0`, `namedScores={}`다.
- 미결정: 없음.
- 확인 한계: 설치·실행·네트워크를 하지 않았다(순수 읽기). `eval_results.created_at`·`updated_at`은 `CURRENT_TIMESTAMP` 기본값을 INTEGER 컬럼에 두고 있어 SQLite가 문자열로 저장할 것으로 짐작하나 실제 값은 확인하지 못했다(`updated_at`은 `EvalResult.save()`가 초 단위 epoch를 쓴다. 레코드 의미에는 쓰이지 않음). `Eval.save()`가 `updatedAt`을 넘기지만 `evals` 테이블에 그 컬럼이 없어(`drizzle/0000_lush_hellion.sql` 이후 `ALTER`에도 없음) 무시될 것으로 추론한다. 캐시 적중 때의 `latencyMs`는 provider 구현마다 다르다(provider 스펙 몫). 원본 테스트(`test/models/*`, `test/evaluator/metrics.test.ts` 등)는 파일명만 확인했고 열지 않았다.

### 1.5 필수 코드 참조

라이선스: MIT(`overview.md` 1절). 코드를 옮길 때 저작권·허가 문구를 유지한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/types/index.ts:335-367` `PromptMetricsSchema`, `CompletedPromptSchema` | 열·열 집계의 필드 목록과 optional 여부 (`PromptSchema` 필드는 `src/contracts/validators/prompts.ts:13-26`) | R-01, R-16 |
| C-02 | `src/types/index.ts:391-425` `EvaluateResult` | 결과 한 칸의 필드 목록 | R-04~R-14 |
| C-03 | `src/types/results.ts:1-16` `ResultFailureReason`, `isResultFailureReason` | `NONE 0 / ASSERT 1 / ERROR 2`와 범위 검사 | R-09 |
| C-04 | `src/database/tables.ts:29-39, 58-114, 156-171, 177-192, 257-286` | `prompts`·`evals`·`eval_results`·`evals_to_prompts`·`evals_to_tags`·`datasets`·`evals_to_datasets` 컬럼과 FK(인덱스는 제외) | R-03, R-18, R-21 |
| C-05 | `src/contracts/shared.ts:3-42` `TokenUsage` 스키마, `NormalizedTokenUsage` | 토큰 사용 구조 | R-12 |
| C-06 | `src/util/tokenUsageUtils.ts:30-234` (`createEmpty*`, `cloneTokenUsageBreakdown`, `getAccumulatedTokenTotal`, `accumulateTokenUsage`) + `src/contracts/completionDetails.ts:3-19` `addCompletionDetails` | 0으로 채운 사용량, 누적(루트·`assertions`·`incurredTokenUsage`) | R-12, R-13 |
| C-07 | `src/util/tokenUsageUtils.ts:331-448, 456-507` (`accumulateGradingTokenUsage`, `accumulateAssertionTokenUsage`, `accumulateGradingRequest`, `accumulateResponseTokenUsage`) | 응답·채점 토큰을 요청 수·캐시·실제 실행분과 함께 누적 | R-12, R-13, R-16 |
| C-08 | `src/util/eval/promptMetrics.ts:1-39` | 기본 `metrics`, pass/fail/error·캐시 히트 카운트 | R-01, R-09, R-16 |
| C-09 | `src/util/namedMetrics.ts:1-98` + `src/assertions/index.ts:332-351` `renderMetricName` | metric 누적(값·가중치·개수)과 metric 이름 템플릿 렌더 | R-15 |
| C-10 | `src/evaluator.ts:4264-4315` `updatePromptMetricsForRow` | 행 → 열 `metrics` 접기 순서와 내용 | R-15, R-16 |
| C-11 | `src/evaluator.ts:1358-1441` `createEvaluateResult`, `normalizeCachedTargetResponse` + `:1727-1739` `getTraceLinkage` | 정상 행 초기값, 응답 정규화(`incurredCost`·토큰). `traceId`/`evaluationId`는 추적 컨텍스트가 있고 `traceparent`가 W3C 형식일 때만 | R-04, R-12, R-14 |
| C-12 | `src/evaluator.ts:624-683` `applyGradingResult`, `applyGradingError` + `:1493-1508` | 채점 결과·채점 예외·오류 응답을 행에 적용 | R-05~R-07 |
| C-13 | `src/evaluator.ts:1990-2031` + `:2070-2090` `buildProviderErrorContext` 일부 + `:3861-3893, 3961-3993` | 예외 행·타임아웃 행의 필드 | R-05, R-08 |
| C-14 | `src/evaluator.ts:2516-2549` `buildLivePromptColumns`, `:3019-3039`, `:3111-3180` + `src/models/prompt.ts:24-32` `generateIdFromPrompt` + `src/util/provider.ts:46-48` `getProviderIdentifier` | 열 만들기, `testIdx` 부여(repeat 바깥·변수 조합 안쪽), 열 `id`. 범위 안의 `isAllowedPrompt`·`isProviderAllowed`·`getProviderPromptOverride`(prompt·provider 필터 매칭), `prepareTestCaseForEval`·`generateVarCombinations`(기본 테스트 병합·변수 조합 펼치기)는 eval-run·설정 로딩 스펙 몫이다. 여기서는 "통과한 (provider, prompt, 테스트)마다 칸이 생긴다"만 쓴다 | R-01, R-02 |
| C-15 | `src/models/evalResult.ts:696-862` (`persistTraceMetadata`, `persistRepeatMetadata`, `surface*Metadata`, `strip*`) | `__promptfoo` 이름공간에 trace·repeat 연결 정보를 넣고 빼는 규칙 | R-21, R-22 |
| C-16 | `src/models/evalResult.ts:992-1075, 1254-1332, 1372-1447, 1458-1462` | `createFromEvaluateResult`, 생성자의 누락 값 대체, `toEvaluateResult`, 칸 키. 범위 안의 정제 helper(`sanitizeForDb`·`sanitizeForDbWithSecrets`·`redactSensitiveResultFieldsForDb`·`serializeResultProviderRefs`·`sanitizeProvider`)와 `extractAndStoreBinaryData`는 R-21의 글로 풀었다. 이들은 저장 전 비밀·직렬화 정리이고 레코드의 필드 의미를 바꾸지 않는다 | R-21, R-22 |
| C-17 | `src/models/eval.ts:99-101, 476-634, 670-676, 1482-1510, 1538-1576` (`getStats`가 부르는 `accumulateGenerationTokenUsage`는 레드팀 생성 비용용이라 이 스펙 범위 밖이고, 일반 평가에는 `config.metadata.generationAccounting`이 없어 아무것도 하지 않는다) | `createEvalId`, `Eval.create`, `version`, `getStats`, `toEvaluateSummary`. 범위 안의 `sanitizeTracingConfigForPersistence`(추적 자격증명 제거)·`sanitizeRuntimeOptions`(함수·`abortSignal` 제거)·`getAuthor`(작성자 해석)는 R-18의 글로 풀었고, `RepeatStabilityCalculator`는 범위 밖이다 | R-18, R-23 |
| C-18 | `src/evaluator/runtime.ts:3-78` | `EvaluationStoreResult`, `EvaluationRecord`, `EvaluationStore` 인터페이스 | R-26 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(실행·테스트 열람 없음). 시간·측정값은 조건으로 적는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-02, R-03 | provider A(`label: gpt`), provider B(label 없음, id `anthropic:messages:x`) × prompt P1(label `P1`)·P2 × 테스트 3개(변수 조합 1개, repeat 없음) | `prompts` 4개: `promptIdx` 0=(A,P1) 1=(A,P2) 2=(B,P1) 3=(B,P2), `provider` = `gpt`, `gpt`, `anthropic:messages:x`, `anthropic:messages:x`. 열 0과 2의 `id`는 같다. 행 12개, `testIdx` 0~2마다 `promptIdx` 0~3 |
| T-02 | R-02 | 테스트 1개, 변수 조합 2개, repeat 2 | `testIdx`와 (`repeatIndex`, `repeatGroupId`): 0=(0, `test-0-vars-0`), 1=(0, `test-0-vars-1`), 2=(1, `test-0-vars-0`), 3=(1, `test-0-vars-1`). repeat를 빼면 `repeatGroupId`·`repeatIndex`는 없다 |
| T-03 | R-04, R-06, R-12, R-16 | 응답 `{output:'ok', cost: 0.002, tokenUsage:{prompt:10, completion:5, total:15}}`(`latencyMs` 없음), 어서션 `contains` 하나 통과 | 행: `success=true`, `score=1`, `failureReason=0`, `error` 없음, `cost=0.002`, `latencyMs`=측정값(≥0), `response.tokenUsage` = `{prompt:10, completion:5, total:15, numRequests:1, …}`(`incurredTokenUsage` 없음). 열 `metrics`: `testPassCount=1`, `score=1`, `cost=0.002`, `assertPassCount=1`, `tokenUsage.total=15`, `tokenUsage.numRequests=1`, `tokenUsage.assertions.numRequests=0`, `incurredCost`는 없음 |
| T-04 | R-06, R-09 | 어서션 둘(가중치 1 · 통과, 가중치 1 · 실패) | `score=0.5`, `success=false`, `failureReason=1`, `error`=실패한 어서션의 이유. 열: `testFailCount+1`, `assertPassCount+1`, `assertFailCount+1` |
| T-05 | R-06 | T-04와 같고 테스트 `threshold: 0.5` | `success=true`, `failureReason=0`, `gradingResult.reason`에 `Aggregate score 0.50 ≥ 0.5 threshold`, 열 `assertFailCount`는 여전히 +1 |
| T-06 | R-05, R-09, R-16 | 응답 `{error:'429', cost:0.001, tokenUsage:{total:3}}` | `success=false`, `failureReason=2`, `score=0`, `error='429'`, `gradingResult` 없음, `cost=0.001`. 열: `testErrorCount+1`, `cost`·`tokenUsage`에 응답 값 반영 |
| T-07 | R-05, R-16 | `callApi`가 호출 도중 예외 | 행에 `response`·`cost`·`tokenUsage` 없음, `latencyMs=0`, `metadata.errorContext.providerId`=그 provider id, `failureReason=2`. 열: `testErrorCount+1`, `cost`·`tokenUsage` 불변 |
| T-08 | R-08 | `timeoutMs: 5000`인데 칸이 5초를 넘김 | 행 `error`가 `Evaluation timed out after 5000ms`로 시작, `latencyMs=5000`, `response`·`metadata` 없음. 열: `testErrorCount+1`, `totalLatencyMs+5000`, 나머지 불변 |
| T-09 | R-04, R-11, R-12 | 캐시 적중 응답 `{cached:true, cost:0.002, tokenUsage:{prompt:10, completion:5, total:15}}` | `response.incurredCost=0`, `response.tokenUsage` = 루트 `{prompt:10, completion:5, total:15, cached:15, numRequests:1}` + `incurredTokenUsage` = 전부 0·`numRequests:0`. 행 `cost=0.002`, `incurredCost=0`. 열: `testCacheHitCount=1`, `cost=0.002`, `incurredCost=0` |
| T-10 | R-17 | 같은 `testIdx`의 두 열이 모두 통과했는데 `select-best`가 열 1을 탈락시킴 | 열 1의 행: `success=false`, `failureReason=1`, `score`는 비교 결과 점수로 교체, `componentResults` 끝에 비교 결과 추가. 열 1 `metrics`: `testPassCount-1`, `testFailCount+1`. 열 0 불변 |
| T-11 | R-21, R-22 | 저장한 행에서 `cost`가 null, `latency_ms`가 null, `failure_reason=99`, metadata에 `__promptfoo.repeatLinkage={repeatIndex:1, repeatGroupId:'g'}` | 복원본: `cost=0`, `latencyMs=0`, `failureReason=0`, `repeatIndex=1`, `repeatGroupId='g'`, `metadata`에 `__promptfoo` 없음, `provider`는 `{id,label}`만, `description`은 `undefined` |
| T-12 | R-13 | 저장 행: `response`에 `tokenUsage` 없음, `gradingResult.tokensUsed = {total:20, prompt:15, completion:5, numRequests:1}` | 복원본 `tokenUsage`: 루트 `total=0`, `numRequests=1`, `assertions = {total:20, prompt:15, completion:5, numRequests:1}`, `incurredTokenUsage` 없음 |
| T-13 | R-18 | `createEvalId(new Date('2026-10-22T01:02:03Z'))` | 정규식 `^eval-[A-Za-z0-9]{3}-2026-10-22T01:02:03$`에 일치 |
| T-14 | R-16, R-24 | 열의 행이 통과 3 · 오류 1, 각 지연 100ms·오류 행 지연 5000ms | `totalLatencyMs=5300`, `testPassCount=3`, `testErrorCount=1`. UI식 평균 지연 = 5300/3 ≈ 1766.7ms(오류 행 분자 포함, 분모 제외) |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@dfe2d45 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-14 `buildLivePromptColumns`; 열 `id` 계산 `src/models/prompt.ts:24-32`; 재개 시 복원 `src/evaluator.ts:2690-2740` | 코드 읽기. 주석(`:2506-2515`)이 provider·prompt 라벨 중복 시 열이 합쳐지지 않는 이유를 밝힘 |
| R-02, R-03 | `src/evaluator.ts:3019-3039`, `:3111-3180`(`appendRunEvalOptionsForTestCase`), `:3219-3243`(provider 필터), `:3285-3312`(prompt 필터); `src/models/evalResult.ts:1458-1462` | 코드 읽기. DB 유일 제약 부재는 `src/database/tables.ts:115-153`의 인덱스 목록(모두 비유일)으로 확인 |
| R-04 | C-11; 호출·지연 `src/evaluator.ts:918-995`; 응답 정규화 호출 `:1888`; `providerOutput` 응답 `:958-964` | 코드 읽기. `latencyMs` 계산은 `:989-991`, 응답 우선은 `:1400` |
| R-05 | `src/evaluator.ts:1493-1508`, `:1990-2031`, `:2037-2105` | 코드 읽기. 예외 행의 `latencyMs`는 지역 변수가 호출 완료 후에만 대입되는 점(`:1820`, `:1889`)에서 도출 |
| R-06 | `src/evaluator.ts:624-640`; 집계 `src/assertions/assertionsResult.ts:205-211, 252-312, 314-382`; 어서션 없음 `src/assertions/index.ts:776-778`; 동시 실행 `:882-890` | 코드 읽기. 어서션별 점수 산식은 assertion 스펙 몫 |
| R-07 | `src/evaluator.ts:642-683`, `:1637-1642` | 코드 읽기 |
| R-08 | C-13 (`:3861-3893`, `:3961-3993`); 열 반영 `:4574-4608`, `:5619-5647`; 타임아웃 시작 `:4507-4572` | 코드 읽기. 이 경로는 `updatePromptMetricsForRow`(`:4264`)를 부르지 않음 |
| R-09 | C-08 `updatePromptResultCounts`; `src/models/eval.ts:966-971`; C-16 생성자 `:1327-1329`; `src/types/results.ts:1-16` | 코드 읽기 |
| R-10 | `src/evaluator.ts:1400`, `:989-991`, `:1610`; `src/models/evalResult.ts:1318`; 캐시된 지연 `src/cache.ts:670-721, 1017` | 코드 읽기. 캐시 적중 값은 provider가 `latencyMs`를 응답에 싣는지에 달려 있어 일반 규칙을 확정하지 못함 |
| R-11 | `src/evaluator.ts:1400-1402, 1426-1441, 4310-4314`; `src/models/evalResult.ts:1319, 1407-1411`; 캐시 응답의 `cost`: `src/providers/anthropic/messages.ts:893-901`; 채점 비용 부재: `src/types/index.ts:546-601`(`GradingResult`에 cost 없음), `src/matchers/*.ts`와 `src/assertions/geval.ts`(결과에 `cost`를 싣는 코드 없음, grep); `cost` 어서션 `src/assertions/cost.ts:3-12` | 코드 읽기. 단위(USD)는 UI·어서션 문구에서 추론 |
| R-12 | C-06, C-07; 정규화 호출 `src/evaluator.ts:1426-1441` | 코드 읽기와 손 계산(T-03, T-09, T-12) |
| R-13 | C-16 `toEvaluateResult` `:1394-1405`; 라이브 `src/evaluator.ts:1413, 1934, 1958-1961`; 주석 `"Mirror the live accounting"`(`evalResult.ts:1394`)과 달리 라이브 쪽은 `response.tokenUsage` 유무로 갈린다 | 코드 읽기. 이 차이는 `trackRowStats`(`:4196-4208`)가 쓰는 라이브 `row.tokenUsage`에만 영향 |
| R-14 | `src/evaluator.ts:1403-1420`, `:1292-1298`, `:4404-4439`, `:2082-2091`; 파일 메타 `src/evaluatorHelpers.ts:122-152`; 키 이름 `src/providers/constants.ts:7`; 세션 `src/redteam/util.ts:430-435`; `skillCalls`의 의미는 [skill-calls-metadata](skill-calls-metadata.md) | 코드 읽기 |
| R-15 | `src/assertions/assertionsResult.ts:274-296, 354-359`; C-09; C-10; 파생 `src/evaluator.ts:2192-2221`; UI 분모 `src/app/src/pages/eval/components/utils.ts:183-201`; `cost` 측정 어서션 `src/assertions/cost.ts:3-12` | 코드 읽기 |
| R-16 | C-10 `:4264-4315`; 호출 위치 `:4441-4452`; 저장 실패 처리 `:4248-4257`; 컬럼 평탄화 `assertionsResult.ts:339-352` | 코드 읽기 |
| R-17 | `src/evaluator.ts:2310-2378`(병합), `:4129-4194`(열 보정), `:5037-5068, 5421-5544` | 코드 읽기. 흐름 순서·취소 처리는 eval-run 몫 |
| R-18 | C-17 `Eval.create` `:476-634`; 정제 `src/util/sanitizer.ts:334-354, 605-697`; `drizzle/0000_lush_hellion.sql:7-13` 및 이후 `ALTER`(`author`(0002), `prompts`·`vars`·`is_redteam`·`runtime_options`) | 코드 읽기. `config`에서 추적 자격증명 외 비밀 값 정제가 호출자 쪽에 있는지는 미탐색 |
| R-19 | `src/evaluator.ts:162, 4722-4732, 4873-4958, 5583, 5599, 5614-5616, 5690, 5811`; `src/models/eval.ts:688-727, 1421-1430` | 코드 읽기 |
| R-20 | `src/models/eval.ts:770-794, 850-861, 1460-1475`; `src/optimizer/promptOptimizer.ts:779`; 행 `id` `src/models/evalResult.ts:1040` | 코드 읽기 |
| R-21 | C-16 `:992-1136`; 정제 helper `:46-52, 388-442, 636-690, 864-893`; 연결 정보 C-15 | 코드 읽기. 헤더 마스킹 목록(`:454-484`)의 세부는 이 스펙의 범위 밖 |
| R-22 | C-16 `:1281-1332, 1372-1447`; 투영 `:54-146, 211-281, 896-908` | 코드 읽기 |
| R-23 | C-17 `:670-676, 1482-1510, 1538-1576`; 표 변환 `src/presentation/evalResults.ts:9-153`; 타입 `src/types/index.ts:427-526` | 코드 읽기. `repeatStability` 계산은 미탐색 |
| R-24 | `src/node/retry.ts:171-293`; `src/util/calculateFilteredMetrics.ts:255-330`; UI `hooks.ts:52-71`, `ResultsTable.tsx:622-665, 760-810` | 코드 읽기. SQL 전체(`calculateFilteredMetrics`)는 앞부분만 읽음 |
| R-25 | `src/server/routes/eval.ts:709-805` | 코드 읽기. 오류 행에 평점을 줄 때의 불일치는 코드 추적(실행 아님) |
| R-26 | C-18; `src/node/evaluationStore.ts:7-89`; `src/node/evaluatorRuntime.ts:23-84`; `src/evaluator/inMemoryStore.ts:34-161`; `src/evaluator.ts:6240-6302`; 문서 `docs/architecture/packages.md:86` | 코드 읽기와 `grep -rln InMemoryEvaluationStore`(테스트 4개와 위 문서·정의 파일만) |
| T-01~T-14 | 각각 관련 R-ID의 근거 | 구현을 읽고 손으로 도출. 실행하지 않았다 |

**문서·주석과 구현의 차이**

- `EvaluateResult`의 `description` 주석은 "FIXME(ian): The EvalResult model doesn't pass this through"(`src/types/index.ts:393`)이다. 실제로 `EvalResult` 생성자는 `description`을 대입하지 않아(`src/models/evalResult.ts:1303-1331`) 복원한 행의 `description`은 항상 없다. 설명은 `testCase.description`에서 읽는다.
- 타입 주석의 "on the new version 2, this is stored per-result"는 옛 용어다. 코드의 `Eval.version()`은 3(레거시)·4이고 `EvaluateSummary` 버전은 2·3이다(`src/models/eval.ts:670-676, 1538-1576`).
- `evalResult.ts:1394-1396`의 "Mirror the live accounting in the evaluator"와 달리, 라이브 행은 `response.tokenUsage`가 있을 때만 응답 토큰·요청을 더한다(R-13).
- `latency` 어서션의 오류 문구는 "does not support cached results"(`src/assertions/latency.ts:12-14`)지만 평가기는 `response.latencyMs ?? 측정값`을 항상 넘기므로(`src/evaluator.ts:1610, 1631`) 이 분기는 평가 경로에서는 사실상 도달하지 않는다(추론).
- `eval_results.metadata`는 타입이 `Record<string, string>`(`tables.ts:113`)이지만 코드는 임의 JSON을 넣는다(`EvalResult.metadata: Record<string, any>`).

### 2.2 코드 읽는 순서

1. `src/types/index.ts:335-425` (열·열 집계·행 타입)와 `src/database/tables.ts` — 필드 목록.
2. `src/evaluator.ts` `createEvaluateResult`(`:1358`) → `applyGradingResult`(`:624`) → `updatePromptMetricsForRow`(`:4264`) — 행이 만들어지고 열에 접히는 경로. 호출 지점은 `processEvalStep`(`:4317`) 이후 `:4441-4452`.
3. `src/models/evalResult.ts` `createFromEvaluateResult`(`:992`) → `toEvaluateResult`(`:1372`) — 저장·복원에서 달라지는 것.
4. `src/models/eval.ts` `create`(`:476`), `getStats`(`:1482`), `toEvaluateSummary`(`:1538`).
5. `src/util/tokenUsageUtils.ts` — 요청 수와 캐시·실제분 규칙.

원본의 전략: 행은 DB 컬럼 몇 개와 JSON 덩어리(`response`, `grading_result`, `test_case`)로 저장하고, 열 집계는 행을 추가할 때마다 증분으로 갱신한다(필요하면 재계산 가능).

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 아직 없다.

## 적용 메모

원본 동작과 다르게 하고 싶은 점만 둔다(사용 목적: 스킬을 여러 모델에 평가해 모델별 점수·비용·지연을 기록).

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01, R-11 | "모델"과 "스킬 버전"을 열의 `provider` 문자열과 `config`에 두지 말고 기록 행의 명시 필드(`model_id`, `skill_version` 등)로 둔다 | 원본에서 모델 이름은 `provider.id`·`label` 문자열이고 열 키는 위치(`promptIdx`)라 실행 간·모델 간 비교 키가 불안정하다(`testIdx`·`promptIdx`는 구성이 바뀌면 달라진다, 행 `id`는 매번 새 UUID) | 기록 행 = (실행 id, 모델, 스킬 버전, 케이스 안정 id, repeat 번호) 키. 원본 `testIdx`·`promptIdx`는 보조 정보 |
| R-11 | 비용을 `null`(미보고)과 `0`을 구분해 저장하고 `incurredCost`(실제 지출)와 `cost`(캐시 포함 환산 비용)를 둘 다 둔다. 채점 모델 비용을 별도 필드로 계산해 남긴다 | 원본은 저장·복원에서 `undefined`를 0으로 만들고(R-11), 채점 모델 비용은 레코드에 없다(토큰만 `assertions`에 남는다) | 비용 필드는 nullable. 채점 비용은 `tokenUsage.assertions`와 채점 모델 단가로 계산해 별도 컬럼 |
| R-10, R-08, R-24 | 지연 평균은 오류·타임아웃 행과 캐시 적중 행을 제외한 행으로 계산하고 분모를 명시한다 | 원본 UI는 분자에 오류·타임아웃 지연을 넣고 분모는 오류를 뺀다(R-24). 타임아웃 행의 지연은 한계값이거나 평가 시작 이후 경과 시간이다 | 집계 함수의 분모·제외 규칙을 정의. T-14를 새 규칙으로 대체 |
| R-16 | 열 `metrics`를 증분으로 갱신하기보다 행에서 읽을 때 계산하거나, 증분 갱신한다면 재계산과의 일치를 검사한다 | 원본은 비교 어서션·사람 평점·타임아웃 행에서 증분 보정을 하며 재계산과 어긋날 수 있다(불변식) | 행 단위 기록이 원본, 집계는 파생 |
| R-02, R-14 | 반복(`repeat`) 실행은 `repeatGroupId` 같은 그룹 키로 묶어 평균·분산을 함께 기록한다. 스킬 호출 정보(`skillCalls`)는 `response.metadata` 한 곳에서만 읽는다 | 원본은 repeat 정보를 `metadata.__promptfoo`에 숨겨 저장하고(R-21), 응답 metadata를 행 metadata에 복제한다(R-14) | 저장 형식에서 전용 필드로 승격, metadata 중복 제거 |
