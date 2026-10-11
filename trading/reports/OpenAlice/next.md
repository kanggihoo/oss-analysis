# OpenAlice — 확인한 범위와 다음에 볼 것

- 분석 SHA: `87bc415260aaac92a072d89a1c6440268a3efdf1` (repos.lock.tsv와 일치해야 함)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1–Q7 (정리)
- 검증 수준 요약: 코드 확인 0 / 추론 0 / 미확인 12 (범위 정리 문서, 미확인은 아래 체크리스트 건수)

## 확인한 범위

| 영역 | 읽은 것 | 깊이 |
|---|---|---|
| 정책·문서 | `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/market-data-architecture.md`(1-140행), `docs/workspace-issues-and-scheduling.md`(205-230행) | 부분 |
| 스킬 14개 중 | `build-thesis`, `scan-value-chain`, `sector-rotation`, `retrospective`, `alice`, `alice-analysis`, `alice-uta`, `traderhub`, `market-data`, `self-scheduling`, `opencli-reader`, `delegate-autoquant`(앞 50행) | 전문 또는 핵심부 |
| 스킬 미독 | `workspace-manager`(헤딩만), `file-delivery`(헤딩만), `alice/references/collaboration.md`(헤딩만) | 헤딩 |
| 도구 표면 | `src/server/cli-commands.ts` 전체, `src/main.ts`(200-330, 380-513), `src/core/tool-center.ts` | 전체 |
| 데이터 | `src/domain/market-data/{vendors,hub-data,credential-map,aggregate-search}.ts`, `bars/*`, `reference/{service,cache,hub,macro}.ts`, `tool/{equity,etf,economy 상단,derivatives,indices,market,market-bars,quant,snapshot,sector-rotation,reference-board,simulate,source-resolve}.ts`, `domain/analysis/{snapshot,sector-rotation,simulate}.ts`, `calc-v2/evaluator.ts`(함수표), `indicator/functions/technical.ts` | 핵심부 |
| 뉴스 | `src/domain/news/` 전체(types, config, store, rss, rss-parser, archive) | 전체 |
| 스케줄 | `src/core/schedule-expr.ts`, `workspaces/schedule/{scanner(1-520행), declaration, marker-store(1-50행)}.ts`, `workspaces/issues/{declaration, auto-complete, comment-prompt}.ts`, `service.ts`(스캐너 배선 2360-2470, 용량 상수) | 핵심부 |
| 에이전트 주입 | `workspaces/{context-injector, alice-harness-policy, alice-harness-assets}.ts`, `adapters/{index, claude}.ts`, `templates/chat/*`, `templates/{auto-quant-v2,auto-prediction}/template.json` | 핵심부 |
| 경계 | `src/tool/trading.ts`(발췌), `services/trading-mode.ts`, `core/config.ts`(agent/marketData/trading/UTA 스키마), `services/uta/.../{guards/*, git/TradingGit.ts(1-135,238-262), UnifiedTradingAccount.ts(발췌), keyless-data-sources.ts}`, `routes-trading.ts`(495-535), `ui/src/pages/{TradingAsGitPage,InboxPage}.tsx`, `ui/src/components/PushApprovalPanel.tsx`(grep) | 부분 |
| opentypebb | `providers/{fmp,twse,yfinance}/index.ts`, `core/provider/utils/errors.ts`, `yfinance/utils/helpers.ts`(45-100), `extensions/news/news-router.ts` | 부분 |

## 미확인 항목 체크리스트

- [ ] **에이전트의 실제 행동**: 스킬을 얼마나 따르는지, 런타임이 웹 검색을 실제로 쓰는지(실행·설치 금지 규칙으로 실행 확인 불가). 현재는 `추론`.
- [ ] **TraderHub 호스팅 서비스**(`https://traderhub.openalice.ai`)가 어떤 키·데이터를 대신 제공하는지: 서버 코드는 이 레포 밖. 응답 스키마만 `reference/types.ts`로 간접 확인 가능.
- [ ] **FMP 키가 없을 때 `equityGetRatios` 동작**: 코드상 `provider: 'fmp'` 고정이고 hub 대체가 없다는 것까지만 확인. 실제 실패 형태는 미확인(`추론`).
- [ ] **AutoQuant V2 / Auto Prediction** 판단·백테스트 규칙: 별도 저장소(`TraderAlice/Auto-Quant-V2` v0.9.34 `52d6314…`, `Auto-Prediction` v0.1.2 `d6c9447…`)에 있어 이 SHA로는 확인 불가.
- [ ] **MCP 경로**: 워크스페이스가 `/mcp/:wsId`를 실제로 쓰는지(템플릿 bootstrap에서 `.mcp` 문자열을 찾지 못함). `simulate`/`calculate` 도구가 에이전트에게 닿는지 확정하지 못함.
- [ ] **yfinance fetcher 내부**: 심볼 처리, 한국 `.KS` 실제 동작, 요청 간격. 설명문(`providers/yfinance/index.ts:56`)만 확인.
- [ ] **`workspace-manager`, `file-delivery`, `collaboration.md` 스킬 본문**, `docs/` 나머지(약 40개 문서).
- [ ] **스펙/테스트 파일**: 동작 보증 근거로 쓸 수 있으나 읽지 않음(예: `scanner.spec.ts`, `trading.spec.ts`).
- [ ] **커넥터·알림 서비스**(`services/connector`): GUIDE §0 제외 범위.
- [ ] **브로커 내부**(CCXT/Alpaca/IBKR/Longbridge): GUIDE §0 제외 범위. 단, 봉 소스로서의 능력 표기(`getBarCapabilities`)만 간접 확인.
- [ ] **UI 세부**: Tracked 그래프, Issue 보드 화면의 표시 항목 상세.
- [ ] **사후 채점이 정말 없는지**: `src`, `services` 키워드 검색(hit-rate, outcome, post-mortem, scorecard)으로만 확인. 정기 리포트 후속 결정(`routine-follow-up-store.ts`)이 유일한 후보였고 사람용.

## 다음에 볼 파일과 함수

| 우선 | 파일 | 이유 |
|---|---|---|
| 1 | `src/workspaces/schedule/scanner.spec.ts` | 발사 판정, catch-up, 용량 초과 시나리오를 테스트가 어떻게 보증하는지 |
| 1 | `src/tool/trading.spec.ts`, `services/uta/.../guards/*.spec.ts` | 승인 경계와 가드 동작의 보증 범위 |
| 2 | `src/workspaces/templates/chat/bootstrap.mjs`, `_common.mjs` | `.mcp.json` 생성 여부, 에이전트가 받는 도구 표면 확정 |
| 2 | `src/webui/routes/reference.ts`, `routes/bars.ts`, `routes/news.ts` | UI와 에이전트가 같은 계약을 쓰는지 |
| 2 | `packages/opentypebb/src/providers/yfinance/models/equity-historical.ts` | 야후 봉 처리(한국 심볼, 분봉 한도) |
| 3 | `docs/workspace-issues-and-scheduling.md` 전체, `docs/workspace-agent-guidance.md` | 스케줄·지침 설계 의도 |
| 3 | `services/uta/src/http/routes-trading.ts` 나머지 | 승인 API 전체 |

## 분석 중 생긴 질문

1. `allowAiTrading=true`일 때 헤드리스(스케줄) 실행이 push까지 도달하는 것을 막는 다른 장치가 있는가? (`tradingPush` 외 경로, UTA 서비스 측 인증)
2. 도구 설명문에서 `calculateIndicator`를 아직 언급하는 이유: 모델 혼동 문제(`main.ts:268-270` 주석)가 남아 있는가?
3. RSS 인덱스의 7일 한계에서 `retrospective` 스킬이 "과거 구간 뉴스"를 요구하는 상황의 처리는 문서화되어 있는가?
4. 에이전트가 자체 웹 검색을 쓸 때 출처·시점 표기를 강제하는 규칙이 스킬 어디에 있는가? (현재까지 발견하지 못함)
