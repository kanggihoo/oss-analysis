# Next Session Plan: CodeBurn

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `9a40cc603fcd194caca9daa8c5134a61ea7e0e2b`
- **작성/갱신 일자**: `2026-10-15`

---

## 1. 이번 세션에서 확인한 범위

- [x] `repos/codeburn`을 `f1bf7a1` → `9a40cc6`로 fast-forward. 메타데이터 기록 (`artifacts/codeburn/repo-metadata.txt`)
- [x] 진입점, 명령 등록, provider registry(43개), 두 캐시의 위치와 버전 (코드 확인)
- [x] `codeburn report` 대표 흐름 10단계 (코드 확인, 일부 내부는 미확인)
- [x] archify 구조도 `structure`, 흐름도 `report-flow`
- [x] overview에 주요 기능 절 추가 (명령 그룹별, 근거 수준 표기)

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [x] `ensureCacheHydrated` backfill → [[codeburn-day-aggregation-and-caching]] (2026-10-15 재작성)
- [ ] `hydrateCache`의 365일 backfill과 기간 파싱이 서로 다른 `parseAllSessions` 호출이라 두 번 도는지 (세션 캐시 덕에 싸다는 것은 `추론`)
- [x] `CachedFile`과 piece 이름 규칙 → [[codeburn-data-ingestion-and-caching]]
- [x] 비용 계산 시점: 캐시에서 읽을 때 재계산, 예외는 `REPORTED_COST_PROVIDERS`·`costFromBilling` (`src/parser.ts:2794,2821,2984`)
- [ ] optimize · guard · plugins · quota · sync · act · sharing 하위 시스템 역할
- [ ] 주변 앱(`mac/`, `windows/`, `app/`, `vscode/`, `gnome/`, `dash/`) 내부 구조
- [x] wiki concept 노트 10개를 `9a40cc6` 기준으로 처음부터 다시 씀 (2026-10-15, 코드 읽기만, 실행 없음)

---

## 3. 다음에 볼 파일 및 함수 (Next Entry Points)

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src/parser.ts:2123` | `scanProjectDirs`, `fingerprintFile`, `reconcileFile` | 증분 파싱 판정 (Q1) |
| `src/session-cache.ts:239`, `:2390` | `CACHE_VERSION`, `saveCache` | 캐시 구조와 원자적 저장 (Q1) |
| `src/models.ts:537`, `:1516` | `loadPricing`, `calculateCost` | 가격표 폴백과 비용 공식 (Q2) |
| `src/providers/claude.ts` | `discoverSessions`, `createSessionParser` | 대표 provider (Q3) |
| `src/cache-refresh-lock.ts` | `acquireCacheRefreshLock` | 다중 프로세스 경쟁 (Q4) |
| `src/classifier.ts:200` | `classifyTurn` | 분류 규칙 (Q5) |

---

## 4. 참고 사항 및 후속 제안

- 실행 실험은 아직 안 했다. `npm ci` 후 `npm run dev -- report --format json`이 가장 싸다. 단, 의존성 설치와 실제 홈 디렉터리 로그 읽기가 따르므로 먼저 허락을 받는다. `CODEBURN_CACHE_DIR`로 캐시 위치를 스크래치로 돌릴 수 있다 (`src/cache-dir.ts:11-13`).
- `loadPricing`과 `loadCurrency`는 네트워크(LiteLLM, Frankfurter)에 접속할 수 있다. 실험 시 오프라인 폴백 경로도 함께 본다.
- `repos/codeburn`의 미추적 `AGENTS.md`는 graphify 사용 규칙이다. 이 워크스페이스 규칙이 아니므로 따르지 않는다.
