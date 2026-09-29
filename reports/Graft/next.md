# Next Session Plan: Graft

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `f9e65396e638e517aecae0d731017f53084d70ed`
- **작성/갱신 일자**: `2026-09-15`

---

## 1. 이번 세션에서 확인한 범위

- [x] 코드 기준 기록 (SHA, clean 워킹트리, 규모) → `artifacts/Graft/repo-metadata.txt`
- [x] 최상위 모듈 경계 파악: cli / engine / graph / ai / ask / mcp / hosts / claude / blast / viz / brain / telemetry / app
- [x] LLM 경계 확인: `--deep`만 `ai/llm/factory.ts`에 도달하고 build·check·ask는 tree-sitter 결정론 경로 (`코드 확인`)
- [x] 질의 전 그래프 갱신 경로 확인: `graph/refresh.ts:150 ensureFreshGraph()` → `fingerprint.probeDrift` → 필요시 `buildGraph` (`코드 확인`)
- [x] archify 다이어그램 3종(구조도 / `graft ask` 흐름 / 전체 시스템) 생성 및 검증 통과
- [x] 전체 네트워크 egress 지점 4개 식별: `--deep`(사용자 키), Brain Client(`/api/public/brains`, opt-in, 5s 타임아웃), GitHub App(`api.github.com`), 텔레메트리(`events.nanonets.com`, baked host) (`코드 확인`)
- [x] `src/app/*`가 CLI와 분리된 런타임임을 확인: `server.ts:73 createApp`(webhook HTTP) + `WorkQueue` + `fork()` 자식 워커(`review-process.ts:179`) (`코드 확인` — import 그래프·시그니처 수준)

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] `ask()`의 랭킹은 실제로 어떻게 합쳐지는가? `index-file`(토큰 카운트) / `graphrank`(그래프 전파) / `fuse`의 가중치와 컷오프. `src/ask/ask.ts`가 1,588줄로 가장 큰 파일이라 여기가 사실상 제품의 심장으로 보인다 (`추론`).
- [ ] `--deep` 없이 만든 그래프와 `--deep` 그래프의 검색 품질 차이는 어디서 발생하는가? (concept node 유무가 랭킹에 미치는 영향)
- [ ] 캐시 무효화 정확성: `contentHash` 기반 재사용이 언제 stale해질 수 있는가? `graph/extract-cache.ts` + `fingerprint.ts`의 drift 판정 경계 조건.
- [ ] `src/brain/*` 상세: 파일 구성과 엔드포인트(`link.ts:133 baseUrlFor` → `/api/public/brains/<id>/rules/anchors`, `RULES_TTL_MS` 6시간, `MAX_ATTACHED_RULES` 6)는 확인했으나, 규칙이 실제로 프롬프트에 어떻게 섞이는지(`attach.ts:37 rulesForPointers`의 선택 기준)와 `push.ts`가 무엇을 업로드하는지는 미확인.
- [ ] `src/app/*` 상세: 별도 런타임인 것은 확인. 남은 것은 큐잉/중복 제거(`jobKey`), 자식 프로세스 프로토콜(`StartMessage`/`PublishMessage`/`DoneMessage`), 리뷰 결과가 PR에 어떻게 게시되는지. `docs/github-app.md`와 대조 필요.
- [ ] 에이전트 통합의 실제 효과: `src/claude/hooks.ts`가 어떤 hook 이벤트에 무엇을 주입하는가. `test/claude-hooks.test.ts`가 35KB로 가장 크다.
- [ ] README 벤치마크(−42% 토큰 등)의 재현 절차가 레포 안에 있는가? (현재까지 미발견)

## 3. 다음에 볼 파일 및 함수 (Next Entry Points)

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src/ask/ask.ts` | `ask()`, `formatAsk()` | 랭킹·융합·컨텍스트 조립의 실제 순서와 컷오프 |
| `src/ask/fuse.ts`, `src/ask/graphrank.ts` | 점수 결합 | 두 신호의 가중치와 정규화 방식 |
| `src/graph/fingerprint.ts` | `probeDrift()`, `readFingerprint()` | drift 판정의 정확한 비교 대상과 비용 |
| `src/graph/extract-cache.ts` | 캐시 키 | content hash 재사용 경계 |
| `src/claude/hooks.ts` | hook 등록 | Claude Code 턴마다 실제로 주입되는 내용 |
| `src/brain/link.ts`, `src/brain/push.ts` | 링크/업로드 | 오픈소스 ↔ Trail 클라우드 경계 |

## 4. 참고 사항 및 후속 제안

- clone은 `--depth 50` 얕은 복제다. 히스토리 분석(blame, 설계 변천)이 필요하면 `git fetch --unshallow` 먼저 실행할 것.
- 실행 검증은 아직 하지 않았다. `npm i`는 tree-sitter 네이티브 빌드(node-gyp)를 요구하므로 Windows에서 시간이 걸릴 수 있다. 다음 세션에서 `npm test`(`scripts/run-tests.mjs`, 122개 파일)를 돌려 `실행 확인` 근거를 확보하면 좋다.
- `graft build`를 이 워크스페이스 자체에 한 번 돌려보면 산출물(`graft/*.md`, `.graph/wiring.json`)의 실제 모양을 가장 빠르게 볼 수 있다 — 단, `--deep` 없이 돌리면 키가 필요 없다.
- 텔레메트리는 기본 on이다(`DO_NOT_TRACK=1` 또는 `graft telemetry disable`로 차단). 실행 검증 전에 꺼두는 편이 안전하다.
