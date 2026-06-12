---
title: CodeBurn Codex Provider
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence, deepwiki]
sources:
  - artifacts/codeburn/deepwiki/pages-md/4.3-other-providers-(codex-copilot-opencode-piomp-and-more).md
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-provider-plugin-system.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - repos/codeburn/src/providers/codex.ts
  - repos/codeburn/src/codex-cache.ts
  - repos/codeburn/src/fs-utils.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/providers/index.ts
  - repos/codeburn/tests/providers/codex.test.ts
  - repos/codeburn/tests/provider-registry.test.ts
confidence: high
---
# CodeBurn Codex Provider

이 페이지는 [[codeburn-provider-plugin-system]]의 child-level deep dive로, DeepWiki `4.3 Other Providers` 중 Codex provider를 중심으로 정리한다. DeepWiki는 외부 baseline이고, 아래 내용은 현재 `repos/codeburn` source를 직접 확인해 기록한다. 전체 provider registry와 parser/cache boundary는 [[codeburn-provider-plugin-system]], 더 넓은 ingestion/cache flow는 [[codeburn-data-ingestion-and-caching]]를 참조한다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## Role in the registry

Codex는 optional lazy provider가 아니라 core provider다. `src/providers/index.ts`가 `./codex.js`를 정적 import하고, `coreProviders` 배열에 `codex`를 포함한다. 따라서 `providers` export와 `getAllProviders()` 모두 Codex를 포함한다. (`repos/codeburn/src/providers/index.ts:1-19`, `repos/codeburn/src/providers/index.ts:155-174`)

Codex provider object는 `createCodexProvider()`에서 만들어진다. Provider id는 `codex`, display name은 `Codex`, `discoverSessions()`는 Codex session directory를 scan하고, `createSessionParser()`는 JSONL parser를 반환한다. (`repos/codeburn/src/providers/codex.ts:603-631`)

## Data source discovery

Codex root directory는 다음 priority로 결정된다. (`repos/codeburn/src/providers/codex.ts:78-80`)

```text
createCodexProvider(codexDir override)
→ CODEX_HOME
→ ~/.codex
```

Discovery는 root 아래 `sessions/YYYY/MM/DD/` 구조를 순회하고, 파일명은 `rollout-*.jsonl`만 인정한다. 파일 첫 줄은 `session_meta`여야 하고 `payload.originator`가 case-insensitive로 `codex`로 시작해야 valid Codex session으로 인정된다. Project key는 `session_meta.payload.cwd`에서 leading slash를 제거하고 `/`를 `-`로 바꾼 값이다. (`repos/codeburn/src/providers/codex.ts:82-135`, `repos/codeburn/src/providers/codex.ts:249-298`)

```text
~/.codex/sessions/2026/04/14/rollout-abc123.jsonl
first line: { type: "session_meta", payload: { originator: "codex-cli", cwd: "/Users/test/myproject" } }
→ SessionSource { provider: "codex", project: "Users-test-myproject" }
```

Codex cache에 file fingerprint가 일치하는 project가 있으면 discovery는 첫 줄을 다시 parsing하지 않고 cached project를 사용한다. (`repos/codeburn/src/providers/codex.ts:281-285`, `repos/codeburn/src/codex-cache.ts:71-80`)

## Large JSONL handling

Codex CLI 0.128+는 첫 `session_meta` line에 system prompt/base instructions를 넣어 20KB 이상이 될 수 있다. 현재 source는 고정 작은 buffer가 아니라 `createReadStream()` + `readline`으로 첫 줄을 읽고, `FIRST_LINE_READ_CAP = 1MB`까지만 허용한다. (`repos/codeburn/src/providers/codex.ts:86-127`)

전체 session parse도 file 전체를 string으로 읽지 않는다. Codex parser는 `readSessionLines(source.path, undefined, { largeLineAsBuffer: true })`를 사용한다. `readSessionLines()`는 stream cap 2GB를 두고, 32KB보다 큰 line은 Buffer로 넘길 수 있다. Codex source comment에는 heavy user session이 250MB를 넘을 수 있어 whole-file read/split을 피한다고 명시되어 있다. (`repos/codeburn/src/fs-utils.ts:4-15`, `repos/codeburn/src/fs-utils.ts:78-115`, `repos/codeburn/src/providers/codex.ts:349-354`)

Buffer path의 `parseCodexLine()`은 full JSON parse 대신 head 64KB에서 필요한 string field를 뽑고, user/assistant text는 최대 2000 chars 수준의 compact representation으로 제한한다. (`repos/codeburn/src/providers/codex.ts:74-76`, `repos/codeburn/src/providers/codex.ts:138-247`)

## Parser event flow

Codex parser는 다음 event들을 축적하다가 `event_msg`의 `token_count`에서 하나의 `ParsedProviderCall`을 emit한다.

```text
session_meta → sessionId, fork metadata, session model
turn_context → session model update
response_item:function_call → pending tools + toolSequence
patch_apply_end → pending Edit toolSequence
response_item:user message → pendingUserMessage + new turnId
response_item:assistant message → pendingOutputChars
response_item/event_msg:token_count → ParsedProviderCall
```

근거: `repos/codeburn/src/providers/codex.ts:359-428`.

`function_call`은 `toolNameMap`으로 canonical name에 매핑된다. 현재 mapping은 다음과 같다. (`repos/codeburn/src/providers/codex.ts:31-41`)

| Raw Codex tool | CodeBurn tool |
|---|---|
| `exec_command` | `Bash` |
| `read_file` | `Read` |
| `write_file` | `Edit` |
| `apply_diff`, `apply_patch` | `Edit` |
| `spawn_agent`, `close_agent`, `wait_agent` | `Agent` |
| `read_dir` | `Glob` |

함수 call arguments에 `file_path`/`path`가 있으면 `toolSequence`의 `file`, `command`/`cmd`가 있으면 `command`로 보존한다. `patch_apply_end`는 changes object의 file paths를 `Edit` tool sequence로 만든다. (`repos/codeburn/src/providers/codex.ts:374-405`)

## Token usage and cost semantics

Codex `token_count` event의 `payload.info`에는 `last_token_usage`와 `total_token_usage`가 올 수 있다. 현재 parser는 `last_token_usage`가 있으면 그 값을 우선 사용하고, 없고 `total_token_usage`가 있으면 이전 cumulative counters와의 delta를 계산한다. 이후 cumulative counters는 last/fallback branch와 무관하게 항상 최신 total로 업데이트한다. (`repos/codeburn/src/providers/codex.ts:479-521`)

OpenAI-style logs에서는 cached token이 input token 안에 포함될 수 있으므로, CodeBurn은 다음처럼 Anthropic-style bucket으로 normalize한다. (`repos/codeburn/src/providers/codex.ts:523-528`)

```text
uncachedInputTokens = max(0, input_tokens - cached_input_tokens)
cacheReadInputTokens = cached_input_tokens
```

Cost는 `calculateCost(model, uncachedInputTokens, outputTokens + reasoningTokens, 0, cachedInputTokens, 0)`로 계산한다. 즉 reasoning token은 output cost bucket에 합쳐지고, cache write bucket은 Codex path에서 0이다. (`repos/codeburn/src/providers/codex.ts:551-558`)

`payload.info`가 없지만 pending user/assistant text가 있으면 문자 수를 4 chars/token으로 나눠 input/output token을 추정하고 `costIsEstimated: true`를 표시한다. (`repos/codeburn/src/providers/codex.ts:428-477`)

## Deduplication and fork handling

Codex provider에는 두 가지 dedup boundary가 있다.

1. Parser-local `seenKeys`: cached results 또는 새 parse 결과가 중복 yield되지 않게 한다. (`repos/codeburn/src/providers/codex.ts:311-319`, `repos/codeburn/src/providers/codex.ts:548-549`)
2. Core parser `parseProviderSources()`: provider parser 결과를 session cache turn으로 바꾸기 전/후 다시 cross-source dedup과 date filter를 적용한다. Codex provider가 새 파일을 parse한 경우 마지막에 `flushCodexCache()`가 호출된다. (`repos/codeburn/src/parser.ts:1947-2052`)

Forked Codex session은 parent history를 replay할 수 있다. 현재 parser는 `forked_from_id`와 `session_meta.timestamp`가 있으면 fork timestamp 이후 5초 이내 replay event를 skip하고, dedup key도 fork session id 대신 parent namespace(`forkedFromId || sessionId`)를 사용한다. Key는 cumulative total뿐 아니라 cumulative input/cached/output/reasoning breakdown까지 포함한다. 이렇게 해야 parent replay는 collide해서 제거되고, 같은 cumulative total을 가진 genuine divergent fork work는 보존된다. (`repos/codeburn/src/providers/codex.ts:359-364`, `repos/codeburn/src/providers/codex.ts:428-432`, `repos/codeburn/src/providers/codex.ts:532-549`)

## Codex-specific cache

Codex에는 generic `session-cache.json` 외에 별도 provider-level result cache가 있다. (`repos/codeburn/src/codex-cache.ts:9-31`)

```text
CODEBURN_CACHE_DIR/codex-results.json
or ~/.cache/codeburn/codex-results.json
version: 3
key: file path + mtimeMs + sizeBytes
value: project + ParsedProviderCall[]
```

`readCachedCodexResults()`는 file stat과 cache fingerprint가 같으면 parsed calls를 반환한다. `writeCachedCodexResults()`는 memory cache에 결과를 기록하고, `flushCodexCache()`가 삭제된 file entry를 evict한 뒤 temp file(`*.tmp`)에 0600 permission으로 쓰고 `sync()` 후 atomic rename한다. (`repos/codeburn/src/codex-cache.ts:36-69`, `repos/codeburn/src/codex-cache.ts:94-143`)

이 cache는 heavy Codex JSONL을 다시 streaming/compact-parse하지 않기 위한 provider-local optimization이고, core parser의 `SessionCache`와는 별도 layer다. Core parser는 Codex parse가 실제로 발생했을 때만 `flushCodexCache()`를 호출한다. (`repos/codeburn/src/parser.ts:2045-2048`)

## Test-backed behaviors

`tests/providers/codex.test.ts`가 다음 behavior를 회귀 테스트한다.

- `YYYY/MM/DD/rollout-*.jsonl` discovery와 `cwd` project sanitize.
- `Codex Desktop`처럼 originator case가 다른 session도 허용.
- 16KB, 64KB보다 큰 first `session_meta` line, trailing newline 없는 first line, stream chunk를 넘는 first line 처리.
- truncated/torn first-line write와 empty/non-Codex file skip.
- `last_token_usage` parsing, cached input subtraction, reasoning token 보존, cost 계산.
- `spawn_agent`/`wait_agent`/`close_agent` → `Agent` normalization.
- duplicate `token_count` event 제거와 `total_token_usage`가 없는 첫 event 보존.
- fork replay double-count 방지와 divergent fork event 보존.

근거: `repos/codeburn/tests/providers/codex.test.ts:94-240`, `repos/codeburn/tests/providers/codex.test.ts:244-495`.

`tests/provider-registry.test.ts`는 Codex가 core provider list에 있고, `exec_command → Bash`, `read_file → Read`, `write_file → Edit`, `spawn_agent → Agent`, `gpt-5.3-codex → GPT-5.3 Codex` 같은 display normalization을 검증한다. (`repos/codeburn/tests/provider-registry.test.ts:5-7`, `repos/codeburn/tests/provider-registry.test.ts:75-89`)

## Current-source corrections vs DeepWiki

- DeepWiki가 “parser calculates deltas from cumulative totals”라고 요약한 것은 부분적으로만 맞다. 현재 parser는 `last_token_usage`를 우선 사용하고, last가 없을 때 `total_token_usage` delta fallback을 쓴다.
- DeepWiki의 Codex line ranges는 현재 checkout과 맞지 않는다. 예를 들어 provider object는 현재 `repos/codeburn/src/providers/codex.ts:603-631`에 있다.
- Codex cache는 단순 skip flag가 아니라 `codex-results.json` version 3에 `project`와 `ParsedProviderCall[]`를 저장한다. Discovery도 이 cached project를 활용한다.
- Codex fork replay dedup은 단순 session id 기준이 아니라 parent namespace + cumulative token breakdown 기반이다.
- 이번 작업에서 `pnpm exec vitest run tests/providers/codex.test.ts tests/provider-registry.test.ts`를 시도했지만, checkout에 `node_modules/.bin/vitest`가 없어 `Command "vitest" not found`로 실행 검증은 되지 않았다. Source/test file inspection으로 검증했다.

관련 페이지: [[codeburn]], [[codeburn-provider-plugin-system]], [[codeburn-data-ingestion-and-caching]], [[codeburn-pricing-and-currency-resolution]], [[evidence-backed-analysis]].
