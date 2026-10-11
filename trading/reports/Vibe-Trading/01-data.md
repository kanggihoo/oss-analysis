# Vibe-Trading — 데이터 인벤토리와 수집 방식

- 분석 SHA: `e532650b527ba3fb146ef00d533f6fc5040d5d2d` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1, Q2
- 검증 수준 요약: 코드 확인 48 / 추론 2 / 미확인 2

> 경로는 모두 레포 루트(`repos/Vibe-Trading`) 기준이다. 이 레포는 "데이터를 미리 모아 프롬프트에 주입"하지 않는다. 메인 에이전트의 데이터는 **LLM이 도구를 호출해서(tool call)** 가져온다. 예외는 swarm 시작 시의 OHLCV 사전 조회 하나뿐이다.

<a id="q1"></a>
## Q1. 데이터 인벤토리

### 1-1. 판단에 들어가는 데이터 (분류별)

| 분류 | 데이터 / 필드 | 제공자 | 키 필요 | 소비 주체 | 근거 위치 | 검증 |
|---|---|---|---|---|---|---|
| 가격·거래량 | OHLCV (일봉 기본, 분봉 지원 loader별 상이), 기본 `max_rows=250` | `get_market_data` → loader 28종(아래 1-2) | 소스별(tushare·finnhub·alphavantage·tiingo·fmp·qveris는 키) | 메인 에이전트, swarm 워커, 백테스트 엔진 | `agent/src/tools/market_data_tool.py:79-150`, `agent/src/market_data.py:14`, `agent/backtest/loaders/registry.py:36-66` | 코드 확인 |
| 가격·거래량 | swarm 사전 조회: 최근 30일 OHLCV, 표에는 마지막 5행, 최대 8종목 | 같은 loader 계층 (`resolve_loader(market)`) | 소스별 | swarm 모든 워커의 system prompt "Ground Truth" 블록 | `agent/src/swarm/grounding.py:70-80,160-206`, `agent/src/swarm/runtime.py:813-864` | 코드 확인 |
| 기술지표 | RSI 14(Wilder), MACD 12/26/9, 볼린저 20, SMA 20/50/200, EMA 20, 거래량 SMA20 대비 비율 | 코드 계산 (pandas) | 없음 | 메인 에이전트(`technical_indicators`), swarm(2개 프리셋) | `agent/src/tools/technical_indicator_tool.py:24-31,121-141,158-209` | 코드 확인 |
| 기술지표 | 임의 지표·VaR·MDD·GPD 꼬리·몬테카를로 | LLM이 `bash`로 스크립트 작성 → `src.quantlib.*` 호출 | 없음 | swarm bear/CRO 에이전트 | `agent/src/swarm/presets/investment_committee.yaml:93-99,157-163` | 코드 확인 (스크립트 내용은 LLM이 매번 작성 → 재현성은 프롬프트 의존) |
| 펀더멘털 | PIT 재무 패널(annual/quarterly/ttm), `source`는 `auto`/`sec`뿐 | SEC EDGAR XBRL | 없음 | 메인 에이전트 `get_fundamentals` | `agent/src/tools/get_fundamentals_tool.py:18-20,64-67,165-167`, `agent/backtest/loaders/fundamentals_loader.py:3` | 코드 확인 |
| 펀더멘털 | 재무제표 3종 + 핵심지표: A주(Eastmoney F10), 미국(SEC), 홍콩(Eastmoney) | Eastmoney, SEC | 없음 | 메인, swarm 5개 프리셋 | `agent/src/tools/financial_statements_tool.py:1-24` | 코드 확인 |
| 펀더멘털 | 종목 프로필: key stats, financialData, 추정, 보유자 | Yahoo quoteSummary | 없음 | 메인, swarm 3개 프리셋 | `agent/src/tools/stock_profile_tool.py:1-12,281-284` | 코드 확인 |
| 펀더멘털 | 증권사 리포트 + 컨센서스 EPS (**A주 전용**) | Eastmoney reportapi, THS | 없음 | investment_committee 3개 에이전트 | `agent/src/tools/research_reports_tool.py:1-17` | 코드 확인 |
| 수급 | 주문 규모별 순유입(주력/초대/대/중/소), 일·분 | Eastmoney fflow (A/HK/US) | 없음 | investment_committee | `agent/src/tools/fund_flow_tool.py:1-17` | 코드 확인 |
| 수급 | 북향·남향 자금, 융자융권 잔고, 용호방, 블록딜, 락업 해제, 주주 수 (**A주/중화권 전용**) | Eastmoney datacenter, HKEX | 없음 | 북향 2개 프리셋만. 나머지는 프리셋 미참조(메인 에이전트 자유 호출) | `agent/src/tools/northbound_tool.py:1-12`, `agent/src/tools/southbound_tool.py:1-30`, `agent/src/tools/margin_trading_tool.py:1-12`, `agent/src/tools/dragon_tiger_tool.py:1-14`, `agent/src/tools/block_trades_tool.py:1-14`, `agent/src/tools/lockup_expiry_tool.py:1-14`, `agent/src/tools/shareholder_count_tool.py:1-12` | 코드 확인 |
| 수급 | 13F 기관 보유, ETF 구성종목(미국 N-PORT, A주) | SEC EDGAR | 없음 | 메인 에이전트 (프리셋 미참조) | `agent/src/tools/institutional_holdings_tool.py:1-30`, `agent/src/tools/etf_holdings_tool.py:1-25` | 코드 확인 |
| 뉴스 | 종목·시장 헤드라인: SH/SZ/BJ → Eastmoney, US/HK → Yahoo. **한국(.KS/.KQ)은 미지원** (`unsupported market` 에러) | Eastmoney search-api, Yahoo v1 | 없음 | 메인, swarm(bull/bear 등 2개 프리셋) | `agent/src/tools/stock_news_tool.py:42-43,251-267,356-358` | 코드 확인 |
| 뉴스 | 임의 웹 검색, 웹 페이지 본문 | ddgs(6엔진), Jina Reader, 선택적 Aliyun IQS | 없음(IQS만 키) | 메인 에이전트 | `agent/src/tools/web_search_tool.py:25-30,150-170`, `agent/src/tools/web_reader_tool.py:18-20` | 코드 확인 |
| 감성·소셜 | 텍스트 감성 점수 [-1,1] (사전 기반), 크립토 공포탐욕지수 | 코드 사전, alternative.me | 없음 | 메인, swarm 다수 | `agent/src/tools/sentiment_tool.py:1-9,102` | 코드 확인 |
| 거시 | FRED 시계열 (키 없으면 레지스트리에서 **도구 자체가 빠짐**) | FRED REST | 필요(`FRED_API_KEY`) | 메인(프리셋 미참조) | `agent/src/tools/fred_macro_tool.py:1-17,53` | 코드 확인 |
| 거시 | `macro` 시장 체인: akshare → tushare → local | akshare, tushare | tushare만 키 | loader 경유 | `agent/backtest/loaders/registry.py:240` | 코드 확인 |
| 거시·이벤트 | Polymarket 이벤트 계약 내재확률 | Polymarket Gamma/CLOB | 없음 | 1개 프리셋 | `agent/src/tools/prediction_market_tool.py:1-30,1002` | 코드 확인 |
| 코인 전용 | L2 호가창 깊이 (OKX/Binance 현물) | ccxt | 없음 | 1개 프리셋 | `agent/src/tools/orderbook_depth_tool.py:1-25,285` | 코드 확인 |
| 코인 전용 | 펀딩비 | loader 프레임의 `funding_rate` 컬럼 언급만 확인 | 미확인 | 미확인 | `agent/backtest/loaders/base.py:276` | 추론 (주석에서 `funding_rate` 평균화 언급. 어느 loader가 채우는지 안 열어봄) |
| 코인 전용 | 온체인, OI | 못 찾음 (`skills/defi-yield`, `crypto-derivatives` 문서는 안 읽음) | - | - | - | 미확인 |
| 포트폴리오 | 계좌·보유·주문·체결·호가 조회 | 브로커 커넥터(`trading_*` 도구) | 브로커 키 | 메인 에이전트 | `agent/src/tools/trading_connector_tool.py:236-700` | 코드 확인 |
| 과거 판단·메모리 | 영속 메모리 상위 3건 자동 recall(각 500자) | `~/.vibe-trading/memory` 파일 | 없음 | 메인 에이전트 사용자 메시지에 주입 | `agent/src/agent/context.py:390-400`, `agent/src/memory/persistent.py:20-30` | 코드 확인 |

### 1-2. 시장별 loader 폴백 체인 (코드가 곧 우선순위)

| 시장 | 체인(앞이 우선) | 근거 | 검증 |
|---|---|---|---|
| 한국 `kr_equity` | pykrx → yahoo → yfinance → local | `agent/backtest/loaders/registry.py:220` | 코드 확인 |
| 크립토 `crypto` | okx → binance → ccxt → yfinance → local (**Upbit 없음**) | `agent/backtest/loaders/registry.py:231` | 코드 확인 |
| 미국 | yahoo → stooq → sina → eastmoney → yfinance → tiingo → fmp → finnhub → alphavantage → longbridge → akshare → local | `agent/backtest/loaders/registry.py:191-204` | 코드 확인 |
| A주 | tencent → mootdx → eastmoney → baostock → akshare → tushare → gildata → local | `agent/backtest/loaders/registry.py:179-190` | 코드 확인 |
| 지수·환율·선물 | index: yahoo→yfinance→local, forex: mt5→akshare→yfinance→local, futures: akshare→local | `agent/backtest/loaders/registry.py:238-246` | 코드 확인 |

### 1-3. 한국 시장 데이터 현황 (이 프로젝트의 핵심 관심사)

| 데이터 | 있는가 | 내용 | 근거 | 검증 |
|---|---|---|---|---|
| 일봉 OHLCV | 있음 | pykrx `get_market_ohlcv_by_date(..., adjusted=True)`. 컬럼 시가/고가/저가/종가/거래량을 영문으로 변환, NaN 행 제거. **일봉만**(분봉 요청은 빈 결과). 수정주가는 KRX가 아니라 Naver 기반이라고 코드가 명시 | `agent/backtest/loaders/pykrx_loader.py:1-30,45-56,92-128,146-164,167-193` | 코드 확인 |
| 종목 코드 규칙 | `005930.KS`(코스피), `247540.KQ`(코스닥)를 6자리로 변환 | `agent/backtest/loaders/pykrx_loader.py:66-68`, `agent/src/market_data.py:46-48` | 코드 확인 |
| 투자자별 수급(외인·기관) | **없음** | pykrx loader는 OHLCV만 호출. 한국 수급용 도구 없음(수급 도구는 전부 Eastmoney A주·HK·US). 찾아본 곳: `agent/src/tools/*flow*`, `*northbound*`, `grep -rIl pykrx` 결과 loader·엔진·테스트뿐 | `agent/backtest/loaders/pykrx_loader.py:158-163` | 코드 확인 (없음) |
| 펀더멘털(DART 등) | **없음** | `get_fundamentals`는 `auto/sec`만. `grep -rIil "opendart\|open dart\|kiwoom"` 결과 0건 | `agent/src/tools/get_fundamentals_tool.py:20` | 코드 확인 (없음) |
| 한국 뉴스 | **없음** | `unsupported market` 분기. Yahoo `search_news`는 .KS를 라우팅하지 않음 | `agent/src/tools/stock_news_tool.py:356-358` | 코드 확인 (없음) |
| Upbit 시세·캔들 | 커넥터 경유로만 있음 | 티커 `/ticker`, 캔들 `/candles/{minutes/N,days,weeks,months}` (1회 최대 200개), 인증 불필요. 백테스트 loader 체인에는 없음 | `agent/src/trading/connectors/upbit/sdk.py:296-371` | 코드 확인 |
| KIS 시세·일봉 | 커넥터 경유로만 있음 | `inquire-price`(TR `FHKST01010100`), `inquire-daily-itemchartprice`(TR `FHKST03010100`, 일·주·월). 저자가 KIS 계정 없이 작성했다고 파일 머리에 명시 | `agent/src/trading/connectors/kis/sdk.py:16-19,390-465` | 코드 확인 |
| 키움 | **없음** | 키움 관련 코드 0건 | grep 결과 | 코드 확인 (없음) |

### 1-4. 정의만 있고 쓰이지 않는 것 / 쓰임이 제한적인 것

| 항목 | 상태 | 근거 | 검증 |
|---|---|---|---|
| loader `nobitex`, `wallex`, `qveris`, `tickerall` | 어떤 시장 폴백 체인에도 없음. `source=`를 명시할 때만 쓰임(명시 요청이 실패해도 다른 소스로 폴백 금지) | `agent/backtest/loaders/registry.py:155-157` + 체인 표 178-247 | 코드 확인 |
| 도구 `get_sector_info`, `get_block_trades`, `get_southbound_flow`, `get_lockup_expiry`, `get_shareholder_count`, `get_macro_series`, `get_sec_filings`, `get_institutional_holdings` | 30개 swarm 프리셋 어디에도 이름이 없음. 메인 에이전트가 자유 호출해야만 쓰임 | `agent/src/swarm/presets/*.yaml` grep 결과 0건 (도구명은 각 `tools/*.py`의 `name =`) | 코드 확인 |
| 한국 시장에 investment_committee를 돌릴 때 | `get_research_reports`(A주 전용), `get_margin_trading`(A주 전용), `get_fund_flow`(A/HK/US), `get_stock_news`(한국 미지원)가 에러 봉투를 반환 → 한국 종목은 사실상 OHLCV + `get_financial_statements`(한국 미지원) 없이 가격 중심 분석 | `agent/src/swarm/presets/investment_committee.yaml:47-49` + 각 도구 docstring | 추론 (도구별 시장 분기를 docstring과 분기 코드로 확인, 한국 종목 실행은 안 해봄) |

<a id="q2"></a>
## Q2. 수집 방식

### 2-1. 계층 구조와 우선순위

- **벤더 라우터**: `FALLBACK_CHAINS`(시장 → 소스 순서). `resolve_loader(market)`가 체인을 앞에서부터 돌며 `is_available()`이 참인 첫 loader를 쓴다 (`agent/backtest/loaders/registry.py:574-610`). 생성자에서 예외가 나도 다음으로 넘어간다 (같은 함수).
- **우선순위 설정**: 환경변수 `MARKET_DATA_ORDER_<MARKET>`으로 재정렬. 기본 체인의 순열이어야 하며 소스 추가·삭제는 거부하고 기본 순서 유지 (`agent/backtest/loaders/registry.py:462-472,524-571`). 예: `MARKET_DATA_ORDER_KR_EQUITY`.
- **체인 기준**: IP 차단 위험이 낮은 공개 소스를 앞에 두고, 키 필요 소스를 뒤에 둔다 (`registry.py:173-177`의 주석).
- **도구 수준 재시도**: 요청 소스가 실패하면 시장 체인에서 최대 5번까지 다른 소스를 시도 (`agent/src/market_data.py:202-275`).
- **명시 소스는 조용히 강등하지 않음**: `local`/`tickerall`/`fmp`/`nobitex`/`wallex`/`qveris`는 사용 불가 시 에러 (`registry.py:155-157,639-660`). 이유 주석: 토만 단위 시계열이 USDT로 오인되는 단위 오류 방지.

### 2-2. pre-fetch vs tool call

| 데이터 | 방식 | 근거 | 검증 |
|---|---|---|---|
| 메인 에이전트의 모든 시장·재무·뉴스 데이터 | **tool call** (LLM이 `get_market_data` 등을 호출). 단, 이름·티커를 먼저 `search_symbol`로 확정하도록 system prompt가 강제 | `agent/src/agent/context.py:170-185` | 코드 확인 |
| swarm 가격 | **pre-fetch**(최근 30일, 종목 ≤8, 표 5행) + 워커의 tool call 병행. 사전 조회 실패는 경고만 남기고 계속 | `agent/src/swarm/runtime.py:813-864`, `agent/src/swarm/grounding.py:70-80` | 코드 확인 |
| 스케줄 리서치 플레이북 | 도구 이름을 적지 않고 "필요한 데이터 능력"만 적음 → LLM이 도구 선택 | `agent/src/scheduled_research/playbooks.py:16-18` | 코드 확인 |
| 포트폴리오·계좌 | tool call (`trading_account` 등) | `agent/src/tools/trading_connector_tool.py:317-350` | 코드 확인 |

### 2-3. 가공, 캐시, look-ahead, 제한과 실패

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 지표 계산 | 정형 지표는 코드(`technical_indicators`). 그 외는 LLM이 쓴 스크립트(swarm)와 `quantlib_call` | `technical_indicator_tool.py:24-31`, `investment_committee.yaml:93-99` | 코드 확인 |
| 결측 처리 | pykrx: `to_numeric` 후 OHLC NaN 행 제거. 거래 정지 시 ffill은 단일 시장 5봉, 다중 시장 10봉 제한 | `pykrx_loader.py:186-192`, `agent/backtest/engines/base.py:285-298` | 코드 확인 |
| 단위·조정주가 표기 | 소스별 조정 방식을 `raw/split/split_dividend/split_dividend_additive`로 라벨링, 혼합 시 경고. 예: pykrx=`split`, tencent·eastmoney(A주)=배당 가산형 | `agent/backtest/loaders/registry.py:260-304,392-446` | 코드 확인 |
| 캐시 | **기본 꺼짐**(`VIBE_TRADING_DATA_CACHE`). 켜면 `source/symbol/timeframe/start/end/fields`가 키. `end_date`가 오늘 이전인 확정 구간만 저장 → 만료(TTL) 개념 없음 | `agent/backtest/loaders/base.py:457-459,475-485,552-564,625-683` | 코드 확인 |
| 미래 데이터 차단(백테스트) | 신호를 1봉 shift한 뒤 다음 봉 시가 체결, 한국 엔진의 상·하한가 판정도 직전 종가 기준 | `agent/backtest/engines/base.py:247,316-334`, `agent/backtest/engines/korea_equity.py:175-194` | 코드 확인 |
| 미래 데이터 차단(재무) | PIT: 공시 가능일 이후에만 값이 보이도록 하는 불변식을 loader 머리에서 선언 | `agent/backtest/loaders/fundamentals_loader.py:3` | 코드 확인 (불변식 선언까지. 구현 본문은 안 읽음) |
| 호출 제한 | 호스트별 throttle(`HostThrottle`), pykrx는 기본 1.0초 간격(`VIBE_TRADING_PYKRX_MIN_INTERVAL`) | `pykrx_loader.py:25-29,57-63,157` | 코드 확인 |
| 실패 처리 | loader 단위: 개별 종목 실패는 결과에서 빠질 뿐 배치를 멈추지 않음. 도구 단위: 에러 봉투 반환. 판단 단위: 프롬프트 원칙 3 "도구가 안 준 것은 채우지 않는다" + 기초 가격 증거가 없으면 grounding 게이트가 거절 | `pykrx_loader.py:129-144`, `context.py:49-55`, `release.py:61` | 코드 확인 |
| 실제 서빙 소스 기록 | pykrx가 없어 yahoo가 대신 응답하면 run card에 **실제 서빙 소스**를 적도록 보정 | `agent/backtest/runner.py:1803-1812` | 코드 확인 |

### 2-4. 한국 연동 평가에 필요한 메모 (짧게)

- pykrx는 **선택 의존성**이다 (`is_available()`이 `import pykrx`만 검사, `pykrx_loader.py:84-90`). 미설치면 한국 데이터는 조용히 yahoo/yfinance로 내려간다 (`registry.py:220`). 그래서 run card에 서빙 소스를 적는 보정이 있다.
- 한국 엔진은 **롱 온리**다. 공매도를 요청하면 생성자에서 거부한다 (`korea_equity.py:157-166`).
