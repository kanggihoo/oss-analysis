---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/providers/registry.ts
  - src/providers/scriptBasedProvider.ts
  - src/providers/scriptResult.ts
  - src/providers/scriptContext.ts
  - src/providers/pythonCompletion.ts
  - src/providers/rubyCompletion.ts
  - src/providers/golangCompletion.ts
  - src/providers/scriptCompletion.ts
  - src/providers/providerRegistry.ts
  - src/python/workerPool.ts
  - src/python/worker.ts
  - src/python/persistent_wrapper.py
  - src/python/wrapper.py
  - src/python/wrapper.ts
  - src/python/pythonUtils.ts
  - src/python/stderr.ts
  - src/ruby/wrapper.rb
  - src/ruby/rubyUtils.ts
  - src/golang/wrapper.go
  - src/evaluatorHelpers.ts
  - src/evaluator.ts
  - src/util/transform.ts
  - src/util/file.ts
  - src/util/fileReference.ts
  - src/util/json.ts
  - src/util/secureTempFiles.ts
  - src/envars.ts
  - src/esm.ts
  - src/assertions/index.ts
  - src/assertions/python.ts
  - src/assertions/ruby.ts
  - src/assertions/scriptBody.ts
  - src/assertions/scriptResultNormalization.ts
  - src/assertions/utils.ts
  - src/util/caseMapping.ts
  - src/prompts/index.ts
  - src/prompts/processors/python.ts
  - src/prompts/processors/executable.ts
  - src/prompts/processors/javascript.ts
  - src/types/index.ts
  - src/contracts/providers.ts
  - src/util/config/load.ts
  - site/docs/providers/python.md
  - site/docs/providers/go.md
  - site/docs/providers/custom-script.md
  - site/docs/configuration/reference.md
depends: []
status: ready
reimplementation: 미실행
---

# 스크립트 브리지·확장 훅

> promptfoo가 Python·Ruby·Go·`exec:` 명령·JS 파일로 쓴 provider, 어서션, 프롬프트 함수, 변수 생성 함수, 변환을 어떤 함수 이름·입출력 JSON·프로세스 수명·타임아웃·오류 규칙으로 호출하는지, 그리고 `extensions` 훅이 평가 중 언제 어떤 컨텍스트로 불리고 그 반환값이 어떻게 반영되는지를 정의한다.

<!--
경로는 모두 repos/promptfoo/ 기준. 이 레포는 MIT(overview 1절)라 코드 인용·발췌에 제한이 없다.
원본은 실행하지 않았다(설치·빌드·네트워크 금지). 따라서 "실행 확인"은 하나도 없다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 흐름은 "Python 스크립트로 쓴 CLI 래퍼 provider + Python 맞춤 채점 + JS/Python 훅"이다.

1. 설정의 `providers: - id: file://wrap.py` 가 `createScriptBasedProviderFactory('python','py')` 에 걸려 `PythonProvider`가 만들어진다(C-01). 경로는 설정 파일 디렉터리(`config.basePath`) 기준으로 풀린다.
2. `beforeAll` 훅이 있으면 평가 시작 때 한 번, 테스트가 `RunEvalOptions`로 펼쳐지기 전에 `suite`를 받는다(R-28).
3. 평가 단계(provider × prompt × test × repeat) 하나마다 `beforeEach` 훅이 불리고 반환된 `test`가 쓰인다(R-29).
4. provider 첫 호출 때 `PythonProvider.initialize()`가 워커 풀을 만들고, 워커마다 `persistent_wrapper.py`를 띄워 `wrap.py`를 한 번 import한다(R-08, R-09). 이후 호출은 `[prompt, options, context]`를 임시 JSON 파일로 넘기고 stdin으로 `CALL|…` 한 줄을 보낸다(R-10).
5. 워커가 `call_api`를 실행해 `{"type":"result","data":…}`를 응답 파일에 쓰고 `DONE|<경로>`를 stdout으로 알린다. Node는 파일을 읽어 `output`/`error` 속성을 검증하고(R-05) 평가기가 응답을 처리한다(R-06).
6. 결과는 어서션으로 간다. `type: python`/`file://grade.py` 어서션은 일회성 프로세스에서 `get_assert(output, context)`를 실행하고, 반환값(bool/number/dict)이 `GradingResult`로 정규화된다(R-22~R-24).
7. 행이 만들어지면 `afterEach` 훅이 `{test, result}`를 받아 `namedScores`·`metadata`·`response.metadata`를 덧붙이고(R-30), 행이 저장된다. 전부 끝나면 `afterAll`이 전체 결과를 받는다(R-31). 평가가 끝나 스코프가 닫히면 워커 풀이 종료된다(R-15).

### 1.2 범위·통합 지점 [필수]

- 제공: 아래 호출 규칙 전부.
  - provider: `python:`/`file://*.py`, `ruby:`/`file://*.rb`, `golang:`/`file://*.go`, `exec:` 명령, `file://*.js|ts|…` 클래스.
  - 어서션 값: `file://x.py|.rb|.js[:fn]`과 인라인 `python`/`ruby` 코드.
  - 변수 생성: `file://gen.js|.py`.
  - 프롬프트 함수: `file://p.js|.py[:fn]`과 실행 파일 프롬프트.
  - 변환·설정 참조의 Python 호출.
  - `extensions` 훅.
- 제외:
  - `http`·`websocket`·`browser` 등 커스텀 타깃 provider 구현(범위 밖, 지도의 `custom-target-providers`). 레지스트리가 어떤 문자열을 어느 provider로 보내는지는 R-01에서 스크립트 계열만 다룬다.
  - 개별 어서션 핸들러의 내용(`javascript` 인라인 어서션 포함. 여기서는 스크립트 호출·결과 정규화 경계만 쓴다).
  - OpenTelemetry 계측 세부(`persistent_wrapper.py`의 `_traced_call`은 `PROMPTFOO_ENABLE_OTEL`이 켜졌을 때만 동작하며 호출 규칙을 바꾸지 않는다).
- 외부 의존·선행 계약:
  - 호출자(평가기)가 `context`(`vars`, `prompt`, `test`, `evaluationId` 등)를 만들어 준다. 이 스펙은 스크립트에 넘어가는 모양만 정의한다.
  - 외부 인터프리터(`python`, `ruby`, `go`)와 `go.mod`는 사용자가 준비한다.
  - 응답 캐시(`getCache`/`isCacheEnabled`)는 키·저장 규칙만 R-07에서 정의하고 저장소 구현은 범위 밖이다.
  - 선행 스펙은 없다.
- 소유 상태·부작용:
  - Python provider 인스턴스마다 워커 풀(자식 프로세스 N개)과 요청 큐를 소유한다. 수명은 평가 스코프(R-15)다.
  - 호출마다 `os.tmpdir()` 아래에 0700 디렉터리와 0600 JSON 파일을 만들고 호출 뒤 지운다(`createSecureTempDirectory`, `writeSecureTempFile`; Go는 `fs.mkdtemp`로 모듈 전체를 복사하고 지운다).
  - 캐시 쓰기.
  - 훅은 `suite`, `test`, `result` 중 정해진 필드만 바꾼다(R-28~R-31).

### 1.3 인터페이스와 데이터 의미 [필수]

타입은 중립 표현이다. `ctx`는 아래 "context" 항목의 객체다.

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| provider 지정 문자열 | `python:<path>[:fn]`, `ruby:<path>[:fn]`, `golang:<path>[:fn]`, `exec:<command line>`, `file://<path>[.py|.rb|.go][:fn]`, `file://<x>.js|cjs|mjs|ts|cts|mts` | R-01, R-02. `exec`만 `file://` 형태가 없다. |
| 함수 이름 규칙(provider) | `call_api(prompt, options, ctx)`, `call_embedding_api(prompt, options)`, `call_classification_api(prompt, options)` | `file://x.py:fn`처럼 이름을 주면 세 종류 모두 그 이름 하나를 부른다(R-03). Go는 `CallApi`만 된다(R-19). |
| provider 반환(Python/Ruby) | map. `call_api`는 `output`, 임베딩은 `embedding`, 분류는 `classification` 중 자기 속성 또는 `error` | 둘 다 없으면 예외(R-05). 선택 필드는 `ProviderResponse`(`tokenUsage`, `cost`, `latencyMs`, `logProbs`, `metadata`, `sessionId`, `guardrails`, `conversationEnded` 등, `src/contracts/providers.ts`). |
| options(스크립트 2번째 인자) | `ProviderOptions` 복사본 | `{...options, config: {...options.config, ...processedConfig}}`. `config.basePath`가 들어 있다. `config` 안의 `file://` 참조는 provider 초기화 때 내용으로 바뀐다(R-04). |
| context(3번째 인자, `call_api`만) | `CallApiContextParams`에서 `getCache`, `logger`, `filters`, `originalProvider`를 뺀 얕은 복사 | 남는 것은 `vars`, `prompt`, `test`, `repeatIndex`, `testIdx`, `evaluationId`, `testCaseId`, `traceparent`, `bustCache` 등(`src/evaluator.ts:1241-1290`). 임베딩·분류에는 context를 안 넘긴다(R-04). |
| 워커 요청 파일 | `request.json` = 인자 배열 JSON, `response.json` = `{"type":"result","data":…}` 또는 `{"type":"error","error":str,"traceback":str}` | UTF-8, `ensure_ascii=False`. 순환 참조는 `safeJsonStringify`가 버린다. |
| 워커 제어 프로토콜 | stdin: `CALL|<fn>|<req>|<resp>`, `SHUTDOWN`; stdout: `\nREADY`, `\nDONE|<resp>` | 줄 단위. 그 밖의 stdout 줄은 버려진다(R-10). |
| 일회성 요청 파일 | Python: `input.json`(인자 배열)·`output.json` = `{"type":"final_result","data":…}`; Ruby도 같은 모양 | R-17. |
| `exec:` 호출 | argv = (명령줄을 쪼갠 것) + `[prompt, JSON(options), JSON(context)]`; stdout → `{output}` | R-20. |
| 어서션 함수 | `get_assert(output, ctx)` (Python·Ruby 기본), JS는 export 함수 | `ctx` = `{prompt, vars, test, logProbs, provider, providerResponse, config?, metadata?, trace?}`. 반환: bool / number / `GradingResult` dict(또는 JSON 문자열). |
| 변수 생성 함수 | JS: `(varName, prompt, vars, provider)`, Python: `get_var(var_name, prompt, vars)`; 반환 `{output: string}` 또는 `{error}` | R-25. |
| 프롬프트 함수 | `fn({vars, provider: {id,label}, config})` → string \| `{prompt, config?}` \| object | R-26. |
| 훅 호출 규칙 | 함수 이름이 `beforeAll`·`beforeEach`·`afterEach`·`afterAll` 중 하나면 `(context, {hookName})`, 아니면 `(hookName, context)` | R-27. |
| 훅 컨텍스트 | beforeAll `{suite}`; beforeEach `{test}`; afterEach `{test, result}`; afterAll `{suite, results, prompts, evalId, config}` | `src/evaluatorHelpers.ts:540-640`. 반영되는 필드는 R-28~R-31. |
| 환경변수·설정 키 | `PROMPTFOO_PYTHON`, `PROMPTFOO_PYTHON_WORKERS`, `PROMPTFOO_PYTHON_DEBUG_ENABLED`, `PROMPTFOO_RUBY`, `REQUEST_TIMEOUT_MS`, `PROMPTFOO_EVAL_TIMEOUT_MS`; provider `config.pythonExecutable`, `workers`, `timeout`, `rubyExecutable`, `goExecutable` | R-08, R-16, R-13, R-19, R-17, R-18. |

### 1.4 행동 규칙과 남은 질문 [필수]

모든 행은 구현부를 읽은 것이고 실행하지 않았다. 따라서 검증 수준은 `코드 확인`, `추론`, `미확인`만 쓴다.

**A. 선택과 이름 규칙**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | provider 문자열이 스크립트 계열이다. | `exec:`, `python:`, `ruby:`, `golang:` 접두사 또는 `file://` + 확장자(`.py` / `.rb` / `.go`, 또는 `.py:` 처럼 함수 접미사가 붙은 형태)이면 해당 provider가 선택된다. `exec`는 확장자 규칙이 없다. 이 네 팩토리는 `providerMap`에서 JS 파일 팩토리보다 앞에 있다. JS 파일(`.js .cjs .mjs .ts .cts .mts`) 문자열은 `file://` 유무와 상관없이 JS 팩토리로 간다. | 코드 확인 |
| R-02 | Python·Ruby·Go provider 생성. | 접두사/`file://`를 떼고 `parsePathOrGlob(basePath, path)`로 파일과 함수 이름을 나눈다. 마지막 `:`가 인덱스 1보다 뒤에 있고 그 앞이 `.py`/`.go`/`.rb`/JS 확장자로 끝날 때만 뒤쪽을 함수 이름으로 본다. 경로는 상대 경로로 저장되고 호출 때 `resolve(basePath, scriptPath)`로 절대화한다. `id()`는 `options.id ?? "<lang>:<relpath>:<fn or default>"`이다(`exec`는 항상 `exec:<명령줄>`). | 코드 확인 |
| R-03 | 함수 이름 기본값. | provider는 호출 종류(`call_api`/`call_embedding_api`/`call_classification_api`)가 곧 함수 이름이다. `:fn`이 있으면 세 종류 모두 `fn`을 부르고 결과 검증 속성만 종류별로 다르다. 어서션 `get_assert`, 변수 `get_var`, 변환 `get_transform`, 설정 참조 `get_config`가 Python의 기본 이름이고 `:fn`으로 바꾼다(변수는 못 바꾼다, R-25). `Class.method`는 Python(`getattr(getattr(module, Class), method)`)과 Ruby(`Object.const_get(Class).public_send`)가 지원하고 Ruby 최상위 이름은 `send`라 private도 된다. | 코드 확인 |

**B. 공통 provider 결과 규칙(Python·Ruby)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-04 | `call_api` 호출 인자. | 인자는 `[prompt, options, context]`(C-02). 임베딩·분류는 `[prompt, options]`. context는 `sanitizeScriptContext`로 얕게 복사해 직렬화 불가 키 4개를 뺀 것이다(원본 객체는 건드리지 않는다, C-03). Python·Ruby는 첫 호출 전에 `config`의 `file://` 문자열을 파일 내용으로 바꾼다(`.json/.yaml` 파싱, JS는 함수면 호출, `.py`는 `get_config()` 실행, `.txt/.md`는 텍스트). | 코드 확인 |
| R-05 | 스크립트 반환값 검증. | 반환값이 객체가 아니거나, 종류별 속성(`output`/`embedding`/`classification`)도 `error`도 자기 속성으로 갖지 않으면 `The Python script \`fn\` function must return a dict with an own \`output\` or \`error\` property …, instead got: <JSON>`을 던진다(Ruby는 `Ruby`/`hash`). 상속 속성은 인정하지 않는다(C-02). | 코드 확인 |
| R-06 | 평가기가 provider 응답을 처리한다. | 응답에 `error`가 있으면 그 문자열로 ERROR 행(채점 안 함). `output`이 null/undefined면 `No output` ERROR 행. provider 호출이 예외를 던지면 스택과 함께 ERROR 행. 빈 문자열 `output`은 정상이라 어서션으로 간다. | 코드 확인 |
| R-07 | 캐시. | Python/Ruby 키: `<lang>:<scriptPath>:<fn or default>:<apiType>:<sha256(스크립트 파일 내용)>:<prompt>:<JSON(options)>:<JSON(context.vars)>`. `error`가 비어 있지 않으면 저장하지 않는다. 적중 시 `cached:true`로 바꾸고 `tokenUsage`가 있으면 `{cached: total, total, numRequests: 기존 ?? 1}`로 다시 쓴다. 새 결과는 `cached:false`로 표시하고 Python만 `tokenUsage.numRequests`가 비었으면 1로 채운다. Go 키에는 함수 이름이 없고 `error` 키가 있으면(`'error' in result`) 저장하지 않으며, 적중 시 `cached:true`만 붙는다. `exec:` 키는 `exec:<명령줄>:<명령줄에서 존재하는 파일들의 sha256>:<prompt>:<JSON(options)>`이고 존재하는 파일이 하나도 없으면 경고하고 캐시를 쓰지 않는다. | 코드 확인 |

**C. Python provider 워커 풀**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-08 | 워커 수 결정. | 우선순위: `config.workers` > `PROMPTFOO_PYTHON_WORKERS`(provider `env` 값 우선) > `-j`(`cliState.maxConcurrency`, 명시했을 때만) > 1. 1 미만은 경고 후 1. 8 초과는 메모리 경고만 한다. 전역 상태는 워커 사이에 공유되지 않는다(워커마다 import 1회). | 코드 확인 |
| R-09 | 첫 호출. | `PythonProvider.initialize()`가 한 번만 풀을 만든다(동시 호출은 같은 Promise를 공유). Python 실행 파일을 풀당 한 번 검증한 뒤 워커를 병렬로 띄우고 각 워커가 `READY`를 보낼 때까지 최대 30초 기다린다. import 중 스크립트가 죽으면 `Python worker exited before becoming ready (<exit>)`로 바로 실패한다. 초기화가 실패하면 풀 전체를 종료하고 provider는 초기화 상태를 되돌려 다음 호출이 재시도한다. 초기화 때는 함수가 있는지 확인하지 않는다(호출 때 확인). | 코드 확인 |
| R-10 | 워커 한 번 호출(C-04, C-05). | Node가 임시 디렉터리에 `request.json`·빈 `response.json`을 만들고 `CALL\|fn\|req\|resp`를 stdin에 쓴다. 워커는 `get_callable`로 함수를 찾고(async면 `asyncio.run`), 응답 파일을 쓰고 fsync하고 읽을 수 있는지 최대 3번 확인한 뒤 `\nDONE\|<resp>`를 출력한다. Node는 `DONE` 경로가 진행 중 요청의 응답 경로와 일치할 때만 완료로 본다. 응답 파일은 ENOENT면 1ms부터 두 배씩(최대 5초, 16회, 합계 약 18초) 재시도해 읽는다. `type:"error"`면 `Python error: <error>\n<traceback>`를 던진다. 사용자 코드의 `print`(stdout)는 제어 줄이 아니면 버려지고 stderr는 줄 단위로 로거에 간다(`Traceback`/`ERROR:` 등 접두사에 따라 error/warn/info/debug, 접두사 없으면 warn). | 코드 확인 |
| R-11 | 함수가 없다/함수가 예외를 던진다. | 함수 이름이 모듈에 없으면 `AttributeError`로 "사용 가능한 함수 목록 / 기대 이름 3개 / 비슷한 이름 제안"을 담은 메시지가 `type:"error"`로 돌아온다. 사용자 예외도 `type:"error"`(str(e)+traceback)이다. 두 경우 워커는 죽지 않고 다음 요청을 받는다. | 코드 확인 |
| R-12 | 디스패치(C-06). | 풀은 준비됐고 바쁘지 않은 첫 워커에 즉시 보낸다. 없으면 요청을 큐 끝에 넣고, 워커가 풀리거나 준비될 때마다 큐 앞에서부터 가능한 만큼 보낸다(FIFO). 워커 하나는 동시에 한 요청만 받는다(`Worker is busy`). 풀이 초기화되지 않았으면 `Worker pool not initialized`. | 코드 확인 |
| R-13 | 타임아웃과 중단. | 호출 한 번의 제한은 `config.timeout`(ms), 없으면 `REQUEST_TIMEOUT_MS`, 없으면 300000. 시간이 지나면 `Python worker timed out after <ms>ms`를 던지고, 그 프로세스를 멈춘 뒤(POSIX: stdin 닫기 + SIGINT, 2초 뒤 SIGKILL; Windows: `taskkill /t /f`) 새 프로세스로 교체한다(전역 상태 소실). 요청 파일들은 프로세스가 완전히 끝난 뒤에 지운다. 평가 단계 타임아웃(`evaluateOptions.timeoutMs`, `PROMPTFOO_EVAL_TIMEOUT_MS`)의 AbortSignal은 `callApi(prompt, ctx, options)`의 세 번째 인자로 오지만 Python·Ruby·Go `callApi`는 받지 않으므로 호출을 취소하지 못한다. 평가 단계 타임아웃이 provider 타임아웃보다 먼저 지나면 평가기는 그 칸을 시간 초과 ERROR 행으로 저장하고 다음으로 넘어가지만([eval-run](./eval-run.md) R-35) Python 호출은 계속된다. 워커는 `busy`로 남아, 그 호출이 끝나 응답 파일 읽기까지 마칠 때까지(또는 위 provider 타임아웃이 지나 프로세스 교체가 끝날 때까지) 다른 요청을 받지 않는다. 끝나면 `call()`이 `busy`를 풀고 `.finally(processQueue)`가 큐 맨 앞 요청을 그 워커에 보낸다(교체한 경우는 새 프로세스가 `READY`를 보낸 뒤 `onStateChange`로 큐를 처리한다). 큐에 들어간 요청에는 취소 신호가 없어 그 칸이 이미 시간 초과로 저장됐어도 나중에 그대로 실행되고, 캐시가 켜져 있고 `error`가 없으면 그 결과는 캐시에 저장되지만 행에는 반영되지 않는다. `withProvider`의 `activeCalls`가 0이 될 때까지 풀 종료도 미뤄진다(R-15). | 코드 확인 |
| R-14 | 워커 비정상 종료. | 진행 중 요청은 `Worker crashed (exit code N \| signal S)`로 실패하고 워커를 다시 띄운다. 요청이 한 번 완료(`DONE` 수락)될 때마다 연속 실패 횟수가 0이 된다. 충돌 또는 재시작 실패가 연달아 3번이면 그 워커는 영구 사망 처리되고(`Worker crashed and could not be restarted`), 풀의 모든 워커가 죽으면 큐의 요청이 `All N Python worker(s) for <script> crashed and could not be restarted …`로 실패한다. 재시작 중에는 요청이 큐에서 기다린다. | 코드 확인 |
| R-15 | 평가 종료와 풀 종료. | Python provider는 초기화 때 `providerRegistry.register(this)`로 자신을 등록한다. 등록 자원은 활성 평가 스코프(`withEvaluation`)가 점유하고, 스코프가 끝나 점유자가 없고 그 provider의 진행 중 호출(`activeCalls`)도 없으면 `maybeReleaseResource`가 `shutdown()`을 부른다. 진행 중 호출이 있으면 풀을 닫지 않고, 그 호출이 settle된 뒤 `withProvider`의 `finally`가 다시 시도한다. SIGINT/SIGTERM/`beforeExit`에서도 모두 닫는다. 워커 종료는 `SHUTDOWN` 전송 → 5초 대기 → SIGINT → 2초 뒤 SIGKILL, 큐에 남은 요청은 `Worker pool shutting down`으로 거부된다. | 코드 확인 |
| R-16 | Python 실행 파일. | `config.pythonExecutable` > provider `env.PROMPTFOO_PYTHON` > 프로세스 `PROMPTFOO_PYTHON` > 기본 `python`(C-07). 후보는 `--version` 출력이 `Python`으로 시작해야 한다. 명시한 경로가 틀리면 `Python 3 not found. Tried "<path>" …`로 실패하고, 명시하지 않은 기본값이면 `python3`/`python`(Windows는 `where python`, `py`) 순으로 `sys.executable`을 찾아 대체한다. | 코드 확인 |

**D. 일회성 브리지(Ruby provider, Python 비-provider 호출처)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-17 | Python 어서션·변수·변환·설정 참조·프롬프트 함수·확장 훅(`runPython`, C-08). | 호출마다 새 `python wrapper.py <절대경로> <fn> input.json output.json` 프로세스를 띄운다(모듈을 매번 import, 워커 풀 없음). 인자는 JSON 배열이고 결과는 `{"type":"final_result","data":…}`여야 한다. **타임아웃이 없다**(중단은 `abortSignal`만: SIGTERM, 1초 뒤 SIGKILL). 종료 코드가 0이 아니면 오류이고, 출력 JSON이 깨졌거나 `final_result`가 아니면 오류이며, 모두 `Error running Python script: …`로 감싸 던진다. 스크립트의 stdout은 debug 로그로 간다. `PROMPTFOO_PYTHON_DEBUG_ENABLED`가 true면 stdio를 상속해 pdb를 쓸 수 있다. | 코드 확인 |
| R-18 | Ruby provider·어서션. | provider: `call_api` 호출마다 `ruby wrapper.rb <절대경로> <fn> input.json output.json`(R-17와 같은 파일 규약, `JSON.generate`)을 `execFile`로 실행한다. 스크립트는 `load`되고 최상위 함수는 `send`로, `Class.method`는 `public_send`로 부른다. Ruby 실행 파일은 `config.rubyExecutable` > `PROMPTFOO_RUBY` > `ruby`이고 같은 방식으로 검증한다. 타임아웃이 없고, 중단은 임베딩 호출의 `abortSignal`만 지원한다(SIGTERM 후 SIGKILL). 결과 검증·캐시는 R-05, R-07. 인라인 `ruby` 어서션은 코드를 임시 `script.rb`에 `def main(output, context)`로 감싸 같은 경로로 실행한다. | 코드 확인 |

**E. Go provider와 `exec:` provider, JS provider**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-19 | Go provider 호출(C-09). | 호출마다 (1) 스크립트에서 위로 `go.mod`를 찾는다(없으면 `Could not find go.mod file in any parent directory`). (2) 모듈 루트 전체를 임시 디렉터리에 복사한다. (3) 스크립트 디렉터리에서 `go list -json .`을 실행한다. (4) 패키지가 `main`이면 `wrapper.go`와 스크립트 파일을 같이, 아니면 `provider.go`(`var CallApi = provider.CallApi`)를 만들어 `wrapper.go`와 같이 `go build`한다. (5) 바이너리를 `[<임시 스크립트 경로>, <fn>, <JSON 인자>]`로 실행한다. (6) stdout을 `JSON.parse`한 객체를 그대로 반환한다. 래퍼는 함수 이름이 `call_api`/`CallApi`일 때만 `CallApi(string, map, map) (map, error)`를 부르고, 다른 이름은 `Unknown function: <fn>`을 stdout에 쓰고 종료 코드 1이다. Go `error`를 돌려주면 `Error calling function: …`를 stdout에 쓰고 종료 코드 1이다. 임베딩·분류도 같은 래퍼를 거치며 인자가 2개라 래퍼가 `args[2]`를 읽다 실패한다(실질적으로 `call_api`만 동작). 결과 형태 검증(R-05)이 없고 타임아웃이 없다. 임시 디렉터리는 항상 지운다. 오류 처리: 빌드·실행 어느 `execFile`이든 실패(종료 코드 0이 아닌 경우 포함)하면 `catch`가 오류 객체의 `message`만 써서 `Error running Golang script: <message>`를 던진다(`error.stdout`·`error.stderr` 필드는 읽지 않는다). 성공한 실행의 stderr만 `Golang script stderr: …`로 로그한다. 따라서 Go `error`·`Unknown function` 문구(stdout에 쓴다)가 던져지는 메시지에 들어가는지는 Node가 그 `message`에 무엇을 넣는지에 달려 있다(확인 한계 참조). | 코드 확인(래퍼·빌드 절차·오류 메시지 구성), 추론(임베딩 호출이 `args[2]` 접근으로 실패한다는 것)
| R-20 | `exec:` provider 호출(C-10). | 명령줄을 `[^\s"']+|"…"|'…'` 규칙으로 쪼개 첫 토큰을 명령, 나머지를 앞쪽 인자로 하고 `[prompt, JSON(options), JSON(context)]`를 뒤에 붙여 `execFile`(셸 없음)로 실행한다. context는 `getCache`·`logger`·`filters`·`originalProvider`를 **전달받은 객체에서 직접 삭제**한 뒤 직렬화한다(R-04와 달리 호출자 객체가 바뀐다). `cwd`는 `config.basePath`가 있을 때만 설정한다. stdin은 즉시 닫는다. 종료 코드가 0이 아니면 그 오류로 reject. 성공하면 stdout·stderr의 ANSI 이스케이프를 지우고 trim하며, stderr만 있고 stdout이 비면 stderr 문자열로 reject, 아니면 `{output: <stdout>}`을 돌려준다(JSON을 파싱하지 않는다). 타임아웃이 없다. 캐시 키의 파일 존재 확인은 `cwd`가 아니라 프로세스 현재 디렉터리 기준이다. | 코드 확인 |
| R-21 | JS provider(`file://x.js` 등). | `importModule(path)`로 모듈을 불러 `default.default \|\| default \|\| 모듈` 값을 `new Cls({...providerOptions, id: providerOptions.id ?? 원래 경로})`로 만든다. 같은 프로세스에서 실행되며 `:fn` 접미사 문법은 이 경로에 없다. 인스턴스는 `id()`와 `callApi(prompt, ctx, options)`를 가진 `ApiProvider`여야 한다(타입 계약, 클래스 형태 검사 없음). | 코드 확인(로더), 추론(클래스 계약은 `ApiProvider` 인터페이스에서) |

**F. 어서션·변수·프롬프트**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | 어서션 `value: file://path[:fn]`. | 첫 `:`을 기준으로 경로와 함수를 나눈다. JS: `importModule(path, fn)` 후 `fn` > 모듈 자체 > `default` 순으로 함수를 찾아 `(output, ctx)`로 호출(없으면 `Assertion malformed`). `.py`: `runPython(path, fn ?? "get_assert", [output, ctx])`. `.rb`: `runRuby`로 같은 규칙. `.go` 등은 스크립트로 실행되지 않는다(`.json/.yaml/.yml/.txt`만 파일 내용으로 읽고 그 외는 `Unsupported file type`). `.py`·`.rb` 실행이 예외를 던지면 어서션은 예외가 아니라 `{pass:false, score:0, reason:<메시지>}`가 된다. 결과는 `valueFromScript`로 보관되고, 어서션 타입이 `javascript`/`python`/`ruby`면 그대로 채점 결과가 되고, 다른 타입이면 비교 대상 값으로 쓰이며 함수·boolean·`pass` 있는 객체를 돌려주면 오류다. 중복 표시: 이 규칙은 [assertion-family](./assertion-family.md) R-08과 겹친다(여기서는 스크립트 호출 경계 중심). | 코드 확인 |
| R-23 | 인라인 `python`/`ruby` 어서션(C-11). | `value` 문자열을 Nunjucks로 렌더한 뒤 한 줄이면 `return <value>`, 여러 줄이면 첫 들여쓰기 스타일로 줄마다 들여써 `def main(output, context):`(Ruby는 `def main(output, context) … end`) 본문에 넣고 임시 파일에서 `main`을 `[output, ctx]`로 호출한다. 예외는 `Python code execution failed: <메시지>` / `Ruby code execution failed: …`의 `pass:false` 결과가 된다. 중복 표시: 이 규칙은 [assertion-family](./assertion-family.md) R-37과 겹친다. | 코드 확인 |
| R-24 | 스크립트 어서션 반환 정규화(C-12). | `true`/`"true"` → 통과(점수 1), `false`/`"false"` → 실패(0). 숫자(또는 숫자 문자열)는 `assertion.threshold`가 없으면 `>0`, 있으면 `>= threshold`로 통과 판정하고 점수는 그 숫자. `{`로 시작하는 문자열은 JSON으로 파싱해 객체로 처리. 객체는 `pass_`→`pass`, `named_scores`→`namedScores`, `named_score_weights`, `component_results`, `tokens_used`의 snake_case를 허용(이미 camelCase가 있으면 유지)하고 유한 숫자만 허용하는 `GradingResult` 검증을 거친다. 객체 점수가 `threshold`보다 작으면 `pass=false`와 `<Lang> score S is less than threshold T: <reason>`으로 바뀐다. `not-` 접두사(inverse)는 최종 pass를 뒤집는다. 어느 모양도 아니면 `<Lang> assertion must return a boolean, number, or {pass, score, reason} object …` 오류. 어서션 반환 정규화는 [assertion-family](./assertion-family.md) R-35~R-39를 따른다. 이 행은 R-38(Python·Ruby 반환 정규화)·R-39와 중복이며, 값이 다르면 assertion-family 쪽이 기준이다. | 코드 확인 |
| R-25 | 변수 값이 `file://x`(렌더링 전 vars). | JS(`isJavascriptFile`): 기본 export 함수를 `(varName, basePrompt, vars, provider)`로 호출해 `{output: string}`이어야 하고 `error`가 있으면 `Error running <path>: …`. Python `.py`: `runPython(path, "get_var", [varName, basePrompt, vars])`, 결과 `{output, error}`에서 `output`은 문자열이어야 하고 trim해서 변수에 넣는다(`:fn` 접미사는 이 경로에서 지원하지 않는다: 접미사를 붙이면 파일 경로 자체가 달라진다). `.rb`·`.go` 등은 실행되지 않고 파일 내용이 텍스트(trim)로 들어간다. | 코드 확인 |
| R-26 | 프롬프트 함수. | JS `file://p.js[:fn]`: `importModule(path, fn)` 함수를 `({vars, provider:{id,label}, config})`로 호출. Python `file://p.py:fn`: `runPython(path, fn, [그 컨텍스트])`. 함수 이름이 없는 `file://p.py`는 **레거시**라 파일 전체를 `PythonShell.run`으로 실행하고 컨텍스트 JSON을 argv로 주며 stdout 줄을 `\n`으로 이은 것이 프롬프트가 된다(Python 실행 파일은 `PROMPTFOO_PYTHON`, 기본 `python`). `exec:<명령>`, 확장자 `.sh .bash .exe .bat .cmd .ps1 .rb .pl`, 실행 비트가 있는 파일은 실행 파일 프롬프트라 컨텍스트 JSON 한 개를 마지막 인자로 주고(`.rb`도 Ruby 브리지가 아니라 직접 실행) stdout을 trim해 쓰며 `config.timeout`(기본 60000ms) 제한이 있고, 명령줄에 존재하는 파일이 있으면 `exec-prompt:<명령줄>:<파일 해시들>:<JSON(컨텍스트)>` 키로 stdout을 캐시한다. 반환값: 문자열은 그대로, `prompt` 키가 있는 객체는 `prompt`(문자열 아니면 JSON 문자열)를 쓰고 `config`는 프롬프트 설정에 얕게 병합, 다른 객체는 JSON 문자열, 그 밖은 `Prompt function must return a string or object` 오류. `.go` 프롬프트는 실행되지 않는다. | 코드 확인 |

**G. 확장 훅**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-27 | `extensions` 항목 `file://<path>:<fn>`과 호출 규칙(C-13, C-14). | 스키마(`TestSuiteSchema`)는 `file://`로 시작하고 `파일:함수` 두 부분이며 `.py` 또는 JS 확장자여야 한다고 하지만 어긴 설정은 `eval`에서 경고만 하고 계속 진행한다. `runExtensionHook`은 항목을 순서대로 처리한다. 함수 이름이 정확히 `beforeAll`/`beforeEach`/`afterEach`/`afterAll`이면 그 훅에서만 실행하고 `(context, {hookName})`으로 부른다. 다른 이름이거나 이름이 없으면 모든 훅에서 실행하고 `(hookName, context)`로 부른다(`before_all` 같은 snake_case는 "다른 이름"이다). 앞 항목이 반환한 컨텍스트가 다음 항목의 입력이다. 함수 해석은 `transform()`과 같다: JS는 `importModule` 후 이름이 모듈의 own 함수 속성이면 그것, 모듈 자체가 함수면 그것, 아니면 `default`; Python은 `runPython(path, fn ?? "get_transform", [인자1, 인자2])`(R-17, 호출마다 새 프로세스). CLI `-x/--extension` 항목이 설정 파일 항목보다 앞에 온다. | 코드 확인 |
| R-28 | `beforeAll`. | 평가기가 `testSuite`를 받은 직후, 생성 프롬프트·평가 단계 펼치기보다 먼저, `{suite}`로 한 번 호출한다. `defaultTest.assert`가 없으면 `[]`을 채워 주고, `providerPromptMap`이 없으면 각 provider의 id·label로 프롬프트 선택자를 채운 맵을 넣어 준다. 훅이 truthy를 반환하면 `suite`의 `prompts`, `providerPromptMap`, `tests`, `scenarios`, `defaultTest`, `nunjucksFilters`, `derivedMetrics`, `redteam`만 반환값으로 교체된다(`providers` 등은 원래 값). Python 훅은 JSON을 거치므로 `prompt.function`이 사라지는데, 평가기가 `label`이 같고 `raw`가 같으면 원래 함수를 다시 붙인다(라벨이 중복이면 복구하지 않고 경고). | 코드 확인 |
| R-29 | `beforeEach`. | 평가 단계 하나(provider × prompt × test × repeat)마다 provider 호출 전에 `{test}`로 부른다. 반환이 truthy면 `{test: ret.test}`로 교체되고(반환 객체에 `test`가 없으면 `undefined`가 되어 이후가 깨진다) 그 `test`가 그 단계 실행에 쓰인다. 반환이 falsy면 입력 `test` 객체가 그대로다(JS 훅이 제자리에서 바꾼 것은 반영된다, Python은 JSON 사본이라 반환해야 반영된다). 이 훅의 실행 시간은 평가 단계 타임아웃 시계 안에 든다. 단계 처리 전체(`processEvalStep` → `runEvalStepAfterBeforeEach` → `beforeEach` 훅 → `runEvalInternal`)가 `Promise.race`로 타이머와 경쟁하고, 타이머는 단계 처리를 시작한 같은 동기 구간에서 설정되므로 `timeoutMs`는 훅·렌더·provider 호출·어서션을 합친 시간이다([eval-run](./eval-run.md) R-35, R-41). 훅 호출에는 취소 신호가 없어 시간 초과 뒤에도 훅은 끝까지 돈다(Python 훅이면 일회성 프로세스가 끝날 때까지). 훅이 끝나면 `runEvalInternal`은 이미 abort된 신호를 들고 계속 가다가 provider 호출 진입점(`withProvider`의 `signal.throwIfAborted()`)에서 던지므로 provider는 호출되지 않고, 그 칸은 이미 시간 초과 ERROR 행으로 저장되어 있다. 훅이 바꾼 `test`는 `finally`에서 원래 단계 객체로 복사된다. | 코드 확인 |
| R-30 | `afterEach`. | 행이 만들어지고 채점된 뒤 저장 직전에 `{test, result}`로 부른다(`result`는 `namedScores`·`metadata`·`response.metadata`를 복사한 사본). 반환 `result`에서 반영되는 것은 `namedScores`(유한한 숫자만, 기존에 얕게 병합), `metadata`(얕게 병합), `response.metadata`(얕게 병합)뿐이다. `success`·`score`·`response.output` 등은 바뀌지 않는다. 반환이 없으면 변경 없음. | 코드 확인 |
| R-31 | `afterAll`. | 모든 결과가 저장되고 프롬프트 지표가 정리된 뒤 `{suite, results, prompts, evalId, config}`로 한 번 부른다. 반환값은 무시한다. | 코드 확인 |
| R-32 | 훅 오류. | 훅 함수가 던지면 `Extension hook "<hook>" failed for <extension>: <msg>`로 감싼다(`cause` 유지). `afterEach`만 평가기가 잡아서 오류 로그를 남기고 훅 수정 없이 행을 저장한다. `beforeAll`·`beforeEach`·`afterAll`은 잡는 곳이 없어 `evaluate()`가 그 오류로 reject된다(평가 스코프 정리 후 재던짐). 한 평가 단계의 훅 실패는 그 단계만 ERROR로 만들지 않는다. | 코드 확인 |

**H. 환경**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-33 | 모든 자식 프로세스(Python/Ruby/Go/exec/실행 프롬프트)의 환경. | `getProcessEnv()` = `process.env` + 설정/`--env-file`로 불러온 "file" 계층 값. 설정 파일의 `env:` 블록(제품 내부의 provider/suite 계층)은 자식 프로세스 환경에 넣지 않는다(코드 주석: 템플릿·서브프로세스 계층에서 분리). 즉 provider·suite `env:`에만 둔 API 키는 스크립트에서 `os.environ`으로 보이지 않고, `options.env` 인자로만 전달된다. | 코드 확인(`getProcessEnv`와 호출처), 추론(`options.env`가 스크립트 인자에 들어 있다는 점은 `ProviderOptions`가 `env`를 갖는 것에서) |

- 불변식:
  - 한 Python 워커는 한 시점에 한 요청만 처리한다. 응답은 `DONE` 경로가 진행 중 요청의 경로와 같을 때만 수락된다.
  - 스크립트 인자와 결과는 JSON으로 표현 가능한 값만 지난다(직렬화에서 함수 속성이 사라지고 순환은 버려진다). 이 때문에 Python/Ruby/Go/exec 스크립트와 Python 훅은 `context.logger`·`getCache`·`filters`·`originalProvider`를 쓸 수 없다.
  - 일회성 브리지(R-17, R-18)와 Go(R-19)는 호출 사이에 상태를 공유하지 않고, Python provider만 워커 프로세스 안에서 모듈 전역 상태를 유지한다.
- 미결정: 없음. (R-13, R-19, R-29의 이전 질문은 코드로 확정해 각 행에 반영했다. R-19에서 남는 Node 동작 의존은 확인 한계.)
- 확인 한계:
  - 실행하지 않았다. Python 3·Ruby·Go 설치와 실제 프로세스 동작, `python-shell`의 줄 분리·종료 이벤트 순서, Windows 경로는 코드 읽기로만 확인했다.
  - R-19: Node `execFile`(`util.promisify`)이 실패 시 만드는 오류 객체의 `message`에 stdout이 들어가는지는 Node 동작이라 확인하지 못했다. 코드는 `message`만 쓰고 `stdout`/`stderr` 필드는 읽지 않는다. Node 문서상 `message`는 `Command failed: <명령>\n<stderr>` 꼴로 알려져 있어 stdout은 빠진다고 추정하지만 `미확인`이다. 그렇다면 Go가 stdout에 쓴 `error` 문구는 사용자에게 안 보이고 종료 코드 1과 명령 문자열만 보인다.
  - `execFile`의 `maxBuffer` 기본값(Node 문서상 1 MiB)은 외부 동작이라 `미확인`이고, `exec:` provider·Ruby·Go 모두 이 옵션을 지정하지 않는다. 큰 출력이 잘리거나 오류가 날 수 있다.
  - `site/docs` 중 대조한 부분(python.md의 워커·타임아웃·크래시 절, reference.md의 훅 절, custom-script.md)은 구현과 일치했다. go.md, ruby.md의 나머지 절과 python.md의 예제 절은 대조하지 않았다. 문서에 없고 구현에만 있는 규칙(R-08의 `-j` 연동, R-09의 30초 준비 제한)은 구현을 따랐다.

### 1.5 필수 코드 참조 [필수]

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/providers/scriptBasedProvider.ts:13-55` `createScriptBasedProviderFactory` | 접두사·`file://`+확장자 매칭, 경로 추출, 클라우드 설정일 때의 경로 규칙 | R-01, R-02 |
| C-02 | `src/providers/scriptResult.ts:5-44`, `:73-102` | 호출 종류별 필드 이름, 인자 배열 모양, 오류 판정, 반환값 검증 메시지 | R-04, R-05, R-07 |
| C-03 | `src/providers/scriptContext.ts:15-57` | 직렬화 불가 키 목록, 얕은 복사 | R-04 |
| C-04 | `src/python/persistent_wrapper.py:93-178`, `:324-478` | 모듈 로드(`sys.path` 삽입), `Class.method`, 함수 없음 메시지, 제어 프로토콜, 응답 파일 쓰기·검증, 오류 응답 | R-10, R-11 |
| C-05 | `src/python/worker.ts:255-401`, `:403-420` `call`/`executeCall`/`createTimeout` | 요청 파일·응답 파일 규약, 백오프 읽기, 타임아웃 시 교체 | R-10, R-13 |
| C-06 | `src/python/workerPool.ts:27-142`, `:148-169` | 초기화, 가용 워커 선택, 큐 FIFO, 전원 사망 처리, 종료 | R-09, R-12, R-14, R-15 |
| C-07 | `src/python/pythonUtils.ts:29-34`, `:173-209` | Python 실행 파일 우선순위와 검증·대체 탐색 | R-16 |
| C-08 | `src/python/wrapper.py:9-43`, `src/python/pythonUtils.ts:246-432` `runPython` | 일회성 Python 호출 규약과 오류 처리 | R-17 |
| C-09 | `src/golang/wrapper.go:13-63`, `src/providers/golangCompletion.ts:70-226` | Go 래퍼 인자·함수 이름 제한, 빌드·실행 절차 | R-19 |
| C-10 | `src/providers/scriptCompletion.ts:24-34`, `:52-133` | 명령줄 분리 정규식, argv 구성, 출력·오류 처리, 캐시 키 | R-20 |
| C-11 | `src/assertions/scriptBody.ts:1-18`, `src/assertions/python.ts:18-29` | 인라인 코드 감싸기 | R-23 |
| C-12 | `src/assertions/scriptResultNormalization.ts:138-274`, `src/util/caseMapping.ts:13-45` | 반환값 정규화, snake_case 매핑, threshold·inverse | R-24 |
| C-13 | `src/evaluatorHelpers.ts:643-658`, `:756-897` | 훅 이름 판별, 호출 규약, 반환 병합 | R-27~R-31 |
| C-14 | `src/util/transform.ts:61-121`, `:237-311` | 확장 함수(JS/Python) 해석과 호출, 오류 래핑 | R-27 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출(원본 테스트는 열지 않았고, 실행도 하지 않았다). 아래 기대값은 코드 읽기에서 나온 값이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01~R-03, R-04, R-05, R-10 | `providers: [file://p.py]`, `p.py`에 `def call_api(prompt, options, context): return {"output": "hi"}`, `workers`·`-j` 없음 | 워커 1개가 뜨고 `p.py`를 1회 import. 결과 `output:"hi"`, `cached:false`, 인자는 `[prompt, options, context]`이고 context에 `logger`·`getCache`·`filters`·`originalProvider` 키가 없다. |
| T-02 | R-03, R-05 | `file://p.py:gen`, 임베딩 호출 | `gen(prompt, options)` 호출(context 없음). 반환에 `embedding`이 없고 `error`도 없으면 `…must return a dict with an own \`embedding\` or \`error\` property` 오류. |
| T-03 | R-05, R-06 | `call_api`가 `{"foo": 1}` 반환 | 오류 메시지에 `instead got: {"foo":1}`가 포함되어 던져지고 행은 ERROR. |
| T-04 | R-06, R-07 | `call_api`가 `{"error": "boom"}` 반환 | 행은 ERROR `boom`, 캐시에 저장되지 않는다. |
| T-05 | R-11 | `call_api`가 `ValueError("x")`를 던짐 → 다음 요청 | 첫 요청은 `Python error: x\n<traceback>`. 같은 워커 프로세스가 다음 요청을 처리하고 모듈 전역 변수는 유지된다. |
| T-06 | R-13 | `config.timeout: 1000`, `call_api`가 5초 sleep, 모듈 전역 `n`을 증가 | `Python worker timed out after 1000ms`. 프로세스가 교체되어 다음 호출에서 `n`이 초기값으로 돌아간다. |
| T-07 | R-14 | `workers:1`, 호출 중 `os._exit(1)`이 연속 3번 | 처음 두 번은 `Worker crashed (exit code 1)` 후 재시작. 세 번째 뒤 워커는 사망, 이후 요청은 `All 1 Python worker(s) for <script> crashed and could not be restarted …`. 중간에 호출 하나가 정상 완료되면 횟수는 0으로 돌아간다. |
| T-08 | R-08, R-12 | `workers:3`, 동시 호출 5개(각 1초) | 3개가 즉시 병렬 실행, 나머지 2개는 큐에서 FIFO로 대기. 각 워커의 모듈 전역 상태는 서로 보이지 않는다. |
| T-09 | R-20 | `exec: python chain.py` | argv = `["chain.py", prompt, options JSON, context JSON]`. stdout `"  ok\n"` → `{output:"ok"}`. stdout 비고 stderr `"warn"` → reject `Error("warn")`. 종료 코드 1 → reject. |
| T-10 | R-19 | `file://p.go:Other` | 래퍼가 `Unknown function: Other`를 출력하고 종료 코드 1 → `Error running Golang script: …`. `file://p.go`의 `call_api`/`CallApi`는 정상. |
| T-11 | R-22, R-24 | `file://g.py` 어서션, `get_assert`가 `{"pass_": True, "score": 0.7, "reason": "ok", "named_scores": {"a": 1}}`, `threshold: 0.8` | `pass:false`, `reason:"Python score 0.7 is less than threshold 0.8: ok"`, `namedScores:{a:1}`. `threshold` 없으면 `pass:true`. |
| T-12 | R-22 | 같은 어서션인데 `g.py` 안에서 예외 발생 | 예외가 아니라 `{pass:false, score:0, reason:<오류 메시지>}`. |
| T-13 | R-25 | `vars: {x: file://gen.py}`, `get_var`가 `{"output": " v\n"}` 반환. 같은 방식의 `file://gen.rb` | `x === "v"`. `.rb`는 실행되지 않고 파일 내용이 `x`에 들어간다. |
| T-14 | R-27 | `extensions: [file://h.js:beforeEach, file://h.js:handler]` | `beforeEach` 때 첫 항목은 `(context, {hookName:'beforeEach'})`, 둘째는 `(hookName, context)`로 호출. 다른 세 훅에서는 첫 항목은 건너뛰고 둘째만 호출. |
| T-15 | R-28, R-29 | Python 훅이 `beforeAll`에서 `context["suite"]["tests"].append(...)`만 하고 반환하지 않음 / `return context` | 반환하지 않으면 변경이 없고, 반환하면 `tests`가 교체된다. JS 훅은 제자리 변경이 반환 없이도 반영된다. |
| T-16 | R-30 | `afterEach`가 `{"result": {"namedScores": {"cost_usd": 0.3, "bad": null}, "metadata": {"k": 1}}}` 반환 | `namedScores`에 `cost_usd`만 병합(유한 숫자만), `metadata.k = 1` 병합, `success`·`score`·`response.output`은 그대로. |
| T-17 | R-32 | `beforeEach`가 예외 / `afterEach`가 예외 | 전자는 `Extension hook "beforeEach" failed for …`로 `evaluate()`가 reject. 후자는 오류 로그만 남기고 행은 훅 수정 없이 저장. |
| T-18 | R-13 | `workers:1`, `PROMPTFOO_EVAL_TIMEOUT_MS=1000`, `config.timeout` 기본, `call_api`가 5초 sleep. 칸 2개를 동시에 시작 | 두 칸 모두 약 1초에 시간 초과 ERROR 행으로 저장된다. 첫 호출은 5초에 끝나고(결과는 캐시에만 저장) 그 뒤에야 둘째 요청이 워커에 전달되어 5초 더 실행된다. 둘째 요청은 시간 초과로 취소되지 않는다. |
| T-19 | R-29 | `PROMPTFOO_EVAL_TIMEOUT_MS=1000`, `beforeEach` 훅이 3초 걸림 | 1초에 시간 초과 ERROR 행이 저장된다. 훅은 3초까지 계속 돌고, 끝난 뒤 provider는 호출되지 않는다. |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]

문서(`site/docs`)와 구현이 다른 점은 아래 "차이" 열에 쓴다. 문서 쪽에서 구현과 어긋나는 것을 찾지는 못했고, 문서가 말하지 않는 구현 규칙만 확인했다.

| R-ID / T-ID | 근거 (repo@dfe2d45 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `src/providers/registry.ts:432-435`, `:1685-1704`, `:2040-2063`(패밀리 우선), C-01 | 팩토리 `test` 직접 읽기. |
| R-02 | `src/providers/pythonCompletion.ts:70-83`, `rubyCompletion.ts:66-79`, `golangCompletion.ts:40-57`, `scriptCompletion.ts:58-60`, `src/util/file.ts:369-420` `parsePathOrGlob`, `src/providers/index.ts:156-160`(`basePath`를 config에 주입) | 코드 읽기. |
| R-03 | `pythonCompletion.ts:285`, `scriptResult.ts`, `persistent_wrapper.py:111-120`, `wrapper.py:21-25`, `wrapper.rb:23-30`, `assertions/index.ts:507,525`, `evaluatorHelpers.ts:283`, `util/transform.ts:94-102`, `util/fileReference.ts:41-47` | 기본 이름 값 직접 확인. Python 일회성 `Class.method`는 점 1개만(`split(".")`)이다. |
| R-04 | C-02, C-03, `pythonCompletion.ts:267-279`, `rubyCompletion.ts:168-180`, `src/util/fileReference.ts:52-108`, 평가기 context 구성 `src/evaluator.ts:1241-1290` | 코드 읽기. `bustCache` 등 선택 키는 `cacheEnabled`가 꺼진 경우에만 붙는다. |
| R-05 | C-02 `scriptResult.ts:73-102` | 코드 읽기. |
| R-06 | `src/evaluator.ts:1493-1510`, `:2005-2025` | 코드 읽기. `output === ""`는 통과한다. |
| R-07 | `pythonCompletion.ts:239-305`, `rubyCompletion.ts:139-209`, `golangCompletion.ts:81-96,208-213`, `scriptCompletion.ts:63-85,123-127`, `scriptResult.ts:46-71` | 코드 읽기. `exec:`의 파일 존재 확인은 `fs.existsSync(cleanPart)`로 프로세스 cwd 기준이다. |
| R-08 | C-06, `pythonCompletion.ts:174-217` | 코드 읽기. 문서의 `workers`·`PROMPTFOO_PYTHON_WORKERS` 설명과 같고 `-j` 연동은 문서에 없다. |
| R-09 | `pythonCompletion.ts:94-164`, `worker.ts:81-245`, C-06 | 코드 읽기. |
| R-10 | C-04, C-05, `src/python/stderr.ts` | 코드 읽기. 백오프 합계(약 18초)는 코드 주석의 계산. |
| R-11 | `persistent_wrapper.py:111-170,376-478` | 코드 읽기. |
| R-12 | `workerPool.ts:91-142` | 코드 읽기. |
| R-13 | `worker.ts:255-300,403-420,434-487`, `pythonCompletion.ts:308-313`(2번 인자만 받음), `evaluator.ts:4507-4577`(단계 타임아웃), `workerPool.ts:91-142`, `worker.ts:255-300`, `providerRegistry.ts:113-160`(`withProvider`), `pythonCompletion.ts:228-306`(호출이 끝나면 캐시 저장) | 코드 읽기. 문서 "timeout 시 워커 재시작"과 일치. 단계 타임아웃·큐 상호작용은 문서에 없고 구현을 따랐다. 큐 요청에 취소 신호가 없는 것은 `QueuedRequest` 필드(`functionName`,`args`,`resolve`,`reject`)로 확인. |
| R-14 | `worker.ts:496-557` | 코드 읽기. 문서 "Crashes" 절과 일치. |
| R-15 | `pythonCompletion.ts:94-164,329-342`, `src/providers/providerRegistry.ts:67-96,224-283,489-560,642-665`, `worker.ts:572-603` | 등록·스코프·종료 호출 코드와 `maybeReleaseResource`(`providerRegistry.ts:553-632`: 점유자 또는 `activeCalls`가 있으면 보류, 아니면 `resource.shutdown()`)를 읽었다. |
| R-16 | C-07, `pythonCompletion.ts:128-132` | 코드 읽기. |
| R-17 | C-08, `src/util/transform.ts:94-102`, `src/util/secureTempFiles.ts` | 코드 읽기. `wrapper.py`는 모듈 import 때 `Importing module …`을 stdout에 출력(debug 로그로 감). |
| R-18 | `src/ruby/wrapper.rb:13-46`, `src/ruby/rubyUtils.ts:187-366`, `rubyCompletion.ts:116-243`, `assertions/ruby.ts` | 코드 읽기. Ruby `callApi`는 2번 인자까지만 받고 임베딩만 `abortSignal` 전달. |
| R-19 | C-09, `golangCompletion.ts:145-163`(`runCommand`), `:214-218`(`catch`가 `error.message`만 사용) | 코드 읽기. 문서 `site/docs/providers/go.md`는 `CallApi` 시그니처와 `package main` 외 패키지 지원을 설명하고 함수 이름 제한은 말하지 않는다(차이: 문서에 없는 제한). |
| R-20 | C-10, `site/docs/providers/custom-script.md`(stdout이 `output`, JSON도 `output`이라는 설명과 일치) | 코드 읽기. |
| R-21 | `src/providers/registry.ts:1685-1704`, `src/esm.ts:232-262` | 코드 읽기. |
| R-22 | `src/assertions/index.ts:480-571`, `src/assertions/utils.ts:54-68` | 코드 읽기. |
| R-23 | C-11, `assertions/python.ts`, `assertions/ruby.ts` | 코드 읽기. |
| R-24 | C-12 | 코드 읽기. |
| R-25 | `src/evaluatorHelpers.ts:257-297` | 코드 읽기. |
| R-26 | `src/prompts/processors/python.ts:20-106`, `processors/javascript.ts:7-52`, `processors/executable.ts:19-143`, `src/prompts/index.ts:56-125`, `src/evaluatorHelpers.ts:397-421` | 코드 읽기. `.rb`가 실행 파일 확장자 목록에 있어 Ruby 브리지를 거치지 않는다. |
| R-27 | C-13, C-14, `src/types/index.ts:1223-1249`(스키마), `src/node/doEval.ts:834-843`(경고만), `src/util/config/load.ts:1089-1092`(CLI 우선) | 코드 읽기. 문서 `reference.md`의 호출 규약 설명(`site/docs/configuration/reference.md:466-482`)과 일치. 스키마는 함수 이름을 필수로 요구하지만 런타임은 이름 없는 항목도 처리한다(차이). 함수 이름이 `before_all`처럼 snake_case면 모든 훅에서 레거시 규약으로 불린다(문서 예시의 `extension_hook`과 같은 경우). |
| R-28 | `src/evaluator.ts:2380-2435`, `:5794`, `src/evaluatorHelpers.ts:683-754`, `:830-850` | 코드 읽기. |
| R-29 | `src/evaluator.ts:4350-4372`, `:3250-3300`(평가 단계 생성), `:4507-4577`(`processEvalStepWithTimeout`: `Promise.race([processEvalStep, 타이머])`, `finally`에서 `evalStep.test` 복사), `src/providers/providerRegistry.ts:113-120`(`throwIfAborted`), `src/evaluator.ts:1767-2100` 구간에 abort 검사 없음(`grep throwIfAborted` 결과) | 코드 읽기. [eval-run](./eval-run.md) R-35·R-41과 같다. |
| R-30 | `src/evaluator.ts:4399-4442`, `src/evaluatorHelpers.ts:855-893` | 코드 읽기. 문서 "Fields like success, score… not overridable"과 일치. |
| R-31 | `src/evaluator.ts:5649-5663`, `:5599-5601` | 코드 읽기. |
| R-32 | `src/evaluatorHelpers.ts:818-829`, `src/evaluator.ts:4404-4442`, `:6030-6070,6120-6140`(`evaluationError` 재던짐) | 코드 읽기. `afterAll` 예외 전파는 호출부에 try/catch가 없는 것과 `evaluate()`의 재던짐 구조로 읽었다. |
| R-33 | `src/envars.ts:526-535`, 호출처: `worker.ts:100`, `pythonUtils.ts:276`, `rubyUtils.ts:290`, `golangCompletion.ts:144`, `scriptCompletion.ts:103`, `executable.ts:65` | 코드 읽기. `getEnvOverrides` 계층 구조는 열지 않았고 `envars.ts:546-551`의 주석으로 판단했다. |
| T-01~T-17 | 각각 관련 R-ID의 근거와 같다 | 구현에서 도출. 실행하지 않았다. |

### 2.2 코드 읽는 순서 [선택]

1. `src/providers/registry.ts:432-435` → `scriptBasedProvider.ts`: 문자열이 어떤 provider 클래스가 되는지.
2. `src/providers/pythonCompletion.ts` → `src/python/workerPool.ts` → `worker.ts` → `persistent_wrapper.py`: Python provider 한 호출의 전체 경로(Node 쪽 큐·타임아웃, Python 쪽 프로토콜).
3. `src/providers/scriptResult.ts`, `scriptContext.ts`: Python·Ruby가 공유하는 입력·검증·캐시 규칙.
4. `rubyCompletion.ts`·`rubyUtils.ts`·`wrapper.rb`, `golangCompletion.ts`·`wrapper.go`, `scriptCompletion.ts`: 나머지 계열의 차이.
5. `src/evaluatorHelpers.ts:756` `runExtensionHook` → `util/transform.ts`: 훅 호출 규약과 Python/JS 해석. 호출 위치는 `src/evaluator.ts`의 `runBeforeAllExtensions`, `runEvalStepAfterBeforeEach`, `processEvalRows`, `runAfterAllExtensions`.

원본 구현 전략: Python provider만 퍼시스턴트 워커 풀로 최적화되어 있고, 같은 `pythonUtils.runPython` 일회성 경로를 어서션·변수·변환·훅이 재사용한다. 인자와 결과는 모두 "임시 JSON 파일"로 오가고 stdout/stdin은 제어 신호용이라 사용자 `print`와 충돌하지 않는다.

### 2.3 비교·재사용 출처 [선택]

- 어서션 계열 스펙 [assertion-family](./assertion-family.md)가 R-08(값 해석), R-37(Python·Ruby 인라인), R-38·R-39(반환 정규화)에서 이 스펙의 R-22~R-24와 같은 규칙을 정의한다. 일회성 프로세스 호출 세부는 이 스펙의 R-17·R-18이 기준이고, 반환 정규화는 assertion-family R-35~R-39가 기준이다. 사례 T-11은 assertion-family T-11과 같다.
- 평가 단계 타임아웃과 훅 호출 위치는 [eval-run](./eval-run.md) R-35·R-41이 기준이고, 이 스펙은 훅 호출 규약과 워커 풀 쪽 상호작용(R-13, R-29)을 정의한다.

## 적용 메모 [선택]

"내 스킬(SKILL.md)을 여러 모델에 평가하고 모델 적합도를 기록하는 환경"에서 가져올 때의 메모다. 원본과 다르게 할 점이라기보다 이 목적에 맞는 선택지다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-20, R-19, R-18, R-17 | 내 CLI(Codex 등)를 평가 대상으로 붙일 때는 `exec:`을 그대로 쓰지 말고 Python `call_api` 래퍼(`subprocess`로 CLI 실행 후 `{output, tokenUsage, cost, metadata, sessionId}` 반환)를 기본 경로로 삼는다. | `exec:`은 명령 뒤에 `prompt`·options JSON·context JSON을 **항상 덧붙여** 외부 CLI 인자와 충돌하고, 출력은 stdout 문자열뿐이라 토큰·비용·메타데이터를 못 돌려주며, 타임아웃과 구조화된 오류 경로가 없다. Ruby·Go도 타임아웃이 없고 Go는 호출마다 모듈을 복사해 빌드한다. 반면 Python provider는 `timeout`·`workers`·`error` 반환·캐시를 모두 갖는다. | 신규 설계: 스크립트 provider 한 종류(Python 규약, R-03·R-04·R-05)와 호출별 타임아웃(R-13)을 기본으로 두면 R-17~R-20은 가져오지 않아도 된다. |
| R-08, R-13 | 에이전트형 CLI는 작업 디렉터리·세션 상태를 쓰므로 워커 간 전역 상태가 공유되지 않는다는 점(R-08)을 "격리 보장"으로 쓰고, 호출마다 별도 작업 디렉터리를 만드는 책임은 스크립트에 둔다. 타임아웃(기본 300초)은 스킬 평가에 맞춰 호출 단위 설정으로 연다. | 원본은 워커 프로세스를 호출 사이에 재사용하므로 상태가 남는다. | 사례: 같은 워커에 연속 호출 시 모듈 전역 상태가 유지됨(T-05)을 그대로 두고, 스킬 평가용 래퍼는 호출마다 임시 디렉터리에서 CLI를 실행한다. |
| R-22, R-24 | 맞춤 채점은 `file://grade.py:get_assert`의 `{pass, score, reason, named_scores}` 반환 규약만 가져온다. snake_case 매핑·threshold·inverse는 그대로 유용하다. | 모델별 적합도를 `named_scores`(항목별 점수)로 기록하기 쉽다. | 바뀌는 것 없음. 인라인 `python`/`ruby` 코드 어서션(R-23)은 코드 주입 경로라 가져오지 않아도 된다. |
| R-27, R-30, R-31 | 기록은 `afterEach`에서 `namedScores`·`metadata`를 붙이고 `afterAll`에서 전체 결과를 모아 저장한다. JS 훅은 같은 프로세스라 모듈 상태를 유지할 수 있지만 Python 훅은 호출마다 새 프로세스라(R-17) 상태를 못 가진다. | 기록 저장을 파일·DB에 쓰려면 JS 훅이 편하고, Python으로 쓰려면 `afterAll`에서 일괄 처리하는 편이 낫다. | 인터페이스: 훅 이름 4개와 `(context, {hookName})` 규약만 가져오고 `file://path:fn` 스키마 검증은 필수로 올려 경고에 그치지 않게 한다(원본은 경고만 한다, R-27). |
| R-33 | 설정의 `env:`가 자식 프로세스 환경에 안 들어가는 규칙은 그대로 두지 말고, 스킬 평가에서는 필요한 키를 래퍼에 명시적으로 넘기는 방식을 정한다. | 원본에서는 `options.env`(스크립트 인자)로만 전달되어 CLI가 `os.environ`에서 키를 못 읽는다. | 신규 설계: 래퍼가 `options.env`를 `subprocess` 환경에 합치는 규칙을 문서화한다. |
