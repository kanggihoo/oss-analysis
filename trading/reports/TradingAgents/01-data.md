# TradingAgents — 데이터 인벤토리와 수집 방식

- 분석 SHA: `1394a3f72aa4393e1a98f51b382434c4b4c2d972` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1, Q2
- 검증 수준 요약: 코드 확인 86 / 추론 4 / 미확인 3 (표의 검증 열과 본문 표기를 센 값)

범례: 근거 위치는 레포 루트 기준 `경로:시작줄-끝줄`. 핵심 근거 permalink는 `BASE` = `https://github.com/TauricResearch/TradingAgents/blob/1394a3f72aa4393e1a98f51b382434c4b4c2d972/` 뒤에 경로와 `#L시작-L끝`을 붙인다.

<a id="q1"></a>
## Q1. 데이터 인벤토리: 무엇을 보는가

### Q1-0. 전체 구조 한 줄

- 판단에 들어가는 외부 데이터는 거의 전부 **LLM이 도구를 호출해서 가져오는 방식(tool call)** 이다. 예외는 Sentiment Analyst(미리 가져와 프롬프트에 삽입)와 런 시작 시 종목 신원·포트폴리오·메모리 로그다.
- 도구 12개는 `tradingagents/agents/tools.py:18-291`에 정의되고, 모두 `route_to_vendor()`(`tradingagents/dataflows/router.py:200-297`)를 거친다. 코드 확인.

### Q1-1. 데이터 인벤토리 표

| 분류 | 데이터 / 필드 | 제공자 (API, 라이브러리) | 키 필요 | 소비 주체 (에이전트, 단계) | 근거 위치 | 검증 |
|---|---|---|---|---|---|---|
| 가격·거래량 | OHLCV CSV (Open/High/Low/Close/Volume, 소수 2자리 반올림) | yfinance `Ticker.history` | 불필요 | Market Analyst (도구 `get_stock_data`, tool call) | `tradingagents/dataflows/vendors/yahoo/market.py:18-65`, `tradingagents/agents/tools.py:18-38` | 코드 확인 |
| 가격·거래량 | 5년 일봉 CSV 캐시(지표·스냅샷의 원천) | yfinance `Ticker.history(auto_adjust=True)` | 불필요 | `get_indicators`, `get_verified_market_snapshot` 내부 | `tradingagents/dataflows/vendors/yahoo/ohlcv.py:161-257` | 코드 확인 |
| 가격·거래량 | 대체 벤더 OHLCV | Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED` | `ALPHA_VANTAGE_API_KEY` | 기본값 아님. `data_vendors["core_stock_apis"]`로 선택 시 | `tradingagents/dataflows/router.py:99-102`, `tradingagents/dataflows/vendors/alpha_vantage/common.py:28-35` | 코드 확인(라우팅). 내부 구현은 미정독 → 미확인 |
| 기술지표 | `close_50_sma`, `close_200_sma`, `close_10_ema`, `macd`, `macds`, `macdh`, `rsi`, `boll`, `boll_ub`, `boll_lb`, `atr`, `vwma` (프롬프트가 안내하는 12종) | stockstats `wrap()` 로컬 계산 | 불필요 | Market Analyst (`get_indicators`, 호출 1회당 지표 1개; 쉼표로 여럿 주면 분할) | `tradingagents/agents/analysts/market_analyst.py:22-44`, `tradingagents/agents/tools.py:59-69`, `tradingagents/dataflows/vendors/yahoo/market.py:207-235` | 코드 확인 |
| 기술지표 | 지표 파라미터(RSI 14, 볼린저 20일 2σ, ATR 14, MACD 12/26/9 등) | stockstats 기본값 | - | 위와 동일 | 레포는 파라미터를 넘기지 않고 이름만 넘김(`market.py:223`). 실제 기본값은 stockstats 라이브러리 소관(미설치, 미열람). 프롬프트는 `boll`을 "20 SMA", RSI를 "70/30"으로만 설명(`market_analyst.py:35,38`) | 추론 |
| 기술지표 | `mfi` (벤더는 지원, 프롬프트 목록엔 없음) | stockstats | 불필요 | Market Analyst가 이름을 알아서 부르면 동작 | 지원: `market.py:143-147`, 프롬프트 목록 누락: `market_analyst.py:22-44` | 코드 확인 |
| 기술지표 | 검증 스냅샷: 최신 OHLCV 1행 + 지표 11종 + 최근 종가 표(최대 30행) | stockstats + `load_ohlcv(fill_gaps=False)` | 불필요 | Market Analyst (`get_verified_market_snapshot`, 프롬프트가 보고서 전 호출을 지시) | `tradingagents/dataflows/vendors/yahoo/snapshot.py:23-27,66-127`, `market_analyst.py:48` | 코드 확인 |
| 펀더멘털 | 개요 28개 필드: Name, Sector, Industry, Market Cap, PE(TTM), Forward PE, PEG, P/B, EPS(TTM), Forward EPS, Dividend Yield, Beta, 52주 고저, 50/200일 평균, Revenue(TTM), Gross Profit, EBITDA, Net Income, Profit Margin, Operating Margin, ROE, ROA, Debt to Equity, Current Ratio, Book Value, Free Cash Flow | yfinance `Ticker.info` | 불필요 | Fundamentals Analyst (`get_fundamentals`) | `tradingagents/dataflows/vendors/yahoo/fundamentals.py:23-104` | 코드 확인 |
| 펀더멘털 | 재무제표 3종(대차대조표·현금흐름·손익, 분기/연간 CSV) — 미국 상장사 | SEC EDGAR companyfacts XBRL (as-filed) | 불필요(User-Agent 필수) | Fundamentals Analyst | `tradingagents/dataflows/vendors/sec_edgar.py:36-37,46-73,190-237` | 코드 확인 |
| 펀더멘털 | 재무제표 3종 — 그 외 국가/폴백 | yfinance `quarterly_*`, `balance_sheet`, `cashflow`, `income_stmt` | 불필요 | Fundamentals Analyst | `yahoo/fundamentals.py:107-145` | 코드 확인 |
| 펀더멘털 | SEC 라인 아이템: Total Assets, Current Assets, Cash, Total/Current Liabilities, Stockholders Equity / Revenue, Cost of Revenue, Gross Profit, Operating Income, Net Income, Diluted EPS / Operating·Investing·Financing CF, CapEx | SEC us-gaap 태그 | 불필요 | 위와 동일 | `sec_edgar.py:46-73` | 코드 확인 |
| 펀더멘털 | 내부자 거래 | yfinance `Ticker.insider_transactions` | 불필요 | Fundamentals Analyst (`get_insider_transactions`) | `yahoo/fundamentals.py:148-166`, `tools.py:218-229` | 코드 확인 |
| 수급·자금흐름 | 기관/외국인 수급, 공매도 잔고, 옵션 체인 | **없음** | - | - | `funding|open interest|institutional|short interest|options chain` 등을 `*.py`(tests 제외)에서 grep, 데이터 소스로는 0건(유일한 hit은 프롬프트 문구 "Institutional framing", `sentiment_analyst.py:152`) | 코드 확인(부재) |
| 뉴스 | 종목 뉴스(제목·요약·출처·링크, 기본 최대 20건) | yfinance `Ticker.get_news`, 실패 시 `yf.Search` | 불필요 | News Analyst (`get_news`), Sentiment Analyst(사전 수집) | `yahoo/news.py:57-134`, `default_config.py:141` | 코드 확인 |
| 뉴스 | 글로벌 뉴스(고정 검색어 5개, 기본 10건·7일) | yfinance `yf.Search(...).news` | 불필요 | News Analyst (`get_global_news`) | `default_config.py:142-152`, `yahoo/news.py:137-201` | 코드 확인 |
| 뉴스 | 대체 뉴스 벤더 | Alpha Vantage News | `ALPHA_VANTAGE_API_KEY` | 기본값 아님 | `router.py:129-136` | 코드 확인(라우팅) |
| 감성·소셜 | StockTwits 최근 30건(Bullish/Bearish 태그, 본문 280자 컷) | `api.stocktwits.com/api/2/streams/symbol` | 불필요 | Sentiment Analyst (사전 수집, tool 아님) | `vendors/stocktwits.py:30,74-162`, `sentiment_analyst.py:70-72` | 코드 확인 |
| 감성·소셜 | Reddit 게시글(r/wallstreetbets+stocks+investing, 서브레딧당 5건, 본문 240자 컷. 암호화폐는 CryptoCurrency·CryptoMarkets 등) | Reddit 공개 Atom/RSS 검색 | 불필요 | Sentiment Analyst (사전 수집) | `vendors/reddit.py:68,79-93,248-337`, `sentiment_analyst.py:73-76` | 코드 확인 |
| 감성·소셜 | 게시글 필터링(관련도 `noul`<0.3 제거, 입장 bullish/bearish/neutral/unclear) | TypeSafe Jev API | `TYPESAFE_API_KEY`(선택) | Sentiment Analyst (키 있을 때만) | `agents/post_screen.py:36-61,133-159` | 코드 확인 |
| 감성·소셜 | 감성 구조화 결과 `overall_band`(6단계)/`overall_score`(0-10)/`confidence`/`narrative` | Sentiment Analyst LLM 출력 | - | 이후 모든 토론 에이전트가 텍스트로 소비 | `agents/schemas.py:296-379` | 코드 확인 |
| 거시 | FRED 시계열(별칭 40여 개: fed_funds_rate, 10y_treasury, cpi, core_pce, unemployment, vix, ecb_deposit_rate 등, 최근 40행, 기본 365일) | FRED API | `FRED_API_KEY` | News Analyst (`get_macro_indicators`, LLM이 지표명 선택) | `vendors/fred.py:22-90,167-286` | 코드 확인 |
| 거시 | 예측시장 확률(거래량 상위 6건, 1주 변동) | Polymarket Gamma `public-search` | 불필요 | News Analyst (`get_prediction_markets`, LLM이 topic 작성) | `vendors/polymarket.py:22-28,70-149` | 코드 확인 |
| 코인 전용 | 펀딩비, OI, 온체인, 공포탐욕지수 | **없음** | - | - | 위 grep에서 0건. 코인 처리는 심볼 정규화(`BTC-USD`, 11개 base)·서브레딧 분기·CLI에서 펀더멘털 분석가 제외뿐 | 코드 확인(부재) |
| 코인 전용 | 코인 심볼 매핑/제외 규칙 | 로컬 로직 | - | 전 단계 | `dataflows/symbols.py:43-45,79-100`, `cli/prompts.py:127-136`, `vendors/reddit.py:81-93` | 코드 확인 |
| 포트폴리오·보유 | 현금, 통화, 종목별 수량·평균단가(음수=공매도) | 호출자가 넘긴 JSON/`PortfolioContext` | - | Trader, Aggressive/Conservative/Neutral, Portfolio Manager. Research Manager·분석가·불·베어는 **안 봄** | `portfolio.py:23-64`, `agents/context.py:204-218`, 사용처: `trader/trader.py:33`, `risk_mgmt/*_debator.py:28`, `managers/portfolio_manager.py:28` | 코드 확인 |
| 종목 신원 | 회사명·섹터·산업·거래소(과거 날짜 런은 회사명만) | yfinance `Ticker.info` | 불필요 | 모든 에이전트(공통 `instrument_context`, 런 시작 시 1회 pre-fetch) | `agents/context.py:61-169`, `graph/trading_graph.py:117-128,300-306` | 코드 확인 |
| 과거 판단·메모리 | 같은 종목 과거 결정+성찰 최대 5건, 타 종목 성찰 최대 3건 | 로컬 마크다운 로그 `~/.tradingagents/memory/trading_memory.md` | - | **Portfolio Manager만** | `memory/log.py:93-130`, `managers/portfolio_manager.py:35-40`, `default_config.py:86` | 코드 확인 |

### Q1-2. 정의만 있고 쓰이지 않는(또는 기본 경로에서 쓰이지 않는) 항목

| 항목 | 상태 | 근거 | 검증 |
|---|---|---|---|
| Alpha Vantage 전 계열(OHLCV, 지표, 펀더멘털, 뉴스, 내부자) | 라우터에 등록돼 있으나 기본 `data_vendors`가 모두 다른 벤더라 **옵트인**. 키 없으면 `VendorNotConfiguredError` | `router.py:99-140`, `default_config.py:158-167`, `alpha_vantage/common.py:28-35` | 코드 확인 |
| `mfi` 지표 | 벤더만 지원, 프롬프트 목록에 없어 LLM이 우연히 부를 때만 사용 | `yahoo/market.py:143`, `market_analyst.py:22-44` | 코드 확인 |
| `TraderProposal.entry_price/stop_loss/position_sizing`, `PortfolioDecision.price_target/time_horizon` | 값은 보고서 텍스트로만 렌더되고, 코드 어디에서도 소비하지 않음(주문·한도 계산 없음) | `agents/schemas.py:155-183,253-260`, `memory/log.py:58`(결정 텍스트 통째로 저장) | 코드 확인 |
| `TradingMemoryLog.batch_update_with_outcomes` | 정의만 있고 테스트에서만 호출 | `memory/log.py:203-254`, grep: 비테스트 호출 0건 | 코드 확인 |
| `memory_log_max_entries` | 구현돼 있으나 기본 `None`(회전 꺼짐) | `default_config.py:90`, `memory/log.py:273-308` | 코드 확인 |
| `get_stockstats_indicator` | 일괄 계산 실패 시 폴백으로만 호출 | `yahoo/market.py:183-195` | 코드 확인 |
| 분석가 도구 목록에 없는 데이터: `PortfolioContext.cash`는 Research Manager에 전달되지 않음 | 의도된 설계(연구팀은 보유 현황을 모름) | `agents/schemas.py:120-127`(설명문), `managers/research_manager.py:17-51` | 코드 확인 |

### Q1-3. 시장·자산별 차이

| 구분 | 차이 | 근거 | 검증 |
|---|---|---|---|
| 미국 vs 비미국 재무제표 | 미국 SEC 등록사는 EDGAR(공시일 기준 as-filed), 그 외는 Yahoo로 폴백. 한국(.KS/.KQ)·홍콩·A주 등은 EDGAR 대상 아님(`cik_for`가 None이면 `NoMarketDataError`) | `sec_edgar.py:135-142,190-194`, `default_config.py:163` | 코드 확인 |
| 과거 날짜 런 | Yahoo 개요·재무제표·내부자 거래는 **제공 보류 문구**로 대체(시점 정합성 때문). SEC만 as-filed 제공 | `dataflows/date_window.py:108-170`, `yahoo/fundamentals.py:37-39,110-112,154-156` | 코드 확인 |
| 코인 | 펀더멘털 분석가는 CLI 선택지에서 제외, 서브레딧은 코인 커뮤니티로, StockTwits는 `BTC.X` 형식으로 변환 | `cli/prompts.py:127-136`, `vendors/reddit.py:87-93`, `vendors/stocktwits.py:63-71` | 코드 확인 |
| 지역 벤치마크 | `.KS`→`^KS11`, `.KQ`→`^KQ11` 등 21개 접미사 맵, 기본 SPY | `default_config.py:182-204`, `memory/settlement.py:14-35` | 코드 확인 |

<a id="q2"></a>
## Q2. 수집 방식: 어떻게 가져오는가

### Q2-1. 수집 계층 구조

```text
LLM 도구 호출 (tools.py) ──► route_to_vendor(method, ...)  (router.py:200)
                               ├─ category 조회: TOOLS_CATEGORIES (router.py:45-87)
                               ├─ 벤더 체인 결정: tool_vendors[method] > data_vendors[category] (router.py:160-173)
                               └─ 체인 순차 시도 → 실패 유형별 분기 (router.py:231-259)
```

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 우선순위 설정 위치 | `DEFAULT_CONFIG["data_vendors"]`(카테고리 단위) 와 `["tool_vendors"]`(툴 단위, 우선) | `default_config.py:158-171`, `router.py:160-173` | 코드 확인 |
| 기본 체인 | 가격·지표·뉴스=`yfinance`, 펀더멘털=`sec_edgar,yfinance`, 거시=`fred`, 예측시장=`polymarket` | `default_config.py:158-167` | 코드 확인 |
| 체인 의미 | 설정한 값이 **정확한 체인**이다. 사용자가 고르지 않은 벤더로 몰래 폴백하지 않는다. `"default"`만 모든 벤더 사용. 쉼표로 다중 지정 시 순서대로 폴백 | `router.py:211-225` | 코드 확인 |
| 폴백 트리거 | `VendorUnavailableError`(스로틀·장애)·`VendorNotConfiguredError`(키 없음)·`NoMarketDataError`(빈/오래된 데이터)·기타 예외 모두 **다음 벤더로** | `router.py:235-259` | 코드 확인 |
| 체인 소진 후 | 장애 있으면 `DATA_UNAVAILABLE:` 문자열, 전원 "데이터 없음"이면 `NO_DATA_AVAILABLE:` 문자열(둘 다 "추정·날조 금지" 지시 포함). 핵심 카테고리의 비정형 예외는 `raise`(런 중단), 선택 카테고리(거시·예측시장)는 센티널로 강등 | `router.py:176-197,261-295`, `OPTIONAL_CATEGORIES`: `router.py:94` | 코드 확인 |
| 예외 분류 | 3종 타입 계층(`NoMarketDataError`, `VendorUnavailableError`, `VendorNotConfiguredError`) | `dataflows/errors.py:21-58` | 코드 확인 |
| 한국 벤더 삽입 위치 | `VENDOR_METHODS`에 `"kiwoom"` 등 항목 추가(`router.py:97-149`), `data_vendors` 체인 문자열에 이름 추가(`default_config.py:158-167`), 새 도구·카테고리는 `TOOLS_CATEGORIES`와 분석가 `TOOLS` 튜플(`market_analyst.py:8-12`)도 수정 | 해당 줄 | 추론(구조에서 도출. 실제 삽입은 시도 안 함) |

### Q2-2. 가져오는 방식: pre-fetch vs tool call (데이터별)

| 데이터 | 방식 | 근거 | 검증 |
|---|---|---|---|
| 종목 신원(회사명·섹터) | pre-fetch (런 시작 1회, 실패 시 빈 dict로 계속) | `trading_graph.py:117-128,300-306`, `agents/context.py:61-82` | 코드 확인 |
| 포트폴리오 | pre-render (호출자 제공) | `trading_graph.py:305`, `portfolio.py:37-51` | 코드 확인 |
| 메모리 로그 | 그래프의 `Memory Log` 노드가 분석가와 병렬로 pre-fetch | `graph/setup.py:157-166`, `trading_graph.py:308-335` | 코드 확인 |
| Sentiment 3원천(뉴스·StockTwits·Reddit) | **pre-fetch**, 프롬프트 블록으로 삽입(도구 없음, 환각 도구호출 방지) | `sentiment_analyst.py:1-18,63-76,88-112`, `analyst_execution.py:27-33` | 코드 확인 |
| 가격·지표·검증 스냅샷 | **tool call**(Market Analyst) | `market_analyst.py:8-12`, `tools.py:18-94` | 코드 확인 |
| 펀더멘털·재무제표·내부자 | **tool call**(Fundamentals Analyst) | `fundamentals_analyst.py:14-20` | 코드 확인 |
| 종목 뉴스·글로벌 뉴스·FRED·Polymarket | **tool call**(News Analyst) | `news_analyst.py:13-18` | 코드 확인 |
| 토론·매니저·트레이더 단계 | 새 데이터 수집 **없음**. 앞 단계 산출 텍스트와 `NO_EXTERNAL_TOOLS`("프롬프트에 있는 근거만 사용, 도구·웹검색 금지") | `agents/structured.py:36-39`, `research_manager.py:51`, `trader.py:60` | 코드 확인 |

### Q2-3. 원시 데이터 가공

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 지표 계산 주체 | **코드**(stockstats). LLM은 지표 이름만 고르고 값은 도구가 계산해 돌려줌 | `yahoo/market.py:207-235` | 코드 확인 |
| 결측·휴장일 | 지표 표에서 비거래일은 `"N/A: Not a trading day (weekend or holiday)"`로 표기 | `market.py:171-176` | 코드 확인 |
| 가격 결측 처리 | 지표용 데이터는 종가 없는 행 제거 후 ffill/bfill. **검증 스냅샷은 채우지 않음**(채우면 전일 가격이 오늘 날짜로 인용되므로) | `yahoo/ohlcv.py:82-89,248-251`, `snapshot.py:37-39` | 코드 확인 |
| 날짜·타임존 | 바 단위 로컬 날짜로 정규화(UTC 변환 시 아시아 시장이 하루 밀리는 문제 회피) | `ohlcv.py:42-65` | 코드 확인 |
| 단위·통화 | Yahoo 배당수익률·부채비율은 %, 마진·수익률은 분수임을 라벨에 명시. 영국 펜스(GBp)→GBP 변환 라벨. 보고통화 vs 시세통화 구분 | `yahoo/fundamentals.py:19-20,45-62,74,88-89` | 코드 확인 |
| SEC 단위 | USD 백만 단위 표기, EPS는 USD/shares 그대로. 분기값은 서로 빼서 만들지 않음(4분기 파생 금지) | `sec_edgar.py:220-235`, 주석 `sec_edgar.py:80-83,248-251` | 코드 확인 |
| 심볼 정규화 | `XAUUSD→GC=F`, `BTCUSD→BTC-USD`, `700.HK→0700.HK`, `600519.SH→600519.SS` 등. 한국 6자리 코드(`005930.KS`)는 규칙 없이 그대로 통과 | `dataflows/symbols.py:103-144` | 코드 확인 |
| 환경 날조 방지 | 데이터 없음/장애 시 "추정·날조 금지" 센티널 문자열 반환 | `router.py:176-197` | 코드 확인 |

### Q2-4. 캐시

| 대상 | 위치·키 | 만료 기준 | 근거 | 검증 |
|---|---|---|---|---|
| OHLCV(5년) | `data_cache_dir/{SYMBOL}-YFin-data.csv`, 기본 `~/.tradingagents/cache` | 파일 mtime이 **오늘**일 때만 유효. 오늘 날짜 요청은 추가로 900초 TTL(장중 미확정 봉 방지). 빈 캐시는 미스로 처리 | `ohlcv.py:18-24,146-158,190-224`, `default_config.py:85` | 코드 확인 |
| SEC 티커맵·companyfacts | `data_cache_dir/sec_edgar/*.json` | 24시간 | `sec_edgar.py:41,122-132` | 코드 확인 |
| 종목 신원 | 프로세스 메모리 `lru_cache(256)`, 실패는 캐시 안 함 | 프로세스 수명 | `agents/context.py:85-86` | 코드 확인 |
| `get_stock_data`(OHLCV CSV 출력), 뉴스, 개요, FRED, Polymarket | 캐시 **없음**(매 호출 네트워크). 따라서 같은 런에서 `get_stock_data`(비캐시)와 지표(캐시) 간 시점 불일치 가능성은 있으나 장중 외엔 무시 가능 | `market.py:18-65` 에 캐시 코드 없음 | 코드 확인(캐시 부재), 불일치 영향은 추론 |
| Alpha Vantage | 캐시 여부 | 미열람 | 미확인 |
| LangGraph 체크포인트 | 종목별 SQLite `data_cache_dir/checkpoints/<TICKER>.db`, thread_id = `sha256(ticker:date:signature)[:16]`(옵트인) | 성공 완료 시 삭제 | `graph/checkpointer.py:19-65`, `trading_graph.py:140-165,401-402` | 코드 확인 |

### Q2-5. 미래 데이터 차단(look-ahead 방지)

| 장치 | 동작 | 근거 | 검증 |
|---|---|---|---|
| 미래 날짜 런 거부 | `trade_date`가 오늘보다 미래면 `ValueError` | `trading_graph.py:30-41,183` | 코드 확인 |
| 도구 날짜 클램프 | LLM이 어떤 날짜를 넣어도 `as_of`/`as_of_window`가 `trade_date`(그래프 상태에서 주입) 이하로 강제. 윈도가 전부 미래면 길이 유지한 채 이동 | `dataflows/date_window.py:78-105`, 상태 주입: `tools.py:20-24` | 코드 확인 |
| OHLCV 필터 | 캐시 파일엔 오늘까지 담겨 있어도 `Date <= as_of` 로 잘라냄 | `ohlcv.py:229-230` | 코드 확인 |
| 오래된 프레임 거부 | 최신 행이 요청일보다 10일 넘게 과거면 `NoMarketDataError`(stale) | `ohlcv.py:18,109-143` | 코드 확인 |
| 뉴스·소셜 윈도 | `[start, end+1일)` 반개구간으로 자름. 날짜 없는 항목은 윈도가 "현재"에 닿을 때만 보존. 피드가 최근만 제공하면 "공백"이 아니라 **unavailable** 문구 | `date_window.py:23-31,44-68`, `yahoo/news.py:119-134`, `stocktwits.py:44-55`, `reddit.py:38-48` | 코드 확인 |
| 재무제표 | SEC는 `filed <= as_of`인 사실만, 재공시(수정)는 당시 버전. Yahoo·내부자는 과거 날짜 런에서 보류 | `sec_edgar.py:153-187(특히 176)`, `date_window.py:134-170` | 코드 확인 |
| FRED | 실시간 빈티지를 `as_of`로 고정(개정 전 값). FRED 현재일보다 미래면 Chicago 날짜로 클램프 | `vendors/fred.py:195-204` | 코드 확인 |
| Polymarket | 과거 날짜 런은 제공 보류 | `polymarket.py:86-91` | 코드 확인 |
| 종목 신원 | 과거 날짜 런은 회사명만(현재 이름임을 명시), 섹터·거래소 제외 | `agents/context.py:138-143` | 코드 확인 |
| 메모리 | 과거 날짜 런은 `resolved <= trade_date`인 교훈만 주입 | `memory/log.py:105-107`, `trading_graph.py:130-138` | 코드 확인 |
| **잔여 구멍** | Sentiment(StockTwits·Reddit·Yahoo 뉴스)는 피드가 보관본이 없어 과거 런에서 point-in-time이 **보장되지 않음**. 레포 스스로 인정 | `sentiment_analyst.py:10-13`, `backtest.py:121-125` | 코드 확인 |

### Q2-6. 호출 제한과 실패 처리

| 대상 | 재시도·백오프 | 실패 시 판단 계속 여부 | 근거 | 검증 |
|---|---|---|---|---|
| Yahoo (전 경로) | 429 시 지수 백오프 3회(2→4→8초), 초과하면 `VendorUnavailableError`. 빈 응답이면 호스트 도달성 확인 후 "장애"와 "데이터 없음" 구분 | 센티널 문자열로 **계속** | `yahoo/common.py:17-26,49-76` | 코드 확인 |
| Reddit RSS | 429 시 `Retry-After` 또는 60초(±20% 지터) 1회 재시도. 응답 5MB 상한 | 실패는 `<Reddit unavailable ...; not an absence>` 문구로 **계속** | `reddit.py:137-182,185-226,281-282` | 코드 확인 |
| StockTwits | 재시도 없음, 10초 타임아웃 | `<stocktwits unavailable: ...>`로 계속 | `stocktwits.py:97-106` | 코드 확인 |
| SEC EDGAR | 재시도 없음, 30초 타임아웃. 실패는 `VendorUnavailableError`→다음 벤더 | 계속 | `sec_edgar.py:107-119` | 코드 확인 |
| FRED | 타임아웃 30초. 400은 에러 메시지로 변환. 키 없으면 `FredNotConfiguredError`→선택 카테고리라 센티널 | 계속 | `fred.py:146-164`, `router.py:288-295` | 코드 확인 |
| Jev(TypeSafe) | 3회 시도, 429/529·연결오류에 백오프, 16 워커 병렬. 실패 시 **비필터 상태로 통과**(fail-open) + 안내 문구 | 계속 | `post_screen.py:28-34,68-98,162-164` | 코드 확인 |
| LLM 공급자 | `llm_max_retries`로 SDK 재시도 횟수 전달(기본 None=SDK 기본) | 구조화 출력 실패→자유 텍스트 1회 재시도, 그것도 실패하면 예외 전파(런 중단) | `default_config.py:117-120`, `agents/structured.py:59-95` | 코드 확인 |
| 도구 예외 | 도구에서 예외가 나가면 런이 끝난다는 것이 레포의 전제(`tools.py:88` 주석). ToolNode의 기본 예외 처리 동작은 LangGraph 소관 | - | 전제: `tools.py:88`. LangGraph 동작은 미열람 | 미확인 |
| 예외 누수 가능 경로 | Sentiment Analyst는 `get_news.func(...)`를 try 없이 호출한다. 주석은 "예외가 올라오지 않는다"고 하지만(`sentiment_analyst.py:63-65`) 라우터는 핵심 카테고리의 비정형 예외를 `raise`한다(`router.py:288-295`). 다만 Yahoo 경로는 `yf_retry`가 모든 예외를 `VendorUnavailableError`로 바꾸므로(`common.py:73-76`) 기본 설정에서 실제 발생 가능성은 낮다 | - | 예외 경로: 코드 확인, 실제 발생 빈도: 추론 |

### Q2-7. 이 문서에서 확인한 README와 코드의 차이

- `default_config.py:161-163` 주석은 "overview와 insider 도구는 Yahoo"라 쓰지만, 내부자 거래 도구는 `news_data` 카테고리 소속이다(`router.py:67-74`). 따라서 내부자 거래의 벤더는 `data_vendors["news_data"]`로 정해진다. 코드 확인.
- `default_config.py:129-130` 주석은 "내부 에이전트 토론은 영어로 유지"라 하나, 불·베어·리스크 토론 프롬프트에도 `get_language_instruction()`이 붙는다(`researchers/bull_researcher.py:49`, `context.py:14-34`). 코드 확인.
