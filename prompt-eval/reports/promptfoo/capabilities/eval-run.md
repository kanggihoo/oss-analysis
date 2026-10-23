---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/main.ts
  - src/mainUtils.ts
  - src/constants.ts
  - src/commands/eval.ts
  - src/node/doEval.ts
  - src/node/retry.ts
  - src/evaluator.ts
  - src/evaluatorHelpers.ts
  - src/util/eval/filterTests.ts
  - src/util/eval/filterProviders.ts
  - src/util/eval/filterPrompts.ts
  - src/util/eval/repeatStability.ts
  - src/util/eval/summary.ts
  - src/validation/filterRange.ts
  - src/util/promptMatching.ts
  - src/util/provider.ts
  - src/util/transform.ts
  - src/util/testCaseReader.ts
  - src/util/fetch/errors.ts
  - src/util/config/load.ts
  - src/models/eval.ts
  - src/models/evalResult.ts
  - src/envars.ts
  - src/types/index.ts
  - src/scheduler/retryPolicy.ts
  - src/scheduler/rateLimitRegistry.ts
  - src/scheduler/rateLimitKey.ts
  - src/scheduler/adaptiveConcurrency.ts
  - src/cliState.ts
  - src/commands/retry.ts
  - src/providers/openai/chat.ts
  - src/util/eval/filterTestsUtil.ts
  - src/providers/agentWorkspace.ts
  - site/docs/usage/command-line.md
  - site/docs/configuration/rate-limits.md
  - test/evaluator/execution.test.ts
depends:
  - ./config-loading.md
  - ./provider-contract.md
  - ./assertion-family.md
  - ./eval-records.md
  - ./response-cache.md
status: ready
reimplementation: 미실행
---

# 평가 실행 파이프라인 (`promptfoo eval`)

> `eval` 명령이 `TestSuite`(와 CLI 옵션)를 받아 provider별로 허용된 prompt 열 × 테스트 × 변수 조합 × repeat를 "칸"으로 펼치고, 칸마다 렌더 → provider 호출 → 변환 → 채점을 거쳐 행으로 저장·집계하며, 필터·동시성·딜레이·타임아웃·취소·재개·재시도·`--watch`와 프로세스 종료 코드를 정하는 규칙 전체를 정의한다.

경로는 모두 `repos/promptfoo/` 기준이다. 이번 작성은 코드 읽기만 했고(설치·빌드·실행·네트워크 없음) `실행 확인`은 없다. "정적 추적"은 코드의 호출·신호 연결을 따라가 결론을 낸 것이고 실행으로 확인하지 않았다. 원본 테스트는 사례 이름을 검색했고 `test/evaluator/execution.test.ts`의 몇 사례(`:1031-1174`)만 열었다. 이 스펙은 R-ID마다 "무엇이 일어나는가"를 쓰고, 행 레코드·열 집계·어서션 내부는 선행 스펙을 링크한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. **옵션 해석(`doEval`).** `eval` 옵션을 zod로 검증하고(R-01), 설정을 `TestSuite`로 만든다(`resolveConfigs`, [config-loading](./config-loading.md) R-01~R-15). `--resume`/`--retry-errors`면 저장된 평가의 설정을 다시 해석한다(R-43~R-45). repeat·cache·`-j`·`--delay`를 정하고(R-03, R-04), 테스트·provider·prompt 필터를 적용하고(R-06~R-08), API 키를 점검하고(R-09), `Eval` 레코드를 만들고(R-11), CLI면 Ctrl+C 일시정지 핸들러를 건다(R-38).
2. **실행 단위 구성(`evaluate`).** `beforeAll` 훅 → 테스트 목록(시나리오 펼침, range) → provider×prompt 열 → `defaultTest` 병합·`transformVars` → 변수 조합 → repeat → 칸(단계) 목록을 만든다(R-13~R-21). 재개면 이미 끝난 칸을 뺀다(R-43).
3. **스케줄.** `runSerially` 테스트를 먼저 하나씩, 이어서 나머지를 동시 상한 `-j`(기본 4)로 돌린다. 동시성이 1이고 모델 채점이 있으면 grader 호출을 모아서 돌리는 경로로 간다(R-22~R-25).
4. **한 칸(`runEval`).** 변수 준비 → 프롬프트 렌더 → provider 호출(캐시·스케줄러 포함) → 응답 정규화 → provider 지연 대기 → 행 생성 → 오류·무출력 판정 → `transform` → 어서션 실행 → 행 완성(R-26~R-34). 칸마다 단계 타임아웃(R-35)과 취소 신호(R-37)를 받는다.
5. **행 처리.** 칸이 끝나면 `afterEach` 훅 → 행 저장 → 열 `metrics` 접기 → 비일시적 대상 오류 검사 순서로 처리한다(R-32, R-41, [eval-records](./eval-records.md) R-16). 최대 지속 시간이 지나면 남은 칸이 오류 행이 된다(R-36).
6. **열 사이 비교와 마무리.** 모든 칸이 끝난 뒤 `select-best`/`max-score`를 `testIdx`별로 처리하고, 남은 칸의 시간 초과 행을 넣고, `afterAll` 훅을 부르고, 평가를 저장한다(R-40, R-42).
7. **종료 처리(`doEval` 후반).** 통계 → 표·요약 → 공유 → `-o` 출력 순서로 처리한 뒤, 통과율이 임계값 미만이거나 대상이 불가용으로 중단됐으면 종료 코드를 `100`(기본)으로 정한다(R-47~R-49). 일시정지로 끝났으면 6~7을 건너뛴다(R-38).

### 1.2 범위·통합 지점

- 제공: 위 흐름 전체. CLI `eval` 옵션 중 실행에 영향 주는 것(1.3), 실행 단위 구성 규칙, 한 칸의 단계 순서, 동시성·딜레이·타임아웃·최대 지속 시간·취소·일시정지, 재개·오류 재시도·`--watch`, 종료 코드 계약, 호출 수·비용에 영향 주는 인자, `--repeat` 안정성 보고.
- 제외:
  - 스케줄러 내부(적응형 동시성, 헤더 파싱, 429 재시도 알고리즘): 별도 스펙 없음. 경계만 R-25에 쓴다.
  - 결과 저장·출력 파일 형식·`list/show/export/delete` 명령, 공유(`--share`), 표 출력: results-store·hosted-integration 소관. 이 스펙은 호출 위치와 순서만 쓴다(R-42).
  - 설정 파일 로딩: [config-loading](./config-loading.md). 단 이 스펙은 "로딩이 eval-run 소관이라고 넘긴 부분"(시나리오 펼침, `defaultTest` 병합, 최상위 `tests` 필터, 변수 조합, 렌더 호출 순서)을 R-14~R-21, R-28에서 정한다.
  - 어서션 핸들러 내부: [assertion-family](./assertion-family.md). 열 사이 비교 어서션의 계산은 같은 문서 R-49~R-52.
  - 웹 UI(`view`), 레드팀 실행(`redteam run`), 클라우드 설정 UUID(`-c <uuid>`)와 `promptfoo retry <evalId>` 명령(results-store 소관이지만 같은 `evaluate()` 재개 경로를 쓰므로 R-45에서 차이만 쓴다).
  - 훅 규칙: `extensions` 훅의 호출 위치만 R-41에 쓴다(훅 입출력·실패 처리는 [script-bridges](./script-bridges.md)).
- 외부 의존·선행 계약:
  - provider 호출 문맥·응답 처리: [provider-contract](./provider-contract.md) R-02~R-06, R-08. 캐시 키·repeat 이름공간·`--no-cache`: [response-cache](./response-cache.md) R-05~R-07. 행·열 레코드와 집계: [eval-records](./eval-records.md) R-01~R-09, R-16~R-20.
  - 라이브러리: `async`(`forEachOfLimit`), `glob`, `chokidar`, `mathjs`(`derivedMetrics`가 있을 때만), `commander`, `zod`.
- 소유 상태·부작용:
  - `Eval` 레코드와 행·열 저장(`--no-write`가 아니면 DB), 전역 `cliState`(`resume`, `retryMode`, `_retryErrorResultIds`, `maxConcurrency`, `basePath`), 프로세스 종료 코드(`process.exitCode`), SIGINT 리스너, chokidar 감시자, 선택적 per-step 작업공간 복사본(`copy_working_dir`, 단계 끝에 삭제).
  - 평가 한 번 안의 공유 상태: `conversations`(`_conversation` 변수용), `registers`(`storeOutputAs` 값), `provider.delay`(첫 칸에서 한 번 채워짐). 모두 한 `evaluate()` 호출 안에서만 산다.

### 1.3 인터페이스와 데이터 의미

**CLI `eval` 옵션 중 실행에 영향 주는 것** (원문 이름. 로딩·출력 옵션은 해당 스펙 소관이라 표에서 구분)

| 옵션 | 효과 | 기본값·우선순위·잘못된 입력 | R-ID |
|---|---|---|---|
| `-c, --config <paths...>` | 설정 파일(들). 설정 합치기는 config-loading | 없으면 작업 디렉터리의 기본 설정. 디렉터리 항목은 그 안의 기본 설정으로 대체(없으면 경고, 모두 없으면 실패) | R-02 |
| `-p -t -r -a -v/--vars --model-outputs --var --prompt-prefix --prompt-suffix --grader -x --description --tag` | 입력·`defaultTest` 덮어쓰기 | `--var`·`--grader`는 resume·retry에서 무시. `--tag`는 resume·retry와 함께 쓰면 실패 | R-02, R-10 |
| `-j, --max-concurrency <n>` | 동시 단계 상한 | `-j` > `commandLineOptions.maxConcurrency` > `evaluateOptions.maxConcurrency` > 4. 양의 정수가 아니면 옵션 오류 | R-03, R-23 |
| `--repeat <n>` | 테스트마다 반복 횟수 | CLI > 설정 > 1. 양의 정수가 아니면 옵션 오류. 설정 값이 양의 safe integer가 아니면 조용히 1 | R-03, R-20 |
| `--delay <ms>` | 비캐시 호출 뒤 대기, 동시성 1로 강제 | CLI > 설정 > 0. 0 이상 정수가 아니면 옵션 오류 | R-04, R-31 |
| `--no-cache` | 캐시 읽기·쓰기 끔 | 명시했을 때만 설정을 덮는다. 의미는 response-cache | R-03 |
| `-n, --filter-first-n <n>` `--filter-pattern <re>` `--filter-range <s:e>` `--filter-sample <n>` `--filter-sample-seed <n>` `--filter-metadata <k=v>`(반복 가능) `--filter-failing <경로·id>` `--filter-failing-only` `--filter-errors-only` | 테스트 부분집합 | 적용 순서·의미는 R-06. 숫자는 양의 정수, 정규식 오류는 던짐 | R-06, R-07 |
| `--filter-providers, --filter-targets <re>` / `--filter-prompts <re>` | provider / prompt 부분집합 | 정규식(앵커 없음), id 또는 label에 일치 | R-08 |
| `--resume [evalId]` / `--retry-errors` | 중단된 평가 이어가기 / 최신 평가의 ERROR만 재실행 | 둘은 동시에 못 씀. `--no-write`와도 못 씀. `--resume`만 쓰면 `latest` | R-02, R-43~R-45 |
| `-w, --watch` | 설정·프롬프트·테스트 파일 변경 시 재실행 | resume과 함께면 무시, 클라우드 UUID `-c`와는 불가 | R-46 |
| `--no-write` | DB에 쓰지 않음(메모리에만) | 기본은 씀. resume·retry·SIGINT 일시정지는 쓰기 필요 | R-11, R-38 |
| `--suggest-prompts <n>` | 첫 prompt의 변형을 제안 모델 n회 호출로 만들어 대화형(y/n)으로 골라 추가 | 1~50, 비resume만 | R-12 |
| `--safe-mode` | 인라인 JS(변환·어서션) 비활성 | 설정 `commandLineOptions.safeMode`가 기본값 | R-30 |
| `-o --table --no-table --table-cell-max-length --share --no-share --no-progress-bar --env-file --verbose --remote` | 출력·공유·환경·레드팀 | 이 스펙 밖(`-o` 확장자 검증만 R-01) | R-01, R-42 |
| `--interactive-providers` | 제거됨 | 경고 후 종료 코드 2 | R-48 |

**설정 `evaluateOptions` 키(실행 관련)와 환경변수**

| 이름 | 의미 | 기본값·규칙 | R-ID |
|---|---|---|---|
| `evaluateOptions.timeoutMs` / `PROMPTFOO_EVAL_TIMEOUT_MS` | 칸 하나의 시간 제한(ms) | `options.timeoutMs \|\| env` (둘 다 0이면 없음). **CLI 옵션 없음** | R-35 |
| `evaluateOptions.maxEvalTimeMs` / `PROMPTFOO_MAX_EVAL_TIME_MS` | 평가 전체 최대 지속 시간(ms) | `options.maxEvalTimeMs ?? env`, 0 이하면 없음. **CLI 옵션 없음** | R-36 |
| `evaluateOptions.repeat/delay/maxConcurrency/cache` | `--repeat`·`--delay`·`-j`·`--no-cache`의 설정판 | CLI·`commandLineOptions`보다 낮은 우선순위 | R-03 |
| `evaluateOptions.filterRange` / `commandLineOptions.filterRange` | `--filter-range`의 설정판 | CLI > `commandLineOptions` > `evaluateOptions` | R-06 |
| `test.options.repeat` | 그 테스트의 repeat(전역 덮어씀) | 양의 safe integer 아니면 전역 값 | R-20 |
| `test.options.runSerially` | 그 테스트를 직렬 구간에서 실행 | — | R-22 |
| `test.options.disableVarExpansion` / `PROMPTFOO_DISABLE_VAR_EXPANSION` | 변수 배열·`file://` 글롭 펼침 끔 | — | R-18 |
| `test.options.storeOutputAs` | 출력을 레지스터에 저장해 뒤 테스트 변수로 | 쓰면 동시성 1 | R-23, R-27 |
| `test.options.disableConversationVar` / `PROMPTFOO_DISABLE_CONVERSATION_VAR` | `_conversation` 변수 주입 끔 | — | R-23, R-27 |
| `PROMPTFOO_PASS_RATE_THRESHOLD` | 통과율 임계값(%) | 100 | R-47 |
| `PROMPTFOO_FAILED_TEST_EXIT_CODE` | 임계값 미달 시 종료 코드 | 100 | R-47 |
| `PROMPTFOO_DELAY_MS` | 문서는 `--delay`의 환경변수판이라고 함 | `eval` 경로에서는 효과 없음(2.1 D-1) | R-31 |
| `PROMPTFOO_MIN_CONCURRENCY`, `PROMPTFOO_SCHEDULER_QUEUE_TIMEOUT_MS`, `PROMPTFOO_DISABLE_ADAPTIVE_SCHEDULER` | 스케줄러(경계) | 기본 1 / 300000ms / 적응형 켜짐 | R-25 |
| `PROMPTFOO_ASSERTIONS_MAX_CONCURRENCY` | 한 칸 안의 어서션 동시 수 | 기본 3, assertion-family R-13 | R-33 |

**실행 단계(내부 연산 이름: `RunStep`)**: 한 칸을 돌리는 데 필요한 값의 묶음이다. 필드: `provider`(열의 provider 인스턴스), `prompt`(`raw = 접두 + 원문 + 접미`, `template = 접두·접미 붙이기 전 원문`, label, config), `test`(병합이 끝난 테스트에 이 조합의 `vars`가 든 사본), `testIdx`, `promptIdx`, `repeatIndex`, `repeatGroupId?`, `delay`(ms, 항상 숫자), `evaluateOptions`(`repeat`는 테스트별 값으로 바뀜), `conversations`, `registers`, `abortSignal`, `evalId`, `rateLimitRegistry`. 단계 목록의 순서가 곧 실행 시작 순서(R-22)이고 `testIdx`·`promptIdx`가 [eval-records](./eval-records.md)의 칸 키다.

**`evaluate(testSuite, evalRecord, options) → evalRecord`**: 위 흐름 2~6단계의 구현. `options`는 `maxConcurrency, repeat, delay, cache, timeoutMs, maxEvalTimeMs, filterRange, abortSignal, pauseSignal, restorePromptColumns, generateSuggestions, suggestionsCount, showProgressBar, eventSource` 등이다. 완료는 모든 칸의 행이 저장되고 비교·마무리가 끝났을 때이고, 취소·일시정지·대상 불가용으로 끝나면 그때까지 저장된 상태로 돌아온다(R-37). `runEval(step) → [EvaluateResult]`는 한 칸(R-26~R-34)이며 일시정지로 중단된 칸은 빈 목록을 돌려준다(R-38).

### 1.4 행동 규칙과 남은 질문

규칙 묶음: CLI·실행 전 결정(R-01~R-12), 실행 단위 구성(R-13~R-21), 순서·동시성(R-22~R-25), 한 칸(R-26~R-34), 시간·취소(R-35~R-39), 비교·훅·마무리(R-40~R-42), 재개·재시도·watch(R-43~R-46), 종료 코드(R-47~R-49), 비용·호출 수·반복(R-50~R-52).

**A. CLI·실행 전 결정**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 옵션 검증(`evalCommand` action, C-01) | `EvalCommandSchema`(= `CommandLineOptionsSchema.partial()` + `help, interactiveProviders, remote, noShare, retryErrors, suggestPrompts(1~50), extension, resume(string·boolean)`)로 파싱한다. 위반(`-j 0`, `--repeat 1.5`, `--delay -1`, `--filter-first-n 0`, `--filter-range` 형식·순서 오류, 숫자 아닌 값)은 `Invalid command options: …`를 남기고 `process.exitCode = 1`로 끝난다(평가 시작 안 함). 남은 위치 인자(예 `eval foo`)는 `Unknown command: foo. Did you mean -c foo?`와 종료 코드 1(`help`만 도움말). `--no-cache`는 사용자가 명시했을 때만 `cache`를 덮는다. `-o`의 확장자가 지원 형식이 아니면 `Unsupported output file format`을 던진다(종료 코드 1). 정규식 옵션(`--filter-providers/--filter-prompts/--filter-pattern`)의 문법 오류는 해당 적용 시점에 던진다(종료 코드 1) | 코드 확인 |
| R-02 | 상충·전제 검사 | `--resume`+`--retry-errors`, `--tag`+`--resume`/`--retry-errors`, `--no-write`+`--resume`/`--retry-errors`는 실패한다. `--resume` 대상이 없으면 `Could not find evaluation to resume: <id>`, `--retry-errors`인데 평가가 하나도 없으면 `No previous evaluation found to retry errors from`. CLI 호출이면 `logger.error` + `process.exitCode = 1`(빈 `Eval`을 돌려줌), 라이브러리 호출이면 `EvalRunError`(종료 코드 1)를 던진다. 클라우드 UUID `-c`는 한 개만 허용되고 `--watch`와 못 쓴다(던짐). `-c`가 디렉터리면 그 안의 기본 설정으로 바뀐다([config-loading](./config-loading.md) R-02와 같은 `eval` 전용 처리) | 코드 확인 |
| R-03 | 런타임 옵션 해석(C-02) | 평가 시작 전에 네 값을 정한다. `repeat`: `--repeat` > `commandLineOptions.repeat` > `evaluateOptions.repeat`, 양의 safe integer가 아니면 1. `cache`: 명시한 `--no-cache` > `commandLineOptions.cache` > `evaluateOptions.cache` > true. `false`면 `Cache is disabled.`를 로그하고 `disableCache()`. `maxConcurrency`: `-j` > `commandLineOptions` > `evaluateOptions` > 4(`DEFAULT_MAX_CONCURRENCY`). `delay`: `--delay` > `commandLineOptions.delay` > `evaluateOptions.delay` > 0이고, 0·NaN이면 `options.delay`는 `undefined`. **resume·retry는 이 넷을 CLI·설정 대신 저장된 `runtimeOptions`에서 가져오고(없으면 `config.evaluateOptions`), repeat은 양의 safe integer 아니면 1, cache 기본 true, `-j` 기본 4, delay 기본 0**이다. 설정의 `config.evaluateOptions`는 등록 시점(`defaultConfig`)의 값 위에 덮어쓰이되 `eventSource`는 호출자 값으로 고정된다 | 코드 확인 |
| R-04 | `delay > 0`(`doEval`·`promptfoo retry` 경로) | `maxConcurrency = 1`이 되고 `cliState.maxConcurrency = 1`, 로그 `Running at concurrency=1 because <n>ms delay was requested between API calls`. 그 외에는 `-j`를 명시했을 때만 그 값을 `cliState.maxConcurrency`(Python 워커 풀 크기 등 provider용)에 복사한다. 이 강제는 `doEval`/retry 경로의 것이고 `evaluate()`를 직접 부르는 호출자는 delay가 있어도 동시성이 그대로다 | 코드 확인 |
| R-05 | 시간 제한 값의 출처 | `timeoutMs`(칸 단위)와 `maxEvalTimeMs`(평가 전체)는 **CLI 옵션이 없다**. 설정 `evaluateOptions`(resume은 저장된 설정) 또는 환경변수 `PROMPTFOO_EVAL_TIMEOUT_MS`·`PROMPTFOO_MAX_EVAL_TIME_MS`로만 준다. 우선순위가 다르다: `timeoutMs`는 `options.timeoutMs \|\| env`(설정 값 0은 env로 넘어감), `maxEvalTimeMs`는 `options.maxEvalTimeMs ?? env`(설정 값 0은 "없음"으로 존중됨). 환경변수는 평가가 돌 때마다 읽는다 | 코드 확인 |
| R-06 | 테스트 부분집합 필터(비resume, 최상위 `tests`만, C-02, C-03) | `filterTests`가 정해진 순서로 적용한다: ① `--filter-metadata`(반복 플래그는 AND, 한 플래그 안의 쉼표 값은 OR, `\,`는 리터럴 쉼표, 값은 메타데이터 값의 `toString()` 부분 문자열 포함, 배열이면 원소 중 하나라도; 테스트 자신의 `metadata`만 보고 `defaultTest.metadata`는 아직 합쳐지기 전이라 보지 않으며 `metadata`가 없는 테스트는 제외) → ② `--filter-failing`/`--filter-failing-only`/`--filter-errors-only`(이전 평가 id 또는 `.json` 결과 파일에서 해당 행의 테스트만, 런타임 변수는 비교에서 제외, 못 찾으면 경고와 빈 목록, `failing-only`+`errors-only`는 합집합) → ③ `--filter-pattern`(정규식, `description`이 없는 테스트는 제외) → ④ `--filter-range start:end`(0 기반, end 미포함, `:N`·`N:` 허용) → ⑤ `--filter-first-n` → ⑥ `--filter-sample`: Fisher–Yates로 섞어 앞 N개를 취하고, **취한 테스트의 순서도 섞인 순서**다. `--filter-sample-seed`가 있으면 시드 기반 PRNG라 같은 입력에서 같은 결과, 없으면 `Math.random`. 시나리오가 있으면 range는 여기서 빼고 `evaluate()`가 합쳐진 목록에 적용한다(R-14). 시나리오가 없고 필터 뒤 테스트가 0개인데 원래 명시 테스트가 있었으면 암시적 기본 테스트(R-14)를 만들지 않아 단계가 0개가 된다(필터가 켜져 있고 명시 테스트가 없던 경우의 암시적 테스트 `[{metadata}]`도 같은 필터를 받는다) | 코드 확인 |
| R-07 | 시나리오·resume과 필터의 상호작용 | 시나리오 테스트에는 위 최상위 필터가 적용되지 않는다. 로드 시 시나리오별로 `--filter-first-n/pattern/failing/sample`만 적용되고(sample 시드는 시나리오 위치로 파생), `--filter-range`는 R-14의 합친 목록에 적용된다. resume·retry는 테스트 필터를 **적용하지 않고** `filterRange`만 저장값으로 되살린다(CLI `--filter-range`가 다르면 경고 후 무시) | 코드 확인 |
| R-08 | provider·prompt 필터 | `--filter-providers`/`--filter-targets <정규식>`은 두 번 적용된다: 로드 때 설정의 provider 항목(id·label)에([config-loading](./config-loading.md) R-15), `doEval`에서 만들어진 인스턴스의 `id()`·`label`에 비앵커 `RegExp.test`로. 0개가 되면 열이 없어 단계도 없다. resume·retry는 저장된 `runtimeOptions.providerFilter`를 재적용하고 CLI 값이 다르면 경고 후 무시, 저장 필터가 0개 provider를 만들면 실패한다. `--filter-prompts <정규식>`은 로드 때 `testSuite.prompts`를 `id` 또는 `label`이 일치하는 것으로 줄이고, 0개가 되면 경고 뒤 `No prompts found` 오류(종료 코드 1)다 | 코드 확인 |
| R-09 | API 키 사전 점검(provider 필터 뒤, 칸 실행 전) | provider 인스턴스가 `getApiKey()`를 가지고 키가 필요하면(`requiresApiKey()`가 아니면 `config.apiKeyRequired !== false`; `azure:`는 제외) 키가 없을 때 `Missing required API keys: <ENV> (<provider 설명>)…`로 실패한다. 호출은 하지 않는다. CLI는 종료 코드 1, 라이브러리는 `EvalRunError` | 코드 확인 |
| R-10 | `--grader`, `--var`, `--prompt-prefix/--prompt-suffix`, `-x`, `--tag` 적용 위치 | `--grader`는 `defaultTest.options.provider`에, `--var`는 `defaultTest.vars`에 `{…기존, …CLI}`로 얹힌다(둘 다 resume·retry에서는 건너뜀). prefix·suffix는 설정 로딩에서 `defaultTest.options`로 들어가고(config-loading R-41) 실행 때 R-19로 쓰인다. `--tag`는 `config.tags`에 합쳐 저장된다(resume·retry와 함께 쓰면 R-02 실패) | 코드 확인 |
| R-11 | 평가 레코드 생성(C-02) | `--no-write`가 아니면 DB 마이그레이션 후 `Eval.create(config, testSuite.prompts, {author, runtimeOptions})`, 아니면 `new Eval(config, {author, runtimeOptions})`(`persisted=false`, 행은 메모리에만). `runtimeOptions = {…options, providerFilter?}`(repeat, delay, maxConcurrency, cache, filterRange, timeoutMs, maxEvalTimeMs 등; 함수·`abortSignal`은 저장 때 제거). 레코드 필드·`persisted` 의미는 [eval-records](./eval-records.md) R-18, R-20. `TestSuiteSchema` 검증은 경고만 한다 | 코드 확인 |
| R-12 | `--suggest-prompts <n>` 또는 `generateSuggestions`(비resume) | 평가 시작 직후(열 만들기 전) `generatePrompts(첫 prompt의 raw, n)`을 부른다. n은 정수 1~50이어야 하고(CLI 스키마는 51 이상을 거부, 평가기는 정수가 아니거나 1 미만이면 1, 50 초과는 50으로 보정) **제안 모델 호출이 정확히 n회** 일어난다. 호출은 서로 독립이고 입력(고정 시스템 메시지 + "Generate a variant…" + 첫 prompt 원문)이 같으며 동시 4개(`SUGGESTIONS_CONCURRENCY`)까지 병렬이다. 제안 모델은 `getDefaultProviders().suggestionsProvider`([default-providers](./default-providers.md) R-18)다. 실패한 호출은 경고만 남기고 성공한 변형만 모으며(일부 실패는 `Only <k> of <n> requested prompt variants were generated` 경고), 하나도 없으면 `Failed to generate prompts: <오류>`로 평가가 실패한다. 제안 호출의 토큰은 평가 통계에 합산되지 않는다. 받은 변형 각각에 대해 `Do you want to test this prompt?`(기본 아니오)를 **대화형으로 하나씩** 묻고, y로 고른 것만 `{raw: 변형, label: 변형}`으로 prompt 목록 뒤에 추가한다(모든 provider와 새 열을 이룸). 같은 흐름을 쓰는 `optimize`와의 차이는 [prompt-optimize](./prompt-optimize.md) R-27 표를 따른다. 하나도 고르지 않으면 `No prompts selected. Aborting.`과 함께 CLI는 종료 코드 1로 평가 없이 끝나고, 라이브러리는 `PromptSuggestionsRejectedError`. 표준 입력으로 응답을 받아야 하는 대화형 기능이다(비대화형 환경의 동작은 미확인) | 코드 확인 |

**B. 실행 단위 구성** (`evaluate()` 안, 모두 칸 실행 전)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-13 | `evaluate` 진입 후 순서(C-18) | ① 모든 provider를 레지스트리에 등록(`useProvider`), 추적 수신기 시작(추적이 켜진 경우) → ② `Starting evaluation <id>` → ③ resume이고 `extensions`가 있으면 저장 열 스냅샷으로 훅이 볼 prompt 목록 준비 → ④ `beforeAll` 훅(R-41) → ⑤ (비resume) 프롬프트 제안(R-12) → ⑥ 테스트 목록 구성·range(R-14) → ⑦ 열 만들기와 `appendPrompts`(R-17) → ⑧ 변수 준비(R-15, R-16) → ⑨ 단계 목록(R-18~R-20) → ⑩ 비교 어서션이 있는 `testIdx` 표시 → ⑪ resume이면 끝난 칸 제거(R-43) → ⑫ 동시성 보정(R-23) → ⑬ 직렬 단계, 이어서 동시 단계(R-22) → ⑭ 열 사이 비교(R-40) → ⑮ 시간 초과 행(R-36), `setVars`, `afterAll`, `save`(R-42) | 코드 확인 |
| R-14 | 테스트 목록 구성(C-04) | `testSuite.tests`가 비어 있지 않으면 그 순서 그대로가 기본 목록이다. 비어 있으면 시나리오가 있을 때(빈 배열 포함) `[]`, 없을 때 `[{}]`(변수 없는 빈 테스트 1개: `defaultTest`만으로 한 번 실행)다. 시나리오가 있으면 `scenarios` 순서대로, 각 시나리오의 `config[]` 항목마다(시나리오 위치 번호 0부터 증가) `tests[]`(없으면 `[{}]`)를 합성해 **목록 뒤에** 붙인다. 합성: 최상위 키는 `defaultTest < config 항목 < 테스트`의 스프레드, `vars`·`options`·`metadata`는 같은 우선순위의 얕은 병합, `assert = config 항목.assert + 테스트.assert`(`defaultTest.assert`는 R-15에서 앞에 붙는다), `metadata.conversationId ??= "__scenario_<번호>__"`. 그다음 `filterRange`(R-06·R-07이 정한 곳에서만)를 이 목록에 적용한다. 이 목록의 위치가 R-19의 `repeatGroupId`에 쓰이는 "테스트 위치"다 | 코드 확인 |
| R-15 | `defaultTest` 병합(테스트마다, 변수 펼치기 전, C-04) | 테스트 객체를 **제자리에서** 바꾼다. `vars = {…defaultTest.vars, …test.vars}`, `assert = [...(test.options.disableDefaultAsserts === true ? [] : defaultTest.assert), ...test.assert]`(기본이 앞, [assertion-family](./assertion-family.md) R-23), `threshold = test ?? default`, `options = {…default, …test}`, `metadata = {…default, …test}`, `prompts`·`providers`·`assertScoringFunction`은 테스트 값이 없을 때만 기본값(문자열 스코어링 함수는 로드). `provider`는 테스트에 없고 기본에 있으면 기본을 쓴다(객체면 `loadApiProvider`로 만들고 인스턴스면 그대로). `assert`가 배열이 아니면 `defaultTest.assert is not an array in test case #<n>` 오류 | 코드 확인 |
| R-16 | `transformVars`(`test.options.transformVars ?? defaultTest.options.transformVars`) | R-15의 vars 병합 직후, **변수 조합 펼치기·`file://` 변수 로딩보다 앞에서** 테스트당 한 번 실행한다. 입력은 병합된 원본 vars(배열·`file://` 문자열 그대로), context는 `{prompt: {}, uuid: <실행마다 새 UUID>}`이고 반환 객체를 `{…vars, …반환}`로 얹는다. 반환이 객체가 아니면 `Transform function did not return a valid object`로 평가 전체가 실패한다. `uuid`를 쓰면 같은 설정도 값이 달라진다. 결과의 변수 이름들이 `Eval.vars` 표시 순서(`varNames`)의 기준이다 | 코드 확인 |
| R-17 | 열 만들기(`buildLivePromptColumns`, C-05) | provider를 설정 순서대로, 각 provider에서 `getProviderPromptOverride(provider, providerPromptMap)`(label 키 먼저, 없으면 id 키) `?? provider.prompts`가 허용하는 prompt를 `testSuite.prompts` 순서로 돌며 열을 하나씩 만든다. `promptIdx`는 전역 연속 번호다. 허용 규칙(`isPromptAllowed`): 선택자 목록이 없으면(`undefined`) 모두 허용, 빈 배열이면 모두 제외, 있으면 어느 하나와 맞는 prompt만 — 선택자는 label 또는 id와 정확히 같거나, `접두*`(label·id가 접두로 시작), 또는 `그룹`(label·id가 `그룹:`으로 시작). 열의 `id`·`provider`·`metrics` 초기값은 [eval-records](./eval-records.md) R-01 | 코드 확인 |
| R-18 | 변수 조합(`generateVarCombinations`, C-06) | `PROMPTFOO_DISABLE_VAR_EXPANSION` 또는 `options.disableVarExpansion`이면 펼치지 않고 `vars` 하나만 쓴다. 아니면 변수 이름 순서대로 데카르트 곱을 만든다(**마지막 변수가 가장 빨리 바뀜**). 변수 값이 문자열 배열이면 원소마다 한 갈래이고, 첫 원소가 문자열이 아닌 배열(객체 배열 등)이면 배열 전체가 한 값이다. `file://`로 시작하는 문자열은 `cliState.basePath`(없으면 작업 디렉터리) 기준 글롭으로 풀려 일치 파일마다 한 갈래(값은 `file://<일치 경로>`)이고, 일치가 0개면 `No files found for variable <이름> at path …`를 던진다 — 글롭 문자 없는 일반 경로도 같은 글롭 호출을 거치므로 **없는 파일은 일치 0개**이고, 이 오류는 단계 목록을 만드는 중(호출 0회)에 나서 평가 전체가 실패한다(CLI 종료 코드 1). 글롭 결과 순서는 `glob` 라이브러리가 정하고 코드에서 정렬하지 않는다. 파일을 실제로 읽는 시점은 R-28(칸마다) | 코드 확인 |
| R-19 | 단계 목록 만들기(C-07) | 중첩 순서: 테스트(R-14 목록 순) → repeat 번호 → 변수 조합 → provider(설정 순) → 열(prompt 순). (테스트, repeat, 조합) 하나마다 `testIdx`를 0부터 1씩 올리며 그 `testIdx`를 모든 열이 공유한다([eval-records](./eval-records.md) R-02). provider는 `test.providers`가, 열은 `test.prompts`가 걸러 통과한 것만 단계가 된다(선택자 문법은 R-17과 같고 provider는 label·id 외 정규화된 id도 비교, 빈 배열이면 전부 제외). 단계의 `prompt.raw`는 `(테스트 옵션 prefix \|\| defaultTest prefix \|\| '') + 원문 + (suffix)`이고 `prompt.template`은 붙이기 전 원문이다. 단계의 `test`는 `{…테스트, vars: 이 조합}`이다. repeat>1이면 `repeatGroupId = test-<R-14 목록 위치>-vars-<조합 위치>`, 단계마다 `repeatIndex`가 붙는다 | 코드 확인 |
| R-20 | repeat 값과 의미 | 테스트별 repeat = `options.repeat`(양의 safe integer일 때) 아니면 전역 repeat. **한 테스트의 repeat 번호 r마다 변수 조합 전체를 다시 돈다**(R-19의 순서). `repeat`가 2 이상이거나 `repeatIndex > 0`인 단계는 캐시 이름공간 `repeat:<r>` 아래서 실행되어 repeat마다 따로 호출·캐시된다([response-cache](./response-cache.md) R-07). 단계 변수에는 `__repeatIndex`(정수), `__evalStepId`(`test-<testIdx>-prompt-<promptIdx>-repeat-<r>`)가 들어가고 평가 id가 있으면 `__evalId`도 들어간다(프롬프트·provider가 참조할 수 있고 저장되는 행의 `vars`에서는 빠진다) | 코드 확인 |
| R-21 | 같은 `testIdx`의 칸들의 공통점 | 같은 `testIdx`의 칸은 같은 변수 조합·같은 repeat 번호·같은 테스트 객체 설정을 공유하고 provider×prompt만 다르다. 열 사이 비교(R-40)와 `repeatGroupId`는 이 성질을 쓴다. 비교 어서션 대상 `testIdx`는 단계 목록을 만들 때 표시된다 | 코드 확인 |

**C. 순서·동시성**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | 단계 실행 순서(C-08) | `test.options.runSerially`인 단계는 **먼저, 목록 순서대로 하나씩** 실행하고, 끝난 뒤 나머지를 동시 구간에서 실행한다. 동시 구간(`async.forEachOfLimit`)은 목록 순서로 시작하되 동시에 최대 `concurrency`개를 돌리므로 **시작 순서는 결정적이고 완료 순서·행 저장 순서는 비결정**이다(`testIdx`·`promptIdx`는 단계 목록 위치로 정해져 완료 순서와 무관). 직렬·동시를 합친 "단계 목록 위치"(진행 표시·`processedIndices`)는 원래 R-19 순서 기준이다. 동시성 1이고 grouped 경로(R-24)면 `[직렬…, 동시…]` 순서로 하나씩 돌린다 | 코드 확인 |
| R-23 | 동시성 보정(`adjustConcurrencyForSerialFeatures`) | 동시성이 2 이상일 때 다음 중 하나면 1로 낮추고 로그를 남긴다: (a) 어느 prompt 원문이 `_conversation` 변수를 템플릿에서 참조(`PROMPTFOO_DISABLE_CONVERSATION_VAR`·테스트 `disableConversationVar`와 무관하게 판정), (b) 어느 테스트가 `storeOutputAs`를 사용, (c) `browser-provider`가 `persistSession: true`. `_conversation` 값은 키 `[provider label(없으면 id), prompt id, promptIdx, test.metadata.conversationId]`별로 누적된 직전 입출력 목록이다(오류 응답은 누적하지 않음) | 코드 확인 |
| R-24 | grouped 경로(동시성 1 **이고** 단계 타임아웃 없음 **이고** `_conversation` 미사용) | 모델 채점 어서션(assertion-family R-26 집합)이 든 테스트는 provider 호출만 먼저 하고 채점을 미뤄, grader provider별로 묶어 처리한다(로컬 모델 재적재 비용을 줄이는 용도). 행은 여전히 단계 목록 순서대로 저장되지만 **grader 호출 순서는 행 순서와 다르다**. 단계 타임아웃이 설정돼 있으면 이 경로는 꺼지고 로그가 남는다 | 코드 확인 |
| R-25 | 스케줄러 경계(범위 밖, 별도 스펙 없음) | 모든 target 호출(`callApi`)과 어서션 grader 호출은 호출 큐를 거친다. 큐는 rate-limit 키(provider `id()` + `apiKey` 끝 4자·`apiBaseUrl`·`region`·`organization`의 해시)별로 하나이고, 큐의 동시 상한은 `-j`(기본 4)에서 시작해 rate limit이 걸리면 절반으로 줄고 성공이 5번 이어지면 1.5배로 회복한다(`-j` 상한, 하한 `PROMPTFOO_MIN_CONCURRENCY` 기본 1, 대기 제한 `PROMPTFOO_SCHEDULER_QUEUE_TIMEOUT_MS` 기본 5분, `PROMPTFOO_DISABLE_ADAPTIVE_SCHEDULER`면 큐 없이 호출). 재시도 기본 정책: 최대 3회, 지수 백오프(1초 기준, 상한 60초, 지터 20%), 서버 `Retry-After` 우선, 하드 쿼터(`quota`)는 재시도하지 않음, `provider.config.maxRetries` 또는 `handlesOwnRetries`로 줄이거나 끔. evaluator가 소유하는 것은 `-j` 값 전달, 단계 타임아웃(R-35), 최대 지속 시간(R-36), `--delay`(R-31), 취소 신호 전달(R-37)이다 | 코드 확인(정책 값·진입점) / 내부 알고리즘 미탐색 |

**D. 한 칸(`runEval`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-26 | 한 칸의 단계 순서(C-09) | ① `provider.delay ??= step.delay` → ② 변수 사본 만들기(R-27) → ③ 프롬프트 렌더(R-28) → ④ (`providerOutput`이 없으면) `copy_working_dir`가 설정된 provider·prompt 설정이면 이 단계 전용 작업공간 복사(생성 실패는 행 예외) → ⑤ 추적 컨텍스트(켜진 경우) → ⑥ provider 호출(R-29) → ⑦ 응답 정규화(eval-records R-04) → ⑧ 대화 기록 갱신(오류 응답 제외) → ⑨ provider 지연 대기(R-31) → ⑩ 행 만들기(eval-records R-04, R-14) → ⑪ 오류·무출력 판정 또는 `transform`·어서션(R-30, R-33) → ⑫ 토큰 합산, `storeOutputAs` 저장 → ⑬ 행 1개 반환. 작업공간 복사본은 어서션이 끝난 뒤(미룬 채점이면 채점 뒤) 삭제되고 응답 `metadata`에 `workingDir`(와 git 저장소면 `workspaceDiff`)가 더해진다. 어느 단계에서든 예외가 나면 R-34 | 코드 확인 |
| R-27 | 변수 준비 | 단계의 `vars`는 `structuredClone(test.vars)`이므로 단계끼리 변수 객체를 공유하지 않는다(렌더가 `file://` 값을 이 사본에 제자리로 읽어 넣어도 다음 칸은 다시 읽는다, config-loading R-46). 이어서 순서대로 덧씌운다: `_conversation`(R-23의 prompt 참조 시, `PROMPTFOO_DISABLE_CONVERSATION_VAR`·`disableConversationVar`가 꺼진 경우) → `registers`(`storeOutputAs`로 저장된 값, **테스트 변수보다 우선**) → `__evalId`·`__evalStepId`·`__repeatIndex`(R-20). 저장되는 행의 `vars`와 어서션·grader에 주는 `vars`는 `__eval*` 세 개를 뺀 값이다 | 코드 확인 |
| R-28 | 렌더(`renderRunEvalPrompt`, [config-loading](./config-loading.md) R-45~R-52) | 단계의 prompt(`raw`=접두+원문+접미)를 `renderPrompt(prompt, vars, nunjucks 필터, provider, skipRenderVars)`로 렌더한다. `renderPrompt`가 변수 `file://`를 읽고(칸마다, 캐시 없음) 프롬프트 함수(`prompt.function`)가 있으면 그 반환이 `raw`(접두·접미 포함)를 **대체**하며 Nunjucks 렌더 순서는 config-loading R-47이다. 렌더된 문자열이 JSON으로 파싱되면 그 값을 `renderedJson`으로 기억해 대화 기록에 쓴다. 결과 행의 `prompt.raw`는 렌더된 최종 문자열, `prompt.config`는 `{…prompt.config, …test.options(repeat 제외)}`다. 렌더·변수 파일 읽기 예외는 R-34(오류 행) | 코드 확인 |
| R-29 | provider 호출 | 호출 대상은 `test.provider`가 `ApiProvider` 인스턴스면 그것(열의 provider가 아니라), 아니면 열의 provider다(그래도 행 수는 열마다 하나). `test.providerOutput`이 있으면 호출 없이 `{output: providerOutput, tokenUsage: 0, cost: 0, cached: false}`가 응답이다. 호출 문맥·`abortSignal`·캐시가 꺼졌을 때의 `bustCache`는 [provider-contract](./provider-contract.md) R-02. 호출은 provider별 큐(R-25)와 `providerRegistry.withProvider`를 거치며, 응답 `metadata`는 직후 JSON 왕복으로 정리된다. 외부 추적 제공자가 켜졌으면 호출 뒤 추적을 가져온다 | 코드 확인 |
| R-30 | 변환(`transformRunEvalResponse`, 응답이 오류·무출력이 아닐 때만) | ① `provider.transform`이 있으면 `transform(provider.transform, output, {vars, prompt})`로 `output`을 바꾸고, 이 값을 `providerTransformedOutput`으로 기억 → ② `test.options.transform`(없으면 `postprocess`)이 있으면 한 번 더 바꾼다(context에 `metadata`: 응답 metadata도). 변환 안 예외는 `Transform failed (<라벨>): <메시지>`로 감싸 던지고, 반환이 `null`/`undefined`면 `Transform function did not return a value`를 던진다 → 어느 쪽이든 칸이 R-34의 오류 행이 된다. 변환 뒤에도 `output`이 null이면 invariant 오류. 인라인 JS 변환은 `--safe-mode`에서 던진다. 어서션별 `transform`은 어서션 안에서 적용([assertion-family](./assertion-family.md) R-06) | 코드 확인 |
| R-31 | provider 지연(`--delay`) | 단계 시작 때 `provider.delay ??= step.delay`로 **그 provider 인스턴스에 처음 한 번만** 값이 정해진다(`provider.delay`가 이미 설정된 provider는 CLI·설정 `--delay`보다 자기 값이 우선, 그 provider에서만). `step.delay`는 `options.delay \|\| 0`이라 항상 숫자이므로 `provider.delay ??= step.delay ?? PROMPTFOO_DELAY_MS`의 환경변수 분기는 `eval` 경로에서 도달하지 않는다(2.1 D-1). 응답이 오면(오류 응답 포함) `response.cached`가 거짓이고 `handlesOwnDelay`가 아니고 `provider.delay > 0`이면 그 ms를 쉰다(취소되면 쉬기만 끝내고 응답은 유지). 대기는 응답을 받은 **뒤**, 어서션 **앞**이고 해당 칸의 동시 슬롯을 잡은 채이며 단계 타임아웃(R-35)에 포함된다. 첫 칸 앞이 아니라 매 비캐시 호출 뒤에 쉬므로 마지막 칸 뒤에도 쉰다. 어서션의 grader 호출에는 이 대기가 없다 | 코드 확인 |
| R-32 | 칸이 행을 돌려준 뒤의 처리 순서(`processEvalRows`) | 행마다(단계 타임아웃 뒤늦은 행은 건너뜀, R-35) ① 변수 이름 수집, 평가 통계(`stats.successes/failures/errors`)·비교 어서션 대상 `testIdx` 표시·어서션 type 수집, `numComplete` 증가 → ② `afterEach` 훅(R-41) → ③ 행 저장(`appendResult`; 저장 예외는 로그만 남기고 `resultPersistenceFailed`, 평가는 계속) → ④ 열 `metrics` 접기([eval-records](./eval-records.md) R-16) → ⑤ 비일시적 대상 오류면 평가 중단(R-39) → ⑥ 진행 표시. 열 목록(`appendPrompts`)은 단계가 끝난 뒤 마지막 저장에서 1초 넘게 지났을 때만 다시 저장한다(진행 중 `metrics`는 최대 1초 지연, eval-records R-19). 같은 단계가 여러 행을 돌려줄 수 있는 구조지만 일반 평가는 단계당 행 1개다 | 코드 확인 |
| R-33 | 채점 연결(`applyRunEvalResponseOutcome`, `gradeRunEvalResponse`) | `response.error`가 있으면 행 `error`, ERROR, 어서션 없이 끝. `output`이 null/undefined면 `No output`(ERROR). 그 밖(빈 문자열 포함)은 R-30 변환 뒤 `runAssertions({prompt: 렌더된 문자열, provider, providerResponse: {…처리된 응답, providerTransformedOutput}, test, vars, latencyMs: response.latencyMs ?? 측정값, assertScoringFunction, traceId})`를 부르고 결과를 행에 옮긴다(`pass`→`success`, `score`, `namedScores`, `gradingResult`, 실패면 `error=reason`·ASSERT; [eval-records](./eval-records.md) R-05~R-07, [assertion-family](./assertion-family.md) R-12~R-24). 채점 단계도 같은 abort·캐시 이름공간으로 감싸지고, 채점 중 취소는 `Aborted: …` ERROR 행이 된다(R-38). `grouped` 경로(R-24)는 채점을 provider 호출 큐에 올려 나중에 한다 | 코드 확인 |
| R-34 | 칸 안 예외(렌더·변수 파일·변환·호출·채점 오류 등) | 평가를 멈추지 않고 그 칸만 `error = 스택(없으면 메시지)`, ERROR, `score=0`, `latencyMs`(호출이 끝났으면 그 값, 아니면 0), `metadata.errorContext`가 든 행이 된다([eval-records](./eval-records.md) R-05 (c)). 로그는 `Provider call failed during eval`(취소로 인한 것은 로그 생략). 예외: CLI 일시정지로 provider 호출이 끝나기 전에 중단된 칸은 행 없이 빈 목록을 돌려 resume 대상으로 남는다(R-38). `beforeEach` 훅 예외는 칸 안이 아니라 호출부에 `catch`가 없어 평가 전체로 전파된다(훅이 실제로 던지는 조건은 script-bridges) | 코드 확인 |

**E. 시간 제한·취소**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-35 | 단계 타임아웃(`timeoutMs` = `options.timeoutMs \|\| PROMPTFOO_EVAL_TIMEOUT_MS`, 0이면 없음, C-10) | `beforeEach` 훅 → 렌더 → provider 호출 → 지연 대기 → 어서션(미룬 채점이면 provider 호출까지)이 도는 동안의 시계다. 칸마다 자체 `AbortSignal`을 만들어 호출에 전달하고, 제한 안에 행이 만들어지지 않으면 abort 후 **재시도 없이** 그 칸을 `Evaluation timed out after <ms>ms: Error: Evaluation timed out after <ms>ms`, `latencyMs=<ms>`, `response`·`metadata` 없는 ERROR 행으로 저장하고 `stats.errors`, 열 `testErrorCount`·`totalLatencyMs`만 올린다([eval-records](./eval-records.md) R-08). 늦게 도착한 원래 행은 저장하지 않는다. 행이 만들어진 뒤의 저장·`afterEach`는 시계 밖이다. 한 칸이 시간 초과여도 다른 칸은 계속된다. provider가 abort를 무시해도 시간 초과 행은 바로 저장된다(호출 자체는 백그라운드에서 끝까지 갈 수 있음, 원본 테스트 사례 이름 `should not block timeout rows when a provider call does not settle after abort`) | 코드 확인 |
| R-36 | 최대 지속 시간(`maxEvalTimeMs` = `options.maxEvalTimeMs ?? PROMPTFOO_MAX_EVAL_TIME_MS`, 0 이하면 없음) | `evaluate()` 시작 시계다(준비·훅·`beforeAll` 포함). 시간이 되면 전체 평가 `AbortSignal`을 abort하고 `Evaluation stopped after reaching max duration (<ms>ms)` 경고를 낸다. 진행 중이던 칸은 abort 오류를 담은 ERROR 행이 되고(원본 테스트 열람: 오류 문자열에 abort 메시지 포함), 시작하지 못한 칸(`processedIndices`에 없는 단계)은 마무리 때 `Evaluation exceeded max duration of <ms>ms`, `latencyMs=시작 이후 경과 시간`인 ERROR 행으로 채운다. 이어서 열 사이 비교는 abort 때문에 못 끝낸 `testIdx`를 `Aborted:` ERROR로 표시하고(시간 초과면 그 뒤 마무리 계속), `afterAll`·`save`가 실행되어 **정상 종료와 같은 경로**로 끝난다(결과적으로 종료 코드는 R-47: 오류 행이 있으므로 기본 100) | 코드 확인 / 진행 중 칸의 중복 행 가능성은 확인 한계 |
| R-37 | 취소 신호의 종류와 결과 | 칸이 받는 `abortSignal` = 호출자 `abortSignal`(+ 최대 지속 시간 컨트롤러 + CLI 일시정지 신호). 대상 불가용(R-39)은 별도 컨트롤러라 provider에게는 가지 않고 루프만 멈춘다. 취소 뒤 흐름: 루프의 `checkAbort()`가 `Operation cancelled`를 던져 시작 전인 칸을 멈추고, 호출자 취소·CLI 일시정지면 `Evaluation interrupted, saving progress...`와 함께 `setVars`·열 `appendPrompts`만 하고 돌아온다(`save`·`afterAll`·시간 초과 행·비교는 하지 않는다), 최대 지속 시간이면 R-36, 대상 불가용이면 열·vars를 저장하고 돌아온다. 취소가 아닌 예외는 평가 전체를 실패시키고 진행 표시를 정리한 뒤 던진다(CLI 종료 코드 1) | 코드 확인 |
| R-38 | CLI Ctrl+C 일시정지(`--no-write`가 아닐 때만, C-11) | 첫 SIGINT: `paused=true`, `Pausing evaluation... Press Ctrl+C again to force exit.`, 일시정지 신호 abort, 10초 뒤에도 안 끝나면 `Evaluation shutdown timed out, force exiting...`과 함께 `process.exit(130)`. 둘째 SIGINT: 즉시 `Force exiting...`, `process.exit(130)`. `doEval`은 SIGINT만 다룬다(SIGTERM은 `--watch` 모드의 감시자 종료에만 쓰인다). 일시정지 시점에 **provider 호출이 아직 끝나지 않은 칸**은 행 없이 중단되어 resume이 다시 한다. **provider 호출이 끝난 칸**은 행으로 남는다: 미룬 채점(R-24)은 끝까지 채점하고, 그 밖은 채점 중 abort를 감지하면 `Aborted: <메시지>` ERROR 행으로 저장된다(응답은 보존, 정적 추적). 일시정지로 끝나면 `Evaluation paused. ID: <id>`와 `promptfoo eval --resume <id>` 안내를 찍고 **통계·표·공유·`-o` 출력·종료 코드 판정을 건너뛰어** 종료 코드가 0이다. `--no-write`이거나 라이브러리 호출이면 이 핸들러가 없다 | 코드 확인 / `Aborted:` 행은 정적 추적 |
| R-39 | 비일시적 대상 오류 | 행의 `response.metadata.http.status`가 401·403·404·501이면(`NON_TRANSIENT_HTTP_STATUSES`; 상태를 `metadata.http`에 싣는 provider만 해당: `http`, `openai` chat·responses 등은 코드 확인, 나머지 provider는 미확인) 그 행은 정상적으로 저장·집계된 **뒤** `Target returned HTTP <status>. Aborting scan - this error will not resolve on retry.`와 함께 평가를 중단한다(남은 칸은 행 없이 사라지고 `save`·`afterAll`·비교도 건너뜀). 이 상태는 CLI 종료 코드를 정한다(R-47) | 코드 확인 |

**F. 비교·훅·마무리**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-40 | 열 사이 비교의 위치 | 모든 단계가 끝난 뒤, `select-best`가 있는 `testIdx`들을 `testIdx` 순서로 하나씩(각 모델 호출 1회, repeat 이름공간 적용), 그다음 `max-score`가 있는 `testIdx`들을 처리한다. 한 `testIdx`는 변수 조합·repeat 하나이므로 **repeat마다 따로 비교**한다. 비교 입력은 저장소에서 읽은 그 `testIdx`의 행들(resume이면 이전 실행의 행 포함, retry면 대체되는 옛 ERROR 행은 제외). 계산·병합 규칙은 [assertion-family](./assertion-family.md) R-49~R-52, 열 `metrics` 보정은 [eval-records](./eval-records.md) R-17 | 코드 확인 |
| R-41 | `extensions` 훅 호출 위치만(규칙은 [script-bridges](./script-bridges.md)) | `beforeAll`: R-13 ④(열·테스트 목록 구성 전, 반환된 `suite`가 이후 실행에 쓰임). `beforeEach`: 칸 실행 직전(`runEvalInternal` 앞), 반환 `test`가 그 단계의 테스트가 됨. `afterEach`: 칸 행이 완성된 뒤, 행 저장·`metrics` 접기 **앞**(훅이 `namedScores`·`metadata`·`response.metadata`를 바꿀 수 있고, 훅 예외는 로그만 남기고 훅 수정 없이 저장). `afterAll`: 비교·시간 초과 행 뒤, `save` 앞(저장소의 모든 행을 읽어 전달) | 코드 확인 |
| R-42 | 마무리와 종료 처리 순서 | `evaluate()`: 열 `appendPrompts`(진행 중에는 최대 1초 간격) → 진행 표시 정리 → (시간 초과면 R-36의 행) → `setVars`(변수 이름 순서: 설정·변환된 변수 먼저, 행에서 발견된 것은 뒤에 추가) → `afterAll` → 소요 시간 `setDurationMs` → `save()`(persisted일 때). 이후 `doEval`: 재시도 정리(R-45) → 일시정지면 종료(R-38) → 메모리 행 비우기(persisted일 때) → 공유 시작(백그라운드, 조건이 맞을 때) → `getStats()` → 표(`--table`, 로그 레벨이 debug가 아니고 행 500 미만일 때) → 요약(+repeat 안정성, R-52) → 공유 완료 대기 → `-o` 출력 파일 기록 → 종료 코드 판정(R-47). 출력·공유 내용은 results-store·hosted-integration | 코드 확인 |

**G. 재개·재시도·watch**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-43 | `--resume [evalId]`(C-12) | 대상은 `evalId` 또는 가장 최근 평가(`latest`). 저장된 평가의 `config`를 `resolveConfigs(저장된 provider 필터, config)`로 다시 해석해 `testSuite`를 만들고, 설정 파일·CLI 필터·`--var`·`--grader`는 쓰지 않는다. `cliState.resume = true`로 `evaluate`가 저장된 열(provider·prompt 정의·`metrics`)을 복원한다. 단계 목록(R-13 ⑨)은 **원래 평가와 같은 순서로 다시 만들어진 뒤**, `eval_results`에 이미 있는 `(testIdx, promptIdx)` 칸은 모두 제거된다(`Resuming: skipping <n> previously completed cases`; 완료 목록 조회가 실패하면 경고 후 전체를 다시 돌림). 따라서 **ERROR·`Aborted:` 행도 완료로 취급되어 다시 돌지 않는다**(재실행은 R-45). 복원한 열이 현재 정의와 어긋나면(provider 순서·selector·prompt 정의) `Cannot resume evaluation because …`로 실패한다. 이전 평가에 `testCacheHitCount`가 없으면 행을 훑어 채운다. JSONL 출력은 이어 쓴다. 새 칸이 끝나는 대로 같은 `Eval` 레코드에 행·열 `metrics`가 더해지고 종료 처리는 R-42, 종료 코드는 R-47(누적 통계 기준) | 코드 확인 |
| R-44 | resume이 복원하는 것과 아닌 것 | 복원(재적용): `repeat`·`cache`·`maxConcurrency`·`delay`·`timeoutMs`·`maxEvalTimeMs`(저장된 `runtimeOptions`/저장 설정), `filterRange`, provider 필터. **CLI의 `-j`·`--repeat`·`--delay`·`--no-cache`·`--filter-*`(range·provider 포함)·`--var`·`--grader`·`--tag`는 무시**(range·provider는 경고). 복원하지 않는 것: `--filter-first-n/pattern/sample/metadata/failing*`(저장 안 되고 resume에서 적용도 안 됨 — 저장된 `config.tests`는 필터 전 목록이므로 부분집합으로 시작한 평가를 resume하면 필터 밖 테스트가 대상에 들어오거나 `testIdx` 대응이 어긋날 수 있다: 추론, 문서도 "other transient filters … are not restored"라고 적음). prompt는 **저장된 열의 텍스트(raw·label·template·config)를 쓴다**(정적 추적: 열 복원이 현재 파일 대신 저장 스냅샷을 쓰므로 resume 사이에 prompt 파일을 고쳐도 반영되지 않음, 호출 가능한 prompt가 있으면 현재 정의와 정확히 일치해야 함). 반면 **변수 `file://`(예: `vars: {skill: file://SKILL.md}`)는 칸마다 현재 파일을 읽으므로 resume 전후 칸이 서로 다른 파일 내용으로 돌 수 있다**. provider 인스턴스는 저장된 설정에서 새로 만들어진다(설정 파일을 고쳐도 반영되지 않지만 `file://` provider 모듈·환경변수는 현재 것이 쓰이고, 열 일치 검사는 provider 식별자·prompt 정의만 비교하므로 그 차이는 감지되지 않음) | 코드 확인 / 필터 복원 부재·prompt 스냅샷은 정적 추적·추론 |
| R-45 | `--retry-errors`(`doEval`) 및 `promptfoo retry <evalId>`(비교용) | `eval --retry-errors`는 **가장 최근 평가**의 ERROR 행 id를 모으고(없으면 `No ERROR results found in the latest evaluation`을 알리고 그 평가를 그대로 돌려줌 — 종료 코드 판정도 없음, 0), R-43과 같이 저장 설정으로 resume 모드를 켜되 `retryMode=true`로 완료 목록에서 ERROR 행을 **뺀다**(그 칸만 다시 돈다. `Aborted:`·시간 초과·`No output` 행 포함). 새 행이 저장되는 동안 옛 ERROR 행은 지워지지 않고(비교 어서션은 옛 ERROR 행을 입력에서 제외), 평가가 정상 끝나고 일시정지가 아니면 `deleteErrorResults`로 옛 ERROR 행을 지운 뒤 `recalculatePromptMetrics`로 열 `metrics`를 다시 계산한다(`derivedMetrics`는 다시 적용 안 됨, [eval-records](./eval-records.md) R-24). 정리가 실패해도 재시도 결과는 남고 경고만 한다. 재시도 후에도 ERROR인 칸은 다음 재시도 대상이 된다. `promptfoo retry <evalId> [-c 설정] [--max-concurrency] [--delay] [--share]`는 같은 `evaluate()`를 `-c`를 줄 수 있는 별도 명령으로 부르며 종료 코드 판정이 없고 실패하면 1이다(results-store 소관) | 코드 확인 |
| R-46 | `--watch`(비resume, C-13) | 첫 실행이 끝난 뒤 감시자(chokidar)를 한 번 만든다. 감시 대상: 설정 파일들, 문자열·`{id}` 형태의 `file://` prompt 경로, 문자열 `file://` provider 경로, 테스트 소스(`--tests`/`--vars` 값 또는 설정 `tests`와 소스별 경로, 테스트가 가리키는 중첩 `file://` 변수 파일 포함). **`defaultTest`·시나리오·어서션 `value`·변환·확장 파일, provider 모듈이 import하는 파일은 감시하지 않는다**. 변경이 감지되면 CommonJS 모듈 캐시를 지우고 구성을 처음부터 다시 읽어 **새 `Eval`로** 전체를 다시 실행한다(재개 아님, 이전 실행과 독립). 변경 이벤트마다 재실행을 시작하며 실행 중 재실행을 막는 잠금은 없다. 설정·이메일·`EvalRunError`·프롬프트 제안 거부 오류는 로그만 남기고 감시를 계속한다. CLI는 감시자가 닫힐 때까지(SIGINT·SIGTERM 한 번) 프로세스를 유지한다. **watch 모드에서는 종료 코드 판정(R-47)이 실행되지 않는다**. 감시 경로를 못 찾으면 실패한다 | 코드 확인 |

**H. 종료 코드**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-47 | 정상 종료한 CLI `eval`(비watch·비일시정지)의 통과율 규칙(C-01) | `successes/failures/errors`는 `evalRecord.getStats()`(열 `metrics`의 pass·fail·error 개수 합, [eval-records](./eval-records.md) R-09, R-23)이고 `passRate = successes / (successes + failures + errors) × 100`. `PROMPTFOO_PASS_RATE_THRESHOLD`(기본 100, 유한하지 않은 값이면 100)보다 **작으면**, 또는 대상 불가용 중단(R-39)이 있으면 `process.exitCode = PROMPTFOO_FAILED_TEST_EXIT_CODE`(기본 100, safe integer가 아니면 100; **0으로 두면 실패해도 0**). 임계값 환경변수를 명시했을 때만 `Pass rate x% is below the threshold of y%`를 출력한다. 통과율 조건만 걸렸으면 곧바로 돌려주고, 대상 불가용이면 정리까지 한 뒤 끝난다. 통과율이 임계값 이상이면 코드는 건드리지 않는다(0). 행이 0개이면 `passRate`가 NaN이라 비교가 거짓이어서 0이다. 라이브러리 호출(`eventSource`가 cli가 아님)은 종료 코드를 설정하지 않는다 | 코드 확인 |
| R-48 | 그 밖의 종료 코드 | 0: 정상(R-47 비해당), 일시정지(R-38), watch(R-46), 실패 행이 없고 임계값 이상, `--retry-errors`인데 ERROR 없음. 1: 옵션 오류(R-01)·상충(R-02)·API 키 누락(R-09)·설정 해석 오류(`ConfigResolutionError`)·`EvalRunError`·그 밖의 던져진 예외(평가 중 예기치 않은 예외 포함). 2: `--interactive-providers`. 100(기본): R-47. 130: 두 번째 Ctrl+C 또는 일시정지 10초 초과. `shutdownGracefully`는 종료 코드를 보존한다(강제 종료 타이머도 `process.exitCode`로 끝) | 코드 확인 |
| R-49 | 종료 코드가 세는 것 | 통계는 **행(칸) 단위**다. repeat는 칸이므로 `--repeat 5`에서 1건이 실패하면 통과율 80%다. 오류 행(provider 오류·타임아웃·`No output`·`Aborted:`)은 `errors`로 분모에 들어가므로 **assert 실패와 provider 오류를 종료 코드로 구분할 수 없다**(둘 다 100). `select-best`·`max-score`에서 지는 열은 실패로 바뀌어(eval-records R-17) 분모·실패에 들어가므로 비교 어서션을 쓴 평가는 모든 칸이 "정상"이어도 기본 100이 나온다. resume이면 이전 실행의 행까지 누적한 통계다. 대상 불가용 판정은 평가의 **모든 저장 행**(이번 실행 이전 행 포함)에서 `http.status` 401·403·404·501을 찾으므로 resume 뒤에도 같은 행이 남아 있으면 다시 잡힌다 | 코드 확인 / resume 재판정은 쿼리 읽기에 근거 |

**I. 비용·호출 수·반복**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-50 | target 호출 수 | 캐시가 없을 때 target 호출 수 ≈ 칸 수 = Σ(테스트) `repeat(테스트) × 변수 조합 수 × (테스트 필터를 통과한 열 수)`. 열 수 = provider별 허용된 prompt 수의 합(R-17; `--suggest-prompts`로 고른 변형도 prompt 수에 든다), 변수 조합 수 = 배열 변수 길이와 `file://` 글롭 일치 수의 곱(R-18), `test.providers`·`test.prompts`가 열을 줄인다. `providerOutput`이 있는 테스트는 호출 0. 캐시 적중 칸은 호출 없이 `cached`(비용은 `cost` 유지·`incurredCost` 0, [response-cache](./response-cache.md)). 스케줄러 재시도(R-25)와 provider 자체 재시도는 이 수에 더해질 수 있고 `numRequests`에 반영되는 방식은 provider-contract R-05. `copy_working_dir`·에이전트 provider는 칸마다 도구 호출이 여러 번일 수 있다(provider 소관) | 코드 확인(식) / 재시도 합산은 추론 |
| R-51 | grader 호출 수 | 칸마다 모델 채점 어서션 하나당 grader를 최소 1회(`g-eval`은 기준 수만큼, assertion-family R-48), 결정적·코드 어서션은 0회(`webhook`은 HTTP 1회). `select-best`는 `testIdx`당 grader 1회(열 수와 무관), `max-score`는 모델 호출 0. 합: 칸 수 × (그 테스트의 모델 채점 어서션 수) + `select-best`가 있는 `testIdx` 수. grader 비용은 행 `cost`에 없고 토큰만 `tokenUsage.assertions`에 남는다([eval-records](./eval-records.md) R-11). repeat는 칸 수를 곱하므로 grader 호출도 같은 비율로 는다. `--suggest-prompts`의 제안 모델 호출 n회는 이 합에 들지 않는 평가 전 별도 비용이고(R-12), 고른 변형은 prompt 열을 늘려 이후 칸 수(R-50)를 키운다 | 코드 확인 |
| R-52 | repeat로 분산을 보는 방법과 한계 | repeat마다 호출·채점·캐시가 따로 일어나므로(캐시가 꺼졌거나 첫 실행일 때) 칸마다 별개의 호출 결과를 얻는다. 같은 설정으로 **다시** 돌리면 캐시가 켜진 한 repeat마다 같은 캐시 항목이 적중해 원래 결과가 그대로 재현된다(분산 측정은 `--no-cache` 또는 첫 실행의 저장 결과로만 가능, [response-cache](./response-cache.md) R-07). 평가 종료 요약의 "Repeat stability"는 `repeatGroupId`가 있는 행만 `(repeatGroupId, promptIdx, provider id, provider label)` 그룹으로 모아 `passed/failed/errors/cached`와 `passRate = passed/(passed+failed)`를 구한다. 오류 행은 `errors`로 세고 통과율 분모에서 뺀다. 그룹에 통과와 실패가 모두 있으면 `unstable`. 캐시된 행이 하나도 없는 그룹에만 95% Wilson 구간을 붙인다. 점수(`score`)의 평균·분산은 계산하지 않는다(열 `metrics.score`는 합). 요약은 불안정 그룹 5개까지만 출력한다 | 코드 확인 |

- 불변식:
  - 같은 입력(설정·테스트 파일·CLI 필터·시드 지정 sample)이면 **단계 목록의 내용과 순서, `testIdx`·`promptIdx`·`repeatGroupId`는 같다**. 단, 변수 `file://` 글롭 순서(R-18), `transformVars`의 `uuid`(R-16), 시드 없는 `--filter-sample`(R-06), 시나리오·테스트 파일이 읽을 때마다 같은 순서로 풀리는지(config-loading 확인 한계)는 예외다.
  - 칸의 시작 순서는 결정적이지만(R-22) 완료 순서·행 저장 순서·grader 호출 순서(R-24)는 아니다. `-j 1`이면 칸이 목록 순서로 하나씩 돈다(단 `runSerially` 테스트가 먼저, R-22).
  - 한 칸의 실패는 다른 칸을 멈추지 않는다. 평가 전체를 멈추는 것은 호출자 취소·CLI 일시정지, 최대 지속 시간, 대상 불가용(R-39), 칸 밖 예외(R-37)뿐이다.
  - 행은 한 번 저장되면 resume이 다시 돌리지 않는다. ERROR 행을 다시 돌리는 방법은 `--retry-errors`뿐이다(R-43, R-45).
  - 종료 코드는 `PROMPTFOO_PASS_RATE_THRESHOLD`가 100일 때 "모든 칸이 통과"가 아니면 100이다. watch·일시정지·라이브러리 호출은 예외.
- 미결정: 없음.
- 확인 한계:
  - 읽기만 했다(설치·실행 없음). 모든 흐름은 정적 추적이다. R-38의 `Aborted:` 행, R-44의 prompt 스냅샷 사용·필터 비복원, R-49의 resume 뒤 대상 불가용 재판정은 코드 연결을 따라간 결론이다.
  - `async.forEachOfLimit`이 한 반복이 던질 때 진행 중인 나머지 반복을 기다리는지는 라이브러리 동작이라 읽지 않았다. 취소·일시정지·최대 지속 시간으로 루프가 도중에 끊길 때(R-36~R-38) 이미 진행 중이던 칸의 행이 평가가 반환된 뒤에 저장되는지, 마무리의 "최대 시간 초과 행"과 중복 행이 되는지는 이 동작에 달려 있다. 원본 테스트 한 사례(두 칸이 동시에 시작해 모두 abort 오류 행이 되는 경우, `test/evaluator/execution.test.ts:1094`)만 열었다.
  - CLI `--delay`는 스키마에 `prefault(0)`이 있어(`src/types/index.ts` `CommandLineOptionsSchema`) 플래그를 생략했을 때 `EvalCommandSchema.partial()` 파싱 결과가 `0`을 채우는지(채우면 R-03의 `commandLineOptions.delay`·`evaluateOptions.delay`가 CLI에서는 도달하지 않는다)는 zod 4의 `partial()`+`prefault` 동작에 달려 있어 확인하지 못했다. `doEval` 자체의 우선순위(`cmdObj.delay ?? commandLineOptions.delay ?? evaluateOptions.delay ?? 0`)는 코드로 확인했고, 원본 테스트는 `doEval`을 직접 부르는 사례로 `commandLineOptions.delay`가 쓰임을 보인다(이름만 열람).
  - 스케줄러 내부, provider별 `metadata.http.status` 기록 여부(R-39의 해당 provider 전수), `promptfoo retry` 명령의 세부, `copy_working_dir` 작업공간 복사 규칙은 읽지 않았다.
  - 시간은 모두 `Date.now()`와 타이머이므로 사례의 시간 값은 조건으로만 쓴다.

### 1.5 필수 코드 참조

라이선스: MIT(overview 1절). 인용·복사 시 저작권·허가 문구를 유지한다. 줄 번호는 모두 SHA `dfe2d45` 기준이다. 아래 범위 안의 내부 helper 중 `isPromptAllowed`·`isProviderAllowed`·`getProviderPromptOverride`는 R-17·R-19의 글로, `renderPrompt`·`transform`·`runAssertions`·`createEvaluateResult`는 선행 스펙 링크로 풀었다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/commands/eval.ts:25-257` `evalCommand`, `src/node/doEval.ts:79-90` `EvalCommandSchema`, `:1270-1293` 종료 코드, `src/types/index.ts:107-155` `CommandLineOptionsSchema` | 옵션 등록·검증, 종료 코드 판정 블록 | R-01, R-47, R-48 |
| C-02 | `src/node/doEval.ts:338-875` `runEvaluationWithEnv` 앞부분 | 상충 검사, resume·retry 설정 복원, 런타임 옵션 해석, delay→동시성 1, 필터 적용 순서, API 키 점검, 레코드 생성 | R-02~R-11 |
| C-03 | `src/util/eval/filterTests.ts:75-117, 191-368` `splitMetadataFilterValue`, `createSeededRandom`, `filterTests` | 필터 적용 순서, 메타데이터 OR/AND, 시드 PRNG와 Fisher–Yates | R-06 |
| C-04 | `src/evaluator.ts:2875-3086` `buildTestsFromSuite`, `getInitialTests`, `mergeScenarioTest`, `prepareTestVariables`, `applyInputTransform`, `prepareTestCaseForEval`, `resolveDefaultTestProvider`; `src/validation/filterRange.ts:1-49` | 테스트 목록·시나리오 합성, `defaultTest` 병합, `transformVars`, range 문법 | R-14~R-16 |
| C-05 | `src/evaluator.ts:2516-2549` `buildLivePromptColumns`; `src/util/promptMatching.ts:1-72`; `src/util/provider.ts:76-130` | 열 만들기와 prompt·provider 선택자 문법 | R-17, R-19 |
| C-06 | `src/evaluator.ts:2142-2190` `generateVarCombinations` | 변수 조합 규칙 | R-18 |
| C-07 | `src/evaluator.ts:3111-3378` `appendRunEvalOptionsForTestCase`·`ForVars`·`ForProvider`, `createRunEvalOption`, `createRunEvalTest`; `:474-488` | 단계 목록 순서, `testIdx`·`repeatGroupId`, 접두·접미, repeat 정규화 | R-19, R-20 |
| C-08 | `src/evaluator.ts:3696-3731` `adjustConcurrencyForSerialFeatures`; `:4610-4909` `executeEvalSteps`, `runGroupedEvalSteps`, `runSerialEvalSteps`, `runConcurrentEvalSteps`; `:5934-5936` | 직렬→동시 순서, 동시성 보정, grouped 경로 조건 | R-22~R-24 |
| C-09 | `src/evaluator.ts:727-895, 918-1021, 1091-1356, 1646-1697, 1767-2035` `createRunEvalState`, `getEvalRuntimeVars`, `renderRunEvalPrompt`, `callProviderForRunEval`, `callActiveProvider`, `buildCallApiContext`, `applyProviderDelayIfNeeded`, `transformRunEvalResponse`, `runEvalInternal` | 한 칸의 단계 순서, 변수 준비, 호출 대상, 지연, 변환 | R-26~R-31, R-33, R-34 |
| C-10 | `src/evaluator.ts:4507-4608, 3861-3993, 5619-5647, 6031-6073` `processEvalStepWithTimeout`, `addEvalStepTimeoutResult`, `createEvalStepTimeoutResult`, `createMaxDurationTimeoutResult`, `addMaxDurationTimeoutResults`, `evaluate` | 단계 타임아웃, 최대 지속 시간의 신호 구성과 행 | R-35, R-36 |
| C-11 | `src/node/doEval.ts:877-930, 995-1004`; `src/evaluator.ts:4492-4505` `abortIfTargetUnavailable`; `src/util/fetch/errors.ts:373-377` | 일시정지 핸들러, 대상 불가용 상태 목록 | R-37~R-39 |
| C-12 | `src/evaluator.ts:2684-2830` `buildCompletedPrompts`, `:3666-3694` `filterCompletedResumeSteps`; `src/node/doEval.ts:106-142, 438-520, 935-989` | 저장 열 복원·불일치 오류, 완료 칸 제거, retry 정리 | R-43~R-45 |
| C-13 | `src/node/doEval.ts:1188-1269, 1301-1339`; `src/util/testCaseReader.ts:1064-1123` `resolveTestsWatchPaths` | watch 감시 대상·재실행·종료 대기 | R-46 |
| C-14 | `src/util/eval/repeatStability.ts:1-206` | repeat 안정성 그룹·통과율·Wilson 구간 | R-52 |
| C-15 | `src/scheduler/retryPolicy.ts:1-89`; `src/scheduler/rateLimitRegistry.ts:39-48, 142` | 스케줄러 기본 재시도 정책과 환경변수(경계) | R-25 |
| C-16 | `src/evaluator.ts:5739-6029` `_runEvaluation`, `:6108-6224` `evaluateWithResources` | 평가 한 번의 전체 순서와 정리 | R-13, R-37, R-42 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(정적 추적, 실행 없음). 시간·측정값은 조건으로 적는다. provider는 `echo`처럼 외부 호출이 없는 것을 가정하고 캐시·스케줄러는 대체하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-17, R-18, R-19, R-20, R-21 | provider A·B, prompt P1·P2(둘 다 모든 provider 허용), 테스트 t0(`vars: {x: [a, b]}`)·t1(변수 1개 조합), `--repeat 2` | `testIdx` 0~5: (t0, r0, x=a)=0, (t0, r0, x=b)=1, (t0, r1, x=a)=2, (t0, r1, x=b)=3, (t1, r0)=4, (t1, r1)=5. 각 `testIdx`마다 `promptIdx` 0=(A,P1) 1=(A,P2) 2=(B,P1) 3=(B,P2)의 칸 4개, 총 24 단계. `repeatGroupId`는 t0: `test-0-vars-0`·`test-0-vars-1`, t1: `test-1-vars-0`. 단계 시작 순서가 이 순서 |
| T-02 | R-47, R-48, R-49 | 칸 10개: 통과 9·assert 실패 1. (a) 기본 환경 (b) `PROMPTFOO_PASS_RATE_THRESHOLD=90` (c) `PROMPTFOO_FAILED_TEST_EXIT_CODE=7` (d) 칸 10개 모두 통과 (e) 칸 10개 중 provider 오류 1·통과 9 (f) 필터로 칸 0개 | (a) 종료 코드 100 (b) 90% < 90이 거짓이므로 0 (c) 7 (d) 0 (e) 오류 행도 `errors`라 100 (f) 통계 0/0 → `passRate` NaN → 0 |
| T-03 | R-04, R-31 | `--delay 200`, 단일 provider, 캐시 꺼짐, 칸 3개 | `Running at concurrency=1 because 200ms delay …`. 칸마다 응답 후 ≥200ms 대기 후 다음 칸 시작(마지막 칸 뒤에도 대기). 같은 설정을 캐시 켜고 두 번째 실행하면 캐시 적중 칸은 대기 없음. provider 설정에 자체 `delay`가 있으면 그 provider는 그 값을 쓴다 |
| T-04 | R-35 | `evaluateOptions.timeoutMs: 1000`, 칸 3개 중 하나의 provider가 abort를 존중하며 5초 걸림 | 그 칸만 `error`가 `Evaluation timed out after 1000ms`로 시작, `latencyMs=1000`, `response` 없음, 재시도 없음. 나머지 2칸은 정상. 열 `testErrorCount=1`. 종료 코드 100 |
| T-05 | R-36, R-37 | `PROMPTFOO_MAX_EVAL_TIME_MS=3000`, 칸 10개(각 1초), `-j 1` | 3초 무렵 abort. 진행 중이던 칸은 abort 오류가 든 ERROR 행, 나머지 미시작 칸은 `Evaluation exceeded max duration of 3000ms` ERROR 행. 칸 10개 모두 행이 있고 `afterAll`·`save` 실행. 종료 코드 100 |
| T-06 | R-38, R-43, R-44 | 칸 10개(`-j 1`) 중 4개가 끝났을 때 Ctrl+C 한 번 → `promptfoo eval --resume <id> -j 8 --repeat 3` | 일시정지: `Evaluation paused. ID: …`, 종료 코드 0, `-o` 파일·공유 없음. resume: `Resuming: skipping 4 previously completed cases`, 나머지 6칸만 실행. `-j 8`·`--repeat 3`은 무시(저장값 `-j 1`·repeat 1 사용). 같은 평가 id에 행이 이어 쌓임. 일시정지 순간 provider 응답을 기다리던 칸은 행이 없었고 resume에서 다시 호출됨 |
| T-07 | R-45 | 최신 평가에 ERROR 행 2개(칸 (1,0), (3,0)), `eval --retry-errors` | 그 2칸만 다시 호출. 성공하면 새 행이 저장되고 옛 ERROR 행 2개가 삭제되며 열 `metrics`가 다시 계산됨. ERROR 행이 없는 평가에서는 `No ERROR results found in the latest evaluation`을 알리고 아무것도 돌리지 않으며 종료 코드 0 |
| T-08 | R-06, R-07 | 테스트 10개(description d0~d9), (a) `--filter-pattern 'd[0-4]' --filter-first-n 2` (b) `--filter-sample 3 --filter-sample-seed 1`을 두 번 (c) `--filter-sample 3`을 두 번 (d) `--filter-first-n 3` 평가를 `--resume` | (a) 패턴이 먼저: d0~d4 중 앞 2개 d0·d1. (b) 두 실행의 테스트 선택과 순서가 같다. (c) 실행마다 다를 수 있다. (d) resume은 `--filter-first-n`을 복원하지 않으므로 저장된 `config.tests` 전체(10개)에서 이미 끝난 `(testIdx, promptIdx)`만 빠진다(R-44의 추론 경로) |
| T-09 | R-14, R-15 | `defaultTest: {vars: {a: 1}, assert: [A]}`, 시나리오 1개 `config: [{vars: {b: 2}, assert: [S]}]`, `tests: [{vars: {a: 9}, assert: [T]}]`, 최상위 `tests: [{vars: {c: 3}, assert: [U]}]` | 테스트 2개, 최상위 `u`가 먼저: `vars {a:1,c:3}`, `assert [A, U]`. 시나리오 합성 테스트: `vars {a:9, b:2}`, `assert [A, S, T]`, `metadata.conversationId = __scenario_0__`. `disableDefaultAsserts: true`인 테스트는 `A`를 뺀다 |
| T-10 | R-20, R-52 | `--repeat 3`, 캐시 켜짐, provider가 매번 다른 출력, 칸 1개 → 같은 설정으로 한 번 더 실행 | 첫 실행: provider 3회 호출, `repeatGroupId` 같은 3행. 통과·실패가 섞이면 요약에 `Repeat stability` `unstable`과 95% 구간. 두 번째 실행: 3행 모두 캐시 적중(출력 동일), 구간은 생략되고 `cached results` 메시지. `--no-cache`로 두 번째를 돌리면 새 샘플 3개 |
| T-11 | R-23, R-27 | prompt에 `{{_conversation}}`, `-j 4` | `Setting concurrency to 1 because the _conversation variable is used.` 칸이 목록 순서로 하나씩 돌고 직전 입출력이 `_conversation`에 쌓임 |
| T-12 | R-39, R-47 | `http` provider(또는 `metadata.http.status`를 싣는 provider)의 첫 응답이 상태 401, 칸 20개, `-j 1` | 첫 행은 저장·집계되고 `Target returned HTTP 401. Aborting scan…` 후 중단. 남은 19칸은 행이 없다. 종료 코드 100(통과율과 무관) |
| T-13 | R-09 | `anthropic:messages:…` provider가 있고 API 키 환경변수가 없음 | `Missing required API keys: ANTHROPIC_API_KEY (<provider 설명>)`와 종료 코드 1, provider 호출 0회, 행 0개 |
| T-14 | R-50, R-51 | provider A(prompt P1·P2·P3 허용), B(`prompts: [P1]`), 테스트 5개 중 1개는 `vars: {x: [a, b]}`, `--repeat 3`, 모든 테스트에 `llm-rubric` 1개, 1개 테스트에 `select-best` 추가 | 열 4개. `testIdx` 6개 × repeat 3 = 18 testIdx × 4 = 72 target 호출. grader 호출 72(`llm-rubric`) + `select-best`가 든 테스트의 testIdx 수(변수 조합이 하나라면 repeat 3개 → 3) = 75. 캐시 없음 기준 |
| T-15 | R-46 | `--watch`, prompt 파일 변경 | 새 `Eval`로 전체 재실행, 종료 코드는 판정하지 않음. `defaultTest.vars`가 가리키는 `file://` 파일을 바꿔도 재실행되지 않음 |
| T-16 | R-08 | `--filter-prompts 'nomatch'` | 로드 중 경고 후 `No prompts found` 오류, 종료 코드 1 |
| T-17 | R-18 | `vars: {skill: file://skills/missing/SKILL.md}`(파일 없음), 테스트 3개 | 칸 호출 0회. 단계 목록을 만드는 중 `No files found for variable skill at path <절대경로>/skills/missing/SKILL.md in directory <basePath>`(설정 로딩이 변수 경로를 절대화해 둠, config-loading R-39)로 평가 전체 실패, 종료 코드 1. 행 0개 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@dfe2d45 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `src/commands/eval.ts:182-247`, `src/node/doEval.ts:79-90`, `src/types/index.ts:84-103, 107-155` | 코드 읽기 |
| R-02 | `src/node/doEval.ts:144-170, 300-332, 371-436, 438-511` `failEvalRun`, `EvalRunError` | 코드 읽기 |
| R-03 | C-02 `src/node/doEval.ts:583-630` | 코드 읽기. `evalCommand`가 등록 시점에 `defaultConfig.evaluateOptions`를 복사하는 부분 `src/commands/eval.ts:25-33` |
| R-04 | `src/node/doEval.ts:632-654`, `src/node/retry.ts:337-370` | 코드 읽기 |
| R-05 | `src/evaluator.ts:4514, 5934, 6034`, `src/envars.ts:639-651`, `src/types/index.ts:301-312` | 코드 읽기 |
| R-06 | C-03; `src/node/doEval.ts:656-713`; `src/util/eval/filterTestsUtil.ts:1-80` | 코드 읽기. `filterTestsByResults`의 매칭 내부는 앞부분만 |
| R-07 | `src/util/config/load.ts:1226-1284`, `src/node/doEval.ts:660-688, 958-961` | 코드 읽기 |
| R-08 | `src/util/eval/filterProviders.ts:57-112`, `src/util/eval/filterPrompts.ts`, `src/util/config/load.ts:1198-1206, 1286-1290`, `src/node/doEval.ts:534-549, 731-736` | 코드 읽기 |
| R-09 | `src/node/doEval.ts:738-758`, `src/util/provider.ts:236-279` `checkProviderApiKeys` | 코드 읽기 |
| R-10 | `src/node/doEval.ts:788-818` | 코드 읽기 |
| R-11 | `src/node/doEval.ts:359-361, 846-875` | 코드 읽기. `runtimeOptions` 정제는 eval-records C-17 |
| R-12 | `src/evaluator.ts:2432-2495`, `src/suggestions.ts:18-118`, `src/node/doEval.ts:227-259, 819-821` | 코드 읽기. 같은 입력으로 n회 부르는 호출이 캐시 키를 공유해 같은 변형을 돌려주는지는 provider 소관이라 미확인 |
| R-13 | C-16 `src/evaluator.ts:5739-6029`, `:6108-6224` | 코드 읽기 |
| R-14 | C-04 `:2875-2940`; `src/node/doEval.ts:686-713` | 코드 읽기 |
| R-15 | C-04 `:2942-3109` | 코드 읽기 |
| R-16 | `src/evaluator.ts:2942-2991`, `src/util/transform.ts:231-290` | 코드 읽기 |
| R-17 | C-05, `src/util/promptMatching.ts`, eval-records C-14 | 코드 읽기 |
| R-18 | C-06 `:2142-2190`, `:3142-3146` | 코드 읽기. 글롭 순서는 라이브러리 소관 |
| R-19 | C-07 `:3111-3378`; `src/util/provider.ts:76-130` | 코드 읽기 |
| R-20 | `src/evaluator.ts:474-488, 3147-3177, 772-788`; response-cache C-05 | 코드 읽기 |
| R-22 | `src/evaluator.ts:5919-5933, 4610-4909` | 코드 읽기. `async.forEachOfLimit`의 시작 순서는 라이브러리 일반 동작(읽지 않음) |
| R-23 | `src/evaluator.ts:160-183, 3696-3731, 808-829` | 코드 읽기 |
| R-24 | `src/evaluator.ts:535-595, 3766-3833, 4704-4805, 5934-5956` | 코드 읽기 |
| R-25 | C-15, `src/scheduler/rateLimitKey.ts:1-46`, `src/scheduler/adaptiveConcurrency.ts:1-60`, `src/evaluator.ts:4067-4096, 1185-1191` | 코드 읽기. 큐 내부·헤더 파싱 미탐색 |
| R-26 | C-09 `:1767-2035`, `src/providers/agentWorkspace.ts:755-773` | 코드 읽기. 작업공간 복사 내부는 미탐색 |
| R-27 | `src/evaluator.ts:727-829, 1794-1817, 1915` | 코드 읽기 |
| R-28 | `src/evaluator.ts:857-895`, `src/evaluatorHelpers.ts:242-546` | 코드 읽기 |
| R-29 | `src/evaluator.ts:918-1021, 1091-1239, 1241-1298` | 코드 읽기 |
| R-30 | `src/evaluator.ts:1646-1697`, `src/util/transform.ts:231-290` | 코드 읽기 |
| R-31 | `src/evaluator.ts:1335-1356, 1794-1798, 3355`, `src/node/doEval.ts:645-654` | 코드 읽기. `PROMPTFOO_DELAY_MS` 참조는 `src/evaluator.ts:1794` 한 곳뿐(`grep`) |
| R-32 | `src/evaluator.ts:4383-4468, 4724-4732, 4863-4875, 4893-4907` | 코드 읽기 |
| R-33 | `src/evaluator.ts:1454-1644` | 코드 읽기 |
| R-34 | `src/evaluator.ts:1990-2105`, `:4366` | 코드 읽기 |
| R-35 | C-10 `:4507-4572` | 코드 읽기 |
| R-36 | `src/evaluator.ts:6031-6073, 4676-4693, 5986-6007, 5589-5597, 5619-5647`, `test/evaluator/execution.test.ts:1094-1174` | 코드 읽기, 원본 테스트 한 사례 열람(모킹, 실행 아님) |
| R-37 | `src/evaluator.ts:5739-5768, 4676-4702, 4911-4960` | 코드 읽기 |
| R-38 | C-11 `src/node/doEval.ts:877-930, 995-1004`; `src/evaluator.ts:1193-1234, 1990-1997, 1532-1644, 650-683`; 원본 테스트 이름 `test/evaluator/execution.test.ts:1031, 1060`(응답·채점이 일시정지 뒤 끝나는 경우 보존) | 코드 읽기. `Aborted:` 행 저장은 신호 연결의 정적 추적 |
| R-39 | `src/evaluator.ts:685-690, 4492-4505, 4456`, `src/util/fetch/errors.ts:373-377`, `src/providers/openai/chat.ts:105-116, 893-994` | 코드 읽기. provider 전수 미확인 |
| R-40 | `src/evaluator.ts:4962-5035, 5070-5261, 5373-5402` | 코드 읽기 |
| R-41 | `src/evaluator.ts:2380-2430, 4350-4381, 4402-4441, 5649-5664` | 코드 읽기 |
| R-42 | `src/evaluator.ts:5546-5617, 4721-4732`, `src/node/doEval.ts:967-1179` | 코드 읽기 |
| R-43 | C-12, `src/evaluator.ts:5781-5842, 3666-3694` | 코드 읽기 |
| R-44 | `src/node/doEval.ts:534-549, 596-625, 660-688, 731-736, 788-821`, `src/util/config/load.ts:1219-1224`, `site/docs/usage/command-line.md`(range 절: "other transient filters ... are not restored", 문서 서술) | 코드 읽기. 필터 비복원은 `config.tests` 저장 시점이 필터 전이라는 추론 |
| R-45 | `src/node/doEval.ts:466-511, 967-989`, `src/models/evalResult.ts:1186-1210`, `src/node/retry.ts:337-440`, `src/commands/retry.ts:11-45`, `src/evaluator.ts:5373-5387`, `src/cliState.ts:30-60` | 코드 읽기 |
| R-46 | C-13 | 코드 읽기 |
| R-47 | C-01 `src/node/doEval.ts:1035-1037, 1270-1293`, `src/models/eval.ts:1482-1510` | 코드 읽기 |
| R-48 | `src/node/doEval.ts:144-170`; `src/commands/eval.ts:182-247`; `src/main.ts:160-198`; `src/mainUtils.ts:211-221` | 코드 읽기 |
| R-49 | `src/node/doEval.ts:1035-1037, 1079`, `src/models/eval.ts:885-930` `findTargetErrorStatus` | 코드 읽기 |
| R-50 | R-17~R-20, R-29 | 식은 단계 목록 구성에서 도출 |
| R-51 | assertion-family R-48~R-51, `src/evaluator.ts:5180-5199` | 코드 읽기와 선행 스펙 |
| R-52 | C-14, `src/util/eval/summary.ts:366-410`, `src/models/eval.ts:765-811, 1512-1540` | 코드 읽기 |
| T-01~T-17 | 해당 R-ID의 근거 | 구현을 읽고 손으로 도출. 실행하지 않음 |

**문서·주석과 구현의 차이** (구현을 사실로 썼다)

| ID | 문서·주석의 서술(위치) | 구현 | 관련 R-ID |
|---|---|---|---|
| D-1 | `PROMPTFOO_DELAY_MS=1000 promptfoo eval`이 `--delay`와 같다(`site/docs/configuration/rate-limits.md:85-93`). [provider-contract](./provider-contract.md) R-08도 `provider.delay ??= 인자 delay ?? PROMPTFOO_DELAY_MS ?? 0`이라 적음 | `evaluate()`가 단계에 넣는 `delay`는 `options.delay \|\| 0`으로 항상 숫자이므로 `delay ?? env`의 환경변수 분기는 `eval`·`retry` 경로에서 도달하지 않는다(`src/evaluator.ts:1794, 3355`). 이 변수가 효과를 내는 곳은 `delay` 없이 `runEval`을 직접 부르는 경우뿐이다 | R-31 |
| D-2 | `--delay`는 "Delay between each test"(`src/commands/eval.ts:93`) | 비캐시 provider 호출 **응답 뒤**에 그 provider 인스턴스의 `delay`만큼 쉬고, 같은 설정으로 `doEval`이 동시성도 1로 강제한다 | R-04, R-31 |
| D-3 | 문서 "exit code `100` when there is at least 1 test case failure or when the pass rate is below the threshold … `1` for any other error"(`site/docs/usage/command-line.md:172`) | provider 오류·타임아웃 행도 실패와 똑같이 `errors`로 세어 100이다. 1은 평가를 시작하지 못했거나 평가가 예외로 끝났을 때다. 임계값을 낮추면 일부 실패가 있어도 0이다 | R-47~R-49 |
| D-4 | `findTargetErrorStatus` 주석은 "401, 403, 404, 500, 501"(`src/models/eval.ts:874-876`) | 실제 목록은 401·403·404·501(`NON_TRANSIENT_HTTP_STATUSES`) | R-39 |
| D-5 | 문서(range 절)는 resume 때 "other transient filters from the original run are not restored"라고 적음 | 코드와 같은 결론이다(`--filter-first-n/pattern/sample/...`는 저장 안 됨). 차이 아님, 문서 서술을 근거로만 인용 | R-44 |
| D-6 | (이 스펙의 이전 서술) `--suggest-prompts`는 평가 전 제안 모델 1회 | 변형 수 n만큼 호출하고 동시성 4(`src/suggestions.ts:67-93`). [prompt-optimize](./prompt-optimize.md) 2.1 ⑤의 지적에 따라 R-12·R-51을 고쳤다 | R-12, R-51 |

### 2.2 코드 읽는 순서

1. `src/commands/eval.ts` `evalCommand`(옵션·action) → `src/node/doEval.ts` `doEvalWithEnv`의 `runEvaluationWithEnv`(338~1299): 설정 해석 → 옵션 결정 → 필터 → 레코드 → `evaluate` → 종료 처리 순서.
2. `src/evaluator.ts` `evaluate`(6247) → `Evaluator.evaluate`(6031)·`evaluateWithResources`(6108) → `_runEvaluation`(5739): 전체 순서(R-13).
3. 단계 목록: `buildTestsFromSuite`(2875) → `buildCompletedPrompts`/`buildLivePromptColumns`(2516) → `buildRunEvalOptions`(2993) → `appendRunEvalOptionsForTestCase`(3111) → `generateVarCombinations`(2142).
4. 실행: `executeEvalSteps`(4610) → `processEvalStepWithTimeout`(4507) → `processEvalStep`(4317) → `runEvalInternal`(1767) → `callProviderForRunEval`(918)·`transformRunEvalResponse`(1646)·`gradeRunEvalResponse`(1532) → `processEvalRows`(4383).
5. 중단·재개: `doEval.ts` 877~1004(SIGINT), `filterCompletedResumeSteps`(3666), `buildCompletedPrompts`(2684).
6. 원본의 전략: 단계 목록을 한 번에 다 만들어 두고(칸마다 `structuredClone`한 변수로 독립 실행) 저장소에 행을 한 칸씩 흘려 넣는다. resume은 "단계 목록을 같은 순서로 다시 만든 뒤 DB에 있는 칸을 빼는" 방식이라 `testIdx`·`promptIdx`가 안정적이어야 한다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드를 복사하지 않았다.

## 적용 메모

사용 목적: 내 스킬(SKILL.md)을 여러 모델에 평가하고 개선하고 모델 적합도를 기록하는 환경에서 평가 한 번의 순서·결정성·중단·재개·반복을 어떻게 가져올지. 원본의 미결정을 해소한 것이 아니다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-19, R-43, R-44 | 칸의 키를 위치 번호(`testIdx`·`promptIdx`)가 아니라 (실행 id, 모델 id, 스킬 버전, 케이스 안정 id, repeat 번호)로 두고, 완료 집합과 resume을 이 키로 관리한다 | 원본 resume은 "같은 설정이면 같은 위치"라는 가정에 기대어 위치 번호로 완료 칸을 뺀다. 필터·시나리오·변수 글롭 순서가 바뀌면 어긋난다(R-44) | resume 입력: 저장된 키 집합 − 완료 키 집합. T-06·T-08(d)는 키 기준으로 새로 작성 |
| R-44 | resume 시 변수 파일(SKILL.md)과 provider 설정이 실행 사이 바뀌었는지 내용 해시로 비교해 바뀌었으면 거부(또는 새 실행으로 분기)한다 | 원본은 prompt 텍스트는 스냅샷으로 고정하지만 변수 `file://`는 칸마다 현재 파일을 읽어 한 평가 안에 서로 다른 스킬 버전이 섞일 수 있다 | 실행 시작 시 입력 파일 해시를 기록, resume이 비교 |
| R-06, R-16, R-18 | 순서를 바꾸는 요소(시드 없는 sample, `transformVars`의 UUID, 글롭 순서)는 정렬·시드 고정으로 결정적으로 만든다 | "같은 설정 → 같은 순서·같은 단계 목록"을 보장하려면 R-06·R-16·R-18의 비결정 요인을 없애야 한다 | 불변식의 예외 목록이 비게 됨 |
| R-22, R-24 | 완료 순서·저장 순서를 결정적으로 보고 싶으면 행을 단계 목록 순서로 정렬해 기록하거나 `-j 1`을 기록용 모드로 둔다. 행에 단계 위치를 별도로 남긴다 | 원본의 시작 순서는 결정적이나 `-j > 1`에서 완료·저장 순서와 grader 호출 순서는 비결정(grouped 경로에서도 다름) | 기록은 순서 대신 칸 키로 조인 |
| R-52, R-10(response-cache) | repeat 분산을 재려면 repeat마다 캐시를 끄거나(`--no-cache`) 캐시 키에 repeat 번호를 넣은 채 **첫 실행의 결과를 보존**한다. 점수(`score`)의 평균·표준편차를 직접 계산해 저장한다 | 원본 안정성 요약은 통과/실패 비율과 Wilson 구간뿐이고 점수 분산은 없으며, 캐시된 재실행은 분산을 0으로 만든다 | 기록 행: (키, repeat별 score·pass·cost·지연), 파생: 평균·표준편차·불안정 플래그 |
| R-47~R-49 | 종료 코드를 "assert 실패 / provider 오류 / 인프라 오류"로 나누고, 모델 비교 실행에서는 `select-best`·`max-score` 패자를 실패로 세지 않는다 | 원본은 오류와 실패를 같은 100으로 묶고 비교 패자를 실패로 센다(R-49). 모델 비교는 "정상"이어도 100이 나온다 | 코드 계약 변경: 종료 코드 표 새로 정의, 통계는 칸 단위 대신 "스킬×모델" 단위 통과율 |
| R-38, R-45 | 일시정지 때 `Aborted:` 오류 행을 만들지 않고 미완료로 남긴다 | 원본은 채점 도중 abort된 칸을 ERROR로 저장해 resume이 건너뛴다(정적 추적) | resume은 "행 없음"과 "ERROR"를 구분, 첫 Ctrl+C는 진행 중 칸을 끝낼지 버릴지 선택 가능 |
| R-31 | 딜레이는 provider별·키별 토큰 버킷으로 두고 `--delay`는 한 값으로 그 전체에 적용한다 | 원본은 비캐시 응답 뒤 고정 sleep + 동시성 1 강제라 느리다. 스킬 평가에서 provider 호출이 길면 비용이 크다 | 스케줄러 스펙 범위 |
