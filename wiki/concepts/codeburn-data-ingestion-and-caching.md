---
title: CodeBurn Data Ingestion and Caching
created: 2026-06-10
updated: 2026-10-15
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence]
sources:
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/session-cache.ts
  - repos/codeburn/src/parse-workers.ts
  - repos/codeburn/src/cache-refresh-lock.ts
  - repos/codeburn/src/cache-dir.ts
  - repos/codeburn/src/dashboard.tsx
  - repos/codeburn/src/main.ts
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-domain-terminology.md
confidence: high
---
# CodeBurn Data Ingestion and Caching

검증 기준 checkout: repos/codeburn at 9a40cc603fcd194caca9daa8c5134a61ea7e0e2b (2026-10-15).

[[codeburn]]이 provider별 session source를 발견·파싱하고, 결과를 디스크 session cache에 저장해 다음 실행에서 재사용하는 경로를 정리한다. 용어는 [[codeburn-domain-terminology]], provider 발견은 [[codeburn-provider-plugin-system]], 일별 집계는 [[codeburn-day-aggregation-and-caching]]를 본다.

## 용어
- **session source**: provider가 발견한 파싱 단위(JSONL 파일, SQLite DB의 가상 경로, 네트워크 소스).
- **fingerprint**: 파일의 `dev / ino / mtimeMs / sizeBytes` 4-튜플. 변경 여부 판단 키.
- **session cache**: 파싱 결과(`CachedFile` → `CachedTurn` → `CachedCall`)를 provider별로 저장한 디스크 캐시.
- **envelope**: session cache의 최상위 `envelope.json`. 이 파일의 rename이 저장을 "공개"하는 단일 시점.
- **cold hydration**: 캐시가 complete가 아닐 때 전체 이력을 처음부터 채우는 파싱.

## 전체 흐름 (코드 확인)
```text
parseAllSessions(range, provider, opts)                     parser.ts:6299
 ├─ singlePassParse  (withSinglePassParse 범위 안이면 공유)   parser.ts:6112
 ├─ 메모리 memo (cacheKey, TTL 180s / validated 5분)          parser.ts:6339-6360
 ├─ burstReuse       (CODEBURN_PARSE_BURST_MS > 0 일 때)      parser.ts:4942
 ├─ loadCache(month scope)                                   parser.ts:6380-6383
 ├─ 미완료 → hydrating.lock 후 runParse(isCold)              parser.ts:6397-6406
 ├─ 완료 → session-refresh.lock 후 runParse(write)            parser.ts:6429-6458
 └─ runParseInner: discovery → scanProjectDirs(claude)
                   → parseProviderSources(기타) → orphan pass → completeness 표시 → saveCache
```

## parseAllSessions (parser.ts:6299)
- 입력: `dateRange?`, `providerFilter?`, `opts.includeAggregateOnly?`.
- 내부 동작: `parseAllSessionsUnfiltered` 후 Codex session 이름 적용, 기본은 aggregate-only provider(gateway) 프로젝트를 제외한다(parser.ts:6303-6306). 캐시 writer와 day 집계만 `includeAggregateOnly: true`로 전체를 받는다(parser.ts:6290-6297 주석). 코드 확인.
- 반환값: `Promise<ProjectSummary[]>`.

## 재사용 계층 (메모리)
1. **single-pass scope**: `withSinglePassParse(range, fn)`(parser.ts:6102) 안에서 시작 시각과 month scope가 같은 요청은 한 번만 파싱하고 더 짧은 end는 `filterProjectsByDateRange`로 잘라 쓴다(parser.ts:6112-6131). 호출처는 `dashboard.tsx:2303`. 코드 확인.
2. **exact-key memo**: key는 range + provider + Claude root + proxy/alias/override/savings 설정 hash(parser.ts:4970-4991). `CACHE_TTL_MS = 180_000`(parser.ts:4751) 또는 watcher가 clean이라 답하면 `VALIDATED_REUSE_CAP_MS` 5분(parser.ts:4790)까지 재사용. 코드 확인.
3. **burst reuse**: 같은 start, 약간 더 늦은 end 요청을 재사용. `CODEBURN_PARSE_BURST_MS` 기본 0이라 one-shot CLI에서는 꺼짐(parser.ts:4772-4775, 4942-4967). 코드 확인. resident `serve` 전용 최적화로 보인다(추론).
4. **load window**: `withLoadWindow(range, fn)`(parser.ts:6083)은 여러 range 요청의 합집합만큼 session cache를 한 번에 로드. `main.ts:1430,1469`가 today+month에 사용. 코드 확인.

## 디스크 캐시 거래와 잠금
- 경로: `CODEBURN_CACHE_DIR` 또는 `~/.cache/codeburn`(cache-dir.ts:11-14), 하위 `session-cache.v10/`(session-cache.ts:239-244). 코드 확인.
- **cold 경로**: `isCacheComplete`가 false면 `beginColdHydration`이 `hydrating.lock`(session-cache.ts:2788, fresh 15분/최대 대기 10분 :2789-2790)을 잡는다. 다른 프로세스가 hydrating 중이면 기다렸다가 다시 load한다(parser.ts:6397-6406). advisory이며 정확성 게이트가 아니다(session-cache.ts:2780-2786 주석). 코드 확인.
- **warm 경로**: `acquireCacheRefreshLock`(cache-refresh-lock.ts:256)이 `session-refresh.lock`(:8, heartbeat 10s / stale 90s :9-10)을 잡는다. `timed-out`/`unavailable`이면 이미 읽은 snapshot을 read-only로 서빙, `completed-by-other`면 다시 load 후 read-only, 획득하면 reload 후 write 파싱(parser.ts:6435-6458). 코드 확인.

## runParseInner (parser.ts:6488)
- 입력: memo key, `SessionCache`, range, provider, `{isCold, readOnly, snapshotOnly, refreshLock}`.
- 내부 동작:
  - `discoverAllSessionsWithFailures`로 source 수집, Claude와 나머지 provider를 분리(parser.ts:6516-6534). 코드 확인.
  - Claude project는 `scanProjectDirs`, Claude desktop ledger와 다른 provider는 `parseProviderSources`(parser.ts:6578-6624). 권한 오류(EPERM/EACCES)는 해당 provider만 skip(parser.ts:6602-6608, 6622-6629). 코드 확인.
  - cold 실행 중 `PROGRESS_SAVE_FILE_INTERVAL = 2000` 파일 또는 30s마다 부분 저장(parser.ts:3519-3523, 6545-6554). 코드 확인.
  - 발견되지 않았지만 캐시에 남은 durable provider(원본 파일이 지워진 VS Code 계열 등)도 빈 source로 orphan pass를 돌려 금액이 사라지지 않게 한다(parser.ts:6633-6661). 코드 확인.
  - 끝까지 돈 provider에 `markProviderComplete`, 범위 제한 run이면 `completeFrom` floor 기록, 무필터·무실패 run만 whole-cache `complete = true`(parser.ts:6688-6700). 코드 확인.
  - 변경이 있으면 `saveCache`. resident 프로세스에서는 `SHARD_PUBLISH_COALESCE_MS = 90_000` 동안 저장을 미룰 수 있으나 durable provider가 dirty면 즉시 저장(parser.ts:4914, 6702-6720). 코드 확인.
- 반환값: `ProjectSummary[]`.

## 파일 단위 증분: fingerprintFile / reconcileFile
- `fingerprintFile`(session-cache.ts:2568): `stat` 기반 4-튜플. WSL UNC 경로는 dev/ino를 0으로(:2601), SQLite DB는 WAL을 포함한 별도 fingerprint, `#`/`:` 가상 접미사는 떼고 DB를 stat(:2604-2624). 코드 확인.
- `reconcileFile`(session-cache.ts:2654) 반환 4종: 캐시 없음 → `new`, 4-튜플 동일 → `unchanged`, 같은 dev/ino에 크기 증가 + `lastCompleteLineOffset ≤ size` → `appended`(offset부터 읽음), 그 외 → `modified`(전체 재파싱). 코드 확인.
- **Claude**(`scanProjectDirs`, parser.ts:2123): `appended`만 tail 증분 파싱, 나머지 변경은 전체 재파싱(parser.ts:2205-2214). unchanged 파일의 dedup key를 `seenMsgIds`에 미리 넣어 중복 메시지를 막는다(parser.ts:2251-2258). 코드 확인.
- **기타 provider**(`parseProviderSources`, parser.ts:3610): append 분기가 없고 변경되면 `changedSources`로 전체 재파싱(parser.ts:3724-3737). 네트워크 source는 fingerprint 없이 매번 다시 가져온다(parser.ts:3687-3693). 캐시된 파싱 실패(`failed`)는 같은 fingerprint면 다시 읽지 않는다(parser.ts:3725-3735). 코드 확인.
- read-only 실행에서 변경된 파일을 옛 캐시로 서빙하면 `readOnlyServedStale = true`로 표시(parser.ts:2200-2218). 코드 확인.

## 병렬 파싱 (parse-workers.ts)
- `decideParseWorkers`: 전체 재파싱 대상 바이트가 `MIN_PENDING_BYTES = 200MB` 미만이면 직렬(parse-workers.ts:25, 65). `CODEBURN_PARSE_WORKERS`로 강제, 코어 수 상한(:56-61). 메모리 예산은 평균 파일 크기 기반(:8-19). 코드 확인.
- append는 worker로 보내지 않는다(parser.ts:2271-2274). worker pool 생성 실패 시 직렬로 강등(parser.ts:2279-2287). 코드 확인.

## session cache 디스크 구조 (v10)
- `CACHE_VERSION = 10`(session-cache.ts:239). v8 provider 샤드 → v9 provider×UTC month 샤드 → v10 provider×**UTC day piece** + provider index + piece별 dedup key 파일(session-cache.ts:225-238). turn 형태는 같아 v9/v8/v7에서 재파싱 없이 이전한다. 코드 확인.
- 파일 이름: piece `<provider>.<YYYY-MM-DD>.<nonce>.json`, keys `<piece>.keys.json`, index `index.<provider>.<nonce>.json`(session-cache.ts:2153-2167). nonce 덕에 공개된 파일을 덮어쓰지 않는다. 코드 확인.
- `IndexRow`: piece day(파일의 최신 call UTC 일), v9 호환 `month/until`, fingerprint, call 시간 범위 `lo/hi`, piece 내 byte offset/length(session-cache.ts:662-675). 범위 조회는 index와 keys만 읽고 필요한 member만 읽는다. 코드 확인.
- `CachedFile`(session-cache.ts:123): `fingerprint`, `lastCompleteLineOffset`, project/cwd, `mcpInventory`, `turns`, `failed` 마커, Claude 전용 title/PR/sidechain/subagent 연결, `lineage`. 코드 확인.
- `ProviderSection.envFingerprint`가 바뀌면 그 section을 통째로 버린다(session-cache.ts:2408-2410 주석). `complete/completeFrom`은 provider 단위 완료 표시(:172-188). 코드 확인.
- `saveCache`(session-cache.ts:2390): 다른 프로세스가 먼저 공개했으면 그 envelope를 base로 rebase하고, 공개 경합 시 한 번 재시도한 뒤 envelope를 원자적 rename으로 마지막에 기록(:2396-2420, 2149-2151). 코드 확인.

## 설계 의도 (추론)
- Append-only 로그 특성을 이용해 Claude의 따뜻한 경로를 tail 읽기로 줄이고, 디스크 구조를 day piece로 쪼개 "오늘 한 세션 추가"가 하루치 piece만 다시 쓰게 했다. 여러 프로세스(menubar, desktop, CLI)가 같은 캐시를 공유하므로 nonce 파일 + envelope 공개 + 두 잠금으로 lost update를 막는다. 추론.

## 관련
[[codeburn-provider-plugin-system]] · [[codeburn-codex-provider]] · [[codeburn-day-aggregation-and-caching]] · [[codeburn-pricing-and-currency-resolution]] · [[codeburn-turn-classification-engine]] · [[codeburn-report-status-export-commands]]

## 미확인
- `loadCache`(session-cache.ts:1805)의 stub/hidden fingerprint 로딩 세부와 v9→v10 이전 경로 전체.
- first-paint floor(`withColdFirstPaintFloor`, `deferToBackgroundFill`)의 background fill 순서.
- `ParseWorkerPool` 결과 순서 보장과 worker 측 pricing snapshot 전달.
- 실제 실행으로 lock 경합/stale 처리 동작을 확인하지 않음(실행 확인 없음).
