---
title: CodeBurn Codex Provider
created: 2026-06-11
updated: 2026-10-15
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence]
sources:
  - repos/codeburn/src/providers/codex.ts
  - repos/codeburn/src/codex-cache.ts
  - repos/codeburn/src/codex-fork-replay.ts
  - repos/codeburn/src/codex-session-index.ts
  - repos/codeburn/src/codex-credits.ts
  - repos/codeburn/src/codex-throughput.ts
  - repos/codeburn/src/parse-worker.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/models.ts
  - repos/codeburn/src/providers/index.ts
  - wiki/concepts/codeburn-provider-plugin-system.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
confidence: high
---

# CodeBurn Codex Provider

검증 기준 checkout: repos/codeburn at 9a40cc603fcd194caca9daa8c5134a61ea7e0e2b (2026-10-15).

관련: [[codeburn]], [[codeburn-provider-plugin-system]], [[codeburn-data-ingestion-and-caching]], [[codeburn-pricing-and-currency-resolution]], [[codeburn-subscription-plans-and-currency]], [[codeburn-turn-classification-engine]]

## 역할

- OpenAI Codex CLI의 **rollout 파일**(세션 하나를 한 줄 JSON 이벤트로 적은 `rollout-*.jsonl`)을 읽어 `ParsedProviderCall`로 바꾸는 core provider. `coreProviders`에 포함(index.ts:200). (코드 확인)
- 본체 `src/providers/codex.ts`(1648줄) + 보조 모듈 5개 + worker 경로. 구 baseline의 단일 파일+캐시 구조보다 크게 확장됐다. (코드 확인)

## Discovery

- `getCodexDir()` (codex.ts:187-189): 인자 → `CODEX_HOME` → `~/.codex` 순. (코드 확인)
- `discoverSessionsInDir()` (codex.ts:603-655)
  - 입력: codex home 경로.
  - 내부 동작: `sessions/YYYY/MM/DD/rollout-*.jsonl`을 단계별 `mapWithConcurrency`로 수집, 이어서 `archived_sessions/`. basename 기준 중복 제거(날짜 폴더 우선).
  - 반환값: `SessionSource[]`. (코드 확인)
- `discoverSessionFile()` (codex.ts:579-601): 캐시의 project 인덱스(`getCachedCodexProject`)가 맞으면 파일을 열지 않고 반환. 아니면 첫 줄 `session_meta`를 검증하고 `cwd`를 `sanitizeProject`로 project 이름화. `cwd`가 문자열이 아니면 `'unknown'`. (코드 확인)
- `createCodexProvider()` (codex.ts:1573-1646): 다중 home 처리. (코드 확인)
  - launcher가 만든 **nest home**(다른 런처의 중첩 Codex home)이면 기본 `~/.codex`와 함께 스캔하고 이미 청구된 session id와 겹치는 nest source를 제거(`dropOverlappingNestSources`, :1565-1571).
  - 같은 물리 경로의 alias면 빈 결과(`duplicateHome`, :1580-1583).
  - Windows에서 WSL home의 `~/.codex`도 추가(`wslCodexDirs`, :1593-1594).
  - `probeRoots()`로 sessions/archived 경로를 doctor에 노출(:1612-1616).

## 파서 흐름: `createParser()` (codex.ts:780-1540)

- 입력: `source`, 공유 `seenKeys`, 선택 `capture`(worker용, 있으면 캐시를 읽고 쓰지 않음).
- 내부 동작 (코드 확인):
  1. 캐시 확인(:783-794): `exact` 적중이면 캐시 call을 dedup 거쳐 그대로 yield. `resume` 적중이면 저장된 offset/state부터 이어 읽기(:792-794).
  2. `readSessionLines(..., { largeLineAsBuffer: true, byteOffsetTracker })`로 스트리밍(:1014-1018). 큰 줄은 Buffer로 받아 compact 파서(`parseCodexLine` :469)가 필요한 필드만 뽑는다. 250MB 넘는 세션 대응(주석 :1009-1013).
  3. `session_meta`(:1023-1050): sessionId, cwd, `forked_from_id`/`parent_thread_id` 기록, fork면 replay 상태 시작.
  4. `turn_context`·`thread_settings_applied`: 모델과 **service tier**(Fast=priority, flex 요금 등급) 갱신(:1069, :1083).
  5. tool 이벤트(`function_call`, `custom_tool_call`, `mcp_tool_call_end`, `item_completed`, `patch_apply_end`)로 tools/skills/MCP/LOC 누적(:1176-1316).
  6. 사용량: `token_usage_record`(:1337-1352)를 보면 그 파일은 이후 `token_count`를 무시(`hasTokenUsageRecord`, :1359). 없으면 `token_count`(:1354-1513) 처리.
  7. `task_complete`(:1222-1258)에서 task 지속시간을 call별 `activeDurationMs`/`toolWaitMs`로 생성 토큰 비율 배분.
- 반환값: `AsyncGenerator<ParsedProviderCall>`. EOF에서 캐시 기록 후 yield(:1528-1539). 한 줄도 못 읽으면 캐시를 쓰지 않는다(:1520-1523).

## 토큰·비용 의미 (`accountUsage`, codex.ts:915-1000)

- OpenAI의 `input_tokens`는 캐시 토큰을 포함하므로 `input - cached`로 Anthropic식 "비캐시 입력"으로 정규화(:924-926). (코드 확인)
- `cache_write_input_tokens`는 가격표에 명시 cache-write 요금이 있을 때만 별도 버킷으로 분리(:936-941). (코드 확인)
- reasoning 토큰은 이미 output에 포함 → `billableOutputTokens('codex', ...)`가 더하지 않음(models.ts:60-66). (코드 확인)
- 비용은 `calculateCost(pricingModelAt(model, timestamp), ..., speed, ..., 'codex')`(:952-962). `pricingModelAt`은 날짜별 모델 별칭 가격용. (코드 확인)
- `info`가 없는 `token_count`는 문자 수로 토큰을 추정하고 `costIsEstimated: true`(:1361-1418). 모델 없으면 `'gpt-5'`. (코드 확인)
- `last_token_usage`가 없으면 `total_token_usage`의 직전 대비 증분 사용, prev 카운터는 항상 갱신(:1444-1477). (코드 확인)

## 중복 제거와 fork

- dedup key (코드 확인):
  - `token_usage_record`: `codex:<forkedFromId||sessionId>:response:<response_id>` (:1347-1349, response_id 없으면 경로+offset).
  - `token_count`(누적값 있음): `codex:<forkedFromId||sessionId>:<total>:<input>:<cached>:<output>:<reasoning>` (:1503-1504). fork는 부모 namespace를 써서 복제 기록이 부모와 충돌하도록.
  - 누적값 없음: 파일 경로 + 줄 offset (:1505).
- 바이트 동일 연속 `token_count`는 재방출로 간주해 skip(:1433-1435). (코드 확인)
- **fork replay**: fork된 rollout 앞부분에 부모 기록이 재타임스탬프되어 복사된 구간. `isCodexForkReplay`(codex-fork-replay.ts:29-55)는 1초 초과 간격 또는 fork 후 5초 경과로 구간을 끝낸다. 구간 내 기록은 `loadCodexParentReplay`(:143)로 부모 파일에 실제 있는지 확인한 것만 버리고 나머지는 센다(codex.ts:805-816, :1100-1127). (코드 확인)

## 캐시 (`src/codex-cache.ts`)

- `CODEX_CACHE_VERSION = 22`(:71). 주석 :11-70이 버전별 재파싱 사유 이력. (코드 확인)
- `readCachedCodexResults()` (:293-320): fingerprint(dev/ino/mtime/size) 완전 일치면 `exact`. 같은 inode가 커졌고 저장 offset 직전 바이트가 개행이면 `resume`(append-only 가정, `endsLineAt` :268-282). WSL UNC 경로는 dev/ino를 0으로(:287-291). (코드 확인)
- discovery용 경량 project 인덱스 파일 별도(`codexProjectsFileName`, :76-81). (코드 확인)
- parser 쪽 provider별 parse version 문자열은 `session-cache.ts:433`. (코드 확인)

## Worker thread 병렬 파싱

- `parseProviderSources`에서 codex이고 쓰기 실행이면, 캐시로 못 푸는 파일만 worker job으로 모은다(parser.ts:3808-3831). (코드 확인)
- worker(parse-worker.ts:35-43)는 빈 dedup Set으로 `parseCodexFileFull`(codex.ts:1551-1556)을 돌리고 결과·claimed keys·캐시 쓰기 정보를 JSON 문자열로 반환. fork 부모 조회는 `routeCodexParentReplay`로 부모 스레드에 위임(:22-26). (코드 확인)
- 부모는 순서를 검증하고, keys가 기존 dedup과 하나라도 겹치면 결과를 버리고 in-process로 재파싱(parser.ts:3870-3889). (코드 확인)

## 보조 모듈

- `codex-session-index.ts`: Codex 세션 이름을 리포트에 덧씌움(`applyCodexSessionNames`, :78; parser.ts:10, serve.ts:14에서 사용). (코드 확인)
- `codex-credits.ts`: 토큰을 ChatGPT 구독 **credit**(USD와 다른 Codex 사용량 단위)으로 환산(`codexCredits` :60). `models-report.ts`에서만 사용. (코드 확인)
- `codex-throughput.ts`: `mergeToolIntervals`(:116)를 parser와 공유, `CodexThroughputReader`(:202)는 `main.ts`의 Tok/s 표시용. (코드 확인)

## 미확인

- `parseCodexLine`의 대형 줄 compact 디코딩(:469-577) 세부 필드 윈도우 정확성.
- launcher nest home 판정(`src/launcher-homes.ts`) 내부 규칙은 읽지 않았다.
- `codex-credits.ts` 요율 표의 현재 값과 공식 문서 일치 여부.
- 실제 rollout 파일로 실행 확인은 하지 않았다(코드 확인만).
