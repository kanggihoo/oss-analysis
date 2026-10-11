# daily_stock_analysis — 데이터 인벤토리와 수집 방식

- 분석 SHA: `ce364e457aab288863a5707e7b3df79786ad07f2` (repos.lock.tsv와 일치해야 함)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1, Q2
- 검증 수준 요약: 코드 확인 65 / 추론 1 / 미확인 0 (실행 확인 0; 본문 내 표기 횟수 기준 근사치)

경로 약어: `analyzer.py`=`src/analyzer.py`, `pipeline.py`=`src/core/pipeline.py`, `base.py`=`data_provider/base.py`, `config.py`=`src/config.py`, `search_service.py`=`src/search_service.py`, `storage.py`=`src/storage.py`, `orchestrator.py`/`runner.py`/`executor.py`/`factory.py`/`protocols.py`=`src/agent/…`, `defaults.py`/`aggregator.py`/`router.py`/`deliberation.py`=`src/agent/skills/…`, `agents/*_agent.py`=`src/agent/agents/…`, `search_tools.py`/`data_tools.py`=`src/agent/tools/…`, `stock_analyzer.py`=`src/stock_analyzer.py`. 그 외는 레포 루트 기준 상대경로를 그대로 적었다.

범례: "레거시 경로"는 `AGENT_MODE=false` 기본 경로(`src/core/pipeline.py:434-999`), "Agent 경로"는 `AGENT_MODE=true` 또는 `AGENT_SKILLS`가 `all`이 아닌 값으로 설정될 때(`pipeline.py:561-571`).

---

## Q1. 데이터 인벤토리 {#q1}

### 1-1. 판단에 들어가는 데이터

| 분류 | 데이터 / 필드 | 제공자 (API, 라이브러리) | 키 필요 | 소비 주체 (에이전트, 단계) | 근거 위치 | 검증 |
|---|---|---|---|---|---|---|
| 가격·거래량 | 일봉 `open/high/low/close/volume/amount/pct_chg` (+`ma5/ma10/ma20`, `volume_ratio`를 코드가 계산해 붙임) | A주: efinance(P0) > akshare(P1) > pytdx(P2) > baostock(P3) > yfinance(P4) > tencent(P5), tushare는 토큰이 있으면 P-1. 한국/일본/대만: yfinance 단일 | 기본 무료. tushare 토큰, tickflow 키는 선택 | 레거시: `_format_prompt` "技术面数据" 표, `StockTrendAnalyzer`. Agent: technical agent 도구 `get_daily_history` | `data_provider/base.py:546-604`, `:1791-1906`, `efinance_fetcher.py:282`, `akshare_fetcher.py:418`, `pytdx_fetcher.py:118`, `baostock_fetcher.py:76`, `yfinance_fetcher.py:77`, `tencent_fetcher.py:33`, `tushare_fetcher.py:216-230`, `tickflow_fetcher.py:88`; 프롬프트 `src/analyzer.py:4448-4462` | 코드 확인 |
| 가격·거래량 | 실시간 시세 `price, change_pct, volume, amount, volume_ratio(量比), turnover_rate, amplitude, open/high/low, pre_close, pe_ratio, pb_ratio, total_mv, circ_mv, change_60d, high_52w, low_52w` + 품질 메타(`fetched_at, provider_timestamp, is_stale, stale_seconds, fallback_from, data_quality, missing_fields`) | A주: `tencent,akshare_sina,efinance,akshare_em` 순(설정 `REALTIME_SOURCE_PRIORITY`). 미국/홍콩: longbridge·yfinance·akshare(홍콩은 futu 포함). 한/일/대: yfinance만 | 무료(기본) | 레거시 프롬프트 "实时行情增强数据"(`analyzer.py:4465-4496`), 칩/컨텍스트팩 | `data_provider/realtime_types.py:111-162`, `src/config.py:1287`, `data_provider/base.py:2424-2700`, `:2483-2494`(한/일/대) | 코드 확인 |
| 기술지표 | MA5/10/20/60(단순이평), MACD 12/26/9, RSI 6/12/24(ewm alpha=1/period), 乖离率 `(price-MA)/MA*100`(MA5/10/20), 5일 평균 대비 거래량비(`vol/mean(직전 5일)`; 0.7 이하 축량, 1.5 이상 방량), 지지(MA5/MA10 ±2% 이내 + MA20) / 저항(최근 20일 고점), 추세 상태 7단계, 종합 `signal_score` 0-100 | 코드 계산(pandas) | 불필요 | LLM 프롬프트에 "系统评分/系统信号"로 들어감(참고값). 가드레일이 지지/저항 값을 사용 | `src/stock_analyzer.py:186-200`(상수), `:265-340`(MA/MACD/RSI), `:341-392`(추세), `:394-409`(乖离), `:411-447`(거래량), `:449-480`(지지/저항), `:585-754`(점수) | 코드 확인 |
| 펀더멘털 | `financial_report`: `report_date, revenue, net_profit_parent, operating_cash_flow, roe` / `dividend`: `ttm_cash_dividend_per_share, ttm_dividend_yield_pct, ttm_event_count` | A주: akshare `stock_financial_abstract` 등(`fundamental_adapter.py:372-470`). 해외(한국 포함): yfinance 어댑터 | 무료 | 레거시 프롬프트 "财报与分红"(`analyzer.py:4497-4612`) | `data_provider/fundamental_adapter.py:372-480`, `data_provider/base.py:4281-4286`(해외 분기), `:3916-4000`(offshore 컨텍스트) | 코드 확인 |
| 펀더멘털 | **(수집만, 레거시 프롬프트 미사용)** `growth`: `revenue_yoy, net_profit_yoy, roe, gross_margin` / `earnings.forecast_summary`(业绩预告) / `earnings.quick_report_summary`(业绩快报) / `institution`: `institution_holding_change, top10_holder_change` | akshare `stock_yjyg_em`, `stock_yjkb_em`, `stock_institute_hold`, `stock_gdfx_top_10_em` | 무료 | 알림 렌더링(`notification.py:2239-2344`), Agent `get_stock_info` 도구(`data_tools.py:142-170`, 모든 블록을 compact로 노출) | `fundamental_adapter.py:372-480`; 레거시 프롬프트에 없음: `analyzer.py:4497-4690` 전체를 읽어 `growth`/`forecast`/`institution(CN)` 참조 없음 확인 | 코드 확인 |
| 수급·자금흐름 | `capital_flow.stock_flow`: `main_net_inflow`(主力净流入 순액), `inflow_5d`, `inflow_10d` / `sector_rankings.top/bottom`(상위·하위 섹터 5개 순유입) | akshare `stock_individual_fund_flow`, `stock_sector_fund_flow_rank`(A주만). 보조: MiaoXiang(MX_APIKEY, 5일/10일 합계 제공), 홍콩은 Futu | 무료(akshare), 키(MiaoXiang) | 레거시 프롬프트 "主力资金流向(操作建议过滤器)"(`analyzer.py:4557-4660`), `stabilize_decision_with_structure` 가드레일(`analyzer.py:1093`) | `fundamental_adapter.py:510-564`(akshare 소스는 `inflow_5d`/`inflow_10d`를 **항상 None**으로 둠: `:536-540`), `miaoxiang_fetcher.py:380-386`, `data_provider/base.py:4619-4700` | 코드 확인 |
| 수급·자금흐름 | **(수집만)** `dragon_tiger`(龙虎榜 20일 플래그) | akshare | 무료 | 레거시 프롬프트에서 미사용. `INDEX_SKIP_MODULES`에 이름 존재(`pipeline.py:127`) | `fundamental_adapter.py:566-`, `base.py:4710-4760` | 코드 확인 |
| 수급·자금흐름 | 대만 3대 법인 `foreign_net, trust_net, dealer_net, total_net` | TWSE T86 + TPEx OpenAPI(`data_provider/tw_institutional_fetcher.py:9-16`, 정부 공개데이터) | 불필요 | 대만 종목만 프롬프트에 주입(`analyzer.py:4629-4690`), 한국에는 해당 블록 없음. 모듈 docstring은 "분석 경로에 연결되지 않음"이라 쓰지만 실제로는 `base.py:4109-4118`에서 호출됨(docstring과 코드 불일치) | `analyzer.py:4629-4690`, `data_provider/base.py:4109-4118`, `tw_institutional_fetcher.py:1-20` | 코드 확인 |
| 수급·자금흐름 | 칩 분포 `profit_ratio, avg_cost, concentration_90/70, cost_90/70_low/high` | akshare, tushare, MiaoXiang(`get_chip_distribution` 구현체 3개) | 무료/토큰 | 레거시 프롬프트 "筹码分布数据"(`analyzer.py:4673-4716`). Actions 워크플로는 기본 `ENABLE_CHIP_DISTRIBUTION=false` | `data_provider/akshare_fetcher.py:1821`, `tushare_fetcher.py:1151`, `miaoxiang_fetcher.py:259`, `realtime_types.py:197-218`, `config.py:1278`, `00-daily-analysis.yml:437` | 코드 확인 |
| 뉴스 | 6~5개 차원 검색 결과 `title/snippet/url/source/published_date` + 관련도 점수/이유 | Bocha, Tavily, Brave, SerpAPI, MiniMax, SearXNG, Anspire | 키 필요(SearXNG 자체호스팅/공개 인스턴스는 키 불필요) | 레거시: 사전 검색 후 "舆情情报" 섹션. Agent: IntelAgent/RiskAgent/단일 에이전트 도구 | `src/search_service.py:2404-2520`(provider 등록 순서), `:4384-4636` | 코드 확인 |
| 뉴스 | 로컬 인텔 풀(RSS: SEC, HKEX, MarketWatch / NewsNow 5종) | 공개 RSS, NewsNow | 불필요 | `refresh_auto_sources`가 켜져 있을 때만(`NEWS_INTEL_AUTO_FETCH_ENABLED` 기본 False) 뉴스 컨텍스트에 최대 6건 추가 | `intelligence_service.py:38-106`, `:307-358`, `config.py:1047`, `pipeline.py:3019-3069` | 코드 확인 |
| 감성·소셜 | Reddit/X/Polymarket 감성 텍스트 | api.adanos.org | `SOCIAL_SENTIMENT_API_KEY` | **미국 티커만**, 뉴스 컨텍스트에 이어 붙임 | `src/services/social_sentiment_service.py:1-12`, `:72-86`, `pipeline.py:737-750` | 코드 확인 |
| 거시 | 대시장 복기: 주요 지수(`^KS11`, `^KQ11` 등), 등락 통계(A주만), 업종/개념 순위(A주만), 시장 뉴스 쿼리, 지수 강약 | akshare/efinance/yfinance 등, 검색엔진 | 무료/키 | `daily_market_context` 요약을 프롬프트에 주입 + 가드레일이 읽음 | `src/market_analyzer.py:552-578`, `:721-778`, `src/core/market_profile.py:83-96`(KR: `has_market_stats=False`), `src/services/daily_market_context.py` | 코드 확인 |
| 거시 | FXMacroData 공개 매크로 도구(지표 이력, 릴리스 캘린더 등) | `fxmacrodata_public` 패키지 | `FXMACRODATA_API_KEY` 선택 | Agent 경로 intel/risk agent 도구 목록 | `src/agent/tools/fxmacrodata_tools.py:1-62`, `src/agent/agents/risk_agent.py:33-46` | 코드 확인 |
| 거시 | 시장 단계 `phase`(premarket/intraday/lunch_break/closing_auction/postmarket/non_trading/unknown), 시장 로컬시각, 마지막 완전 일봉 날짜, 개장/마감까지 분 | `exchange-calendars` | 불필요 | "市场阶段上下文" 프롬프트 섹션 + phase 가드레일 | `src/core/trading_calendar.py:76-124`, `:551-616`, `src/market_phase_prompt.py:44-83` | 코드 확인 |
| 거시 | 시장 구조(활성 테마, 선도 개념/업종, 종목 소속 보드, 리스크 태그) | akshare 보드 데이터 | 무료 | "시장 구조" 프롬프트 섹션(없으면 빈 문자열) | `src/market_structure_prompt.py:13-60`, `pipeline.py:1359-1395` | 코드 확인 |
| 코인 전용 | 펀딩비, OI, 온체인, 공포탐욕지수 | **없음** | - | - | `funding_rate|open_interest|onchain|binance|upbit|fear.?greed|crypto|bitcoin`을 `src data_provider api bot` 전체에서 대소문자 무시 grep: 일치 없음 | 코드 확인 |
| 포트폴리오·보유 현황 | `quantity, avg_cost, total_cost, unrealized_pnl_*, price_stale` 등(`portfolio_context`) | 로컬 DB `portfolio_*` 테이블, Futu 계좌(`--portfolio futu`는 종목 리스트 대체) | Futu OpenD | 레거시 LLM 프롬프트에는 **직접 안 들어감**(`analyzer.py`에 `portfolio` 문자열 없음). 컨텍스트팩 블록과 DecisionSignal `holding_state`에만 사용 | `main.py:619-636`, `analysis_context_builder.py:452-501`, `decision_signal_extractor.py:449-462`, Agent 도구 `data_tools.py:610-650` | 코드 확인 |
| 과거 판단·메모리 | 전일 일봉 대비 `volume_change_ratio`, `price_change_ratio`; 최근 2일만 사용 | SQLite `stock_daily` | - | 레거시 프롬프트 "量价变化"(`analyzer.py:4849-4862`) | `src/storage.py:3483-3540` | 코드 확인 |
| 과거 판단·메모리 | `AgentMemory`(분석 결과·5일/20일 성과·신뢰도 보정) | SQLite | - | **정의만 있고 호출처 없음**. 설정 플래그 `AGENT_MEMORY_ENABLED`(기본 False)만 존재 | `src/agent/memory.py:1-60`, `src/config.py:1081`; `AgentMemory` 호출처는 `src/agent/__init__.py:37-39` 지연 임포트뿐(grep) | 코드 확인 |
| 과거 판단·메모리 | Skill opinion 사후 성과 기반 가중치(0.83~1.2배) | SQLite `skill_opinion_*` | - | specialist 모드의 `SkillAggregator`가 사용(옵션 게이트 `_use_outcome_autoweight`) | `src/services/skill_opinion_weight_service.py:25-35`, `src/agent/skills/aggregator.py:205-240` | 코드 확인 |

### 1-2. 정의만 있고 실제로 쓰이지 않는 것

| 항목 | 정의 위치 | 호출처 확인 결과 | 검증 |
|---|---|---|---|
| `PortfolioAgent` | `src/agent/agents/portfolio_agent.py:1-165` | `src/agent/agents/__init__.py:14,22`에서 export만. `_build_agent_chain`(`orchestrator.py:840-872`)에 없음 | 코드 확인 |
| `AgentMemory` / `calibrate_confidence` | `src/agent/memory.py:216-262` | 호출처 없음(위 표 참조) | 코드 확인 |
| 성장률·실적예고·기관보유·용호방 | `fundamental_adapter.py` | 레거시 프롬프트 미참조. 알림 표시와 Agent `get_stock_info`에서만 소비 | 코드 확인 |
| 백테스트 요약 도구(`get_skill_backtest_summary` 등) | `src/agent/tools/backtest_tools.py:131-261` | 도구 레지스트리에는 등록(`factory.py:359-373`)되어 단일 에이전트가 볼 수 있으나, technical/intel/risk/decision의 `tool_names`에는 없음. 프롬프트가 사용을 지시하는 문장은 못 찾음 | 추론(단일 에이전트 경로에서 LLM이 호출할 가능성은 열려 있으나 지시는 없음) |
| `akshare` 소스의 5일/10일 자금흐름 | `fundamental_adapter.py:536-540` | 값이 항상 `None`이라 프롬프트 표는 `N/A`가 됨(MiaoXiang 보조 소스가 채우는 경우만 값 존재) | 코드 확인 |
| 로컬 인텔 풀 RSS | `intelligence_service.py` | 기본 꺼짐(`news_intel_auto_fetch_enabled=False`) | 코드 확인 |

### 1-3. 시장별 데이터 차이

| 데이터 | A주 | 홍콩 | 미국 | 일본/한국/대만 |
|---|---|---|---|---|
| 일봉 | 6개 소스 폴백 | akshare/tushare/yfinance/longbridge/futu | finnhub>alphavantage>yfinance>longbridge (longbridge 설정 시 선두) | **yfinance만** (`base.py:634-649`) |
| 실시간 시세 | 4개 소스 | 설정 우선순위 `futu,longbridge,akshare,yfinance` | longbridge/yfinance | yfinance만 (`base.py:2483-2494`) |
| 주력 자금흐름 | akshare(+MiaoXiang) | Futu 있을 때만 | 없음(`not_supported`) | 없음(`not_supported`) (`base.py:4057-4075`) |
| 칩 분포 | akshare/tushare/miaoxiang | 없음 | 없음 | 없음 |
| 3대 법인 | - | - | - | 대만만 |
| 소셜 | - | - | adanos(키 필요) | - |
| 용호방·보드 | akshare | Futu 보드(선택) | 없음 | 없음 |

근거: `data_provider/base.py:4627`(`_is_non_cn_request` 또는 ETF면 자금흐름 `not_supported`), `:4057-4075`.

---

## Q2. 수집 방식 {#q2}

### 2-1. 수집 계층 구조

| 구분 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 벤더 추상화 | `BaseFetcher`(ABC)가 `_fetch_raw_data → _normalize_data → _clean_data → _calculate_indicators`를 템플릿으로 강제, 각 벤더가 `priority`를 클래스 속성으로 가짐 | `data_provider/base.py:346-545` | 코드 확인 |
| 라우터 | `DataFetcherManager`가 `priority` 오름차순으로 정렬한 리스트를 순서대로 시도(실패 시 다음). 우선순위는 환경변수(`EFINANCE_PRIORITY` 등)로 조정 | `base.py:619-720`, `:1791-1906`, `:1902` | 코드 확인 |
| 기본 순서 | efinance(0) > akshare(1) > pytdx(2) > baostock(3) > yfinance(4) > tencent(5); tushare 토큰 있으면 -1, tickflow 기본 2, miaoxiang 기본 6, longbridge 5, futu 2, finnhub 2, alphavantage 3 | 각 fetcher의 `priority`(위 표) | 코드 확인 |
| 시장 필터 | 시장별로 지원하지 않는 벤더는 사전에 제외 (`_DAILY_MARKET_FETCHER_SUPPORT`) | `base.py:634-649`, `:794-817` | 코드 확인 |
| 한국 처리 경로 | `normalize_stock_code`가 `005930.KS`를 접미사 형태로 보존 → `_is_kr_market` → 일봉/시세/펀더멘털 모두 yfinance | `base.py:71-153`(보존 규칙 `:139-140`), `:190-192`, `:1973-1980`, `:2483-2494`, `:4281-4286` | 코드 확인 |
| 한국 종목 사용자 입력 | 6자리 숫자 `005930`은 종목 인덱스에 `.KS`가 있으면 매핑, 없으면 A주로 해석 | `docs/market-support.md:15`, `src/services/stock_code_utils.py:56-64` | 코드 확인 |
| 다종목 한/일/대 DB 폴백 | DB에 컨텍스트가 없으면 일봉을 즉시 가져와 저장 | `pipeline.py:1965-1998` | 코드 확인 |

### 2-2. 가져오는 방식 (pre-fetch vs tool call)

| 데이터 | 레거시 경로 | Agent 경로 | 근거 | 검증 |
|---|---|---|---|---|
| 일봉(60일치로 MA/지표) | pre-fetch → DB → 프롬프트 | 도구 `get_daily_history`, `analyze_trend`(LLM이 호출). 단 사전에 DB에 240일치 보장(`_ensure_agent_history`) | `pipeline.py:376-432`, `:1396-1421`, `agents/technical_agent.py:26-35` | 코드 확인 |
| 실시간 시세·칩 | pre-fetch | pre-fetch 후 `initial_context`로 넘김 + 도구로도 호출 가능 | `pipeline.py:518`, `:547`, `:1496-1530` | 코드 확인 |
| 펀더멘털/자금흐름 | pre-fetch(8초 예산) | `initial_context['fundamental_context']`로 주입 + `get_stock_info`, `get_capital_flow` | `pipeline.py:595-610`, `:1505-1511`, `agents/intel_agent.py:25-33` | 코드 확인 |
| 뉴스 | pre-fetch(고정 쿼리 5차원) | **LLM이 도구 호출** | `pipeline.py:683-704`, `agent/tools/search_tools.py:146-256` | 코드 확인 |
| 대시장 복기 | 사전 생성/재사용 후 주입 | 동일 | `main.py:638-696`, `pipeline.py:2047-2087` | 코드 확인 |

### 2-3. 원시 데이터 가공

| 항목 | 방식 | 근거 | 검증 |
|---|---|---|---|
| 지표 계산 | 전부 코드(pandas). LLM은 지표를 계산하지 않고 표로 받음 | `stock_analyzer.py:265-340`, `base.py:576-604` | 코드 확인 |
| 결측/이상 | 일봉은 `close`, `volume` 결측 행 삭제 후 날짜 정렬(`base.py:546-575`). 20행 미만이면 추세 분석 생략하고 "数据不足" 위험 요인만 남김(`stock_analyzer.py:219-222`) | 코드 확인 |
| 단위 | 거래량 "주(股)", 거래대금 "원(元)". 프롬프트에서 万/亿 표기로 변환(`_format_volume/_format_amount`: `analyzer.py:5095-5121`). 한국은 `currency` 메타에 KRW만 표기 | 코드 확인 |
| 이상 거래량 | 전일 대비 10배 초과면 "降权解读" 문구를 프롬프트에 추가 | `analyzer.py:4849-4862` | 코드 확인 |
| 칩 데이터 유효성 | 의미 없는 칩이면 "筹码数据不可用"으로 접고 LLM에 "만들지 말라" 지시 | `analyzer.py:883-960`, `:4673-4716` | 코드 확인 |
| 데이터 부재 | `context['data_missing']`이면 "N/A는 무시하고 뉴스 중심, 기술지표는 데이터 없음이라 쓰고 **절대 조작 금지**" | `analyzer.py:4941-4949` | 코드 확인 |
| 품질 점수 | 컨텍스트팩이 quote/daily_bars/technical/chip/fundamentals/news 블록 상태(`available/missing/stale/fallback/partial/estimated/fetch_failed/not_supported`)로 `overall_score`와 level(≥85 good, ≥70 usable, ≥55 limited, 미만 poor)을 계산 | `analysis_context_builder.py:504-551`, `analysis_context_pack_prompt.py:28-71` | 코드 확인 |
| 지표 입력 스냅샷 | 시세에 장중 반영 후 MA 재계산(`_augment_historical_with_realtime`, Issue #234) | `pipeline.py:644-655`, `:2733-2811` | 코드 확인(함수 호출 확인, 내부는 미열람) |

### 2-4. 캐시

| 캐시 | 키 / 위치 | 만료 | 근거 | 검증 |
|---|---|---|---|---|
| 일봉 | SQLite `stock_daily`(`code`+`date`), 같은 거래일 데이터가 있으면 네트워크 생략(断点续传) | 거래일 기준 | `pipeline.py:376-432`, `src/storage.py:107` | 코드 확인 |
| 실시간 시세 | 메모리 + `realtime_cache_ttl` | 기본 600초(`is_stale` 판단 기준으로도 사용) | `src/config.py:1289`, `base.py:2391-2423` | 코드 확인 |
| 펀더멘털 컨텍스트 | 메모리 dict, 키=`(종목, 예산)`, 최대 256개 | `fundamental_cache_ttl_seconds=120` | `config.py:1303`, `base.py:1578-1615`, `:4295-4310` | 코드 확인 |
| 검색 결과 | 메모리 dict, 키=`쿼리\|max_results\|days`, 동시 요청 병합(in-flight) | 600초 | `search_service.py:2698-2800`, TTL 생성 `:2516` | 코드 확인 |
| 펀더멘털 스냅샷 | `fundamental_snapshot` 테이블 write-only("no read dependency") | - | `pipeline.py:626-637` | 코드 확인 |
| 뉴스 | `news_intel` 테이블(검색 결과 영속) | - | `pipeline.py:717-731`, `storage.py:186` | 코드 확인 |
| 종목명 | 메모리 `_stock_name_cache` | 프로세스 수명 | `base.py:691-692` | 코드 확인 |

### 2-5. 미래 데이터 차단(look-ahead)

| 장치 | 내용 | 한계 | 근거 | 검증 |
|---|---|---|---|---|
| frozen target date | 종목 처리 시작 시 "시장별 마지막 완전 일봉 날짜"를 ContextVar에 고정해 Agent 도구 스레드가 같은 기준일을 읽음 | Agent 도구 경로 중심 | `src/services/history_loader.py:25-45`, `pipeline.py:3334` | 코드 확인 |
| 추세 분석 구간 | `end_date`=frozen 날짜 또는 시장 현재일, 직전 89일 | - | `pipeline.py:640-655` | 코드 확인 |
| 분석 컨텍스트 | `get_analysis_context(code, target_date)`는 `target_date`를 받지만 **무시하고 DB 최신 2행을 사용**한다고 코드 주석이 명시 | 과거 시점 재현(백테스트용 재분석)은 구조적으로 불가 | `src/storage.py:3483-3515` | 코드 확인 |
| 사후 평가 | 평가 전 최소 경과일(`BACKTEST_MIN_AGE_DAYS=14`), 평가창 10거래일, 평가는 분석일 이후 봉만 사용 | 분석은 실시간 전용(재현 불가)이므로 look-ahead 문제가 "분석 시점"에는 없음 | `config.py:1233-1236`, `core/backtest_engine.py:158-215` | 코드 확인 |

### 2-6. 호출 제한과 실패 처리

| 항목 | 동작 | 근거 | 검증 |
|---|---|---|---|
| 서킷브레이커(일봉) | 연속 3회 실패 → 5분 열림 | `base.py:650` | 코드 확인 |
| 서킷브레이커(실시간) | 3회/300초, 반열림 1회 | `realtime_types.py:443-448` | 코드 확인 |
| 서킷브레이커(칩) | 2회/600초(더 보수적) | `realtime_types.py:450-454` | 코드 확인 |
| 펀더멘털 | 단계 예산 8초(`FUNDAMENTAL_STAGE_TIMEOUT_SECONDS_DEFAULT`), 호출당 8초, 재시도 `fundamental_retry_max=1`, 타임아웃 워커 격리(quarantine) | `config.py:185`, `:1297-1301`, `base.py:3381-3487` | 코드 확인 |
| 실패 시 계속 여부 | **계속한다(fail-open)**: 실시간 실패 → 히스토리 종가로 진행(`pipeline.py:516-535`), 칩 실패 → 생략, 펀더멘털 실패 → `failed` 컨텍스트로 진행(`:603-605`), 일봉 실패 → "既有数据로 분석"(`:3352-3354`), 일봉도 없으면 `data_missing=True`로 뉴스 중심 분석(`:763-775`) | 코드 확인 |
| 실패 상태 전달 | 상태값이 `stale/fallback/missing/fetch_failed/partial/estimated`이면 `CORE_DEGRADED_STATUSES`로 분류되어 신뢰도 "高"를 "中"으로 상한(`phase_decision_guardrail.py:159-168`) | 코드 확인 |
| 요청 지터 | Actions 시작 시 0~60초 랜덤 sleep, LLM 요청 직전 `gemini_request_delay`(기본 2.0초, Actions는 `3.0`) | `00-daily-analysis.yml:41-42`, `:106`, `config.py:1002`, `analyzer.py:4027-4032` | 코드 확인 |
| 한국 특이사항 | 한국 일봉/시세가 yfinance 단일이라 폴백이 없다(소스 1개). yfinance 실패 시 일봉 `DataFetchError` 발생 → 기존 DB 데이터가 있으면 그것으로, 없으면 `data_missing` 경로 | `base.py:1989`, `:2183`, `pipeline.py:3352-3354` | 코드 확인 |
