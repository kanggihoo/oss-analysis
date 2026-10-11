# OpenAlice — 데이터 인벤토리와 수집 방식

- 분석 SHA: `87bc415260aaac92a072d89a1c6440268a3efdf1` (repos.lock.tsv와 일치해야 함)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1, Q2
- 검증 수준 요약: 코드 확인 90 / 추론 2 / 미확인 1 (표의 검증 열 기준 집계)

> 읽는 법: OpenAlice에서 "에이전트가 쓰는 데이터"는 **CLI 도구 표면**(`alice`, `traderhub`, `alice-uta`)으로 정의된다(`src/server/cli-commands.ts:20-270`). 각 도구의 이름 → 구현 → 제공자를 따라가서 표를 만들었다. 서비스 코드가 도구를 ToolCenter에 등록하는 위치는 `src/main.ts:247-282`.

## Q1. 데이터 인벤토리 {#q1}

### 1.1 도구 표면 (에이전트가 닿을 수 있는 것)

| CLI | 그룹 | 내부 도구 | 위치 | 검증 |
|---|---|---|---|---|
| `alice` | rss: glob/grep/window/read | globRss, grepRss, windowRss, readRss | `cli-commands.ts:35-40` | 코드 확인 |
| `alice` | market: search/search-bars/bars/vendors/vendor-set | marketSearchForResearch, searchBars, getMarketBars, listMarketVendors, setMarketVendor | `cli-commands.ts:42-51` | 코드 확인 |
| `alice` | analysis: search-bars/quant/snapshot | searchBars, calculateQuant, marketSnapshot | `cli-commands.ts:52-58` | 코드 확인 |
| `traderhub` | board(get/rotation), equity, etf, economy, global, shipping, fed, crypto, index | marketGetBoard, sectorRotation, equityGet*, etf*, economy*, crypto*, indexSearch | `cli-commands.ts:61-132` | 코드 확인 |
| `alice-uta` | account/contract/order/position/git/market/sim | listUTAs, getPortfolio, getQuote, placeOrder … | `cli-commands.ts:212-270` | 코드 확인 |
| `alice`(워크스페이스) | peer/conversation/inbox/issue/provenance/track/… | workspace_*, inbox_push, issue_*, entity_upsert | `cli-commands.ts:134-211` | 코드 확인 |
| (CLI 미노출) | — | `simulate`(진입 1회+청산 규칙 1개 백테스트), `calculate`(thinking) | 등록 `main.ts:247`, `:274` / `cli-commands.ts`에 없음 | 코드 확인 |

`simulate`와 `calculate`(thinking)는 ToolCenter에 등록되지만 CLI_EXPORTS에는 없다. MCP 서버(`src/server/mcp.ts:73-92`, 설정 기본 `enabled: false` `src/core/config.ts:355-358`)로만 닿을 수 있다는 것은 `추론`(워크스페이스가 `/mcp/:wsId`를 쓰는지 여부는 템플릿 bootstrap에서 `.mcp` 문자열을 찾지 못해 `미확인`).

### 1.2 데이터 분류별 표

| 분류 | 데이터 / 필드 | 제공자 (API, 라이브러리) | 키 필요 | 소비 주체 (에이전트, 단계) | 근거 위치 | 검증 |
|---|---|---|---|---|---|---|
| 가격·거래량 | OHLCV 봉(`date,open,high,low,close,volume`), 간격 1m/5m/15m/30m/1h/4h/1d/1w, 최대 5000봉 | 벤더: yfinance(기본), fmp, eastmoney, twse(=Yahoo 차트). 브로커: UTA 소스(Alpaca IEX, CCXT 등) | yfinance 불필요 / fmp 키 / 브로커 계정 | 채팅·헤드리스 에이전트가 `alice market bars`, `alice analysis snapshot/quant` 호출 | `bars/bar-service.ts:31`, `:34-39`, `:41`, `:198-260`, `:263-308` | 코드 확인 |
| 가격·거래량 | 키 없는 거래소 공개 데이터 `binance-readonly|BTC/USDT` (binance/okx/bybit, 옵트인) | CCXT 공개 API | 불필요 | 크립토 봉 소스 | `config.ts:384`, `:404-410`, `services/uta/src/domain/trading/keyless-data-sources.ts:17-35` | 코드 확인 |
| 가격·거래량 | 종목 검색(미국 SEC 심볼 인덱스 + 벤더 온라인 검색 + 크립토/FX yfinance 검색 + 원자재 카탈로그) | SEC(via opentypebb), yfinance, eastmoney 등 | 불필요 | 심볼→barId 해석 | `aggregate-search.ts:86-161`, `symbol-index.ts:40`, `:42-43` | 코드 확인 |
| 가격·거래량 | 섹터 ETF 11개(XLK…XLU)+SPY 일봉 300일 | yfinance(기본 equity 벤더) | 불필요 | `traderhub board rotation` | `analysis/sector-rotation.ts:23-38`, `:264-296` | 코드 확인 |
| 가격·거래량 | 시장 랭킹: gainers/losers/active, 스크리너 4종, `relative_volume`, `dollar_volume`, `turnover`, `avg_volume` | yfinance(기본), 또는 hub | 불필요 | `traderhub equity discover`, `board get --board movers` | `tool/equity.ts:184-247`, `reference/service.ts:58-84` | 코드 확인 |
| 기술지표 | `sma(s,n)`, `ema(s,n)`, `macd(s,fast,slow,signal)`(인자 4개 필수), `slope(s,n)`, `rsi(s,n=14)`, `roc(s,n)`, `stdev`, `atr(h,l,c,n)`, `bbands(s,n,std=2)`, `zscore(s,n?)`, `rvol(v,n=20)`, `obv`, `mfi(...,n=14)`, `vwap`, `correlation`, `highest/lowest(s,n)`, `max/min/sum/average/median` | 자체 구현(순수 TS, 코드 계산) | 불필요 | 에이전트가 스크립트를 써서 호출. **파라미터는 에이전트가 정함(기본값은 rsi14, rvol20, mfi14, bbands std2뿐)** | `calc-v2/evaluator.ts:305-326`, `indicator/functions/technical.ts:15-134`, `statistics.ts:14-159` | 코드 확인 |
| 기술지표 | snapshot 고정 지표: `sma20`, `sma50`, `rsi14`, `periodHigh/Low`, `distFromHighPct/LowPct`, `latest.changePct/dayAmplitudePct` (기본 창 90봉) | 자체 구현 | 불필요 | `alice analysis snapshot` | `domain/analysis/snapshot.ts:96-170`, `tool/snapshot.ts:22-52` | 코드 확인 |
| 기술지표 | 섹터 로테이션: 기간 수익률 1D/1W/1M/3M/6M = 1/5/21/63/126거래일, `rel_strength`(vs SPY), `momentum_acceleration`, `dv_share`, `dv_share_change`, `rvol`(20일), `rotation_score` | 자체 구현 | 불필요 | `traderhub board rotation` | `sector-rotation.ts:41`, `:45`, `:132-164`, `:166-262` | 코드 확인 |
| 펀더멘털 | 프로필+핵심지표(시총, PER, PBR, EV/EBITDA, 배당수익률 등) | yfinance(대만 `.TW/.TWO`는 twse 우선) | 불필요 | `traderhub equity profile` | `tool/equity.ts:16-48` | 코드 확인 |
| 펀더멘털 | 재무제표 income/balance/cash, annual/quarter, limit 기본 5 | yfinance 고정 | 불필요 | `traderhub equity financials` | `tool/equity.ts:50-77` (`:64`) | 코드 확인 |
| 펀더멘털 | 재무비율(ROE, ROA, 마진, 유동·당좌비율, D/E, PER, PBR, PSR 등) TTM+이력 | **FMP 고정** | **FMP 키 필요**(코드상) | `traderhub equity ratios` | `tool/equity.ts:79-109` (`:104`) | 코드 확인 |
| 펀더멘털 | 애널리스트 목표가 컨센서스(high/low/consensus/median) | yfinance | 불필요 | `traderhub equity estimates` | `tool/equity.ts:170-182` | 코드 확인 |
| 펀더멘털 | 실적 발표 캘린더(종목별/기간별) | FMP 고정, hub가 캘린더 3종 대체 | FMP 키 또는 hub | `traderhub equity earnings`, `board get --board calendar` | `tool/equity.ts:111-130`, `market-data/hub-data.ts:16-20`, `reference/service.ts:86-128` | 코드 확인 |
| 펀더멘털 | ETF 정보·보유종목·섹터 비중 | yfinance(info, search), FMP 우선→yfinance 폴백(holdings, sectors) | FMP 선택 | `traderhub etf *` | `tool/etf.ts:42`, `:69`, `:89-91`, `:109-111` | 코드 확인 |
| 수급·자금흐름 | 내부자 거래(Form 4) | FMP 우선→실패 시 yfinance | FMP 선택 | `traderhub equity insiders` | `tool/equity.ts:132-154` | 코드 확인 |
| 수급·자금흐름 | 공매도 지표(shares short, % float, days-to-cover) | yfinance 공유통계 | 불필요 | `traderhub equity short-interest` | `tool/equity.ts:156-168` | 코드 확인 |
| 수급·자금흐름 | 섹터 달러거래량 점유율 변화(`dv_share_change`)를 **자금 이동 대리 지표**로 사용 | 자체 계산(ETF 거래대금) | 불필요 | 로테이션 보드 | `sector-rotation.ts:168-174`(방법론 문자열에 "proxy for fund flow, not a clean read" 명시) | 코드 확인 |
| 수급·자금흐름 | 기관·외국인·프로그램 매매 등 투자자별 수급 | 없음 | — | — | `src/tool/`, `packages/opentypebb/src/providers/` 둘러봤으나 해당 도구 없음 (FMP `InstitutionalOwnership` fetcher는 있으나 Alice 도구 미연결, 아래 1.3) | 코드 확인(없음) |
| 뉴스 | RSS 기사: `title, content(요약), pubTs, ts, dedupKey, metadata{source,link,guid,categories,image}` | 사용자 RSS 28개 중 기본 8개 활성(Fed, ECB, MarketWatch Top, WSJ Markets, CNBC Economy, Nikkei Asia, SCMP Business, CoinDesk) | 불필요 | `alice rss glob/grep/window/read` | `domain/news/types.ts:6-21`, `news/config.ts:34-268`, `collector/rss.ts:105-139` | 코드 확인 |
| 감성·소셜 | 소셜·감성 점수 | 없음 | — | — | `src/`, `services/`에서 reddit/twitter/stocktwits 키워드 파일 없음. 유사물: UMich 소비자심리(거시 카드, `macro.ts:38`). 개인투자자 활동·감성 타입 `TopRetailData{activity, sentiment}`는 정의와 클라이언트 메서드만 있음(1.3) | 코드 확인(없음) |
| 거시 | 14개 FRED 카드: DFF, DGS2, DGS10, T10Y2Y, UNRATE, ICSA, DCOILWTICO, DTWEXBGS, PAYEMS, M2SL, UMCSENT, T10YIE, DRTSCILM + CPIAUCSL→CPI YoY 파생 | FRED(provider `federal_reserve`), hub가 대체 가능 | FRED 키 또는 hub | `traderhub board get --board macro` | `reference/macro.ts:25-46`, `:69-112` | 코드 확인 |
| 거시 | 임의 FRED/BLS/EIA 시계열 검색·조회, EIA 석유·에너지 | FRED, BLS, EIA | 키 또는 hub | `traderhub economy *` | `tool/economy.ts:24-28`, `:35-215` | 코드 확인 |
| 거시 | OECD 국가별 CPI/금리/선행지수/주택/주가/소매, 12+개국(한국 `south_korea` 포함) | OECD | 불필요 | `traderhub global *` | `tool/economy.ts:219-390`(국가 목록 `:227`) | 코드 확인 |
| 거시 | 해상 병목 6곳 일별 통행(IMF PortWatch), FOMC 문서, 연준 대차대조표(WALCL 등), 프라이머리 딜러 포지션, ECB 국제수지 | IMF, FRED, NY Fed, ECB | FRED 키 또는 hub | 해당 보드/도구 | `tool/economy.ts:280-340`, `:391-458`, `reference/service.ts:130-137` | 코드 확인 |
| 거시 | S&P500 PER·CAPE·수익률 스트립 | multpl (`reference-board.ts:26`에 명시) | 불필요 | `board get --board valuation` | `reference/valuation.ts`, `service.ts:144-147` | 코드 확인 |
| 코인 전용 | BTC/ETH 선물 기간구조와 연환산 베이시스, Deribit 옵션 체인·선물 목록 | Deribit | 불필요 | `board get --board term-structure`, `traderhub crypto options/futures` | `tool/derivatives.ts:29`, `:42`, `reference/term-structure.ts`, `service.ts:139-142` | 코드 확인 |
| 코인 전용 | 옵션 미결제약정(OI): Deribit 옵션 체인 응답에 포함 | Deribit | 불필요 | `traderhub crypto options` | `tool/derivatives.ts:19-29` | 코드 확인 |
| 코인 전용 | 펀딩비: CCXT 계정 전용 `getFundingRate`(현재·이전 펀딩비). UTA 서비스 ToolCenter에 `trading-ccxt` 그룹으로 등록되나 `CLI_EXPORTS`에 없어 에이전트 CLI로는 노출되지 않는 것으로 보임 | CCXT 브로커 | 브로커 계정 | UTA 내부 | `services/uta/.../brokers/ccxt/ccxt-tools.ts:16-63`, `uta-manager.ts:108`, `:137` | 코드 확인(등록) / 추론(CLI 비노출) |
| 코인 전용 | 온체인, 공포탐욕지수, 거래소 간 OI 집계 | 없음 | — | — | `src`, `services`, `packages/opentypebb/src`에서 `on-chain`, `fear greed`, `glassnode`, `whale` 키워드 검색 결과 해당 데이터 없음 | 코드 확인(없음) |
| 포트폴리오·보유 현황 | 포지션: `symbol, secType, aliceId, side, quantity, avgCost, marketPrice, marketValue, unrealizedPnL, realizedPnL, percentageOfEquity, percentageOfPortfolio, risk(레버리지·청산가)`; 계정 정보; 대기 주문; 체결 이력; FX 환산(USD) | UTA(브로커 어댑터) | 브로커 키 | `alice-uta account portfolio` 등 | `tool/trading.ts:333-429`, `:311-332`, `:431-470`, `:872-910` | 코드 확인 |
| 포트폴리오·보유 현황 | 장 개폐 상태(isOpen, nextOpen, nextClose) | 브로커 마켓 클록 | 브로커 키 | `alice-uta market clock` | `tool/trading.ts:594-608` | 코드 확인 |
| 과거 판단과 메모리 | 거래 커밋 이력(Trading-as-Git 로그, 커밋 메시지=매매 사유), 주문 이력 | UTA TradingGit | — | `alice-uta git log/show`, `order history` | `tool/trading.ts:610-639`, `services/uta/.../git/TradingGit.ts:94-117` | 코드 확인 |
| 과거 판단과 메모리 | 워크스페이스 파일·Git 이력, Issue 코멘트(`<id>.comments.json`), Inbox 리포트, 추적 엔티티(`entities.jsonl`), 출처(provenance) | 로컬 파일 | — | 에이전트가 파일·`alice inbox/issue/track` 호출 | `core/entity-store.ts:1-21`, `tool/inbox-push.ts:15-85`, `skills/self-scheduling/SKILL.md:236-245` | 코드 확인 |

### 1.3 정의만 있고 Alice에서 쓰이지 않는 데이터 소스

| 항목 | 정의 위치 | 호출 확인 | 판단 | 검증 |
|---|---|---|---|---|
| opentypebb `news` 라우터(`WorldNews`, `CompanyNews`; FMP·yfinance fetcher) | `packages/opentypebb/src/extensions/news/news-router.ts:8-29`, `providers/fmp/index.ts:96-97`, `providers/yfinance/index.ts:13` | `src/domain/market-data/client/typebb/`에 news 클라이언트 없음(파일: base, commodity, crypto, currency, derivatives, economy, equity, etf, index). `src/`에서 `getCompanyNews`/`CompanyNews` grep 결과 없음. 라우터는 `core/api/app-loader.ts:36`, `:85`에 마운트됨 | **정의·마운트만, Alice 도구로는 미사용.** 에이전트는 RSS만 본다 | 코드 확인 |
| 사용자 키 `tiingo`, `benzinga`, `biztoc`, `nasdaq`, `tradingeconomics`, `econdb`, `intrinio` | `core/config.ts:332-344`, `credential-map.ts:15-27` | `packages/opentypebb/src/providers/` 디렉터리에는 econdb, intrinio만 있고 tiingo·benzinga·biztoc·nasdaq·tradingeconomics provider 디렉터리 없음. econdb/intrinio를 부르는 `src/tool` 호출 없음 | 키 슬롯만 있음 (미사용) | 코드 확인 |
| 개인투자자 활동·감성 `TopRetail`(`activity`, `sentiment`) | `domain/market-data/equity/types/discovery.ts:46-51`, `client/typebb/equity-client.ts:250` | `src/tool/`에 호출 없음(`getTopRetail` grep: 클라이언트 정의만) | 정의만, 미사용 | 코드 확인 |
| FMP `InstitutionalOwnership`, `GovernmentTrades`, `AnalystEstimates`, `EarningsCallTranscript`, `CompanyFilings` 등 fetcher 다수 | `providers/fmp/index.ts:86-140` | `src/tool/`에 대응 도구 없음 (사용 도구는 equity.ts의 Profile/Financials/Ratios/Insider/Calendar) | 라이브러리에 있으나 도구로 미노출 | 코드 확인 |
| v1 `calculateIndicator`(`createAnalysisTools`) | `src/tool/analysis.ts` | `main.ts:268-270` 주석: "retired from the tool surface". 그러나 `tool/market.ts:27`, `:31` 설명문이 아직 `calculateIndicator`를 언급 | 코드는 남아 있고 등록 안 됨. 설명문은 낡음 | 코드 확인 |

### 1.4 시장별 차이

| 시장 | 쓰는 데이터 | 근거 | 검증 |
|---|---|---|---|
| 미국 주식 | SEC 심볼 인덱스, yfinance(봉·프로필·재무·컨센서스·공매도), FMP(비율·캘린더·내부자), Form 4, 섹터 ETF | `symbol-index.ts:40`, `tool/equity.ts` | 코드 확인 |
| 대만 | `.TW/.TWO` 심볼이면 twse를 키 지표(PER·배당수익률·PBR)에 우선. 옵트인 벤더 | `tool/equity.ts:27-34`, `providers/twse/index.ts:23-45` | 코드 확인 |
| 중국 A주 | eastmoney 벤더 옵트인(secid `1.600519`), 전용 K라인(전복권) | `core/config.ts:325-331`, `aggregate-search.ts:101-111` | 코드 확인 |
| 한국 | 한국 전용 소스·분기 코드 없음(upbit, kiwoom, pykrx, KRX 키워드 검색 결과 없음). 다만 yfinance 벤더 설명이 "KR (.KS)"를 커버 범위로 명시하므로 Yahoo 티커 `005930.KS` 같은 입력이 가능하다는 것이 설계 의도. OECD 거시에 `south_korea` 있음 | `providers/yfinance/index.ts:56-57`, `tool/economy.ts:227` | 코드 확인(없음, 설명문) / 추론(실제 데이터 품질·지연은 미확인) |
| 크립토 | yfinance `BTC-USD` 류, 키 없는 binance/okx/bybit 공개 봉, CCXT 브로커, Deribit 파생 | `aggregate-search.ts:108`, `config.ts:384-410`, `tool/derivatives.ts` | 코드 확인 |

---

## Q2. 수집 방식 {#q2}

### 2.1 수집 계층 구조와 폴백 체인

| 계층 | 구조 | 우선순위 설정 | 위치 | 검증 |
|---|---|---|---|---|
| 봉(K라인) | `BarService`가 벤더 어댑터와 UTA 브로커를 **한 `barId="{sourceId}|{symbol}"` 네임스페이스로 연합**. 같은 자산이라도 소스가 다르면 barId가 다르고 자동 교체(폴백)를 하지 않음("redundancy is the feature") | 사용자가 barId로 고름. 소스 후보 정렬은 관련도 → 비파생 우선 → 신선도 랭크(realtime0, iex1, subscription2, delayed3, free4) | `bars/types.ts:3-20`, `bar-service.ts:386-401`, `tool/source-resolve.ts:18-20`, `:33-59` | 코드 확인 |
| 봉 | 벤더 선택은 `config.marketData.providers.{equity,crypto,currency,commodity}`(기본 모두 yfinance) + `extraVendors` | `market-data.json` | `core/config.ts:312-331` | 코드 확인 |
| 벤더 토글 | `setMarketVendor`가 `extraVendors`를 바꾸면 다음 검색에서 즉시 반영(재시작 불필요) | 에이전트가 `alice market vendor-set` | `domain/market-data/vendors.ts:43-107`, `main.ts:206-216` | 코드 확인 |
| 보드(저빈도) | **hub 우선 → 로컬 빌드(사용자 키) → 오류**. hub는 `https://traderhub.openalice.ai`(기본 활성), 보드별 서킷브레이커 60초, 타임아웃 5초. `meta.origin`으로 hub/local 구분 | `marketData.hub.enabled/baseUrl` | `reference/hub.ts:20-77`, `config.ts:345-351`, `reference/service.ts:55-147` | 코드 확인 |
| 캘린더(종목 단위) | FMP 호출을 hub로 대체(프록시 래퍼), 알 수 없는 파라미터면 hub 우회, 실패 시 로컬 | 클라이언트 메서드 수준 | `hub-data.ts:16-69` | 코드 확인 |
| 키 대체 | FRED/EIA/BLS 키가 없으면 `hub:<baseUrl>` 센티널로 hub 키 프록시 사용, 사용자 키가 있으면 우선 | — | `credential-map.ts:47-61` | 코드 확인 |
| 펀더멘털 도구 | 폴백이 **도구마다 하드코딩**: 프로필(대만만 twse↔yfinance 순서 변경), 내부자(FMP→yfinance), ETF holdings·sectors(FMP→yfinance). 재무제표는 yfinance 고정, 비율은 FMP 고정 | 코드 | `tool/equity.ts:27-45`, `:143-153`; `tool/etf.ts:89-91`, `:109-111` | 코드 확인 |

### 2.2 가져오는 방식: pre-fetch vs tool call

| 데이터 | 방식 | 근거 | 검증 |
|---|---|---|---|
| 봉, 지표, 스냅샷, 펀더멘털, 거시, 포트폴리오, 보드 | **tool call**(에이전트가 셸에서 CLI 실행 → 게이트웨이 → ToolCenter 도구). 프롬프트에 데이터를 미리 넣지 않음 | `cli-commands.ts:20-270`, `skills/build-thesis/SKILL.md:26-31`("don't answer from memory — run the tools") | 코드 확인 |
| RSS 기사 | **사전 수집(pre-fetch)**: 10분마다 백그라운드로 JSONL에 적재, 에이전트는 조회만 | `main.ts:421-439`, `domain/news/config.ts:22` | 코드 확인 |
| 보드 데이터 | 호출 시 생성하되 TTL 캐시(아래 2.4) — 사실상 지연 평가 캐시 | `reference/cache.ts:19-53` | 코드 확인 |
| 심볼 인덱스 | **부팅 시 로드**(24시간 캐시 파일, API 실패 시 만료 캐시, 전부 실패해도 빈 인덱스로 기동) | `symbol-index.ts:42-43`, `:58-80`, `main.ts:200-201` | 코드 확인 |
| 스케줄 실행 프롬프트 | Issue 본문(What) 그대로. 데이터 주입 없음 | `issues/declaration.ts:341-343` | 코드 확인 |

### 2.3 원시 데이터 가공

| 항목 | 처리 | 위치 | 검증 |
|---|---|---|---|
| 지표 계산 | 코드가 계산(LLM에 맡기지 않음). 지표는 **최신 스칼라만 반환**, 시계열 인덱싱 불가. 조건문·크로스오버 연산자 없음(에이전트가 결과를 비교) | `alice-analysis/SKILL.md:63-66`, `:158-159`, `calc-v2/evaluator.ts:305-326` | 코드 확인 |
| 봉 정제 | OHLC 중 하나라도 비유한(null/NaN)이면 행 제외하고 `meta.quality{inspectedRows, excludedRows, latestExcludedRecordAt}` 보고 | `bars/quality.ts:1-22`, `bar-service.ts:239-244` | 코드 확인 |
| 날짜 | 일/주봉은 날짜만(`YYYY-MM-DD`), 분봉은 ISO 인스턴트. 브로커가 세션 시작 시각으로 찍는 타임스탬프를 날짜로 정규화 | `bar-service.ts:118-129` | 코드 확인 |
| 단위 | 보드 카드에 스케일 적용(M2 ×1e9, 고용 ×1e3), CPI YoY는 코드로 파생(`(value/전년동월 - 1) ×100`). 스킬은 단위 규칙을 명시(`percent_change`는 분수 0.052, OECD는 퍼센트 단위) | `reference/macro.ts:36-37`, `:56-67`, `traderhub/SKILL.md:125-133` | 코드 확인 |
| 결측치 | 로테이션: 데이터 부족 시 해당 기간 수익률 `null`, 점수는 가능한 입력만 평균. **ETF 하나라도 조회 실패하면 `catch(() => [])`로 조용히 빈 배열 처리** | `sector-rotation.ts:86-93`, `:220-221`, `:286` | 코드 확인 |
| 4h 봉 | yfinance/eastmoney/twse는 4h 미지원(오류), FMP는 1w 미지원(오류) — 에이전트에게 "1h로 받아 직접 집계"를 제안 | `bar-service.ts:204-207` | 코드 확인 |
| yfinance 분봉 보관 한도 | 1m=7일, 1h=729일, 기타 분봉=59일. 한도 밖 `start`는 오류, 추론한 창은 줄임 | `bar-service.ts:208-218` | 코드 확인 |

### 2.4 캐시

| 대상 | 위치 | 키 | 만료 | 검증 |
|---|---|---|---|---|
| 보드(메모리) | `cachedBoard` 클로저 | 보드별 1엔트리 | movers 60초, termStructure 120초, calendar·macro 30분, fed 1시간, valuation·globalMacro·shipping 6시간. 만료+상류 실패 시 마지막 값을 `meta.stale: true`로 제공 | `reference/service.ts:44-53`, `cache.ts:19-53` | 코드 확인 |
| 캘린더 사용자 지정 기간 | 캐시 우회(`uncachedCalendar`) | — | 없음 | `service.ts:153-156`, `:166-195` | 코드 확인 |
| 심볼 인덱스 | `data/cache/equity/symbols.json` | — | 24시간 | `symbol-index.ts:42-43` | 코드 확인 |
| RSS | `data/news-collector/news.jsonl`(append-only) + 메모리 버퍼 | `dedupKey`(guid > link > sha256(title+content) 16자) | 버퍼는 최신 2000건·7일, 디스크는 보관(조회 도구는 `readRss`의 id 조회만 디스크 접근) | `news/store.ts:21-23`, `:74-121`, `:310-322`, `:260-280`, `news/config.ts:24-26` | 코드 확인 |
| 봉(K라인) | **캐시 없음**. 호출마다 벤더/브로커 조회 | `bar-service.ts` 전체에서 cache 문자열 없음(grep) | — | 코드 확인 |
| hub 장애 | 보드별 60초 브레이커 | 보드명 | 60초 | `hub.ts:29-31`, `:46-60` | 코드 확인 |

### 2.5 미래 데이터 차단 (look-ahead 방지)

| 장치 | 설명 | 위치 | 검증 |
|---|---|---|---|
| `asOf`/`end` 상한 | 벤더 호출에 `end_date`를 전달하고 **응답을 한 번 더 `<= end_date`로 후처리 필터**. 브로커 경로도 같음. `end`와 `asOf`가 다르면 오류 | `bar-service.ts:219-244`, `:288-290`, `:416` | 코드 확인 |
| snapshot | 기본 `asOf`는 현재, 지정하면 `end`와 `asOf`를 모두 전달해 창 크기와 상한을 함께 고정 | `domain/analysis/snapshot.ts:101-109` | 코드 확인 |
| simulate | 진입일~`asOf` 사이만 걷기(`asOf` 이후 봉 미사용) | `domain/analysis/simulate.ts:4-8` | 코드 확인 |
| 뉴스 | `getNewsV2`의 `endTime`으로 `pubTs > endTime` 제외. 단 `grepRss/globRss`는 `endTime=new Date()` 고정이라 실시간 전용, `windowRss`만 과거 구간 지정 가능 | `news/store.ts:229-258`, `news/query/archive.ts:219`, `:269-278` | 코드 확인 |
| 뉴스 보관 한계 | 조회 인덱스는 메모리 2000건·7일이라 **오래된 시점의 retro에는 뉴스가 비어 있을 수 있음**("not the full disk archive") | `news/query/archive.ts:206-208`, `:257-258` | 코드 확인 |
| 펀더멘털/컨센서스 | as-of 필터 없음(항상 현재 시점 값). 도구에 `asOf` 파라미터 없음 | `tool/equity.ts` 전체 | 코드 확인(없음) |
| 신선도 계약 | `meta.asOf`, `isLatestActual`(주말 제외 거래일 격차 0), `staleTradingDays`, `freshness{timestampKind, delay.status, recordAgeSeconds, historical}` — 휴일은 무시(격차를 ≤1 과대 계산) | `bar-service.ts:152-182`, `bars/freshness.ts:21-46` | 코드 확인 |

백테스트 신뢰성: 가격 as-of는 코드가 막지만, 펀더멘털과 컨센서스는 막지 않으므로 과거 시점 분석에 쓸 때는 에이전트가 직접 제외해야 한다(스킬 `retrospective`는 가격·뉴스 중심, `retrospective/SKILL.md:25-44`). 판단: 코드 확인(없음 확인) / 영향 평가는 `추론`.

### 2.6 호출 제한과 실패 처리

| 대상 | 동작 | 위치 | 검증 |
|---|---|---|---|
| 벤더 봉 실패 | **자동 재시도·백오프 코드 없음**(`bar-service.ts`, `client/typebb/*.ts`, `packages/opentypebb/src` 전체에서 retry/backoff 구현 못 찾음, 검색 키워드: retry, retries, backoff, 429, rate limit, sleep). 대신 **오류를 분류해서 에이전트에게 설명**: Yahoo 429/401/403/crumb → `RateLimitedError`("이것은 데이터 없음이 아니다. 몇 분 뒤 재시도하거나 소스를 바꿔라(fmp 또는 브로커 barId)"), DNS/연결 실패 → `NetworkUnreachableError`. `calculateQuant`에서는 `kind:"data-source"` 오류 + 다음 행동 제안으로 변환 | `packages/opentypebb/src/core/provider/utils/errors.ts:54-93`, `providers/yfinance/utils/helpers.ts:48-78`, `calc-v2/evaluator.ts:201-204`, `tool/quant.ts:76-81` | 코드 확인 |
| 데이터 소스 오류 지침 | "스크립트를 고치지 말고 제안을 따르거나 사용자에게 데이터 불가를 알려라" | `tool/quant.ts:76-81` | 코드 확인 |
| 브로커 일부 불능 | 계정별 `settlePerAccount`로 격리하고 `degraded`/`connecting` 마커로 노출, "어느 소스가 degraded인지 반드시 사용자에게 알려라" | `tool/trading.ts:411-426`, `:445-459` | 코드 확인 |
| 보드 일부 실패 | `Promise.allSettled`로 개별 리스트 실패는 빈 배열, 캘린더는 3개 모두 실패해야 오류, 부분 실패는 `errors{}`에 기록 | `reference/service.ts:63-84`, `:96-127` | 코드 확인 |
| RSS | 피드 1회 재시도(2초 뒤), 타임아웃 15초. 피드 하나 실패해도 다음 피드 계속, 경고 로그만 | `collector/rss-parser.ts:23-40`, `collector/rss.ts:83-93` | 코드 확인 |
| 심볼 검색 | 한 벤더 실패는 `allSettled`로 격리(다른 벤더 결과 사용) | `bar-service.ts:318-322`, `aggregate-search.ts:106-118` | 코드 확인 |
| hub 비정상 | hub가 다운이거나 비정상 응답이면 조용히 로컬로 폴백, 단 `meta.origin`에 표시 | `reference/hub.ts:48-71` | 코드 확인 |
| 호출 제한(레이트리밋) | Yahoo는 비공식 클라이언트를 IP·요청 지문으로 차단하므로 `RateLimitedError`로 명시(위 행). FMP/FRED 등 키 기반 쿼터를 세는 코드는 없음. OECD "tiny quota"는 6시간 캐시로 완화(주석). 사전 스로틀 없음 | `errors.ts:54-93`, `reference/service.ts:41-43`, `:51` | 코드 확인 |

실패 시 판단 중단 여부: 코드가 판단을 멈추지 않는다. 오류를 도구 결과로 돌려주고 에이전트가 계속할지 정한다(`instruction.md:28-31`의 "Do not fill gaps with plausible facts" 지침이 유일한 방어선) — 검증: 코드 확인(코드는 중단 로직 없음) / 에이전트 동작은 `추론`.
