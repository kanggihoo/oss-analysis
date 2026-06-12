---
title: CodeBurn Data Ingestion and Caching
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence, deepwiki]
sources:
  - artifacts/codeburn/deepwiki/pages-md/2.1-data-ingestion-and-parsing-pipeline.md
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-domain-terminology.md
  - repos/codeburn/src/fs-utils.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/session-cache.ts
  - repos/codeburn/src/daily-cache.ts
  - repos/codeburn/src/cli-date.ts
  - repos/codeburn/src/providers/types.ts
  - repos/codeburn/src/providers/index.ts
confidence: high
---
# CodeBurn Data Ingestion and Caching

이 페이지는 [[codeburn]]이 provider별 local log / DB / network source를 어떻게 읽고, 파싱하고, 캐싱하는지 설명한다. DeepWiki `2.1 Data Ingestion and Parsing Pipeline`을 출발점으로 삼았지만, durable claim은 local checkout `repos/codeburn`의 source path로 검증했다. 관련 domain entity 이름은 [[codeburn-domain-terminology]]를 참조한다.

검증 기준 checkout: `repos/codeburn` at `f1bf7a197bb38e70cc71cf1905bfa5cbd92c1cc3`.

## Mental model
CodeBurn은 모든 raw log를 매번 처음부터 통째로 읽는 도구가 아니다. Provider가 session source를 발견하면 CodeBurn은 파일 fingerprint를 보고 바뀐 source만 다시 파싱한다. 파싱 결과는 raw JSON 원본이 아니라 compact turn 형태로 `session-cache.json`에 저장되고, UI/JSON/MCP 요청 때 그 cache에서 `ProjectSummary`를 재구성한다.

```text
provider discovery
→ source fingerprint check
→ unchanged source: cached turns 재사용
→ changed source: streaming/file read + provider parse
→ compact call/turn cache
→ ClassifiedTurn / SessionSummary / ProjectSummary
→ dashboard/report/menubar/MCP
```

중심 orchestration은 `parseAllSessions()`다. 이 함수는 먼저 in-memory TTL cache를 확인하고, disk `SessionCache`를 로드한 뒤, `discoverAllSessions()`로 provider source를 찾는다. Claude JSONL은 `scanProjectDirs()`로, non-Claude provider들은 `parseProviderSources()`로 처리된다. (`repos/codeburn/src/parser.ts:2123-2152`, `repos/codeburn/src/parser.ts:2231-2320`, `repos/codeburn/src/providers/index.ts:176-186`)

## 1. Discovery: 어디서 읽을지 찾는다
Provider interface의 핵심 책임은 두 가지다.

| Provider 책임 | 의미 | Evidence |
|---|---|---|
| `discoverSessions()` | provider별 local file, SQLite source, network source 위치를 찾는다. | `repos/codeburn/src/providers/types.ts:38-48` |
| `createSessionParser()` | 찾은 source를 `ParsedProviderCall` stream으로 바꾼다. | `repos/codeburn/src/providers/types.ts:38-48`, `repos/codeburn/src/parser.ts:2013-2023` |

즉, CodeBurn core parser는 모든 provider log format을 직접 hard-code하기보다 provider adapter가 발견과 1차 normalization을 맡게 하고, core는 그 결과를 project/session/turn/cost 구조로 접는다.

## 2. 파일 읽기 전략: 두 reader가 있다
DeepWiki의 "8MB 미만 readFile, 8~128MB stream" 설명은 현재 checkout의 `src/fs-utils.ts`와 다르다. 현재 source 기준으로는 아래 두 reader가 분리되어 있다.

| Reader | 쓰임 | 크기 제한 | 동작 |
|---|---|---:|---|
| `readSessionFile()` / `readSessionFileSync()` | 일부 provider가 source 전체를 문자열로 읽을 때 | 128MB | `stat()` 후 128MB 초과면 `null`, 이하면 `readFile(..., 'utf-8')` |
| `readSessionLines()` | Claude JSONL처럼 line-oriented log를 읽을 때 | 2GB | `createReadStream()`으로 chunk를 읽고 newline 기준으로 line yield |

근거: `MAX_SESSION_FILE_BYTES`는 128MB이고 `readSessionFile()`은 이를 넘으면 skip한다. `MAX_STREAM_SESSION_FILE_BYTES`는 2GB이고 `readSessionLines()`는 streaming cap으로 이를 쓴다. (`repos/codeburn/src/fs-utils.ts:4-15`, `repos/codeburn/src/fs-utils.ts:25-45`, `repos/codeburn/src/fs-utils.ts:87-105`)

따라서 현재 전략은 다음처럼 이해하면 된다.

```text
파일 전체가 필요한 provider path → 128MB 이하만 readFile, 초과는 skip
JSONL처럼 line 단위 처리 가능한 path → createReadStream 기반 readSessionLines, 최대 2GB
```

## 3. 큰 JSONL line은 Buffer/large-line parser로 처리한다
`readSessionLines()`는 `largeLineAsBuffer` 옵션을 받을 수 있다. line 길이가 기본 32KB를 넘으면 string으로 변환하지 않고 `Buffer`로 넘길 수 있다. Claude path는 이 옵션과 byte offset tracker를 함께 쓴다. (`repos/codeburn/src/fs-utils.ts:69-76`, `repos/codeburn/src/fs-utils.ts:112-115`, `repos/codeburn/src/parser.ts:1870-1885`)

`parseJsonlLine(line: string | Buffer)`은 line 크기에 따라 다음처럼 동작한다.

| 조건 | 처리 |
|---|---|
| 32KB 이하 string/Buffer | 일반 `JSON.parse` |
| 32KB 초과 string | `parseLargeJsonlLine()` |
| 32KB 초과 Buffer | `parseLargeJsonlBuffer()` |

큰 line parser는 전체 JSON object를 보존하지 않는다. 필요한 field만 스캔해서 compact `JournalEntry`를 만든다. Assistant message에서는 model, id, usage/cache token, web search count, tool_use 일부를 추출하고, user text와 command input도 cap을 둔다. (`repos/codeburn/src/parser.ts:116-133`, `repos/codeburn/src/parser.ts:248-462`, `repos/codeburn/src/parser.ts:880-955`)

## 4. Claude JSONL이 turn으로 바뀌는 과정
Claude 경로는 다음 순서로 raw JSONL을 turn과 summary로 바꾼다.

```text
collectJsonlFiles(project dir)
→ subagents/ 아래 JSONL까지 재귀 수집
→ parseClaudeEntries(filePath)
→ parseJsonlLine + compactEntry
→ dedupeStreamingMessageIds
→ groupIntoTurns
→ classifyTurn
→ buildSessionSummary
```

`collectJsonlFiles()`는 일반 session `.jsonl`뿐 아니라 `subagents/`와 workflow subagent transcript까지 수집한다. (`repos/codeburn/src/parser.ts:1466-1490`)

`groupIntoTurns()`의 규칙은 간단하다: 새 user message가 나오면 turn을 시작하고, 다음 user message가 나오기 전까지 assistant message/call을 같은 turn에 누적한다. 다음 user message 또는 EOF에서 turn을 finalize한다. Assistant message는 `parseApiCall()`에서 token usage, cache token, web search request, cost, tools, MCP tools, skills, subagent types, bash commands, dedup key를 가진 `ParsedApiCall`로 바뀐다. (`repos/codeburn/src/parser.ts:1080-1139`, `repos/codeburn/src/parser.ts:1166-1208`)

## 5. 날짜 필터링은 비용 발생 시점 기준이다
`cli-date.ts` 기준으로 `all` period는 무한대가 아니라 최근 6개월이다. `--to`는 해당 날짜의 23:59:59.999까지 포함하고, `--from > --to`면 error다. (`repos/codeburn/src/cli-date.ts:11-16`, `repos/codeburn/src/cli-date.ts:104-124`)

Turn filtering은 user message 시간이 아니라 첫 assistant call timestamp 기준에 가깝다. 비용이 실제로 발생한 시점이 assistant call 쪽이기 때문이다. (`repos/codeburn/src/parser.ts:1435-1447`, `repos/codeburn/src/parser.ts:1600-1607`, `repos/codeburn/src/parser.ts:2077-2082`)

## 6. Cache layer A: in-memory TTL cache
`parseAllSessions()` 결과는 process memory에 잠깐 저장된다.

| 항목 | 값 |
|---|---:|
| TTL | 180초 |
| 최대 entry | 10개 |
| key 구성 | date range, provider filter, Claude config env, proxy path config hash |

근거: `repos/codeburn/src/parser.ts:2123-2152`.

이 cache는 dashboard/menubar/MCP가 짧은 시간 안에 같은 range를 반복 조회할 때 유용하지만, process가 끝나면 사라진다.

## 7. Cache layer B: `session-cache.json`
더 중요한 cache는 disk session cache다. 기본 위치는 `~/.cache/codeburn/session-cache.json`이며 `CODEBURN_CACHE_DIR`로 override할 수 있다. (`repos/codeburn/src/session-cache.ts:85`, `repos/codeburn/src/session-cache.ts:116-122`)

```text
SessionCache
└── providers[provider]
    ├── envFingerprint
    └── files[sourcePath]
        ├── fingerprint(dev, ino, mtimeMs, sizeBytes)
        ├── lastCompleteLineOffset?
        ├── canonicalCwd? / canonicalProjectName?
        ├── mcpInventory
        ├── turns
        ├── agentType?
        └── failed?
```

근거: `repos/codeburn/src/session-cache.ts:46-79`.

Cache에는 raw log 전체가 아니라 compact `CachedTurn[]`이 저장된다. 그래서 fingerprint가 같으면 raw file을 다시 읽지 않고 cached turns를 `ClassifiedTurn` / `SessionSummary`로 복원할 수 있다.

## 8. 파일 변경 판단: fingerprint reconciliation
각 source file은 `dev + ino + mtimeMs + sizeBytes`로 비교된다. `reconcileFile()` 결과는 `new`, `unchanged`, `appended`, `modified` 네 가지다. (`repos/codeburn/src/session-cache.ts:278-346`)

현재 확인한 Claude 처리 경로에서는 `lastCompleteLineOffset`을 저장하지만, changed Claude file을 offset부터만 incremental parse하는 일반 경로라기보다 `parseClaudeEntries(filePath, tracker)`로 다시 읽어 cache를 갱신한다. 따라서 현재 source 기준으로 안전하게 말할 수 있는 동작은 "unchanged file은 재사용, changed file은 재파싱"이다. (`repos/codeburn/src/parser.ts:1507-1585`, `repos/codeburn/src/parser.ts:1870-1885`)

## 9. Claude cache update 흐름
```text
collectJsonlFiles
→ fingerprintFile
→ reconcileFile
→ unchangedFiles / changedFiles 분리
→ unchanged cached turn들의 dedup key를 seen set에 먼저 등록
→ changed file만 parseClaudeEntries
→ turns를 CachedTurn으로 바꿔 section.files[filePath]에 저장
→ diskCache._dirty = true
```

저장되는 값에는 fingerprint, last complete line offset, canonical project path/name, MCP inventory, cached turns, subagent agent type이 포함된다. (`repos/codeburn/src/parser.ts:1507-1585`)

## 10. non-Claude provider cache update 흐름
```text
source list
→ provider section 가져오기
→ network provider면 매번 changed로 취급
→ file provider면 fingerprint 비교
→ unchanged면 cached turns 재사용
→ changed면 provider.createSessionParser(...).parse()
→ ParsedProviderCall[] canonicalize
→ providerCallsToCachedTurns
→ section.files[source.path]에 저장
```

Network provider는 on-disk fingerprint가 없으므로 synthetic fingerprint를 쓰고 매번 fetch/parse 대상으로 취급한다. 일부 provider는 unchanged여도 provider-specific 이유로 재파싱한다. (`repos/codeburn/src/parser.ts:1897-1912`, `repos/codeburn/src/parser.ts:1947-2052`)

## 11. 실패도 cache한다
한 파일이 malformed이거나 provider parser가 실패해도 전체 run을 죽이지 않는다. 대신 현재 fingerprint에 대해 `turns: []`, `failed: true`인 negative-result marker를 저장한다. 같은 파일이 변하지 않는 동안은 다시 읽고 다시 실패하지 않으며, fingerprint가 달라지면 재시도된다. (`repos/codeburn/src/session-cache.ts:64-68`, `repos/codeburn/src/parser.ts:1566-1574`, `repos/codeburn/src/parser.ts:2034-2042`)

## 12. Cache 저장과 daily cache
`saveCache()`는 `session-cache.json`에 바로 덮어쓰지 않는다. `session-cache.json.<random>.tmp`에 쓰고 `fsync` 후 `rename()`으로 atomic replace한다. 오래된 temp file cleanup도 있다. (`repos/codeburn/src/session-cache.ts:251-274`, `repos/codeburn/src/session-cache.ts:367-387`)

`daily-cache.json`은 session cache와 역할이 다르다. Session cache는 파일별 compact turns를 저장해 raw session 재파싱을 줄이고, daily cache는 날짜별 aggregate를 저장해 trend/history/menubar payload 계산을 빠르게 한다. `ensureCacheHydrated()`는 어제까지의 gap만 다시 파싱해 `aggregateDays()` 결과를 추가하고, local-model savings config hash가 바뀌면 daily cache를 비우고 재수화한다. (`repos/codeburn/src/daily-cache.ts:200-252`)

## 핵심 trade-off
- 원본 provider log는 source of truth로 두고, cache에는 compact turn만 저장한다.
- line-oriented JSONL은 stream으로 읽어 큰 파일에서도 memory 폭증을 줄인다.
- 큰 JSONL line은 필요한 field만 추출해 parsing memory와 cache 크기를 줄인다.
- 파일 fingerprint가 같으면 raw file을 다시 열지 않고 cached turn을 재사용한다.
- 파싱 실패도 cache해 반복 실패 비용을 막는다.
- day-level aggregate는 별도 daily cache에 저장해 UI refresh 비용을 줄인다.

관련 페이지: [[codeburn]], [[codeburn-domain-terminology]], [[evidence-backed-analysis]], [[deepwiki-first-baseline]].
