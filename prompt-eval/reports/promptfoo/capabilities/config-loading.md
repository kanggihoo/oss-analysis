---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/util/config/load.ts
  - src/util/config/default.ts
  - src/util/config/extensions.ts
  - src/prompts/index.ts
  - src/prompts/utils.ts
  - src/prompts/constants.ts
  - src/prompts/processors/text.ts
  - src/prompts/processors/string.ts
  - src/prompts/processors/json.ts
  - src/prompts/processors/jsonl.ts
  - src/prompts/processors/yaml.ts
  - src/prompts/processors/csv.ts
  - src/prompts/processors/javascript.ts
  - src/prompts/processors/python.ts
  - src/prompts/processors/executable.ts
  - src/util/file.ts
  - src/util/pathUtils.ts
  - src/util/testCaseReader.ts
  - src/util/xlsx.ts
  - src/util/yamlLoad.ts
  - src/util/render.ts
  - src/util/templates.ts
  - src/util/providerRef.ts
  - src/util/promptMatching.ts
  - src/util/validateTestPromptReferences.ts
  - src/util/validateTestProviderReferences.ts
  - src/providers/index.ts
  - src/csv.ts
  - src/evaluatorHelpers.ts
  - src/evaluator.ts
  - src/types/index.ts
  - src/types/configAliases.ts
  - src/validators/providers.ts
  - src/contracts/prompts.ts
  - src/contracts/validators/prompts.ts
  - src/assertions/validateAssertions.ts
  - src/node/doEval.ts
  - src/commands/eval.ts
  - src/commands/validate.ts
  - src/main.ts
  - src/envars.ts
  - src/esm.ts
  - src/models/prompt.ts
  - site/docs/configuration/prompts.md
  - site/docs/configuration/test-cases.md
  - site/docs/configuration/modular-configs.md
  - test/prompts/index.test.ts
  - test/prompts/utils.test.ts
  - test/prompts/fileMetadata.test.ts
depends: []
status: ready
reimplementation: 미실행
---

# 설정·프롬프트·테스트 로딩 (+ 설정 스키마 계약)

> `promptfooconfig.*`(와 그 안의 `file://` 참조, CLI 인자)를 읽어 `providers`·`prompts`·`tests`·`defaultTest`·`scenarios` 등을 `TestSuite`(평가 실행기가 받는 입력)로 만들고, 그 입력이 따르는 설정 스키마(`TestSuiteConfig`/`UnifiedConfig`/`TestSuite`)를 정의한다. SKILL.md 같은 긴 텍스트 파일을 프롬프트나 변수로 넣는 `file://` 동작을 포함한다.

경로는 모두 `repos/promptfoo/` 기준이다. 이번 작성은 코드 읽기만 했고(설치·실행 없음) `실행 확인`은 없다. 이 스펙은 공유 계약 `config-schema`를 합친 것이라 별도 `config-schema.md`는 만들지 않는다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

`promptfoo eval -c promptfooconfig.yaml`(또는 `optimize`·`validate`·`generate`)이 `resolveConfigs`를 부를 때의 순서다. 같은 함수를 여러 명령이 쓴다(R-01~R-14).

1. **설정 파일 찾기.** `-c` 인자(경로·글롭, 여러 개 가능)를 펼친다. `-c`가 없으면 작업 디렉터리의 `promptfooconfig.{yaml,yml,json,cjs,cts,js,mjs,mts,ts}` 중 처음 있는 것을 기본 설정으로 쓴다(R-01, R-02).
2. **파일 하나 읽기.** YAML/JSON은 파싱 후 `$ref`를 풀고, JS/TS는 모듈로 가져온다. 그다음 문자열 속 `{{ env.X }}`만 렌더하고, 스키마를 검사하되 틀려도 경고만 하고, `targets`→`providers` 등 별칭을 바꾸고, `prompts`가 없으면 `['{{prompt}}']`를 넣는다(R-03~R-08).
3. **설정 합치기.** `-c`가 있으면(하나여도) `prepareCombinedConfig`가 설정들을 합치고, prompts·defaultTest·scenarios의 파일 참조를 그 설정 파일의 디렉터리 기준 절대 경로로 바꾸며, tests는 설정별 디렉터리와 함께 넘긴다(R-09, R-10). 기본 설정만 쓸 때는 이 단계를 거치지 않는다(R-14).
4. **CLI와 설정 병합 후 필수 항목 검사.** CLI 인자가 설정보다 우선하는 항목을 정하고, prompts·providers가 없으면 실패한다(R-11~R-13).
5. **구성 요소별 읽기.** `readPrompts`(프롬프트 파일 → `Prompt[]`), `resolveProviderConfigs` + `loadApiProviders`(provider 인스턴스), `readTestConfigs`/`readTest`(테스트 소스 → `TestCase[]`), `defaultTest`, `scenarios`(R-15~R-43).
6. **참조 검증.** 어서션 형태, 테스트가 가리킨 provider·prompt가 존재하는지 확인한다(R-44).
7. **결과 반환.** `{ testSuite, config, basePath, commandLineOptions, selectedProviderConfigs, testSources }`. 이후 평가 시점(경계, eval-run 소유)에 `renderPrompt`가 변수의 `file://`를 읽고 Nunjucks로 렌더한다(R-45~R-52).

### 1.2 범위·통합 지점

- 제공: 위 흐름 전체와 설정·프롬프트·테스트 스키마 정의(1.3). 입력 소스 목록(1.3의 "테스트 입력 소스"·"프롬프트 파일 형식"), 변수 `file://` 로딩 동작(R-45~R-52).
- 제외:
  - 평가 실행(렌더 후 provider 호출, 채점, 집계)은 `eval-run`이다. `renderPrompt`는 SKILL.md 동작을 정확히 쓰기 위해 R-45~R-52에서 입력·결과만 정의한다.
  - 데이터 소스별 로더 내부(Hugging Face `huggingface://datasets/…`, Google Sheets, SharePoint, Azure Blob `az://…`)는 "지원 목록과 경계"만 쓴다(R-35).
  - 레드팀 설정(`redteam`, `plugins`, `strategies`)은 모양만 통과시키고 해석하지 않는다.
  - 클라우드 설정 UUID(`-c <uuid>`), `resume`/`retry`의 저장된 설정 재생(`resolveReplayConfigs`), 웹 UI의 설정 편집(`configDraft`)은 다루지 않는다.
  - provider를 만드는 규칙(접두어 디스패치, 각 provider 설정)은 provider 계약 스펙의 몫이다. 여기서는 "설정 항목 → `loadApiProviders` 입력" 경계만 쓴다(R-15).
- 외부 의존·선행 계약(별도 스펙 없이 경계만 정의):
  - `importModule(path, functionName?)`(`src/esm.ts:232-262`): JS/TS 파일을 가져와 `module.default.default || module.default || module`을 돌려주고, `functionName`이 있으면 그 이름의 export를 돌려준다. 실패하면 던진다. JS/TS 설정 파일, 프롬프트 함수, 테스트 생성기, 변수 스크립트, nunjucks 필터가 쓴다.
  - `runPython(file, functionName, args)`: Python 함수를 호출해 JSON으로 변환 가능한 값을 돌려준다. `.py` 프롬프트 함수·테스트 생성기·변수 스크립트가 쓴다(스크립트 브리지 스펙의 몫).
  - `loadApiProviders(configs, {basePath, env})`: provider 설정 목록을 `ApiProvider[]`로 만든다(provider 계약).
  - 라이브러리: YAML(`js-yaml` v4 호환 스키마: 병합 키 `<<` 허용, 빈 문서는 `undefined`, 문서 2개 이상이면 오류, `src/util/yamlLoad.ts:26-45`), CSV(`csv-parse`), 글롭(`glob`), `$ref` 해석(`@apidevtools/json-schema-ref-parser`), Nunjucks, 선택 의존 `read-excel-file`(xlsx), `pdf-parse`(PDF).
- 소유 상태·부작용:
  - `cliState`(프로세스 전역): `resolveConfigs`가 끝날 때 `basePath`, `config`, `selectedProviderConfigs`를 덮어쓴다. 로딩 중에는 `withBasePath`/`withEnv`/`withConfig`로 비동기 범위에 한정해 설정한다.
  - 파일 읽기 외 쓰기는 없다. 단, JS/TS 설정·프롬프트·변수·생성기 파일과 `.py`·실행 파일 프롬프트는 사용자 코드를 실행한다(읽기만 하는 것이 아니다).
  - 네트워크: 원격 테스트 소스(R-35)와 클라우드 provider 참조 때만. 그 외 로컬 파일.
  - `telemetry.record('feature_used', …)`가 일부 경로(Sheets, xlsx 등)에서 호출된다(동작에 영향 없음).

### 1.3 인터페이스와 데이터 의미

**진입 함수**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `resolveConfigs(cmdObj, defaultConfig, type?)` (`load.ts:928`) | `Partial<CommandLineOptions>`, `Partial<UnifiedConfig>`, `type?: 'DatasetGeneration'\|'AssertionGeneration'` → `{testSuite, config, basePath, commandLineOptions?, selectedProviderConfigs?, testSources?}` | 핵심 진입점. `type`이 있으면 provider가 없어도 된다. 끝에서 `cliState.basePath/config/selectedProviderConfigs`를 덮어쓴다. `config`는 저장·재생용 선언형 사본(테스트의 provider 인스턴스는 `undefined`로 치환), `testSuite`는 인스턴스가 만들어진 실행용 |
| `loadDefaultConfig(dir=cwd, name='promptfooconfig')` | → `{defaultConfig, defaultConfigPath}` | 확장자 순서대로 첫 파일. 없으면 `{}`와 `undefined` |
| `readConfig(path)` / `maybeReadConfig(path)` | → `UnifiedConfig` / `UnifiedConfig \| undefined` | `maybe`는 파일이 없을 때(ENOENT)만 `undefined`. 그 외 오류는 던진다 |
| `readPrompts(input, basePath='', labelBasePath?, sourceBasePaths?)` | `string \| (string\|Partial<Prompt>)[] \| Record<string,string>` → `Prompt[]` | 입력 순서대로 이어 붙인다. 입력 하나가 0개를 내면 던진다 |
| `readTestConfigs(tests, basePath, env)` / `readTests(...)` / `readTest(test, basePath, isDefaultTest, env)` | `TestSuiteConfig['tests']` → `TestCase[]` | `readTestConfigs`는 provider를 만들지 않고 `file://` 변수를 절대 경로로 바꿔 저장 가능한 행을 낸다. `readTests`/`readTest`는 행의 `provider` 문자열·객체를 `ApiProvider`로 만든다 |
| `renderPrompt(prompt, vars, filters?, provider?, skipRenderVars?)` (`evaluatorHelpers.ts:242`) | → string | 경계. 평가 때 호출. 변수 `file://` 로딩과 템플릿 렌더(R-45~R-52) |

**설정 최상위 키** (`TestSuiteConfigSchema`, `types/index.ts:1312-1469`에 `UnifiedConfigSchema`가 `evaluateOptions`·`commandLineOptions`·`targets`를 더함)

| 키 | 타입 | 로드 시 의미 |
|---|---|---|
| `providers` | string \| 함수 \| 배열(string, 함수, `ProviderOptions{id,label,config,prompts,transform,delay,env,inputs}`, `{<id>: ProviderOptions}` 맵) | `targets`가 별칭. 둘 중 정확히 하나. `file://*.yaml\|yml\|json`은 그 파일의 항목(단일·배열)으로 펼침(R-15) |
| `targets` | `providers`와 같음 | 읽은 뒤 `providers`로 옮기고 지움(R-07) |
| `prompts` | string \| 배열(string, `{id, label?, raw?}`, `Prompt`) \| 맵 `{<raw>: <label>}`(레거시) | R-16~R-29. 선언형 파일에서는 없어도 스키마가 통과하고 기본값 `['{{prompt}}']`(R-08) |
| `tests` | string \| 배열(string, `TestCase`, `{path, config?}`) \| `{path, config?}` | R-30~R-40. 없으면 빈 목록 |
| `defaultTest` | `file://…` 문자열 \| `TestCase`에서 `description` 제외 | R-41 |
| `scenarios` | 배열(`file://…` 문자열 \| `{description?, config: Partial<TestCase>[], tests: TestCase[]}`) | R-42 |
| `env` | 키→문자열(숫자·불린은 문자열화) | 템플릿·provider·`PROMPTFOO_*` 스위치에 쓰는 환경 덮어쓰기 계층(R-05, R-53). 합칠 때 뒤가 이김 |
| `nunjucksFilters` | 이름 → 파일 경로(글롭 가능) | `basePath` 기준으로 `importModule`한 함수. 글롭이 여러 파일이면 마지막 것이 이김 |
| `extensions` | `file://경로.py\|.js…:함수` 문자열 배열(또는 null) | 형식 위반은 스키마 경고. 합칠 때 이어 붙이고, CLI `-x`가 앞에 붙음 |
| `derivedMetrics` | `[{name, value: 식 문자열 \| 함수}]` | 그대로 통과 |
| `description`, `tags`, `metadata` | string, `{string:string}`, `{string:any}` | 그대로. `metadata`는 `defaultTest.metadata`의 기본값이 됨(R-41) |
| `outputPath` | string \| string[] | 그대로(CLI `--output` 우선) |
| `sharing` | boolean \| `{apiBaseUrl?, appBaseUrl?}` | `PROMPTFOO_DISABLE_SHARING`이 참이면 `false` |
| `evaluateOptions` | `EvaluateOptionsSchema`(cache, delay, maxConcurrency, repeat, timeoutMs, maxEvalTimeMs, filterRange …) | 통과. 의미는 eval-run |
| `commandLineOptions` | `CommandLineOptionsSchema.partial()` | 검증 실패는 던짐(R-07). `envPath`는 설정 디렉터리 기준 절대화(R-13) |
| `tracing`, `redteam`, `writeLatestResults`, `basePath` | — | 통과. `basePath`는 설정 파일 디렉터리 기준 절대 경로로 바꿈(R-07) |

**`TestSuite`** (`resolveConfigs`가 만드는 값, `TestSuiteSchema` `types/index.ts:1181-1307`): `basePath`, `description`, `tags`, `prompts: Prompt[]`, `providers: ApiProvider[]`, `tests: TestCase[]`, `scenarios`, `defaultTest: TestCase`(항상 객체, R-41), `derivedMetrics`, `nunjucksFilters`(이름→함수), `redteam`, `extensions`, `tracing`, `env`(값은 모두 문자열). `outputPath`·`sharing`·`evaluateOptions`·`metadata`는 `testSuite`가 아니라 반환된 `config`에 남는다.

**`Prompt`** (`contracts/prompts.ts`): `{id?, raw: string, label: string, template?, display?(폐기), function?, config?}`. `config`는 provider 설정에 병합될 값이고 이 스펙은 전달만 한다. `function`은 프롬프트 함수(R-25).

**`TestCase`** (`types/index.ts:947-1018`): `description?`, `vars?: Record<string, string\|number\|boolean\|object\|array>`(null 불가), `provider?`(string \| ProviderOptions \| ApiProvider), `providers?: string[]`(실행할 provider 필터), `prompts?: string[]`(실행할 prompt 필터), `providerOutput?`, `assert?`, `assertScoringFunction?`(`file://….js\|py[:함수]` 또는 함수), `options?`(`prefix, suffix, postprocess(폐기), transform, transformVars, storeOutputAs, rubricPrompt, provider(채점 모델), factuality, disableVarExpansion, disableConversationVar, disableDefaultAsserts, runSerially, repeat` + 임의 키), `threshold?`, `metadata?`(임의 키). 테스트 파일의 `vars`는 `TestCaseWithVarsFile`로 문자열·문자열 배열(vars 파일 경로)도 허용한다.

**테스트 입력 소스** (`tests` 문자열·배열 항목·`{path}`가 가리킬 수 있는 것; 판정 순서는 R-30, 형식은 R-31~R-36)

| 소스 | 지정 | 결과 |
|---|---|---|
| CSV(로컬) | `*.csv` | 행 → `TestCase`(열 규칙 R-32) |
| xlsx/xls(로컬, 선택 의존) | `*.xlsx[#시트이름\|#1기반번호]` | 행 → CSV와 같은 규칙(R-33) |
| JSON·JSONL·YAML(로컬) | `*.json`, `*.jsonl`, `*.yaml`, `*.yml` | `TestCase` 배열(또는 단일). 안의 `file://`를 풂(R-34) |
| JS/TS 생성기 | `*.js\|ts\|mjs\|cjs\|mts\|cts[:함수]` | 모듈 export(함수면 `config`를 인자로 호출) → `TestCase[]` |
| Python 생성기 | `*.py[:함수]`(기본 함수명 `generate_tests`) | 목록을 반환해야 함 |
| 인라인 | `TestCase` 객체 | 그대로 |
| 원격(경계만) | `huggingface://datasets/…`, `https://docs.google.com/spreadsheets/…`, `https://….sharepoint.com/…`, `az://…`(csv/json/jsonl/yaml/yml) | 각 로더가 `TestCase[]`를 돌려주고 `metadata.__promptfoo.remote = true`를 붙인다(R-35) |
| 글롭 | 위 형식에 `*` 등 | 일치 파일마다 처리(R-37) |
| 그 밖 | 디렉터리, 지원하지 않는 확장자 | 경로에 따라 `[]` 또는 오류(R-37) |

**프롬프트 파일 형식** (`processPromptFile`, `prompts/index.ts:27-79`. 상세는 R-19~R-25)

| 지정 | 처리기 | 프롬프트 수 | `raw` |
|---|---|---|---|
| `.md`, `.j2` | 템플릿 파일 | 1 | 파일 UTF-8 전체(가공 없음) |
| `.txt` | 텍스트 | 구분자 줄로 나눈 청크 수 | 청크(앞뒤 공백 제거) |
| `.json` | JSON | 1 | 내용(`file://` 풀어 다시 직렬화) 또는 원문 |
| `.jsonl` | JSONL | 비어 있지 않은 줄 수 | 각 줄 |
| `.yaml`, `.yml` | YAML | 1 | 파싱 후 `file://` 풀어 `JSON.stringify`한 문자열 |
| `.csv` | CSV | 행 수 | `prompt` 열(없으면 한 줄=한 프롬프트) |
| `.js/.ts/.mjs/.cjs/.mts/.cts[:함수]` | JS 함수 | 1 | 함수의 소스 문자열. 실제 내용은 호출 때 |
| `.py[:함수]` | Python | 1 | 파일 내용. 실제 내용은 호출 때 |
| `exec:경로`, `.sh .bash .exe .bat .cmd .ps1 .rb .pl`, 확장자 모를 때 실행 권한이 있는 파일 | 실행 파일 | 1 | 100KB 미만 텍스트 파일이면 그 내용, 아니면 경로 문자열. 실제 내용은 호출 때 |
| 그 밖의 확장자 | 없음 | 0 | → 오류(R-26) |

**환경 스위치** (설정 `env` 블록 → env 파일 → `process.env` 순으로 읽음, `envars.ts:545-559`)

| 이름 | 기본값 | 효과 |
|---|---|---|
| `PROMPTFOO_STRICT_FILES` | 꺼짐 | 켜면 프롬프트 경로 `stat` 실패를 던짐(R-26) |
| `PROMPTFOO_PROMPT_SEPARATOR` | `---` | `.txt` 청크 구분 줄(R-21) |
| `PROMPTFOO_CSV_DELIMITER` / `PROMPTFOO_CSV_STRICT` | `,` / 꺼짐 | 프롬프트·테스트 CSV의 구분자 / 느슨한 따옴표 허용 끔(R-23, R-32) |
| `PROMPTFOO_DISABLE_TEMPLATING` | 꺼짐 | 켜면 env 템플릿 렌더·변수 렌더 모두 생략(R-05, R-47) |
| `PROMPTFOO_DISABLE_TEMPLATE_ENV_VARS` | 꺼짐(`PROMPTFOO_SELF_HOSTED`가 기본값) | 켜면 템플릿의 `env`에서 `process.env`를 뺌(R-05) |
| `PROMPTFOO_DISABLE_REF_PARSER` | 꺼짐 | `$ref` 역참조 생략(R-04) |
| `PROMPTFOO_DISABLE_JSON_AUTOESCAPE` | 꺼짐 | 켜면 JSON 프롬프트도 문자열 템플릿으로 렌더(R-47) |
| `PROMPTFOO_DISABLE_VAR_EXPANSION` | 꺼짐 | 변수 배열·글롭 확장 끔(R-46) |
| `PROMPTFOO_DISABLE_PDF_AS_TEXT` / `PROMPTFOO_DISABLE_MULTIMEDIA_AS_BASE64` | 꺼짐 | 변수 `file://`의 PDF·미디어 특수 처리를 끔(R-46) |
| `PROMPTFOO_DISABLE_SHARING` | 꺼짐 | `config.sharing = false` |
| `PROMPTFOO_NO_TESTCASE_ASSERT_WARNING` | 꺼짐 | `vars.assert` 경고 끔(R-43) |

**CLI 입력** (`commands/eval.ts:33-80`와 `CommandLineOptionsSchema` `types/index.ts:107-161` 중 로딩에 쓰는 것)

`-c/--config <경로…>`, `-p/--prompts <경로…>`(설정의 `prompts`를 대체), `-t/--tests <경로>`와 `-v/--vars <경로>`(설정의 `tests`를 대체), `-r/--providers <이름\|경로…>`(provider 선택), `--var key=value`(모든 테스트의 변수), `-x/--extension`, `--description`, `-o/--output`, `--prompt-prefix/--prompt-suffix`, `--grader`, `--filter-providers/--filter-targets`, `--filter-prompts`, `--filter-first-n/--filter-pattern/--filter-failing/--filter-sample/--filter-sample-seed`(시나리오 테스트에만 여기서 적용, 최상위 `tests` 필터는 `doEval`), `-a/--assertions`+`--model-outputs`(독립 어서션 모드, R-11).

### 1.4 행동 규칙과 남은 질문

규칙 묶음: 설정 파일(R-01~R-08), 여러 설정·CLI(R-09~R-14), providers(R-15), prompts(R-16~R-29), tests·defaultTest·scenarios(R-30~R-43), 검증(R-44), 변수 `file://`와 SKILL.md(R-45~R-52), 환경 계층(R-53).

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `-c` 없이 실행. 기본 설정 탐색(`main.ts:66-69`; 일부 명령은 건너뜀) | 작업 디렉터리에서 `promptfooconfig.<ext>`를 `yaml, yml, json, cjs, cts, js, mjs, mts, ts` 순으로 찾아 처음 있는 것을 쓴다(C-01). 없으면 `defaultConfig={}`, `defaultConfigPath=undefined`. 실행 때마다 `doEval`이 다시 읽는다(수정 반영) | 코드 확인 |
| R-02 | `-c`에 경로·글롭을 줌 | 각 항목을 작업 디렉터리 기준으로 글롭 확장한다. 한 항목이 0개로 풀리면 `No configuration file found at <항목>…` 오류. `eval` 명령(`doEval`)에서는 디렉터리 항목이 그 안의 기본 설정 파일로 같은 자리에서 바뀐다(없으면 경고하고 뺀다, 모두 없으면 실패). 다른 명령(`optimize`, `validate` 등)은 이 대체를 하지 않아 디렉터리를 주면 R-03의 형식 오류가 난다. 입력 순서가 합칠 때의 우선순위가 된다(뒤가 이김) | 코드 확인 |
| R-03 | 설정 파일 확장자 | `.json/.yaml/.yml`은 `loadYaml`(JSON도 YAML 파서로 읽음, 빈 파일은 `{}`)로 읽고 `$ref`를 푼다. JS/TS 확장자는 `importModule`로 가져온다. 그 외 확장자는 `Unsupported configuration file format: <ext>` | 코드 확인 |
| R-04 | 선언형(YAML/JSON) 설정 | `$RefParser.dereference`로 `$ref`를 푼다. 단 `providers[].config.functions[].parameters`와 `tools[].function.parameters`는 풀기 전에 떼어 두었다가 그대로 돌려놓는다(스키마 안의 `$ref`를 보존). `PROMPTFOO_DISABLE_REF_PARSER`면 통째로 생략. JS/TS 설정은 대상이 아니다 | 코드 확인(해석 범위는 확인 한계) |
| R-05 | 설정 객체의 모든 문자열 | `{{ env.NAME }}`(필터·`env['NAME']` 포함)만 로드 시 렌더한다. 먼저 `config.env` 값을 `process.env`/env 파일 기준으로 렌더하고(1패스), 그 결과를 덮어쓰기로 삼아 설정 전체를 렌더한다(2패스). 필터가 없는데 값이 정의되지 않은 `env.X`와 `env` 아닌 템플릿(`{{ vars.x }}`, `{{prompt}}`)은 그대로 둔다. `undefined`인 env 값은 버린다(빈 문자열은 유지). `PROMPTFOO_DISABLE_TEMPLATE_ENV_VARS`면 첫 패스에 `process.env`를 쓰지 않는다 | 코드 확인 |
| R-06 | 스키마 검사 | 선언형은 `TestSuiteConfigSchema`에 `prompts` 선택·`providers`/`targets` 선택(둘 중 정확히 하나)을 더한 스키마, JS/TS는 `UnifiedConfigSchema`로 검사한다. 위반하면 `Invalid configuration file <경로>:` 경고만 남기고 계속한다(결과 설정은 읽은 그대로). `doEval`의 `TestSuiteSchema` 검사도 경고뿐이다. `validate` 명령은 같은 검사를 오류+종료 코드 1로 다룬다 | 코드 확인 |
| R-07 | 읽은 설정의 정규화 | `commandLineOptions`는 `CommandLineOptionsSchema.partial()`로 검사해 위반 시 `ConfigResolutionError`를 던지고(경고 아님), 통과하면 작성된 키만 남긴다. `targets`가 있으면 `providers`로 옮기고 지운다(둘 다 있으면 `targets`가 이김). 최상위 `plugins`/`strategies`는 `redteam.plugins/strategies`로 옮긴다. `basePath`가 있으면 설정 파일 디렉터리 기준으로 절대화한다 | 코드 확인 |
| R-08 | 설정에 `prompts` 없음 | `['{{prompt}}']`를 넣는다. 경고(`Expected top-level "prompts" property…`)는 `tests`가 있고(문자열 아님) 어느 테스트의 `vars`에도 `prompt`가 없고 첫 provider에 `inputs`가 없을 때만 낸다 | 코드 확인 |
| R-09 | 설정 파일이 둘 이상(여러 `-c`, 글롭) | 합치기(`prepareCombinedConfig`, C-05): `providers`는 이어 붙이되 같은 문자열·같은 JSON 직렬화·같은 함수 참조는 한 번만. `prompts`는 이어 붙이고 같은 문자열은 한 번만(객체는 중복 제거 안 함). 배열형과 맵형 prompts를 섞으면 `Cannot mix …` 오류. `tests`는 설정별로 따로 읽어 이어 붙이고 각 설정의 디렉터리를 기준으로 쓴다. `scenarios`는 이어 붙인다. `defaultTest`: `file://` 문자열이 하나라도 있으면 마지막 문자열이 이기고 그 문자열 뒤에 오는 객체 `defaultTest`는 무시된다. 문자열이 없으면 객체끼리 `vars/options/metadata`는 얕게 병합하고 `assert`는 이어 붙인다. `tags`·`nunjucksFilters`·`env`·`evaluateOptions`·`commandLineOptions`·`metadata`는 뒤가 이기는 얕은 병합. `outputPath`는 이어 붙임, `extensions`는 이어 붙임(2개 이상이고 설정이 여럿이면 경고), `derivedMetrics`는 이어 붙임, `description`은 `', '`로 연결, `sharing`은 하나라도 `false`면 `false` 아니면 첫 객체, `tracing`은 첫 번째. `basePath`는 첫 설정의 디렉터리 | 코드 확인 |
| R-10 | 합칠 때 파일 참조 | `prompts`(문자열·`id`가 `file://`인 객체의 `raw`·맵 키), `defaultTest` 문자열, `scenarios`의 `file://` 항목과 시나리오의 `config`·`tests` 안 테스트(문자열, `{path, config}`, `vars` 문자열·배열·중첩 `file://`, `provider`의 `file://`)를 그 설정 파일 디렉터리(또는 설정의 `basePath`) 기준 절대 경로로 바꾼다. 최상위 `tests`는 바꾸지 않고 설정별 `basePath`와 함께 `testSources`로 넘겨 읽을 때 그 기준을 쓴다(R-39). `{{`가 남은 참조는 env 렌더 후에도 `{{`이면 그대로, 원격 참조(`://`이고 `file://` 아님)는 그대로. `providers`와 `nunjucksFilters`는 절대화하지 않고 최종 `basePath`(첫 설정)에서 해석한다 | 코드 확인 |
| R-11 | CLI가 설정과 겹침 | 설정 파일이 하나라도 있으면 기본 설정은 쓰지 않는다. `prompts`: `--prompts` > 설정 > 기본 설정 > `[]`. `tests`: `--tests`/`--vars` > 설정 > 기본 설정 > `[]`(CLI 값이면 설정의 `tests`는 읽지 않음). `description`: CLI > 설정. `outputPath`: `--output` > 설정. `extensions`: `-x` 값 뒤에 설정 값. `providers`: 설정(`--providers`는 R-15의 선택). `--assertions`+`--model-outputs`(독립 어서션 모드)이면 `prompts=['{{output}}']`, `providers=['echo']`, 각 출력이 `vars.output`인 테스트로 바꾼다(`--model-outputs` 없으면 오류). `--assertions` 값은 `readAssertions`가 읽는다 | 코드 확인 |
| R-12 | 필수 항목 | 설정 파일 없음 + prompts·providers 없음 + CI 아님: `No promptfooconfig found`(경고 수준, 사용법 안내). prompts 없음: `You must provide at least 1 prompt`. providers 없음(`type`이 Dataset/AssertionGeneration이면 면제): `You must specify at least 1 provider (for example, openai:gpt-4.1)`. 읽은 프롬프트가 0개: `No prompts found…`. 모두 `ConfigResolutionError` | 코드 확인 |
| R-13 | 기준 디렉터리 | `basePath = path.resolve(fileConfig.basePath ?? defaultConfig.basePath ?? dirname(config[0]) ?? '')`. 전역 `cliState.basePath`에도 넣는다. 상대 `commandLineOptions.envPath`는 `basePath` 기준으로 절대화한다. 설정 파일 안의 상대 경로는 설정 파일 디렉터리가 기준이고 작업 디렉터리가 아니다. `--tests` 경로는 작업 디렉터리 기준이다(`--vars`는 설정 `basePath` 기준, 2.1의 D-4) | 코드 확인 |
| R-14 | `-c` 없이 기본 설정만 사용 | 합치기·절대화 없이 `defaultConfig`를 그대로 쓴다. 상대 경로는 `basePath`(설정에 `basePath`가 없으면 작업 디렉터리)에서 읽는다. 다중 설정 규칙(R-09, R-10)은 적용되지 않는다 | 코드 확인 |
| R-15 | `providers` 해석(`load.ts:1160-1211`, `providers/index.ts:368-421`, `util/providerRef.ts`) | `file://*.yaml\|yml\|json` 항목은 파일을 읽어(`basePath` 기준, 중첩 `file://` 풀이 포함) 단일·배열 `ProviderOptions`로 펼친다. 객체는 `id`가 있으면 옵션 객체, 키 하나가 옵션 키가 아니면 `{<id>: 옵션}` 맵으로 본다. `--providers` 토큰은 설정 provider에 id 일치 > label 일치 > `id`가 `:토큰`으로 끝남 순으로 대응시키고, 없으면 새 provider 문자열로 쓴다. `--filter-providers/--filter-targets`로 인스턴스화 전에 거른다(0개면 경고). 이후 `loadApiProviders`가 `ApiProvider[]`를 만든다 | 코드 확인 |
| R-16 | `readPrompts` 입력 | 문자열 1개, 문자열·객체 배열(객체는 `raw ?? id`가 원문), 맵 `{raw: label}`(`raw`=키, `label`=값)을 `{raw, …}` 목록으로 정규화한다. `null`·빈 문자열·빈 배열·빈 객체·숫자·불린은 `Invalid input prompt: …` | 코드 확인 |
| R-17 | 프롬프트 문자열이 파일인가(`maybeFilePath`, C-08) | 아니다: `\n` 포함, 또는 `portkey://`·`langfuse://`·`helicone://` 포함. 맞다: `file://`로 시작, 또는 마지막/뒤에서 둘째 `:` 토큰이 알려진 확장자(`.cjs .cts .j2 .js .json .jsonl .md .mjs .mts .py .ts .txt .yml .yaml`)로 끝남, 또는 뒤에서 3·4번째 글자가 `.`, 또는 `*`·`/`·`\` 포함. 파일로 판정된 뒤 결과가 0개면 오류가 된다(R-26): 한 줄짜리 인라인 프롬프트에 `/`가 들어 있으면(예: `Run /commit`) 글롭 문자(`*`, `?` 등)가 없을 때 `There are no prompts in "…"`이다. 글롭 문자가 있으면 일치 0건이라 원문 문자열로 쓴다(R-26) | 코드 확인(정적 추적, 미실행) |
| R-18 | `prompt.function`이 있는 객체(Node API 입력) | 그대로 통과. `raw`가 `exec:`로 시작하면 이후를 경로로 보고 실행 파일 처리기로 보낸다(`:함수` 부분은 무시) | 코드 확인 |
| R-19 | 파일 경로의 확장자 분기(C-09) | 확장자는 `parsePathOrGlob`가 `file://`를 떼고 `basePath`로 절대화한 경로에서 뽑는다. `:함수` 접미는 `.js/.ts…/.py/.go/.rb` 경로일 때만 함수명이다(Windows 드라이브 콜론 보호 포함). 분기는 1.3의 "프롬프트 파일 형식" 표와 같다. 분기 순서는 `.csv, .j2, .json, .jsonl, JS 계열, .md, .py, .txt, .yml/.yaml, 실행 확장자` 다음 "경로가 실행 권한 있는 파일이면 실행 파일", 그 밖은 `[]`. `.go`는 확장자 분기가 없다(실행 권한이 있을 때만 실행 파일로) | 코드 확인 |
| R-20 | `.md`, `.j2` 파일 | 파일 전체 UTF-8 내용이 프롬프트 1개의 `raw`다. 분할·트림·프런트매터 제거 없음. `label = prompt.label \|\| "<라벨경로>: <내용 앞 50자>..."`, `config = prompt.config` | 코드 확인 |
| R-21 | `.txt` 파일 | 줄바꿈(`\r?\n`)으로 나눠 앞뒤 공백을 뺀 줄이 구분자(`PROMPTFOO_PROMPT_SEPARATOR`, 기본 `---`)와 같으면 청크를 끊는다. 각 청크는 `\n`으로 이어 붙인 뒤 `trim`하고, 빈 청크는 버린다. `label = "<label>: " + "<라벨경로>: <청크>"`(label 없으면 뒤쪽만). 구분자 줄이 없으면 프롬프트 1개 | 코드 확인 |
| R-22 | `.json`, `.yaml/.yml` 파일 | JSON: BOM을 떼고 파싱이 되면 안의 `file://` 문자열을 재귀로 읽어(`maybeLoadConfigFromExternalFile`) 다시 직렬화한 문자열이 `raw`, 파싱에 실패하면 원문 그대로 `raw`. YAML: 파싱 후 같은 방식으로 `file://`를 풀고 `JSON.stringify`한 문자열이 `raw`(YAML 파싱 실패 시 원문). 둘 다 프롬프트 1개, 최상위가 배열이어도 1개다(챗 메시지 배열로 쓰는 용도). `label = prompt.label \|\| "<라벨경로>: <raw 앞부분(JSON 전체, YAML은 80자)>"` | 코드 확인 |
| R-23 | `.csv` 프롬프트 파일 | 내용에 구분자(`PROMPTFOO_CSV_DELIMITER`)가 없으면 비어 있지 않은 줄마다 프롬프트(첫 줄이 `prompt`면 헤더로 건너뜀). 있으면 헤더 기준 파싱(`prompt` 열 필수 값, `label` 열 선택, 값이 비어 있는 행은 제외, 파싱 오류면 줄 단위로 대체). 라벨: 행의 `label` 열 > (`prompt.label`이 있고 행이 여럿이면 `<label>: <내용>`, 하나면 `<label>`) > `Prompt <n> - <내용>`이고, 겹치면 `(row n)`을 붙인다. 행이 여러 개이고 `prompt.id`가 있으면 `id:<n>` | 코드 확인 |
| R-24 | `.jsonl` 프롬프트 파일 | BOM을 떼고 비어 있지 않은 줄마다 프롬프트(원문 줄이 `raw`). 줄이 여럿이면 라벨 `<label>: <줄>` 또는 `<라벨경로>: <줄>`, 하나면 `label` 또는 라벨경로 | 코드 확인 |
| R-25 | JS·Python·실행 파일 프롬프트 | 읽는 시점에는 호출하지 않는다. JS는 `importModule(경로, 함수명)`으로 함수를 가져와 `function`에 래핑한다(`raw = String(함수)`, `label = label \|\| 경로[:함수]`). Python: `:함수`가 있으면 `runPython(경로, 함수, [ctx])`, 없으면 파일 전체를 `python`(`PROMPTFOO_PYTHON`)으로 실행해 stdout을 프롬프트로(레거시). 실행 파일: 경로(인자 포함 가능)를 `execFile`로 실행해 stdout을 프롬프트로 쓰고(타임아웃 기본 60초, 종료 코드 오류는 던짐, stderr만 있으면 오류, 파일 해시가 있고 캐시가 켜져 있으면 결과를 캐시). 호출 인자 `ctx = {vars, provider:{id,label}, config}`는 모두 같다(실행 파일은 argv로 JSON). 반환이 string이면 프롬프트, `{prompt, config?}`이면 `prompt`(문자열이 아니면 JSON 직렬화)와 `config` 병합, 그 밖의 객체·배열은 JSON 직렬화(R-47의 `renderPrompt` 앞단), 그 밖의 타입은 오류 | 코드 확인 |
| R-26 | 글롭·디렉터리·없는 파일(C-09, C-11) | 경로에 글롭 문자(`hasMagic`)가 있거나 경로가 디렉터리면 `globSync`로 풀어 파일마다 한 단계만 재귀 처리한다(깊이 1). 일치 파일이 0개면 원문 문자열 하나를 프롬프트로 쓴다(`file://…` 포함 그대로). 글롭이 아닌 경로: 파일이 없으면 확장자 분기의 `readFileSync`가 ENOENT를 던진다(`PROMPTFOO_STRICT_FILES`면 `stat` 단계에서 던짐). 확장자가 알려지지 않았거나 처리기가 0개를 내면 `readPrompts`가 `There are no prompts in "<입력>"`을 던진다. 디렉터리 경로를 글롭 문자 없이 주면, 글롭이 디렉터리 자신을 돌려주고 안쪽 재귀는 0개를 내므로 원문 문자열 프롬프트가 된다(정적 추적, 문서의 `prompts: file://prompts/`는 이렇게 동작하지 않음, D-2) | 코드 확인(정적 추적, 미실행) |
| R-27 | 라벨·ID | 프롬프트 식별은 `label`이다. 평가 기록의 prompt id는 `sha256(label)`(label이 없으면 `id`, 둘 다 없으면 `raw`)다(`models/prompt.ts:24-32`). 파일 프롬프트의 라벨 경로는 `readPrompts`의 `labelBasePath` 기준 상대 경로(설정 디렉터리의 작업 디렉터리 기준 상대 경로)라서 체크아웃 위치에 따라 변하지 않는다. 입력 `id`는 문자열·CSV 처리기와 글롭 확장(`<id>:<상대경로>[:<n>]`)에서만 결과에 남고, 단일 파일 `.md/.txt/.json/.yaml/.jsonl` 처리기는 `id`를 내보내지 않는다 | 코드 확인 |
| R-28 | 프롬프트 객체 `{id, label?, raw?, config?}` | 원문은 `raw ?? id`. `label`과 `config`는 그 파일에서 나온 모든 프롬프트에 전달된다(`.md/.txt/.json/.csv` 등 공통). `-c` 경로(설정 합치기)에서는 객체에 `raw` 또는 `label` 문자열이 있어야 하며 없으면(`id`만 있어도) `Invalid prompt: … 'raw' or 'label' string property` 오류다(스키마는 `{id}`만으로도 통과). `id`가 `file://`이면 `raw`를 절대 경로로 만든다. `id`·`raw`가 없는 객체는 `PromptSchema`(`raw`, `label` 필수)로 검사하고 실패하면 `Invalid prompt object` | 코드 확인 |
| R-29 | `--prompts` CLI | 설정의 `prompts`를 통째로 대체하고 `basePath`/라벨 기준 없이(작업 디렉터리) 읽는다 | 코드 확인 |
| R-30 | `tests` 판정(`readTestsWithEnv`, C-14) | 문자열: `az://`면 원격 로더. `yaml`/`yml`로 끝나면 글롭 로더(R-37). 아니고 글롭 문자가 없거나 그 이름의 파일이 실제로 있으면 단일 소스 로더(R-31). 그 밖에는 배열 항목처럼 처리. `{path, config}` 객체: 단일 소스 로더(`config`는 생성기 인자). 배열: 항목마다 — 문자열이 원격 참조이거나 JS/Python/xlsx/`:함수` 형태면 단일 소스 로더, 그 밖 문자열은 글롭 로더, `{path,config}`는 단일 소스 로더, 객체는 인라인 `TestCase`(R-39). 그 밖 타입은 경고 `Unsupported 'tests' format` 후 `[]`. 문자열 입력은 `{{ env.X }}`를 먼저 렌더한다 | 코드 확인 |
| R-31 | 단일 소스 로더(로컬 파일)(C-13) | 경로에서 `file://`를 떼고 `basePath`로 절대화. 콜론이 2개 이상이면 `Too many colons…`. 마지막 콜론 뒤는 함수명(JS/Python만 쓰임). 확장자: `.js` 계열 → R-35(JS 생성기), `.py` → Python 생성기(기본 함수 `generate_tests`, 목록이 아니면 `Python test function must return a list of test cases, got <타입>`), `.csv` → R-32, `.xlsx/.xls`(시트 지정 `#` 포함) → R-33, `.json` → R-34, `.jsonl` → R-34, `.yaml/.yml` → R-34. 그 밖은 `[]`(예: 디렉터리 경로를 문자열 `tests`로 주면 빈 목록) | 코드 확인 |
| R-32 | CSV 테스트 파일(C-15) | `PROMPTFOO_CSV_DELIMITER`(기본 `,`)로 BOM을 허용해 `columns:true` 파싱. 먼저 엄격 파싱하고 실패하면 느슨한 따옴표로 재시도(`PROMPTFOO_CSV_STRICT`면 재시도 없음). 행 → `TestCase`: 열 이름(앞뒤 공백 제거)이 `__expected`·`__expected<N>` → 어서션(값을 `assertionFromString`으로 변환, 빈 값은 건너뜀), `__prefix`/`__suffix` → `options.prefix/suffix`, `__description`, `__providerOutput`, `__metric`(모든 어서션의 `metric`), `__threshold`, `__metadata:<키>`(키가 `[]`로 끝나면 `,`로 나눠 배열, `\,`는 쉼표), `__config:__expected[<N>]:threshold`(해당 어서션의 threshold)이고 나머지 열은 모두 `vars[열]=문자열`이다. 한 줄 밑줄(`_expected` 등)은 경고. 설명이 없으면 `Row #<n>`. `vars` 값은 항상 문자열이라 셀에 `file://…`를 쓰면 R-46이 적용된다 | 코드 확인 |
| R-33 | xlsx/xls 테스트 파일 | 선택 의존 `read-excel-file`이 없으면 설치 안내 오류. `경로#이름` 또는 `경로#<1기반 정수>`로 시트를 고르고 기본은 첫 시트. 시트가 없거나 범위를 벗어나면 `Sheet "…" not found. Available sheets: …`, 빈 시트·헤더만 있는 시트·데이터가 모두 빈 칸이면 오류. 첫 행이 헤더, 빈 칸은 `''`, 값은 문자열화해서 CSV 행과 같은 규칙(R-32)으로 변환 | 코드 확인 |
| R-34 | JSON/JSONL/YAML 테스트 파일 | 글롭 로더(R-37; 문자열 `tests`가 `yaml/yml`로 끝나거나 배열 항목 문자열일 때): 파싱 후 `file://` 재귀 해석(`vars` 안의 값은 그대로 둠)과 `$ref` 역참조를 하고 단일 객체면 배열로 감싼다. `description` 기본값은 없다. 단일 소스 로더(`{path, config}` 형태 등, R-31): JSON은 YAML 파서로 읽어 배열 또는 단일 객체를 `TestCase[]`로, JSONL은 빈 줄 제외 한 줄 한 케이스(실패 시 `Failed to parse JSONL test file <경로> on line <n>`)이고 둘 다 `description`이 없으면 `Row #<n>`을 채운다. **YAML은 단일 소스 로더에서 각 항목을 CSV 행처럼 `testCaseFromCsvRow`로 변환한다**: 항목의 모든 키가 `vars`가 되므로(`__expected` 같은 특수 키만 해석), `vars:`/`assert:` 구조의 `TestCase` YAML은 문자열 `tests`나 배열 항목(글롭 로더)으로 줘야 의도대로 읽힌다 | 코드 확인 |
| R-35 | 원격·생성기 소스(경계) | `huggingface://datasets/…`, Google Sheets URL, SharePoint URL, `az://…`는 각 로더가 `TestCase[]`를 만든다(Sheets·SharePoint는 CSV 행 규칙 R-32). 원격 결과는 `metadata.__promptfoo.remote = true`가 붙고 이후 `file://`·provider 재해석을 받지 않는다. JS 생성기는 모듈 export가 함수면 `config`(중첩 `file://`를 읽은 값)를 인자로 호출한 결과, 아니면 export 자체를 쓴다. 반환 안에 함수·provider 인스턴스가 있으면 저장·재개 불가 경고. 각 로더의 내부(HTTP, 인증, 페이징, 제한 쿼리)는 이 스펙 밖이다 | 코드 확인(경계만) |
| R-36 | 원격이 아닌 소스의 `{{ env.X }}` | 소스 문자열·`vars` 파일 참조에서 env 템플릿만 렌더된다 | 코드 확인 |
| R-37 | 글롭 로더(`loadTestsFromGlobWithEnv`) | `file://`를 떼고 `basePath`로 절대화. 그 경로가 실제 존재하면 그것 하나, 아니면 글롭 확장. JS/Python 파일은 `:함수` 접미가 붙어도 목록에 추가한다. 일치 0건: 글롭 문자가 없는 경로면 `No test files found for path: <절대경로>` 오류, 글롭 문자가 있으면 경고 후 0행. 파일별로: `.csv`·Google Sheets·JS·Python·xlsx → 단일 소스 로더, `.yaml/.yml/.jsonl/.json` → 파싱·`file://` 해석·`$ref` 역참조, 그 밖(디렉터리 포함) → `Unsupported file type for test file: <경로>`. 각 행은 행이 놓인 파일의 디렉터리를 `vars` 파일 목록·provider 스크립트의 기준으로 쓴다(인라인 `file://` 변수는 설정 디렉터리 기준 유지) | 코드 확인 |
| R-38 | 테스트 행 검증(`defaultTest` 아닌 행) | `assert, vars, options, metadata, provider, providerOutput, threshold(숫자)` 중 하나도 없고 `description`만 있는 행도 아니면 `Test case must contain assert, vars, options, metadata, provider, providerOutput, threshold, or only a description.` 오류 | 코드 확인 |
| R-39 | 테스트 행의 `vars`(`loadTestWithVars`, `readTestFiles`) | 객체면 그대로. 문자열·문자열 배열이면 vars 파일 경로(글롭 가능, `basePath` 기준)로 보고 각 YAML 파일을 읽어(`file://` 재귀 해석) `Object.assign`으로 합친다(뒤가 이김). 값의 `file://` 문자열은 이 단계에서 읽지 않는다. 저장 가능한 행을 만들 때(`readTestConfigs`) `file://` 값(중첩 객체·배열 포함, `{{ env }}` 렌더)은 `file://<절대경로>`로 바뀐다. 값이 `null`인 변수는 스키마 위반 | 코드 확인 |
| R-40 | 테스트 행의 `provider` | `readTests`/`readTest`(둘째 패스)가 문자열·`{id,…}` 객체를 `loadApiProvider`로 만든다(경로 기준: 행이 놓인 파일 디렉터리 또는 저장된 `metadata.__promptfoo.providerBasePath`). 저장용 `config.tests`(첫 패스, `readTestConfigs`)에는 선언한 문자열·객체가 그대로 남고, JS 생성기 등이 넘긴 `ApiProvider` 인스턴스만 `undefined`로 치환된다. 설정 안에서 `provider: file://….yaml`은 설정 디렉터리 기준 | 코드 확인 |
| R-41 | `defaultTest` | `file://` 문자열이면 `maybeLoadFromExternalFile`로 읽은 YAML/JSON 객체(파일 하나, 상대 경로는 `basePath` 기준), 객체면 그대로. `readTestConfig(…, isDefaultTest=true)`로 `vars`의 `file://`를 절대화하고 행 검증은 생략한다. `TestSuite.defaultTest`는 항상 객체이며 `{metadata: config.metadata, …defaultTest, options: {prefix: --prompt-prefix, suffix: --prompt-suffix, provider: --grader, …defaultTest.options}}`다: 설정의 `defaultTest.options`가 CLI의 prefix/suffix/grader 값보다 우선하고, `defaultTest.metadata`가 있으면 `config.metadata`는 병합되지 않고 대체된다 | 코드 확인 |
| R-42 | `scenarios` | `file://` 문자열 항목은 읽어서(글롭이면 배열) 시나리오 객체로 바꾼다. 로딩 때 `scenario.tests`(문자열이면 외부 파일, 배열이면 `readTestConfigs`)를 읽고 `--filter-first-n/pattern/failing/sample`을 시나리오 테스트에 적용한다(`config.scenarios`에는 필터된 행을 저장). `scenario.config`는 해석하지 않는다(다중 설정 때 절대화만). `[]`·`undefined`면 시나리오 없음. 시나리오가 `TestSuite.scenarios`로 가고, 실행 시 `config[i] × tests[j]`로 펼쳐진다(`evaluator.ts:2875-2940`: 변수·옵션·메타데이터는 `defaultTest < config 항목 < 테스트`로 병합, 어서션은 `config 항목 + 테스트`를 이어 붙임). 이 펼침은 eval-run 소유다 | 코드 확인 |
| R-43 | 테스트 `vars` 안의 `assert` 키 | 테스트가 하나라도 `vars.assert`를 가지면 경고(`PROMPTFOO_NO_TESTCASE_ASSERT_WARNING`으로 끔). 동작은 바뀌지 않는다 | 코드 확인 |
| R-44 | 로딩 끝의 검증(`load.ts:1325-1344`) | 최상위 `tests`와 `defaultTest`의 `assert`가 배열이고 각 항목이 `type`을 가진 어서션 스키마인지 검사한다(10000개 초과 불가, `assert-set`은 재귀). 시나리오 테스트의 `assert`는 이 시점 검사 대상이 아니다. `tests`·`defaultTest`·시나리오의 `providers` 필터가 로드된 provider id·label에 모두 존재해야 한다(`ProviderReferenceValidationError`). `tests`·`defaultTest`의 `prompts` 필터는 로드된 프롬프트의 label·id와 일치(정확히 / `접두어*` / `그룹` 이 `그룹:…`과 일치)해야 한다(`PromptReferenceValidationError`, 설정 YAML에서 줄·열 위치를 찾아 붙임). 위반은 모두 던진다 | 코드 확인 |
| R-45 | **SKILL.md를 프롬프트 파일로 넣음**: `prompts: [file://skills/x/SKILL.md]`(또는 `./SKILL.md`, 맨 경로 `SKILL.md`) | `.md`이므로 R-20: 프롬프트 1개, `raw`는 YAML 프런트매터를 포함한 파일 전체(가공 없음), `label`은 `<설정 기준 상대 경로>: <내용 앞 50자>...`(`label:`을 주면 그 값). `{id: file://…, label: skill-v1, config: {…}}`로 이름·설정을 줄 수 있다. 같은 내용을 `.txt`로 두면 R-21로 `---` 줄에서 쪼개지므로(프런트매터 구분선 포함) 쓰면 안 된다. 이 `raw`는 렌더 때 Nunjucks 템플릿으로 취급된다(R-48) | 코드 확인 |
| R-46 | **변수로 넣음**: 테스트·`defaultTest`·CSV 셀·`--var`의 값이 `file://…`로 시작하는 문자열(예: `vars: {skill: file://skills/x/SKILL.md}`) | 로딩 단계에서는 읽지 않고 경로만 절대화한다(R-39). 평가 단계: (a) 단계 목록을 만드는 중(provider 호출 전) `generateVarCombinations`가 `file://` 값을 `basePath` 기준 글롭으로 푼다. 글롭 문자 없는 일반 경로도 같은 글롭 호출을 거치므로 **없는 파일은 일치 0건**이고, `No files found for variable <이름> at path …`가 나서 호출 0회로 평가 전체가 실패한다(테스트마다 나는 오류가 아님, [eval-run](./eval-run.md) R-18). n건이면 테스트가 n개 조합으로 늘어난다(`disableVarExpansion` 또는 `PROMPTFOO_DISABLE_VAR_EXPANSION`이면 펼치지 않음). (b) `renderPrompt`가 확장자로 읽는다: `.js/.ts…`는 실행해 `{output: string}`(함수 시그니처 `(변수명, 프롬프트 원문, vars, provider)`), `.py`는 `get_var`를 호출해 `{output}`을 `trim`, `.yaml/.yml`은 파싱 후 `JSON.stringify`한 문자열, `.pdf`는 텍스트 추출, 이미지는 `data:<mime>;base64,<데이터>`, 비디오·오디오는 순수 base64(미디어는 환경 스위치로 끔), **그 밖의 모든 확장자(`.md`, `.txt`, `.json` 포함)는 UTF-8 텍스트를 `trim()`한 문자열**이다. `.json`도 객체로 파싱하지 않는다. 변수는 호출마다 파일을 다시 읽고(캐시 없음) 호출자가 넘긴 `vars` 객체를 제자리에서 바꾼다. 읽는 시점에 파일이 없으면 ENOENT를 던진다(변수 펼침이 켜져 있으면 (a)에서 먼저 걸러지므로 펼침을 끈 경우에만 해당). 크기·인코딩 제한은 코드에 없다(BOM 제거 없음) | 코드 확인 |
| R-47 | 변수 값을 읽은 뒤 템플릿이 만들어지는 순서(`renderPrompt` 424-545) | (1) 문자열 변수 끝의 `\n` 하나를 제거. (2) `resolveVariables`: 변수 값 안의 `{{ name }}`(공백 허용, `\w+`만)을 다른 변수 값으로 치환, 최대 5회(`$&` 등 특수 치환 패턴은 글자 그대로). (3) 프롬프트 원문이 유효한 JSON이면(`PROMPTFOO_DISABLE_JSON_AUTOESCAPE` 없을 때) 안의 모든 문자열을 `vars`로 Nunjucks 렌더하고 `JSON.stringify(…, null, 2)`로 되돌린다. 이때 변수 값은 다시 렌더되지 않고 그대로 들어간다. (4) 그렇지 않으면(JSON이 아니거나 (3) 도중 예외가 나면) 문자열 변수 값을 하나씩 먼저 Nunjucks로 렌더하고(값 안에서 `env` 외의 정의되지 않은 변수를 하나라도 참조하면 그 값은 렌더하지 않고 그대로), 그 결과 변수들로 프롬프트 원문(R-48의 `raw` 자동 래핑 적용)을 렌더한다. `PROMPTFOO_DISABLE_JSON_AUTOESCAPE`이면 (3)·변수 사전 렌더 없이 원문을 원래 `vars`로 바로 렌더한다. Nunjucks 환경은 `autoescape: false`, `throwOnUndefined: false`(정의되지 않은 `{{x}}`는 빈 문자열)다. 문법 오류는 던진다 | 코드 확인 |
| R-48 | 파일 내용에 `{{`·`{%`·`{#`가 있음(SKILL.md의 예시 코드, 템플릿 구문) | **프롬프트 파일로 넣은 경우**(R-45) 내용이 템플릿 원문이므로 항상 렌더된다: 정의되지 않은 `{{x}}`는 사라지고, 닫히지 않은 열림 태그(줄 끝까지 닫힘이 없는 `{{`·`{%`·`{#`)가 있고 `{% raw %}…{% endraw %}`가 없으면 프롬프트 전체를 `{% raw %}`로 감싸서 렌더하므로 그 프롬프트의 `{{task}}` 같은 자리표시자도 치환되지 않는다. **변수로 넣은 경우**(R-46)는 (3)의 JSON 프롬프트 경로에서는 변수 안의 템플릿이 평가되지 않는다. (4)의 문자열 프롬프트 경로에서는 변수 값도 렌더 대상이다: 값에 정의되지 않은 변수 참조가 하나라도 있으면 값 전체를 그대로 두고, 모두 정의되어 있으면 렌더되며(`{{ 1+1 }}`처럼 변수 이름으로 시작하지 않는 식은 정의 검사에서 빠짐), 닫히지 않은 태그가 있으면 값 전체를 `raw`로 감싸 렌더한다. 이 절차 어느 것도 파일 내용을 이스케이프해 주지 않는다 | 코드 확인 |
| R-49 | `--var key=file://…` | `defaultTest.vars`에 `{…기존, …CLI}`로 얹힌다(재개 실행 제외). 경로는 절대화되지 않고 렌더 때 `cliState.basePath`(설정 디렉터리) 기준으로 해석되며, 글롭 확장은 `basePath`에서 한다 | 코드 확인 |
| R-50 | 변수·프롬프트 경로 해석 | 상대 경로는 설정 파일 디렉터리(또는 설정의 `basePath`)가 기준이다. `..`로 밖을 가리켜도, 절대 경로도 막지 않는다(경로 제한 없음). 다중 설정에서 테스트의 `vars`와 `prompts`는 그 설정의 디렉터리를 기준으로 절대화되어 합쳐진다 | 코드 확인 |
| R-51 | 모델이 챗 형식(`[{role,content}]`)일 때 SKILL.md를 system 메시지로 | 프롬프트를 JSON 파일(`.json`)이나 인라인 JSON 문자열로 쓰고 `content`에 `{{skill}}`을, `vars.skill`에 `file://…/SKILL.md`를 둔다. R-47(3)에 따라 결과는 들여쓰기 2칸의 JSON이고 `skill` 자리에는 R-46의 `trim`된 파일 내용이 JSON 문자열로 이스케이프되어 들어간다(변수 값 안의 템플릿은 평가되지 않지만 `{{다른변수}}` 단순 자리표시자는 R-47(2)로 치환된다) | 코드 확인 |
| R-52 | 경로의 `{{ env.X }}` | `file://{{ env.SKILL_DIR }}/SKILL.md`처럼 쓰면 설정 읽기(R-05)·프롬프트·테스트 참조 절대화(R-10, R-39) 단계에서 env만 렌더된다 | 코드 확인 |
| R-53 | 환경 값의 계층 | `PROMPTFOO_*` 스위치와 템플릿 `env`는 설정 `env` 블록(및 provider 환경) > env 파일 > `process.env` 순서로 읽는다. 설정의 `env` 값 숫자·불린은 문자열로 바꿔 provider·테스트 로딩에 준다(`config.env`에는 작성 그대로 남음). `env`가 객체 대신 문자열(예: 문서가 보여 주는 `env: file://configs/env.yaml`)이면 이 로더에는 그 파일을 읽는 코드가 없다(스키마 경고, D-3) | 코드 확인 / 효과는 추론 |

- 불변식:
  - 설정 파일·프롬프트 파일·테스트 파일을 읽는 동안 쓰기는 없다(R-25의 실행 파일·스크립트 부작용 제외).
  - 합쳐진 `config.prompts`(문자열·객체)의 파일 참조는 `file://` 접두를 유지한 채 절대 경로이거나 R-10의 예외(템플릿 잔여·원격)다.
  - `testSuite.tests`의 모든 행은 R-38을 통과했고(`defaultTest`와 원격 행 제외), `testSuite.defaultTest`는 객체다.
  - `config.tests`는 재생 가능한 선언형 행이다(provider 인스턴스 없음, `vars`의 `file://`는 절대 경로).
- 미결정: 없음. 문서와 구현이 다른 지점(D-1~D-5)은 구현대로 R-ID에 썼다. 실행으로 확인되지 않은 정적 추적(R-17, R-26)은 아래 확인 한계에 둔다.
- 확인 한계:
  - 코드 읽기만 했고 어떤 명령도 실행하지 않았다. 따라서 R-17(`/`가 들어간 인라인 프롬프트)과 R-26(디렉터리 프롬프트)은 `glob`·`path` 라이브러리가 코드에서 가정한 대로 동작한다는 전제의 정적 추적이다.
  - `$ref` 해석 범위(원격 URL, 외부 파일, 순환 참조)는 `@apidevtools/json-schema-ref-parser` 기본값에 달려 있고 읽지 않았다(R-04).
  - 글롭 결과 순서는 `glob` 라이브러리가 정한다(코드에서 정렬하지 않음). 여러 파일이 같은 키를 덮으면(R-09) 결과가 이 순서에 의존한다.
  - Windows 경로는 드라이브 문자 콜론 보호 코드가 있다는 것만 확인했고 동작은 검증하지 않았다.
  - 원격 로더(HF·Sheets·SharePoint·Azure)·`importModule`·`runPython`·`loadApiProviders`·클라우드 설정·`tracing` 자격 증명 보존(`preserveTracingCredentialReferences`)은 경계만 읽었다.

### 1.5 필수 코드 참조

라이선스: MIT(overview 1절). 이 스펙은 코드를 복사하지 않고 위치만 가리킨다. 사용 시 원본의 저작권·허가 문구를 유지한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/util/config/extensions.ts:5-15` `DEFAULT_CONFIG_EXTENSIONS`, `src/util/config/default.ts:9-27` `loadDefaultConfig` | 기본 설정 확장자 우선순위 | R-01 |
| C-02 | `src/util/config/load.ts:354-472` `readConfigInScope`, `normalizeLoadedConfig` | 파일 형식 분기, 검증 스키마 구성(선언형 `prompts`·`providers`·`targets` 완화, `refine`), 별칭 이동, 기본 prompts | R-03, R-06~R-08 |
| C-03 | `src/util/config/load.ts:188-297` `dereferenceConfig`; `:309-342` `renderConfigEnvTemplates`; `src/util/render.ts:13-31,50-146` `replaceTemplates`, `renderEnvOnlyInObject` | `$ref` 역참조와 파라미터 보존, env 전용 2패스 렌더(`{{`~다음 `}}` 단위로 스캔, `env.`·`env[`를 참조하는 것만 렌더, 정의 안 된 값은 보존) | R-04, R-05 |
| C-04 | `src/util/templates.ts:423-472` `templateEnv`, `:474-515` `getNunjucksEngine` | 템플릿 `env` 전역의 계층, `autoescape:false`, `throwOnUndefined` 기본 `false`, `load` 필터 | R-05, R-47 |
| C-05 | `src/util/config/load.ts:577-922` `prepareCombinedConfig` | 합치기 표(providers 중복 키, prompts 절대화·중복 제거·맵/배열 혼합 금지, tests 소스별 `basePath`, defaultTest·sharing·env 병합, scenarios 로드) | R-09, R-10 |
| C-06 | `src/util/config/load.ts:995-1371` `resolveLoadedConfig` | CLI·설정·기본 설정 우선순위, 필수 검사, defaultTest 읽기·조립, providers·prompts·tests·scenarios 읽는 순서, 검증 호출, `envPath` 절대화 | R-11~R-15, R-41, R-42, R-44 |
| C-07 | `src/prompts/constants.ts:1-15` `VALID_FILE_EXTENSIONS`, `src/prompts/utils.ts:11-89` `maybeFilePath`, `normalizeInput` | 파일 판정 규칙, 입력 정규화 | R-16, R-17 |
| C-08 | `src/prompts/index.ts:27-218` `processPromptFile`, `processPrompt`, `readPrompts` | 확장자 분기 순서, `exec:`, 글롭 한 단계 재귀·라벨·ID 규칙·문자열 폴백, 빈 결과 오류 | R-18~R-20, R-26~R-28 |
| C-09 | `src/util/file.ts:369-425` `parsePathOrGlob`, `src/util/pathUtils.ts:34-44` `safeResolve` | `file://` 제거, `:함수` 접미 규칙, 존재 확인과 `PROMPTFOO_STRICT_FILES`, 글롭·디렉터리 판정 | R-19, R-26 |
| C-10 | `src/prompts/processors/text.ts:13-71`, `json.ts:15-44`, `jsonl.ts:14-29`, `yaml.ts:20-46`, `csv.ts:29-114`, `string.ts:11-23` | 형식별 `raw`·`label` 생성 규칙(청크 구분, BOM, `file://` 재귀 해석, CSV 헤더·라벨 중복 처리) | R-20~R-24 |
| C-11 | `src/util/file.ts:125-359` `maybeLoadFromExternalFile`, `maybeLoadConfigFromExternalFile` | 설정 안 `file://` 로더: `.json`/`.yaml`/`.csv`(단일 열이면 값 배열)/그 밖 텍스트, 글롭이면 배열, `assertion`·`vars` 문맥 보존, 환경 렌더 | R-22, R-34, R-41, R-42 |
| C-12 | `src/prompts/processors/javascript.ts:27-50`, `python.ts:20-106`, `executable.ts:19-143` | 프롬프트 함수 컨텍스트와 래핑, 실행 파일 라벨·원문·캐시·타임아웃 | R-25 |
| C-13 | `src/util/testCaseReader.ts:113-148,202-302` `readStandaloneTestsFile`, `readLocalStandaloneTestsFile`, `getStandaloneTestsFileMetadata` | 소스 종류 분기, 확장자·시트·함수 접미 파싱 | R-31, R-35 |
| C-14 | `src/util/testCaseReader.ts:632-747`, `:770-888` `loadTestsFromGlobWithEnv`, `readTestsWithEnv` | `tests` 입력 형태 판정, 글롭 로더, 원격 판정 `isRemoteTestsReference`(`:925`) | R-30, R-37 |
| C-15 | `src/csv.ts:43-120` `assertionFromString`, `:159-345` `testCaseFromCsvRow` | CSV 특수 열과 `__expected` 문자열 → 어서션 변환(`javascript:`·`fn:`·`eval:`·`python:`·`grade:`·`llm-rubric:`·`(not-)?type(threshold)?:value`·기본 `equals`) | R-32 |
| C-16 | `src/util/xlsx.ts:1-130` `getSheetIndex`, `parseXlsxFile` | 시트 지정, 오류 조건, 셀 문자열화 | R-33 |
| C-17 | `src/util/testCaseReader.ts:448-613` `loadTestWithVars`, `readTestWithEnv`, `validateTestCase`; `:484-501` `resolveVarsFileReferences`; `:67-90` `readTestFiles` | 행 로딩, vars 파일 합치기, `file://` 절대화, provider 기준 디렉터리, 행 검증 | R-38~R-40 |
| C-18 | `src/evaluatorHelpers.ts:54-115` `resolveVariables`, `autoWrapRawIfPartialNunjucks`, `referencesUndefinedVariables`; `:242-546` `renderPrompt` | 변수 `file://` 로더 확장자 분기(`:254-395`), 프롬프트 함수 결과 처리(`:397-422`), 렌더 순서·JSON 경로(`:424-545`) | R-25, R-46~R-48, R-51 |
| C-19 | `src/evaluator.ts:2142-2190` `generateVarCombinations` | 변수 `file://` 글롭 확장, 배열 확장 | R-46 |
| C-20 | `src/evaluator.ts:2875-2940` `buildTestsFromSuite`, `mergeScenarioTest`; `:3044-3086` `prepareTestCaseForEval` | 시나리오 펼침과 `defaultTest` 병합(경계 참고용) | R-42 |
| C-21 | `src/util/providerRef.ts:125-130,184-280` `isProviderConfigFileReference`, `normalizeProviderRef`; `src/providers/index.ts:368-421` `resolveProviderConfigs`; `src/util/config/load.ts:151-186` `resolveCliProvidersWithConfig` | provider 항목 형태 분류, 파일 provider 펼침, `--providers` 토큰 대응 | R-15 |
| C-22 | `src/util/promptMatching.ts:22-50` `doesPromptRefMatch`; `src/util/validateTestProviderReferences.ts`; `src/assertions/validateAssertions.ts:86-125` | prompt·provider 참조 검증 규칙(label/id 일치, `접두*`, `그룹:` 접두), 어서션 검증 | R-44 |
| C-23 | `src/types/index.ts:107-161, 947-1103, 1181-1307, 1312-1499` | `CommandLineOptions`, `TestCase`, `Scenario`, `TestGeneratorConfig`, `TestSuite`, `TestSuiteConfig`, `UnifiedConfig` 필드 정의(1.3의 표와 함께 읽음) | 1.3, R-06 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(정적 추적). 원본 테스트(`test/prompts/*.test.ts`)는 사례 이름을 확인했을 뿐이고 실행하지 않았다. 외부 로더·provider는 쓰지 않는다(설정은 provider 없이 `type`을 주거나 `echo`로 가정).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-20, R-45 | `SKILL.md` 내용 `---\nname: x\n---\n본문\n`. `readPrompts(['file://SKILL.md'], dir)` | 1개. `raw`는 파일 내용과 완전히 같음(`---` 줄 포함, 끝 개행 유지). `label`은 `<라벨경로>: ---\nname: x\n---\n본문\n...`(내용 앞 50자 + `...`). 라벨경로는 이 호출에서는 `dir/SKILL.md` 절대 경로, `resolveConfigs` 경유 시 작업 디렉터리 기준 상대 경로 |
| T-02 | R-21, R-45 | 같은 내용을 `skill.txt`로 두고 같은 호출 | 2개: `name: x`, `본문`(앞의 빈 청크는 버려짐, `---` 줄이 구분자). 각 `raw`는 `trim`됨. `.md`와 다른 결과다 |
| T-03 | R-46, R-47, R-51 | 프롬프트 `[{"role":"system","content":"{{skill}}"},{"role":"user","content":"{{task}}"}]`, vars `{skill:'file://SKILL.md', task:'T'}`, `SKILL.md`=`"  # S\n사용: {{task}}\n"` | `renderPrompt` 결과는 2칸 들여쓰기 JSON. system `content`는 `"# S\n사용: T"`(앞뒤 공백 제거, `{{task}}`는 `resolveVariables`로 치환), user는 `"T"` |
| T-04 | R-47, R-48 | 문자열 프롬프트 `"스킬:\n{{skill}}"`, `vars.skill=file://SKILL.md`. (a) 파일 내용 `예 {{ unknown }}` (b) 내용 `예 {{ task }}`, `vars.task='T'` | (a) 정의되지 않은 변수를 참조하므로 값이 그대로 들어가 `스킬:\n예 {{ unknown }}`. (b) `스킬:\n예 T` |
| T-05 | R-48 | 프롬프트 파일 `SKILL.md`(R-45)에 `표본: {{ name }}` 한 줄과 `예시 {{` (닫히지 않음)이 모두 있음, `vars.name='N'` | 닫히지 않은 열림 태그가 있으므로 전체가 `{% raw %}`로 감싸져 렌더 결과가 원문과 같고 `{{ name }}`도 `N`으로 바뀌지 않는다 |
| T-06 | R-17, R-26 | `readPrompts(['Run /commit'])` / `['Run /commit?']` / `['Run /commit\nnow']` | 첫째 `There are no prompts in "Run /commit"` 오류. 둘째 `raw: 'Run /commit?'` 문자열 프롬프트 1개(글롭 일치 없음). 셋째 개행 때문에 파일로 보지 않아 문자열 프롬프트 |
| T-07 | R-26 | `readPrompts(['file://missing.md'], dir)` / `['file://missing-*.md']` | 첫째 ENOENT(`readFileSync`) 오류. 둘째 `raw: 'file://missing-*.md'` 문자열 프롬프트 1개 |
| T-08 | R-28, R-45 | `readPrompts([{id:'file://SKILL.md', label:'skill-v1', config:{temperature:0}}], dir)` | 1개, `label:'skill-v1'`, `config` 전달, `raw`=파일 내용, `id` 필드는 없음. 평가 기록 prompt id는 `sha256('skill-v1')` |
| T-09 | R-09, R-10 | `-c a.yaml b.yaml`: a=`{providers:[p1], prompts:['file://a.md'], tests:[{vars:{x:'1'}}]}`, b=`{providers:[p1,p2], prompts:['file://b.md'], defaultTest:{assert:[A]}}`(서로 다른 디렉터리) | `providers=[p1,p2]`(중복 제거), `prompts`는 두 절대 경로(`file://<a디렉터리>/a.md`, `file://<b디렉터리>/b.md`) 순서대로, `basePath`=a의 디렉터리, `defaultTest.assert=[A]` |
| T-10 | R-06, R-07 | (a) `description: 5`를 가진 설정 (b) `commandLineOptions: {maxConcurrency: -1}` | (a) `Invalid configuration file …` 경고 후 계속 진행. (b) `Invalid commandLineOptions in configuration file …` 오류로 실패 |
| T-11 | R-32 | CSV `question,__expected,__description\nQ1,contains:foo,d\n`, `tests: file://t.csv` | 1행 `{vars:{question:'Q1'}, assert:[{type:'contains', value:'foo'}], options:{}, description:'d'}` |
| T-12 | R-33 | `tests: file://t.xlsx#2` / `file://t.xlsx#Nope`(시트 2개) | 둘째 시트의 행 / `Sheet "Nope" not found. Available sheets: …` |
| T-13 | R-37 | `tests: [file://cases/*.yaml]`에서 일치 0건 / `tests: file://cases/missing.yaml` | 경고 `No test files found…`와 0행(글롭 문자 있음) / `No test files found for path: …` 오류(글롭 문자 없음) |
| T-14 | R-46 | `vars: {doc: 'file://docs/*.md'}`, 일치 파일 2개 / 0개 | 평가 시 테스트가 2개 조합으로 늘어남 / 단계 목록을 만드는 중(provider 호출 0회) `No files found for variable doc at path <절대경로>/docs/*.md in directory <basePath>`로 평가 전체 실패(로딩 때 절대화됨, R-39; [eval-run](./eval-run.md) R-18, T-17) |
| T-15 | R-46 | `vars.a='file://a.json'`(내용 `{"k":1}\n`), `vars.b='file://b.yaml'`(내용 `k: 1\n`) | `a`는 문자열 `{"k":1}`(파싱 안 함, `trim`), `b`는 문자열 `{"k":1}`(`JSON.stringify`) |
| T-16 | R-07, R-12 | `targets: [echo]`에 `providers` 없음 + `prompts: ['hi']` / `providers`·`targets`를 모두 줌 | 첫째 `providers=['echo']`로 정상. 둘째 스키마 경고 후 `targets`가 `providers`를 덮어씀 |
| T-17 | R-01 | 한 디렉터리에 `promptfooconfig.yaml`과 `.json`이 둘 다 있음 | `.yaml`만 읽음 |
| T-18 | R-41 | `defaultTest: file://dt.yaml`(내용 `vars: {skill: file://SKILL.md}\nassert: [..]`), `--prompt-prefix X` | `config.defaultTest.vars.skill`은 절대 `file://` 경로. `testSuite.defaultTest.options.prefix`는 `dt.yaml`에 `options.prefix`가 없으면 `X` |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repos/promptfoo@dfe2d45 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, `src/main.ts:66-69`, `src/node/doEval.ts:365-369` | 코드 읽기. 건너뛰는 명령 목록(`shouldSkipDefaultConfigLoading`)은 열지 않음 |
| R-02 | `src/util/config/load.ts:581-598` `prepareCombinedConfig`, `src/node/doEval.ts:371-408` | 코드 읽기 |
| R-03 | C-02 `load.ts:354-382`, `src/util/yamlLoad.ts:26-45`, `src/esm.ts:232-262` | 코드 읽기 |
| R-04 | C-03 `load.ts:188-297` | 코드 읽기. 라이브러리 기본 동작은 확인 한계 |
| R-05 | C-03 `load.ts:309-342`, `src/util/render.ts:50-146`, `src/util/templates.ts:423-472`, `src/envars.ts:583-592` | 코드 읽기 |
| R-06 | `load.ts:405-428`, `src/node/doEval.ts:834-843`, `src/commands/validate.ts:470-512`, `src/types/index.ts:1312-1499` | 코드 읽기 |
| R-07 | `load.ts:88-106,395-402,430-446,468-470`, `src/types/configAliases.ts` | 코드 읽기 |
| R-08 | `load.ts:447-467` | 코드 읽기 |
| R-09 | C-05 `load.ts:599-663,665-812,814-910` | 코드 읽기. 글롭 순서는 확인 한계 |
| R-10 | `load.ts:672-757,774-841` `resolveConfigPath`, `makeAbsolute`, `makeTestAbsolute`, `resolveNestedFileReferences` | 코드 읽기 |
| R-11 | `load.ts:946-953,1004-1036,1075-1097,1189-1196,1212-1216`, `src/commands/eval.ts:33-80`, `src/node/doEval.ts:806-812` | 코드 읽기 |
| R-12 | `load.ts:1101-1140,1286-1290` | 코드 읽기 |
| R-13 | `load.ts:1038-1049,1350-1362`, `site/docs/configuration/test-cases.md:593-616` | 코드 읽기. `--vars` 경로 차이는 D-4 |
| R-14 | `load.ts:942-953`, `src/node/doEval.ts:519` | 코드 읽기 |
| R-15 | C-21, `load.ts:1160-1211` | 코드 읽기. provider 생성 내부는 경계 |
| R-16 | C-07 `src/prompts/utils.ts:44-89`, `test/prompts/index.test.ts:57-69` | 코드 읽기, 테스트 사례 이름 열람 |
| R-17 | C-07 `utils.ts:11-36`, `src/prompts/index.ts:117-131,172-179`, `src/util/file.ts:369-425`, `test/prompts/utils.test.ts:46-66,117-119` | 코드 읽기, 정적 추적(미실행). `/`·확장자 위치 규칙은 테스트 사례 이름과 일치(테스트는 읽기만 함) |
| R-18 | `src/prompts/index.ts:105-115` | 코드 읽기 |
| R-19 | C-08 `index.ts:27-79`, C-09 | 코드 읽기 |
| R-20 | C-10 `text.ts:58-71`, `test/prompts/fileMetadata.test.ts:39-59` | 코드 읽기, 테스트 이름 열람 |
| R-21 | C-10 `text.ts:13-48`, `test/prompts/fileMetadata.test.ts:25,124` | 코드 읽기 |
| R-22 | C-10 `json.ts:15-44`, `yaml.ts:20-46`, `site/docs/providers/groq.md`(`prompts: file://openai-compatible-prompt-format.yaml` 사례를 grep으로 확인, 파일 본문은 열지 않음) | 코드 읽기 |
| R-23 | C-10 `csv.ts:29-114` | 코드 읽기 |
| R-24 | C-10 `jsonl.ts:14-29` | 코드 읽기 |
| R-25 | C-12, `src/evaluatorHelpers.ts:397-422` | 코드 읽기. 실행 파일·Python 호출 내부(`parseScriptParts`, `runPython`)는 경계 |
| R-26 | C-08 `index.ts:133-183,195-218`, C-09, `test/prompts/index.test.ts:71-105,513-519` | 코드 읽기, 정적 추적(미실행) |
| R-27 | C-08 `index.ts:140-170`, `src/models/prompt.ts:24-32`, `test/prompts/fileMetadata.test.ts:61-87` | 코드 읽기. id가 저장소에서 어떻게 쓰이는지는 eval-records |
| R-28 | `src/prompts/utils.ts:61-73`, `load.ts:701-719,774-789`, `src/validators/prompts.ts` | 코드 읽기 |
| R-29 | `load.ts:1189-1196` | 코드 읽기 |
| R-30 | C-14 `testCaseReader.ts:770-888` | 코드 읽기 |
| R-31 | C-13 | 코드 읽기 |
| R-32 | `testCaseReader.ts:343-378`, C-15 | 코드 읽기 |
| R-33 | C-16, `site/docs/configuration/test-cases.md:239-283` | 코드 읽기 |
| R-34 | `testCaseReader.ts:380-446,247-254,259-265,691-726`, C-15 | 코드 읽기(YAML이 단일 소스 로더에서 CSV 변환기를 거치는 점은 `:247-254`의 `csvRowsToTestCases` 호출에서 확인, 미실행) |
| R-35 | `testCaseReader.ts:50-61,113-200,315-341`, `src/integrations/huggingfaceDatasets.ts:152` | 경계만 읽음(로더 내부 미탐색) |
| R-36 | `testCaseReader.ts:118,777,484-501` | 코드 읽기 |
| R-37 | C-14 `testCaseReader.ts:632-747`, `test/util/testCaseReader.test.ts`(사례 이름: "warns and adds no rows when the glob matches nothing" 등) | 코드 읽기, 테스트 이름 열람 |
| R-38 | `testCaseReader.ts:590-613` | 코드 읽기 |
| R-39 | C-17 `testCaseReader.ts:448-459,67-90,484-501,549-563` | 코드 읽기 |
| R-40 | `testCaseReader.ts:503-582`, `load.ts:1219-1224`, `site/docs/configuration/test-cases.md:608-614` | 코드 읽기 |
| R-41 | `load.ts:1051-1061,1148-1153,1292-1301`, `src/evaluator.ts:3044-3086` | 코드 읽기 |
| R-42 | `load.ts:814-841,1226-1284`, C-20 | 코드 읽기. 펼침은 eval-run |
| R-43 | `testCaseReader.ts:867-885` | 코드 읽기 |
| R-44 | `load.ts:1325-1344`, C-22, `src/util/validateTestPromptReferences.ts:171-200` | 코드 읽기 |
| R-45 | C-08 `index.ts:49-51`, C-10 `text.ts:58-71`, `src/prompts/utils.ts:11-36`, `examples/config-custom-prompt-function/promptfooconfig.yaml:28`(`id: file://prompt.md` 사례) | 코드 읽기 |
| R-46 | C-18 `evaluatorHelpers.ts:254-395`, C-19, `site/docs/configuration/test-cases.md:580-640`, `examples/eval-rag/promptfooconfig.yaml:14`(`context: file://docs/reimbursement.md` 사례) | 코드 읽기. 문서와 차이는 D-1 |
| R-47 | C-18 `evaluatorHelpers.ts:424-545,54-94`, C-04 | 코드 읽기 |
| R-48 | C-18 `evaluatorHelpers.ts:97-115,507-545`, `src/util/templates.ts:522-560` | 코드 읽기. `extractVariablesFromTemplate`의 정규식 한계(복잡한 식)는 세부 미탐색 |
| R-49 | `src/node/doEval.ts:806-812`, `src/commands/eval.ts:71-77`, `evaluatorHelpers.ts:260-263` | 코드 읽기 |
| R-50 | `evaluatorHelpers.ts:260-263`, `load.ts:672-681`, `src/util/file.ts:182` | 코드 읽기. 경로 검사 코드를 찾지 못함(없음은 추론이 아니라 읽은 범위의 부재) |
| R-51 | `evaluatorHelpers.ts:507-519`, `site/docs/configuration/prompts.md:160-210` | 코드 읽기 |
| R-52 | `load.ts:309-342,672-681`, `testCaseReader.ts:484-501` | 코드 읽기 |
| R-53 | `src/envars.ts:515-559`, `load.ts:979-993,600`, `src/types/index.ts:1379-1391` | `env: file://…`의 효과(문자열 펼침)는 추론 |
| T-01~T-18 | 해당 R-ID의 근거 | 모두 구현에서 도출(정적 추적). 실행하지 않음. T-01의 `label` 문자열은 `labelPath`가 `readPrompts`에 준 기준에 따라 상대 경로 접두가 달라질 수 있음 |

**문서와 구현의 차이** (구현을 사실로 썼다)

| ID | 문서의 서술(위치) | 구현 | 관련 R-ID |
|---|---|---|---|
| D-1 | 변수 `file://`의 YAML/JSON은 "Parsed to object"(`site/docs/configuration/test-cases.md` "Supported File Types" 표) | `.yaml/.yml`은 `JSON.stringify`한 문자열, `.json`은 파싱하지 않고 텍스트(`trim`). 객체로 변수에 들어가는 경로는 `vars` 파일(`vars: path.yaml`)과 설정 안 `file://` 로더뿐이다 | R-46, R-39 |
| D-2 | `prompts: file://configs/prompts.yaml`(프롬프트 목록 YAML)와 `prompts: file://prompts/`(디렉터리), `tests: file://configs/tests/`가 여러 항목으로 펼쳐진다고 읽힘(`site/docs/configuration/modular-configs.md:25-96`) | YAML 프롬프트 파일은 목록이어도 프롬프트 1개(JSON 문자열, R-22). 글롭 문자가 없는 디렉터리 프롬프트는 원문 문자열 프롬프트(R-26). 문자열 `tests`가 디렉터리면 `[]`(R-31), 배열 항목이면 `Unsupported file type for test file`(R-37). 디렉터리를 쓰려면 `file://prompts/*`처럼 글롭을 줘야 한다 | R-22, R-26, R-31, R-37 |
| D-3 | `env: file://configs/env-prod.yaml`(`modular-configs.md:114`) | `env`를 파일에서 읽는 코드가 없다. 스키마는 객체만 받는다(R-06 경고) | R-53 |
| D-4 | "Explicit `--tests` and `--vars` paths resolve from the working directory"(`test-cases.md`) | `--tests`만 작업 디렉터리(`basePath: ''`), `--vars`는 설정이 있을 때 설정 `basePath` 기준(`load.ts:1213-1215`의 `cmdObj.tests ? '' : basePath`) | R-13 |
| D-5 | "Videos … Converted to base64" 표와 이미지 예시의 `data:image/jpeg;base64,{{image}}` | 이미지는 이미 `data:<mime>;base64,…` 전체 문자열이고, 비디오·오디오는 순수 base64(R-46). 문서 예시대로 접두를 한 번 더 붙이면 중복된다 | R-46 |

### 2.2 코드 읽는 순서

1. `src/node/doEval.ts:351-420`(설정 경로 정리) → `src/util/config/load.ts` `resolveConfigs`(928) → `prepareCombinedConfig`(577) → `resolveLoadedConfig`(995). 이 세 함수가 R-01~R-15, R-41~R-44의 전부다.
2. 프롬프트: `src/prompts/index.ts` `readPrompts`(195) → `processPrompt`(89) → `processPromptFile`(27) → `processors/*`. 파일 판정은 `utils.ts` `maybeFilePath`, 경로 파싱은 `util/file.ts` `parsePathOrGlob`.
3. 테스트: `util/testCaseReader.ts` `readTestsWithEnv`(770) → `loadStandalone`/`loadTestsFromGlobWithEnv` → `readLocalStandaloneTestsFile`(202) → `src/csv.ts` `testCaseFromCsvRow`.
4. 변수와 렌더(경계): `evaluator.ts` `generateVarCombinations`(2142) → `evaluatorHelpers.ts` `renderPrompt`(242).
5. 원본의 전략: 로딩을 두 번 한다. 첫 패스(`readTestConfigs`, provider 없음)가 저장·재생용 선언형 `config.tests`를 만들고, 둘째 패스(`readTest`)가 실행용 `testSuite.tests`를 만든다. 파일 참조 절대화는 첫 패스(`file://` 변수)와 합치기 단계(프롬프트·테스트 경로)에서 일어난다.

### 2.3 비교·재사용 출처

없음(다른 레포의 같은 기능 스펙 없음). 원본 코드를 복사하지 않았다.

## 적용 메모

원본 동작과 다르게 하려는 것은 아직 정하지 않았다. 사용 목적(내 SKILL.md를 여러 모델에 평가·개선하고 적합도를 기록)에서 이 스펙 범위의 주의점만 적는다.

| 관련 R-ID | 원본과 다르게 할 점(또는 주의) | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-45, R-46, R-51 | SKILL.md를 "시스템 지시문 텍스트"로 넣으려면 변수(`vars.skill: file://…`) + 챗 JSON 프롬프트 조합이 템플릿 평가를 가장 덜 탄다(JSON 경로는 변수 값을 다시 렌더하지 않음). `.md` 프롬프트로 직접 넣으면 내용 전체가 템플릿이 된다 | R-47, R-48: 예시 코드의 `{{ }}`·`{% %}`가 사라지거나 전체가 `raw`로 감싸짐 | 재구현 시 변수 값을 "데이터"로만 취급해 템플릿 평가를 끄는 옵션을 둘 수 있음(그러면 T-04, T-05 기대값이 달라짐) |
| R-27, R-45 | 스킬 버전을 기록하려면 프롬프트에 명시적 `label`(예: `skill-v1`)을 주는 편이 안전하다 | prompt id가 `sha256(label)`이고 `.md`의 기본 라벨은 경로 + 앞 50자라서, 내용이 앞 50자 이후만 바뀐 두 버전은 같은 id를 가진다(코드 확인) | 버전 식별자는 내용 해시로 따로 만들어 기록하는 편이 정확함(eval-records 쪽에서 확정) |
| R-17, R-26 | 한 줄짜리 프롬프트에 `/`가 있으면(`Run /commit`) 파일로 오판되어 오류가 난다. 객체 `raw`로 줘도 같은 판정을 거치므로 원본에서의 우회는 개행을 넣거나 `?` 같은 글롭 문자를 붙이는 것뿐이다. 재구현에서는 `file://`·확장자 명시 때만 파일로 보는 규칙이 더 예측 가능함 | 스킬 평가 프롬프트는 슬래시 명령·경로를 자주 포함함 | 파일 판정 규칙(C-07)을 바꾸면 R-17, T-06 기대값이 달라짐 |
| R-46 | 변수 `file://`가 없는 파일·글롭 0건이면 로딩이 아니라 평가의 단계 목록 구성 중에 터져 평가 전체가 실패한다 | R-46: 로딩 단계에서 `file://` 존재를 확인하지 않음 | 재구현에서는 로딩 단계에서 변수 `file://` 존재를 확인해 일찍 실패시키는 편이 낫다(바뀌는 흐름: R-39 뒤에 존재 확인 추가) |
