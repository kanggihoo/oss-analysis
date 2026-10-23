---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/providers/registry.ts
  - src/providers/index.ts
  - src/providers/credentials.ts
  - src/envars.ts
  - src/providers/claude-agent-sdk.ts
  - src/providers/opencode-sdk.ts
  - src/providers/openai/codex-sdk.ts
  - src/providers/openai/codex-app-server.ts
  - src/providers/openai/codexProcess.ts
  - src/providers/openai/codexApiKeyGating.ts
  - src/providers/openai/billing.ts
  - src/providers/agentic-utils.ts
  - src/providers/agentWorkspace.ts
  - src/providers/agenticRunQueue.ts
  - src/providers/mcp/transform.ts
  - src/contracts/providerConfig/mcp.ts
  - src/evaluator.ts
  - src/util/provider.ts
  - src/util/render.ts
  - src/util/pathUtils.ts
  - src/node/doEval.ts
  - src/scheduler/rateLimitRegistry.ts
  - src/assertions/cost.ts
  - src/matchers/agent.ts
  - site/docs/providers/claude-agent-sdk.md
  - site/docs/providers/openai-codex-sdk.md
  - site/docs/providers/openai-codex-app-server.md
  - site/docs/providers/opencode-sdk.md
  - site/docs/guides/test-agent-skills.md
depends:
  - provider-contract.md
  - skill-calls-metadata.md
  - response-cache.md
status: ready
reimplementation: 미실행
---

# 에이전트 SDK 프로바이더 (Claude Agent SDK · Codex SDK/app-server · OpenCode SDK)

> 평가 설정의 provider 항목(`anthropic:claude-agent-sdk`, `opencode:sdk`, `openai:codex-sdk`, `openai:codex-app-server`)을 받아, 렌더된 prompt 한 건을 코딩 에이전트 SDK에 보내고 그 에이전트가 낸 메시지·이벤트 스트림을 `ProviderResponse`(output·tokenUsage·cost·metadata·error)로 바꿔 돌려주는 provider 4종과, 그 호출의 도구·권한·작업 디렉터리·스킬 노출·세션 설정.

경로 표기: 1부 본문은 심볼과 옵션 이름 중심이고 `repos/promptfoo/` 기준 경로·줄 번호는 1.5와 2부에만 쓴다. 설명은 Claude Agent SDK를 끝까지 따라가고(R-10~R-32), OpenCode·Codex SDK·Codex app-server는 차이만 쓴다(R-33 이후).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표는 Claude Agent SDK다.

1. 평가기가 렌더된 prompt 문자열과 호출 문맥으로 `callApi(prompt, context, {abortSignal})`를 부른다. 이 시점에 `context.prompt.config`는 프롬프트 config에 테스트 `options`(`repeat` 제외)를 합친 값이고, `copy_working_dir`가 켜져 있으면 `working_dir`가 이미 복사본 경로로 바뀌어 있다(R-06, R-53).
2. provider가 유효 구성을 만들고(`{...provider config, ...prompt config}`) 옵션을 검증한다. 도구 허용 목록·사용 가능 도구·SDK 옵션·서브프로세스 환경을 계산한다. 이 단계의 오류는 예외로 던진다(R-08, R-10~R-22).
3. 캐시가 가능하면 키를 만들어 조회한다. 히트면 호출 없이 `cached: true` 응답을 돌려준다(키·우회 규칙은 [response-cache](response-cache.md)).
4. 작업 디렉터리를 준비한다(`working_dir` 확인 또는 빈 임시 디렉터리 생성). 호출자의 취소 신호를 SDK용 `AbortController`에 연결한다(R-10, R-31).
5. SDK의 `query({prompt, options})`를 호출하고 반환된 비동기 메시지 스트림을 끝까지 소비한다. `assistant` 메시지에서 도구 호출을, `user` 메시지에서 도구 결과를, `result` 메시지에서 종료 후보를 모은다(R-23).
6. 후보 중 메인 에이전트의 마지막 `result`를 고르고, 토큰·비용을 합산해 성공(`output`) 또는 실패(`error`) 응답을 만든다. 두 경우 모두 `metadata`에 `skillCalls`·`toolCalls` 등이 실린다. 성공 응답만 캐시에 쓴다(R-24~R-29).
7. 끝에서 임시 디렉터리 삭제와 취소 리스너 해제를 한다. 평가기는 응답 `metadata`에 워크스페이스 정보를 합치고 어서션이 끝나면 워크스페이스를 지운다(R-31, R-53).

다른 런타임의 차이는 다음과 같다.
- OpenCode: 로컬 서버를 띄우거나 `baseUrl` 서버에 붙어 세션을 만들고 prompt를 한 번 보낸다. 스킬 도구가 켜져 있으면 세션 이력을 다시 읽어 `skillCalls`를 만든다(R-33~R-39).
- Codex SDK: Codex CLI 자식 프로세스에 스레드를 만들어 `thread.run`(또는 스트리밍 `runStreamed`)을 한다(R-40~R-45).
- Codex app-server: `codex app-server`를 JSON-RPC로 구동해 `thread/start` → `turn/start` → 알림 수신 후 `turn/completed`를 기다린다(R-46~R-50).

### 1.2 범위·통합 지점 [필수]

- 제공: ① 4개 provider의 id 접두어와 모델 지정 방식, ② 평가 결과에 영향을 주는 옵션(모델, `working_dir`, 도구 허용·금지, 권한 모드·샌드박스, `setting_sources`·`skills`·`plugins`, MCP, 시스템 프롬프트, 턴·예산 한도, 세션·스레드 재개)의 이름·기본값·잘못된 값 처리, ③ 호출 흐름과 `ProviderResponse` 변환·실패·중단 규칙, ④ 토큰·비용 집계, ⑤ 작업 디렉터리 기본값·`copy_working_dir`·환경 노출 같은 안전 기본값, ⑥ 스킬 노출 설정이 SDK로 전달되는 경로, ⑦ provider별 응답 캐시 사용 여부 한 표(1.3).
- 제외(이유):
  - `metadata.skillCalls` 채우는 규칙과 `skill-used` 판정: [skill-calls-metadata](skill-calls-metadata.md) 소관이다. 여기서는 어디서 부르는지만 쓴다.
  - 캐시 키 재료·우회 조건·작업 디렉터리 지문: [response-cache](response-cache.md) R-20~R-34 소관이다. 여기서는 사용 여부 표와 링크만 둔다.
  - `ApiProvider` 계약·접두어 디스패치·env 병합: [provider-contract](provider-contract.md)(R-10~R-15, R-30~R-31).
  - 커스텀 타깃·레드팀·일반 LLM API provider, `openai:codex-security`, `openinterpreter`: 요청된 제외.
  - 트레이싱·OpenTelemetry(`deep_tracing`, GenAI 스팬 생성): 스펙 범위에서 제외된 기능이다. 이 provider들이 스팬을 만들지만 `ProviderResponse` 변환에는 영향이 없다(`deep_tracing`이 켜지면 Codex 스레드 지속 옵션이 무시되는 것만 R-43에 적는다).
  - 스케줄러(동시성·재시도·레이트리밋): 평가기가 provider를 감싸는 쪽이다. `provider.config.maxRetries`(비음수 정수)를 스케줄러가 읽는다는 것과 Codex SDK만 429 형태 오류를 만든다는 것(R-45)만 쓴다.
  - SDK 내부 동작(스킬 탐색·로딩, 권한 판단, 기본 도구 집합·기본 한도, 서브타입 이름, `thread.run`이 항목을 어떻게 채우는지): 외부 코드이므로 `미확인`으로 표시하고 확인 한계에 모은다.
- 외부 의존·선행 계약: 선행 스펙 3개가 정의한 `ApiProvider`·`ProviderResponse`·`TokenUsage`·접두어 디스패치·env 병합(provider-contract), `SkillCallEntry`와 `skill-used`(skill-calls-metadata), 캐시 정책·키·우회(response-cache)를 전제한다. 그 밖에 다음 외부 의존의 경계만 정의한다.
  - SDK 패키지·실행기: `@anthropic-ai/claude-agent-sdk`(`^0.3.273`), `@opencode-ai/sdk`(v2 우선, v1)와 `opencode` CLI, `@openai/codex-sdk`(`^0.156.1`), `codex` 실행파일. 입력은 옵션 객체, 정상 결과는 메시지·이벤트 스트림 또는 턴 결과, 실패는 예외 또는 비성공 결과다. 패키지가 없거나 버전이 맞지 않으면 설치 안내 오류가 `{error}`로 돌아온다(R-04).
  - 토큰→USD 환산 `calculateOpenAIUsageCostFromTokenUsage(model, tokenUsage) → number | undefined`: Codex 두 provider만 쓴다. 규칙(조회 키·단위·목록 밖 모델이면 undefined)은 R-62에 있고, 모델별 단가 숫자 전체는 코드(C-36)가 원본이며 이 스펙은 복사하지 않는다.
  - Nunjucks 문자열 렌더링 `renderVarsInObject(obj, vars)`: 객체의 모든 문자열 값을 재귀적으로 렌더한다. `vars`가 없거나 `PROMPTFOO_DISABLE_TEMPLATING`이면 그대로 돌려준다.
  - 평가기의 단계 타임아웃(`evaluateOptions.timeoutMs` 또는 `PROMPTFOO_EVAL_TIMEOUT_MS`, 기본 0 = 없음)과 취소 신호 생성: eval-run 소관이다. 이 provider들은 취소 신호만 받는다(R-30).
- 소유 상태·부작용:
  - Claude: 호출마다 SDK 서브프로세스, 임시 디렉터리(`working_dir`가 없을 때), 세션 파일(SDK가 `persist_session` 기본 true로 디스크에 저장, SDK 쪽이라 `미확인`). provider 인스턴스 안의 상태는 SDK 모듈 참조와 캐시 범위 UUID뿐이다.
  - OpenCode: 인스턴스가 소유하는 서버 프로세스·클라이언트·세션 맵(최대 100개, 오래된 것부터 삭제)·세션별 직렬화 큐. `cleanup()`이 세션과 서버를 정리한다.
  - Codex SDK: 인스턴스별 Codex 객체 맵·스레드 맵·직렬화 큐(`cleanup()`에서 정리). Codex 쪽 스레드는 `~/.codex/sessions`에 남는다(소스 주석, `미확인`).
  - Codex app-server: 연결 키별 자식 프로세스(`reuse_server` 기본 true면 재사용)·스레드 맵. `cleanup()`이 연결을 닫는다.
  - 평가기가 만드는 `copy_working_dir` 워크스페이스(R-52, R-53)와 에이전트가 `working_dir`에 쓰는 파일(R-51)은 이 기능의 부작용이다.

### 1.3 인터페이스와 데이터 의미 [필수]

옵션 이름은 YAML 설정 키 그대로다. 표의 "미설정 시"는 promptfoo가 정한 값이며, "SDK 기본"은 promptfoo가 값을 넘기지 않아 SDK가 정한다는 뜻이다(내용은 `미확인`). 모든 옵션은 provider 구성(`providers[].config`)과 프롬프트·테스트 수준 구성에서 쓸 수 있고 후자가 이긴다(R-06). 타입 선언이 가장 정확한 옵션 목록은 C-01(Claude), C-15(OpenCode), C-22(Codex SDK), C-27(app-server)이다.

**표 1-A. id 접두어**

| 접두어(경로) | 클래스 | `id()` | 모델 지정 | 외부 의존 |
|---|---|---|---|---|
| `anthropic:claude-agent-sdk`, `anthropic:claude-code` (뒤에 무엇이 붙어도 일치) | `ClaudeCodeSDKProvider` | `options.id`, 없으면 `anthropic:claude-agent-sdk` | `config.model`만 | `@anthropic-ai/claude-agent-sdk` |
| `opencode`, `opencode:<접미어>` | `OpenCodeSDKProvider` | `options.id`, 없으면 경로 원문 | `config.provider_id`+`config.model`, 없으면 OpenCode 기본 | `@opencode-ai/sdk`, `opencode` CLI |
| `openai:codex-sdk[:<모델>]`, `openai:codex[:<모델>]` | `OpenAICodexSDKProvider` | `options.id`, 없으면 경로 원문 | 경로의 모델 > `config.model` > SDK 기본 | `@openai/codex-sdk` |
| `openai:codex-app-server[:<모델>]`, `openai:codex-desktop[:<모델>]` | `OpenAICodexAppServerProvider` | 〃 | 〃 | `codex` 실행파일 |

**표 1-B. Claude Agent SDK 옵션 (평가 영향)**

| 옵션 | 타입 | 미설정 시 | 평가 영향 · 잘못된 값 처리 |
|---|---|---|---|
| `model` | string | SDK 기본 | 그대로 전달. 알려진 모델명이나 별칭(`default, best, fable, fable[1m], sonnet, opus, haiku, sonnet[1m], opus[1m], opusplan, opusplan[1m]`)이 아니면 경고만 남기고 진행 |
| `fallback_model` | string(쉼표 목록) | SDK 기본 | 항목마다 위와 같이 경고만 |
| `max_turns`, `max_thinking_tokens`, `thinking`, `effort`, `betas` | number / object / string / list | SDK 기본 | promptfoo 검증 없이 전달. 한도를 넘으면 SDK가 비성공 `result`를 낸다(R-26) |
| `max_budget_usd` | number | 없음 | 세션 비용 상한. 전달만 하고 초과 시 SDK가 종료한다(소스 주석 `error_max_budget_usd`, SDK 쪽) |
| `task_budget` | `{total: number}` | 없음 | 토큰 예산(도구 사용 속도 조절). 전달만 |
| `working_dir` | string | 빈 임시 디렉터리 | R-10. 상대 경로는 설정 파일 디렉터리 기준(R-07) |
| `copy_working_dir` | `true\|false\|'git'\|'copy'` | false | 호출마다 `working_dir` 복사본에서 실행(R-52) |
| `additional_directories` | string[] | 없음 | 절대화해 전달. 에이전트가 접근할 수 있는 추가 디렉터리 |
| `tools` | string[] 또는 `{type:'preset', preset:'claude_code'}` | R-12가 계산 | 사용 가능 도구 집합. 그 밖의 값이면 throw `tools must be an array of tool-name strings or the claude_code preset` |
| `custom_allowed_tools` | string[] | 없음 | 기본 허용 목록을 대체(R-11). 문자열 배열이 아니면 throw |
| `append_allowed_tools` | string[] | 없음 | 기본 허용 목록에 추가. 배열이 아니면 throw |
| `allow_all_tools` | boolean | false | `tools`를 Claude Code 프리셋으로(R-12). boolean이 아니면 throw |
| `disallowed_tools` | string[] | 없음 | 정렬·중복 제거해 `disallowedTools`로 전달(항상 허용보다 우선, SDK 쪽) |
| `permission_mode` | `default\|manual\|plan\|acceptEdits\|bypassPermissions\|dontAsk\|auto` | `default` | R-14. 다른 값이면 throw `permission_mode must be one of ...` |
| `allow_dangerously_skip_permissions` | boolean | 없음 | `bypassPermissions`에 필수. boolean이 아니면 throw |
| `sandbox`, `permission_prompt_tool_name`, `plan_mode_instructions` | object / string / string | 없음 | 전달만 |
| `can_use_tool`, `on_elicitation`, `hooks`, `spawn_claude_code_process`, `stderr` | 함수·객체 | 없음 | 프로그램 API 전용(YAML로 못 씀). 앞의 넷은 캐시를 우회한다 |
| `ask_user_question` | `{behavior?: 'first_option'\|'random'\|'deny'}` | 없음 | AskUserQuestion 자동 응답(R-20). 객체가 아니거나 `behavior`가 세 값이 아니면 throw |
| `setting_sources` | `('user'\|'project'\|'local')[]` | `[]`(아무 설정도 읽지 않음) | R-15 |
| `skills` | string[] 또는 `'all'` | 없음(SDK 쪽 필터 없음, "스킬 끔"이 아님) | R-15 |
| `plugins` | `{type:'local', path}[]` | 없음 | R-15 |
| `agents`, `agent` | map / string | 없음 | 서브에이전트 정의·메인 스레드 에이전트. `agents`가 비어 있지 않으면 사용 가능 도구에 `Task`가 들어간다 |
| `mcp` | `{enabled?, server?, servers?[], ...}` | 없음 | R-16 |
| `strict_mcp_config` | boolean | true | 명시한 MCP 서버만 허용 |
| `cache_mcp` | boolean | false | MCP가 있어도 캐시 허용(캐시 스펙) |
| `custom_system_prompt` | string | 없음 | R-17 |
| `append_system_prompt`, `exclude_dynamic_sections` | string / boolean | 없음 | 기본 시스템 프롬프트(`claude_code` 프리셋)에 덧붙임 / 사용자별 동적 구간 제거 |
| `output_format` | `{type:'json_schema', schema, ...}` | 없음 | 구조화 출력(R-25) |
| `resume`, `continue`, `fork_session`, `resume_session_at`, `session_id`, `persist_session`, `title` | string / boolean | SDK 기본 | R-19 |
| `apiKey`, `apiKeyRequired` | string / boolean | env `ANTHROPIC_API_KEY` / true | R-21 |
| `env` | `map<string,string>` | 없음 | 서브프로세스 환경 추가(R-21) |
| `max_subagent_spawn_depth`, `max_concurrent_subagents` | 양의 정수 | 5(환경변수 기본) / SDK 기본 | 양의 안전 정수가 아니면 throw `<옵션> must be a positive safe integer` |
| `executable`, `executable_args`, `extra_args`, `path_to_claude_code_executable` | string / list / map / path | SDK 기본 | R-22 |
| 그 밖 통과 | — | SDK 기본 | `settings`, `managed_settings`, `enable_file_checkpointing`, `include_partial_messages`, `include_hook_events`, `forward_subagent_text`, `tool_config`, `prompt_suggestions`, `agent_progress_summaries`, `debug`, `debug_file`, `deep_tracing` |

**표 1-C. OpenCode SDK 옵션**

| 옵션 | 타입 | 미설정 시 | 평가 영향 · 잘못된 값 처리 |
|---|---|---|---|
| `provider_id`, `model` | string | OpenCode 설정의 기본 모델 | 둘 중 하나라도 있으면 prompt에 `model:{providerID, modelID}`를 싣는다. 한쪽만 있으면 나머지는 빈 문자열 |
| `apiKey` | string | env(`provider_id`별 → `ANTHROPIC_API_KEY` → `OPENAI_API_KEY`) | `provider_id`가 있으면 spawn하는 서버 설정에 주입. 프롬프트 수준 변경 불가(throw) |
| `baseUrl` | string | 서버 직접 기동 | 기존 서버에 접속. `hostname`·`port`·`timeout`·`log_level`·`mcp`·`custom_agent`·`apiKey`는 무시(경고). 프롬프트 수준 변경 불가(throw) |
| `hostname`, `port`, `timeout`, `log_level` | string / number / number / string | `127.0.0.1`, 0(임의), 30000(서버 기동 제한 ms), 없음 | `timeout`은 서버 기동 제한이지 호출 제한이 아니다 |
| `working_dir` | string | 임시 디렉터리를 만들지만 서버에는 넘기지 않음(R-38) | 세션 쿼리 `directory` |
| `copy_working_dir` | `true\|false\|'git'\|'copy'` | false | R-52 |
| `workspace` | string | 없음 | `baseUrl` 또는 `working_dir` 없이 쓰면 throw |
| `tools` | `map<tool, boolean>` | R-34 | 객체·boolean이 아니거나 빈 이름이면 `{error}` |
| `permission` | `map<tool, ask\|allow\|deny \| map<glob, ...>>` | 없음 | 형식이 틀리면 `{error}` |
| `agent`, `custom_agent`, `variant`, `format` | string / object / string / object | 없음 | 에이전트·모델 변형·출력 형식. `custom_agent`는 서버를 직접 띄울 때만 적용 |
| `session_id`, `parent_session_id`, `persist_sessions` | string / string / boolean | 새 세션, 없음, false | R-35 |
| `restart_server_per_call` | boolean | false | R-35. 프롬프트 수준 변경 불가 |
| `mcp` | `map<name, {type:'local'\|'remote', ...}>` | 없음 | 서버 설정으로 전달 |
| `cache_mcp` | boolean | false | 캐시 스펙 |
| `max_retries` | number | — | 선언만 있고 코드 어디서도 읽지 않는다(효과 없음) |
| `enable_streaming` | boolean | — | 효과 없음(경고 1회) |

**표 1-D. Codex SDK 옵션** (provider 구성은 엄격 검증: 목록에 없는 키는 생성 시 오류, R-40)

| 옵션 | 타입 | 미설정 시 | 평가 영향 |
|---|---|---|---|
| `model`, `model_provider`, `model_reasoning_effort` | string / string / `minimal\|low\|medium\|high\|xhigh\|max\|ultra` | SDK 기본 | 스레드 옵션·CLI 설정으로 전달. 알려진 OpenAI 모델이 아니면 경고만(`model_provider`가 openai가 아닐 때는 경고 없음) |
| `working_dir` | string(비어 있지 않음) | `process.cwd()` | R-42 |
| `copy_working_dir` | `true\|false\|'git'\|'copy'` | false | R-52 |
| `additional_directories` | string[] | 없음 | `--add-dir` 상당 |
| `skip_git_repo_check` | boolean | false | Git 저장소 요건(R-42) |
| `sandbox_mode` | `read-only\|workspace-write\|danger-full-access` | 값을 넘기지 않음(SDK 기본, 문서는 `workspace-write`라 쓰나 `미확인`) | 파일 시스템 접근 수준 |
| `approval_policy` | `never\|on-request\|on-failure\|untrusted` | 값을 넘기지 않음(SDK 기본) | 승인 필요 시점 |
| `network_access_enabled`, `web_search_enabled`, `web_search_mode` | boolean / boolean / `disabled\|cached\|live` | 넘기지 않음 | `web_search_mode`가 있으면 `web_search_enabled`는 무시 |
| `collaboration_mode` | `coding\|plan` | 없음 | `cli_config.collaboration_mode`로 전달 |
| `thread_id`, `persist_threads`, `thread_pool_size` | string / boolean / 양의 정수 | 없음 / false / 1 | R-43 |
| `output_schema` | object | 없음 | 구조화 출력 스키마 |
| `cli_env`, `inherit_process_env` | map / boolean | 없음 / false | R-41 |
| `apiKey`, `base_url` | string | env `OPENAI_API_KEY`/`CODEX_API_KEY` | R-41 |
| `codex_path_override`, `skip_codex_version_check` | string / boolean | 번들 CLI / false | 지정한 바이너리는 SDK 버전과의 호환성을 사전 점검(건너뛰기 가능) |
| `cli_config` | object | 없음 | `--config key=value`로 펼쳐 전달(MCP 서버 등 promptfoo가 모르는 Codex 설정) |
| `enable_streaming`, `deep_tracing` | boolean | false | 스트리밍 이벤트 수집 여부 / 트레이싱(범위 밖) |
| `maxRetries` | 비음수 정수 | 스케줄러 기본 | 스케줄러가 읽음(R-45) |

**표 1-E. Codex app-server 옵션** (표 1-D와 같은 이름은 같은 뜻, 아래는 다른 것과 기본값만)

| 옵션 | 타입 | 미설정 시 | 평가 영향 |
|---|---|---|---|
| `sandbox_mode` | 〃 | `read-only` | thread/turn 파라미터로 항상 전달(R-48) |
| `approval_policy` | 위 4값 또는 `{granular:{sandbox_approval, rules, skill_approval, request_permissions, mcp_elicitations}}` | `never` | 〃 |
| `network_access_enabled` | boolean | false | turn `sandboxPolicy.networkAccess` |
| `sandbox_policy` | object | 없음 | `sandbox_mode`에서 만든 정책을 통째로 대체 |
| `ephemeral`, `thread_cleanup` | boolean / `unsubscribe\|archive\|none` | true / `unsubscribe` | 스레드를 저장하지 않음 / 턴 뒤 정리 방식 |
| `reuse_server` | boolean | true | 같은 연결 키면 `codex app-server` 프로세스 재사용 |
| `request_timeout_ms`, `startup_timeout_ms`, `turn_timeout_ms` | 양의 정수 | 30000, 30000, 없음 | R-47 |
| `base_instructions`, `developer_instructions`, `personality`, `service_tier`, `reasoning_summary`, `approvals_reviewer`, `collaboration_mode`(객체) | string / enum | 없음 | thread/turn 파라미터 |
| `server_request_policy` | `{command_execution, file_change, permissions, user_input, mcp_elicitation, dynamic_tools}` | 안전한 거절 | R-49 |
| `include_raw_events`, `experimental_raw_events`, `experimental_api`, `persist_extended_history` | boolean | false, false, true(핸드셰이크), false | 응답 `raw`에 알림 포함 / 프로토콜 기능 |
| `copy_working_dir` | — | 구성 스키마에 없음 | 지원하지 않음(R-52) |

**표 1-F. `ProviderResponse` 채우기 (성공 응답)**

| 필드 | Claude | OpenCode | Codex SDK | Codex app-server |
|---|---|---|---|---|
| `output` | 구조화 출력이 있으면 그 값(객체), 없으면 `result` 문자열 | 최종 응답의 `text` 부분을 줄바꿈으로 이은 문자열. `format.type: json_schema`면 JSON 문자열 | `turn.finalResponse` 또는 `''`(문자열) | 마지막 `agentMessage` 항목 텍스트(R-50) |
| `tokenUsage` | 모델별 사용량 합산(R-27), 없으면 `{}` | 어시스턴트 메시지 `tokens`(R-36), 없으면 undefined | `turn.usage`(R-44), 없으면 undefined | 마지막 `thread/tokenUsage/updated`(R-50) |
| `cost` | SDK가 준 `total_cost_usd`(재개 세션은 차감) | 어시스턴트 메시지 `cost`(있을 때만) | 가격표 환산(R-62) | 가격표 환산(R-62) |
| `raw` | 최종 `result` 메시지 JSON | 프롬프트 응답 전체 JSON | `turn` JSON | 스레드·턴·항목·사용량 JSON |
| `sessionId` | `result.session_id` | 세션 id | `thread.id` 또는 `'unknown'` | 스레드 id |
| `metadata` | `skillCalls`, `toolCalls`, `numTurns`, `durationMs`, `durationApiMs`, `modelUsage`, `permissionDenials`, `terminalReason`, `structuredOutput`, `apiErrorStatus`, `assistantErrors`, 재개 세션이면 `usageAccounting`·`sessionCost`·`sessionModelUsage` | 스킬 호출이 있을 때만 `{skillCalls}` | 스킬 필드만(`skillCalls`, 필요 시 `attemptedSkillCalls`), 없으면 undefined | `codexAppServer{threadId, turnId, model, modelProvider, cwd, sandboxMode, approvalPolicy, itemCounts, items, serverRequests, notificationCount}` + 스킬 필드 |
| 평가기가 더하는 것 | `copy_working_dir`면 `metadata.workingDir`(복사본 경로)와 git 복사본이면 `metadata.workspaceDiff` (R-53) | 〃 | 〃 | — (app-server는 대상 provider로 지원 안 함) |

실패 응답은 `{error: string}`이 기본이다. Claude의 비성공 `result`만 `tokenUsage`·`cost`·`raw`·`sessionId`·`metadata`를 함께 돌려준다(R-26). 나머지 provider의 실패 응답에는 사용량·메타데이터가 없다(R-37, R-45, R-50).

**표 1-G. 토큰·비용 요약** (`TokenUsage` 필드 정의는 provider-contract C-05)

| provider | `prompt` | `completion` | `total` | `cached` | `completionDetails` | `cost` 출처 |
|---|---|---|---|---|---|---|
| Claude | Σ(input + cacheRead + cacheCreation) | Σ output(추론 토큰 포함) | prompt + completion | 설정 안 함 | `reasoning`(추론 토큰이 보고될 때), `cacheReadInputTokens`, `cacheCreationInputTokens`(둘 중 하나가 0보다 크거나 추론이 있을 때만) | SDK 보고값 |
| OpenCode | `input` | `output` | `total` 또는 input+output | `cache.read`(`cache`가 있을 때) | `reasoning`, `cacheReadInputTokens`, `cacheCreationInputTokens` | 메시지 `cost`(있을 때) |
| Codex SDK | `input_tokens`(캐시 포함) | `output_tokens` | input+output | `cached_input_tokens \|\| 0` | `reasoning`, `cacheCreationInputTokens`(숫자로 보고될 때) | 가격표 추정, 모델 미지정이면 undefined |
| app-server | 〃(`last ?? total ?? 원본`) | 〃 | 〃 | 〃 | `cacheCreationInputTokens`(숫자일 때) | 가격표 환산(R-62), `config.model` 없으면 undefined |

**표 1-H. 안전 기본값** (R-51, R-54)

| | Claude | OpenCode | Codex SDK | Codex app-server |
|---|---|---|---|---|
| `working_dir` 없음 | 빈 임시 디렉터리, 도구 없음 | 임시 디렉터리를 만들지만 서버에 넘기지 않음, 도구 전부 거부 | `process.cwd()`(Git 저장소 요건) | `process.cwd()`(Git 저장소 요건) |
| `working_dir` 있음, 도구 미지정 | 읽기 전용 `Read, Grep, Glob, LS`만 사용 가능 | 읽기 전용 `glob, grep, list, read`만 허용, 나머지 거부 | 샌드박스는 SDK 기본(미확인) | `read-only` 샌드박스, 승인 `never`, 네트워크 없음 |
| 쓰기·셸 허용 방법 | `append_allowed_tools`/`custom_allowed_tools`/`tools`/`allow_all_tools` + `permission_mode` | `tools.edit`·`tools.bash` 등 + `permission` | `sandbox_mode: workspace-write` 이상 | `sandbox_mode`, `approval_policy`, `server_request_policy` |
| 서브프로세스 환경 | 프로세스 환경 전체 + `config.env` + provider env | 서버가 프로세스 환경 전체 + provider env를 상속 | 최소 목록 + `cli_env`(`inherit_process_env`로 전체) | 〃 |
| 격리 옵션 | `copy_working_dir` | `copy_working_dir` | `copy_working_dir` | 없음 |

**표 1-I. provider별 응답 캐시 사용 여부** (규칙은 response-cache 링크)

| provider | 응답 캐시 | 키 접두어 | 근거 |
|---|---|---|---|
| Claude Agent SDK | 사용 | `anthropic:claude-agent-sdk` | 키 재료·우회·지문·인스턴스 범위: response-cache R-20~R-25 |
| OpenCode SDK | 사용 | `opencode:sdk` | response-cache R-26 |
| Codex SDK | 없음 | — | response-cache R-27. `cacheKey`는 스레드 풀 키일 뿐이다 |
| Codex app-server | 없음 | — | response-cache R-27 |

스킬 노출 설정이 SDK로 가는 경로는 R-55~R-58에 있다.

### 1.4 행동 규칙과 남은 질문 [필수]

검증 수준은 `코드 확인`(구현부를 직접 읽음), `추론`, `미확인`(외부 SDK·문서만 근거)이며 이번 분석은 실행하지 않았으므로 `실행 확인`은 없다.

**A. 식별·로딩**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | provider 경로가 `anthropic:claude-agent-sdk` 또는 `anthropic:claude-code`로 시작 | 일반 `anthropic:` factory보다 앞선 factory가 `ClaudeCodeSDKProvider`를 만든다. `create`는 경로 문자열을 읽지 않고 `providerOptions`만 넘기므로 접미어(예: `anthropic:claude-code:sonnet`)는 모델이 아니다. 모델은 `config.model`로만 정한다. `id()`는 `options.id`가 있으면 그 값, 없으면(문자열 항목이면 항상) `anthropic:claude-agent-sdk`다 | 코드 확인 |
| R-02 | 경로가 `opencode`이거나 `opencode:`로 시작 | `OpenCodeSDKProvider`를 만들고 `id()`는 `options.id ?? 경로 원문`이다. 접미어는 의미가 없고 모델은 `config.provider_id`·`config.model`로만 정한다 | 코드 확인 |
| R-03 | 경로가 `openai:<type>[:<모델>]`, type이 `codex-sdk`·`codex`(SDK) 또는 `codex-app-server`·`codex-desktop`(app-server) | 모델은 경로 세 번째 부분 이후를 `:`로 다시 이은 값이고, 경로 모델이 `config.model`보다 우선한다(둘 다 없으면 SDK 기본). `id()`는 `options.id ?? 경로 원문`이다. `openai:codex-security`는 먼저 걸리는 별도 factory다. 생성 시 모델-엔드포인트 호환 검사는 다음 조건이 모두 맞을 때만 실행된다: type이 위 Codex 4종, `model_provider`(없으면 `cli_config.model_provider`)가 문자열 `'openai'`와 정확히 같음, `base_url`(없으면 `cli_config.openai_base_url`)이 비어 있지 않은 문자열이고 호스트가 OpenAI 공식 호스트(`api.openai.com`과 `us\|eu\|au\|ca\|jp\|in\|sg\|kr\|gb\|ae.api.openai.com`, URL이 파싱되지 않으면 공식이 아님). 검사 대상은 `경로 모델 \|\| config.model`(없거나 문자열이 아니면 통과)의 마지막 `/` 뒤 이름이고, `gpt-live-transcribe` 또는 `gpt-live-transcribe-*`면 `OpenAI model "gpt-live-transcribe" requires Realtime transcription sessions, which are not yet supported by promptfoo.`, 그 밖의 `gpt-live-*`면 `Use openai:live:<모델> for GPT-Live sessions.`, `gpt-transcribe`면 `OpenAI model "gpt-transcribe" is transcription-only. Use openai:transcription:gpt-transcribe (or bare openai:gpt-transcribe).`를 throw해 provider 로드가 실패한다. 일반 `openai:` API 경로의 폐기 모델·Codex 전용 모델 거부(`assertOpenAiApiModel`)는 Codex 경로에 적용되지 않는다 | 코드 확인 |
| R-04 | 첫 호출 때 외부 SDK 로드 | Claude: `cliState.basePath`(절대일 때)·`process.cwd()`·promptfoo 설치 위치 상위 2곳에서 패키지를 찾고, 없으면 설치 안내 오류, 버전이 `^0.3.273` 밖이면 버전 불일치 오류다. OpenCode: `@opencode-ai/sdk/v2` → `@opencode-ai/sdk`(v1) 순으로 import하고 둘 다 실패하면 설치 안내 오류다(v1/v2에 따라 세션 API 모양이 달라진다). Codex SDK: `@openai/codex-sdk`가 `^0.156.1`이어야 하고 아니면 오류다. app-server: 패키지가 필요 없고 `codex`(또는 `codex_path_override`)를 자식 프로세스로 띄운다. 로드 오류는 모두 `{error}`로 반환된다 | 코드 확인 |
| R-05 | API 키 요건 | Claude·Codex SDK·app-server는 `requiresApiKey()`가 false라 평가 시작 전 키 점검에서 빠진다. Claude는 호출 안에서 `config.apiKey \|\| env`가 없고 `apiKeyRequired`가 false도 아니고 Bedrock·Vertex 환경변수도 없으면 `Anthropic API key is not set...`를 throw한다. Codex는 키가 없으면 Codex 로그인 상태에 맡긴다. OpenCode는 `requiresApiKey`가 없어, CLI `eval`의 사전 점검이 `getApiKey()`가 빈 값이면 `Missing required API keys: OPENCODE_API_KEY (...)`로 평가를 거부한다. `provider_id`별 env → `ANTHROPIC_API_KEY` → `OPENAI_API_KEY` 순으로 찾으며, `config.apiKeyRequired: false`(타입에는 없지만 점검이 읽음)로 건너뛸 수 있다 | 코드 확인 |

**B. 구성 병합·전달 (공통)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | `callApi`의 유효 구성 | `{...this.config, ...context.prompt.config}`를 얕게 합친다(뒤가 이긴다). `context.prompt.config`는 평가기가 프롬프트 config와 테스트 `options`(`repeat` 제외)를 합친 값이고, 워크스페이스가 있으면 `working_dir`가 복사본 경로다. Codex 두 provider는 추가로 합성 후 `provider` 키를 지우고 `renderVarsInObject(config, vars)`로 모든 문자열을 Nunjucks 렌더한다(app-server는 `cli_config`·`cli_env`·`server_request_policy`(그 안 `permissions`·`dynamic_tools`)를 한 단계 깊게 합친다). 렌더 예외는 try 밖이라 throw로 전파된다. Claude·OpenCode는 구성 문자열을 vars로 렌더하지 않는다(로드 시점 `{{ env.* }}`만 렌더됨, provider-contract R-14). 알 수 없는 키는 Claude·OpenCode에서는 조용히 무시되고, Codex 두 provider는 provider 구성이면 오류, 프롬프트 병합 구성이면 버린다(R-40, R-46) | 코드 확인 |
| R-07 | 상대 경로 해석 | 기준은 `cliState.basePath`(설정 파일 디렉터리, 절대화), 없으면 `process.cwd()`이고 이미 절대 경로면 그대로 쓴다(`safeResolve`). 적용 대상: 모든 provider의 `working_dir`; Claude의 `additional_directories`·`plugins[].path`·`settings`(문자열일 때)·`debug_file`·`path_to_claude_code_executable`; Codex SDK의 `additional_directories`. app-server는 기준이 `config.basePath \|\| cliState.basePath \|\| process.cwd()`이고 `additional_directories`는 `path.resolve`로 푼다. `working_dir`를 생략한 Codex 두 provider는 `process.cwd()`다 | 코드 확인 |
| R-08 | 오류가 호출자에게 가는 방식 | 구성 검증·작업 디렉터리 확인 단계는 `callApi`가 throw하고 평가기가 그 행을 ERROR(스택 포함)로 만든다(provider-contract R-03③): Claude의 옵션 검증·키 부재·`working_dir` 부재·`copy_working_dir` 오용, OpenCode의 `prepareCall`(`copy_working_dir` 오용, `apiKey`·`baseUrl`·`restart_server_per_call` 프롬프트별 변경, `workspace` 요건, `working_dir` 검증), Codex SDK의 `copy_working_dir` 오용·렌더 예외. 그 이후 SDK 실행 단계의 오류는 `{error}`로 반환된다. Codex 두 provider의 생성자는 엄격 스키마 위반이면 provider 로드 단계에서 throw한다 | 코드 확인 |
| R-09 | prompt를 SDK 입력으로 | Claude: 렌더된 문자열을 그대로 `query({prompt})`에 넘긴다(JSON을 해석하지 않는다). OpenCode: `parts: [{type:'text', text: prompt}]`. Codex SDK: 문자열이 JSON 배열이고 모든 원소가 키가 정확히 2개인 `{type:'text', text}` 또는 `{type:'local_image', path}`이면 배열 입력, 아니면 문자열 그대로. app-server: JSON 배열이고 모든 원소가 `text`·`image`(url)·`local_image`/`localImage`(path)·`skill`(name, path)·`mention`(name, path)이면 입력 항목으로 정규화하고, 하나라도 아니면 전체를 단일 `text`로 보낸다 | 코드 확인 |

**C. Claude Agent SDK: 옵션 → SDK 전달**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-10 | 작업 디렉터리 | `working_dir`가 있으면 R-07로 절대화해 SDK `cwd`로 쓴다. 호출 안에서 존재하고 디렉터리인지 확인하며 아니면 throw한다(캐시 조회 뒤). 없으면 `os.tmpdir()/promptfoo-claude-agent-sdk-*`에 빈 디렉터리를 만들어 `cwd`로 쓰고 호출이 끝나면(성공·실패·중단 모두) 지운다. 캐시 히트면 디렉터리를 만들지 않는다 | 코드 확인 |
| R-11 | 도구 허용 목록(`allowedTools`) | 기본은 `working_dir`가 있으면 `[Glob, Grep, LS, Read]`(정렬), 없으면 `[]`다. `allow_all_tools: true`면 `undefined`(허용 목록 없음)이다. `custom_allowed_tools`가 키로 있으면(값이 `undefined`여도) 그 목록으로 대체하고, `append_allowed_tools`가 있으면 기본에 더한다. 결과는 중복 제거·정렬한다. `ask_user_question`이 있으면 `AskUserQuestion`을 허용 목록에서 뺀다. `disallowed_tools`는 중복 제거·정렬해 `disallowedTools`로 넘긴다 | 코드 확인 |
| R-12 | 사용 가능 도구 집합(`tools`) | `config.tools`가 있으면 그대로(권위 있는 목록)다. 없으면 `allow_all_tools: true`일 때 `{type:'preset', preset:'claude_code'}`이고, 아니면 허용 목록에 (`ask_user_question`이면 `AskUserQuestion`)(`skills`가 `'all'`이거나 비어 있지 않은 배열이면 `Skill`)(`agents`가 비어 있지 않으면 `Task`)(`permission_mode: plan`이면 `ExitPlanMode`)를 더해 정렬한 배열이다. 따라서 기본 상태에서는 Bash·Write·Edit가 권한이 아니라 가용성 단계에서 아예 없다. 명시한 `tools`가 `Skill`을 빼면 `skills`를 줘도 `Skill`이 자동으로 더해지지 않는다 | 코드 확인 |
| R-13 | 도구·정책 옵션 검증 | 다음은 throw한다: `allow_all_tools`·`allow_dangerously_skip_permissions`가 boolean이 아님; `custom_allowed_tools`·`append_allowed_tools`·`disallowed_tools`가 문자열 배열이 아님; `permission_mode`가 7값(`default, plan, acceptEdits, bypassPermissions, dontAsk, auto, manual`)이 아님; `tools` 형식 위반; `extra_args`가 문자열·null 값의 객체가 아니거나 예약 이름(C-02의 24개, 정규화 비교)을 포함; `allow_all_tools: true`와 `tools`·`custom_allowed_tools`·`append_allowed_tools` 동시(`Cannot specify allow_all_tools together with ...`); `custom_allowed_tools`와 `append_allowed_tools` 동시(`Cannot specify both custom_allowed_tools and append_allowed_tools`); `ask_user_question`·`mcp` 형식 위반(R-16, R-20). `custom_allowed_tools`·`append_allowed_tools` 충돌 검사는 키 존재(`in`) 기준이다 | 코드 확인 |
| R-14 | `permission_mode` | 미지정이면 `default`를 명시해 넘긴다(SDK가 생략 시 자동 모드를 고를 수 있어서, 소스 주석). `manual`은 `default`로 바꿔 넘긴다. `bypassPermissions`는 `allow_dangerously_skip_permissions === true`가 없으면 `permission_mode 'bypassPermissions' requires allow_dangerously_skip_permissions: true as a safety measure`를 throw한다. 각 모드가 실제로 무엇을 허용하는지는 SDK 쪽이다 | 코드 확인(전달) / 미확인(SDK 판단) |
| R-15 | 스킬·설정·플러그인 전달 | `setting_sources`는 `config.setting_sources ?? []`로 넘겨 기본에서는 어떤 설정 원천도 읽지 않게 한다. `skills`는 값 그대로(`'all'`·이름 배열·미지정) 넘기고, 위 R-12의 `Skill` 도구 추가 외에 promptfoo가 하는 일은 없다. `plugins[]`는 `{...plugin, path: safeResolve(basePath, plugin.path)}`로 경로만 절대화해 넘긴다. 세 옵션 모두 값·경로의 존재나 형식을 검증하지 않고, promptfoo는 `SKILL.md`나 플러그인 파일을 열지 않는다. 스킬 발견·필터링·로딩은 SDK 쪽이다. 소스 주석은 `skills`를 "발견된 스킬을 좁히는 컨텍스트 필터, 샌드박스 아님"이고 새 스킬을 발견하지 않는다고 설명한다 | 코드 확인(전달) / 미확인(SDK 쪽 로딩) |
| R-16 | `mcp` | `mcp`가 있으면 zod 검증(`enabled` 기본 true, `server`·`servers[]` 각 항목은 `command` 또는 `path` 또는 `url` 중 하나 필수)한다. 형식 오류 `Claude Agent SDK MCP configuration is malformed: ...`, `tools`·비어 있지 않은 `exclude_tools`는 지원하지 않아 throw, 서버 이름(`name ?? url ?? command ?? 'default'`)이 SDK 정규화(`[^a-zA-Z0-9_-]`→`_`) 후 충돌하면 throw한다. `enabled: false`면 서버 없음이다. 변환: `url` → `{type:'http', url(+API 키 쿼리), headers(+인증 헤더)}`(OAuth는 호출 시 토큰 1회 발급), `command` → `{type:'stdio', command, args, env}`, `path` → `.py`는 `python3`(Windows `python`), 그 외는 `process.execPath`로 실행하는 stdio. `strict_mcp_config`는 기본 true로 넘긴다 | 코드 확인 |
| R-17 | 시스템 프롬프트·출력 형식 | `custom_system_prompt == null`이면 `{type:'preset', preset:'claude_code', append: append_system_prompt, snapshot:false}`(`exclude_dynamic_sections`가 참이면 `excludeDynamicSections: true` 추가), 아니면(빈 문자열 포함) `{type:'custom', prompt, snapshot:false}`다. `output_format`은 `outputFormat`으로 그대로 전달한다 | 코드 확인 |
| R-18 | 모델·턴·예산·사고·재시도 | `model`, `fallback_model`, `max_turns`, `max_thinking_tokens`, `thinking`, `effort`, `max_budget_usd`, `task_budget`, `betas`는 promptfoo 쪽 기본값·범위 검사 없이 SDK 옵션 이름(`model`, `fallbackModel`, `maxTurns`, ...)으로 전달한다. 모델·fallback 이름이 알려진 목록 밖이면 경고만 한다. 한도 초과의 결과(비성공 `result`)는 R-26이다. 기본 한도 값은 SDK 쪽(`미확인`) | 코드 확인(전달) / 미확인(SDK 기본) |
| R-19 | 세션 옵션 | `resume`, `continue`, `fork_session`, `resume_session_at`, `session_id`, `persist_session`, `title`, `enable_file_checkpointing`은 그대로 전달한다. `title`과 `resume`/`continue`를 같이 주면 경고만 한다(SDK가 저장된 제목을 쓴다). 응답 `sessionId`는 최종 `result.session_id`다. 재개·계속·분기 세션의 사용량 계산은 R-28이다 | 코드 확인 |
| R-20 | `ask_user_question`·훅·서브에이전트 전사 가림 (조건 → 결과) | **A. 설정 검증** `ask_user_question`이 있으면(키가 `undefined`가 아닐 때) 객체여야 하고(배열·null 포함 아니면 throw `ask_user_question must be an object`) `behavior`는 `first_option`·`random`·`deny`·생략 중 하나여야 한다(아니면 throw `ask_user_question.behavior must be first_option, random, or deny`). **B. 설정이 있으면 생기는 효과** `AskUserQuestion`이 허용 목록에서 빠지고(R-11) 사용 가능 도구에 들어가며(R-12), SDK `canUseTool`은 아래 C의 판정 함수(사용자 `can_use_tool`을 감쌈)로 바뀐다. `behavior: random`이면 캐시를 우회한다. `permission_mode`가 `dontAsk`면 SDK가 이 도구를 `canUseTool` 이전에 거부하므로 같은 판정을 `PreToolUse` 훅(matcher `AskUserQuestion`)으로 한 번 더 건다. **C. 판정 함수** 도구 이름이 `AskUserQuestion`이 아니면: 사용자 `can_use_tool`이 있으면 그 결과를 그대로, 없으면 `{behavior:'deny', message:'Tool permission request is not handled by ask_user_question automation'}`(다른 도구를 넓게 허용하지 않음). 이름이 `AskUserQuestion`이면: `behavior`가 `deny`면 `{deny, 'AskUserQuestion is disabled in automated evaluation mode'}`; 입력이 `questions` 배열이 아니거나 어떤 질문이 `question`(string)·`header`(string)·`multiSelect`(boolean)·`options`(각 원소가 `label`·`description` 문자열인 배열)를 못 갖추면 `{deny, 'AskUserQuestion received malformed question input'}`; 그 밖에는 `{behavior:'allow', updatedInput:{questions: 원본 그대로, answers}}`이고 `answers[질문 문장]`은 `first_option`(기본)이면 `options[0].label`, `random`이면 `Math.random`으로 고른 한 선택지의 `label`이다. `options`가 비었거나 없는 질문은 `answers`에 넣지 않는다(다중 선택 질문도 선택지 하나만 답한다). **D. 훅 판정** `dontAsk` 훅은 이벤트가 `PreToolUse`이고 도구가 `AskUserQuestion`일 때만 C(사용자 콜백 없이)를 실행한다. 결과가 `allow`가 아니면(결정이 없는 `null` 포함) `permissionDecision:'deny'`와 사유(`message` 또는 `ask_user_question automation returned no decision`), `allow`면 `permissionDecision:'allow'`와 `updatedInput`을 돌려준다. 다른 이벤트·도구면 `{}`. **E. 훅 순서** promptfoo가 만든 훅은 항상 같은 이벤트의 사용자 훅보다 앞에 놓이고(`PreToolUse`: AskUserQuestion 훅, `PostToolUse`: 전사 가림 훅) 사용자의 명시 거부가 이긴다(소스 주석, 판단은 SDK 쪽). `config.hooks`가 하나라도 있으면 캐시를 우회한다. **F. 전사 가림** `forward_subagent_text`가 거짓(기본)이면 `PostToolUse`(matcher `TaskOutput`) 훅이 붙는다. 이 훅은 이벤트가 `PostToolUse`이고 도구가 `TaskOutput`이며 `tool_response`가 "원시 서브에이전트 전사"일 때만 `updatedToolOutput`으로 가린 사본을 돌려주고 아니면 `{}`다. "원시 전사" 판정: 값이 비null 객체이고, `content`와 `_meta`를 모두 가졌으면 `content`만 같은 규칙으로 재귀 판정하며, 아니면 `isRawTranscript === true` 또는 `task.isRawTranscript === true`(`task`가 객체일 때)이면 참이다. 가리기: `content`+`_meta` 구조면 `content`만 재귀로 가리고, 아니면 대상(`task` 객체가 있으면 그것, 없으면 값 자체)에 `output = '[Subagent transcript omitted; set forward_subagent_text: true to include it]'`를 쓰고(`result` 키가 있으면 그것도 같은 문자열) `isRawTranscript: false`로 바꾼 사본이다. **G. 기록** 스트림에서 `TaskOutput`의 `tool_result`를 받을 때 `tool_use_result`가 원시 전사이고 `forward_subagent_text`가 거짓이면 `metadata.toolCalls`의 해당 `output`도 같은 문자열이다. `forward_subagent_text: true`면 SDK 옵션 `forwardSubagentText`로 전달돼 SDK가 서브에이전트 텍스트를 스트림에 싣는다(SDK 쪽). 사용자 `hooks`는 위 훅 뒤에 그대로 전달된다. 재개 세션이면 `UserPromptSubmit` 훅이 맨 앞에 하나 더 붙는다(R-28) | 코드 확인 |
| R-21 | 서브프로세스 환경·키 | 환경은 프로세스 환경 < `config.env` < provider env 덮어쓰기(`this.env`) 순으로 합친다(키 정렬). 그 위에 `ANTHROPIC_API_KEY = config.apiKey \|\| provider apiKey`를 쓴다(있을 때). `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`는 `max_subagent_spawn_depth`(양의 안전 정수 아니면 throw)가 있으면 그 값, 아니면 환경에 없을 때만 `'5'`다. `max_concurrent_subagents`는 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`로 간다. `allow_all_tools`면 `CLAUDE_CODE_ENABLE_TODO_TOOLS`를 없을 때 `'1'`로 둔다. `copy_working_dir` 워크스페이스에서 돌 때는 `GIT_DIR` 같은 저장소 선택 변수를 환경에서 지운다. SDK 호출용 `env`는 SDK 옵션 `env`로 전달한다 | 코드 확인 |
| R-22 | 통과 옵션과 알 수 없는 키 | `executable`, `executable_args`, `extra_args`(`--` 없는 이름→값, null은 플래그), `path_to_claude_code_executable`, `settings`, `managed_settings`, `sandbox`, `agents`, `agent`, `hooks`, `include_*`, `debug*` 등은 이름을 camelCase로 바꿔 전달한다(`C-05`가 매핑 전체). `ClaudeCodeOptions`에 없는 키는 오류 없이 무시된다(옵션은 명시 매핑으로만 SDK에 가므로) | 코드 확인 |

**D. Claude Agent SDK: 메시지 스트림 → 응답**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-23 | `query()`가 돌려준 스트림을 소비 | 비동기 반복으로 끝까지 읽는다. `assistant` 메시지: 턴 마커를 세고, 내용의 `tool_use` 블록마다 `toolCalls[block.id] = {id, name, input, output: undefined, is_error: false, parentToolUseId: msg.parent_tool_use_id}`를 등록하고, `msg.error`가 있으면 `assistantErrors`에 `{error, uuid, parentToolUseId, request_id?, subagent_type?, task_description?}`를 쌓는다. `user` 메시지: 내용의 `tool_result` 블록의 `tool_use_id`로 항목을 찾아 `output = block.content`(`TaskOutput`의 원시 서브에이전트 전사는 가림 문자열), `is_error = block.is_error ?? false`로 채운다. `result` 메시지: 후보로 저장한다. 그 밖의 메시지 종류는 무시한다. 스트림이 끝날 때 결과가 오지 않은 `tool_use`는 `output`이 `undefined`, `is_error`가 false인 채로 남는다 | 코드 확인 |
| R-24 | 최종 `result` 선택 | 후보 중 배경 서브에이전트 완료(`origin.kind === 'task-notification'`이되 `origin.subkind === 'scheduled-trigger'`가 아닌 것)가 아닌 마지막 것을 고르고, 그런 것이 없으면(구 SDK의 `origin` 없음 포함) 마지막 `result`를 고른다. `result`가 하나도 없으면 `{error: "Claude Agent SDK call didn't return a result"}`다(metadata 없음). 후보가 여러 개이고 `origin`이 없고 마지막이 `terminal_reason`이 없는 성공이면 스트림 절단 가능성 경고만 남긴다 | 코드 확인 |
| R-25 | 선택한 `result.subtype === 'success'` | `output = structured_output`이 `undefined`가 아니면 그 값(객체일 수 있다), 아니면 `result` 문자열. 응답은 `{output, tokenUsage, cost, raw: JSON.stringify(result), sessionId, metadata}`이고 `metadata`는 표 1-F의 필드(`skillCalls`, `toolCalls`, `numTurns`, `durationMs`, `durationApiMs`, `modelUsage`, `permissionDenials`, 있을 때만 `terminalReason`·`structuredOutput`·`apiErrorStatus`·`assistantErrors`, 재개 세션이면 `usageAccounting` 등)다. 이 응답만 캐시에 쓴다. `terminal_reason`이 `aborted_*`·`hook_stopped`여도 응답은 바뀌지 않고 트레이스 스팬만 오류로 표시한다 | 코드 확인 |
| R-26 | `result.subtype !== 'success'` (한도 초과·실행 오류 등) | `error`는 `Claude Agent SDK call failed: <subtype>`이고, 스트림에 어시스턴트 오류가 있었으면 마지막 오류 코드를 ` (<code>)`로 덧붙인다. `output`은 없고 `tokenUsage`·`cost`·`raw`·`sessionId`·`metadata`(`structuredOutput` 제외)는 성공과 같은 규칙으로 채운다. 캐시에 쓰지 않는다. 서브타입 문자열 집합은 SDK가 정한다(`error_max_turns`, `error_during_execution`, `error_max_budget_usd`는 소스 주석 인용, 전체 목록 `미확인`) | 코드 확인 / 미확인(서브타입 집합) |
| R-27 | 토큰 집계 (표 1-G) | 사용량 원천은 `result.modelUsage`(모델별 행, 서브에이전트 호출 포함)이고 비어 있을 때만 `result.usage`(메인 에이전트만)를 한 행으로 쓴다. 둘 다 없으면 `tokenUsage = {}`다(0으로 채우지 않는다). 행들을 합산해 `prompt = Σ(inputTokens + cacheReadInputTokens + cacheCreationInputTokens)`, `completion = Σ outputTokens`(추론 토큰은 여기 포함), `total = prompt + completion`이다. `completionDetails`는 추론 토큰이 보고됐거나 캐시 읽기·쓰기 합이 0보다 클 때만 `{reasoning?, cacheReadInputTokens, cacheCreationInputTokens}`로 붙인다. `cached`·`numRequests`는 채우지 않는다 | 코드 확인 |
| R-28 | 비용과 재개 세션 기준선 | 기본: `cost = max(0, result.total_cost_usd ?? 0)`다(값이 없으면 0이지 undefined가 아니다). `resume`·`continue`·`fork_session`(또는 `extra_args`의 `resume`/`r`/`continue`/`c`/`fork-session`)이면 SDK가 이전 세션 누계를 복원하므로, 첫 `UserPromptSubmit` 훅에서 SDK 실험 API로 세션 누계 스냅샷(제한 5초, 실패는 삼킴)을 기준선으로 잡고 모델별 사용량·비용에서 차감한다. 현재 값이 기준선보다 작으면(카운터 리셋) 기준선을 무시한다. 기준선을 못 잡으면 `tokenUsage = {}`, `cost = undefined`, `modelUsage` 없음, 경고 로그다. 이 경우 `metadata.usageAccounting`은 `'unavailable'`, 잡았으면 `'query'`이고 누계는 `metadata.sessionCost`·`sessionModelUsage`와 `raw`에 남는다. 비용이 undefined이면 `cost` 어서션은 `Cost assertion does not support providers that do not return cost`로 throw한다 | 코드 확인 |
| R-29 | `toolCalls`·`skillCalls`·`modelUsage` 노출 | `metadata.toolCalls`는 R-23 항목의 배열(삽입 순서)이다. `metadata.skillCalls`는 이 배열 중 `name === 'Skill'`만 변환한 것이며 규칙은 skill-calls-metadata R-02~R-04이다(성공·비성공 응답 모두에 실린다). 서브에이전트가 한 호출도 같은 배열에 들어간다(`parentToolUseId`로 구분만 가능) | 코드 확인 |

**E. 실패·중단·타임아웃**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-30 | 타임아웃의 소유 | 네 provider 모두 호출 전체에 대한 자체 타임아웃이 없다. 호출 시간의 상한은 평가기 단계 타임아웃(`evaluateOptions.timeoutMs` 또는 `PROMPTFOO_EVAL_TIMEOUT_MS`, 기본 0 = 없음)이 만드는 취소 신호뿐이다(시간이 되면 평가기가 신호를 abort하고 그 행에 `Evaluation timed out after <N>ms`를 기록한다). provider 고유 시간 제한은 app-server의 `request_timeout_ms`·`startup_timeout_ms`·`turn_timeout_ms`(R-47)와 OpenCode의 서버 기동 `timeout`뿐이다. 턴·비용 한도는 Claude의 `max_turns`·`max_budget_usd`·`task_budget`, OpenCode의 `custom_agent.steps`(`maxSteps`)가 전부이고 Codex에는 없다 | 코드 확인 |
| R-31 | Claude 중단 | 호출 시작 전 세 지점(진입, 캐시 조회 뒤, 작업 디렉터리 준비 뒤)에서 신호가 이미 abort면 `{error: 'Claude Agent SDK call aborted before it started'}`이고 SDK를 부르지 않는다(임시 디렉터리를 만들었으면 지운다). 실행 중 abort되면 같은 사유로 SDK용 `AbortController`를 abort하고, 예외의 이름이 `AbortError`이거나 신호가 abort 상태면 `{error: 'Claude Agent SDK call aborted'}`를 돌려준다. 어느 경우든 임시 디렉터리를 지우고 신호 리스너를 해제한다 | 코드 확인 |
| R-32 | Claude 그 밖의 실행 오류 | SDK 로드·실행·스트림 중 던져진 예외는 `{error: 'Error calling Claude Agent SDK: <예외>'}`로 반환한다(R-08의 throw 단계 제외). 이 응답에는 사용량·메타데이터가 없고 캐시에 쓰지 않는다 | 코드 확인 |

**F. OpenCode SDK 차이**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-33 | 서버·클라이언트 | `baseUrl`이 있으면 `createOpencodeClient({baseUrl})`로 기존 서버에 붙고, 없으면 provider가 `createOpencode({hostname:'127.0.0.1', port:0, timeout:30000, env, config})`로 서버를 띄운다(인스턴스당 1회, 이후 재사용). 서버 환경은 프로세스 환경 + provider env 위에 PATH 앞에 `~/.opencode/bin`을 붙이고(`log_level: debug`이거나 promptfoo가 debug면 `DEBUG=opencode:*`), spawn 동안만 프로세스 환경을 덮었다가 복구한다. 서버 설정에 `logLevel`, `mcp`, `agent.custom`(`custom_agent`), `permission`, `tools`, `provider.<provider_id>.options.apiKey`(`provider_id`와 `apiKey` 둘 다 있을 때)를 싣는다. `OPENCODE_SERVER_PASSWORD`가 있으면 Basic 인증 클라이언트를 만든다 | 코드 확인 |
| R-34 | 도구·권한 기본값과 변환 | 도구 맵은 기본 `{'*': false}`(와일드카드 거부)이고 `working_dir`가 있으면 `glob, grep, list, read`를 true로 더한다. 사용자의 `tools`가 그 위에 덮이며(`edit`·`write`·`patch`·`apply_patch`는 하나의 `edit` 권한이라 서로 값이 다르면 오류) 값은 boolean, 이름은 비어 있지 않아야 한다. v2 서버에서는 세션 생성 시 규칙 배열(`tools` → `allow`/`deny`, `permission`, `custom_agent`의 것 순)을 보내고, v1이거나 `session_id`로 재개하면(그리고 `permission` 규칙이 없을 때) 프롬프트 본문에 `tools`를 싣는다. v1에서 `permission` 규칙은 provider 수준 구성이고 promptfoo가 시작한 세션일 때만 허용되며, 아니면 오류다. `permission`은 `tool: 'ask'\|'allow'\|'deny'` 또는 `tool: {glob: action}`의 평범한 객체여야 한다. 따라서 기본 상태에서 `skill` 도구는 꺼져 있다(`tools.skill: true` 또는 `permission.skill: allow`가 필요). 검증 오류는 `{error: 'Error calling OpenCode SDK: ...'}`다 | 코드 확인 |
| R-35 | 세션 | `session_id`가 있으면 그 세션을 재개(생성하지 않음), 아니면 세션을 만들어(제목 `promptfoo-<시각>`, v2에서 `parent_session_id`가 있으면 `parentID`로 분기) 호출이 끝나면 삭제한다. `persist_sessions: true`면 세션 키(모델·도구·권한·에이전트·작업 디렉터리·MCP 등의 해시)별로 최대 100개까지 재사용한다. 같은 세션을 쓰는 호출은 직렬화 큐로 순서를 맞춘다. `restart_server_per_call`은 `baseUrl`·0이 아닌 `port`·`persist_sessions`·`session_id`·`parent_session_id`와 함께 쓰면 오류이고, 요청 `traceparent`가 바뀔 때 서버를 재시작하며 호출을 직렬화하고 캐시를 끈다 | 코드 확인 |
| R-36 | 응답 변환 | `output`은 최종 응답 `parts` 중 비어 있지 않은 `text` 부분을 `\n`으로 이은 문자열이다. `format.type === 'json_schema'`이면 어시스턴트 메시지 `structured`가 있을 때 `JSON.stringify(structured)`, 없으면 텍스트가 JSON(또는 ```json 펜스)일 때 정규화한 JSON, 그것도 아니면 원문이다. `tokenUsage`는 표 1-G(메시지 `tokens`가 없으면 undefined), `cost`는 메시지 `cost`가 있을 때만 넣는다. `raw = JSON.stringify(응답)`, `sessionId`는 세션 id, `metadata`는 `skillCalls`가 하나라도 있을 때만 `{skillCalls}`다(skill-calls-metadata R-05~R-07, 스킬 도구가 가능하면 세션 이력을 조회) | 코드 확인 |
| R-37 | 실패·중단 | 프롬프트 호출이 던진 예외는 `{error: 'Error calling OpenCode SDK: <메시지>'}`다. 예외가 ENOENT이고 메시지에 `opencode`가 들어 있으면 CLI 설치 안내 오류다. 시작 전·직후 abort는 `OpenCode SDK call aborted before it started`, 실행 중·직후는 `OpenCode SDK call aborted`다. v2 서버에서는 abort 시 `session.abort`로 서버에 중단을 요청하고, v1에는 중단 수단이 없어 프롬프트가 돌아온 뒤 로컬에서만 확인한다. 프롬프트 호출 결과의 `error` 필드는 코드가 검사하지 않는다. SDK가 예외 대신 `{error}` 모양을 돌려주면 `output: ''`에 `error` 없는 응답이 된다(그런 형태를 SDK가 실제로 쓰는지는 미확인). 응답에는 사용량·메타데이터가 없다 | 코드 확인 / 미확인(SDK의 오류 반환 형태) |
| R-38 | 작업 디렉터리 | `working_dir`가 있으면 R-07로 절대화하고 존재·디렉터리 여부를 검사해(아니면 throw) 세션 쿼리의 `directory`로 보낸다. 없으면 임시 디렉터리를 만들었다가 호출 뒤 지우지만 서버에는 넘기지 않는다(`directory` 쿼리가 비어 있다). 이 경우 서버가 어느 디렉터리에서 돌지는 SDK·서버 쪽이다 | 코드 확인 / 미확인(서버 cwd) |
| R-39 | 프롬프트 수준 변경 불가 옵션 | `apiKey`·`baseUrl`·`restart_server_per_call`은 provider 수준 설정이라 프롬프트·테스트 구성에서 값이 달라지면 throw한다(예: `OpenCode SDK baseUrl is provider-level configuration and cannot be overridden per prompt`). `workspace`는 `baseUrl` 또는 `working_dir` 없이 쓰면 throw한다 | 코드 확인 |

**G. Codex SDK 차이**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-40 | 구성 검증 | provider 구성은 엄격한 zod 스키마다(C-22): 표 1-D에 없는 키는 생성 시 `Invalid OpenAI Codex SDK config: <경로>: <사유>`를 throw한다(예: `sandboxMode`처럼 철자가 다른 키). 호출 때 합친 구성은 다시 파싱하되 알 수 없는 키는 버리고(`strip`), 알려진 키의 값이 틀리면 그 행에 `Error calling OpenAI Codex SDK: Invalid ...` 오류를 반환한다. `model`이 알려진 모델 목록 밖이면 경고만 한다(`model_provider`가 OpenAI가 아니면 경고 없음) | 코드 확인 |
| R-41 | 환경·키 | CLI 환경은 기본이 `PATH, Path, HOME, USER, USERNAME, USERPROFILE, TMPDIR, TMP, TEMP, SHELL, COMSPEC, SystemRoot, PATHEXT, LANG, LC_ALL, TERM` 중 값이 있는 것만이고 `inherit_process_env: true`면 프로세스 환경 전체다. 그 위에 `cli_env`가 덮는다. `CODEX_HOME`, 프록시·인증서 변수, `SSH_AUTH_SOCK` 같은 선택 변수가 프로세스에는 있으나 상속되지 않으면 경고 1회(`cli_env`로 옮기라는 안내)를 낸다. provider env(promptfoo 수준 env) 중 `OPENAI_API_KEY`·`CODEX_API_KEY` 외는 CLI에 전달하지 않는다(경고). API 키는 `config.apiKey` 또는 env(`OPENAI_API_KEY`, `CODEX_API_KEY`)에서 찾고(`apiKeyEnvar`는 스키마에 없어 provider 구성에 쓰면 거부된다), `model_provider`가 OpenAI가 아닌데 `config.apiKey`가 명시되지 않았으면 주입하지 않고 환경의 두 키 변수도 제거한다(`cli_env`로 명시한 것은 보존). 키가 없으면 Codex 로그인 상태에 맡긴다 | 코드 확인 |
| R-42 | 작업 디렉터리·Git 요건·샌드박스 전달 | `working_dir`가 없으면 `process.cwd()`다(임시 디렉터리 없음). 호출 때 그 디렉터리가 존재·디렉터리인지 확인하고, 거기서 위로 `.git`(파일 또는 디렉터리)을 찾을 수 있어야 하며 못 찾으면 `{error: 'Error calling OpenAI Codex SDK: Working directory ... is not inside a Git repository ...'}`다(`skip_git_repo_check: true`로 해제). `sandbox_mode`·`approval_policy`·`network_access_enabled`·`web_search_*`는 설정된 것만 스레드 옵션으로 넘기고(기본값을 promptfoo가 채우지 않는다), `model`·`model_reasoning_effort`·`additional_directories`도 같다. 설정하지 않았을 때의 동작은 SDK·CLI 기본(`미확인`)이다 | 코드 확인 / 미확인(SDK 기본) |
| R-43 | 스레드·세션 | 기본은 호출마다 새 스레드를 만들고 끝나면 풀에서 지운다. `thread_id`가 있으면 그 스레드를 재개하고, `persist_threads: true`면 `thread_pool_size`(기본 1) 개까지 스레드를 재사용한다. 풀 키 재료는 인스턴스 키(환경·`base_url`·`cli_config`·`codex_path_override`)와 `working_dir`·`additional_directories`·`model`·`output_schema`·샌드박스·추론·네트워크·웹 검색·승인 설정과, 렌더 전 프롬프트 템플릿(`prompt.raw`, 없으면 렌더된 prompt)이다. 같은 스레드를 쓰는 호출은 직렬화 큐로 순서를 맞춘다. `deep_tracing`이 켜지면 `persist_threads`·`thread_id`·`thread_pool_size`는 무시되고(경고 1회) 호출마다 새 Codex 객체를 만들었다 지운다 | 코드 확인 |
| R-44 | 응답 변환 | 실행은 `enable_streaming`이면 `runStreamed` 이벤트를 소비하고(`turn.completed`의 `usage`, 마지막 `agent_message`의 text, `turn.failed`면 `Codex turn failed: ...` throw, `error` 이벤트는 마지막 오류로 기억하고 종료 이벤트를 기다리며 완료 없이 끝나면 오류), 아니면 `thread.run`이다. 응답은 `{output: turn.finalResponse \|\| '', tokenUsage, cost, metadata, raw: JSON.stringify(turn), sessionId: thread.id \|\| 'unknown'}`다. 토큰은 표 1-G다(`turn.usage`가 없으면 undefined, 그러면 `cost`도 undefined). `cost`는 R-62의 가격표 환산이며 `config.model`이 없으면 undefined이고, 사용자 지정 바이너리와 `gpt-5.6*` 모델은 캐시 쓰기 토큰이 보고되지 않으면 undefined다(Bedrock 경유 모델은 가격표 이름으로 환산). `metadata`는 R-57의 스킬 필드뿐이다. `output_schema`를 주면 `output`은 SDK가 준 JSON 텍스트 그대로의 문자열이다(문서 서술, SDK 쪽) | 코드 확인 / 미확인(JSON 텍스트 형태) |
| R-45 | 실패·중단·재시도 | 취소 신호를 SDK 실행 옵션 `signal`로 넘기고(스트리밍은 이벤트마다 확인), 시작 전 abort는 `OpenAI Codex SDK call aborted before it started`, 그 밖 abort는 `OpenAI Codex SDK call aborted`다. 그 밖 예외는 `{error: 'Error calling OpenAI Codex SDK: <메시지>'}`이고 사용량·메타데이터는 없다. 예외 메시지·상태가 429·`rate_limit_exceeded`·쿼터 계열이면 `metadata.rateLimitKind`와 `metadata.http{status, statusText, headers}`(재시도 대기 힌트 `retry-after-ms`: 메시지의 "try again in ..."나 기본 60초)를 단 오류 응답으로 바꿔 스케줄러가 재시도할 수 있게 한다(하드 쿼터는 재시도 힌트 없음). 스케줄러는 재시도 상한을 `provider.config.maxRetries`(비음수 정수, 없으면 스케줄러 정책의 3회)에서 읽는다. 이런 변환은 네 provider 중 Codex SDK에만 있다. `codex_path_override`를 쓰면 호출마다(성공 결과를 재사용하지 않고) 그 바이너리가 SDK가 요구하는 CLI 버전과 호환되는지 점검하고(`skip_codex_version_check`로 건너뜀) 어긋나면 오류를 반환한다 | 코드 확인 |

**H. Codex app-server 차이**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-46 | 구성·기본값 | 구성은 표 1-E의 엄격 스키마이고 R-40과 같은 방식(생성 시 엄격, 호출 시 `strip`, 오류 접두 `Invalid OpenAI Codex app-server config:`)이다. 호출 때 기본값을 채운다: `approval_policy: 'never'`, `sandbox_mode: 'read-only'`, `network_access_enabled: false`, `ephemeral: true`, `thread_cleanup: 'unsubscribe'`, `reuse_server: true`. 작업 디렉터리는 R-07, 존재·디렉터리·Git 저장소 요건 검사는 R-42와 같되 결과는 `{error: 'Error calling OpenAI Codex app-server: ...'}`이고 통과한 경로는 인스턴스가 기억한다 | 코드 확인 |
| R-47 | 프로세스·핸드셰이크·시간 제한 | 연결 키(환경·`codex_path_override`·`cli_config`·`experimental_api`의 해시)마다 `codex app-server --listen stdio://`(+`cli_config`를 `-c key=value`로 펼침)를 자식 프로세스로 띄우고 stdio JSON-RPC를 쓴다. 핸드셰이크는 `initialize`(clientInfo `promptfoo_codex_app_server`, `capabilities.experimentalApi` 기본 true)와 `initialized` 알림이고, 허용되면 `account/login/start`(`{type:'apiKey', apiKey}`)를 보낸다(메서드가 없으면 무시). 각 요청의 제한은 `request_timeout_ms`(기본 30000, `turn/start` 응답 포함)이고 초과하면 그 연결을 닫는다. 기동 요청은 `startup_timeout_ms`(기본 30000). 턴 완료 대기는 `turn_timeout_ms`가 있을 때만 제한이 있고 초과하면 `turn/interrupt`를 보내고 `codex app-server turn timed out after <N>ms`다. `deep_tracing`이면 연결을 재사용하지 않는다. 자식 프로세스 stdout 줄을 읽는 규칙은 R-61, stderr는 20,000자를 넘으면 마지막 10,000자만 남기고 오류 메시지에 비밀을 가린 채 덧붙는다 | 코드 확인 |
| R-48 | 스레드·턴 파라미터와 샌드박스 | `thread/start`(또는 `thread_id`면 `thread/resume`)에 `approvalPolicy`·`sandbox`(`sandbox_mode ?? 'read-only'`)·`cwd`·`model`·`ephemeral`·`serviceName: 'promptfoo'` 등을 항상 싣고, `turn/start`에 입력 항목·`cwd`·`approvalPolicy`·`effort`·`outputSchema`와 `sandboxPolicy`를 싣는다. `sandboxPolicy`는 `sandbox_policy`가 있으면 그것, 아니면 `sandbox_mode`에서 만든다: `danger-full-access` → `{type:'dangerFullAccess'}`, `workspace-write` → `{type:'workspaceWrite', writableRoots:[working_dir, ...additional_directories], networkAccess, ...}`, `read-only` → `{type:'readOnly', access:{type:'fullAccess'}, networkAccess}`. 기본값(`network_access_enabled: false`가 채워지므로) 때문에 `sandboxPolicy`는 기본적으로 항상 전달된다. 스레드는 `persist_threads`(풀 크기 기본 1, 가장 오래된 비활성 스레드 `thread/unsubscribe`)·`thread_id`로 재사용하고 기본은 턴이 끝나면 `thread_cleanup`(`unsubscribe`/`archive`/`none`)대로 정리한다 | 코드 확인 |
| R-49 | 서버 요청(승인 등) 정책 | 에이전트의 승인·입력 요청은 `server_request_policy`로 즉시 응답한다: 명령 실행·파일 변경 승인은 기본 `decline`, 권한 요청은 `permissions`(기본 `{}`, scope `turn`), 도구 입력 질문은 `user_input`(기본 `empty` = 답 없음, `first-option`, 질문 id별 고정 답), MCP 유도는 `mcp_elicitation`(기본 `decline`), 동적 도구는 `dynamic_tools`에 설정이 없으면 `success: false`와 `No dynamic tool response configured.`, `account/chatgptAuthTokens/refresh`와 알 수 없는 요청은 오류다. 모든 요청과 응답이 `metadata.codexAppServer.serverRequests`에 기록된다 | 코드 확인 |
| R-50 | 응답 변환·실패 | `output`은 완료된 `agentMessage` 항목 중 마지막의 `text`, 없으면 항목별 델타 중 마지막, 그것도 없으면 델타 전체 이음이다. `tokenUsage`는 마지막 `thread/tokenUsage/updated`에서 `last ?? total ?? 원본`을 읽어 표 1-G로 만들고(숫자 `input`/`output`이 없으면 undefined), `cost`는 `config.model`로 가격표 추정(없으면 undefined)이다. 성공 응답은 `{output, tokenUsage, cost, metadata, raw, sessionId: threadId}`이고 `metadata.codexAppServer`와 스킬 필드(skill-calls-metadata R-08~R-11)를 담는다. 실패: `turn/completed`의 `status === 'failed'`나 재시도 아닌 `error` 알림이 있으면 해당 메시지로, 턴 이벤트 누적이 10,000,000자를 넘으면 `codex app-server turn events exceeded 10000000 characters`로 연결을 닫고 오류를 낸다. 모두 `{error: 'Error calling OpenAI Codex app-server: <메시지>'}`로 반환되고 사용량·메타데이터는 없다. abort는 `turn/interrupt`(5초 제한) 후 `OpenAI Codex app-server call aborted`(시작 전이면 `... aborted before it started`)이다. `cost`의 환산은 R-62다 | 코드 확인 |
| R-61 | app-server stdout의 한 줄(`readline` 단위)이 들어올 때 | ① 버퍼가 비어 있고 줄이 공백뿐이면 무시한다. ② 후보 = 버퍼가 비어 있으면 그 줄(`trim`), 아니면 `버퍼의 줄들 + 현재 줄`을 `\n`으로 이은 문자열이다. ③ 후보가 5,000,000자를 넘으면 버퍼를 비우고 연결 실패로 처리한다(대기 요청을 `codex app-server JSON-RPC message exceeded 5000000 characters`로 reject하고 연결을 닫는다). ④ `JSON.parse(후보)`가 성공하면 버퍼를 비우고 메시지를 처리한다. ⑤ 실패했는데 후보가 여러 줄이고 오류가 `Bad control character`면 문자열 안의 날 줄바꿈(따옴표 안, 이스케이프 아님)을 `\n`으로 바꿔 한 번 더 파싱한다. ⑥ 그래도 실패하고 후보가 `{`로 시작하며 오류가 `Unterminated string`·`Unexpected end of JSON input`이거나 `Expected ...` 오류의 위치가 후보 끝이면 메시지가 아직 안 끝난 것으로 보고 줄들을 버퍼에 두고 다음 줄을 기다린다. ⑦ 그 밖의 실패는 경고를 남기고 버퍼를 비운다. 이때 후보가 여러 줄이면(재시도 1회만) 뒤에서부터 `{`로 시작하는 줄(맨 앞 줄 제외, 없으면 마지막 줄)을 새 메시지의 시작으로 보고 그 앞까지를 버리고 현재 줄을 다시 처리한다. ⑧ 처리 분기: `id`가 있고 `result`나 `error`가 있으면 응답(`id`의 대기 요청이 없으면 무시, `error`면 `JsonRpcError(code)`로 reject, 성공 콜백이 던지면 그 예외로 reject), `id`와 `method`가 있으면 서버 요청(R-49 정책 결과를 `{id, result}`로, 던지면 `{id, error:{code:-32000, message}}`로 회신), `method`만 있으면 알림(R-50), 그 밖은 무시한다. 송신은 `JSON.stringify(메시지) + '\n'`이다 | 코드 확인 |
| R-62 | Codex 두 provider가 `cost`를 만들 때(`calculateOpenAIUsageCostFromTokenUsage(model, tokenUsage)`) | ① 모델명이 없거나 `tokenUsage`가 없으면 undefined. 모델명은 Codex SDK는 `config.model`이고 `model_provider`가 `amazon-bedrock`이며 모델이 `openai.gpt-5.6…`이면 `bedrock:gpt-5.6…`, app-server는 `config.model`이다(경로 모델이 `config.model`을 덮은 값). ② `openai.` 접두를 떼고 계산하며 `gpt-6-astra`·`gpt-6.1-sol`이 `openai.`로 오면 undefined, 결과가 있고 원래 이름이 `openai.`로 시작하면 ×1.1이다. ③ 사용량을 `prompt_tokens=prompt`(캐시 읽기 포함 전체 입력), `completion_tokens=completion`, `cached_tokens=cached ?? 0`, 캐시 쓰기 토큰이 숫자로 보고됐을 때만 `cache_write_tokens`로 바꿔 표준(standard) 처리 계층·옵션 없음으로 환산한다. ④ 단가 조회 키는 모델 id 문자열 정확 일치이고 `cost`가 있는 항목(`OPENAI_BILLING_MODELS`)만 쓴다. 단위는 토큰당 USD(`5 / 1e6`처럼 적음)이고, 항목은 `input`·`output`과 선택 `longContext{threshold, input, output}`이며 캐시 읽기 단가는 별도 표(`STANDARD_CACHED_INPUT_RATES`, 없으면 `input`)다. 입력 토큰이 272,000(`GPT_LONG_CONTEXT_THRESHOLD`)을 넘고 `longContext`가 있으면 그 입력·출력 단가를 쓴다. 캐시 쓰기 단가는 `gpt-5.6*`·`gpt-6*` 계열(`CACHE_WRITE_MODELS`)에만 있고 `input × 1.25`다. ⑤ 비용 = 캐시되지 않은 입력 × input + 캐시 읽기 × cachedInput + 캐시 쓰기 × cacheWriteInput + 출력 × output(캐시 읽기 토큰은 입력 토큰 수를 넘지 않게 제한, 캐시 쓰기 토큰은 남은 입력 안으로 제한). ⑥ 단가표에 없는 모델(예: 단가 없는 `gpt-5.3-codex-spark`, 임의의 이름)이면 조회가 실패하고 사용자 단가 설정이 이 경로에는 없으므로 undefined다. ⑦ 캐시 쓰기 단가가 input과 다른 모델인데 `cache_write_tokens`가 보고되지 않았으면 undefined다. ⑧ `bedrock:` 표시 모델은 별도 Bedrock 단가표(표준 계층만, 목록에 없으면 undefined)를 쓴다. 예: `gpt-5.5`는 input `5/1e6`, output `30/1e6`, 캐시 읽기 `0.5/1e6`이므로 `prompt 100, cached 60, completion 20`은 `40×5e-6 + 60×0.5e-6 + 20×30e-6 = 8.3e-4` USD다 | 코드 확인 |

**I. 작업 디렉터리·격리·안전 기본값**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-51 | 평가 도중 에이전트가 파일을 바꿀 수 있는가 | 표 1-H의 기본값이 답이다. 기본 설정에서 Claude(도구가 읽기 전용이거나 없음)와 OpenCode(쓰기·셸 도구가 거부)와 Codex app-server(`read-only` 샌드박스)는 파일을 바꾸지 못한다. Codex SDK는 `sandbox_mode`를 넘기지 않으므로 기본 동작이 SDK·CLI에 달렸고(문서는 `workspace-write`라 서술, `미확인`) `working_dir`를 생략하면 promptfoo가 실행된 디렉터리가 대상이다. 쓰기·셸을 켜면(`append_allowed_tools`+`permission_mode: acceptEdits`, `tools.edit`, `sandbox_mode: workspace-write`) 변경이 실제 `working_dir`에 남고 이후 호출에 영향을 준다. 기본으로는 이를 되돌리지 않는다 | 코드 확인(전달·기본값) / 미확인(SDK의 권한·샌드박스 동작) |
| R-52 | `copy_working_dir` | 값은 `true`(자동), `false`, `'git'`, `'copy'`이고 그 밖이면 `copy_working_dir must be true, false, 'git', or 'copy'`를 throw한다. 지원: Claude, OpenCode, Codex SDK. app-server는 구성 스키마에 키가 없어 provider 구성에 쓰면 생성 시 거부된다(app-server의 `working_dir`가 활성 워크스페이스일 때 저장소 선택 환경변수를 지우는 코드는 다른 타깃의 복사본에서 도는 `agent-rubric` 채점기용이다). `working_dir`가 없으면 `copy_working_dir requires working_dir`다. 복사본 생성: `auto`는 `working_dir`가 git 저장소 루트이고 작업트리가 현재 커밋과 정확히 같을 때(미커밋·미추적·무시된 파일 없음, 속성·eol 변환 없음 등) `git clone --shared --no-checkout` → `checkout --detach <HEAD>` → `remote remove origin`(복사본에서 push할 수 없게)이고, 아니면 `fs.cp` 복사다(링크가 `working_dir` 밖을 가리키거나 `.git`이 worktree·submodule이면 오류). `'git'`은 작업트리가 커밋과 같으면(무시된 파일은 있어도 되나 복제본에는 들어가지 않는다) 복제하고 조건이 안 맞으면 오류, `'copy'`는 항상 복사다. 서브모듈이 있으면 오류다. 위치는 `os.tmpdir()/promptfoo-workspace-*/workspace`이고 tmpdir이 `working_dir` 안이면 그 부모 아래다. 코드 주석은 "호출 간 영향을 막을 뿐 보안 샌드박스는 아니다"라고 쓴다. 이 provider가 `copy_working_dir`를 켠 채 평가기의 워크스페이스가 아닌 디렉터리에서 호출되면(레드팀 전략·스크립트 등) `copy_working_dir runs each eval step in a fresh copy ... was not made.`를 throw한다. 이 호출은 응답 캐시를 읽지도 쓰지도 않는다(response-cache R-23) | 코드 확인 |
| R-53 | 워크스페이스 생명주기·기록 | `providerOutput`이 없는 테스트에서 평가기가 provider 호출 직전(prompt 렌더 뒤)에 `{...provider.config, ...prompt.config}`에 `copy_working_dir`가 있으면 `working_dir`(vars 렌더 후)로 워크스페이스를 만들고, 호출에는 `prompt.config.working_dir`를 복사본 경로로 바꿔 준다. 호출 뒤 provider 응답이 성공이든 `{error}`든 `response.metadata = {...response.metadata, workingDir, workspaceDiff?}`로 합친다(워크스페이스 값이 이긴다). `workspaceDiff`는 git 전략 복사본에서만 생기고(`fs.cp` 복사본은 `workingDir`만 남아 변경 내용을 기록하지 못한다), 복제 당시 HEAD와 비교한 에이전트의 변경(수정·삭제, 새로 만든 파일은 복제본의 커밋된 `.gitignore` 기준으로 무시되지 않는 것, 사용자·시스템 git 설정은 읽지 않는 임시 bare 저장소에서 `diff --cached`)이다. 100,000자를 넘으면 잘라 `[diff truncated after 100000 characters]`를 붙인다. 계산 실패나 워크스페이스가 링크로 바뀐 경우는 경고하고 `workingDir`만 남긴다. 워크스페이스는 어서션(지연 채점 포함)이 끝난 뒤, 예외 경로에서도, 프로세스 종료 때 동기적으로 지운다. 이 provider들은 호출 중 `assertIsolatedWorkingDir`로 `working_dir`가 활성 워크스페이스인지 확인한다 | 코드 확인 |
| R-54 | 환경 노출 | 표 1-H 마지막 두 행: Claude 서브프로세스는 promptfoo 프로세스 환경 전체를 받는다(`config.env`와 provider env가 덮음). OpenCode 서버도 프로세스 환경 전체를 상속한다. Codex 두 provider는 최소 목록과 `cli_env`만 준다. 에이전트가 셸을 쓸 수 있으면 그 환경이 보인다는 점은 추론이다 | 코드 확인(전달) / 추론(셸에서의 노출) |

**J. 스킬 노출 경로 (설정 → SDK 전달)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-55 | Claude에서 스킬을 에이전트가 읽게 하는 설정 | 설정 세 개가 SDK 옵션으로 간다: `working_dir` → `cwd`, `setting_sources` → `settingSources`(기본 `[]`), `skills` → `skills`(그리고 R-12의 `Skill` 도구 추가), `plugins` → `plugins`(경로 절대화). 문서는 `setting_sources: ['project']`로 `<working_dir>/.claude/skills/<이름>/SKILL.md`를 발견하고 `skills`로 좁힌다고 안내한다. 기본값(`setting_sources` 빈 목록)에서는 `working_dir` 안의 스킬도 사용자 홈 스킬도 발견되지 않는 것이 설정 의도다. promptfoo는 스킬 파일의 존재를 확인하지 않는다. 호출 뒤 `Skill` 도구 호출만 `metadata.skillCalls`로 변환된다(skill-calls-metadata) | 코드 확인(전달) / 미확인(SDK 쪽 발견·로딩, 사용자 홈 스킬 포함) |
| R-56 | OpenCode | 전용 스킬 옵션은 없다. `working_dir`가 세션 `directory`로 가고, 스킬은 OpenCode의 `skill` 도구로 로드된다. 기본 도구 맵이 `*: false`라 스킬 도구가 꺼져 있어 `tools.skill: true`(그리고 비대화 실행이면 `permission.skill: allow`)를 줘야 한다. 스킬 도구가 가능하면(`skill` 또는 `*` 규칙 중 `deny`가 아닌 것이 있음) 호출 뒤 세션 이력을 조회해 `skillCalls`를 만든다 | 코드 확인(전달·게이트) / 미확인(스킬 발견 위치 `.agents/skills` 등은 문서 서술) |
| R-57 | Codex SDK | 스킬 설정 옵션이 없다. `working_dir` → `workingDirectory`만 있고 Codex가 `.agents/skills` 등에서 발견한다(문서, SDK 쪽). `CODEX_HOME`을 쓰려면 기본 환경이 상속하지 않으므로 `cli_env.CODEX_HOME`(또는 `inherit_process_env`)이 필요하다. `skillCalls`는 명령 실행 항목에서 `SKILL.md` 경로를 추정한 것(skill-calls-metadata R-08~R-11)이고, `enable_streaming`이 항목 수집에 필요한지는 SDK 쪽이다 | 코드 확인(전달) / 미확인(SDK 발견·비스트리밍 항목) |
| R-58 | Codex app-server | `working_dir` → `cwd`. 프롬프트가 JSON 배열이면 `{type:'skill', name, path}`·`{type:'mention', name, path}` 항목을 SDK 입력 항목 그대로 `turn/start`의 `input`에 실을 수 있다(R-09). `skillCalls`는 SDK provider와 같은 추정 규칙이다 | 코드 확인 |

**K. 캐시 사용 여부**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-59 | 응답 캐시를 쓰는 provider | Claude(`anthropic:claude-agent-sdk`)와 OpenCode(`opencode:sdk`)만 `initializeAgenticCache`→`getCachedResponse`→`cacheResponse`를 쓴다. 키·우회·지문·히트 응답의 `cached: true`는 response-cache R-20~R-26이다. 캐시를 읽는 호출은 SDK·서브프로세스·임시 디렉터리를 만들지 않는다(Claude: R-10). Codex SDK와 app-server는 응답 캐시가 없고(response-cache R-27) 같은 입력을 다시 보내면 매번 SDK를 호출하며 응답에 `cached`가 붙지 않는다. 문서 `openai-codex-sdk.md`의 "응답을 자동으로 캐시한다"는 서술은 구현과 다르다(2.1) | 코드 확인 |

- 불변식: ① 이 provider들은 `ApiProvider.callApi`가 `ProviderResponse`를 돌려주는 계약을 그대로 따른다. 다만 구성·작업 디렉터리 검증 단계는 예외를 던진다(R-08). ② 같은 호출에서 `working_dir`는 하나이고, `copy_working_dir`가 켜지면 그 값은 평가기가 정한 복사본이다. ③ 기본 도구·권한 설정은 쓰기를 허용하지 않는다(Codex SDK는 SDK 기본에 의존, R-42). ④ 응답의 `metadata.skillCalls`는 에이전트가 낸 증거를 변환한 것이고, SDK의 스킬 로딩 여부를 직접 보장하지 않는다.
- 미결정: 없음.
- 확인 한계: 설치·빌드·실행·네트워크·모델 호출을 하지 않았다. 아래는 외부 코드라 코드로 닫을 수 없다. ① Claude Agent SDK가 `setting_sources`·`skills`·`plugins`·`cwd`로 스킬을 어디서 어떻게 발견·로딩·필터링하는지, `Skill` 도구 호출 형태, 사용자 홈 스킬이 `setting_sources: ['user']`가 아닐 때 보이는지, 권한 모드 7종의 실제 동작, `allow_all_tools`·`append_allowed_tools`가 비대화 실행에서 승인 없이 도구를 쓰게 하는지, `max_turns`·`max_budget_usd`의 SDK 기본·초과 시 서브타입 이름, 세션 파일 저장 위치. ② OpenCode SDK가 `{error}`를 예외로 던지는지 반환하는지(R-37), `directory`가 없을 때의 서버 cwd(R-38), `.agents/skills` 발견 규칙. ③ Codex SDK의 `sandbox_mode`·`approval_policy` 기본값, `thread.run`의 항목 수집 범위, `output_schema` 출력 모양. ④ 이 provider들이 만드는 트레이스 스팬의 내용. ⑤ 테스트 파일은 이름 검색과 `test/providers/claude-agent-sdk.test.ts` 일부(스케줄러 합성 사례)만 열람했고 실행하지 않았다.

### 1.5 필수 코드 참조 [필수]

라이선스: MIT(overview 1절), 이 파일들은 Apache·다른 LICENSE가 걸린 하위 디렉터리에 속하지 않는다. 인용·복사 시 저작권·허가 문구를 유지한다. 경로는 모두 `repos/promptfoo/` 기준이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/providers/claude-agent-sdk.ts:442-1068` `ClaudeCodeOptions` | Claude 옵션 전체 이름·타입과 주석(기본값 의미) | R-10~R-22 |
| C-02 | `src/providers/claude-agent-sdk.ts:1243-1344` `RESERVED_POLICY_EXTRA_ARGS`, `normalizeClaudeCliArgumentName`, `validateClaudeToolPolicyConfig` | 도구·권한·`extra_args` 검증과 예약 이름 24개 | R-13 |
| C-03 | `src/providers/claude-agent-sdk.ts:1465-1610` `callApi` 앞부분 | 구성 병합, 환경 병합, 서브에이전트 한도·키 점검, 충돌 검사 | R-06, R-13, R-14, R-21 |
| C-04 | `src/providers/claude-agent-sdk.ts:1621-1673` | 허용 목록·사용 가능 도구 계산, 작업 디렉터리 선택 | R-10~R-12 |
| C-05 | `src/providers/claude-agent-sdk.ts:1691-1778, 1908-1924` `cacheKeyQueryOptions`, `options` | 옵션 → SDK 옵션 이름 매핑 전체(`settingSources ?? []`, `skills`, `plugins`, 시스템 프롬프트 포함) | R-14~R-19, R-22 |
| C-06 | `src/providers/claude-agent-sdk.ts:247-309, 1090-1241, 2221-2226` `isRawSubagentTranscript`, `redactRawSubagentToolOutput`, `createTaskOutputTranscriptRedactionHook`, `createAskUserQuestionCanUseTool`, `buildClaudeHooks`, `validateAskUserQuestionConfig` | AskUserQuestion 자동 응답과 훅 조립 | R-20 |
| C-07 | `src/providers/claude-agent-sdk.ts:2185-2273` 스트림 루프, 최종 `result` 선택 | 메시지 종류별 처리, 배경 작업 결과 제외 | R-23, R-24 |
| C-08 | `src/providers/claude-agent-sdk.ts:109-134, 1926-2010, 2327-2431` | 사용량 기준선·차감, 토큰 합산, 비용 | R-27, R-28 |
| C-09 | `src/providers/claude-agent-sdk.ts:2433-2534, 2595-2616` | 성공·비성공 응답 구성, 예외·중단 처리, 정리 | R-25, R-26, R-29, R-31, R-32 |
| C-10 | `src/providers/mcp/transform.ts:113-226`, `src/contracts/providerConfig/mcp.ts:1-140` | MCP 검증·이름 충돌·변환, 스키마 | R-16 |
| C-11 | `src/providers/agentWorkspace.ts:88-141, 637-749, 755-773` `getCopyWorkingDirMode`, `assertIsolatedWorkingDir`, `createAgentWorkspace`, `createAgentWorkspaceForConfig` | 모드 해석, 오용 검출, 복제·복사 선택과 생성·정리 | R-52, R-53 |
| C-12 | `src/providers/agentWorkspace.ts:179-318, 524-634` `getCloneableRepository`, `getWorkspaceDiff` | git 복제 가능 조건, diff 산출(길이 제한 포함) | R-52, R-53 |
| C-13 | `src/evaluator.ts:1823-1891, 1983-1988, 2032-2034` | 워크스페이스 생성 시점·`working_dir` 치환·metadata 병합·삭제 시점 | R-53 |
| C-14 | `src/providers/agentic-utils.ts:77-86`, `src/util/pathUtils.ts:40-46` `resolveAgenticWorkingDir`, `safeResolve` | 상대 경로 해석 | R-07 |
| C-15 | `src/providers/opencode-sdk.ts:57, 255-406` `FS_READONLY_TOOLS`, `OpenCodeSDKConfig` | OpenCode 옵션 이름·타입·기본값 | R-33~R-39 |
| C-16 | `src/providers/opencode-sdk.ts:688-742, 1034-1112, 1726-1736` | `tools`·`permission` 검증·규칙 변환, 기본 도구 맵 | R-34 |
| C-17 | `src/providers/opencode-sdk.ts:1162-1285, 1502-1600` | 서버 환경·설정, 기동·클라이언트 | R-33 |
| C-18 | `src/providers/opencode-sdk.ts:1383-1484, 1114-1128` | `prepareCall`(throw 단계), `directory` 쿼리, 잠금 옵션 | R-38, R-39 |
| C-19 | `src/providers/opencode-sdk.ts:1627-1681, 1683-1724, 1738-1776` | 세션 생성·재사용, prompt 본문 | R-35, R-36 |
| C-20 | `src/providers/opencode-sdk.ts:641-668, 1898-1937, 1966-2001, 2003-2187` | 토큰·응답 변환, 오류·중단, 호출 전체 흐름 | R-36, R-37 |
| C-21 | `src/providers/registry.ts:131, 481-499, 532-547, 1127-1148, 1206-1245`, `src/util/provider.ts:236-275`, `src/node/doEval.ts:739-760` | 접두어 분기·모델 우선순위, 키 사전 점검 | R-01~R-03, R-05 |
| C-22 | `src/providers/openai/codex-sdk.ts:214-463` `OpenAICodexSDKConfig`, zod 스키마, `parseCodexConfig` | Codex SDK 옵션·엄격 검증 | R-40 |
| C-23 | `src/providers/openai/codex-sdk.ts:792-891`, `src/providers/openai/codexProcess.ts:3-65`, `src/providers/openai/codexApiKeyGating.ts:20-73` | CLI 환경 구성, 최소 환경 목록, 키 주입 조건 | R-41 |
| C-24 | `src/providers/openai/codex-sdk.ts:977-1117` | Git 요건, 스레드 옵션, 스레드 풀 | R-42, R-43 |
| C-25 | `src/providers/openai/codex-sdk.ts:1180-1239, 1520-1538, 1985-2250, 2393-2559` | 스트리밍 이벤트, 호출 흐름, 응답·토큰·비용·정리 | R-43~R-45 |
| C-26 | `src/providers/openai/codex-sdk.ts:465-598`, `src/scheduler/rateLimitRegistry.ts:195-240` | 레이트리밋 응답 변환, `maxRetries` 읽기 | R-45 |
| C-27 | `src/providers/openai/codex-app-server.ts:231-280, 389-575` | app-server 옵션·엄격 스키마 | R-46 |
| C-28 | `src/providers/openai/codex-app-server.ts:1363-1620, 1622-1636` | 병합·기본값·호출 흐름·작업 디렉터리 | R-46 |
| C-29 | `src/providers/openai/codex-app-server.ts:831-891, 1758-1856, 3070-3128` | 프로세스·핸드셰이크·시간 제한·턴 대기 | R-47 |
| C-30 | `src/providers/openai/codex-app-server.ts:2095-2215, 2404-2508, 2510-2575` | 스레드 시작·재개, 턴 파라미터, 샌드박스 정책, 입력 항목 | R-09, R-48 |
| C-31 | `src/providers/openai/codex-app-server.ts:2684-2768, 2884-3068` | 알림 처리, 서버 요청 정책 | R-49, R-50 |
| C-32 | `src/providers/openai/codex-app-server.ts:3207-3284, 3453-3519, 3529-3560` | 응답·토큰·비용·검사 | R-46, R-50 |
| C-33 | `src/providers/openai/billing.ts:819-852` `calculateOpenAIUsageCostFromTokenUsage` | Codex 비용 환산의 진입 조건 | R-44, R-50, R-62 |
| C-34 | `src/providers/agentic-utils.ts:25-61` `isAgenticProvider`, `isAgenticGradingProvider`, `src/matchers/agent.ts:17-80` | 에이전트 provider id 목록과 `agent-rubric` 채점기 게이트(경계 참조) | 1.2 |
| C-35 | `src/providers/openai/codex-app-server.ts:155-156, 1026-1207` `handleLine`, `escapeStringNewlines`, `shouldBufferJsonRpcLine`, `handleMessage`, `handleResponse`, `handleServerRequest`, `recordStderr` | JSON-RPC 줄 조립·재시도·분기 | R-47, R-61 |
| C-36 | `src/providers/openai/billing.ts:569-625, 819-893, 1015-1108, 1114-1263, 1266-1446`, `src/providers/openai/util.ts:14-21, 592-600, 1032-1042, 1207-1219` | 환산 알고리즘, 단가표 구조(`OPENAI_BILLING_MODELS`, `STANDARD_CACHED_INPUT_RATES`, `CACHE_WRITE_MODELS`, 장문맥 단가), 캐시 쓰기 토큰 판독. 단가 숫자는 이 코드가 원본이다 | R-62 |
| C-37 | `src/providers/registry.ts:1181-1196`, `src/providers/openai/util.ts:680-694, 733-775` `isOpenAiFirstPartyApiUrl`, `assertOpenAiModelEndpointCompatibility` | Codex 생성 시 모델-엔드포인트 호환 검사 | R-03 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출. 원본 테스트는 `test/providers/claude-agent-sdk.test.ts`의 일부(스케줄러 합성 사례)를 열람했을 뿐 실행하지 않았다. SDK는 모두 대체물(스트림·응답 데이터)로 바꾼 사례이므로 SDK가 실제로 그 데이터를 만드는지, 도구 권한이 SDK에서 실제로 어떻게 동작하는지는 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-10, R-11, R-12 | Claude, `working_dir` 없음, `apiKey`만 설정 | SDK 옵션 `allowedTools: []`, `tools: []`, `cwd`는 새 임시 디렉터리이고 호출 뒤 그 디렉터리가 없다 |
| T-02 | R-11, R-12, R-07 | Claude, `working_dir: './fixtures/v1'`(설정 파일 기준으로 존재) | `cwd`는 설정 디렉터리 기준 절대 경로, `allowedTools`와 `tools`가 모두 `['Glob','Grep','LS','Read']` |
| T-03 | R-12, R-15 | T-02에 `skills: ['review']`, `setting_sources: ['project']` 추가 | `tools = ['Glob','Grep','LS','Read','Skill']`, `skills: ['review']`, `settingSources: ['project']`. 둘 다 생략하면 `settingSources: []`이고 `skills`는 `undefined` |
| T-04 | R-12 | `tools: ['Bash']`와 `skills: ['review']` | `tools`가 정확히 `['Bash']`(`Skill`이 더해지지 않음) |
| T-05 | R-13 | `allow_all_tools: true`와 `append_allowed_tools: ['Write']` | throw `Cannot specify allow_all_tools together with tools, custom_allowed_tools, or append_allowed_tools`, SDK 호출 없음 |
| T-06 | R-14 | `permission_mode: bypassPermissions`만 / `manual` / 미지정 | 앞은 throw, 가운데는 SDK `permissionMode: 'default'`, 뒤도 `'default'` |
| T-07 | R-05, R-21 | 어떤 키도 없고 `apiKeyRequired` 미지정, Bedrock·Vertex 환경변수 없음 / `apiKeyRequired: false` | 앞은 throw `Anthropic API key is not set ...`, 뒤는 진행 |
| T-08 | R-24 | 스트림 `result`가 둘: 첫째 `origin.kind: 'task-notification'`, 둘째 `origin.kind: 'human'` | 둘째가 선택된다. `origin`이 전혀 없으면 마지막 `result`다. `result`가 없으면 `{error: "Claude Agent SDK call didn't return a result"}` |
| T-09 | R-25, R-27, R-28 | 성공 `result`, `modelUsage`가 `{A:{inputTokens:10, outputTokens:5, cacheReadInputTokens:100, cacheCreationInputTokens:20}, B:{inputTokens:1, outputTokens:2}}`, `total_cost_usd: 0.5`, `result: 'ok'` | `output: 'ok'`, `tokenUsage: {prompt: 131, completion: 7, total: 138, completionDetails: {cacheReadInputTokens: 100, cacheCreationInputTokens: 20}}`, `cost: 0.5` |
| T-10 | R-25 | 성공 `result`에 `structured_output: {a:1}`, `result: '{"a":1}'` | `output`은 객체 `{a:1}`, `metadata.structuredOutput`도 같은 값 |
| T-11 | R-26 | `result.subtype: 'error_max_turns'`(SDK 값을 가정), 스트림에 어시스턴트 오류 `rate_limit` | `error: 'Claude Agent SDK call failed: error_max_turns (rate_limit)'`, `output` 없음, `tokenUsage`·`cost`·`metadata.skillCalls`·`metadata.toolCalls`는 있다 |
| T-12 | R-31 | 호출 전에 취소 신호가 이미 abort | `{error: 'Claude Agent SDK call aborted before it started'}`, SDK `query`가 불리지 않는다 |
| T-13 | R-28 | `resume: 'sid'`, 기준선 스냅샷 실패 | `tokenUsage: {}`, `cost: undefined`, `metadata.usageAccounting: 'unavailable'`, `metadata.sessionCost` 있음. 이때 `cost` 어서션은 throw |
| T-14 | R-52 | `copy_working_dir: true`와 `working_dir`를 설정한 채 평가기를 거치지 않고 `callApi`를 직접 호출 | throw `copy_working_dir runs each eval step in a fresh copy of working_dir ...`, SDK 호출 없음 |
| T-15 | R-53 | 평가기 단계에서 `copy_working_dir: true`, `working_dir`가 clean git 저장소 루트, 에이전트가 파일 하나를 수정 | 호출은 복사본 경로에서 이루어지고 응답 `metadata.workingDir`가 그 경로, `metadata.workspaceDiff`에 수정 diff가 있으며 어서션 후 복사본이 삭제된다. 원본 `working_dir`는 바뀌지 않는다 |
| T-16 | R-34, R-56 | OpenCode, `working_dir` 설정, `tools` 미설정 / `working_dir`도 없음 | 도구 맵이 `{'*': false, glob: true, grep: true, list: true, read: true}` / `{'*': false}`. 둘 다 `skill`이 꺼져 있어 세션 이력 조회를 하지 않는다. `tools: {skill: true}`를 주면 조회한다 |
| T-17 | R-34 | OpenCode `tools: {edit: true, write: false}` | `{error}`가 `OpenCode tools edit, write, patch, and apply_patch share one permission and cannot conflict`를 포함한다 |
| T-18 | R-36, R-37 | OpenCode, 프롬프트 호출이 `{error: {...}}`(data 없음)를 돌려준다고 가정 | `output: ''`, `error` 없음(`raw`에 오류 원문). SDK가 실제로 이렇게 반환하는지는 검증하지 않는다 |
| T-19 | R-40 | Codex SDK, provider `config: {sandboxMode: 'read-only'}` / 프롬프트 구성에만 알 수 없는 키 | 앞은 provider 로드가 `Invalid OpenAI Codex SDK config: ...`로 실패, 뒤는 키가 버려지고 호출이 진행된다 |
| T-20 | R-42 | Codex SDK, `working_dir` 없음, `process.cwd()`가 Git 저장소 밖 / `skip_git_repo_check: true` | 앞은 `{error: 'Error calling OpenAI Codex SDK: Working directory ... is not inside a Git repository ...'}`, 뒤는 진행(스레드 옵션에 `skipGitRepoCheck: true`) |
| T-21 | R-44 | Codex SDK `turn.usage = {input_tokens: 100, cached_input_tokens: 60, output_tokens: 20}`, `config.model: 'gpt-5.5'` / 모델 없음 | `tokenUsage: {prompt: 100, completion: 20, total: 120, cached: 60}`. `cost`는 앞은 가격표 추정, 뒤는 undefined |
| T-22 | R-46, R-48 | app-server 기본 구성 | `thread/start`에 `approvalPolicy: 'never'`, `sandbox: 'read-only'`, `ephemeral: true`; `turn/start`의 `sandboxPolicy`가 `{type:'readOnly', access:{type:'fullAccess'}, networkAccess:false}` |
| T-23 | R-49 | app-server가 `item/commandExecution/requestApproval`을 보냄, `server_request_policy` 없음 | `{decision: 'decline'}`로 응답하고 `metadata.codexAppServer.serverRequests`에 기록된다 |
| T-24 | R-59 | 캐시가 켜진 상태에서 Codex SDK에 같은 prompt를 두 번 | 두 번 모두 SDK를 호출하고 응답에 `cached`가 없다. Claude는 같은 인스턴스·같은 구성이면 둘째가 `cached: true`(response-cache R-25) |
| T-25 | R-03 | `openai:codex-sdk:gpt-5.5`에 `config.model: 'x'` | 모델은 `gpt-5.5`(경로 우선), `id()`는 `openai:codex-sdk:gpt-5.5` |
| T-26 | R-01 | `anthropic:claude-code` 문자열 항목 | `ClaudeCodeSDKProvider`, `id()`는 `anthropic:claude-agent-sdk`. `{id: 'anthropic:claude-code'}` 객체 항목이면 `id()`가 그 값 |
| T-27 | R-62 | Codex SDK, `config.model: 'gpt-5.5'`, `turn.usage = {input_tokens: 100, cached_input_tokens: 60, output_tokens: 20}` / 같은 사용량에 `model: 'gpt-5.5'`로 입력 토큰 300,000 / 모델명이 단가표에 없는 이름 | 첫째 `cost ≈ 8.3e-4`(`40×5e-6 + 60×0.5e-6 + 20×30e-6`). 둘째는 입력이 272,000을 넘어 `longContext` 단가(input `10/1e6`, output `45/1e6`)를 쓴다. 셋째는 `undefined` |
| T-28 | R-61 | app-server stdout에 `{"method":"x","params":{"a":"` 줄 다음 줄 `b"}}` | 첫 줄은 미완료로 버퍼에 남고(`Unterminated string`), 둘째 줄이 오면 두 줄을 `\n`으로 이은 뒤 문자열 안의 날 줄바꿈을 `\n`으로 이스케이프해 파싱하고 알림 하나를 처리한다. 유효하지 않은 한 줄(`not json`)은 경고 후 버리고, 누적이 5,000,000자를 넘으면 연결 실패다 |
| T-29 | R-20 | `ask_user_question: {behavior: 'first_option'}`, 에이전트가 질문 2개(첫째 선택지 `A`,`B`, 둘째 선택지 없음)로 `AskUserQuestion` 호출 / `Bash` 호출 / `behavior: 'deny'` | 첫째: `allow`, `answers`에 첫 질문만 `A`. 둘째: 사용자 `can_use_tool`이 없으면 `deny`(`Tool permission request is not handled ...`). 셋째: `deny`(`AskUserQuestion is disabled in automated evaluation mode`) |
| T-30 | R-03 | `openai:codex-sdk:gpt-live-x`에 `model_provider: openai`와 `base_url: https://api.openai.com/v1` / 같은 설정에서 `base_url` 없음 | 앞은 provider 로드가 `Use openai:live:gpt-live-x for GPT-Live sessions.`로 실패, 뒤는 검사 없이 생성된다 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]

| R-ID / T-ID | 근거 (repo@dfe2d45 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-21 `src/providers/registry.ts:532-547`, `src/providers/claude-agent-sdk.ts:1416-1453`(`providerId`), `src/providers/index.ts:154-158`(provider-contract C-08, `providerOptions.id = renderedId`) | 읽음. 문자열 항목이면 `options.id`가 없다는 것은 provider-contract R-14에서 가져옴 |
| R-02 | `src/providers/registry.ts:481-499`, `src/providers/opencode-sdk.ts:928-943` | 읽음 |
| R-03 | `src/providers/registry.ts:131, 1127-1148, 1160-1245`, `src/providers/openai/codex-sdk.ts:711-732`, C-37 | 읽음 |
| R-04 | `src/providers/claude-agent-sdk.ts:373-440`, `src/providers/opencode-sdk.ts:860-907`, `src/providers/openai/codex-sdk.ts:600-664`, `src/providers/openai/codex-app-server.ts:1792-1856` | 읽음. 설치 상태는 확인하지 않음 |
| R-05 | `src/providers/claude-agent-sdk.ts:1571-1584, 2622-2629`, `src/providers/openai/codex-sdk.ts:738-744`, `src/providers/openai/codex-app-server.ts:1318-1324`, `src/providers/opencode-sdk.ts:948-985`, `src/util/provider.ts:226-275`, `src/node/doEval.ts:739-760` | 읽음. OpenCode에 `requiresApiKey`가 없다는 것은 `grep`으로 확인. 사전 점검은 CLI eval 경로에서만 읽음(Node API 경로 미확인) |
| R-06 | C-03 `src/providers/claude-agent-sdk.ts:1465-1470`, `src/providers/opencode-sdk.ts:1384-1387`, `src/providers/openai/codex-sdk.ts:1991-2000`, `src/providers/openai/codex-app-server.ts:626-690(병합 함수), 1369-1377`, `src/util/render.ts:149-172`, `src/evaluator.ts:716-725, 887-889, 1870-1876` | 읽음. 테스트 `options` 병합은 `mergeProviderPromptConfig`에서 확인 |
| R-07 | C-14, `src/providers/claude-agent-sdk.ts:1664-1673, 1729-1737, 1751-1771`, `src/providers/openai/codex-sdk.ts:2151-2160`, `src/providers/openai/codex-app-server.ts:1622-1636` | 읽음 |
| R-08 | `src/providers/claude-agent-sdk.ts:1455-2024`(try는 2025부터), `src/providers/opencode-sdk.ts:2003-2012, 2179-2181`, `src/providers/openai/codex-sdk.ts:1999-2002, 2135-2142, 2192-2250`, `src/providers/openai/codex-app-server.ts:1449-1456, 1484-1490, 1598-1611` | try 경계를 줄 번호로 대조. provider-contract R-03 ③의 평가기 처리와 연결 |
| R-09 | `src/providers/claude-agent-sdk.ts:1925`, `src/providers/opencode-sdk.ts:1688-1690`, `src/providers/openai/codex-sdk.ts:1540-1585`, `src/providers/openai/codex-app-server.ts:2510-2575` | 읽음 |
| R-10 | C-04, `src/providers/claude-agent-sdk.ts:1859-1895, 2607-2615` | 읽음 |
| R-11 | C-04 `:1621-1640` | 읽음. `in` 연산자 사용을 코드 그대로 반영 |
| R-12 | C-04 `:1642-1662`, 문서 `site/docs/providers/claude-agent-sdk.md:352-366`(문서와 일치) | 읽음 |
| R-13 | C-02, C-03 `:1588-1610` | 읽음 |
| R-14 | C-03 `:1602-1610`, C-05 `:1706-1708`, 문서 `claude-agent-sdk.md:256-262` | 읽음. 모드의 SDK 동작은 미확인 |
| R-15 | C-05 `:1729-1733, 1772`, C-04 `:1651-1653`, 소스 주석 `:559-590`, 문서 `claude-agent-sdk.md:406-423, 483-535` | 읽음. 외부 SDK 발견·로딩은 읽지 않음. 줄 559-590은 주석(SDK의 설명을 옮긴 것) |
| R-16 | C-10, `src/providers/claude-agent-sdk.ts:1475-1477, 1868-1869` | 읽음 |
| R-17 | C-05 `:1710-1725, 1743` | 읽음 |
| R-18 | C-05 `:1702-1704, 1726, 1734, 1757-1758, 1776`, `src/providers/claude-agent-sdk.ts:1429-1448` | 읽음 |
| R-19 | C-05 `:1738-1741, 1760, 1774-1775`, `:1612-1619`, `:2431` | 읽음 |
| R-20 | C-06, `src/providers/claude-agent-sdk.ts:1164-1241, 1675-1684, 1782-1787, 2221-2226`, 문서 `claude-agent-sdk.md:977-1100` | 읽음. 조건 분기를 코드 순서대로 규칙화. 훅이 SDK에서 실제로 어떤 순서·우선순위로 판정되는지는 SDK 쪽 |
| R-21 | C-03 `:1482-1584`, `src/providers/agentWorkspace.ts:78-86` | 읽음 |
| R-22 | C-05, C-02 | 읽음. 알 수 없는 키 무시는 옵션 전달이 명시 매핑이라는 것으로 확인(스키마 검증 코드 없음, `src/contracts`·`src/validators`에서 `claude-agent-sdk` 검색 결과 없음) |
| R-23 | C-07 `:2185-2259` | 읽음 |
| R-24 | C-07 `:2167-2183, 2263-2273, 2300-2326` | 읽음 |
| R-25 | C-09 `:2459-2498` | 읽음 |
| R-26 | C-09 `:2500-2534` | 읽음. 서브타입 이름은 소스 주석(`:593`, `:2305-2310`)에만 있음 |
| R-27 | C-08 `:2350-2416` | 읽음 |
| R-28 | C-08 `:109-134, 1926-2010, 2327-2349, 2417-2431`, `src/assertions/cost.ts:12-15`, 문서 `claude-agent-sdk.md:1162-1166` | 읽음 |
| R-29 | C-09 `:2433-2434`, skill-calls-metadata 2.1 R-02~R-04 | 링크 |
| R-30 | `src/evaluator.ts:4506-4570`, `src/envars.ts:639-641`, `src/providers/opencode-sdk.ts:1551-1553`, `src/providers/openai/codex-app-server.ts:384-385, 1754-1756, 3093-3100` | 읽음. 평가기 쪽 동작은 경계만 확인 |
| R-31 | C-09 `:2595-2615`, `:1460-1462, 1861-1863, 1890-1905` | 읽음 |
| R-32 | C-09 `:2595-2615` | 읽음 |
| R-33 | C-17, `src/providers/opencode-sdk.ts:822-855` | 읽음. SDK의 서버 기동 동작은 미확인 |
| R-34 | C-16, `src/providers/opencode-sdk.ts:1602-1625, 1812-1822`, 문서 `opencode-sdk.md:267-297` | 읽음 |
| R-35 | C-19, `src/providers/opencode-sdk.ts:1153-1159, 1348-1365, 1457-1484, 1888-1896`, `src/providers/agenticRunQueue.ts` | 읽음 |
| R-36 | C-20 `:641-668, 1898-1964`, skill-calls-metadata R-05~R-07 | 읽음 |
| R-37 | C-20 `:1966-2001, 2067-2178` | 읽음. `grep -n "\.error"`에서 SDK 결과의 `error` 필드 검사가 없음을 확인 |
| R-38 | C-18 `:1422-1455`, `:1114-1128`, `:1133-1158, 2051` | 읽음. 임시 디렉터리가 어디에도 전달되지 않음은 `workingDir` 사용처 검색으로 확인. 문서 `opencode-sdk.md:85`는 "임시 디렉터리에서 실행"이라고 서술해 구현과 차이(아래) |
| R-39 | C-18 `:1391-1410` | 읽음 |
| R-40 | C-22 | 읽음. 문서 `openai-codex-sdk.md:218`과 일치 |
| R-41 | C-23, `src/providers/openai/codex-sdk.ts:738-744, 1014-1032`, `src/providers/credentials.ts`(`resolveProviderApiKey`) | 읽음 |
| R-42 | C-24, `src/providers/openai/codex-sdk.ts:1034-1055, 2151-2160, 2192-2196` | 읽음. 문서 `openai-codex-sdk.md:140, 225-238`의 기본값 열과 대조(아래) |
| R-43 | C-24 `:1057-1117`, `src/providers/openai/codex-sdk.ts:1911-1983, 2376-2391, 2534-2547` | 읽음 |
| R-44 | C-25, C-33, 문서 `openai-codex-sdk.md:33, 293, 750` | 읽음 |
| R-45 | C-25, C-26 | 읽음. 429 변환 존재는 `src/providers`에서 `rateLimitKind`·`retry-after-ms` 검색으로 확인(4개 provider 중 Codex SDK만) |
| R-46 | C-27, C-28 `:1449-1473`, C-32 `:3529-3560` | 읽음 |
| R-47 | C-29, `src/providers/openai/codex-app-server.ts:1734-1741, 1195-1207, 1230-1245` | 읽음. 줄 읽기는 R-61(C-35) |
| R-61 | C-35 | 읽음. 규칙은 코드의 분기 순서 그대로이고 T-28은 코드 논리에서 도출 |
| R-62 | C-33, C-36, `src/providers/openai/codex-sdk.ts:2495-2532`, `src/providers/openai/codex-app-server.ts:3513-3518` | 읽음. 모델별 단가 전체는 읽지 않고 구조와 `gpt-5.5` 항목(`util.ts:592-600`, `billing.ts:76-120`의 캐시 읽기 단가)만 확인. 목록 밖 모델이 undefined가 되는 것은 `getModelRates`→`calculateCustomUsageCost` 분기에서 도출 |
| R-48 | C-30 | 읽음 |
| R-49 | C-31 `:2884-3068`, 문서 `openai-codex-app-server.md:188, 247-300` | 읽음 |
| R-50 | C-31, C-32 `:3207-3284, 3453-3512`, `:2912-2926` | 읽음 |
| R-51 | 표 1-H의 각 근거: R-11/R-12(Claude), R-34(OpenCode), R-42(Codex SDK), R-46/R-48(app-server) | 종합. 쓰기 가능성의 최종 판단은 SDK의 권한 규칙이 하므로 `미확인` 표시 |
| R-52 | C-11, C-12, `src/providers/claude-agent-sdk.ts:456, 1470`, `src/providers/opencode-sdk.ts:305, 1222, 1388`, `src/providers/openai/codex-sdk.ts:248, 411, 2001`, `src/providers/openai/codex-app-server.ts:555, 1714`, `src/matchers/agent.ts:54-61` | 읽음. git 복제 가능 조건의 세부(속성·eol·상태 검사)는 C-12를 그대로 참조 |
| R-53 | C-13, `src/providers/agentWorkspace.ts:524-634`(diff), `:400-427`(종료 정리) | 읽음 |
| R-54 | `src/providers/claude-agent-sdk.ts:1482-1506`, `src/providers/opencode-sdk.ts:1162-1226`, C-23 | 읽음. 셸 노출은 추론 |
| R-55 | C-05, C-04 `:1651-1653`, 문서 `claude-agent-sdk.md:483-535`, `site/docs/guides/test-agent-skills.md:41-92` | 읽음 |
| R-56 | C-16, `src/providers/opencode-sdk.ts:1812-1822, 2136-2153`, 문서 `opencode-sdk.md:410-447`, `test-agent-skills.md:196-205` | 읽음 |
| R-57 | C-23, `src/providers/openai/codex-sdk.ts:934-975`, 문서 `openai-codex-sdk.md:711-750` | 읽음 |
| R-58 | C-30 `:2510-2575`, `src/providers/openai/codex-app-server.ts:3780-3819`, 문서 `openai-codex-app-server.md:329-349` | 읽음 |
| R-59 | response-cache R-20~R-27과 같은 파일 C-10~C-12, `src/providers/openai/codex-sdk.ts`·`codex-app-server.ts`에서 `cache` 모듈 import 부재(검색) | 링크·검색. 문서 차이는 아래 |
| T-01~T-30 | 해당 R-ID 근거에서 도출. 실행하지 않음 | 모두 코드 논리 도출이다. 실제 실행 결과와 대조하지 않았다 |

문서와 구현의 차이·특이점:
- `site/docs/providers/openai-codex-sdk.md:836-857`은 이 provider가 응답을 자동 캐시하고 `options.bustCache`로 읽기를 막을 수 있다고 쓴다. 구현은 두 Codex provider 모두 `cache` 모듈을 가져오지 않고, `generateCacheKey`/`cacheKey`는 스레드 풀 키일 뿐이다(R-43, R-59). 구현을 사실로 썼다.
- `site/docs/providers/opencode-sdk.md:85, 267`은 `working_dir`가 없으면 임시 디렉터리에서 실행하고 호출이 끝나면 지운다고 쓴다. 구현은 임시 디렉터리를 만들고 지우지만 서버 세션의 `directory`로 넘기지 않는다(R-38). 구현을 사실로 썼고 서버의 실제 cwd는 미확인이다.
- `site/docs/providers/openai-codex-sdk.md:230`의 `sandbox_mode` 기본값 `workspace-write`와 `approval_policy` "SDK default"는 promptfoo가 값을 채우지 않는다는 점(R-42)에서 SDK 기본값 주장이다. 코드로 확인하지 못했다.
- `OpenCodeSDKConfig.max_retries`(타입 주석 "Maximum retries for API calls, default 2")는 코드 어디서도 읽지 않는다. 문서 표에도 없다.
- `site/docs/providers/claude-agent-sdk.md:1291`은 설정에 `bustCache: true`를 넣으면 읽기를 막는다고 쓰나 코드는 `context.bustCache`만 읽는다(response-cache 2.1이 같은 차이를 적었다).
- `site/docs/guides/test-agent-skills.md`와 문서의 `skills:` 필터가 SDK 0.2.120에서 추가됐다는 서술과 코드의 SDK 범위 `^0.3.273`은 서로 다른 시점이다(overview 2절, 차이가 아닐 수 있음 — 추론).
- `site/docs/providers/claude-agent-sdk.md`는 `effort`의 기본값을 `high`로 쓰나 promptfoo는 값을 채우지 않는다(R-18). 문서는 SDK 기본을 서술한 것으로 보이며 `미확인`이다.

### 2.2 코드 읽는 순서 [선택]

1. 등록: `src/providers/registry.ts`의 네 factory(C-21)로 어떤 클래스가 만들어지는지 본다.
2. 대표: `src/providers/claude-agent-sdk.ts`를 `ClaudeCodeOptions`(C-01) → `callApi` 앞부분(C-03, C-04, C-05) → 스트림 루프(C-07) → 응답 구성(C-08, C-09) 순으로 읽는다. 캐시 부분(`:1780-1866`)은 response-cache가 다룬다.
3. 격리: `src/providers/agentWorkspace.ts`(C-11, C-12)와 `src/evaluator.ts:1823-1891`(C-13).
4. 차이: OpenCode(`:1034-1112`, `:1383-1484`, `:1898-2187`) → Codex SDK(`:214-463`, `:1985-2250`) → app-server(`:1442-1620`, `:2404-2508`).
구현 전략: 외부 SDK를 정적 import하지 않고 첫 호출 때 동적으로 로드해 설치하지 않은 사용자에게 비용을 주지 않는다. 도구·권한 기본값은 "허용 목록이 곧 가용 도구 집합"(Claude), "와일드카드 거부 + 읽기 도구 허용"(OpenCode), "읽기 전용 샌드박스 + 승인 never"(app-server)로 provider마다 다른 방식으로 안전 쪽에 두었다.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드를 복사하지 않았다.

## 적용 메모 [선택]
(목적: 내 스킬(SKILL.md)을 Claude Code·Codex 같은 CLI 환경에서 실제로 쓰는 방식 그대로 평가하고, 여러 모델에 비교하고 기록하는 환경. 아래는 원본 동작을 바꾸자는 제안이 아니라 가져올 때 알아야 할 점이다.)

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-11, R-12, R-15 | 원본 기본값(읽기 전용 도구, `setting_sources: []`)은 "격리된 안전 기본값"이고 실제 CLI 사용과 다르다. 실사용 근사 프로파일은 `setting_sources: ['project']` + `skills` + 필요한 쓰기·셸 도구 + `permission_mode`를 명시해야 한다. 두 프로파일(격리 / 실사용 근사)을 설정 단계에서 구분해 기록하는 편이 안전하다 | 어떤 도구·설정 원천을 열었는지가 스킬 결과를 바꾼다 | 결과 레코드에 유효 옵션(도구 집합·권한 모드·설정 원천)을 남기도록 필드 추가 |
| R-55~R-58 | 스킬을 넣는 방법을 런타임별로 한 인터페이스로 감싼다: 스킬 디렉터리를 fixture 작업 디렉터리 안(`.claude/skills` 또는 `.agents/skills`)에 복사해 넣고 `working_dir`로 가리킨다. 이러면 response-cache의 mtime 지문 범위 안에 들어간다 | `working_dir` 밖 스킬은 캐시 키에 안 들어가고 SDK의 발견 규칙도 `미확인`이다 | 스킬 버전별 fixture 디렉터리 생성 단계가 추가된다. OpenCode는 `tools.skill: true`+`permission.skill: allow`를 같이 켜야 한다 |
| R-25, R-36, R-44 | 출력 타입이 런타임마다 다르다(Claude 구조화 출력은 객체, Codex·OpenCode는 JSON 문자열). 비교 레코드에는 원본 출력과 "문자열로 직렬화한 값"을 분리해 둔다 | 같은 어서션을 여러 런타임에 쓰려면 정규화가 필요하다 | 어서션 입력 정규화 단계 |
| R-27, R-28, R-44, R-50 | 토큰·비용 의미가 다르다: Claude는 prompt에 캐시 읽기·쓰기가 합산되고 `cached`는 비어 있다. Codex는 `input_tokens`에 캐시가 포함되고 `cached`가 따로 있다. OpenCode는 `input`과 `cache`가 분리돼 있다. 비용은 "SDK 보고 / promptfoo 추정 / 없음"의 출처를 함께 기록한다 | 모델 간 비용 비교가 같은 정의에서 나와야 한다 | `{input, output, cacheRead, cacheWrite, reasoning, costSource}` 같은 정규화 필드를 원자료와 함께 저장 |
| R-52, R-53 | `copy_working_dir`의 git 복제(`clone --shared`)와 `workspaceDiff`는 "에이전트가 무엇을 바꿨는지"를 기록하는 데 그대로 가치가 있다. 복잡한 부분(저장소 속성·eol·심볼릭 링크 검사)은 처음에는 `'copy'` 모드(전체 복사)만 구현해도 된다 | 구현 비용 대비 격리 이득이 크고, 'copy'는 조건이 단순하다 | 복제 가능성 판정(C-12)을 생략하면 diff는 복사 전 스냅샷과의 파일 비교로 대체해야 한다 |
| R-30 | 에이전트 호출은 오래 걸릴 수 있는데 원본은 provider 자체 타임아웃이 없다. 모델 비교 실행에서는 평가기 단계 타임아웃과 `max_turns`·`max_budget_usd`를 항상 설정하는 편이 낫다 | 한 행이 멈추면 비교가 끝나지 않는다 | 실행 프로파일의 필수 설정으로 승격 |
| R-03, R-56, R-57 | 여러 모델 비교 시 Claude Agent SDK는 Claude 계열 전용으로 보이므로(추론) 다른 벤더 모델은 OpenCode(`provider_id`+`model`) 또는 Codex(`model_provider`+`model`)로 같은 스킬 fixture를 돌려야 한다. Codex의 `skillCalls`는 추정이라 보조 증거로만 쓴다 | 런타임마다 스킬 호출 증거의 신뢰도가 다르다(skill-calls-metadata) | 레코드에 `source`(tool / heuristic)를 같이 저장 |
