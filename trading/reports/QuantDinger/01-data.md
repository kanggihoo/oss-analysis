# QuantDinger — 데이터 인벤토리와 수집 방식

- 분석 SHA: `ba8cd667acca3e934bbc1cb354922eff413393dc` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1, Q2
- 검증 수준 요약: 코드 확인 66 / 추론 5 / 미확인 1 (본문 표기 건수 기준)

> 경로는 레포 루트 기준이다. 약어: `BE` = `backend_api_python/app`. 예) `BE/services/fast_analysis.py` = `backend_api_python/app/services/fast_analysis.py`.
> 분석 대상 파이프라인은 `POST /fast-analysis/analyze` → `FastAnalysisService.analyze()` 이다(`BE/routes/fast_analysis.py:73-303`, `BE/services/fast_analysis.py:580-1150`). 프론트엔드는 이 레포에 없다.

---

## Q1. 데이터 인벤토리 {#q1}

핵심 사실 먼저: **판단에 쓰이는 모든 입력은 LLM 호출 전에 코드가 미리 가져와(pre-fetch) 한 번에 프롬프트에 넣는다.** `fast_analysis`에는 LLM이 도구를 호출하는 경로가 없다. 도구 호출 루프는 AI 채팅의 `research_agent`에만 있다(04-research.md).

### Q1-1. 판단 입력 표

`키 필요`: 없음 = 무키로 동작, 선택 = 키가 있으면 품질/범위가 늘어남, 필수 = 없으면 그 데이터가 비어 있음.

| 분류 | 데이터 / 필드 | 제공자 (API, 라이브러리) | 키 필요 | 소비 주체 (단계) | 근거 위치 | 검증 |
|---|---|---|---|---|---|---|
| 가격·거래량 | 실시간 시세 `price, change, changePercent, high, low, open, previousClose, source` | `KlineService.get_realtime_price` → 티커 API, 실패 시 1m 봉, 그다음 1D 봉 폴백. 미국주식 티커는 Finnhub→yfinance(`fast_info`/`info`/history) | 선택(Finnhub) | 증거 스냅샷 `quote.*`, 객관 점수의 24h 변동 | `BE/services/market_data_collector.py:338-391`, `BE/services/kline.py:153-308`, `BE/data_sources/us_stock.py:370-399` | 코드 확인 |
| 가격·거래량 | OHLCV 봉 60개 (타임프레임별) | `DataSourceFactory.get_kline`: 미국주식 Yahoo chart→Nasdaq→yfinance→Finnhub(1D만); 암호화폐 네이티브 거래소 REST(binance·bitget·bybit·okx·gate·htx, 기본 binance) | 없음 | 기술지표 계산, 증거 `ohlcv.latest_bar`(마지막 봉 1개만) | `BE/services/market_data_collector.py:393-405`, `BE/data_sources/us_stock.py:477-557`, `BE/data_sources/native_crypto.py:12`, `BE/config/data_sources.py:313-317` | 코드 확인 |
| 가격·거래량 | 24h 거래대금 `volume_24h`, 봉 거래량 변화 `volume_change_24h`, 회전율 `volume_to_market_cap_pct` | 시세의 `quoteVolume` → 없으면 CoinGecko `coins/markets` | 없음 | 암호화폐 팩터 점수 | `BE/services/market_data_collector.py:1639-1725` | 코드 확인 |
| 기술지표 | RSI(14, Wilder, 15봉 이상) | 자체 계산 | 없음 | 객관 점수, 증거 `indicator.rsi.value` | `BE/services/market/technical_indicators.py:23-31,174-191` | 코드 확인 |
| 기술지표 | MACD(12,26,9; SMA 시드 EMA; 34봉 이상), 골든/데드크로스 | 자체 계산 | 없음 | 객관 점수, 반전 확인 가드 | `BE/services/market/technical_indicators.py:33-62,194-235` | 코드 확인 |
| 기술지표 | MA5/10/20 + 추세 라벨(`strong_uptrend`~`strong_downtrend`) | 자체 계산 | 없음 | 객관 점수, 가드, 레짐 판정 | `BE/services/market/technical_indicators.py:64-83` | 코드 확인 |
| 기술지표 | 볼린저(20, 2σ), ATR(14, Wilder), 변동성 등급(ATR% >5 high, >2 medium) | 자체 계산 | 없음 | 객관 점수(감쇠), 손절/목표 계산 | `BE/services/market/technical_indicators.py:85-135,121-130,266-279` | 코드 확인 |
| 기술지표 | 지지/저항(피벗 S1/R1 + 20봉 고저 + BB의 평균), `trading_levels`(손절=max(현재가-2ATR, 지지×0.99), 목표=min(현재가+3ATR, 저항×1.01)) | 자체 계산 | 없음 | 프롬프트 기준가, 계획 폴백 | `BE/services/market/technical_indicators.py:85-152` | 코드 확인 |
| 기술지표 | `volume_ratio`(직전 20봉 평균 대비), `price_position`(20봉 범위 내 위치 %) | 자체 계산 | 없음 | 객관 점수, 가드 | `BE/services/market/technical_indicators.py:156-168` | 코드 확인 |
| 펀더멘털 | 미국: `pe_ratio, pb_ratio, ps_ratio, market_cap, dividend_yield, beta, 52w_high/low, roe, eps, revenue_growth, profit_margin, debt_to_equity, current_ratio, quick_ratio` + 분기/TTM/연간 재무제표 + 실적 이력 | Finnhub `company_basic_financials`, yfinance `Ticker.info`/재무제표 | 선택(Finnhub) | 객관 점수(최근 분기 우선, TTM 폴백), 증거 `financial.<기간>.*` | `BE/services/market_data_collector.py:971-1060`(전체 1133-1405 중 일부만 정독), `BE/professional_report/snapshot.py:288-336` | 코드 확인(1060행 이후 세부는 미확인) |
| 펀더멘털 | CN/HK: 현재가 필드 + 재무지표/재무제표 | Tencent 시세, TwelveData(키 있을 때), AkShare/Eastmoney, yfinance 보강 | 선택(TwelveData) | 객관 점수 | `BE/services/market_data_collector.py:577-640` | 코드 확인(세부 티어 동작은 일부만) |
| 펀더멘털 | **영속 스냅샷 계층**: 메모리 캐시(30분) → DB `qd_fundamental_snapshots`(24시간 이내면 DB 사용) → 제공자 호출 후 DB에 write-back | PostgreSQL | 없음 | 위 모든 펀더멘털의 저장소 | `BE/services/market_data_collector.py:481-564`, `BE/services/fundamental_data.py:201-308,310-379` | 코드 확인 |
| 펀더멘털(암호화폐) | `name, description, category` — **6개 코인(BTC, ETH, BNB, SOL, XRP, DOGE)은 하드코딩 설명**, 나머지는 "{BASE} 是一种加密货币" | 없음(상수) | 없음 | 증거 스냅샷에 `fundamental` 범주 관측으로 들어감(출처 `unknown`) | `BE/services/market_data_collector.py:1407-1452`, `BE/professional_report/snapshot.py:265-283` | 코드 확인 |
| 수급·자금흐름 | 미국: SEC 공시 목록, Form 4 건수(**매수/매도 방향 아님**), 애널리스트 컨센서스, 최근월물 옵션 스냅샷, 공매도 잔고 | SEC EDGAR, Yahoo/yfinance, Nasdaq | 없음(SEC User-Agent만) | 증거 `filings.sec`, `expectations.analyst`, `options.snapshot`, `short_interest.snapshot`, `insider_activity.snapshot` | `BE/data_providers/us_research.py:26,560-614`, `BE/services/market_data_collector.py:195-211` | 코드 확인 |
| 수급·자금흐름 | 홍콩: 보안 프로필, 남향자금 **보유 변화 프록시**(순매수 아님), 애널리스트 기대, HKMA HIBOR | AkShare(Eastmoney), HKMA open API | 없음 | 증거 `security_profile.hk`, `southbound_flow.snapshot`, `expectations.analyst`, `macro.HKMA.*` | `BE/data_providers/hk_research.py:217-267` | 코드 확인 |
| 수급·자금흐름 | A/H 프리미엄, CCASS, 공매도 거래, HKEX 공시 | (소비 코드는 있으나 수집기가 채우지 않음) | — | 증거 키·프롬프트 규칙·피처 모듈은 존재 | 정의: `BE/professional_report/snapshot.py:338-350`, 초기값 빈 dict: `BE/services/market_data_collector.py:153-163`, 채우는 코드는 grep상 없음 | 코드 확인(grep: 수집기 외 채우는 곳 없음) |
| 뉴스 | 헤드라인·요약(300자)·`sentiment`·출처·URL. 미국=Finnhub `company_news`(7일), 암호화폐=Finnhub `general_news('crypto')`, 그 외=`general_news('general')`. 5건 미만이면 검색엔진으로 보충. 최대 15건 | Finnhub, 검색(Tavily→SearXNG→GDELT→SerpAPI→AlphaVantage→Google→Bing→DuckDuckGo) | 선택 | 객관 점수(감성), 증거 `news.0~9` | `BE/services/market_data_collector.py:2469-2569`, `BE/services/search.py:730-782,859-888,928-966` | 코드 확인 |
| 뉴스 | 전역 지정학 이벤트 | 검색 `"war conflict breaking news today"` 1개 쿼리 | 선택 | **기본 꺼짐**(`FAST_ANALYSIS_INCLUDE_GLOBAL_NEWS=false`), 켜면 `asset_relevance=background`로 표시 | `BE/services/market_data_collector.py:2545-2554,2613-2682` | 코드 확인 |
| 감성·소셜 | Finnhub reddit/twitter 소셜 감성 | Finnhub `stock_social_sentiment` (무료 모드에서는 건너뜀) | 필수(유료) | **수집만 하고 쓰이지 않음**: 증거 스냅샷·점수·프롬프트에 연결된 코드 없음 | 수집: `BE/services/market_data_collector.py:2527-2539`, 소비처 없음(grep: `BE/services/fast_analysis*.py`, `BE/professional_report/**`) | 코드 확인 |
| 감성·소셜 | 공포탐욕지수(alternative.me) | `fetch_fear_greed_index` | 없음 | `macro.FEAR_GREED`, 암호화폐 매크로 점수 | `BE/data_providers/sentiment.py:12-18`, `BE/services/fast_analysis_scoring.py:703-720` | 코드 확인 |
| 거시 | VIX(`^VIX`), DXY(`DX-Y.NYB`), 미 10년물(`^TNX`)+스프레드 | yfinance | 없음 | 객관 점수 매크로(20% 가중), 증거 `macro.*`, "중대 매크로 이벤트" 판정 | `BE/data_providers/sentiment.py:56-62,126-130,188-192`, `BE/services/market_data_collector.py:2329-2466` | 코드 확인 |
| 코인 전용 | 펀딩비, OI(USD), OI 24h 변화, 롱숏 계정비 | CoinGlass v4(키 있을 때, 집계) → 키 없거나 불완전하면 Gate → OKX → Binance 공개 API 중 **한 거래소 단위로** 선택 | 선택(CoinGlass 유료) | 팩터 점수, 증거 `crypto.*`, 하드게이트 검증 | `BE/services/market_data_collector.py:1541-1564,1727-1838` | 코드 확인 |
| 코인 전용 | 거래소 순유입(CoinGlass), 스테이블코인 순유입(CryptoQuant) | CoinGlass, CryptoQuant | 필수(유료) | 팩터 점수 | `BE/services/market_data_collector.py:2081-2132` | 코드 확인 |
| 코인 전용 | 온체인 지표 | 없음 | — | — | 수집기에 온체인 호출 없음(`BE/services/market_data_collector.py:1454-1512`의 반환 필드 목록에 없음) | 코드 확인 |
| 포트폴리오·보유 | 수동 보유(`qd_manual_positions`): 수량·평단·손익 | PostgreSQL | 없음 | **포트폴리오 모니터에서 표시·보고서용으로만 사용. 분석(LLM 프롬프트)에는 들어가지 않음** | `BE/services/portfolio_monitor.py:217-289`, 분석 호출은 시세 외 인자 없음 `:306-311` | 코드 확인 |
| 과거 판단·메모리 | 같은 종목의 검증된 과거 판단 최대 3건(결정·가격·정답 여부·수익률) | PostgreSQL `qd_analysis_memory` | 없음 | 프롬프트 `HISTORICAL MEMORY` 블록 | `BE/services/fast_analysis.py:319-372`, `BE/services/analysis_memory.py:557-639` | 코드 확인 |
| 과거 판단·메모리 | 오프라인 보정 임계값(`buy_threshold` 등) | PostgreSQL `qd_ai_calibration` | 없음 | 점수→결정 변환 임계값 | `BE/services/ai_calibration.py:37-42,91-130`, `BE/services/fast_analysis_scoring.py:122-148` | 코드 확인 |

### Q1-2. 정의만 있고 쓰이지 않는 것 (grep으로 호출처 확인)

| 대상 | 상태 | 근거 | 검증 |
|---|---|---|---|
| `FastAnalysisService._calculate_indicators` | **죽은 코드.** `self.tools`가 `__init__`에 없고 호출처 없음. 실제 지표는 `MarketDataCollector._calculate_indicators` | 정의 `BE/services/fast_analysis.py:103-237`, `self.tools` 사용 `:113,140`, `__init__` `:39-42` | 코드 확인 |
| `_format_news_summary`, `_format_crypto_factor_prompt`, `_format_earnings_data`, `_format_macro_summary`, `_build_decision_guidance` | **죽은 코드.** 옛 프롬프트 조립 함수. 현재 프롬프트는 `build_professional_analysis_prompt`만 사용. 레포 전체 grep에서 호출처 없음 | 정의 `BE/services/fast_analysis.py:239-315,377-473,1152-1208` | 코드 확인 |
| `_format_financial_statements`, `format_fundamental_metric` | 테스트에서만 호출 | `backend_api_python/tests/test_market_data_financial_periods.py:119,130` | 코드 확인 |
| `data["sentiment"]` (Finnhub 소셜) | 수집만 됨 | 위 감성 행 참고 | 코드 확인 |
| HK `hkex_announcements`, `short_selling`, `ccass`, `ah_premium`, 미국 `finra_public`·`hkex_public` 제공자 | 소비 측만 구현. 카탈로그 `integration_status` 기본값 `"planned"` | `BE/professional_report/providers/catalog.py:49,170-197` | 코드 확인 |
| `crypto_factors.signals`, `summary`, `sources`, `metric_metadata`(일부) | 증거 스냅샷에서 제외되어 **LLM 프롬프트에는 안 들어감**. UI/점수용 | `BE/professional_report/snapshot.py:390-392` | 코드 확인 |
| 경제 캘린더, Adanos 소셜 감성, 이벤트 레이더, 기회 스캐너 | fast_analysis 경로 연결 없음. 글로벌 마켓 페이지/AI 채팅용 | `BE/routes/global_market.py:45-50`, `BE/routes/ai_chat.py:1490-1512` | 코드 확인 |
| 웹소켓 가격 스트림 `market_price_stream` | 전략 실행기(`trading_executor`) 전용. 분석에 사용되지 않음 | `BE/services/shared_market_price_feed.py`, `BE/services/trading_executor.py:882,2013` | 코드 확인 |

### Q1-3. 시장별 차이

| 시장 | 쓰는 데이터 | 전문 보고서(게이트·리스크플랜) 지원 | 근거 | 검증 |
|---|---|---|---|---|
| Crypto | 시세·K선·지표 + 암호화폐 팩터(펀딩/OI/롱숏/순유입/거래대금) + 매크로(VIX·DXY·TNX·FNG) + 뉴스 | 지원 | `BE/services/market_data_collector.py:184-186,264-277`, `BE/professional_report/contracts.py:19` | 코드 확인 |
| USStock | 시세·K선·지표 + 펀더멘털 + 미국 리서치(SEC/옵션/공매도/내부자) + 매크로 + 뉴스 | 지원 | `BE/services/market_data_collector.py:177-183` | 코드 확인 |
| HKStock | 시세·K선·지표 + 펀더멘털 + HK 리서치(남향 프록시, 애널리스트, HIBOR) + 매크로 + 뉴스 | 지원 | `BE/services/market_data_collector.py:182-183` | 코드 확인 |
| CNStock | 시세·K선·지표 + 펀더멘털 + 뉴스. 전문 보고서 계약의 `Market` 리터럴(`USStock/HKStock/Crypto`)에 없음 → 스냅샷 검증 실패로 `professional_report_error`가 되고 **품질 게이트·리스크플랜이 적용되지 않을 가능성** | 비지원(추론) | `BE/professional_report/contracts.py:19,125`, `BE/professional_report/builder.py:60-72,573-578`. 실제 실행으로 재현하지 않음 | 추론(근거: 리터럴 + `_quality()` 폴백 경로가 동일 검증을 호출) |
| Forex / Futures / MOEX | 시세·K선·지표 + 매크로 + 뉴스(핵심 선물에 펀더멘털 없음) | 비지원(추론, CNStock과 동일 사유) | `BE/data_sources/factory.py:190-214`, `BE/services/market_data_collector.py:177-186` | 추론 |
| 한국(KRX)·업비트·키움 | **없음.** `upbit|kiwoom|pykrx|krx|.ks` grep 결과는 KOSPI 지수 심볼(`^KS11`)과 언어 라벨뿐 | — | `BE/data_providers/indices.py:19`, `BE/services/indicator_translator.py:53` | 코드 확인 |

---

## Q2. 수집 방식 {#q2}

### Q2-1. 수집 계층

```
FastAnalysisService._collect_market_data()                 fast_analysis.py:46-76
  └─ MarketDataCollector.collect_all()                     market_data_collector.py:109-315
       ├─ 코어 병렬(ThreadPool 4~5, 마감 15~45초): price, kline(60), [fundamental, company, us/hk_research | crypto_info]
       ├─ 지표 계산(로컬)                                    :260-262
       ├─ 암호화폐 팩터(순차)                                :264-277
       ├─ 매크로(옵션, 10초)                                 :279-288
       └─ 뉴스(옵션, 8초)                                    :290-304
```

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 벤더 추상화 | `DataSourceFactory`는 **시장당 소스 1개**를 고른다(`_create_source`). 시장 간 폴백 체인은 없다. 폴백은 각 소스 내부에 있다(미국 K선 Yahoo→Nasdaq→yfinance→Finnhub, 가격 Finnhub→yfinance→1m→1D) | `BE/data_sources/factory.py:190-214,328-348`, `BE/data_sources/us_stock.py:477-557` | 코드 확인 |
| 우선순위 설정 | 검색 제공자 순서는 `SEARCH_PROVIDER` 또는 애드온 설정 + 고정 순서(`tavily, searxng, gdelt, serpapi, alpha_vantage, google, bing, duckduckgo`). 암호화폐 기본 거래소는 `CRYPTO_PUBLIC_DEFAULT_EXCHANGE`(기본 binance) | `BE/services/search.py:716-721,773-782`, `BE/config/data_sources.py:315-317` | 코드 확인 |
| 파생상품 일관성 | 펀딩비와 OI를 **서로 다른 거래소에서 섞어 채우지 않는다.** CoinGlass 집계가 완전하면 그것, 아니면 Gate→OKX→Binance 중 완전한 한 스냅샷, 모두 불완전하면 채워진 필드 수가 많은 후보 | `BE/services/market_data_collector.py:1805-1838` | 코드 확인 |
| 가져오는 방식 | 전 항목 pre-fetch. 도구 호출 없음. 병렬 수집 후 한 번에 프롬프트 | `BE/services/fast_analysis.py:648-654,849-851` | 코드 확인 |

### Q2-2. 원시 데이터 가공

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 지표 | **전부 코드로 계산.** LLM은 계산하지 않는다. 봉 5개 미만이면 `{}`, RSI는 15봉, MACD는 34봉 미만이면 생략 | `BE/services/market/technical_indicators.py:8-34` | 코드 확인 |
| 단위 | 펀더멘털은 필드별 `unit`·`period_type`·`source` 메타데이터를 붙임. Finnhub 시총은 백만 단위라 ×1e6, D/E는 /100 | `BE/services/market_data_collector.py:984-1031` | 코드 확인 |
| 프롬프트용 정규화 | 관측값(`observations`)마다 `evidence_id = ev_ + sha256(시장,심볼,메트릭,출처,as_of,값)[:20]`. 미래 시각 관측은 제외하고 `future_timestamp_evidence_excluded` 플래그 | `BE/professional_report/snapshot.py:77-84,142-173` | 코드 확인 |
| 결측 | `value`가 None/빈 문자열이면 관측 자체를 만들지 않음. 프롬프트에는 `missing_required_metrics`로 명시 | `BE/professional_report/snapshot.py:159-160`, `BE/professional_report/prompt.py:98-100,167-170` | 코드 확인 |
| 값 길이 | 증거 값은 JSON으로 직렬화해 240자에서 자름(`_json(limit=240)`) | `BE/professional_report/prompt.py:44-46,63` | 코드 확인 |
| 신선도 기본값 | 시장/기술/암호화폐 2일, 매크로 7일, 뉴스 14일, 펀더멘털 180일, 기타 1일 | `BE/professional_report/snapshot.py:174-182` | 코드 확인 |
| as_of 폴백 | `as_of`를 안 주는 관측(시세, 지표, 매크로)은 `retrieved_at`을 as_of로 씀 → **구조상 항상 fresh.** 실제 신선도 검사가 의미 있는 건 OHLCV 마지막 봉, 펀더멘털 `period_end`, 뉴스 `datetime`, HKMA 정도 | `BE/professional_report/snapshot.py:162,229-237,260-263,370-385` | 코드 확인(해석은 추론: 매크로가 6시간 캐시여도 fresh로 표기됨) |

### Q2-3. 캐시

| 대상 | 위치·키 | 만료 | 근거 | 검증 |
|---|---|---|---|---|
| K선 | `CacheManager`(기본 메모리, Redis는 명시적 활성화 시). 키 `kline:{시장}:{거래소}:{마켓타입}:{네이티브ID}:{심볼}:{TF}:{limit}` | TF별 3~60초(1D=30초) | `BE/services/kline.py:55-66,139-142`, `BE/config/database.py:59-74`, `BE/utils/cache.py:1-5` | 코드 확인 |
| 실시간 가격 | 같은 `CacheManager`, 30초(1D 폴백은 300초). 단 수집기는 `force_refresh=True`로 읽기를 우회 | `BE/services/kline.py:187-190,235,303`, `BE/services/market_data_collector.py:343` | 코드 확인 |
| 펀더멘털 | ① 프로세스 메모리 `{시장}:{심볼}` 30분(`AI_FUNDAMENTAL_CACHE_TTL_SEC`) ② DB 스냅샷 24시간(`AI_FUNDAMENTAL_DB_TTL_SEC`, 최소 300초) ③ 제공자 호출 후 DB write-back | 위 두 TTL | `BE/services/market_data_collector.py:435-440,481-564` | 코드 확인 |
| 암호화폐 지표 | 프로세스 내 dict. CoinGlass 90~180초, CryptoQuant 300~600초, CoinGecko 180초 | 각 `_cache_set` 인자 | `BE/services/market_data_collector.py:1525-1539,1693,1738-1788,2089,2109-2113` | 코드 확인 |
| 매크로 | `market_sentiment` 캐시 키를 **읽기만** 함(6시간). 이 키는 글로벌 마켓 페이지 라우트가 채움. 비어 있으면 매 분석마다 yfinance/alternative.me를 라이브 호출하고 쓰기는 안 함 | 6시간 | `BE/services/market_data_collector.py:2349-2353,2400-2459`, `BE/routes/global_market.py:145-154`, `BE/data_providers/__init__.py:65` | 코드 확인 |
| 미국 리서치 | 키 `us_research:{티커}:v3`, 3시간. 하나라도 수집되면 저장 | 10,800초 | `BE/data_providers/us_research.py:26,570-613` | 코드 확인 |
| 홍콩 리서치 | 키 `hk_research:{코드}` | 만료는 쓰기 시 TTL(기본 TTL 테이블 또는 기본값) — 값 미확인 | `BE/data_providers/hk_research.py:226-229`, `BE/data_providers/__init__.py:159-187` | 미확인 |

### Q2-4. 미래 데이터(look-ahead) 차단

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 분석 경로 | `collect_all()`에 기준일(`as_of`) 인자가 **없다.** 분석은 항상 "지금" 기준. 즉 이 파이프라인으로 과거 시점 재분석(백테스트)은 불가 | `BE/services/market_data_collector.py:109-117` | 코드 확인 |
| 관측 시각 방어 | 관측 `as_of`가 수집 시각보다 미래면 버림 | `BE/professional_report/snapshot.py:163-173` | 코드 확인 |
| 펀더멘털 point-in-time | 스냅샷에 `available_at`(공시 가능일)을 저장하고 `available_at <= 기준일`만 조회. 단 분석 경로는 `as_of`를 안 넘겨 오늘 기준 | `BE/services/fundamental_data.py:216-235,328-363`, `BE/services/market_data_collector.py:446-450` | 코드 확인 |
| 전략 AI 평가 | 백테스트에서는 AI를 **호출하지 않고 우회**(`BacktestAIDecisionClient`, `skipped_in_backtest`) | `BE/services/ai_decision.py:48-80` | 코드 확인 |

### Q2-5. 호출 제한·실패 처리

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 코어 수집 마감 | `max(15, min(45, timeout))`초. 초과한 항목은 취소하고 `failed_items`에 기록한 뒤 **계속 진행** | `BE/services/market_data_collector.py:223-258` | 코드 확인 |
| 추가 TF 수집 | 보조 TF는 `timeout=25`(1H는 18). 보조 TF에서 성공한 펀더멘털/회사정보는 1차 데이터로 역채움(`recovery_target`) | `BE/services/fast_analysis.py:78-101,693-700,738-745,761-767` | 코드 확인 |
| 가격 실패 | 시세·지표·K선 종가 순으로 가격을 찾고 전부 실패하면 `error="Failed to fetch current price from all sources"`로 **분석 중단**(결정 없음) | `BE/services/fast_analysis.py:810-846` | 코드 확인 |
| 그 외 실패 | 펀더멘털/매크로/뉴스/암호화폐 팩터 실패는 빈 값으로 두고 판단 계속. 대신 데이터 품질 게이트(coverage<0.6이면 HOLD 강제)가 작동 | `BE/services/market_data_collector.py:264-304`, `BE/professional_report/quality.py:129-140` | 코드 확인 |
| `failed_items` 한계 | 매크로·뉴스 헬퍼가 내부에서 예외를 삼키고 빈 값을 돌려주므로 `failed_items`에 `macro`/`news`가 들어가는 경우는 드묾. 그래서 `quality_multiplier`의 0.85/0.8 감점은 거의 발동하지 않고, 실질 감점은 지표 누락(×0.65)뿐일 가능성 | `BE/services/market_data_collector.py:279-304,2461-2466,2524-2525,2608-2609`, `BE/services/fast_analysis.py:790-801` | 추론(근거: 해당 라인들의 try/except 구조를 읽음. 실행 재현 없음) |
| 재시도·백오프 | Finnhub 호출 간격 제한과 실패 시 지수 백오프(최대 60초) 있음. LLM 단계 재시도는 `call_llm_api`의 폴백 모델 시도 | `BE/data_sources/us_stock.py:321-368`, `BE/services/llm.py:1097-1135` | 코드 확인(`call_llm_api` 내부 재시도 세부는 미확인) |
| 호출 수 | 기본(1D) 분석 1회당 `collect_all` **4회**(1D, 4H, 1W 전망, 1H 전망). 각 호출이 가격·K선(+주식은 펀더멘털/회사/리서치)을 병렬 수집. 펀더멘털/리서치는 캐시로 중복 호출이 줄어듦 | `BE/services/fast_analysis.py:616-646,685-700,736-779` | 코드 확인 |
