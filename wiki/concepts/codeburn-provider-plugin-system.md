---
title: CodeBurn Provider Plugin System
created: 2026-06-11
updated: 2026-10-15
type: concept
tags: [open-source, architecture, developer-tools, tooling, evidence]
sources:
  - repos/codeburn/src/providers/types.ts
  - repos/codeburn/src/providers/index.ts
  - repos/codeburn/src/providers/sqlite-session-parser.ts
  - repos/codeburn/src/providers/vercel-gateway.ts
  - repos/codeburn/src/providers/copilot.ts
  - repos/codeburn/src/parser.ts
  - repos/codeburn/src/session-cache.ts
  - wiki/projects/codeburn.md
  - wiki/concepts/codeburn-data-ingestion-and-caching.md
  - wiki/concepts/codeburn-codex-provider.md
confidence: high
---

# CodeBurn Provider Plugin System

검증 기준 checkout: repos/codeburn at 9a40cc603fcd194caca9daa8c5134a61ea7e0e2b (2026-10-15).

관련: [[codeburn]], [[codeburn-domain-terminology]], [[codeburn-data-ingestion-and-caching]], [[codeburn-codex-provider]], [[codeburn-pricing-and-currency-resolution]], [[codeburn-day-aggregation-and-caching]]

## 한 줄 요약

- **provider**: AI 코딩 도구 하나(Codex, Cursor, Copilot 등)의 로컬 기록을 읽어 공통 형식으로 바꾸는 어댑터 객체.
- 모든 provider는 `Provider` 타입 하나를 구현하고, `src/providers/index.ts` 레지스트리가 이를 모아 `parser.ts`에 넘긴다. parser는 provider별 포맷을 모르고 `ParsedProviderCall` 스트림만 소비한다. (코드 확인)

## Provider 인터페이스 (`src/providers/types.ts`)

- `Provider` (types.ts:139-165) 필드 (코드 확인):
  - `name` / `displayName`, `modelDisplayName()`, `toolDisplayName()` — 표시용 이름 변환.
  - `discoverSessions(onSkippedVersion?)` → `Promise<SessionSource[]>` (:157) — 디스크/DB에서 세션 후보를 찾는다.
  - `createSessionParser(source, seenKeys, dateRange?)` → `SessionParser` (:158) — 한 source를 파싱할 객체를 만든다.
  - `probeRoots?()` (:164) — `codeburn doctor`가 스캔 경로 존재 여부를 보여주기 위한 선택 메서드.
  - `network?` (:144) — 디스크 파일 없이 API로 가져오는 provider. fingerprint/증분 캐시 불가.
  - `durableSources?` (:153) — 외부 프로세스가 원본을 지울 수 있는 provider. 캐시 항목을 지우지 않고 합집합으로 유지.
- **SessionSource** (types.ts:4-26): 파싱 단위 하나. `path`, `project`, `provider` 필수, `sourceKind`(claude 전용), `agentName`(OMP), `retainWhilePresent`(copilot session-store) 등 provider별 확장 필드가 붙어 있다. (코드 확인)
- **SessionParser** (types.ts:28-30): `parse(): AsyncGenerator<ParsedProviderCall>` 하나뿐. (코드 확인)
- **ParsedProviderCall** (types.ts:32-130): API 호출 1건의 정규화 레코드. 토큰 버킷(input/output/cacheCreation/cacheRead/cached/reasoning), `costUSD`, `deduplicationKey`, `timestamp`, `speed`, `tools`, `sessionId` 등. 최근 추가된 선택 필드: `costFromBilling`, `fallbackCostUSD`, `locAdded/locRemoved/editFailed`, `nanoAiu`(Copilot), `requestCount`(Vercel), `route`, `billing`, `activeDurationMs/toolWaitMs`. (코드 확인)
- **deduplicationKey**: 같은 호출이 여러 파일/경로로 보일 때 한 번만 세기 위한 문자열 키. provider가 만들고 parser가 `seenKeys` Set으로 공유한다. (코드 확인, parser.ts:3784)

## 레지스트리: core + lazy (`src/providers/index.ts`)

- `coreProviders` (index.ts:200): 정적 import된 32개. `pi.ts`가 `pi`, `omp` 두 개를 export한다(:26). (코드 확인)
- `lazyProviderNames` (index.ts:204): 11개 — antigravity, forge, goose, cursor, opencode, cursor-agent, crush, warp, vercel-gateway, zcode, zed. 각각 `loadX()`가 `await import()`로 한 번만 시도하고 실패하면 `null`을 캐시한다 (예: loadCursor index.ts:98-108). (코드 확인)
  - lazy로 두는 이유: SQLite 등 선택적 네이티브 의존성이 깨져도 나머지 provider가 동작하도록. (추론, catch에서 null 반환하는 구조로부터)
- `lazyProviderDisplayNames` (index.ts:209-221): 모듈 로드 실패 시에도 표시 이름을 돌려주기 위한 정적 표. `allProviderNames()` (:233-239)는 `--provider` 검증용 전체 이름 목록. (코드 확인)
- `getAllProviders()` (index.ts:241-257)
  - 입력: 없음.
  - 내부 동작: 11개 lazy loader를 `Promise.all`로 병렬 실행, core 뒤에 성공한 것만 push.
  - 반환값: `Provider[]` (core 순서 → lazy 순서). (코드 확인)
- `getProvider(name)` (index.ts:325-371): lazy 이름이면 해당 loader, 아니면 core에서 find. (코드 확인)
- 기준선 변화: 구 baseline(f1bf7a1)은 core 19 + lazy 9였다. 현재 32 + 11. (코드 확인, 구 수치는 이전 노트 기준)

## Discovery 흐름

- `discoverOne(provider)` (index.ts:268-286): provider 하나의 `discoverSessions()`를 try/catch로 격리. 실패 시 `recordProviderIssue(name,'locate',err)` 기록, provider당 1회 stderr 경고, `{sources: [], failed: true}` 반환. (코드 확인)
- `discoverAllSessionsWithFailures(providerFilter?, providerList?)` (index.ts:298-316)
  - 입력: `--provider` 필터(`'all'`이면 무시), 테스트용 provider 목록.
  - 내부 동작: 필터링 후 모든 provider의 discovery를 `Promise.all`로 동시 실행, 레지스트리 순서로 concat.
  - 반환값: `{ sources, failedProviders }` — "세션 없음"과 "discovery 실패"를 구분하기 위해 실패 이름을 따로 돌려준다(주석 :292-295). (코드 확인)

## Parser 통합 (`src/parser.ts`)

- `runParseInner` (parser.ts:6488~): `discoverAllSessionsWithFailures` 호출(:6518) → claude source와 나머지로 분리(:6522-6525) → 나머지는 provider별 그룹. (코드 확인)
- Claude는 예외 경로: 일반 transcript는 `scanProjectDirs()`(:6579)가 직접 처리하고, `sourceKind === 'claude-desktop-ledger'`만 `parseProviderSources('claude', ...)`(:6589)를 탄다. (코드 확인)
- 나머지 provider: 그룹마다 `parseProviderSources(providerName, sources, seenKeys, diskCache, ...)` (:6616). 권한 오류만 건너뛰고 그 외 오류는 전체 실행을 중단한다(:6620-6625). (코드 확인)
- `parseProviderSources` (parser.ts:3610) 핵심 단계 (코드 확인):
  1. `getProvider()`로 객체 확보(:3625).
  2. source마다 fingerprint 계산(`network` provider는 건너뛰고 합성 fingerprint로 매번 재수집, :3657, :3692-3695).
  3. 변경된 source만 `provider.createSessionParser(source, parserDedup, dateRange)`(:3893) → `parse()`를 끝까지 수집.
  4. Codex는 예외적으로 worker thread 풀에서 먼저 파싱 가능(:3808-3831, [[codeburn-codex-provider]] 참고).
  5. `canonicalizeProviderCallProject` → `providerCallsToCachedTurns`(:3899-3900)로 캐시 turn 형태로 변환.
  6. `durableSources`면 기존 캐시 항목을 지우지 않고 dedup key 기준 합집합 병합(:3855, :3928-3960). 아니면 경로 단위 덮어쓰기.
- `providerCallToCachedCall` (parser.ts:2807-2830): 캐시에는 원칙적으로 `costUSD`를 저장하지 않고 읽을 때 토큰으로 재가격한다. 예외는 `REPORTED_COST_PROVIDERS`(:2794, mistral-vibe·antigravity·devin·vercel-gateway·hermes·kiro 등) 또는 `costFromBilling === true`. (코드 확인) 가격표 갱신이 과거 데이터에도 반영되게 하려는 설계. (추론, 주석 types.ts:44-50 근거)

## 공통 helper (provider가 아닌 파일)

- `sqlite-session-parser.ts`: `createSqliteSessionParser`(:253), `discoverSqliteSessions`(:477). 현재 사용처는 `opencode.ts`, `kilo-code.ts`. (코드 확인)
- `session-message.ts`: `normalizeToolName`, `buildAssistantCall` 등 메시지→call 변환 helper(:50, :77). (코드 확인)
- `vscode-cline-parser.ts`: VS Code 확장 globalStorage 경로 탐색과 `createClineParser`(:135). (코드 확인)
- `opencode-file-parser.ts`(:51, :86), `mistral-vibe-unified.ts`(:54): 각 provider 전용 포맷 보조. (코드 확인)

## 특수 플래그 사용 예

- `network: true`: `vercel-gateway.ts:136` 하나. (코드 확인, grep 기준)
- `durableSources: true`: `copilot.ts:3680`, `quickdesk.ts:529`. 캐시 쪽 정적 목록 `DURABLE_PROVIDER_NAMES`는 `copilot`만 포함(session-cache.ts:346). (코드 확인)
- `probeRoots` 구현: providers 디렉터리 43개 파일에서 등장. (코드 확인, grep 파일 수)

## 새 provider 추가 시 체크 (추론)

1. `Provider` 구현 파일 작성 → `coreProviders` 또는 lazy loader + `lazyProviderNames` + `lazyProviderDisplayNames` 세 곳 동기화(주석 index.ts:202-208).
2. 청구 기록 기반 비용이면 `costFromBilling` 사용, 캐시 포맷이 바뀌면 `PROVIDER_PARSE_VERSIONS`(session-cache.ts) 갱신(주석 parser.ts:2785-2793).

## 미확인

- 43개 provider 각각의 discovery 경로와 포맷은 확인하지 않았다(Codex만 [[codeburn-codex-provider]]에서 확인).
- `onSkippedVersion` 콜백을 실제로 쓰는 provider 목록.
- lazy loader가 실제로 실패하는 환경(네이티브 모듈 부재)에서의 동작은 실행 확인하지 않았다.
