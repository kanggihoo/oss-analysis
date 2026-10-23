---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/commands/optimize.ts
  - src/optimizer/promptOptimizer.ts
  - src/prompts/grading.ts
  - src/prompts/index.ts
  - src/prompts/processors/text.ts
  - src/prompts/processors/python.ts
  - src/suggestions.ts
  - src/evaluator.ts
  - src/node/doEval.ts
  - src/commands/eval.ts
  - src/main.ts
  - src/mainUtils.ts
  - src/util/config/load.ts
  - src/util/promptMatching.ts
  - src/util/json.ts
  - src/util/sanitizer.ts
  - src/models/eval.ts
  - src/models/evalResult.ts
  - src/models/prompt.ts
  - src/cache.ts
  - src/providers/shared.ts
  - src/providers/openai/chat.ts
  - src/providers/anthropic/messages.ts
  - src/providers/defaults.ts
  - src/prompts/processors/javascript.ts
  - src/prompts/processors/executable.ts
  - src/types/index.ts
  - src/types/internal.ts
  - site/docs/usage/prompt-optimization.md
  - site/docs/usage/command-line.md
  - test/optimizer/promptOptimizer.test.ts
  - test/commands/optimize.test.ts
depends:
  - ./eval-run.md
  - ./model-graded-matchers.md
  - ./default-providers.md
  - ./config-loading.md
  - ./eval-records.md
  - ./response-cache.md
status: ready
reimplementation: 미실행
---

# 프롬프트 최적화 (`promptfoo optimize`)

> eval 설정 파일 하나에서 고른 프롬프트 1개 × provider 1개를 설정의 테스트·어서션으로 평가하고, 그 결과(실패·성공 사례와 점수)를 제안 모델에 보내 받은 후보 프롬프트를 같은 테스트로 다시 평가하는 일을 최대 3라운드 되풀이해, 점수가 가장 높은 프롬프트 원문을 로그로 출력하는 명령.

경로는 모두 `repos/promptfoo/` 기준이다. 이번 작성은 코드 읽기만 했고(설치·빌드·실행·네트워크·모델 호출 없음) `실행 확인`은 없다. 라이선스는 MIT(overview 1절)이라 짧은 코드 인용이 가능하지만, 제안 모델에 보내는 시스템 메시지는 본문을 옮기지 않고 구조·규칙으로 풀었다(C-11이 위치).

<!--
작성 메모(삭제하지 않음)
이 스펙 안의 용어
- 기준선: 선택한 프롬프트를 처음 평가한 것. 열 1개.
- 현재 프롬프트: 지금까지 채택된 최선 프롬프트(시작은 선택한 원본). 라운드마다 제안의 기준이 되고, 후보 평가 때 열 하나로 다시 평가된다.
- 후보: 제안 모델이 한 라운드에 돌려준 재작성 프롬프트(최대 3개).
- 열·칸·행: eval-run의 용어(열 = provider×prompt 한 쌍, 행 = 테스트 한 건의 결과). 열 점수 = 그 열 행들의 `score` 합(R-13).
- 검색 집합 / 검증 집합: `--validation-split`이 `tests`를 앞/뒤로 쪼갠 두 묶음. 분할이 없으면 검색 집합 = 전체.
범위: `optimize` 명령 한 개와 그 구현(`optimizePromptTestSuite`). 같은 폴더 선행 스펙은 링크만 하고 복제하지 않는다. 설명용 링크(depends에는 넣지 않음): eval-records R-16(열 `metrics.score` 접기), response-cache R-06(캐시 끔의 범위).
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

1. `promptfoo optimize [-c 설정] [--prompt-index i] [--provider-index j] [--validation-split f]`. 설정 파일을 `eval`과 같은 로더로 읽는다(R-02). 읽은 뒤의 프롬프트·provider 목록에서 인덱스로 **프롬프트 1개 × provider 1개**를 고르고, 테스트가 있는지·함수형 프롬프트가 아닌지 점검한다(R-04, R-05).
2. (`--validation-split`이 있으면) `tests`를 앞쪽 검색 집합과 뒤쪽 검증 집합으로 나눈다(R-16).
3. **기준선 평가**: 선택한 프롬프트 열 1개를 설정의 테스트·어서션으로 평가해 열 점수를 얻는다. 실패한 행은 이후 제안의 근거가 된다(R-08).
4. **라운드 1~3**을 순서대로 돈다(R-07).
   1. 제안 모델을 1회 호출한다. 입력은 현재 프롬프트 원문, 실패 사례(최대 6), 성공 사례(최대 3), 채택 이력(프롬프트·점수·실패 사례)이다(R-09, R-10). 응답의 JSON에서 후보를 최대 3개 추린다(R-11).
   2. `[현재 프롬프트, 후보…]`를 한 평가의 열로 두고 같은 테스트로 평가한다(검증 집합이 있으면 그것도 따로 평가). 열 점수가 가장 높은 것을 고른다(R-12, R-13).
   3. 고른 열의 점수가 현재 프롬프트의 **저장된** 점수보다 **엄격히** 높을 때만 그 프롬프트를 현재 프롬프트로 채택한다. 동점·하락이면 현재 프롬프트와 실패 사례를 그대로 두고 다음 라운드로 간다(R-14).
   4. 후보를 하나도 못 얻으면: 라운드 1은 오류로 끝나고, 라운드 2 이후는 경고를 남기고 그때까지의 최선으로 끝난다(R-11).
5. 종료 조건은 "3라운드를 다 돎" 또는 "라운드 2 이후 후보 생성 실패"뿐이다. 개선이 없어도, 만점이어도 일찍 끝나지 않는다(R-07).
6. 기준선·최선 점수, 개선 여부, **최선 프롬프트 원문**을 로그에 찍고 끝난다. 설정·프롬프트 파일을 고쳐 쓰지 않고, 평가 결과를 DB·출력 파일에 저장하지 않는다(R-15, R-19, R-20).

### 1.2 범위·통합 지점 [필수]

- 제공: 프롬프트 1개 × provider 1개에 대한 "평가 → 제안 → 재평가" 자동 루프, 채택 규칙, 선택·검증 분할 옵션, 비용 구조(R-25, R-26), `eval --suggest-prompts`와의 차이(R-27).
- 제외:
  - 평가 한 번의 실행(칸 만들기, 렌더, 호출, 채점, 동시성, 타임아웃): [eval-run](./eval-run.md). 이 기능은 그 평가를 `evaluate`로 여러 번 부를 뿐이다.
  - 어서션 내부와 모델 채점: [model-graded-matchers](./model-graded-matchers.md)와 assertion-family. 이 스펙은 grader가 이 기능에서 어떻게 정해지는지(R-18)와 호출 수에서의 위치(R-26)만 쓴다.
  - 설정·프롬프트 파일 로딩: [config-loading](./config-loading.md). 프롬프트가 파일일 때의 raw 형태와 렌더 규칙은 그쪽 R-ID를 가리킨다.
  - 제안 모델을 고르는 규칙: [default-providers](./default-providers.md) R-18(이 기능이 쓰는 칸 `suggestionsProvider`와 바꿀 방법이 없다는 것). 복제하지 않는다.
  - 레드팀, 결과 저장·표시, 응답 캐시 내부.
- 외부 의존·선행 계약: 로드된 `TestSuite`(프롬프트·provider 인스턴스·테스트), 평가 함수 `evaluate`(eval-run), 제안 provider(`getDefaultProviders().suggestionsProvider`, `callApi(문자열)`로 부름), 채점 provider(어서션이 정함).
- 소유 상태·부작용: 영속 상태 없음(메모리에만 있는 `Eval` 객체들, R-20). 로그 출력, 종료 코드, telemetry 이벤트(`command_used`: `optimize - started`와 `optimize`, 프롬프트·테스트 수·소요 시간·`improved` 같은 집계값, `optimize.ts:47-54, 94-106`). 제안 호출 1회마다 응답 캐시에 항목이 쓰일 수 있다(R-20). 대상·채점 호출은 사용자 키로 나가며 비용이 든다(R-25, R-26).

### 1.3 인터페이스와 데이터 의미 [필수]

CLI 계약(원문 이름 그대로). 등록된 옵션 전부다(R-01).

| 옵션 | 값·기본값 | 의미·잘못된 입력 |
|---|---|---|
| `-c, --config <path>` | 문자열, 기본 없음 | 설정 파일 경로(글롭 가능, 한 번만 받음). 생략하면 시작할 때 읽어 둔 기본 설정 경로(현재 디렉터리의 `promptfooconfig.*`)를 쓰고, 그것도 없으면 오류(R-02) |
| `--prompt-index <index>` | 정수 ≥ 0, 기본 `0` | 설정을 읽은 뒤 프롬프트 목록의 0부터 센 위치. 범위 밖이면 오류(R-03, R-04) |
| `--provider-index <index>` | 정수 ≥ 0, 기본 `0` | 같은 방식으로 provider 목록의 위치(R-03, R-04) |
| `--validation-split <fraction>` | 0 초과 0.5 이하 수, 기본 없음 | 테스트의 뒤쪽 이 비율을 검증 집합으로 뗀다(R-16). 범위 밖이면 오류 |
| `--env-file, --env-path <path>` | 문자열, 기본 없음 | `.env` 경로. 생략하면 설정의 `commandLineOptions.envPath`를 쓴다(R-02) |
| `-v, --verbose` | 불리언, 기본 false | 모든 명령에 공통으로 붙는 디버그 로그 옵션 |

라운드 수·후보 수·종료 조건·평가 기준(점수 대신 통과율 등)·제안 모델·출력 파일·캐시·동시성·`--grader`·`--var`·필터·`--repeat`를 정하는 옵션은 **없다**(R-01, R-07).

내부 계약(라이브러리 `src/index.ts`로는 내보내지 않는다, R-01).

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `optimizePromptTestSuite(config, testSuite, options)` | `config`: 설정 객체(`outputPath` 등), `testSuite`: 로드된 스위트, `options`: `{promptIndex?, providerIndex?, validationSplit?}` → `PromptOptimizationResult` | CLI가 `resolveConfigs` 결과를 그대로 넘긴다. 라운드 수·후보 수 인자는 없다(R-07) |
| `PromptOptimizationResult` | `baselinePrompt`, `bestPrompt`(둘 다 열 객체: `raw`, `label`, `metrics.score` 등), `baselineValidationPrompt?`, `bestValidationPrompt?`, `candidates`(모든 라운드의 후보 목록), `improved`(bool), `rounds`, `searchTestCount`, `validationTestCount`, `validationSplit?`, 각 `Eval` | `bestPrompt.raw`는 렌더 전 템플릿 원문이다(R-22) |
| 제안 호출 입력(R-09) | 문자열 = JSON 배열 `[시스템 메시지, {role:'user', content: <들여쓰기 2칸 JSON 문자열>}]` | `content` JSON 키: `goal`, `candidateCount`, `currentPrompt`, `failures`, `successes`, `searchHistory`, `responseFormat` |
| 사례 항목 | `{score, success, vars, output, error, gradingReason, namedScores}` | `score`·`success`는 행 값, 나머지는 문자열(없으면 생략). 비밀로 보이는 값은 가려지고 1200자에서 `...[truncated]`로 잘린다(R-09) |
| 이력 항목 | `{failures: 사례 항목[], prompt: 문자열, score: 수}` | 라운드가 끝날 때마다 "그 시점의 현재 프롬프트"를 1건 추가한다. 초기값은 기준선 1건(R-14) |
| 제안 응답 | JSON 객체 `{candidates: [{hypothesis?: string, prompt: string}]}` | 응답 텍스트에서 첫 JSON 객체를 뽑는다(R-11) |
| 후보 프롬프트 객체 | 현재 프롬프트의 모든 필드 + `raw`=후보 문자열, `label`=`<현재 label 또는 'prompt'> [optimized <n>]`, `id`=`sha256(label)` | `n`은 이번 라운드 안의 1부터 센 순번이다(R-12) |

상수(R-07, C-02).

| 이름 | 값 | 쓰임 |
|---|---|---|
| `DEFAULT_ROUNDS` | 3 | 라운드 수(루프 상한) |
| `DEFAULT_CANDIDATE_COUNT` | 3 | 제안에 요청하는 후보 수이자 평가하는 후보 상한 |
| `MAX_FAILURE_EXAMPLES` / `MAX_SUCCESS_EXAMPLES` | 6 / 3 | 제안 입력의 실패·성공 사례 수 상한 |
| `MAX_EXAMPLE_TEXT_LENGTH` | 1200 | 사례의 각 문자열 필드 길이 상한 |
| `VALIDATION_SPLIT_MIN` / `MAX` | 0 / 0.5 | 분할 비율의 열린/닫힌 경계 |

### 1.4 행동 규칙과 남은 질문 [필수]

선택·입력 검증

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `promptfoo optimize` 등록 | 최상위 명령 `optimize`("Optimize one prompt against one configured provider")가 `main.ts`에서 등록된다. 옵션은 1.3 표의 5개 + 공통 `-v`뿐이다(`--env-file`은 이 명령이 직접 정의하며 값을 모으지 않는 단일 값 옵션이다). 위 표에 없는 옵션은 등록돼 있지 않다(commander의 알 수 없는 옵션 오류, 출력 문구는 추론). `-c`를 반복하면 마지막 값이 쓰인다(commander 기본 동작, 추론). 라이브러리 export에는 없다 | 코드 확인(등록·옵션) / 추론(commander 동작) |
| R-02 | 설정 경로·로딩 | 경로 = `--config` 값, 없으면 시작 때 로드한 기본 설정 경로. 둘 다 없으면 `Could not find a config file. Pass --config path/to/promptfooconfig.yaml or run "<init 명령>" to create one.` 오류. 있으면 `resolveConfigs({config:[경로]}, 기본설정)`만 호출한다. 즉 `eval`과 같은 로딩(config-loading R-02~R-44)이지만 CLI의 `--grader`·`--var`·필터·`--prompt-prefix` 같은 값이 없어서 `defaultTest.options.provider`·`prefix`·`suffix`는 설정 파일 값만 쓰인다. `--env-file`이 없으면 설정의 `commandLineOptions.envPath`를 읽어 환경을 추가로 적재한다. 설정에서 온 `commandLineOptions`의 나머지(`cache`, `maxConcurrency`, `repeat` 등)는 쓰이지 않는다(`evaluateOptions`만 R-21처럼 넘어간다) | 코드 확인 |
| R-03 | 옵션 값 파싱 | `--prompt-index`·`--provider-index`: `Number(값)`이 안전한 정수이고 ≥ 0이어야 한다(`1e1`, `0x10`, 공백 포함 `" 2 "`도 `Number`가 정수로 바꾸면 통과). 아니면 commander의 `InvalidArgumentError`로 `--prompt-index must be a non-negative integer.`(옵션 이름만 다름). `--validation-split`: `Number(값)`이 유한하고 `0 < 값 ≤ 0.5`여야 하며 아니면 `--validation-split must be greater than 0 and less than or equal to 0.5`. 이 검사는 CLI 파서에 한 번, 라이브러리 함수 안(`validateOptimizationOptions`)에 같은 조건으로 한 번 더 있다(함수 쪽 메시지는 `promptIndex must be a non-negative integer.` 식) | 코드 확인 |
| R-04 | 프롬프트·provider 선택 | 인덱스는 **설정을 읽고 확장한 뒤의 목록**(`testSuite.prompts`, `testSuite.providers`) 기준이다. 글롭·CSV·`.txt` 분할로 프롬프트가 늘거나 provider 항목이 확장되면 늘어난 목록의 위치다(config-loading R-15, R-21, R-23, R-26). 여러 개가 있어도 CLI가 고르게 하지 않고 기본은 `0`·`0`이다. 범위 밖이면 `Prompt index <i> is out of range. Available prompt indices: 0-<n-1>.`(목록이 비면 `none`), provider도 같은 형식(`Provider index <j> is out of range. Available provider indices: …`). 선택한 provider가 그 프롬프트를 허용하지 않으면(provider의 `prompts` 선택자 또는 `providerPromptMap` 항목이 프롬프트 label·id와 맞지 않음, 규칙은 eval-run R-17) `Prompt index <i> is not configured for provider index <j>.`. 통과하면 스위트를 `prompts=[선택한 프롬프트]`, `providers=[선택한 provider]`로 줄이고, 그 provider의 허용 선택자(provider 항목의 `prompts` 또는 기존 `providerPromptMap` 항목)가 있으면 `providerPromptMap`의 provider 키(label, 없으면 id)에 고정하고 원래 항목이 없었으면 id 키에도 넣어(이후 후보 열도 같은 허용 규칙을 받도록, 선택자가 없으면 맵은 그대로) 로그 `Optimizing prompt index <i> against provider index <j>.`를 남긴다 | 코드 확인 |
| R-05 | 선결 검사(순서대로) | ① 옵션 값 재검증(R-03). ② 프롬프트 0개면 `Prompt optimization requires at least one configured prompt.` ③ 테스트 수 판정이 0이면 `Prompt optimization requires at least one configured test or scenario.` 판정 = `tests` 길이 + 각 시나리오의 `config 수 × (tests 길이, 없으면 1)`의 합이고, `tests`가 비어 있고 `scenarios`가 **없을 때만**(빈 배열이어도 있으면 안 됨) `defaultTest`가 어서션 1개 이상이거나 비어 있지 않은 `vars`를 가지면 1로 센다(어서션 없이 `assertScoringFunction`만 있으면 0). ④ R-04의 선택 오류. ⑤ 선택한 프롬프트에 `function`이 있으면(JS·Python·실행 파일 프롬프트나 Node API 함수) `Prompt optimization currently supports literal string prompts only.` ⑥ 분할이 있고 시나리오가 있으면 `validationSplit is not supported for scenario-based prompt optimization; expand scenarios into explicit tests first.` 오류는 모두 던져지고, CLI는 메시지를 `logger.error`로 찍고 `process.exitCode = 1`로 끝낸다(평가는 하지 않는다) | 코드 확인 |
| R-06 | 내부 평가 한 번의 구성 | 모든 내부 평가는 `evaluate(스위트 복제본, new Eval(설정 + outputPath 제거, {persisted:false}), 옵션)`이다. 스위트는 호출마다 `tests`·`defaultTest`·시나리오의 `assert`·`options`·`metadata`·`vars`·`prompts`·`providers` 배열·객체를 얕게 복사해 넘긴다(평가기가 `defaultTest`를 테스트에 제자리로 합치므로 호출 사이에 어서션이 쌓이지 않게 하는 용도, 이유는 추론). 옵션 = `{...설정의 evaluateOptions, cache:false, eventSource:'library', showProgressBar:false, silent:true}`(R-21) | 코드 확인 / 추론(복제 이유) |

라운드 흐름

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-07 | 라운드 수·후보 수·종료 조건 | 라운드 수 3(`DEFAULT_ROUNDS`)과 후보 수 3(`DEFAULT_CANDIDATE_COUNT`)은 모듈 상수다. CLI·설정·함수 인자 어디서도 못 바꾼다(`generateOptimizedPromptCandidates`는 `candidateCount` 인자를 받지만 `optimizePromptTestSuite`가 넘기지 않고, 루프는 `DEFAULT_ROUNDS`를 직접 쓴다). 종료 조건은 ① 3라운드 완료 ② 라운드 2 이후 후보 생성 실패(R-11)뿐이다. 점수가 이미 최대여도, 직전 라운드에서 채택이 없었어도 다음 라운드를 돈다. 한 라운드는 제안 → 검색 평가 → (검증 평가) → 선택·채택 순서의 순차 실행이다(라운드 사이·평가 사이 병렬 없음) | 코드 확인 |
| R-08 | 기준선 평가 | 검색 집합으로 선택한 프롬프트 열 1개를 평가한다(검증 집합이 있으면 이어서 검증 집합도 따로 평가). 평가 결과 행이 0건이면(필터가 테스트를 모두 걸러냄 등) `No eval test cases ran for the selected prompt/provider — check filters and other test scoping options.`(검증 평가는 `…for the validation split — …`)로 오류 종료한다. 행이 있으면 대상 호출이 전부 실패해 점수가 0이어도 오류가 아니다. 그 열의 행 중 `success=false`를 **결과가 쌓인 순서대로 앞에서 6개**, `success=true`를 앞에서 3개 뽑아 사례로 삼는다(점수 순 정렬 없음, 행 저장 순서는 eval-run R-22대로 비결정). 이력의 첫 항목 = 기준선의 `{실패 사례, 원문 raw, 점수}` | 코드 확인 |
| R-09 | 제안 호출의 입력(각 라운드) | `provider.callApi(문자열)` 한 번. 문자열 = `[시스템 메시지(R-10), {role:'user', content: JSON}]`의 JSON 직렬화. `content`는 들여쓰기 2칸 JSON이고 키는 순서대로 `goal`(고정 문장 "Improve this prompt against the observed evaluation results without changing its intent."), `candidateCount`(3), `currentPrompt`(현재 프롬프트의 **렌더 전 원문 raw**, 자르지 않음), `failures`(≤6), `successes`(≤3), `searchHistory`(이력 전체, 자르지 않음), `responseFormat`(`{candidates:[{hypothesis: 설명 문장, prompt: 설명 문장}]}` 모양 예시). 사례 항목은 `score`·`success`와, `vars`(그 행의 변수 객체)·`output`(응답 출력)·`error`·`gradingReason`(채점 결과의 `reason` 최상위 문자열)·`namedScores`를 각각 비밀 가림(C-13, 깊이 4 초과는 `[...]`) 후 문자열화해 1200자에서 `...[truncated]`로 자른 값이다. **보내지 않는 것**: 렌더된 최종 프롬프트, 어서션 정의(`type`·`value`), 대상 모델 이름, 점수의 척도·방향 설명, 검증 집합의 결과. `vars`에는 `file://` 변수의 파일 **내용**이 들어간다(렌더가 변수 사본에 읽어 넣고 저장 행이 그 사본에서 만들어지므로, eval-run R-27) | 코드 확인 |
| R-10 | 제안 시스템 메시지(C-11)의 규칙 | 구조: 역할 소개 한 줄("구체적인 평가 증거로 프롬프트를 개선한다") + 응답 형식 + 지침. 규칙: ① JSON 객체 하나를 돌려줄 것, 키 `candidates` 배열 ② 각 후보에 `hypothesis`(왜 도움이 될지 한 줄)와 `prompt`(전체 재작성본) ③ 원래 프롬프트의 의도와 필수 동작을 보존할 것 ④ 실패 사례·성공 사례·점수가 붙은 검색 이력을 보고 시도할 가치가 있는 변경을 찾을 것 ⑤ 마크다운 울타리나 JSON 밖의 설명을 쓰지 말 것. **없는 것**: 후보 수·`{{변수}}` 보존·출력 형식(JSON 챗 프롬프트 등) 유지·길이 제한 지시 | 코드 확인 |
| R-11 | 제안 응답 → 후보 | `response.error`가 있거나 `output`이 비면 `Failed to generate optimized prompt candidates: <오류 또는 Unknown error>`. 출력 문자열 전체가 JSON 객체면 그것, 아니면 본문에서 찾은 첫 `{…}`(마크다운 울타리·앞뒤 설명 허용, 닫는 괄호 누락은 보정 시도, C-12)를 쓰며 객체를 못 찾으면 `Failed to parse optimized prompt candidates: …`. `candidates` 배열을 앞에서부터 보며 `prompt`가 문자열이 아니거나, `trim` 후 비었거나, 현재 프롬프트 원문(`trim`)과 같거나, 이미 뽑은 것과 같으면 버리고, 최대 3개를 `trim`한 문자열로 채택한다(`hypothesis`는 문자열이고 비지 않을 때만 유지). 후보가 0개면 `Optimizer provider returned no usable prompt candidates.` **라운드 1**에서 위 어느 오류든 그대로 던져 명령이 끝난다. **라운드 2 이후**에는 provider 예외까지 포함해 `Stopping optimization after round <r-1>: round <r> could not generate new prompt candidates (<원인>). Keeping the best prompt found so far.` 경고만 남기고 루프를 끝낸다. "현재 프롬프트와 같음"만 걸러서, 기준선이나 앞서 기각된 후보와 같은 후보는 다시 평가될 수 있다 | 코드 확인 |
| R-12 | 후보 평가 구성 | 한 라운드의 평가 스위트는 `prompts = [현재 프롬프트, 후보 1..k]`(k ≤ 3), 나머지(테스트·provider·`defaultTest`)는 검색 집합 그대로다. 후보 열은 1.3의 후보 프롬프트 객체 규칙을 따른다(`config` 등 나머지 필드는 현재 프롬프트에서 복사, label이 후보마다 달라 `id`도 달라짐; 라운드가 거듭되면 label이 `… [optimized 2] [optimized 1]`처럼 이어진다). 원래 선택한 프롬프트가 허용돼 있던 모든 곳(고정한 provider 허용 선택자, `defaultTest.prompts`, 각 테스트·시나리오 `config`/`tests`의 `prompts`)에는 현재 프롬프트 label·id와 후보 label들을 허용 목록에 더해 후보 열이 같은 테스트에 걸리게 한다(`extendPromptFilter`). 허용 목록이 없으면(전부 허용) 손대지 않는다. 검증 집합이 있으면 같은 후보로 만든 스위트를 별도 평가로 한 번 더 돌린다. 테스트 `vars`·어서션·provider는 후보가 바꾸지 못한다 | 코드 확인 |
| R-13 | 한 평가 안의 최선 열 고르기 | 열 점수 = 그 열 `metrics.score` = 행 `score`의 **합**이다(평균이 아님, C-16). 숫자가 아니거나 유한하지 않으면 `-∞`로 본다. **통과 행 수·통과율·비용·지연은 비교하지 않는다**(통과 여부는 사례를 실패/성공으로 가르는 데에만 쓰인다). 검증 집합이 없으면 열 순서대로 `점수(후) ≥ 점수(현 최선)`이면 뒤의 열로 바꾸므로 **동점이면 뒤쪽 열(더 뒤 후보)이 이긴다**(현재 프롬프트가 첫 열). 검증 집합이 있으면 열마다 (검색 열, 같은 위치의 검증 열) 쌍을 만들어 첫 쌍(현재 프롬프트)에서 시작해, 뒤 쌍의 **검증 점수가 더 높으면** 그 쌍, 검증 점수가 같고 검색 점수가 `≥`이면 그 쌍, 아니면 유지한다. 열 사이를 비교하는 어서션(`select-best`, `max-score`)은 후보 평가에서는 열이 2개 이상이지만 기준선 평가에서는 열이 1개라 "비교할 출력이 2개 미만" 오류로 처리되므로(assertion-family R-49, 처리 방식은 어서션마다 다름) 두 평가의 점수 척도가 어긋날 수 있다(추론: 1열 기준선은 코드 확인, 어서션 결과는 선행 스펙에서 가져온 규칙) | 코드 확인 / 추론(비교 어서션) |
| R-14 | 채택·증거 갱신·이력 | 라운드 최선 열을 **현재 프롬프트의 저장된 점수**(마지막으로 채택됐을 때 그 평가에서 얻은 값, 이번 평가에서 현재 프롬프트 열을 다시 돌려 얻은 값이 아님)와 비교한다. 검증 집합이 없으면 `최선 점수 > 저장된 점수`일 때만, 있으면 `최선 검증 점수 > 저장된 검증 점수`이거나(같고 `최선 검색 점수 > 저장된 검색 점수`)일 때만 채택한다. 채택하면 현재 프롬프트 ← 그 열의 원문·label·점수, 실패(≤6)·성공(≤3) 사례 ← **그 열의 이번 평가 행**에서 R-08 방식으로 다시 뽑음. 채택하지 않으면 현재 프롬프트·점수·사례는 그대로이고 기각된 후보와 그 실패 사례는 어디에도 남지 않는다. 채택 여부와 상관없이 라운드마다 이력에 "현재 프롬프트의 원문·점수·실패 사례" 1건이 더해진다(그래서 이력에는 채택본만 남고 기각 후보는 없으며, 채택이 없던 라운드는 같은 항목이 되풀이된다). 현재 프롬프트 열 자신이 후보들보다 **엄격히** 높게 나오고 그 값이 저장된 점수보다도 높으면(재측정 잡음 때문에) 그 열이 라운드 최선이 되어, 원문이 같은 채로 저장된 점수만 올라가고 "채택"으로 센다 | 코드 확인 |
| R-15 | 종료와 출력 | `improved` = (검증 집합이 있으면) `최종 검증 점수 > 기준선 검증 점수` 또는 (같고 `최종 검색 점수 > 기준선 검색 점수`), 없으면 `최종 점수 > 기준선 점수`. 최종 = 마지막 현재 프롬프트. 채택마다 이 값들이 엄격히 커지므로 `improved`는 한 번이라도 채택이 있었다는 뜻이다(추론). 로그: 경계선, `Prompt optimization result`, `Baseline search: <label> (<점수>)`, `Best search: <label> (<점수>)`(점수는 `metrics.score` 그대로, 없으면 `n/a`), 분할이 있으면 `Baseline validation: …`·`Best validation: …`, 없으면 노란 글씨 `Validation split disabled; reported improvement is measured on the optimization set.`, `improved`면 `Best candidate improved on the baseline.` 아니면 `Baseline remains strongest.`, 경계선, `Best prompt`, **최선 프롬프트의 `raw`**, 경계선. 후보의 `hypothesis`·라운드별 점수·사용 토큰·비용은 출력하지 않는다. 개선이 없어도 종료 코드는 0이고, 오류만 1이다. 최선이 기준선이면 `raw`는 원문 그대로이고 후보면 `trim`된 후보 문자열이다 | 코드 확인 / 추론(`improved` 의미) |
| R-16 | `--validation-split` | 분할은 **`tests`의 앞뒤 순차 분할**이다(무작위 아님). `tests` 길이가 2 미만이면 분할 없이 전체를 검색 집합으로 쓰고 조용히 넘어간다(출력에 `Validation split disabled…`). 그 밖에는 검증 수 = `min(길이-1, max(1, round(길이 × 비율)))`, 검색 수 = 나머지이며 검색 집합은 앞쪽, 검증 집합은 뒤쪽이다(`defaultTest`·`scenarios` 필드는 둘 다 가진다). 검증 집합은 기준선과 매 라운드에 별도 평가로 돌고(평가 호출 수는 4회 → 8회가 되지만 행 수의 합은 같다, R-25), **선택·채택에서 검증 점수가 우선**이라 순수 홀드아웃이 아니다(R-13, R-14). 제안 모델이 보는 사례·이력은 검색 집합의 결과뿐이다. 검증 평가가 행을 0건 내면 R-08의 오류다. 문서(`prompt-optimization.md`)의 "검증 집합으로 후보 채택을 판단한다"와 일치한다 | 코드 확인 |

모델 선택

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-17 | 제안 모델 | 라운드마다 `getDefaultProviders()`를 새로 불러 `suggestionsProvider`에 R-09 문자열을 `callApi`로 직접 보낸다(컨텍스트·취소 신호 없음, 레지스트리 경유 없음). 어느 모델이 되는지와 지정·변경할 수단이 **없다**는 사실은 [default-providers R-18](./default-providers.md)(환경변수로만 정해지고 `--grader`·`defaultTest.options.provider`의 영향 없음, 같은 표의 R-19는 `generate` 쪽 규칙이라 이 기능과 무관)이 정의한다. 대상 provider·grader와는 독립이라 같은 환경에서 서로 다른 모델이 될 수 있다 | 코드 확인 |
| R-18 | 대상 provider와 grader | 대상 = R-04에서 고른 provider 인스턴스(설정의 `providers[j]`). grader = 어서션이 정한다: `assert[].provider` > 테스트·`defaultTest`의 `options.provider` > 기본 grader 묶음([default-providers R-12~R-17](./default-providers.md), [model-graded-matchers R-09](./model-graded-matchers.md)). `optimize`에는 `--grader`가 없고(R-02), 설정의 값이 그대로 쓰인다 | 코드 확인 |

출력·저장·캐시

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-19 | 결과 쓰기 | 최선 프롬프트는 로그(R-15)에만 있다. 설정 파일, 프롬프트 파일(SKILL.md 포함), 출력 파일을 쓰는 코드가 `optimize.ts`·`promptOptimizer.ts`에 없다(파일 시스템 모듈 import 없음). 파일에 반영하려면 사용자가 로그의 원문을 직접 옮겨야 한다 | 코드 확인 |
| R-20 | 비영속·캐시 | 내부 `Eval`은 모두 `persisted:false`다. 행은 메모리에만 쌓이고(`Eval.addResult`가 DB 삽입 분기를 타지 않음) `Eval.create`·`save`가 불리지 않아 `evals`·`prompts` 등 DB 행이 생기지 않고, `outputPath`를 지워 JSON·JSONL·CSV 출력도 없으며, 공유(share)도 하지 않는다. 앱 시작 때의 DB 마이그레이션은 모든 명령에 공통이라 이 명령에도 있다. **캐시**: 내부 평가는 `cache:false`로 `withCacheEnabled(false)` 안에서 돌아 대상 호출과 grader 호출 모두 응답 캐시를 읽거나 쓰지 않는다([response-cache](./response-cache.md) R-06, 기존 항목은 지워지지 않음). 단 **제안 호출은 평가 밖**이라 이 범위를 받지 않고 프로세스 전체 캐시 상태(기본 켜짐, `PROMPTFOO_CACHE_ENABLED=false`로 끔)를 따르므로, 캐시를 쓰는 provider라면 같은 입력(같은 증거·이력)에는 이전 응답을 재사용할 수 있다. `optimize`에는 `--no-cache`가 없다. 바이너리 응답(이미지·오디오)은 비영속 평가에서도 행을 만들기 전에 blob 저장 단계를 거친다(`evalResult.ts:1026`이 `persist` 분기보다 앞) | 코드 확인 / 추론(제안 호출 캐시 적중은 provider별) / 미확인(blob 저장소가 실제로 쓰이는지) |
| R-21 | 설정의 `evaluateOptions` | 내부 평가 옵션은 설정의 `evaluateOptions` 전체를 펼친 뒤 `cache`·`eventSource`·`showProgressBar`·`silent` 4개만 덮는다. 따라서 `delay`, `maxConcurrency`, `repeat`, `timeoutMs`, `maxEvalTimeMs`, `filterRange`, `generateSuggestions`·`suggestionsCount` 등이 평가마다 그대로 적용된다(`repeat`는 R-25의 행 수에 곱해진다). `extensions`가 있으면 `beforeAll`·`afterAll` 훅이 **내부 평가마다**(최대 4번 또는 8번) 불린다(eval-run R-41), telemetry `eval_ran`도 평가마다 기록된다. `evaluateOptions.generateSuggestions: true`이면 내부 평가마다 `--suggest-prompts`와 같은 대화형 프롬프트 제안이 끼어든다(eval-run R-12, 대화형 환경이 없을 때의 동작은 미확인) | 코드 확인 / 미확인(비대화형) |

`{{변수}}`·템플릿·파일 프롬프트

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | `{{변수}}`·템플릿 처리 | 제안 입력의 `currentPrompt`·사례·출력되는 `bestPrompt.raw`는 모두 **변수 치환 전 템플릿 원문**이다(열의 `raw`는 렌더 전이고 `prefix`/`suffix`는 칸 단계에서 따로 붙으므로 들어 있지 않다, `evaluator.ts:2534-2542`, `:3140-3141`). 후보에 대해 `{{변수}}` 보존을 **검사하거나 되돌리는 코드는 없다**(걸러내는 것은 R-11의 4가지뿐이고 시스템 메시지도 변수 보존을 요구하지 않는다, R-10). 후보 원문은 그대로 새 `raw`가 되어 일반 프롬프트처럼 렌더된다(config-loading R-47, R-48): 변수를 빼면 그 입력이 프롬프트에서 빠질 뿐 오류가 아니고(점수로만 불이익), 정의되지 않은 `{{x}}`는 빈 문자열이 되며, 닫히지 않은 `{{`·`{%`가 있으면 프롬프트 전체가 raw로 감싸져 치환이 일어나지 않고, 문법 오류는 칸 오류 행(점수 0)이 된다(eval-run R-34). 테스트 `vars`는 후보가 바꾸지 못하고 제안 모델은 사례의 `vars`로만 변수 값을 본다 | 코드 확인 |
| R-23 | 프롬프트가 파일 `file://…/SKILL.md`(`.md`)일 때 | 최적화되는 것은 그 프롬프트의 `raw`이고, `.md`면 **파일 전체 UTF-8 내용**(YAML 프런트매터 포함, 분할·트림·가공 없음)이다(config-loading R-20, R-45). 제안 입력 `currentPrompt`는 이 raw 전체를 자르지 않고 JSON 문자열로 이스케이프해 보낸다(절단은 사례 필드에만 있음). 변수 치환 전 원문이라 SKILL.md 안의 `{{`·`{%`가 그대로 보인다. 제안 모델이 돌려준 후보는 "전체 재작성본" 문자열(`trim`)이고, 채택되면 다음 라운드의 `currentPrompt`가 된다. 평가 때는 시드든 후보든 같은 렌더 규칙을 받으므로 SKILL.md 속 예시 코드의 `{{ }}`는 정의되지 않은 변수로 사라지거나 raw 감싸기 대상이 된다(config-loading R-48). 프런트매터를 유지하는지는 검사하지 않는다. 결과는 R-19대로 로그뿐이고 SKILL.md는 바뀌지 않는다. 후보는 `raw`와 `label`(시드 label + ` [optimized n]`)만 바뀌고 `config` 등은 시드에서 복사된다 | 코드 확인 |
| R-24 | 그 밖의 프롬프트 형태에서 무엇이 최적화되나 | ① 인라인 문자열: 그 문자열. ② `.txt`: `---` 줄로 쪼개진 **청크 하나**가 프롬프트이고 인덱스는 쪼갠 뒤의 위치다(config-loading R-21, 같은 SKILL.md를 `.txt`로 두면 프런트매터 구분선에서 쪼개짐). ③ `.json`/`.yaml` 챗 형식·인라인 JSON: 직렬화된 JSON **문자열**이 raw이고 후보도 임의 문자열이라 JSON 유효성·메시지 구조를 검사하지 않는다(유효하지 않으면 렌더 단계 규칙으로 일반 문자열이 된다, config-loading R-47). 제안 입력에는 대상 provider 정보가 없어(R-09) raw가 챗 메시지로 해석된다는 사실은 원문 모양으로만 드러난다. ④ JS·Python·실행 파일·함수 프롬프트: R-05 ⑤로 거부. ⑤ 프롬프트가 아닌 곳에 SKILL.md가 있는 구성(`vars: {skill: file://SKILL.md}`, 에이전트 provider의 `working_dir`·`skills`): 후보 스위트는 `prompts`만 바꾸고 `vars`·provider 설정은 그대로이므로(R-12) SKILL.md는 최적화 대상이 아니다. 에이전트 provider가 그 파일을 어떻게 읽는지는 이 레포 밖이다 | 코드 확인 / 미확인(에이전트 내부) |

비용

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-25 | 대상 provider 호출 수 | 평가 한 번의 호출 수는 [eval-run R-50](./eval-run.md)의 식(열 × 행)이고, 캐시가 꺼져 있어 적중으로 줄지 않는다. 한 열의 행 수를 `T`(= Σ 테스트의 `repeat × 변수 조합 수`, 시나리오·`defaultTest` 단일 테스트 포함, 검증 분할은 `T`를 검색 `S`와 검증 `V`로 나눌 뿐 `S+V=T`)라 하면 기준선 `T`, 라운드 `r`는 `(1 + c_r) × T`(`c_r` = 그 라운드의 유효 후보 수 1~3)이다. 합 = `T × (1 + Σ(1 + c_r))`. 3라운드·후보 3개 최대치는 `T × (1 + 3×4) = 13T`이다(이전 보고 "prompt 열 13회분 × 테스트 수"와 일치). 라운드 `k`(≥2)에서 중단하면 그 라운드 이후는 빠진다. 현재 프롬프트가 매 라운드 열 하나로 **다시** 평가되므로 13열 중 3열은 같은 프롬프트의 재측정이다. 분할을 써도 대상 호출 수는 같다(평가 호출만 늘어남). provider 내부 재시도·에이전트의 도구 호출은 별도로 더해질 수 있다(eval-run R-50) | 코드 확인(식) / 추론(재시도 합산) |
| R-26 | grader·제안 호출 수와 비용 표시 | grader: 위 행(칸)마다 모델 채점 어서션 하나당 최소 1회([eval-run R-51](./eval-run.md), g-eval은 기준 수만큼, model-graded-matchers R-12), 코드 어서션은 0회. 합 ≈ `13T × G`(`G` = 테스트당 모델 채점 어서션 수, 평균), `select-best`는 평가마다 `testIdx`당 1회 추가. 캐시가 꺼져 모두 실제 호출이다. **제안 모델: 라운드당 정확히 1회**(후보 3개를 한 응답에 요청, 응답이 부족하면 더 부르지 않음) → 최대 3회. 최대 총량 ≈ 대상 `13T` + grader `13T×G` + 제안 3. CLI는 토큰·비용·호출 수를 출력하지 않는다(R-15) | 코드 확인 |

관련 진입점: `eval --suggest-prompts`

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-27 | `promptfoo eval --suggest-prompts <n>`(또는 `evaluateOptions.generateSuggestions`)와 `optimize`의 차이 | 두 진입점 모두 제안 provider는 `suggestionsProvider`이고 같은 환경 규칙을 받는다(R-17). 차이는 아래 표다. `eval --suggest-prompts`의 흐름 자체는 [eval-run R-12](./eval-run.md)가 정의한다 | 코드 확인 |

| 항목 | `eval --suggest-prompts <n>` | `optimize` |
|---|---|---|
| 호출 위치 | 평가기 안, 평가 시작 직후(`evaluator.ts:2432-2495`, `suggestions.ts`) | 평가 사이마다 `optimizePromptTestSuite`가 직접 |
| 제안 입력 | **첫 프롬프트의 raw 하나**(`prompts[0]`) + "variant를 만들라"는 고정 메시지. 평가 결과·점수 없음 | 현재 프롬프트 + 실패·성공 사례 + 점수 이력(R-09) |
| 제안 호출 수 | `n`회(1~50, 동시 4개, 호출마다 독립 변형 1개) | 라운드당 1회, 한 응답에 후보 3개 |
| 응답 형식 | 평문(프롬프트만 출력하라는 지시) 그대로 | JSON `candidates`(R-11) |
| 선택 | **대화형 y/n**(기본 아니오)으로 사람이 고름. 하나도 안 고르면 종료 코드 1 | 점수로 자동 선택(R-13, R-14), 대화 없음 |
| 이후 | 고른 프롬프트를 원래 프롬프트 열 뒤에 붙여 **일반 `eval`을 계속**한다(결과 저장·출력·캐시는 `eval` 규칙) | 평가는 비영속·캐시 끔, 결과는 로그 한 번(R-20) |
| 대상 | 프롬프트·provider 선택 옵션 없음(첫 프롬프트만 변형, 모든 provider와 열을 이룸) | 프롬프트 1 × provider 1을 인덱스로 선택(R-04) |
| 라운드 | 1회 | 최대 3라운드 반복 |

- 불변식: 한 실행 안에서 `bestPrompt`의 점수는 기준선 이상이다(전제: 채택은 저장된 점수보다 엄격히 높을 때만, R-14). 설정·프롬프트 파일·DB는 이 명령이 바꾸지 않는다(R-19, R-20). 후보 열을 만들 때 테스트·`vars`·어서션·provider는 바뀌지 않는다(R-12).
- 미결정: 없음.
- 확인 한계: 설치·실행·모델 호출을 하지 않았다(`실행 확인` 없음). 제안 응답이 실제로 어떤 모양으로 오는지(마크다운 울타리를 쓰는 빈도 등), 점수 잡음이 채택에 미치는 정도는 추론이다. commander가 알 수 없는 옵션·잘못된 옵션 값에 찍는 문구와 종료 코드는 라이브러리 소관이라 확인하지 않았다. 비밀 가림(C-13)은 `isSecretField`·`looksLikeSecret`(접두 패턴과 64자 이상 base64류)·`sanitizeJsonString`·`sanitizeObject`의 규칙만 읽었고, 필드 이름 목록 `SECRET_FIELD_NAMES`(`:144-235`)와 URL·헤더 분기는 읽지 않았다(재구현은 C-13 위치를 따른다). 평문 속에 섞인 비밀(문장 안의 키 문자열)은 문자열 **전체**가 `looksLikeSecret`일 때만 가려지는 것으로 읽었다. 비영속 평가의 blob 저장과 `tracing` 설정이 켜진 스위트의 trace 저장은 읽지 않았다. 제안 provider가 JSON 배열 문자열을 챗 메시지로 해석하는지는 OpenAI chat provider(`chat.ts:468`, `parseChatPrompt`)만 확인했고 다른 provider는 provider 소관이다.

### 1.5 필수 코드 참조 [필수]

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/commands/optimize.ts:109-176` `parseValidationSplit`, `parseSelectionIndex`, `optimizeCommand` | 옵션 5개의 이름·기본값·파서와 오류 문구, 액션 오류 처리(`logger.error` + `exitCode=1`) | R-01, R-03 |
| C-02 | `src/optimizer/promptOptimizer.ts:22-29` | 상수 8개(라운드 3, 후보 3, 사례 6/3, 1200자, 기본 인덱스 0, 분할 경계) | R-07, R-09, R-16 |
| C-03 | `src/optimizer/promptOptimizer.ts:82-171` `truncateText`, `stringifyValue`, `sanitizeExampleValue`, `createOptimizationExamples`, `buildCandidateGenerationPayload` | 사례 항목 필드·절단·가림 순서, 제안 입력 JSON의 키와 `goal` 문장, `responseFormat` 모양 | R-09 |
| C-04 | `src/optimizer/promptOptimizer.ts:173-276` `normalizeCandidates`, `generateOptimizedPromptCandidates`, `generateRoundCandidatesOrStop` | 후보 걸러내기 4규칙, 오류 문구 3종, 라운드 1 재던짐/2 이후 경고 후 중단 | R-11 |
| C-05 | `src/optimizer/promptOptimizer.ts:109-117, 308-358` `scoreOf`, `formatScore`, `selectBestPrompt`, `selectBestPromptPair`, `findPromptIndex` | 점수 정규화(-∞), `>=` 동점 처리, 검증 쌍 비교, 열 찾기(raw+label) | R-13 |
| C-06 | `src/optimizer/promptOptimizer.ts:360-431` `createValidationPartition`, `validateOptimizationOptions` | 검증 분할 계산식, 시나리오와 충돌, 옵션 재검증 | R-03, R-16 |
| C-07 | `src/optimizer/promptOptimizer.ts:437-485` `createSelectedOptimizationTestSuite` | 인덱스 선택, 범위·허용 오류 문구, `providerPromptMap` 고정 | R-04 |
| C-08 | `src/optimizer/promptOptimizer.ts:487-629` `extendPromptFilter`, `buildCandidate*`, `createCandidateTestSuite` | 후보 열 객체(label·id 규칙)와 모든 허용 목록 확장 | R-12 |
| C-09 | `src/optimizer/promptOptimizer.ts:631-749` `clone*`, `hasRunnableDefaultTest`, `countConfiguredOptimizationTests`, `createEvaluationOptions`, `assertOptimizationEvalHasResults` | 스위트 복제, 테스트 수 판정, 내부 평가 옵션 4개 덮어쓰기, 0행 오류 | R-05, R-06, R-08, R-21 |
| C-10 | `src/optimizer/promptOptimizer.ts:751-963` `optimizePromptTestSuite` | 선결 검사 순서, 기준선, 라운드 루프, 채택 식, `improved`, 반환 객체 | R-05~R-08, R-12~R-16 |
| C-11 | `src/prompts/grading.ts:133-144` `OPTIMIZE_PROMPT_SYSTEM_MESSAGE` | 제안 시스템 메시지(본문은 R-10의 구조·규칙으로 풀었음) | R-10 |
| C-12 | `src/util/json.ts:334-422` `extractJsonObjects`, `extractFirstJsonObject` | 제안 응답에서 첫 JSON 객체를 뽑는 규칙(통째 파싱 → 본문 스캔 → 괄호 보정) | R-11 |
| C-13 | `src/util/sanitizer.ts:11-15, 144-260, 360-420, 1165-1202, 1357-1560`; `src/util/json.ts:103-132` `safeJsonStringify` | 사례 값 가림: 비밀 필드 이름 집합·비밀 모양 값은 `[REDACTED]`, JSON 문자열은 파싱해 같은 규칙, 깊이 4 초과 `[...]`, 순환 참조 안전 직렬화 | R-09 |
| C-14 | `src/prompts/processors/text.ts:58-71` `processTemplateFile`; `src/prompts/index.ts:49-51` | `.md` 프롬프트 파일 전체가 raw 하나가 되는 규칙(상세는 config-loading R-20) | R-23 |
| C-15 | `src/evaluator.ts:2432-2495`; `src/suggestions.ts:21-118` `generatePrompts` | 비교용 `eval --suggest-prompts`의 제안 입력·호출 수·대화형 선택 | R-27 |
| C-16 | `src/evaluator.ts:4272-4280` `updatePromptMetricsForRow` | 열 점수 = 행 `score` 합(`metrics.score += row.score`) | R-13, R-25 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. 같은 보장을 다루는 원본 테스트 사례명은 2.1에 적었고 사례 본문은 `test/optimizer/promptOptimizer.test.ts`의 `:338-386`, `:1024-1056`만 열었다(테스트를 읽은 것은 실행 확인이 아니다). 점수는 열 점수(행 `score` 합)다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | `-c` 없음, 현재 디렉터리에 기본 설정 없음 | `Could not find a config file. Pass --config …` 오류, 종료 코드 1, 평가 호출 0 |
| T-02 | R-03 | `--validation-split 0`, `0.6`, `abc` / `--validation-split 0.5` / `--prompt-index -1`, `1.5` / `--prompt-index 0` | 앞의 값들은 R-03 오류, `0.5`와 `0`은 통과 |
| T-03 | R-04 | 프롬프트 2개·provider 2개, 옵션 없음 / `--prompt-index 1 --provider-index 1` | 앞은 (0,0) 쌍만 최적화, 뒤는 (1,1) 쌍만. 선택되지 않은 프롬프트·provider는 한 번도 호출되지 않음 |
| T-04 | R-04 | 프롬프트 2개에서 `--prompt-index 2` | `Prompt index 2 is out of range. Available prompt indices: 0-1.` |
| T-05 | R-04 | provider 0이 `prompts: ['B']`만 허용하는데 프롬프트 0은 라벨 `A` | `Prompt index 0 is not configured for provider index 0.` |
| T-06 | R-05 | `tests` 없음, `defaultTest: {}` / `defaultTest.assert`가 1개 있음, `scenarios` 키 없음 / 같은 설정에 `scenarios: []` 추가 | 첫째 오류(`…at least one configured test or scenario.`), 둘째는 테스트 1개로 세어 진행, 셋째는 오류 |
| T-07 | R-05 | 선택한 프롬프트가 `file://p.js`(함수) | `Prompt optimization currently supports literal string prompts only.`, 평가 호출 0 |
| T-08 | R-08, R-09 | 기준선에서 실패 8·성공 5, 한 출력이 3000자, 변수에 `apiKey` 필드 | 사례는 실패 6·성공 3(결과 순서 앞에서부터), 긴 출력은 1200자 + `...[truncated]`, `apiKey` 값은 `[REDACTED]`, 이력 1건 |
| T-09 | R-11 | 제안 응답이 ```` ```json … ``` ```` 울타리 + 설명 문장으로 감싼 JSON, 후보 4개 중 하나는 현재 프롬프트와 같고 하나는 중복 | 첫 JSON 객체를 뽑고 유효 후보 2개만 평가 |
| T-10 | R-11 | 라운드 1의 응답 후보가 모두 현재 프롬프트와 같음 / 라운드 2에서 같은 일이 생김 | 앞: `Optimizer provider returned no usable prompt candidates.`로 명령 종료(코드 1) / 뒤: 경고만 남기고 라운드 1에서 채택한 프롬프트를 최선으로 출력, 종료 코드 0 |
| T-11 | R-13, R-14 | 기준선 4.0. 라운드 1 열 점수: 현재 4.5(재측정), 후보 A 4.5, 후보 B 3.0 | 최선 열 = A(동점이면 뒤쪽), `4.5 > 4.0` → A 채택, 저장된 점수 4.5, 사례는 A 열의 행에서 다시 뽑음 |
| T-12 | R-14, R-15 | 기준선 4.0. 매 라운드 열 점수가 `[현재 4.0, 후보 4.0…]`(전부 동점) | 채택 없음, 3라운드 모두 수행(평가 호출 1+3회), `improved=false`, `Baseline remains strongest.`, 최선 = 기준선 원문, 종료 코드 0 |
| T-13 | R-14, R-15 | 기준선 4.0. 라운드 1 열 점수 `[현재 4.5(재측정), 후보 A 4.2]` | 최선 열 = 현재 프롬프트 열, `4.5 > 4.0` → "채택"(원문 동일), `improved=true`, 출력된 최선 프롬프트가 기준선과 같은 원문 |
| T-14 | R-16 | `tests` 10개, `--validation-split 0.2` / `0.04` / `tests` 1개 / `scenarios`와 함께 | 검색 8·검증 2 / 검색 9·검증 1 / 분할 없이 전체 사용 + `Validation split disabled…` 출력 / 오류(R-05 ⑥) |
| T-15 | R-13, R-14, R-16 | 분할 사용. 기준선 (검색 4, 검증 2). 라운드 1 열: 현재 (4, 2), 후보 A (검색 5, 검증 1), 후보 B (검색 4, 검증 2) | 쌍 비교로 A는 검증이 낮아 탈락, B는 검증이 같고 검색 `≥`라 최선 쌍 = B. 그러나 채택은 `검증 2 > 2`가 아니고 `검색 4 > 4`도 아니라서 채택 없음 |
| T-16 | R-19, R-20 | 실행 전후 비교: 설정 파일·SKILL.md 수정 시각, `promptfoo list evals`, 출력 파일 | 모두 변화 없음(캐시 파일에는 제안 호출 항목이 생길 수 있음) |
| T-17 | R-22, R-23 | `prompts: [file://skills/x/SKILL.md]`(프런트매터 + `{{task}}` 참조 1곳 + 예시 코드의 `{{ }}` 1곳) | 제안 입력 `currentPrompt` = 프런트매터를 포함한 파일 전체(렌더 전). 후보는 문자열 그대로 새 raw가 되어 평가되며, 예시 코드의 정의되지 않은 `{{ }}`는 평가 때 사라짐. 로그의 `Best prompt` 아래에 최선 raw가 출력되고 파일은 불변 |
| T-18 | R-24 | 같은 SKILL.md를 `skill.txt`로 두고 `prompts: file://skill.txt`, 파일에 `---` 프런트매터 구분선 2줄 | 구분선에서 3청크(앞 빈 청크는 버림)로 쪼개져 프롬프트 2개(`name:` 줄들, 본문)가 되고 `--prompt-index 0`은 프런트매터 청크만 최적화함 |
| T-19 | R-25 | `T`=5(테스트 5개, 변수 조합 1, `repeat` 1), 3라운드 모두 유효 후보 3개 / 모든 라운드 후보 2개 / 라운드 1만 하고 라운드 2에서 후보 생성 실패(후보 3개) | 대상 호출 65(=13×5) / 50(=5×(1+3×3)) / 25(=5×(1+4)) |
| T-20 | R-25, R-26 | 위 첫 경우에 `--validation-split 0.2`(`S=4, V=1`), 모델 채점 어서션 테스트당 2개 | 대상 호출 합은 여전히 65(평가 호출은 8회), grader 호출 130, 제안 호출 3 |
| T-21 | R-17, R-18 | `ANTHROPIC_API_KEY`만 설정, 설정에 `defaultTest.options.provider: openai:…` 있음 | 제안 모델은 Anthropic 계열(default-providers R-02, T-17), grader는 설정대로 OpenAI, 대상은 설정의 `providers[j]` |
| T-22 | R-27 | `eval --suggest-prompts 3` / `optimize` | 앞: 제안 호출 3회, 평문 변형 3개를 y/n으로 고르고 고른 것만 열에 더해 일반 평가 / 뒤: 제안 호출 라운드당 1회, 점수로 자동 선택 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]

| R-ID / T-ID | 근거 (repo@dfe2d45 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01; `src/main.ts:110`; `src/mainUtils.ts:162-209` `addCommonOptionsRecursively`; 라이브러리 export: `src/index.ts`에 `optimiz` 없음(`grep`) | 코드 읽기. 사용자 문서 표(`command-line.md:187-195`)는 `--env-file`을 적지 않았다(2.1 아래 차이 ①) |
| R-02 | `src/commands/optimize.ts:21-60`; `src/util/config/load.ts:928-976, 1292-1301` `resolveConfigs`, `defaultTest.options` 구성; `src/main.ts:62-70` 기본 설정 로드 | 코드 읽기 |
| R-03 | C-01 `optimize.ts:109-133`, C-06 `promptOptimizer.ts:409-431`; 원본 테스트 사례명 `parses valid CLI optimizer selections and validation split`(`test/commands/optimize.test.ts:206`) | 코드 읽기, 테스트 사례명 열람 |
| R-04 | C-07 `promptOptimizer.ts:437-485`; eval-run R-17, config-loading R-15·R-21·R-23·R-26; 사례명 `defaults to the first prompt and provider`(`:283`), `rejects provider indices outside the resolved provider list`(`:387`), `keeps exact-label provider prompt routing intact after adopting a candidate`(`:724`) | 코드 읽기, 테스트 사례명 열람 |
| R-05 | C-09 `:700-731`, C-10 `:756-769`, C-06 `:369-375`; 사례명 `rejects prompt optimization when no tests or scenarios are configured`(`:911`), `still rejects … defaultTest is empty`(`:922`), `rejects a defaultTest-only config when an empty scenarios array is present`(`:934`), `accepts a defaultTest-only config with assertions and a scoring function`(`:951`), `rejects function-backed prompts …`(`:1090`), `rejects validation splits for scenario-based …`(`:832`); 프롬프트 `function` 설정 지점 `src/prompts/processors/python.ts:85-107`, `javascript.ts:40`, `executable.ts:138` | 코드 읽기. 함수 프롬프트 3종은 `function:` 대입 위치로 확인 |
| R-06 | C-09 `:631-688, 733-741`, C-10 `:774-781`; 사례명 `clones mutable test suites before each evaluate call so default assertions do not stack`(`:853`), `preserves config evaluation runtime options for internal optimizer evals`(`:426`) | 코드 읽기. 복제 이유는 사례명과 eval-run R-15(제자리 병합)에서의 추론 |
| R-07 | C-02, C-10 `:830-928`; 사례명 `keeps the baseline when a search candidate only ties its score`(`:338-386`: `evaluate` 모의 호출 4번 = 기준선 1 + 라운드 3 확인) | 코드 읽기, 해당 테스트 본문 열람 |
| R-08 | C-10 `:776-825`, C-09 `:743-749`; 사례명 `throws a clear error when prompt/provider filters scope every test away …`(`:1024-1056`, 본문 열람: 기준선 1회만 평가), `errors when the validation split produces no runnable tests`(`:1057`) | 코드 읽기, 테스트 본문(`:1024-1056`) 열람 |
| R-09 | C-03 `:82-171`, C-10 `:802-820, 906-918`; 사례명 `sanitizes and bounds optimizer evidence before sending it to the suggestions provider`(`:69`); eval-run R-27, `src/evaluator.ts:735, 1915` | 코드 읽기. `vars`에 파일 내용이 들어간다는 결론은 eval-run R-27과 `omitEvalRuntimeVars(state.vars)`의 결합(추론에 가까운 정적 추적) |
| R-10 | C-11 | 코드 읽기. 메시지 본문은 구조·규칙으로 요약 |
| R-11 | C-04, C-12; 사례명 `normalizes provider candidates and drops duplicates or unchanged prompts`(`:34`), `keeps an earlier-round improvement when a later round fails to generate candidates`(`:205`), `surfaces a first-round candidate generation failure …`(`:255`) | 코드 읽기, 테스트 사례명 열람. `extractJsonObjects` 중간부(`:373-417`)까지 읽었으나 YAML 파서 동작 세부는 라이브러리 |
| R-12 | C-08 `:487-629`; 사례명 `extends prompt filters for explicit, default, and scenario tests when candidates are added`(`:773`); `src/models/prompt.ts:24-32` `generateIdFromPrompt`(sha256(label)) | 코드 읽기 |
| R-13 | C-05, C-16; 사례 `keeps the baseline when a search candidate only ties its score`(`:338`), `keeps the baseline when validation and search scores both tie`(`:1164`), `uses validation score to reject search-only overfitting when split is enabled`(`:1104`) 이름만; eval-records R-16 | 코드 읽기. 비교 어서션 부분은 assertion-family R-49~R-51의 규칙과 "기준선 열 1개"를 결합한 추론 |
| R-14 | C-10 `:874-928` | 코드 읽기. "재측정 잡음으로 채택된다"는 시나리오는 코드의 논리(현재 열을 다시 평가하고 `>`로 비교)에서 도출했고 실행으로 보이지 않음 |
| R-15 | C-10 `:930-962`, `optimize.ts:62-92`, `promptOptimizer.ts:278-306` `logOptimizationOutcome`; 사례명 `logs validation scores and a non-improving result`(`test/commands/optimize.test.ts:172`) | 코드 읽기 |
| R-16 | C-06 `:360-407`, C-05 `:319-351`, C-10 `:860-890`; `site/docs/usage/prompt-optimization.md`("held-out"), `command-line.md:187-195` | 코드 읽기. 문서와 일치(차이 ② 참고) |
| R-17 | `promptOptimizer.ts:206-223`; [default-providers](./default-providers.md) R-18, `src/providers/defaults.ts`; `suggestions.ts:59-64`(비교: 레지스트리 경유) | 선행 스펙 링크 + 호출부 읽기 |
| R-18 | `src/commands/optimize.ts:33-38`(`resolveConfigs`에 `grader` 없음), `src/util/config/load.ts:1292-1301`; default-providers R-12~R-17, model-graded-matchers R-09 | 코드 읽기, 선행 스펙 |
| R-19 | `optimize.ts:1-12`(import 목록), `promptOptimizer.ts:1-20`(import 목록)에 파일 쓰기 모듈 없음; 사례명 `strips outputPath from internal optimizer evals so they do not pollute the user output file`(`:491`) | 코드 읽기(import 확인 + `grep`) |
| R-20 | C-09 `:733-741`, C-10 `:774-781`; `src/models/eval.ts:636-661, 770-791` `addResult`; `src/models/evalResult.ts:993-1062`; `src/evaluator.ts:6294-6296` `withCacheEnabled`; `src/cache.ts:286-296, 1209`; response-cache R-06; `src/main.ts:64` 마이그레이션 | 코드 읽기. 제안 호출이 캐시를 쓰는지는 `anthropic/messages.ts:1124`·`openai/chat.ts:913` 호출 지점으로 보았고 그 밖 provider 계열은 미확인 |
| R-21 | C-09 `:733-741`; `src/types/index.ts:277-325` `EvaluateOptionsSchema`; `src/types/internal.ts:11-22`; `src/util/config/load.ts:1096`; `src/evaluator.ts:5794, 5657`; eval-run R-12, R-41 | 코드 읽기 |
| R-22 | `src/evaluator.ts:2516-2545, 3140-3141`; config-loading R-47·R-48; eval-run R-34 | 코드 읽기, 선행 스펙 |
| R-23 | C-14, config-loading R-20·R-45; C-10 `:797-820`; `site/docs/usage/prompt-optimization.md` | 코드 읽기 |
| R-24 | config-loading R-21·R-22·R-25·R-47; C-09 | 코드 읽기 |
| R-25 | eval-run R-50, C-16, C-10 `:830-928`; 사례명 `…ties its score`(`:338`, 평가 모의 4회) | 식은 코드의 열 구성에서 도출 |
| R-26 | eval-run R-51, model-graded-matchers R-12, `promptOptimizer.ts:206-223`(1회 호출) | 코드 읽기 |
| R-27 | C-15, `src/node/doEval.ts:227-259`, `src/commands/eval.ts:170-172`, eval-run R-12 | 코드 읽기 |
| T-01~T-22 | 해당 R-ID의 근거 | 구현에서 도출. `T-11`~`T-13`, `T-15`, `T-19`는 점수·호출 수를 가정해 식을 적용한 예시 계산 |

문서와 구현·선행 스펙의 차이

- ① `command-line.md`의 `optimize` 옵션 표는 `-c`, `--prompt-index`, `--provider-index`, `--validation-split` 4개만 적는다. 구현은 `--env-file, --env-path <path>`(`optimize.ts:156`)를 더 등록한다. 구현을 사실로 썼다.
- ② `prompt-optimization.md`는 "Validation splitting requires explicit `tests`"라고 쓰지만 구현은 `tests` 길이가 2 미만이면 오류 없이 분할을 건너뛴다(R-16). 구현을 사실로 썼다.
- ③ 제안 시스템 메시지는 "search history with scores"를 쓰라고 하지만 구현의 이력에는 채택된 현재 프롬프트의 점수만 쌓이고 기각된 후보는 들어가지 않는다(R-14). 구현을 사실로 썼다.
- ④ 이전 보고(overview 2절 Q3)의 "검증 분할을 쓰면 검증용 평가가 더 붙으며"는 평가 호출 횟수에는 맞지만 대상 호출 수는 늘지 않는다(검증 집합은 `tests`를 나눈 것, R-25). 같은 문장의 "prompt 열 기준 최대 13회분 × 테스트 수"는 코드로 확인했다(R-25).
- ⑤ 선행 스펙 [eval-run](./eval-run.md) R-51의 "`--suggest-prompts`는 평가 전 제안 모델 1회"는 구현과 다르다. `generatePrompts`는 변형 개수 `n`만큼 호출한다(`suggestions.ts:67-93`, R-27). 이 스펙은 eval-run을 고치지 않고 차이만 남긴다.

### 2.2 코드 읽는 순서 [선택]

1. `src/commands/optimize.ts` `optimizeCommand`(옵션·파서) → `doOptimize`(설정 로드·출력).
2. `src/optimizer/promptOptimizer.ts` `optimizePromptTestSuite`(`:751`)가 전체 흐름이다. 먼저 `createSelectedOptimizationTestSuite` → 기준선 → 라운드 루프 순으로 읽고, 후보 생성은 `generateOptimizedPromptCandidates`, 후보 평가는 `createCandidateTestSuite`와 `selectBestPrompt(Pair)`, 채택은 `:874-912`.
3. 의존: 시스템 메시지 `src/prompts/grading.ts:133`, 평가 `src/evaluator.ts` `evaluate`(eval-run), 제안 모델 `src/providers/defaults.ts`(default-providers).
4. 구현 전략: 평가기를 **블랙박스로 여러 번 재사용**한다. 프롬프트 열만 늘리는 것으로 후보를 같은 테스트에 걸고(`prompts` 배열 교체 + 허용 목록 확장), 결과는 열 `metrics.score` 하나로 읽는다. 평가기의 캐시·저장·출력은 옵션 한 번(`cache:false`, `persisted:false`, `outputPath` 제거)으로 끈다.

### 2.3 비교·재사용 출처 [선택]

같은 폴더의 다른 레포 스펙: [prompt-optimizer의 프롬프트 최적화](../../prompt-optimizer/capabilities/prompt-optimize.md), [반복 개선·평가 기반 재작성](../../prompt-optimizer/capabilities/iterate-rewrite.md). 정책 차이는 아래 한 줄씩이고 자세한 비교는 적용 메모에 있다.

- 점수 기반 자동 루프: promptfoo는 있음(R-07, R-13, R-14). prompt-optimizer는 코어가 반복 횟수·종료 조건을 갖지 않고(iterate-rewrite R-10) "평가 → 재작성"이 사용자 클릭 2번이며 자동 라운드는 구현에 없다(iterate-rewrite R-30).
- 개선의 근거: promptfoo는 테스트·어서션이 만든 점수와 실패 사례(R-09), prompt-optimizer는 LLM 평가 응답을 압축한 재작성 입력문과 메타 프롬프트(iterate-rewrite R-12~R-22, prompt-optimize 1.1).
- 선택: promptfoo는 점수 합의 엄격 비교로 자동 채택(R-14), prompt-optimizer는 사람이 버전 체인에서 고른다.

## 적용 메모 [선택]

목적: 내 스킬(SKILL.md)을 여러 모델로 평가하고 개선해 모델 적합도를 기록하는 환경에서 promptfoo `optimize`와 prompt-optimizer의 개선 기능 중 무엇을 가져올지 정하는 것.

**비교(짧게).** 두 기능은 "개선 신호"가 다르다. promptfoo `optimize`는 **평가 지표(어서션 점수 합)가 개선을 이끄는 닫힌 루프**다. 제안 입력이 점수·실패 사례·이력이고 채택이 점수의 엄격한 증가라서 사람 없이 3라운드가 돈다. 대신 대상이 "프롬프트 raw 문자열 1개 × provider 1개"로 좁고(R-04), 제안 모델을 못 고르고(R-17), 파일을 쓰지 않으며(R-19), 점수 잡음·과적합 방어가 약하다(R-14, R-16). prompt-optimizer는 **재작성 템플릿이 중심이고 평가→재작성이 사람의 수동 연결**이라 지표 기반 채택·자동 반복이 없지만, 템플릿·이력·UI가 사람이 개선본을 고르는 흐름을 지원한다. 평가 지표로 개선한다는 요구에는 promptfoo 쪽의 구조(평가 증거를 제안 입력으로 넣고 점수로 채택하는 루프)가 맞고, prompt-optimizer는 재작성 문구·템플릿 자산으로 보완하는 후보다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-23, R-24 | SKILL.md를 에이전트 입력 파일로 쓰는 구성에서도 파일 자체를 개선 대상으로 삼는다 | 원본은 `prompts[].raw`만 고쳐서 에이전트 provider의 `working_dir`·`skills`·`file://` 변수로 들어가는 SKILL.md는 대상이 아니다(R-24 ⑤) | 최적화 대상을 "텍스트 슬롯"(프롬프트 raw, 변수 값, 작업 폴더 안 파일)으로 일반화하고 후보 평가 때 해당 슬롯에 후보를 주입하는 단계 추가. 새 사례: 에이전트 provider + `skill-used` 어서션으로 후보 SKILL.md 평가 |
| R-19 | 최선 프롬프트·라운드별 점수·후보·`hypothesis`를 파일(또는 기록 저장소)에 남긴다 | 원본은 로그 한 번뿐이라 모델 적합도를 기록하려면 로그를 파싱해야 한다 | 출력 단계에 기록 저장 추가, 후보·점수·모델 이름을 같은 레코드로 묶음 |
| R-17 | 제안 모델을 명시 선택한다 | 원본에는 지정 수단이 없고 키 유무로 정해진다(default-providers 적용 메모와 같음) | `suggestions` 역할에 provider 입력 추가 |
| R-04, R-07 | 여러 provider를 한 번에 돌려 모델별 최선 프롬프트·점수를 기록하고, 라운드 수·후보 수·종료 조건을 옵션으로 둔다 | 원본은 provider 1개와 상수 3·3이라 "여러 모델에서의 적합도"를 얻으려면 명령을 provider 인덱스마다 따로 돌려야 한다 | provider 목록을 입력으로, 라운드·후보 수를 매개변수로. 바뀌는 불변식: 호출 수 최대 `13T`는 `(1+R×(1+C))T × provider 수`로 일반화 |
| R-14, R-16 | 채택 전에 재측정(`repeat`)하거나 통과율·임계 조건을 함께 보고, 홀드아웃을 채택 판단과 분리한다 | 원본은 합 점수만 비교하고(R-13), 현재 프롬프트 재측정 잡음이 "채택"으로 셀 수 있으며(R-14, T-13), 검증 집합도 선택에 섞인다(R-16) | 채택 식을 `기준 이상 + 최소 개선폭`처럼 바꿈. 새 사례: 같은 프롬프트 재측정이 개선으로 세지지 않음 |
| R-22 | 후보가 `{{변수}}`·프런트매터를 보존했는지 검사한다 | 원본은 검사가 없어 변수가 빠진 후보가 점수로만 걸러진다 | 후보 정규화(R-11)에 보존 검사 단계 추가, 위반 후보는 평가 전에 버림 |
