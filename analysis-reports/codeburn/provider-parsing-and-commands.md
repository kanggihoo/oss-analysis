# codeburn provider 파싱과 주요 CLI 명령 추가 조사

## 1. 주요 provider 파싱 구조

CodeBurn의 공통 provider 계약은 `src/providers/types.ts`의 `Provider`다. 각 provider는 `discoverSessions()`로 원천 파일/DB를 찾고, `createSessionParser()`가 `ParsedProviderCall`을 스트리밍한다. 이후 `src/parser.ts`의 `parseProviderSources()`가 `ParsedProviderCall -> ParsedTurn -> ClassifiedTurn -> SessionSummary -> ProjectSummary`로 정규화한다.

단, Claude는 예외다. `src/providers/claude.ts`는 session source 발견만 담당하고, 실제 JSONL 파싱은 `src/parser.ts`의 Claude 전용 경로가 직접 처리한다.

## 2. Gemini 파싱

근거 파일:
- `src/providers/gemini.ts`
- `docs/providers/gemini.md`

읽는 위치:

```text
~/.gemini/tmp/<project>/chats/session-*.json
~/.gemini/tmp/<project>/chats/session-*.jsonl
```

발견 방식:
- `getGeminiTmpDir()`가 `~/.gemini/tmp`를 기준 디렉터리로 잡는다.
- `discoverSessions()`가 하위 project dir을 순회하고, 각 project의 `chats` 아래에서 `session-*.json` 또는 `session-*.jsonl` 파일만 source로 등록한다.

파싱 방식:
- `createParser()`가 파일 전체를 읽는다.
- 먼저 단일 JSON 세션 형식으로 `JSON.parse(raw)`를 시도한다.
- 실패하면 JSONL로 간주하고 `parseJsonl()`이 줄 단위로 파싱한다.
- JSONL에서는 session metadata line과 message line을 모아 `GeminiSession`을 만든다.

집계 방식:
- `parseSession()`은 `type === 'gemini'`이고 `tokens`와 `model`이 있는 메시지만 대상으로 삼는다.
- 한 Gemini session 전체를 하나의 `ParsedProviderCall`로 접는다.
- dedup key는 `gemini:<sessionId>`라서 같은 세션은 한 번만 집계된다.
- `input`, `output`, `cached`, `thoughts`를 세션 전체에서 합산한다.
- Gemini는 cached token이 input token에 포함되어 있다고 보고, `freshInput = totalInput - totalCached`로 분리한다.
- `thoughts`는 보고서에는 `reasoningTokens`로 보존하지만 비용 계산에서는 output rate로 과금하기 위해 `totalOutput + totalThoughts`를 `calculateCost()`에 넘긴다.

도구/명령 처리:
- `toolCalls`의 `displayName` 또는 `name`을 `toolNameMap`으로 `Read`, `Write`, `Edit`, `Bash`, `WebSearch` 같은 공통 도구명으로 바꾼다.
- Bash로 매핑된 tool call에 `args.command`가 있으면 `extractBashCommands()`로 shell command breakdown에 들어갈 명령을 추출한다.

주의점:
- 세션 전체를 하나의 call로 접기 때문에 Claude/Codex보다 turn 단위 세밀도가 낮다.
- provider-level 캐시는 없다.
- docs 기준 Gemini provider 전용 테스트는 아직 없다.

## 3. Claude 파싱

근거 파일:
- `src/providers/claude.ts`
- `src/parser.ts`
- `docs/providers/claude.md`

읽는 위치:

```text
Claude Code CLI:
$CLAUDE_CONFIG_DIR/projects
~/.claude/projects

Claude Desktop local agent mode:
macOS:   ~/Library/Application Support/Claude/local-agent-mode-sessions
Windows: %APPDATA%/Claude/local-agent-mode-sessions
Linux:   ~/.config/Claude/local-agent-mode-sessions
```

발견 방식:
- `getClaudeConfigDirs()`가 `CLAUDE_CONFIG_DIRS`, `CLAUDE_CONFIG_DIR`, 기본 `~/.claude` 순서로 config dir을 결정한다.
- `discoverSessions()`는 각 config dir의 `projects` 하위 디렉터리를 `SessionSource`로 등록한다.
- Claude Desktop은 `findDesktopProjectDirs()`가 최대 depth 8까지 내려가며 `projects` 디렉터리를 찾는다.

중요한 예외:
- `src/providers/claude.ts`의 `createSessionParser()`는 빈 async generator다.
- 즉, Claude는 provider parser를 쓰지 않고 `src/parser.ts`의 `parseAllSessions()`에서 `claudeSources`만 따로 분리한 뒤 `scanProjectDirs()`로 직접 처리한다.

파싱 방식:
- `scanProjectDirs()`가 각 project dir 안의 `.jsonl` 파일을 찾는다.
- `collectJsonlFiles()`는 `<project>/*.jsonl`뿐 아니라 `<project>/<subdir>/subagents/*.jsonl`도 같이 수집한다.
- `parseSessionFile()`이 `readSessionLines()`로 JSONL을 스트리밍하고, 각 line을 `parseJsonlLine()`으로 `JournalEntry`로 만든다.
- `dedupeStreamingMessageIds()`가 streaming/resumed message 중복을 message id 기준으로 제거한다.
- `groupIntoTurns()`가 user entry를 기준으로 assistant call들을 turn으로 묶는다.
- assistant entry는 `parseApiCall()`에서 `ParsedApiCall`로 변환된다.

토큰/비용 처리:
- `parseApiCall()`은 assistant message의 `usage`와 `model`이 있을 때만 call로 인정한다.
- `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `server_tool_use.web_search_requests`를 읽는다.
- `extractClaudeCacheCreation()`은 Claude cache write가 5분/1시간 split으로 들어오는 경우를 처리한다.
- 1시간 cache write token은 `calculateCost()`의 `oneHourCacheCreationTokens` 인자로 전달되어 별도 배율이 적용된다.

도구/명령/MCP 처리:
- assistant content의 `tool_use` block에서 tool name을 추출한다.
- `mcp__<server>__<tool>` 형태는 MCP tool로 분리한다.
- `Skill` tool은 skill 이름을 따로 뽑는다.
- Bash tool의 command 문자열은 `extractBashCommandsFromContent()`에서 추출된다.
- `extractMcpInventory()`는 `attachment.type === "deferred_tools_delta"`의 `addedNames`를 union해 세션에 사용 가능했던 MCP tool inventory를 만든다.

프로젝트 경로 처리:
- project dir 이름은 보통 `/`가 `-`로 바뀐 slug다.
- `extractCanonicalCwd()`가 JSONL entry의 `cwd`를 찾으면 canonical project path로 사용하고, `scanProjectDirs()`는 cwd-keyed entry와 slug-keyed entry를 병합한다.

주의점:
- Claude 파싱 버그는 `src/providers/claude.ts`가 아니라 대부분 `src/parser.ts`를 봐야 한다.
- provider-level 캐시는 없고, 일별 집계 캐시만 사용한다.

## 4. Codex 파싱

근거 파일:
- `src/providers/codex.ts`
- `docs/providers/codex.md`

읽는 위치:

```text
$CODEX_HOME/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

발견 방식:
- `getCodexDir()`가 `CODEX_HOME` 또는 `~/.codex`를 기준으로 잡는다.
- `discoverSessionsInDir()`는 `sessions/<YYYY>/<MM>/<DD>`만 정규식으로 순회한다.
- 파일명은 `rollout-*.jsonl`만 인정한다.
- 첫 줄은 `session_meta`여야 하고, `payload.originator`가 `codex`로 시작해야 유효한 Codex session으로 본다.
- 첫 줄 읽기는 1MB로 제한한다. Codex session_meta에 큰 system prompt가 들어가는 경우를 고려한 처리다.

캐시:
- `readCachedCodexResults()`가 있으면 cached `ParsedProviderCall`을 바로 yield한다.
- 캐시는 `src/codex-cache.ts`가 관리하며 file fingerprint, 즉 `mtimeMs + sizeBytes` 기반이다.
- 파싱이 끝나면 `writeCachedCodexResults()`로 결과를 저장하고, `parseProviderSources()`의 finally에서 `flushCodexCache()`가 호출된다.

파싱 방식:
- 파일은 `readSessionLines()`로 줄 단위 스트리밍한다. 대형 rollout 파일을 전체 문자열로 올리지 않기 위한 구조다.
- `session_meta`에서 `sessionId`와 session-level model을 얻는다.
- `turn_context`에서 model이 있으면 현재 session model을 갱신한다.
- `response_item/function_call`은 tool call로 보고 `toolNameMap`으로 `Bash`, `Read`, `Edit`, `Agent`, `Glob` 등으로 매핑한다.
- `event_msg/patch_apply_end`는 `Edit` tool로 간주한다.
- user message와 assistant output text는 pending 상태로 모아둔다.
- `event_msg/token_count`가 나오면 그 시점까지의 pending user/tool/output과 token 정보를 하나의 `ParsedProviderCall`로 만든다.

토큰/비용 처리:
- token_count에 `info.last_token_usage`가 있으면 해당 값을 turn 단위 사용량으로 사용한다.
- `last_token_usage`가 없고 `total_token_usage`만 있으면 이전 누적값과의 delta를 계산한다.
- token info 자체가 없으면 user/assistant text 길이를 `CHARS_PER_TOKEN = 4`로 나눠 추정하고 `costIsEstimated: true`를 붙인다.
- OpenAI 계열은 cached token이 input token에 포함되므로 `uncachedInputTokens = inputTokens - cachedInputTokens`로 정규화한다.
- reasoning token은 `reasoningTokens`로 보존하지만 비용 계산에서는 output token에 더해 `calculateCost(model, uncachedInputTokens, outputTokens + reasoningTokens, ...)`를 호출한다.

dedup:
- 실제 token event는 `codex:<sessionId>:<timestamp>:<cumulativeTotal>`.
- 추정 fallback은 `codex:<sessionId>:<timestamp>:est<n>`.
- `prevCumulativeTotal`은 `null` sentinel로 시작한다. 첫 event가 cumulative total 0이어도 중복으로 버려지지 않게 하기 위한 처리다.

주의점:
- Codex는 Gemini보다 세밀하다. token_count event마다 call을 만들기 때문에 turn에 가까운 비용 흐름을 볼 수 있다.
- Bash command 자체는 현재 Codex parser에서 `bashCommands: []`로 저장된다. tool은 `Bash`로 잡히지만 command breakdown까지는 추출하지 않는다.

## 5. 공통 정규화 흐름

`parseAllSessions()` 기준으로 보면 흐름은 다음과 같다.

```text
discoverAllSessions(providerFilter)
  -> claudeSources / nonClaudeSources 분리
  -> Claude: scanProjectDirs() 직접 처리
  -> Non-Claude: provider별 parseProviderSources()
  -> providerCallToTurn()
  -> classifyTurn()
  -> buildSessionSummary()
  -> ProjectSummary[]
  -> 같은 project 이름끼리 merge
```

즉, Gemini와 Codex는 provider 파일에서 `ParsedProviderCall`을 만들고, Claude는 `parser.ts`가 직접 `ParsedApiCall`과 `ParsedTurn`을 만든다. 최종적으로는 모두 `ProjectSummary[]`로 합쳐지기 때문에 dashboard/report/export/compare/optimize가 같은 데이터 구조를 사용한다.

## 6. 주요 CLI 명령 의미

### `codeburn report --format tui|json`

기본 명령이다. `codeburn`만 실행해도 `report`가 실행된다.

의미:
- 선택 기간의 전체 사용량 대시보드 또는 JSON 리포트를 만든다.
- 기본 기간은 `week`, 기본 format은 `tui`.
- `--period`, `--from`, `--to`, `--provider`, `--project`, `--exclude`, `--refresh`를 지원한다.

동작:
- `--format tui`: `renderDashboard()`를 호출해 Ink TUI를 띄운다.
- `--format json`: `parseAllSessions()` 후 `buildJsonReport()` 형태로 비용, daily, projects, models, activities, tools, MCP, shell commands, topSessions를 JSON 출력한다.
- `--from/--to`가 있으면 `--period`보다 우선한다.

### `codeburn status --format terminal|json|menubar-json`

짧은 상태 출력용 명령이다. 특히 macOS/GNOME GUI 클라이언트의 데이터 공급 계약이다.

format별 의미:
- `terminal`: 월간 사용량을 compact one-liner로 출력한다.
- `json`: today/month의 cost와 calls, plan 정보를 짧은 JSON으로 출력한다.
- `menubar-json`: 메뉴바/패널 UI가 소비하는 상세 payload를 출력한다. `current`, `providers`, `history.daily`, `optimize`를 포함한다.

특징:
- `--period`는 `menubar-json`의 primary period로 쓰인다.
- `--no-optimize`는 menubar-json에서 optimize finding 계산을 생략해 빠르게 만든다.
- provider가 `all`이면 과거 날짜는 daily cache에서 가져오고 오늘만 다시 파싱한다.

### `codeburn export -f csv|json`

분석 결과를 파일로 저장하는 명령이다.

기본 동작:
- `--from/--to`가 없으면 Today, 7 Days, 30 Days 세 기간을 export한다.
- `--from/--to`가 있으면 해당 custom period 하나만 export한다.
- `--provider`, `--project`, `--exclude` 필터를 지원한다.

CSV:
- output path를 디렉터리로 취급한다.
- `summary.csv`, `daily.csv`, `activity.csv`, `models.csv`, `projects.csv`, `sessions.csv`, `tools.csv`, `shell-commands.csv`, `README.txt`를 만든다.
- `.codeburn-export` marker가 없는 기존 디렉터리는 덮어쓰지 않는다.

JSON:
- `schema: codeburn.export.v2`를 가진 단일 JSON 파일을 쓴다.
- summary, periods, projects, sessions, tools, shellCommands를 포함한다.
- 기존 JSON이 CodeBurn export schema로 보이지 않으면 덮어쓰지 않는다.

### `codeburn today`

오늘 범위로 `report`를 실행하는 단축 명령이다.

의미:
- 오늘 00:00부터 현재까지의 사용량을 TUI 또는 JSON으로 보여준다.
- `--format tui|json`, `--provider`, `--project`, `--exclude`, `--refresh`를 지원한다.

동작:
- JSON이면 `runJsonReport('today', ...)`.
- TUI면 `renderDashboard('today', ...)`.

### `codeburn month`

이번 달 범위로 `report`를 실행하는 단축 명령이다.

의미:
- 이번 달 1일부터 오늘까지의 사용량을 TUI 또는 JSON으로 보여준다.

동작:
- JSON이면 `runJsonReport('month', ...)`.
- TUI면 `renderDashboard('month', ...)`.

### `codeburn optimize`

토큰 낭비 패턴을 찾고 수정 액션을 제안하는 명령이다.

의미:
- 기본 30일 기간의 프로젝트 사용량과 세션 파일을 분석해 waste finding을 만든다.
- 중복 read, junk directory read, MCP tool 과다 노출, unused MCP, bloated `CLAUDE.md`, low read/edit ratio, cache bloat, ghost agents/skills/commands, bash output bloat, low-worth sessions, context bloat, session outlier 등을 탐지한다.

동작:
- `parseAllSessions(range, provider)`로 프로젝트를 만든다.
- `runOptimize(projects, label, range)`가 finding을 계산하고 출력한다.

### `codeburn compare`

두 모델을 선택해 비용/효율을 비교하는 대화형 명령이다.

의미:
- 지정 기간의 모델 사용 통계를 만들고, Ink UI에서 두 모델을 골라 side-by-side 비교한다.
- 기본 기간은 `all`, 즉 코드상 "최근 6개월" 범위다.

동작:
- `renderCompare(range, provider)`를 호출한다.
- 내부적으로 `compare-stats.ts`의 모델별 비용, token, one-shot, retry, category 비교 로직을 사용한다.

### `codeburn models`

모델별 토큰/비용 테이블을 출력하는 명령이다.

의미:
- provider/model 기준으로 input/output/cache token, calls, cost를 보여준다.
- `--by-task`를 주면 `(provider, model, task)` 단위로 펼친다.

옵션:
- `--period`, `--from`, `--to`
- `--provider`
- `--task`
- `--by-task`
- `--top`
- `--min-cost`
- `--format table|markdown|json|csv`
- `--no-totals`

동작:
- `aggregateModels(projects, opts)`로 row를 만들고 format별 renderer로 출력한다.

### `codeburn yield`

실험적 기능이다. AI 비용이 실제로 main에 들어간 작업인지, revert/abandoned인지 추적한다.

의미:
- 지정 기간의 세션과 현재 git 저장소의 commit/revert 정보를 비교해 productive/reverted/abandoned spend를 추정한다.
- 기본 기간은 `week`.

동작:
- `computeYield(range, process.cwd())`를 실행하고 `formatYieldSummary()`로 출력한다.

주의:
- 현재 working directory의 git history에 의존한다.
- README에서도 experimental로 소개된다.

## 7. 한 줄 요약

- Gemini: `~/.gemini/tmp/.../session-*`을 읽어 세션 전체를 하나의 call로 합산한다.
- Claude: provider는 디렉터리 발견만 하고, `parser.ts`가 JSONL을 직접 turn 단위로 파싱한다.
- Codex: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`을 스트리밍하며 `token_count` 이벤트마다 call을 만든다.
- 명령어는 크게 `report/today/month` 대시보드, `status` 경량 상태/GUI 계약, `export` 파일 출력, `optimize/compare/models/yield` 분석 보조 기능으로 나뉜다.
