# TradingAgents-CN — 데이터 인벤토리와 수집 방식 (Q1, Q2)

- 분석 SHA: `51060a7682cf51810b4bc3a704829438d18cd8dc` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1, Q2
- 검증 수준 요약: 코드 확인 63 / 추론 4 / 미확인 2

> 읽는 법. 라이선스 영역 표기: **[A]** = Apache-2.0 영역(`tradingagents/`, `cli/`, `docs/`, `tests/`, 루트 설정), **[S]** = source-available 영역(`app/`, `core/`, `frontend/`), **[?]** = `LICENSE`가 영역을 열거하지 않은 디렉터리(`install/`, `config/`, `prompts/`, `skills/`, `migrations/`). 근거는 `LICENSE:5-19` (코드 확인).
> 이 문서의 "운영 경로"는 v3.0에서 실제로 도는 경로, 즉 `WorkflowEngine` + `v2_stock_analysis` 계열이다. 레거시 `TradingAgentsGraph`는 서비스 코드에서 호출이 막혀 있다(아래 Q1 끝 "정의만 있는 것" 참고).

## Q1. 데이터 인벤토리 {#q1}

### 1-0. 운영 경로에서 분석가가 쓰는 도구 (DB 바인딩이 코드 기본값보다 우선)

도구 목록은 두 곳에서 정해진다. 둘이 다르다.

| 출처 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 코드 기본값 | 에이전트 클래스의 `metadata.default_tools` (예: market = `get_stock_market_data_unified`) | `core/agents/adapters/market_analyst_v2.py:114-116` [S] | 코드 확인 |
| DB 바인딩 | `tool_agent_bindings` 컬렉션. 없을 때만 코드 기본값 사용. 정렬은 `priority` **내림차순** | `core/config/binding_manager.py:105-120` [S] | 코드 확인 |
| 부트스트랩 시드 | 커뮤니티판 첫 기동 시 들어가는 바인딩 82건 | `install/community_bootstrap.json` → `data.tool_agent_bindings` [?] (한 줄 JSON이라 줄번호 대신 키 경로) | 코드 확인 |

부트스트랩 기준 분석가별 활성 바인딩(`data.tool_agent_bindings`, `is_active=true`):

| 에이전트 | 바인딩된 도구 (priority 순) |
|---|---|
| `market_analyst_v2` | `get_stock_market_data_unified`, `mcp_tdx-mcp_get_stock_info` |
| `fundamentals_analyst_v2` | `get_peer_comparison`, `get_cash_flow_statement`, `get_financial_statements`, `get_stock_fundamentals_unified` |
| `news_analyst_v2` | `get_stock_news_details_unified`(190), `get_stock_news_headlines_unified`(200) |
| `social_analyst_v2` | `get_stock_sentiment_unified` |
| `index_analyst_v2` | `get_market_overview`, `get_china_market_overview`, `get_index_data`, `get_north_flow`, `get_margin_trading`, `get_limit_stats`, `get_index_technical`, `get_market_breadth`, `get_market_environment`, `identify_market_cycle` |
| `sector_analyst_v2` | `get_china_market_overview`, `get_sector_data`, `get_peer_comparison`, `get_fund_flow_data` |

- `news_analyst_v2`는 코드에서 `get_stock_news_unified`를 제거하고 headlines/details 2단 도구로 강제 교체한다 (`core/config/binding_manager.py:15-23`, 코드 확인).
- 분석가 `agent_configs`의 `default_tools`에는 `get_weather`, `test_heartbeat` 같은 시험용 도구 이름이 섞여 있다(`install/community_bootstrap.json` → `data.agent_configs[agent_id=news_analyst_v2]`, `[agent_id=sector_analyst_v2]`). 바인딩이 있으면 바인딩이 이기므로 운영에는 영향이 없다고 본다 (추론: `binding_manager.py:105-120`의 "DB 우선" 로직).

### 1-1. 데이터 인벤토리 표

범례: 키 = 외부 API 키 필요 여부. "소비 주체"는 `v2_stock_analysis` 노드 기준.

| 분류 | 데이터 / 필드 | 제공자 | 키 필요 | 소비 주체 | 근거 위치 | 검증 |
|---|---|---|---|---|---|---|
| 가격·거래량 | A주 일봉 OHLCV 365일 요청(실제 기본 조회폭 60일, 아래 Q2) | MongoDB `stock_daily_quotes` 우선 → Tushare/AKShare/BaoStock 폴백 | Tushare 토큰 필요, 나머지 불필요 | market_analyst_v2 (tool call) | `core/tools/implementations/market/stock_market_data.py:278-432` [S], `tradingagents/dataflows/data_source_manager.py:1274-1395` [A] | 코드 확인 |
| 가격·거래량 | 현재가 `current_price` (시스템 변수) | MongoDB `market_quotes`, `trade_date <= effective_data_date`인 최신 1건 | 불필요(DB) | 모든 에이전트의 프롬프트 변수 | `core/api/workflow_api.py:880-906` [S] | 코드 확인 |
| 가격·거래량 | HK/US 일봉 | HK: AKShare/Yahoo, US: 캐시된 US provider | 일부(US는 Finnhub 등) | market_analyst_v2 | `stock_market_data.py:385-411` [S] | 코드 확인 |
| 기술지표 | MA5/10/20/60, RSI6/12/24(중국식 SMA)·RSI14, MACD(12,26,9, 히스토그램 ×2), 볼린저(20, ±2σ) | 코드에서 pandas로 계산 | 불필요 | market_analyst_v2 | `tradingagents/dataflows/data_source_manager.py:795-841` [A] | 코드 확인 |
| 기술지표 | MA 기울기·방향·꺾임(최근 5일 폴리핏, 일변화율 ±0.02% 임계), `MACHINE_READABLE_MA_CONCLUSIONS`, `MACHINE_READABLE_MACD_CONCLUSIONS` 블록 | 코드 계산(LLM에 재계산 금지) | 불필요 | market_analyst_v2 | `data_source_manager.py:854-900`, `:995`, `:1052` [A] | 코드 확인 |
| 펀더멘털 | 회사 개요, 재무제표(최근 4개 분기), PE/PB/PS(TTM), 역사 밸류에이션 분위 | MongoDB `stock_financial_data`·캐시 → Tushare → AKShare | Tushare 토큰 | fundamentals_analyst_v2 (tool call) | `core/tools/implementations/fundamentals/stock_fundamentals.py:110-165`, `:630-790` [S] | 코드 확인 |
| 펀더멘털 | US 기본면 | OpenAI Responses API `web_search_preview` 호출 | OpenAI 키 | fundamentals_analyst_v2(US) | `tradingagents/dataflows/interface.py:1359-1405`, `stock_fundamentals.py:755-756` [A/S] | 코드 확인 |
| 수급·자금흐름 | 북향자금, 신용거래(两融) 잔고, 상하한가 통계, 시장 폭, 시장 환경, 사이클 | Tushare 어댑터(필수), QMT 대체 일부 | Tushare 토큰 | index_analyst_v2 | `core/tools/implementations/market/index_market_tools.py:23-31`, `:483-600` [S] | 코드 확인 |
| 수급·자금흐름 | 섹터 자금흐름, 동종 비교, 업종 상위 기업, 同花顺 섹터 지수·구성종목 | Tushare 어댑터 | Tushare 토큰 | sector_analyst_v2 | `core/tools/implementations/market/sector_market_tools.py:102-150`, `:389-507` [S] | 코드 확인 |
| 수급·자금흐름 | 칩 분포(보유 원가 분포·수익 비율) | AKShare(동방재부) 또는 Tushare `cyq_perf` | Tushare는 토큰 | chip_distribution_analyst_v2 (연구 매니저가 위임 또는 워크플로 노드) | `core/tools/implementations/market/chip_distribution_tools.py:19-135`, `core/agents/adapters/research_manager_v2.py:172-202` [S] | 코드 확인 |
| 뉴스 | 종목 뉴스 헤드라인 후보 → 선택한 `news_id`의 본문 요점 | MongoDB `stock_news` + AKShare 실시간. HK는 Google News, US는 Finnhub 후보 | AKShare 불필요 / Finnhub 키 | news_analyst_v2 (tool call 2단) | `core/tools/implementations/news/stock_news.py:775-858`, `:1422-1490`, `:1610-1760` [S] | 코드 확인 |
| 감성·소셜 | 사용자 업로드 소셜 메시지(`social_media_messages`, 최근 7일 ≤100건) → 없거나 5건 미만이면 AKShare 뉴스 제목 키워드 계수 | MongoDB + AKShare | 불필요 | social_analyst_v2 (tool call) | `core/tools/implementations/social/stock_sentiment.py:74-100`, `:241-300` [S] | 코드 확인 |
| 감성·소셜 | US: Reddit 감성. 호출은 `from tradingagents.dataflows.interface import get_reddit_sentiment`인데 저장소 어디에도 `def get_reddit_sentiment`가 없다(테스트 2곳이 다른 모듈 `reddit_utils`를 가리킴). ImportError가 `except`로 잡혀 "获取失败" 문자열이 된다 | 사실상 동작하지 않음 | — | social_analyst_v2(US) | `stock_sentiment.py:318-327` [S], `tradingagents/agents/utils/agent_utils.py:1412` [A] | 코드 확인(함수 정의 부재) |
| 거시 | 지수 추세, 시장 개요, 시장 폭, 사이클(대시보드형 도구) | Tushare / QMT | Tushare 토큰 | index_analyst_v2 (결과를 `index_report`로 1시간 캐시) | `core/agents/adapters/index_analyst_v2.py:21-95`, `:172-186` [S] | 코드 확인 |
| 코인 전용 | 없음. 시장 분류 목록에 `crypto`/`futures` 항목만 선언돼 있고(`app/services/config_service.py:231-245`, `tradingagents/constants/data_sources.py:86`) 이를 채우는 provider는 없다. 펀딩비·OI·온체인·공포탐욕 지수 관련 식별자는 `app core tradingagents`의 `*.py` grep에서 0건 | — | — | — | `grep -rli "funding_rate\|open_interest\|fear_greed\|onchain" --include='*.py' app core tradingagents` 결과 없음 | 코드 확인(부재) |
| 포트폴리오·보유 | 보유 종목·거래 기록·계좌 (포지션 분석/거래 복기 워크플로 전용). 종목 분석(`v2_stock_analysis`)에는 `historical_trades` 변수만 trader 프롬프트에 있음 | MongoDB `portfolio`류 | 불필요 | position/trade_review 에이전트, trader_v2 | `core/tools/implementations/trade_review/*.py`, trader 프롬프트 `{historical_trades}` | 코드 확인 |
| 과거 판단·메모리 | 같은 종목 과거 분석 요약(mem0), 승인된 "성장 기억", 반성 교훈 `debate_lesson`·`analysis_lesson`, 어시스턴트 사실 기억 | MongoDB(mem0 호환 저장소, 벡터 어댑터) | LLM/임베딩 키 | bull/bear/risk_manager 일부 (아래 03-decision 4-7) | `app/services/unified_analysis_service.py:1988-2050`, `core/agents/base.py:46`, `:1624-1633` [S] | 코드 확인 |
| 프롬프트 변수 | 회사명, 업종, 통화, 시장명, 유효 데이터 일자 `effective_data_date`, 안정화 노트, 업종·종목별 "분석 차원" 블록 | MongoDB `stock_basic_info`, `analysis_profiles` | 불필요 | 모든 에이전트 | `core/api/workflow_api.py:799-978`, `core/agents/base.py:1603-1612` [S] | 코드 확인 |

### 1-2. 정의만 있고 실제로는 쓰이지 않는 데이터 소스 (호출처까지 확인)

| 항목 | 정의 위치 | 호출 확인 결과 | 검증 |
|---|---|---|---|
| 기술지표 물화 작업(`stock_technical_indicators`) | 설정 `app/core/config.py:278-279`(기본 ON, 평일 18:20), 구현 `app/services/technical_indicator_materialization_service.py:108-123` [S] | `app/main.py`의 스케줄러 등록 목록(`app/main.py:593-977`)에 이 작업이 없고, 서비스 모듈을 import하는 곳은 저장소 전체에서 `technical_factor_bundle_tool.py`가 **읽기만** 한다(`:114`). 쓰는 쪽을 부르는 호출처는 grep 0건 | 코드 확인 |
| `get_stock_news_unified` 도구 | `stock_news.py:1776` [S] | 코드가 `news_analyst_v2`의 바인딩에서 강제 제거(`binding_manager.py:15-23`). 어시스턴트 계획 프롬프트에서는 여전히 추천(`core/agents/planner.py:94`의 "消息面: get_stock_news_unified") | 코드 확인 |
| US 감성 도구의 `get_reddit_sentiment` | `stock_sentiment.py:321` [S] | 정의가 없어 호출 즉시 실패(위 표). 사실상 죽은 경로 | 코드 확인 |
| 레거시 그래프 `TradingAgentsGraph` + `reflect_and_remember` | `tradingagents/graph/trading_graph.py:419`, `:1716` [A] | 서비스 3곳이 `RuntimeError`로 차단(`app/services/simple_analysis_service.py:922-934`, `analysis_service.py:109-121`, `unified_analysis_engine.py:773-796`). `reflect_and_remember` 호출처는 `main.py:26`의 주석뿐 | 코드 확인 |
| `sanitize_analysis_payload` (결정 필드 정규화 + 추천 문구 재작성) | `app/utils/compliance.py:1128-1198` [S] | 호출처가 `tests/test_research_brief_runtime.py`뿐, 운영 코드 호출 0건 | 코드 확인 |
| 부트스트랩 워크플로의 `valuation_analyst_v1` 노드 | `install/community_bootstrap.json` → `data.workflows[id=6ede3bc3-…].edges` | `parallel_analysts -> analyst_1783504388585` 간선만 있고 `merge_analysts`로 가는 간선이 없다. 결과가 합류하지 않는 고아 노드로 보인다 | 추론(간선 목록에 출구가 없다는 사실. LangGraph가 이 분기를 어떻게 처리하는지는 실행 확인 못 함) |

### 1-3. 시장별로 쓰는 데이터가 다른 부분

| 시장 | 가격 | 기본면 | 뉴스 | 감성 | 거시·섹터·수급 | 근거 |
|---|---|---|---|---|---|---|
| A주 | DB 우선 + 신선도 JIT | DB/Tushare/AKShare | DB + AKShare 실시간 | 업로드 소셜 → 뉴스 키워드 | 대시보드형 전용 도구(Tushare/QMT) | `stock_market_data.py:327-383` 외 위 표 |
| HK | AKShare/Yahoo | `get_hk_stock_data_unified` | Google News 후보 | 중문 경로 공유 | 없음 | `stock_market_data.py:385-400`, `stock_news.py:1492-1514` |
| US | 캐시 US provider | OpenAI web_search | Finnhub 후보 | Reddit | 없음 | `stock_market_data.py:402-411`, `stock_fundamentals.py:752-760` |
| ETF | 전용 `etf_daily_quotes` | ETF 분석가 | ETF 전용 프롬프트 | — | — | `unified_analysis_service.py:171-186`, `analysis.py:338` |

## Q2. 수집 방식 {#q2}

### 2-1. 수집 계층, 라우터, 폴백

| 구분 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 우선순위 설정 | MongoDB `system_configs.data_source_configs`(활성 최신 버전) + `datasource_groupings`(시장 분류별). **숫자가 클수록 우선** (`sort(..., reverse=True)`) | `tradingagents/dataflows/data_source_manager.py:110-160` [A], `app/core/data_source_priority.py` `_merge_grouped_enabled_sources` [S] | 코드 확인 |
| 부트스트랩 기본값 | A주 그룹: Tushare 4 > AKShare 3 > local 2 > qmt 1(활성), baostock 1(비활성). US: Alpha Vantage 3 > Yahoo 2 > Finnhub 0. HK: Yahoo 1·AKShare 2·Tushare 3 등 | `install/community_bootstrap.json` → `data.datasource_groupings` [?] | 코드 확인 |
| DB 설정 없을 때 | 기본 순서 `local > AKShare > Tushare > BaoStock` (`default_order`), 어댑터 기본 순서는 `['local','tushare','akshare','baostock']` — 두 기본값이 서로 다르다 | `data_source_manager.py:206-214`, `app/core/data_source_priority.py:12` | 코드 확인 |
| MongoDB 캐시 | `use_app_cache_enabled()`가 켜지면 MongoDB가 현재 소스(최우선). 실패하면 `_try_fallback_sources`가 나머지 소스를 우선순위대로 시도 | `data_source_manager.py:79-103`, `:248-266`, `:1728-1769` | 코드 확인 |
| 폴백 판정 | 결과 문자열에 `❌`나 `错误`가 없으면 성공으로 본다(문자열 휴리스틱) | `data_source_manager.py:1337` | 코드 확인 |

### 2-2. 가져오는 방식 (pre-fetch vs tool call)

| 데이터 | 방식 | 근거 | 검증 |
|---|---|---|---|
| 회사명·업종·현재가·통화·유효 데이터 일자·안정화 노트 | **pre-fetch**: 워크플로 시작 시 DB에서 읽어 프롬프트 변수로 주입 | `core/api/workflow_api.py:1096` (`_prepare_system_variables` 호출), `:799-962` | 코드 확인 |
| 기본면 (A주) | **pre-fetch + tool call 혼합**: 분석가 코드가 `get_stock_fundamentals_unified`, `get_financial_statements(limit=4)`, `get_cash_flow_statement(limit=4)`를 직접 호출해 `HumanMessage`로 먼저 붙이고, 이미 가져온 도구는 LLM의 도구 목록에서 뺀다. LLM에게 남는 도구는 `get_peer_comparison` 등 | `core/agents/adapters/fundamentals_analyst_v2.py:177-191`, `:519-565` | 코드 확인 |
| 가격·지표, 뉴스, 감성, 지수, 섹터 | **tool call**: 분석가 LLM이 `bind_tools`로 도구를 호출. 첫 번째 호출에서 tool_calls가 나오면 도구를 실행하고, **도구 없이** 한 번 더 LLM을 불러 보고서를 쓰게 한다. 도구 호출 반복은 사실상 1라운드 | `core/agents/base.py:729-760`(루프), `:925-936`(도구 실행), `:939`("严格禁止再次调用工具"), `:996`(도구 없는 최종 호출) | 코드 확인 |
| 도구 인자 | 프롬프트가 `ticker, start_date=current_date, end_date=current_date`를 지정. 시작일 확장은 코드가 한다 | 시장 분석 `tool_guidance`(DB 템플릿 `analysts_v2/market_analyst_v2`), `tradingagents/dataflows/interface.py:1553-1564` | 코드 확인 |
| 뉴스 | LLM이 헤드라인 도구로 후보를 보고 → `news_id`를 골라 details 도구로 본문 요점을 받는 2단 tool call | `stock_news.py:1610-1760` | 코드 확인 |
| 반복 상한 | `DEFAULT_MAX_TOOL_ITERATIONS = 3` (`invoke_with_tools` 인자). 에이전트 설정 `max_tool_calls`도 3~4 | `core/agents/base.py:42`, `:670-675`, `install/community_bootstrap.json` → `data.agent_configs[*].max_tool_calls` | 코드 확인 |

README와의 차이: 도구 docstring과 프롬프트는 "시스템이 365일로 확장"이라고 말하지만(`stock_market_data.py:280-303`), 코드는 `MARKET_ANALYST_LOOKBACK_DAYS` 기본 **60일**로 확장한다(`app/core/config.py:326`, `interface.py:1553-1564`). 코드 기준은 60일이다 (코드 확인).

### 2-3. 원시 데이터 가공

- **지표는 전부 코드로 계산**하고 LLM에 재계산을 금지한다. 근거: 도구 출력에 "均线方向结论（工具端确定性计算）"를 넣고(`data_source_manager.py:980-990`, 코드 확인) 프롬프트가 "若工具结果中已包含…不要自行二次计算MA斜率或拐头"라고 지시한다(`core/agents/adapters/market_analyst_v2.py:445`).
  - 원문: "若工具结果中已包含“均线方向结论（工具端确定性计算）”，必须直接引用该结论，不要自行二次计算MA斜率或拐头。"
  - 번역: "도구 결과에 '이동평균 방향 결론(도구 측 결정적 계산)'이 이미 있으면 그대로 인용하고, 직접 MA 기울기나 꺾임을 다시 계산하지 마라."
- 표시는 최근 5거래일만(토큰 절약) `display_rows = min(5, len(data))` (`data_source_manager.py:847`, 코드 확인).
- **사후 정화(코드)**: 시장 분석가는 LLM 출력을 정규식 43개 규칙으로 치환한다. 예: `站稳→高于`, `支撑位→支撑关系`, `突破布林带上轨→高于布林带上轨` (`core/agents/adapters/market_analyst_v2.py:21-65`, `:468-479`). 즉 투자 권유처럼 읽히는 표현을 코드가 문자 단위로 지운다 (코드 확인).
- 결측: 프롬프트가 "工具结果未提供"로 쓰게 하고, 보고서가 비면 `GENERIC_REPORT_FALLBACK = "工具执行或模型生成未完成，当前结论仍待验证。"`로 대체(`core/agents/base.py:21`, `market_analyst_v2.py:231-233`) (코드 확인). 이 문구는 품질 게이트 블랙리스트와 동기화된다(`core/agents/quality_gate.py:25-31`).
- 단위·부호: 통화는 시스템 변수 `currency_name/currency_symbol`로 시장별 주입(`workflow_api.py:925-938`, 코드 확인). 한국어 시장의 부호 규칙(상승=빨강)은 확인하지 못했다(미확인).

### 2-4. 캐시

| 캐시 | 키·만료 | 위치 | 검증 |
|---|---|---|---|
| 시장 데이터 MongoDB 상시 보관 | 별도 만료 없음. 신선도는 아래 JIT로 관리 | `stock_market_data.py:215-262` | 코드 확인 |
| 통합 캐시(Redis → MongoDB → 파일) | 시장·데이터 종류별 TTL, 기본 7200초 | `tradingagents/dataflows/cache/adaptive.py:51-67` [A] | 코드 확인 |
| 시스템 설정 캐시 | `enable_cache: true`, `cache_ttl: 3600`, HK 캐시 86400초 | `install/community_bootstrap.json` → `data.system_configs[0].system_settings` | 코드 확인(시드값) |
| 대시보드형 분석 보고서 | 대시보드(index) 보고서를 `trade_date` 키로 **1시간** 캐시. LLM 산출물 캐시이므로 같은 날 다른 종목 분석이 같은 대시보드 보고서를 공유한다 | `core/agents/adapters/index_analyst_v2.py:21-67`, `:262-278` | 코드 확인 |
| 섹터 보고서 캐시 | 상수에 "已废弃，不再使用"라고 적혀 있으나 읽기·쓰기 코드는 남아 있다. 실제 동작은 미확인 | `core/agents/adapters/sector_analyst_v2.py:21`, `:60-147` | 추론(주석과 코드가 상충) |
| 도구 사용 키 | 인증 키 있는 provider별(Tushare 등) 토큰은 `.env`/DB 설정 | `.env.example:110-116` | 코드 확인 |

### 2-5. 미래 데이터 차단 (look-ahead)

이 시스템은 **백테스트 용도가 아니라 "지금 분석"** 용도이므로 차단 장치가 약하고 일관되지 않다.

| 장치 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 안정화 컷오프 | 중국 시간 19시 이전에는 당일 일봉이 "안정"하지 않다고 보고 분석 일자를 전날로 내림 `effective_data_date`. 요청일이 미래여도 `min(요청일, 안정일)` | `core/tools/trade_date_policy.py:9-28`, `workflow_api.py:841-847` | 코드 확인 |
| 현재가 조회 | `market_quotes`에서 `trade_date <= effective_data_date` | `workflow_api.py:897-906` | 코드 확인 |
| 같은 로직의 중복 구현 | `UnifiedAnalysisService._prepare_system_variables`는 위 조건 없이 "가장 최신 `trade_date`"를 읽는다. 운영 경로(WorkflowAPI)와 다름 | `app/services/unified_analysis_service.py:135-200` | 코드 확인 |
| 가격 도구 | 실제 데이터 일자 ≠ 요청 일자면 도구 출력에 "实际数据日期"와 "日期说明"을 명시 | `stock_market_data.py:42-87`, `:370-379` | 코드 확인 |
| 뉴스 | 분석일 기준 앞 7일 창(`A_SHARE_NEWS_LOOKBACK_DAYS = 7`), 상한 = 분석일 23:59 | `stock_news.py:25`, `:188-197` | 코드 확인 |
| 감성(소셜) | 창의 끝이 분석일이 아니라 `datetime.utcnow()`. 과거 일자 분석에서는 미래 데이터가 섞일 수 있다 | `stock_sentiment.py:84-91` | 코드 확인 |
| 재무 | `_load_recent_financial_data`가 최근 4개 분기를 가져오며 공시일 기준 필터를 하지 않는다 | `stock_fundamentals.py:110-165` | 추론(해당 함수에 `as_of` 필터가 없음. 하위 `_get_cached_raw_financial_data` 내부는 열어보지 않음) |

### 2-6. 호출 제한과 실패 처리

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| LLM 재시도 | `max_retries`(기본 3), 지수 백오프 `min(2**n, 10)`초. 재시도 대상 문자열: `choices`, `null value`, `connection`, `timeout`, `rate_limit`, `429`, `502/503/500`, `limit` | `core/agents/base.py:826-903`(루프와 실패 시 예외), `:834`(백오프) | 코드 확인 |
| 도구가 계속 tool_calls를 반환 | 경고 프롬프트를 덧붙여 한 번 더 호출, 그래도 안 되면 실패 문구 | `core/agents/base.py:1057-1168` | 코드 확인 |
| 데이터 신선도(JIT) | `trading_calendar:last_trade_date`(Redis)와 MongoDB 최신 `trade_date`를 비교, DB가 오래됐으면 **별도 스레드에서 최대 120초** 동기화. 실패·타임아웃이어도 "현재 데이터로 계속" | `stock_market_data.py:215-262`, `:148-212`(120초 `:203`) | 코드 확인 |
| 사전 데이터 검증 | `_validate_task_data`는 구현돼 있으나 "功能未完善"이라며 **주석 처리**. 분석 시작 전 데이터 누락 검사는 꺼져 있다 | `app/services/task_analysis_service.py:221-245`, `:2173-2225` | 코드 확인 |
| 분석가 보고서 품질 게이트 | 길이 50자 미만·실패 문구·결론 키워드 없음 검사. critical이면 1회 재시도, 그래도 실패하면 `low_quality`로 표시만 하고 계속 진행. 표시는 연구원 프롬프트에 "质量提示"로 들어간다 | `core/agents/quality_gate.py:42-112`, `core/agents/analyst.py:315-400`, `core/agents/researcher.py:164-170`, `:284-324` | 코드 확인 |
| 노드 실패 | 일부 노드가 실패해도 워크플로는 계속되고 `degraded_nodes`에 기록 | `core/workflow/engine.py:1169-1175` | 코드 확인 |

### 2-7. 라이선스 경계 메모

- 데이터 수집 핵심(`tradingagents/dataflows/*`, 지표 계산 `data_source_manager.py`)은 **[A]** — 아이디어와 코드 모두 재사용 가능(Apache-2.0 조건 준수).
- 도구 래퍼(`core/tools/implementations/*`), 신선도 JIT, 뉴스 점수화, 감성 도구는 **[S]** — 평가·교육 목적만 가능, 수정 후 재배포·상업 이용 금지. 우리 시스템에는 **아이디어만** 가져와야 한다.
- 단, `tradingagents/graph/setup.py:73-76`은 [S] 영역 모듈(`core.agents.analyst_registry`)을 지연 import한다. [A]와 [S]가 섞여 있어 Apache 영역만 떼어 쓸 때 import 실패에 주의 (코드 확인).

## 출처 링크 (SHA 고정)

- 신선도 JIT: https://github.com/hsliuping/TradingAgents-CN/blob/51060a7682cf51810b4bc3a704829438d18cd8dc/core/tools/implementations/market/stock_market_data.py#L215-L262
- 지표 계산: https://github.com/hsliuping/TradingAgents-CN/blob/51060a7682cf51810b4bc3a704829438d18cd8dc/tradingagents/dataflows/data_source_manager.py#L795-L841
