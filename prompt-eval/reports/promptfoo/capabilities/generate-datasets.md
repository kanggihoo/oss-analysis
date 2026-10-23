---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/commands/generate/dataset.ts
  - src/commands/generate/assertions.ts
  - src/testCase/synthesis.ts
  - src/assertions/synthesis.ts
  - src/util/generation.ts
  - src/util/templates.ts
  - src/util/json.ts
  - src/csv.ts
  - src/util/config/load.ts
  - src/util/testCaseReader.ts
  - src/prompts/index.ts
  - src/prompts/processors/text.ts
  - src/prompts/processors/javascript.ts
  - src/prompts/processors/python.ts
  - src/main.ts
  - src/cache.ts
  - src/assertions/python.ts
  - src/assertions/scriptBody.ts
  - src/assertions/pi.ts
  - src/remoteScoring.ts
  - src/providers/openai/defaults.ts
  - src/providers/openai/chat.ts
  - site/docs/configuration/datasets.md
  - package.json
depends:
  - ./provider-contract.md
  - ./default-providers.md
  - ./config-loading.md
status: ready
reimplementation: 미실행
---

# 테스트·어서션 합성 (`promptfoo generate dataset` / `generate assertions`)

> 설정 파일의 프롬프트(와 기존 테스트)를 읽어, LLM 호출로 합성 테스트 케이스(`vars` 조합)와 추가 어서션(`type`·`metric`·`value`)을 만들고, YAML(데이터셋은 CSV도)로 출력하거나 설정 파일 뒤에 덧붙여 쓰는 기능.

<!--
이 스펙 안의 용어
- 합성 provider: 케이스·질문을 만들어 주는 LLM. 평가 대상(target) provider와 별개다. 선택 규칙은 default-providers 스펙.
- 총 케이스 수(total): `numPersonas × numTestCasesPerPersona`.
- 질문(question): 어서션 합성 1단계가 만드는 평가 질문. 2단계에서 `python` 어서션 또는 모델 채점 어서션(`pi`/`g-eval`/`llm-rubric`)이 된다.
- 경로 표기: 이 문서의 파일 경로는 모두 `repos/promptfoo/` 기준.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

**`generate dataset`**

1. 설정 파일(`--config` 또는 현재 폴더의 기본 설정)을 평가와 같은 로더로 읽는다. 프롬프트가 1개 이상 있어야 하고 provider는 없어도 된다. 합성에 쓰는 입력은 프롬프트 원문 목록(`prompt.raw`)과 기존 `tests`뿐이다. (R-02, R-10)
2. 합성 provider를 정한다: `--provider`가 있으면 그것, 없으면 기본 묶음의 `synthesizeProvider`. (R-07)
3. **호출 1: 페르소나.** 모든 프롬프트를 넣고 "이 프롬프트를 보낼 사용자 페르소나를 최대 N명" 요청 → JSON에서 페르소나 문자열 목록 추출. 0명이면 오류. (R-11)
4. **변수 추출(LLM 아님).** 프롬프트 원문에서 정규식으로 `{{변수}}` 이름 목록을 뽑는다. (R-12)
5. **호출 2…: 케이스.** 최대 20개씩 배치로, 페르소나 하나를 골라 "이 페르소나로서 각 변수의 값을 정하라, 흥미롭거나 특이한 값 K세트"를 요청 → 응답의 `vars` 배열을 모은다. 정확히 같은 케이스는 버리고 목표(total)에 모자라면 더 부르며, 3번 연속 새 케이스가 없으면 멈춘다. (R-13~R-16)
6. 총수를 넘으면 무작위로 total개만 남긴다. `{tests: [{vars: …}, …]}` YAML을 터미널에 찍거나 `--output`(.yaml/.csv) 파일로 쓰고, `--write`면 설정 파일의 `tests` 뒤에 덧붙여 설정 전체를 다시 쓴다. (R-18, R-19)

**`generate assertions`**

1. 1~2단계는 같다. 입력은 프롬프트 원문 목록과 기존 `tests[].assert` 전부. (R-21)
2. **호출 1: 질문.** 프롬프트와 기존 어서션을 넣고 "객관적·원자적 평가 질문(각각 `label`+`question`)"을 요청 → `{questions: […]}` 추출 → 무작위로 `numAssertions`개만 남긴다. (R-22, R-23)
3. **호출 2…N+1: 변환(병렬).** 질문마다 "결정적인 파이썬 함수 본문으로 바꿀 수 있으면 본문, 아니면 `None`"을 요청한다. `None`이면 `{type: <--type>, metric: label, value: question}`, 아니면 `{type: python, metric: label, value: 응답 원문}`. (R-24)
4. `{assert: […]}` YAML을 찍거나 `--output`(.yaml)로 쓰고, `--write`면 설정의 `defaultTest.assert` 뒤에 덧붙여 설정 전체를 다시 쓴다. (R-27, R-28)

### 1.2 범위·통합 지점 [필수]

- 제공: 위 두 명령. 둘 다 `generate` 명령 그룹 아래 등록된다(R-01).
- 제외: `redteam generate`(같은 `generate` 그룹에 등록되지만 별도 파이프라인), 외부 데이터셋 가져오기(`import`), 설정 로더 내부(`config`·테스트 로딩 스펙 몫이며 여기서는 "평가와 같은 경로로 읽는다"까지만).
- 외부 의존·선행 계약:
  - 합성 provider 선택: [default-providers.md](./default-providers.md) R-19(`--provider` 우선, 없으면 `synthesizeProvider`)와 거기 정의된 환경변수 사다리. 여기서는 "합성 provider는 `callApi(문자열)`를 지원하는 `ApiProvider`"로만 쓴다.
  - provider 호출 계약: [provider-contract.md](./provider-contract.md)의 `ApiProvider.callApi`·`ProviderResponse`. 이 기능은 응답의 `output`만 읽고 `error`·`tokenUsage`·`cost`는 쓰지 않는다(R-07, R-17).
  - 설정 로딩: `resolveConfigs`(프롬프트·테스트를 읽는 평가와 같은 로더).
- 소유 상태·부작용: 영속 상태 없음. 부작용은 ① 합성 provider 호출(비용·네트워크), ② `--output` 파일 쓰기, ③ `--write`일 때 설정 파일 덮어쓰기, ④ telemetry 기록(`command_used`). 캐시는 R-06.

### 1.3 인터페이스와 데이터 의미 [필수]

**CLI 옵션** (원문 이름 그대로)

| 명령 | 옵션 | 의미·기본값 |
|---|---|---|
| 공통 | `-c, --config [path]` | 설정 파일. 생략하면 `main`이 찾은 기본 설정 경로. 둘 다 없으면 오류 |
| 공통 | `-i, --instructions [instructions]` | 추가 지시문 문자열. 놓이는 위치가 명령마다 다르다(R-14, R-22) |
| 공통 | `-o, --output [path]` | 결과를 파일로. 생략하면 터미널 출력 |
| 공통 | `-w, --write` | 설정 파일에 병합해 다시 쓴다 |
| 공통 | `--provider <provider>` | 합성 provider 문자열(`openai:chat:…`, `file://…` 등 `loadApiProvider` 입력). 생략 시 `synthesizeProvider` |
| 공통 | `--no-cache` | 정의에 기본값 `false`가 붙어 있다(R-06) |
| dataset | `--numPersonas <number>` | 기본 `'5'` |
| dataset | `--numTestCasesPerPersona <number>` | 기본 `'3'` |
| dataset | `--env-file, --env-path <path>` | `.env` 파일(assertions에는 없음) |
| assertions | `-t, --type [type]` | `pi` \| `g-eval` \| `llm-rubric`. 기본 `pi`. 다른 값은 `InvalidArgumentError` |
| assertions | `--numAssertions <amount>` | 기본 없음 → 코드에서 5 |

**데이터**

| 데이터 | 형태 | 의미·제약 |
|---|---|---|
| 합성 입력 | `prompts: string[]`, `tests: TestCase[]` | `testSuite.prompts[].raw`와 `testSuite.tests`. 라벨·prompt `config`·`defaultTest`·`scenarios`는 쓰지 않는다 |
| 데이터셋 결과 | `VarMapping[]` | 키=변수 이름, 값=모델이 낸 값. 키·값 검증 없음(R-15) |
| 데이터셋 YAML | `{tests: [{vars: VarMapping}, …]}` | `js-yaml` `dump` 기본 옵션 |
| 데이터셋 CSV | 첫 줄=첫 행의 키, 이후 줄=행마다 모든 값을 `"`로 감싼 CSV | C-13. `.csv`는 dataset만 |
| 어서션 결과 | `Assertion[]` = `{type, metric, value}` | `type`은 `python` 또는 `--type` 값. `value`는 질문 문장 또는 파이썬 함수 본문 |
| 어서션 YAML | `{assert: [{type, metric, value}, …]}` | |

**비용에 영향을 주는 인자** (이 기능은 토큰·비용을 집계하거나 출력하지 않는다. 상한 옵션도 없다: 코드 확인)

| 인자 | 영향 |
|---|---|
| `--numPersonas`×`--numTestCasesPerPersona` | 총 케이스 수 → 케이스 호출 횟수(≥ ⌈total/20⌉)와 출력 토큰 |
| 프롬프트 길이·개수 | 모든 호출에 전문이 들어간다(R-10, R-33) |
| 기존 `tests` 수 | 케이스 호출마다 무작위 최대 100개의 `vars`가 JSON으로 들어간다(R-14) |
| `--numAssertions` | 변환 호출 N회(병렬). 질문 호출은 1회 고정(R-26) |
| `--provider` | 합성 모델 선택 → 단가 |
| `--type pi` | 생성 비용은 같지만, 만들어진 어서션이 평가 때 외부 서비스(WITHPI)를 부른다(R-25) |

### 1.4 행동 규칙과 남은 질문 [필수]

**등록·입력·옵션**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | CLI 시작 | `generate` 그룹(설명 "Generate synthetic data") 아래 `dataset`, `assertions`, `redteam`이 등록된다. 앞 둘의 action은 `{...opts, defaultConfig, defaultConfigPath}`로 `doGenerateDataset`/`doGenerateAssertions`를 부른다 | 코드 확인 |
| R-02 | 설정 읽기 | `configPath = --config \|\| 기본 설정 경로`. 없으면 "Could not find a config file…" 오류(합성 전). 있으면 `resolveConfigs({config:[configPath]}, defaultConfig, 'DatasetGeneration'\|'AssertionGeneration')`로 평가와 같은 로더를 쓴다. 이 두 type에서는 **provider가 없어도 오류가 아니고**(`!hasPrompts`일 때만 "You must provide at least 1 prompt"), 설정의 provider는 그래도 인스턴스화된다. `tests`는 평가와 같은 경로로 읽힌다(파일·생성기 확장 포함, 세부는 로딩 스펙 몫). `defaultTest`·`scenarios[].tests`는 합성 입력에 들어가지 않는다 | 코드 확인 |
| R-03 | dataset 옵션 파싱 | `numPersonas`·`numTestCasesPerPersona`를 `Number.parseInt(…, 10)`로 바꿔 넘긴다. `synthesize`는 `numPersonas \|\| 5`, `numTestCasesPerPersona \|\| 3`을 쓰므로 0·NaN은 기본값 5·3이 되고, 음수는 그대로 남아 total이 0 이하가 된다(케이스 호출 0회, 빈 결과). 프롬프트가 0개면 `Dataset synthesis requires at least one prompt.` | 코드 확인 |
| R-04 | assertions 옵션 파싱 | `numQuestions = parseInt(numAssertions \|\| '5')`. 옵션이 없으면 5. `0`은 0으로 남고(기본값 대체 없음) NaN도 그대로 간다(R-23). `--type`은 `pi`/`g-eval`/`llm-rubric`만 허용 | 코드 확인 |
| R-05 | `--instructions` | 빈 문자열이 아니면 쓰인다. 위치는 dataset은 케이스 프롬프트의 "흥미롭거나 특이한…" 문장 뒤(R-14), assertions는 질문 프롬프트 맨 끝(R-22). 페르소나 호출·변환 호출에는 들어가지 않는다 | 코드 확인 |
| R-06 | 캐시 | 옵션 정의가 `.option('--no-cache', desc, false)`다. Commander는 `--no-x` 옵션에 기본값이 주어지면 `cache`의 기본을 그 값(`false`)으로 둔다고 알려져 있어, 플래그 없이도 `!options.cache`가 참이 되어 "Cache is disabled."를 찍고 `disableCache()`를 부른다(응답 디스크 캐시 미사용). 이 옵션을 끄는 방법은 없다. 같은 패턴이 `redteam generate`/`run`에도 있고 `eval`은 기본값 인자가 없다 | 추론 (Commander 소스는 이 환경에 없어 읽지 못했고 실행도 하지 않음) |
| R-07 | 합성 provider 호출 | `provider`가 undefined면 `getDefaultProviders().synthesizeProvider`, 아니면 `loadApiProvider(provider, {basePath: cliState.basePath})`(default-providers R-19). 호출은 항상 `callApi(프롬프트 문자열)` 한 인자(context·options 없음). 응답은 `resp.output`만 읽는다: `undefined`면 invariant 오류, 문자열이 아니면 `JSON.stringify`한다(케이스 호출은 `undefined`/`null`이면 오류). `resp.error`는 읽지 않아 provider 오류의 원문은 오류 메시지에 나오지 않는다 | 코드 확인 |

**dataset 합성**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-10 | 프롬프트 입력 | `testSuite.prompts.map(p => p.raw)`를 그대로 쓴다. 자르기·요약·길이 검사·중복 제거가 없다. 프롬프트가 여럿이면 한 요청 안에서 `<Prompts>` 아래 `<Prompt>…</Prompt>`로 모두 나열한다(변수는 합집합) | 코드 확인 |
| R-11 | 호출 1(페르소나) | 프롬프트 1회 호출. 구조: 프롬프트 나열 + "최대 N명의 페르소나, 응답은 `{personas: string[]}` JSON". 파싱(`extractPersonas`): 코드펜스 제거 후 ① 전체 JSON 파싱(배열이면 요소, 객체면 `personas`·`user_personas`·`persona_list`·`personas_list`·`results` 중 첫 비어 있지 않은 배열) → ② 텍스트에서 JSON 객체를 찾아 같은 키 검사 → ③ 찾은 객체 목록 자체를 요소로 본다. 요소는 문자열이거나 `persona`/`name`/`description` 문자열 필드를 가진 객체, 공백 제거 후 비어 있지 않아야 한다. 0명이면 invariant 오류로 종료. 반환 인원이 N보다 많아도 자르지 않는다 | 코드 확인 (C-03, C-04) |
| R-12 | 변수 추출 | **LLM 호출이 아니라 정규식**(`extractVariablesFromTemplates`). `{# … #}` 주석을 지운 뒤 `{{ 이름 [| 필터…] }}`의 이름(공백·`{}`·`\|`을 뺀 연속 문자열, 점 경로는 통째로)과 `{% if|for 이름 … %}`의 이름을 모으고, `{% for x in xs %}`는 `x`를 빼고 `xs`를 넣는다. 결과는 중복 없는 목록(프롬프트가 여럿이면 합집합). 표현식·리터럴(`{{ 'a' }}`, `{{ f(x) }}`)도 그 문자열이 이름이 된다. 점 경로(`a.b`)는 루트 변수로 줄이지 않는다 | 코드 확인 (C-01) |
| R-13 | 케이스 생성 루프 | total = `numPersonas × numTestCasesPerPersona`. `retryWithDeduplication(op, total)`로 돈다: 목표에 못 미치고 연속 무진전 횟수 ≤ 2인 동안 `op(현재까지 모은 항목)`을 부른다. 매 호출의 요청 크기는 `min(total − 현재 수, 20)`이고 **페르소나는 `personas[현재 수 % 페르소나 수]`** 하나다. 새 항목 = `JSON.stringify` 기준 정확히 같은 것을 뺀 나머지(키 순서가 다르면 다른 항목). 새 항목이 0이거나 `op`가 배열이 아닌 값을 주면 무진전 +1, 새 항목이 있으면 0으로 초기화. 따라서 **연속 3번 무진전이면 목표 미달인 채로 정상 종료**한다 | 코드 확인 (C-02, C-05) |
| R-14 | 케이스 호출 프롬프트 구조 | ① 프롬프트 나열("`{{variables}}`를 가진 프롬프트") ② `<Persona>` ③ "Here are some existing tests:" 아래 기존 테스트의 `vars`를 `JSON.stringify(vars, null, 2)`로 `<Test>`에 담은 목록(호출마다 `tests`에서 무작위 최대 100개, `vars`가 없는 테스트는 제외, 문자열 정렬) ④ "페르소나가 되어 각 변수 값을 정하라… 흥미롭거나 특이한 값 K세트를 생각하라" + `instructions`가 있으면 공백 하나 뒤에 이어 붙임 ⑤ 응답 형식 `{vars: {<변수>: string, …}[]}`(변수 목록을 R-12 결과로 만든다). 이전 배치에서 만든 케이스는 다음 호출의 "existing tests"에 **들어가지 않는다**(원래 `tests`만) | 코드 확인 (C-03) |
| R-15 | 케이스 응답 파싱 | `extractJsonObjects(output)` 결과 중 **`vars`가 배열이고 모든 요소가 배열 아닌 비null 객체**인 첫 객체의 `vars`를 쓴다(빈 배열도 통과). 키 이름이 R-12 변수와 맞는지, 값이 문자열인지, 요청한 개수인지는 검사하지 않는다. 그런 객체가 없으면 invariant 오류 | 코드 확인 (C-05, C-12) |
| R-16 | 호출 횟수 | 합성 provider 호출 = 페르소나 1 + 케이스 호출 K. 모델이 요청한 만큼 새 케이스를 주면 K = ⌈total/20⌉(기본 total=15 → 1회, 총 2회). 적게 주거나 중복이면 늘어나고, 이론상 상한은 호출마다 새 항목 ≥1이 들어올 때 약 3×total+3(루프 조건에서 도출한 값) | 코드 확인 (K 하한·루프), 상한은 추론 |
| R-17 | 오류·부분 실패 | 어떤 호출에서든 invariant 위반·provider 예외·파싱 실패가 나면 **재시도 없이 예외가 올라가** 명령은 종료 코드 1로 끝난다(`main`이 `process.exitCode = 1`). 이미 받은 배치·페르소나는 버려지고 파일도 쓰지 않는다. `retryWithDeduplication`의 재시도는 "새 항목 없음"에만 적용되고 예외는 잡지 않는다. 무진전 종료(R-13)와 `vars: []` 응답은 오류가 아니다 | 코드 확인 |
| R-18 | dataset 출력 | `results`가 total을 넘으면 `sampleArray`(Fisher-Yates)로 total개만 무작위로 남긴다. `configAddition = {tests: results.map(v => ({vars: v}))}`. `--output`이 없으면 구분선과 "New test Cases" 아래 YAML을 로그로 찍는다. `--output`이 있으면 확장자가 `.csv`(C-13)면 CSV, `.yaml`이면 YAML을 쓰고 "Wrote N new test cases to …"를 찍으며 YAML은 찍지 않는다. **다른 확장자(`.yml` 포함)는 합성이 끝난 뒤에** `Unsupported output file type`으로 던지므로 비용은 나가고 결과는 사라진다. CSV는 결과가 0건이면 `No variables to serialize` 오류 | 코드 확인 |
| R-19 | dataset `--write` | 출력 처리 뒤, `--write`면 설정 파일을 **원문 그대로**(`file://`·템플릿 미해석) 읽어 `loadYaml`로 파싱하고 `tests`를 `[...기존, ...새 항목]`으로 바꾼 객체를 `yaml.dump`로 **파일 전체에 다시 쓴다**. 기존 `tests`가 배열이면 그대로, 배열이 아닌 값(예: `file://tests.csv` 문자열, 생성기 객체)이면 1요소 배열로 감싸고, 없으면 빈 배열. `--output`과 함께 쓰면 둘 다 실행된다. 새 케이스는 기존 테스트와 중복 검사하지 않는다(중복 제거는 이번 실행 내부뿐이라 문서의 "unique"는 이 범위) | 코드 확인 |

**assertions 합성**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-21 | 입력 | `prompts`(R-10과 같은 방식) + `tests.flatMap(t => t.assert ?? [])`를 `JSON.stringify(…, null, 2)`로 한 덩어리 `<existing_assertions>`에 넣는다(중복 제거·표본 추출 없음). `defaultTest.assert`와 `scenarios[].tests[].assert`는 포함되지 않는다 | 코드 확인 (C-08) |
| R-22 | 호출 1(질문) | 프롬프트 구조: ① 역할(확률적 AI 시스템의 지표 설계 시니어 데이터 과학자)과 과제("응답 하나를 평가하는 객관적 평가 질문") ② 핵심 요건 7개(이진/5점 리커트/0–1 척도, 응답 속성 중심, 객관성·수치 기준, 원자성, 독립성, 외부 지식 금지, 창작·목록 특수 처리) ③ 질문마다 3단어 이내 Title Case `label`, "Yes가 항상 좋은 응답", `question_source`·`question_type` 값 ④ 안티패턴 3개 ⑤ 절차(앱 분류 → 프롬프트에 **암시된 요구 먼저 소진** → 새 질문) ⑥ 개수 문구: `numQuestions > 0`이면 "Create total N questions … 암시된 질문만으로 N이 차면 새 질문을 만들지 마라", 아니면 "comprehensive set" ⑦ "JSON만 응답" 형식과 레시피 예시 1개 ⑧ 프롬프트 나열과 `<existing_assertions>`. `instructions`는 이 전체 뒤에 줄바꿈 하나 붙여 덧붙인다. 파싱: `extractJsonObjects`로 JSON 객체를 모아 하나도 없으면 오류, **`questions`가 배열이고 모든 요소가 문자열 `label`·`question`을 가진** 첫 객체를 쓴다(없으면 "different shape" 오류). `question_source`·`question_type`·`is_lower_score_desirable`은 읽지 않고 버린다 | 코드 확인 (C-06, C-12) |
| R-23 | 질문 선택 | `sampleArray(questions, numQuestions)`: 개수가 넘치면 **무작위**로 남기고(암시된 질문 우선 같은 정렬 없음), 모자라면 전부. `numQuestions`가 0이거나 NaN이면 `slice(0, 0)`/`slice(0, NaN)`이라 **질문 0개 → 어서션 0개**다(프롬프트의 "comprehensive" 분기는 CLI 경로에서 사실상 쓰이지 않고 호출 비용은 이미 나간다) | 코드 확인 (C-02, C-08) |
| R-24 | 호출 2…(변환) | 호출 직전 `providerModel.config = {maxTokens: 3000}`으로 provider의 `config` 객체를 **통째로 교체**한다(원래 config 키가 사라지고, `maxTokens`를 쓰는 provider에서만 의미가 있다). 질문마다 병렬(`Promise.all`, 동시성 제한 없음)로 변환 프롬프트를 보낸다. 프롬프트: 이 질문을 응답 문자열 `output`만으로 판정하는 파이썬 함수 본문으로 바꿀 수 있는지 판단, 가능하면 `{'pass': bool, 'score': 1.0\|0.0}`를 반환하는 본문만, 불가능(의미 이해·주관·외부 지식·원 입력과 비교 등)하면 문자열 `None`, 애매하면 `None`, 예시 5개 + `<application_description>`(프롬프트 나열) + `<question>`. 응답 `output`을 `toLowerCase().trim() == 'none'`으로 비교해 같으면 `{type: --type 값, metric: label, value: question}`, 아니면 `{type: 'python', metric: label, value: 응답 원문}`. **응답은 가공하지 않는다**(마크다운 펜스·설명문을 지우지 않음) | 코드 확인 (C-07, C-08) |
| R-25 | 어서션 `type` 의미 | `--type`은 파이썬으로 못 바꾼 질문의 `type`만 정한다. 기본 `pi`의 평가 때 핸들러는 `WITHPI_API_KEY`가 없으면 오류를 던지고, 있으면 외부 서비스에 POST한다. `g-eval`·`llm-rubric`은 grader provider를 쓴다(채점 쪽 스펙 몫). `python` 값은 평가 때 본문 줄들을 `def main(output, context):` 아래에 들여써 넣고 `return`이 없는 한 줄 값이면 `return <값>`으로 감싼다(`buildScriptBody`) | 코드 확인 (`pi` 외부 서비스는 코드가 가정한 사실이며 실제 서비스 보장은 미확인) |
| R-26 | 호출 횟수·실패 | 합성 provider 호출 = 질문 1 + 변환 N(N = 선택된 질문 수, 기본 최대 5). 어느 호출이든 예외·불량 응답이면 명령이 실패하고 어서션은 하나도 출력되지 않는다. 변환 호출의 `output`이 문자열이 아니면(`toLowerCase` 호출 실패) 전체가 실패한다. 이미 보낸 병렬 호출의 비용은 나간다 | 코드 확인 |
| R-27 | assertions 출력 | `{assert: results}` YAML. `--output`은 `.yaml`만 허용(`.yml`·그 외는 합성 뒤 오류). `--output`이 없으면 "New test Cases"(문구 그대로, 오타 아님) 아래 YAML을 찍는다 | 코드 확인 |
| R-28 | assertions `--write` | 설정 원문을 읽어 `defaultTest`가 **객체(null 포함)면** 그 값을 펼쳐 `defaultTest = {…기존, assert: […기존 assert, …새 어서션]}`, 객체가 아니면(문자열 `file://…`, undefined) `{}` 기준으로 **교체**한다. 즉 `defaultTest`가 파일 참조 문자열이면 그 참조가 사라진다. 새 어서션은 `tests[]`가 아니라 모든 테스트에 공통인 `defaultTest.assert`에 붙는다. 결과는 R-19와 같이 `yaml.dump`로 파일 전체를 다시 쓴다. R-21에 따라 이후 재실행에서도 이 `defaultTest.assert`는 "기존 어서션"으로 보이지 않아 중복 질문이 나올 수 있다 | 코드 확인 |
| R-29 | `--write` 공통 한계 | 설정 파일을 `readFile`+`loadYaml`로 읽고 `yaml.dump`로 다시 쓰므로 YAML 주석·서식·키 순서·앵커가 보존되지 않는다. JS/TS 설정이면 YAML 파싱 단계에서 실패할 것이고, JSON 설정은 파싱된 뒤 같은 경로에 YAML 텍스트로 다시 쓰인다 | 코드 확인(읽고 쓰는 호출), 파일 형식별 결과는 추론 |

**긴 텍스트 프롬프트(`file://SKILL.md`)일 때**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-30 | `prompts: file://SKILL.md`(`.md`/`.j2`) | 파일 전체가 프롬프트 1개의 `raw`가 된다(`processTemplateFile`: `readFileSync` 전체, frontmatter 제거·분할·잘라내기 없음). 합성은 이 문자열을 그대로 쓴다. 참고: `.txt`는 줄이 `---`뿐인 곳에서 여러 프롬프트로 쪼개지고(`PROMPTFOO_PROMPT_SEPARATOR`로 변경 가능), `.js`는 함수 소스 문자열, `.py`는 파일 전문이 `raw`다 | 코드 확인 (C-14, C-15) |
| R-31 | 변수 추출 결과 | SKILL.md가 보통 문서이면 `{{ }}`·`{% if|for %}`가 없어 **변수 목록이 빈 배열**이다. 이때 케이스 프롬프트의 응답 형식은 `{vars: {}[]}`가 된다. 코드는 변수가 비어 있어도 멈추지 않고, 모델이 준 `vars` 객체를 키 검증 없이 받는다. 결과는 모델에 달렸다: 모델이 임의 키(예: `query`)로 채우면 그대로 `tests`가 되고, `{}`만 내면 `JSON.stringify` 중복 제거로 1건으로 줄고 3번 연속 무진전으로 끝나 `tests: [{vars: {}}]` 같은 결과가 나올 수 있다(오류 없음) | 코드 확인(경로), 모델 응답별 결과는 추론 |
| R-32 | `{{ }}`가 들어 있는 긴 텍스트 | 코드 예시·템플릿 조각에 쓰인 `{{ x }}`(예: `${{ secrets.TOKEN }}`는 `secrets.TOKEN`, `{{ f(x) }}`는 `f(x)`)가 그대로 "변수"가 되어 모델에게 값을 정하라고 요청된다. 파일을 따옴표·코드펜스 안에 있다고 구분하지 않는다. chat JSON 프롬프트의 `{{skill}}`처럼 `vars: {skill: file://SKILL.md}`로 채우는 설계에서는 `skill`이 변수가 되어 모델이 "SKILL.md 내용"을 지어내려 하고, 기존 테스트의 `file://SKILL.md` 값은 파일 내용이 아니라 문자열 그대로 예시 목록에 들어간다 | 코드 확인(추출·예시 포함 경로), 이후 모델 행동은 추론 |
| R-33 | 크기와 비용 | R-10에 따라 전문이 **모든 호출**에 들어간다: dataset은 페르소나 1 + 케이스 K회, assertions는 질문 1 + 변환 N회(변환 프롬프트에도 전문이 다시 들어감). 길이 사전 검사가 없어 컨텍스트를 넘으면 provider 오류로 이어지고 그 오류 원문은 R-07 때문에 숨는다. 프롬프트가 "사용자가 보내는 요청 문장"이 아니어도 페르소나 호출은 "이 프롬프트를 보낼 사용자"를 요청한다(문서형 프롬프트 처리 코드 없음) | 코드 확인 |
| R-34 | 생성물의 종류 | 생성되는 것은 `vars` 세트뿐이고 기대값·케이스별 어서션은 만들지 않는다. 어서션은 `python`과 `--type` 3종뿐이며 `skill-used`·파일 산출 같은 에이전트 특화 어서션을 만드는 코드는 없다(`src/assertions/synthesis.ts` 전체를 읽음) | 코드 확인 |

- 불변식: 합성 provider 호출 횟수는 입력(프롬프트 수·길이)과 무관하고 옵션(total, N)과 모델 응답에만 달려 있다. 어떤 호출 실패도 부분 결과를 남기지 않는다(파일은 합성 성공 뒤에만 쓰인다).
- 미결정: 없음
- 확인 한계: 설치·빌드·실행을 하지 않았다. ① R-06은 Commander 라이브러리 소스를 읽지 못한 추론이다(`^15.0.0`, `package.json:314`; 의미가 달라졌는지는 미확인). ② 합성 응답이 실제로 어떤 모양으로 오는지(예: 기본 OpenAI `synthesizeProvider`가 JSON 모드이고 R-24의 `config` 교체가 이를 지우는 효과 등)는 provider 구현과 모델에 달려 있어 실행 없이 확정하지 못했다. ③ `pi`의 외부 서비스 동작은 코드가 가정한 사실만 확인했다. ④ 원본 테스트(`test/commands/generate/*.test.ts`, `test/testCase/synthesis.test.ts`, `test/assertions/synthesis.test.ts`)는 사례명만 훑었고 열지 않았다.

### 1.5 필수 코드 참조 [필수]

MIT 라이선스(overview 1절)라 인용·복제에 제한이 없다. 아래는 글보다 코드가 짧고 정확한 규칙이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/util/templates.ts:522-562` `extractVariablesFromTemplate(s)` | 변수 추출 정규식 3개(`{{ }}`·`{% if/for %}`·for-in)와 주석 제거, 합집합 | R-12, R-31, R-32 |
| C-02 | `src/util/generation.ts:16-49, 59-68` `retryWithDeduplication`, `sampleArray` | 중복 제거(JSON 문자열 기준)·연속 무진전 ≤2 허용 루프, Fisher-Yates 샘플링과 `min(n, len)` 의미 | R-13, R-18, R-23 |
| C-03 | `src/testCase/synthesis.ts:23-92` `generatePersonasPrompt`, `testCasesPrompt` | 두 프롬프트의 구조(R-11, R-14가 글로 푼 순서와 문구 위치) | R-11, R-14 |
| C-04 | `src/testCase/synthesis.ts:94-168` `extractPersonas` 외 | 페르소나 응답 파싱 순서와 허용 키 | R-11 |
| C-05 | `src/testCase/synthesis.ts:170-309` `synthesize` | 기본값 처리, provider 선택, 호출 순서, 배치 20·페르소나 회전, `vars` 응답 선택 조건, 샘플다운 | R-03, R-07, R-13, R-15 |
| C-06 | `src/assertions/synthesis.ts:22-223` `generateNewQuestionsPrompt` | 질문 생성 프롬프트(R-22 구조의 원문) | R-22 |
| C-07 | `src/assertions/synthesis.ts:225-420` `convertQuestionToPythonPrompt` | 변환 프롬프트(R-24 구조의 원문) | R-24 |
| C-08 | `src/assertions/synthesis.ts:427-543` `synthesize`, `synthesizeFromTestSuite` | 기본값(5·`pi`), 질문 응답 필터, 샘플링, `config` 교체, 병렬 변환, 결과 객체 분기 | R-04, R-21~R-26 |
| C-09 | `src/commands/generate/dataset.ts:31-125` `doGenerateDataset` | 설정 읽기→합성→출력 확장자 분기→`--write` 병합 순서와 `tests` 감싸기 | R-02, R-18, R-19 |
| C-10 | `src/commands/generate/assertions.ts:31-123` `doGenerateAssertions` | 같은 흐름 + `defaultTest.assert` 병합 | R-27, R-28 |
| C-11 | `src/commands/generate/dataset.ts:127-151`, `assertions.ts:125-164` | 옵션 정의·기본값·`--type` 검증 | R-01, R-03~R-06 |
| C-12 | `src/util/json.ts:334-419` `extractJsonObjects` | 응답에서 JSON 객체를 뽑는 관대한 규칙(전체가 객체면 그것 하나, 아니면 `{`마다 균형 잡힌 객체를 JSON→실패 시 YAML/주석 관대 파싱, 미완이면 닫는 괄호 보충, 후보 크기 100,000자 상한) | R-11, R-15, R-22 |
| C-13 | `src/csv.ts:340-355` `serializeObjectArrayAsCSV` | CSV 직렬화(첫 행 키로 헤더, 값은 `toString()` 후 `"`→`""`, 수식 이스케이프 없음, 0건이면 오류) | R-18 |
| C-14 | `src/util/config/load.ts:1128-1139` | 프롬프트 ≥1 필수, `DatasetGeneration`/`AssertionGeneration`이면 provider 불필요 | R-02 |
| C-15 | `src/prompts/processors/text.ts:58-75` `processTemplateFile` | `.md`/`.j2` 파일 전체를 `raw` 하나로 | R-30 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출(원본 테스트·실행 사용 안 함). 합성 provider는 대체물(고정 응답)로 가정하며, 이 사례들은 모델이 실제로 내놓는 품질은 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-11~R-16 | 프롬프트 `"Guide for {{location}}"`, 기존 테스트 없음, 기본 옵션. 대체 provider는 페르소나 5명, 이어서 `vars` 15개를 모두 다르게 준다 | provider 호출 2회, 변수 목록 `[location]`, 결과 15건, 출력 `tests: [{vars: {location: …}}, …]` |
| T-02 | R-13 | `numPersonas=5`, `numTestCasesPerPersona=9`(total 45), 모델이 요청한 만큼 모두 다른 케이스를 줌 | 케이스 호출 3회(요청 크기 20·20·5), 사용 페르소나 인덱스 `0, 20%5=0, 40%5=0`(5명 중 1명만 사용). 페르소나가 3명이면 `0, 2, 1` |
| T-03 | R-13, R-17 | 모델이 매번 같은 `vars` 5개만 반환 | 첫 케이스 호출 후 5건, 이후 연속 무진전 3회째에 종료(케이스 호출 4회, 페르소나 호출 포함 총 5회), 5건 출력, 종료 코드 0 |
| T-04 | R-11, R-17 | 페르소나 응답이 JSON이 아니거나 키가 없어 0명 | invariant 오류, 케이스 호출 없음, 출력·파일 없음, 종료 코드 1 |
| T-05 | R-18 | 정상 합성 후 `--output tests.yml` | 합성 호출은 모두 수행된 뒤 `Unsupported output file type: tests.yml` 오류, 파일 없음 |
| T-06 | R-19 | 설정에 `tests: file://tests.csv`, `--write` | 설정이 `tests: ["file://tests.csv", {vars: …}, …]`로 다시 쓰인다(전체가 YAML 덤프라 주석 소실) |
| T-07 | R-04, R-22~R-24 | `generate assertions`, 기본 옵션. 질문 응답이 7개, 변환 응답이 질문별로 `None`/함수 본문 혼합 | 질문 중 무작위 5개만 남고 변환 호출 5회(병렬). `None`→`{type: pi, metric, value}`, 함수 본문→`{type: python, metric, value: 본문 원문}`, 총 합성 호출 6회 |
| T-08 | R-23 | `--numAssertions 0` | 질문 호출 1회(프롬프트에는 "comprehensive") 후 어서션 0개, 변환 호출 없음, `assert: []` 출력 |
| T-09 | R-28 | 설정에 `defaultTest: file://default.yaml`, `generate assertions --write` | `defaultTest`가 `{assert: […새 어서션]}`로 교체되어 파일 참조가 사라진다 |
| T-10 | R-30, R-31 | `prompts: file://SKILL.md`(변수 표기 없음), 모델이 `{vars:[{query:"a"},{query:"b"}]}`를 줌 | 변수 목록 `[]`, 케이스 프롬프트 형식 문장이 `{vars: {}[]}`, 오류 없이 `tests: [{vars:{query:a}}, …]` 출력(키는 모델이 지어낸 것) |
| T-11 | R-32 | SKILL.md 본문에 ``${{ secrets.TOKEN }}`` 코드 예시 | 변수 목록에 `secrets.TOKEN`이 포함되어 모델에게 값 지정이 요청된다 |
| T-12 | R-18 | CSV 출력, 두 행이 `{a:'1',b:'2'}`, `{b:'3',a:'4'}` | 헤더 `a,b`, 둘째 행은 값 순서 그대로 `"3","4"`(헤더와 열이 어긋남) |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]

| R-ID / T-ID | 근거 (repo@dfe2d45 `파일:줄` `심볼`, 또는 C-ID) | 확인 방법·한계 |
|---|---|---|
| R-01 | `src/main.ts:104-117`, C-11 | 등록 코드 직접 읽음. `redteam`이 같은 `generateCommand`에 붙는 것도 확인 |
| R-02 | C-09 `:38-55`, C-14, `src/util/config/load.ts:1212-1226, 1303-1310`(`readTestSources`→`parsedTests`→`testSuite.tests`) | `defaultTest`·`scenarios`가 합성 입력이 아닌 것은 `synthesizeFromTestSuite`(`src/testCase/synthesis.ts:311-320`, `src/assertions/synthesis.ts:534-543`)가 `prompts.raw`와 `tests`만 넘기는 것에서 확인. 설정 provider 인스턴스화는 `load.ts`의 `loadApiProviders` 호출(1208행 부근) 확인, 생성자 실패 여부는 추론 |
| R-03 | C-05 `:182-183`, C-09 `:64-69`, `src/testCase/synthesis.ts:178-180` | |
| R-04 | C-10 `:64-69`, C-08 `:427-434`, C-11 `:125-131, 141-146` | |
| R-05 | C-03 `:85`, C-08 `:462-464`, 변환 호출 C-07 | `instructions`가 변환·페르소나 프롬프트 함수의 인자가 아님을 시그니처로 확인 |
| R-06 | C-11 `dataset.ts:148`, `assertions.ts:162`, `src/commands/eval.ts:94`, `src/redteam/commands/generate.ts:1123`, `src/cache.ts:55,1165-1167` | **추론**. Commander의 `--no-*` 기본값 규칙은 외부 지식이며 소스 미확인. 테스트(`test/commands/generate/dataset.test.ts`)는 `cache`를 직접 넘겨 이 기본값을 검증하지 않는다(파일명·사례명만 확인) |
| R-07 | C-05 `:204-216, 265-275`, C-08 `:455-469`, default-providers R-19 | |
| R-10, R-12, R-13 | C-05, C-01, C-02 | 코드 직접 읽음. 문서(`site/docs/configuration/datasets.md`)는 단계(페르소나·변수·호출 횟수)를 설명하지 않는다 |
| R-11, R-15 | C-04, C-05 `:211-224, 278-286`, C-12 | `extractJsonObjects` 세부(YAML 관대 파싱)는 `src/util/json.ts` 요약만 읽음 |
| R-14 | C-03 `:36-92` | |
| R-16 | C-05 `:239-294`, C-02 | 상한 3×total+3은 루프 조건(`allItems.length < target && retries <= 2`)에서 내가 유도 → 추론 |
| R-17 | C-02(예외 미처리), `src/main.ts:160-180` | 오류 → `process.exitCode = 1` 확인. 진행 막대(`cli-progress`)는 로그 레벨이 `debug`가 아닐 때만 쓰며 동작과 무관 |
| R-18 | C-09 `:70-89`, C-13, C-02 `:59-68` | |
| R-19 | C-09 `:91-115` | |
| R-21~R-24 | C-06, C-07, C-08 | 프롬프트 요건은 원문을 읽고 구조로 요약 |
| R-25 | `src/assertions/pi.ts:6-17`, `src/remoteScoring.ts:43-73`, `src/assertions/python.ts:18-26`, `src/assertions/scriptBody.ts` | 외부 서비스 호출은 코드가 가정한 동작 |
| R-26, R-27 | C-08 `:507-531`, C-10 `:70-89` | |
| R-28, R-29 | C-10 `:91-106` | 파일 형식별 동작은 `loadYaml` 구현을 읽지 않아 추론 |
| R-30 | C-15, `src/prompts/index.ts:37-52`(`.j2`/`.md` 분기), `src/prompts/processors/text.ts:18-55`(`.txt` 분할), `javascript.ts:25-35`, `python.ts:90-97` | |
| R-31, R-32 | C-01 | 정규식 결과는 손으로 대입. 실행 안 함 |
| R-33, R-34 | C-03, C-06, C-07, `src/commands/generate/*.ts`(비용 출력 없음) | `grep`으로 `tokenUsage`/`cost`가 합성 파일·명령 파일에 없음을 확인 |
| 문서와 구현 차이 | ① 옵션 도움말 `--provider`: dataset은 "adversarial tests"/"default grading provider"라 하나 구현은 `synthesizeProvider`(default-providers 2.1과 같음). ② `site/docs/configuration/datasets.md`는 "By default dataset generation uses OpenAI"라 하나 실제 기본값은 환경변수 사다리(default-providers). ③ 같은 문서는 `-o`가 "CSV and YAML"이라 하나 `.yml`은 거부(R-18). ④ `generate assertions`는 문서 사이트에 전용 가이드가 없다(`command-line.md`는 목록만). ⑤ 지도·요청문의 "변수 추출→다양화→케이스 생성"과 달리 **LLM 호출은 페르소나→케이스 두 종류**이고 변수 추출은 로컬 정규식이다 | 구현을 사실로 썼다 |
| T-01~T-12 | 모두 C-ID 조합에서 손으로 도출 | 실행 안 함 |

### 2.2 코드 읽는 순서 [선택]

1. `src/commands/generate/dataset.ts`(옵션·출력·병합) → `src/testCase/synthesis.ts:170-309`(호출 순서) → `src/util/generation.ts`(루프) → `src/util/templates.ts:522-562`(변수 정규식).
2. `src/commands/generate/assertions.ts` → `src/assertions/synthesis.ts:427-532`(프롬프트 본문 2개는 `:22-420`, 필요할 때만).
3. 선행: `default-providers.md` R-19, `provider-contract.md` R-01·R-03.

### 2.3 비교·재사용 출처 [선택]

- 다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드를 그대로 복사한 부분은 없다(MIT).

## 적용 메모 [선택]

목적: 내 SKILL.md를 여러 모델로 평가하는 환경의 케이스 만들기. 아래는 원본 동작(위 R-ID)이 시사하는 입력 방법이고, 원본과 다르게 할 점은 "바뀌는 것" 열에만 쓴다.

| 관련 R-ID | 원본과 다르게 할 점 / 입력 방법 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-30~R-32 | SKILL.md 전문을 `prompts`로 넣지 않는다. **합성 전용 입력**을 따로 만든다: 스킬이 해결하는 일과 사용자 요청 모양을 한두 문단으로 쓰고 `{{request}}` 같은 변수 자리를 둔 프롬프트를 합성에 쓴다 | 합성기는 프롬프트에서 도메인을 읽고 변수만 채운다. SKILL.md에는 변수가 없어 빈 스키마가 되고(R-31), 문서형 텍스트를 "사용자가 보내는 프롬프트"로 취급한다(R-33) | 원본에 없는 단계(합성용 입력 생성) 추가. 원본 호출 흐름은 바꾸지 않음 |
| R-14, R-05 | 기존 테스트 5~10개를 사람이 써서 시드로 둔다(호출마다 최대 100개가 예시로 들어감). 분포 지시(경계 사례, 스킬이 **발동하지 말아야** 하는 요청, 모호한 요청, 언어·길이 범위)는 `--instructions`로 준다 | 예시와 지시가 케이스 프롬프트에만 들어가는 유일한 조정 수단이다 | 변경 없음(입력 방법) |
| R-13 | 다양성은 페르소나 수가 아니라 별도 실행·지시로 만든다. total ≤ 20이면 페르소나는 사실상 1명만 쓰인다. 여러 페르소나를 쓰려면 total > 20이고 `페르소나 수`가 20을 나누지 않는 값이어야 한다 | `personas[len % P]`와 배치 20 때문(T-02) | 재구현 시 "페르소나 1명당 K개" 의미로 바꾸려면 R-13 변경이 되므로, 바꿀지는 별도 결정 |
| R-25, R-24, R-34 | 어서션은 `--type llm-rubric`으로 만든다(기본 `pi`는 외부 서비스 키 필요). 생성된 `python` 값은 코드 펜스가 섞이지 않았는지 사람이 확인한다. 스킬 호출(`skill-used`)·산출 파일 검사 같은 에이전트 특화 어서션은 직접 쓴다 | 합성은 "응답 품질 질문"만 만든다 | 변경 없음 |
| R-28, R-21 | `generate assertions`는 `--write` 대신 `--output`으로 받아 검토한 뒤 합친다. 결과는 케이스별이 아니라 전역(`defaultTest`)이다 | 파일 전체가 덤프로 다시 쓰이고(R-29) 재실행해도 이전 결과를 못 본다(R-28) | 케이스별 기대값·rubric 연결이 필요하면 원본 계약에 없는 확장이다 |
