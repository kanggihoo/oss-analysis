---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/cache.ts
  - src/cache/storage.ts
  - src/types/cache.ts
  - src/envars.ts
  - src/main.ts
  - src/commands/cache.ts
  - src/commands/eval.ts
  - src/node/doEval.ts
  - src/evaluator.ts
  - src/providers/agentic-utils.ts
  - src/providers/agentWorkspace.ts
  - src/providers/claude-agent-sdk.ts
  - src/providers/opencode-sdk.ts
  - src/providers/openai/codex-sdk.ts
  - src/providers/anthropic/messages.ts
  - src/providers/anthropic/generic.ts
  - src/providers/pythonCompletion.ts
  - src/providers/scriptCompletion.ts
  - src/util/sanitizer.ts
  - site/docs/configuration/caching.md
  - site/docs/providers/claude-agent-sdk.md
  - test/providers/claude-agent-sdk.test.ts
depends: []
status: ready
reimplementation: 미실행
---

# 응답 캐시 (response-cache)

> provider 호출 결과를 디스크(기본)·메모리에 TTL(기본 14일)로 저장해 같은 요청이면 재사용하고, `--no-cache`·환경변수·repeat 이름공간·provider별 키 규칙(특히 에이전트 provider의 `working_dir` 지문)으로 재사용 여부를 정한다. 경로는 모두 `repos/promptfoo/` 기준이다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. `promptfoo eval`이 캐시 정책을 정한다. 우선순위는 CLI `--no-cache`(명시했을 때만) > 설정 `commandLineOptions.cache` > `evaluateOptions.cache` > 기본 true다. false면 `disableCache()`를 부른다(R-05).
2. 평가기는 (테스트, prompt, repeat) 한 건마다 "캐시 켜짐 여부"와 `repeat:<i>` 이름공간을 비동기 컨텍스트(AsyncLocalStorage)에 얹고 provider를 부른다. 채점·비교 호출도 같은 이름공간 아래서 돈다(R-06, R-07).
3. provider가 스스로 키를 만든다. 공통 HTTP 경로(`fetchWithCache`)는 요청(URL·헤더·본문·옵션) 해시, Anthropic Messages는 요청 파라미터 해시, 에이전트 provider는 prompt+옵션+`working_dir` 지문 해시, python/exec는 스크립트 파일 내용 해시+prompt다(R-09~R-12, R-18~R-26).
4. 저장소에서 키를 조회한다. 있으면 호출 없이 `cached: true` 응답을 돌려주고, 없으면 실제 호출한 뒤 성공 응답만 저장한다(R-12~R-13).
5. 평가기는 캐시 응답이면 `incurredCost`를 0으로 기록하고 provider 지연(`delay`)을 건너뛴다(R-16).
6. 재호출이 일어나는 경우: TTL 만료, `promptfoo cache clear`, 키 재료 변화, 캐시 우회 조건, 프로세스 경계(인스턴스 범위 캐시)(R-03, R-17, R-23, R-25, R-18).

### 1.2 범위·통합 지점

- 제공: 저장소 선택·TTL·활성화 정책, repeat 이름공간, 공통 HTTP 캐시(`fetchWithCache`)의 키·저장 조건, 에이전트 provider 캐시(Claude Agent SDK, OpenCode SDK)의 키·우회 조건·`working_dir` 지문, Anthropic Messages·python·exec provider의 키 규칙, "스킬 파일을 바꿨는데 이전 결과가 나오는가"의 조건별 판정(R-28~R-34).
- 제외(이유):
  - provider 호출 구현 자체, 평가 실행 순서(요청된 제외).
  - 그 밖 provider의 개별 키 구성. `fetchWithCache`를 쓰는 파일이 39개, `getCache()`를 직접 쓰는 파일이 27개다. 이 스펙은 공통 `fetchWithCache` 규칙과 Anthropic Messages·python·exec·에이전트 provider만 읽었고 나머지(golang·ruby·bedrock 등)는 미탐색이다.
  - `claimCacheKeyOnce`(`src/cache.ts:624`): OpenAI Responses 백그라운드 과금 중복 방지용 일회성 표식이라 응답 재사용과 무관하다(사용처 `src/providers/openai/responses.ts:1696`만 확인).
- 외부 의존: `cache-manager`(`>=7.2.8 <7.2.10`), `keyv`^6, `keyv-file`^5(`package.json`). 만료 판정과 파일 직렬화는 이 라이브러리가 한다(확인 한계).
- 소유 상태·부작용: 디스크 파일 `<캐시 경로>/cache.json`(키-값 한 파일), 일회성 표식 디렉터리 `<캐시 경로>/claims/`, 프로세스 내 인스턴스·이름공간 맵·진행 중 요청 맵. `--no-cache`는 기존 항목을 지우지 않는다(R-06).

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `PROMPTFOO_CACHE_ENABLED` | bool 문자열 | 기본 true. `1`,`true`,`yes`,`yup`,`yeppers`(대소문자 무시)만 true, 빈 문자열은 기본값, 그 밖의 문자열은 false(`src/envars.ts:567-580`). 모듈 로드 시 한 번만 읽는다(R-04). |
| `PROMPTFOO_CACHE_TYPE` | `disk`\|`memory` | 미설정이면 `NODE_ENV==='test'`일 때 memory, 아니면 disk. `disk` 이외의 값은 memory로 동작한다. 모듈 로드 시 한 번 읽는다. |
| `PROMPTFOO_CACHE_PATH` | 디렉터리 경로 | 기본 `<설정 디렉터리>/cache`. 설정 디렉터리는 `PROMPTFOO_CONFIG_DIR` 또는 `~/.promptfoo`. 없으면 만들고 info 로그를 남긴다. 파일은 `cache.json`. |
| `PROMPTFOO_CACHE_TTL` | 정수(초) | 기본 1209600(14일). 비어 있거나 정수가 아니면 기본값. 캐시 인스턴스를 처음 만들 때 적용한다(R-03). |
| `PROMPTFOO_CACHE_MAX_FILE_COUNT`, `PROMPTFOO_CACHE_MAX_SIZE` | 숫자 | `src/envars.ts:125-126` 타입 선언만 있고 `src/` 어디서도 읽지 않는다(검색 확인). 효과 없음. |
| `--no-cache` | eval 옵션 | "Do not read or write results to disk cache"(`src/commands/eval.ts:94`). 사용자가 명시했을 때만 설정을 덮는다(`:188-191`). |
| `commandLineOptions.cache`, `evaluateOptions.cache` | bool | 설정 파일 키. Node API는 `evaluate(suite, {cache:false})`. |
| `promptfoo cache clear [--env-file p]` | 명령 | 저장소 전체 삭제(R-17). |
| `getCache()` | → Cache | 현재 이름공간이 있으면 키 앞에 `<ns>:`를 붙이는 래퍼, 없으면 기본 인스턴스. |
| `withCacheNamespace(ns, fn)` / `withCacheEnabled(bool\|undefined, fn)` | 비동기 컨텍스트 | 중첩 ns는 `부모:자식`, 같은 ns 재진입은 무시. `enabled` 인자가 undefined면 변경 없음. |
| `fetchWithCache(url, options, timeout, format, bustOrOptions, maxRetries, onResponsePrepared, onRateLimitBackoff)` | → `{data, cached, coalesced?, status, statusText, headers?, latencyMs?, deleteFromCache, updateCache}` | `bustOrOptions`는 bool 또는 `{bust, repeatIndex, cacheKey, sanitizeResponse}`(`src/types/cache.ts`). `format`은 `json`\|`text`. |
| 저장 값 | 문자열 | fetch: `JSON.stringify({data,status,statusText,headers,latencyMs})`. 에이전트: `JSON.stringify(ProviderResponse)`(읽을 때 `cached:true`를 덧붙임). Anthropic Messages: 메시지 JSON. |
| `ProviderResponse.cached`, `CallApiContext.bustCache/repeatIndex/getCache` | bool/int/함수 | 평가기가 provider에 주는 맥락. 캐시가 꺼져 있으면 `bustCache=true`가 들어간다(`src/evaluator.ts:1274-1278`). |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 환경변수 미설정 | 캐시 켜짐, 저장소 disk, TTL 14일. | 코드 확인 |
| R-02 | 첫 `getCache()` 호출 시 type=disk이고 모듈 `enabled`=true | `<경로>/cache.json` 디스크 캐시(디렉터리 자동 생성). 초기화가 예외로 실패하면 warn 후 메모리 캐시. type=memory(또는 `NODE_ENV=test`, 또는 그 시점에 `enabled`=false)이면 메모리 캐시이고 프로세스와 함께 사라진다. | 코드 확인 |
| R-03 | TTL | 기본 TTL은 인스턴스 생성 시 `getCacheTtlMs()`로 전달된다. Anthropic의 프로세스 내 캐시는 호출마다 `getCacheTtlMs()`를 읽고 `ttl<=0`이면 무기한이다. 디스크 항목의 실제 만료 판정과 `PROMPTFOO_CACHE_TTL=0`의 의미는 라이브러리 소관이다. | 코드 확인(전달) / 미확인(라이브러리 만료 의미) |
| R-04 | `PROMPTFOO_CACHE_ENABLED`·`PROMPTFOO_CACHE_TYPE`를 `--env-file`/`.env`로만 지정 | 두 값은 `cache.ts` 모듈 평가 시 읽는다. `--env-file` 로드는 `main()` 안에서 일어나므로(`src/main.ts:54-55`) 그 뒤에 로드된 값은 이 두 값에 반영되지 않을 가능성이 크다. 셸 환경변수는 반영된다. PATH·TTL은 지연 읽기라 `.env`로 바뀐다. | 추론(import 순서 근거, 실행 안 함) |
| R-05 | eval 실행 | `cache = CLI(명시) ?? commandLineOptions.cache ?? evaluateOptions.cache ?? true`. false면 로그 "Cache is disabled."와 `disableCache()`. resume/retry는 저장된 `runtimeOptions.cache`(없으면 true)를 쓴다. | 코드 확인 |
| R-06 | 캐시 꺼짐(`--no-cache`, `PROMPTFOO_CACHE_ENABLED=false`, `cache:false`) | 평가기는 `withCacheEnabled(options.cache===false ? false : isCacheEnabled())`로 감싼다. 그러므로 `evaluateOptions.cache:true`는 환경변수로 꺼진 캐시를 켜지 못한다. 꺼진 동안 `fetchWithCache`는 읽기·쓰기 모두 없이 곧바로 호출하고, 에이전트 provider는 "비활성" 결과(읽기·쓰기 없음)를 쓴다. 기존 항목은 지워지지 않으며, 이후 캐시를 켠 실행은 그 항목에 히트할 수 있다. | 코드 확인 |
| R-07 | repeat 이름공간 | 호출은 `repeatIndex>0` 이거나 유효 repeat 수>1이면 이름공간 `repeat:<i>`(i는 0부터) 아래서 실행한다. 테스트별 `options.repeat`가 전역을 덮는다. 모든 키는 `<ns>:<키>`가 된다. repeat=1의 index 0은 이름공간이 없으므로 `--repeat 2`의 `repeat:0` 항목과 키를 공유하지 않는다. 같은 설정으로 다시 돌리면 repeat마다 각자 항목에 히트한다. 채점(assertion)·비교 단계도 같은 이름공간으로 감싼다. | 코드 확인 |
| R-08 | `fetchWithCache`에 `repeatIndex>0`을 직접 넘김 | 현재 이름공간에 `repeat:<i>`가 이미 없을 때만 키에 `:repeat<i>` 접미를 붙인다(평가기 경유 호출은 R-07 때문에 접미 없음). | 코드 확인 |
| R-09 | fetch 키 재료 | 키 = `[<ns>:]fetch:v3:` + sha256(JSON{format, headers, method, options, url}) + `[:repeat<i>]`. headers는 이름·값 정렬 목록이고 `traceparent`·`tracestate`는 제외. options는 `headers`·`signal`·`method`를 뺀 나머지를 이름순으로 담고 `body`는 본문 식별자로 대체. 클라우드 대상 요청이면 클라우드 인증 헤더·팀 ID 헤더가 실제 전송값처럼 키에 들어간다. | 코드 확인 |
| R-10 | fetch 키의 비밀 처리 | 헤더·쿼리·JSON 본문에서 필드명이 비밀 목록(`isSecretField`)에 있거나 값이 비밀 모양(`looksLikeSecret`: `sk-`, Bearer, AKIA 등과 64자 이상 base64 계열)이면 값을 `{__promptfooSecretFingerprint: HMAC-SHA256(고정 salt)}`로 바꿔 해시한다. salt는 컴파일 상수라 프로세스를 넘어 안정적이다. 따라서 API 키 값이 바뀌면 키가 바뀌어 미스, 같은 값이면 실행 사이에도 히트한다. 분류기가 달라지면 키 값만 달라질 뿐 의미는 같다. | 코드 확인 |
| R-11 | 본문이 string·URLSearchParams·ArrayBuffer·TypedArray가 아님(스트림, FormData 등), 또는 `options`에 원시값이 아닌 항목이 있음 | 키를 만들 수 없어(`null`) 캐시 없이 호출한다. | 코드 확인 |
| R-12 | 호출 성공 여부 | 응답이 `ok`(2xx)이고 JSON 형식일 때 본문 최상위 `error` 값이 truthy가 아니면 저장한다. 비-ok, `error` 있음은 저장하지 않지만 결과는 호출자에게 반환한다. 비-ok에서 본문이 비면 data는 `Empty Response: <status>: <statusText>`. `ok`이고 본문이 빈 text 형식은 저장에서 제외하는 규칙이 없다(문서의 "Empty responses are not cached"와 다름, 2.1). | 코드 확인 |
| R-13 | 캐시 히트·미스·동시 요청 | 히트: 호출 없이 `cached:true`, 저장된 `latencyMs`. 미스: 호출 후 `cached:false`. 같은 키(와 같은 abort signal)를 동시에 미스한 호출은 업스트림 호출 하나를 공유하고, 나중 호출자는 `coalesced:true`·`cached:false`를 받는다. 쓰기가 끝날 때까지 호출자는 대기한다(취소 가능). | 코드 확인 |
| R-14 | 캐시 켜짐 & bust 아님 & `getAuthHeaders` 또는 `sanitizeResponse`를 쓰는데 `cacheKey`를 직접 안 줌 | 예외 발생("Request-time authentication requires cache bypass or an explicit principal-scoped cache key." / "Response sanitization requires …"). `cacheKey`를 주면 접두 `fetch:v3:`(클라우드 리다이렉트 제한 시 `fetch:cloud-auth:v3:`) 뒤에 붙는다. | 코드 확인 |
| R-15 | `fetchWithCache`의 `bust:true` | 읽기·쓰기 모두 하지 않고 직접 호출한다(캐시 비활성과 같음). 에이전트 유틸의 `bustCache`는 주석상 "읽기만 우회, 쓰기는 함"이지만, 평가기가 `bustCache=true`를 주는 경우는 캐시가 꺼진 경우뿐이고 그때는 유틸이 먼저 비활성 결과를 돌려주므로 이 분기는 평가 경로에서 도달하지 않는다. | 코드 확인 |
| R-16 | 평가기의 캐시 응답 처리 | `response.cached`이면 provider `delay`를 건너뛰고, `cost`는 그대로 두되 `incurredCost`를 0으로 기록한다. | 코드 확인(비용·지연) / 미탐색(통계 집계 세부) |
| R-17 | `promptfoo cache clear` 또는 `cache.clearCache()` | 진행 중 요청 맵·이름공간 인스턴스 맵을 비우고 저장소 전체를 지우며 `claims/`를 삭제한다. 이름공간 인스턴스의 `clear`는 그 접두를 가진 키만 지운다. clear 세대 카운터가 올라가 Anthropic의 프로세스 내 캐시도 비워진다. | 코드 확인 |
| R-18 | Anthropic Messages | 캐시는 `isCacheEnabled()`, MCP 미사용, 커스텀 헤더 없음일 때만 쓴다. 키 = `anthropic:messages:<모델>:<apiBaseUrl 해시>:<해시{providerId, label 또는 인스턴스 UUID}>:<해시{요청 params(metadata 제외)+헤더}>`. `label`이 있으면 디스크(공유) 캐시에 읽고 쓰고, 없으면 provider 인스턴스 안의 메모리 맵(최대 개수 제한, TTL 적용)만 쓰므로 프로세스 사이에 재사용되지 않는다. `pause_turn`은 저장하지 않는다. | 코드 확인 |
| R-19 | python·exec provider | python 키 = `python:<경로>:<함수>:<apiType>:<스크립트 내용 sha256>:<prompt>:<options JSON>:<vars JSON>`, exec 키 = `exec:<명령>:<명령에 나온 실존 파일들의 내용 해시>:<prompt>:<options JSON>`(해시할 파일이 없으면 캐시 안 씀). 스크립트가 따로 읽는 다른 파일(예: SKILL.md)은 키에 없다. python은 오류 결과를 저장하지 않는다. | 코드 확인(python·exec만) |
| R-20 | 에이전트 공통 `initializeAgenticCache` | 캐시 꺼짐 → 비활성. `mcp`가 있고 `cacheMcp`가 아니면 → 비활성. `workingDir`가 있는데 지문 계산이 예외(타임아웃 포함)면 오류 로그("Caching is disabled.") 후 비활성. 그 밖에는 키 = `<prefix>:<sha256(JSON{…cacheKeyData, workingDirFingerprint(없으면 null), mcp(있으면)})>`, 읽기는 `!bustCache`, 쓰기는 항상. `getCache()`를 쓰므로 repeat 이름공간이 적용된다. 히트 시 `{...저장값, cached:true}`, 읽기·쓰기 오류는 로그만 남기고 무시한다. | 코드 확인 |
| R-21 | `getWorkingDirFingerprint(dir)` | sha256("dir:<dir mtimeMs>;files:<정렬된 `상대경로:mtimeMs` 목록을 `,`로 연결>"). `dir` 아래를 재귀로 훑고 숨김·`.git`·`node_modules`도 제외하지 않는다. 일반 파일(`isFile()`)만 포함하고 하위 디렉터리 자체의 mtime은 넣지 않는다. 시작 후 2000ms를 넘기면(디렉터리 순회 중, 32개씩 stat하는 배치 사이에서 확인) 예외. | 코드 확인 |
| R-22 | 지문이 감지하지 못하는 것 | (a) `working_dir` 밖의 파일: 사용자 `~/.claude/skills`와 사용자 수준 설정, `additional_directories`, `plugins` 경로 내용. (b) 내용이 바뀌어도 mtime이 같은 파일(내용이 아닌 mtime만 사용). (c) 심볼릭 링크로만 닿는 파일·디렉터리: `readdir(withFileTypes)`의 `isFile()/isDirectory()`는 링크에 false라 목록에서 빠진다. 반대로 과잉 무효화도 있다: 폴더 안 무관한 파일 변경·`.git` 내부 변화도 지문을 바꾼다. | 코드 확인(a, b) / 추론(c: Node Dirent 표준 의미, 실행 안 함) |
| R-23 | Claude Agent SDK 캐시 우회(읽기·쓰기 모두 안 함) | 다음 중 하나면 우회한다. 격리 작업공간(`copy_working_dir`로 eval 단계가 만든 복사본)에서 실행, `can_use_tool`·`on_elicitation`·`hooks`·`spawn_claude_code_process`가 있음, `ask_user_question.behavior==='random'`, 활성 MCP에 인증·헤더·env·인자·URL 자격증명/쿼리가 있음, `settings`·`managed_settings` 지정, `extra_args`가 비어 있지 않음, prompt 수준 설정이 `env`·`apiKey`를 provider 설정과 다르게 지정, `continue`·`resume`·`session_id`, `apiKeyRequired:false` 또는 Bedrock/Vertex 모드. MCP가 설정돼 있으면 별도로 `cache_mcp:true`가 있어야 캐시한다(R-20). 저장은 결과 subtype이 `success`일 때만 한다. | 코드 확인 |
| R-24 | Claude Agent SDK 키 재료 | `prompt`(변수가 렌더된 최종 문자열), `cacheKeyQueryOptions`, `credentialCacheScope`, `ask_user_question`(있으면), `workingDirFingerprint`, 활성 `mcp`. `cacheKeyQueryOptions`에는 모델·max_turns·권한 모드·system prompt(append/custom)·도구 허용/거부 목록(정렬·중복 제거)·`tools`·`skills`(이름 필터 값)·`plugins`(경로를 절대화한 목록, 내용 없음)·`agents`(내용 포함)·`setting_sources`(기본 `[]`)·`additional_directories`(절대 경로)·`output_format`·thinking/effort/budget 등이 들어간다. 제외: `cwd`(경로 자체), `title`, 콜백류, 프로세스 `env`(고정 `{}`), `mcpServers`. 따라서 `working_dir`의 위치가 달라도 지문(파일 상대경로+mtime)이 같으면 같은 키다. | 코드 확인 |
| R-25 | Claude Agent SDK의 `credentialCacheScope` | provider 인스턴스마다 `crypto.randomUUID()`로 만든 값이 항상 키에 들어간다. 그래서 다른 프로세스(= 다른 인스턴스)가 만든 디스크 항목은 같은 설정이어도 히트하지 않고, 같은 인스턴스 안에서만 재사용된다(같은 인스턴스 안에서도 repeat가 다르면 이름공간 때문에 별개). 디스크에는 쓰이지만 다음 실행이 읽지 못해 TTL까지 쌓인다. | 코드 확인 |
| R-26 | OpenCode SDK | 우회: 격리 작업공간, 상태 있는 세션(`session_id`·`persist_sessions`), 권한 규칙(`permission` 등) 존재, 민감 MCP, 민감 `baseUrl`, `restart_server_per_call`. 키 prefix `opencode:sdk`, 재료는 `prompt`와 `historyAffectingInputs`(provider_id·model·baseUrl·tools·permission·agent·workspace·format·variant·session_id 등·credentialScope·apiVersion). `config.working_dir`가 있을 때만 지문을 넣는다(없으면 지문 없음). `credentialScope`는 인스턴스 UUID지만 `config.baseUrl`이 있으면 `undefined`라 그때는 프로세스를 넘어 재사용된다. | 코드 확인 |
| R-27 | Codex SDK·Codex app-server | 응답 캐시 없음. 두 파일은 `../../cache`를 가져오지 않고, `cacheKey`는 스레드 재사용 키다. | 코드 확인 |
| R-28 | (스킬 판정 1) Claude Agent SDK, SKILL.md 수정 후 `promptfoo eval`을 새로 실행(`--watch` 재실행 포함) | 이전 실행이 디스크에 쓴 항목은 R-25 때문에 히트하지 않는다. 따라서 이전 결과가 나오지 않는다(SKILL.md 위치와 무관). 전제: 실행마다 provider 인스턴스를 새로 만든다. `eval` 경로의 `resolveConfigs→loadApiProviders`(`src/node/doEval.ts:519`, watch 재실행도 매번 호출)에서 만들어진다고 읽었다. | 코드 확인(키) / 추론(인스턴스 수명) |
| R-29 | (스킬 판정 2) 같은 프로세스·같은 provider 인스턴스 안에서 키 재료가 같은 호출이 두 번 있고, 그 사이 SKILL.md가 `working_dir` 밖(사용자 `.claude/skills`, `plugins` 경로, `additional_directories`)에서 수정됨 | 두 번째는 이전 응답(`cached:true`)을 받는다. 키에 그 파일 내용이 없고 지문도 범위 밖이기 때문이다. 현실적 발생은 평가 도중 훅·에이전트·외부 프로세스가 파일을 바꾸는 경우로 좁다. | 코드 확인(키 재료) / 추론(발생 빈도) |
| R-30 | (스킬 판정 3) SKILL.md가 `working_dir` 안(예: `<working_dir>/.claude/skills/x/SKILL.md`, `setting_sources:['project']`)에 있고 수정됨 | mtime이 바뀌면 지문이 바뀌어 미스(재호출). 다만 mtime을 보존하는 수정(`cp -p`, `rsync -t` 등)이나 심볼릭 링크 경유 파일은 지문이 바뀌지 않아 같은 인스턴스 안에서는 이전 응답이 나올 수 있다(R-22). | 코드 확인(mtime 비교) / 추론(링크, mtime 보존) |
| R-31 | (스킬 판정 4) OpenCode SDK, `config.baseUrl` 지정, 스킬 파일이 `working_dir` 밖이거나 `working_dir` 미지정 | 프로세스를 넘어 항목이 재사용되고(R-26) 키에 스킬 내용이 없으므로 SKILL.md를 수정해도 이전 결과가 나올 수 있다. `working_dir` 안이면 R-30 규칙이다. `baseUrl`이 없으면 R-28과 같은 이유로 프로세스 간 히트 없음. | 코드 확인 |
| R-32 | (스킬 판정 5) 스킬 텍스트를 prompt·system prompt·변수로 넣는 직접 모델 호출(`fetchWithCache` 계열, Anthropic Messages) | 요청 본문(params)이 키 재료라 내용이 바뀌면 키가 바뀌어 미스. 오래된 결과는 나오지 않는다. 단 Anthropic Messages는 `label`이 없으면 프로세스 내 캐시만 쓰고(R-18), 실행 사이 재사용을 원하면 `label`이 필요하다. | 코드 확인 |
| R-33 | (스킬 판정 6) python·exec provider가 스크립트 안에서 SKILL.md를 직접 읽음 | 키에 스크립트 파일 내용 해시와 prompt·vars만 있어 SKILL.md를 수정해도 같은 키 → 이전 결과가 나온다(프로세스 간에도, TTL 14일까지). | 코드 확인 |
| R-34 | (스킬 판정 7) 확실히 신선한 결과가 필요한 경우 | `--no-cache`(읽기·쓰기 없음), `copy_working_dir`(에이전트 provider 캐시 우회, R-23), `promptfoo cache clear`. Claude Agent SDK는 새 프로세스면 R-28로 이미 안전하다. | 코드 확인 |

- 불변식: 키는 재료가 같으면 항상 같다(`credentialCacheScope`·인스턴스 UUID가 들어가는 키는 "인스턴스 범위 안에서" 같다). 저장 값은 성공 응답뿐이고 오류 응답은 저장하지 않는다(fetch: R-12, Claude: subtype success, python: 오류 제외). 항목은 응답 내용으로 무효화되지 않고, TTL·clear·키 재료 변화로만 사라진다.
- 미결정: 없음.
- 확인 한계: 설치·실행을 하지 않았다. (1) 디스크 항목의 만료 판정, `PROMPTFOO_CACHE_TTL=0` 의미, 동시 프로세스의 `cache.json` 쓰기 일관성은 `cache-manager`·`keyv`·`keyv-file` 내부 동작이라 미확인. (2) R-04(`.env` 시점), R-22(c)(링크), R-28의 인스턴스 수명은 코드 읽기에 의한 추론이다. (3) 에이전트 provider가 실제로 SKILL.md를 읽는 위치·방식(SDK 쪽 스킬 로딩)은 외부 SDK 동작이라 읽지 않았다. 지문과 키 규칙만 근거다. (4) Node API로 같은 provider 객체를 여러 번 `evaluate()`에 넘기는 장수 프로세스(예: 서버)는 R-29가 더 자주 해당할 수 있으나 경로를 따라가지 않았다.

### 1.5 필수 코드 참조

라이선스는 MIT(overview 1절)라 인용이 허용된다. 아래 파일은 Apache·다른 LICENSE가 걸린 하위 디렉터리에 속하지 않는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/cache.ts:55-69` `enabled`, `cacheType`, `getCacheTtlMs` | 환경변수 기본값·TTL 초 단위 변환 | R-01~R-04 |
| C-02 | `src/cache.ts:84-133` `getCache`, `getCacheInstance` | disk/memory 선택·폴백·경로 | R-02 |
| C-03 | `src/cache/storage.ts:12-77` `createDiskCache` | 디스크 저장 어댑터(keyv-file 한 파일, 값/만료 봉투). 다른 KV 저장소로 대체 가능 | R-02, R-03 |
| C-04 | `src/cache.ts:135-284` 이름공간 래퍼, `shouldApplyRepeatCacheSuffix`, `getScopedCacheKey`, `withCacheNamespace`, `clearNamespacedCache` | 접두 키 변환, 이름공간별 삭제, 중첩 규칙 | R-07, R-08, R-17 |
| C-05 | `src/evaluator.ts:474-482, 1760-1765, 4329-4331` | repeat 이름공간 이름 규칙과 적용 지점 | R-07 |
| C-06 | `src/cache.ts:349-449` 비밀 지문·문자열/URL/본문 정규화 | 비밀 값을 HMAC 지문으로 바꾸는 규칙 | R-10 |
| C-07 | `src/util/sanitizer.ts:144-249, 360-413` `SECRET_FIELD_NAMES`, `isSecretField`, `looksLikeSecret` | 비밀 판정 목록(바꿔도 키 값만 달라짐) | R-10 |
| C-08 | `src/cache.ts:451-605` 헤더·본문·옵션 식별자와 `getFetchCacheKey` | fetch 키 조립 | R-09, R-11 |
| C-09 | `src/cache.ts:815-877, 934-969, 991-1136` `prepareFetchResponse`, `fetchWithCache` | 저장 조건, bust·가드, 히트/미스/동시 요청 | R-12~R-15 |
| C-10 | `src/providers/agentic-utils.ts:67-142, 186-302` | 지문 알고리즘, 키 생성, 초기화·읽기·쓰기 | R-20, R-21 |
| C-11 | `src/providers/claude-agent-sdk.ts:1414, 1686-1857, 2495-2496` | 키 재료, 우회 조건, `credentialCacheScope`, success만 저장 | R-23~R-25 |
| C-12 | `src/providers/opencode-sdk.ts:987-989, 1133-1151, 2024-2061, 2161` | OpenCode 우회 조건·키 재료·`credentialScope` | R-26 |
| C-13 | `src/providers/anthropic/messages.ts:1123-1150, 1215-1225`, `src/providers/anthropic/generic.ts:221, 372-445` | Anthropic 키와 label별 저장 범위 | R-18 |
| C-14 | `src/providers/pythonCompletion.ts:239-246`, `src/providers/scriptCompletion.ts:40-75` | 스크립트 해시 기반 키 | R-19, R-33 |
| C-15 | `src/node/doEval.ts:596-630`, `src/commands/eval.ts:188-191` | 캐시 설정 우선순위 | R-05 |

### 1.6 수락 사례

출처는 기본이 "구현에서 도출"이다. 표기한 것은 원본 테스트 열람이며, 파일 시스템·SDK를 목으로 바꾼 단위 테스트라 실행하지 않았고 실행 확인이 아니다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-09, R-12, R-13 | 캐시 켜짐, 같은 POST 요청(JSON 본문)을 두 번 `fetchWithCache`, 응답 200 | 호출 1회, 둘째는 `cached:true`. |
| T-02 | R-06 | `--no-cache`로 실행 후 캐시 켜고 다시 실행 | 첫 실행은 저장하지 않으므로 둘째도 미스. 앞서 존재하던 항목은 그대로 있다. |
| T-03 | R-12 | 응답 500, 또는 200이지만 본문 `{"error":"x"}` | 결과는 반환되고 저장되지 않아 다음 호출도 업스트림으로 간다. |
| T-04 | R-07 | `--repeat 3` 실행 후 같은 설정으로 재실행 | `repeat:0/1/2` 항목이 각자 히트(첫 실행에선 3회 호출). 한 실행 안에서 repeat 사이엔 항목을 공유하지 않는다. |
| T-05 | R-10 | 같은 요청에서 API 키 값만 변경 | 다른 키 → 미스. 같은 값이면 프로세스를 새로 띄워도 히트. |
| T-06 | R-25 | (원본 테스트 열람 `test/providers/claude-agent-sdk.test.ts:5858`) 같은 설정·같은 키의 provider 두 인스턴스 | 둘 다 SDK를 호출한다(호출 2회). |
| T-07 | R-21, R-30 | (원본 테스트 열람 `:5971`, 파일 mtime 목) `working_dir` 안 파일 mtime을 바꾼 뒤 재호출 | 지문이 달라 미스. 바꾸지 않으면 같은 인스턴스에서 히트. |
| T-08 | R-23 | `copy_working_dir` 사용 또는 `config.hooks` 지정 | 읽기·쓰기 모두 없이 매번 호출. |
| T-09 | R-20, R-21 | `working_dir`가 순회 2000ms를 넘는 큰 디렉터리 | 오류 로그 후 그 호출은 캐시 없이 실행(결과는 정상 반환). |
| T-10 | R-31 | OpenCode `baseUrl` 지정·`working_dir` 없음, SKILL.md 수정 후 새 프로세스로 같은 프롬프트 | 이전 응답이 `cached:true`로 나온다(TTL 내). |
| T-11 | R-18, R-32 | Anthropic Messages, system prompt에 SKILL.md 내용 포함, 내용을 바꿈 | 키가 달라 미스. `label`이 없으면 새 프로세스에서는 어떤 경우에도 미스. |
| T-12 | R-33 | python provider가 SKILL.md를 읽어 prompt에 합성, SKILL.md만 수정 | 스크립트·prompt·vars가 같으면 이전 결과 히트. |
| T-13 | R-09 | 두 요청이 헤더 순서·`traceparent`만 다름 | 같은 키(헤더 정렬, trace 헤더 제외). |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (promptfoo@dfe2d45) | 확인 방법·한계 |
|---|---|---|
| R-01, R-02, R-03 | C-01, C-02, C-03; `src/envars.ts:567-580` `getEnvBool`, `:599-611` `getEnvInt`; `src/util/config/manage.ts:9-17` | 코드 읽기. 만료 판정은 라이브러리(확인 한계). 사이트 문서 `site/docs/configuration/caching.md`의 기본값 표와 일치 |
| R-04 | `src/cache.ts:55-58`, `src/main.ts:52-55`, `src/mainUtils.ts:69-99` | 모듈 평가 시점과 `main()` 시점 대조(추론) |
| R-05 | C-15, `src/node/doEval.ts:609, 618, 627-629` | 코드 읽기 |
| R-06 | `src/evaluator.ts:1274-1278, 1760-1761, 6294-6296`; `src/cache.ts:286-296, 948, 991-1022` | 코드 읽기 |
| R-07, R-08 | C-04, C-05; `src/evaluator.ts:3147-3153, 5179-5186`; `src/cache.ts:183-194, 959, 595`; 문서 `caching.md`의 repeat 문장과 일치 | 코드 읽기 |
| R-09~R-11 | C-06~C-08 | 코드 읽기 |
| R-12 | `src/cache.ts:815-877`. **차이: 문서≠구현** — `caching.md`는 "Empty responses are not cached"라고 하나 구현은 비-ok의 빈 본문만 별도 처리하고 ok+빈 text 본문을 제외하는 코드가 없다. "Error responses are not cached"는 일치 | 구현을 사실로 씀 |
| R-13, R-14 | C-09; `src/cache.ts:1024-1065, 1102-1135` | 코드 읽기 |
| R-15 | `src/cache.ts:991`; `src/providers/agentic-utils.ts:153, 209-217, 242`; `bustCache`를 세팅하는 곳은 `src/evaluator.ts:1277` 외에 `src/redteam/strategies/gcg.ts:70`, `src/redteam/commands/discover.ts:315`(레드팀 경로, 이 스펙 밖). **차이: 문서≠구현** — `site/docs/providers/claude-agent-sdk.md:1291`은 "설정에 `bustCache: true`를 넣으면 읽기를 막는다"고 하나, `claude-agent-sdk.ts`는 `context?.bustCache`만 읽고 provider config 키로 받지 않는다 | 구현을 사실로 씀 |
| R-16 | `src/evaluator.ts:1343-1354, 1426-1441` | 통계(`testCacheHitCount`, `cacheHits`, `src/node/doEval.ts:937-952, 1035`)는 이름만 확인 |
| R-17 | `src/commands/cache.ts:6-45`; `src/cache.ts:125-130, 209-245, 1182-1193`; `src/providers/anthropic/generic.ts:417-423` | 코드 읽기 |
| R-18 | C-13 | 코드 읽기 |
| R-19 | C-14; `golangCompletion.ts`·`rubyCompletion.ts`는 `getCache`를 쓰는 것만 목록으로 확인, 미열람 | 코드 읽기(python·exec만) |
| R-20 | C-10 `agentic-utils.ts:205-247, 256-302` | 코드 읽기. 단위 테스트 사례명 `test/providers/agentic-utils.test.ts:248-330`(mcp·bustCache)만 확인 |
| R-21, R-22 | C-10 `agentic-utils.ts:99-142` | 코드 읽기. (c)는 Node 표준 동작에 기댄 추론. 테스트 `claude-agent-sdk.test.ts:5971`은 fs를 목으로 바꾼 것 |
| R-23~R-25 | C-11; `src/providers/agentWorkspace.ts:88-141` `assertIsolatedWorkingDir`; 문서 `claude-agent-sdk.md:1252-1283`. **차이: 문서≠구현** — 문서 첫 문장(1254)은 "프롬프트·설정·`working_dir` 파일이 이전 실행과 같으면 캐시를 읽는다"며 실행 사이 재사용을 암시하나 구현은 provider 인스턴스 범위다(문서 1275-1277은 "one provider" 범위를 언급) | 구현을 사실로 씀 |
| R-26 | C-12 | 코드 읽기 |
| R-27 | `src/providers/openai/codex-sdk.ts:1923-1942, 2212`; `codex-app-server.ts`의 `cacheKey`/`threads` | `../../cache` import 부재를 grep으로 확인 |
| R-28~R-34 | R-20~R-26 + `src/providers/claude-agent-sdk.ts:1729-1733, 1772`(plugins·skills·settingSources) + `src/node/doEval.ts:519, 1236-1275, 1301-1335` | 판정은 키 재료·지문 범위 대조. 실행 확인 없음 |
| T-06 | `test/providers/claude-agent-sdk.test.ts:5839-5882` | 사례명·본문 열람, 실행 안 함 |
| T-07 | `test/providers/claude-agent-sdk.test.ts:5971-6041` | 위와 같음 |
| 나머지 T | 해당 R-ID 근거 | 구현에서 도출. 실행 안 함 |

### 2.2 코드 읽는 순서

1. `src/cache.ts:55-133`(정책·저장소) → `:135-284`(이름공간) → `:916-1136`(`fetchWithCache`).
2. `src/evaluator.ts:474-482, 1274-1278, 1760-1765, 6294`(정책을 컨텍스트로 얹는 지점).
3. `src/providers/agentic-utils.ts:99-247` → `claude-agent-sdk.ts:1686-1857` → `opencode-sdk.ts:2024-2061`.
4. 구현 전략 두 가지: 정책과 이름공간을 전역 변수가 아닌 비동기 컨텍스트(AsyncLocalStorage)로 전달해 동시 실행되는 호출마다 값이 다르게 하고, 키는 "재료를 정규화하고 비밀은 고정 salt HMAC으로 바꾼 뒤 sha256"으로 만든다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드를 복사하지 않았다.

## 적용 메모

목적: 내 스킬(SKILL.md)을 여러 모델에 평가하고 개선하며 모델 적합도를 기록하는 환경. 아래는 우리 결정이고 원본 동작이 아니다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-24, R-30 | 에이전트 provider 캐시 키에 "스킬 디렉터리 내용 해시(SKILL.md와 참조 파일, 링크 추적)"를 명시적 재료로 넣는다 | mtime 지문은 `working_dir` 밖·링크·mtime 보존 수정을 놓치고(R-22), `.git` 같은 무관한 변화로 과잉 무효화된다 | 지문 입력과 키 재료 정의가 바뀐다. 사례: T-07에 "mtime 보존 수정도 미스"를 추가 |
| R-25 | Claude Agent SDK 캐시는 프로세스 간 효과가 없으므로(R-25) 캐시를 믿고 비용을 아끼려는 기대를 두지 않는다. 실행 사이 재사용이 필요하면 인스턴스 UUID 대신 안정적 식별자(label·모델·설정 해시)를 범위로 쓴다 | 모델 적합도 비교는 신선한 호출이 기본이어야 한다 | 키 범위 정의 변경. 사례: T-06을 "같은 label이면 히트"로 대체 |
| R-16, R-34 | 평가 기록에 `cached`와 `incurredCost`를 항상 남기고, 스킬 변경 전후 비교는 `--no-cache`이거나 스킬 내용 해시가 키에 든 경우만 신뢰한다 | 캐시 히트가 섞이면 적합도 수치가 오염된다 | 결과 레코드 필드 추가 |
