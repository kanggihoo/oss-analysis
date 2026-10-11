# ai-hedge-fund — 데이터 인벤토리와 수집 방식

- 분석 SHA: `78b779c1389e2d1452dc29606d2c4126d859b964` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1, Q2
- 검증 수준 요약: 코드 확인 67 / 추론 4 / 미확인 0

> 범위 메모: 이 SHA의 레포는 v2(`hedge_fund/`)만 담고 있다. `src/`, `app/`(v1)은 존재하지 않는다(`git ls-files`로 해당 경로 파일 0개 확인). 아래는 모두 v2 코드 기준이다.

## Q1. 데이터 인벤토리 {#q1}

판단(LLM 페르소나 5명 + 퀀트 모델 1개)에 실제로 들어가는 데이터는 **단일 공급자 Financial Datasets(FD) API**(`https://api.financialdatasets.ai`, 키 `FINANCIAL_DATASETS_API_KEY`)의 재무지표·실적(earnings)·기업 메타뿐이다. 가격은 판단 입력이 아니라 **사이징/평가용 종가**로만 쓰인다.

### Q1-1. 실제로 쓰이는 데이터

| 분류 | 데이터 / 필드 | 제공자 | 키 필요 | 소비 주체 (에이전트, 단계) | 근거 위치 | 검증 |
|---|---|---|---|---|---|---|
| 가격·거래량 | 일봉 종가(`close`)만 사용. 분석용 mark = 기준일 이전 7일 lookback 중 최신 bar의 close | FD `/prices/` | 예 | `assess_fund` → 사이징 mark, 거래 가능 종목 판별 | `hedge_fund/pipeline/stages.py:173-196` (`_mark_prices`), `stages.py:37` | 코드 확인 |
| 가격·거래량 | 체결·NAV 평가용 정확 종가(해당 세션 bar 필수) | FD `/prices/` | 예 | `execute_decision`, `advance` | `hedge_fund/pipeline/stages.py:103-117` (`exact_marks`) | 코드 확인 |
| 가격·거래량 | 벤치마크(기본 SPY) 종가 = 거래일 그리드 + 벤치마크 NAV | FD `/prices/` | 예 | `advance`, `session_closes`, `backtest_fund` | `hedge_fund/data/sessions.py:21-30`, `hedge_fund/pipeline/session.py:142-146`, `hedge_fund/fund/spec.py:90-93` | 코드 확인 |
| 기술지표 | 없음. 어떤 페르소나 입력에도 RSI/MA가 없다. `QuantModel._compute_rsi`(RSI 14)는 정의만 있고 호출처 없음(Q1-2) | - | - | - | `hedge_fund/signals/base.py:86-97` | 코드 확인 |
| 펀더멘털 | `PeriodFundamentals` 14개 필드: `report_period, filing_date, market_cap, price_to_earnings_ratio, return_on_equity, gross_margin, operating_margin, net_margin, debt_to_equity, current_ratio, revenue_growth, earnings_per_share, book_value_per_share, free_cash_flow_per_share`. `period="ttm"`, 최대 20개(`periods=20`), 최소 4개(`MIN_PERIODS`) | FD `/financial-metrics/` (`filing_date_lte=기준일`) | 예 | LLM 5 페르소나 전원(공통 snapshot) | `hedge_fund/features/snapshot.py:34-50`, `snapshot.py:178-234`, `snapshot.py:27`, `hedge_fund/data/client.py:98-120` | 코드 확인 |
| 펀더멘털(파생) | 코드가 계산해 프롬프트에 넣는 집계: `roe_avg`, `net_margin_avg`, `gross_margin_trend`(최신-최오래), `bvps_cagr`(분기 간격 ttm 가정, years=(n-1)/4), `debt_to_equity_latest`, `market_cap_latest`, `eps_growth_yoy`(t-0 대비 t-4, t-4 EPS<=0이면 None) | 로컬 계산 | - | 5 페르소나 | `hedge_fund/features/snapshot.py:62-75`, `snapshot.py:259-298` | 코드 확인 |
| 펀더멘털(실적) | `EarningsRecord.quarterly.eps_surprise`(`BEAT`/`MISS`), `source_type`(8-K/10-Q/10-K/20-F), `filing_date`, `report_period` | FD `/earnings/` (`limit=8`) | 예 | `PEADModel`만 | `hedge_fund/signals/pead.py:42-58`, `pead.py:103-153`, `hedge_fund/data/client.py:186-201` | 코드 확인 |
| 기업 메타 | `sector`, `industry`만 사용(최신 facts 사용 = PIT 근사로 문서화) | FD `/company/facts/` | 예 | snapshot (`sector`는 blind에서도 유지, `industry`는 blind에서 제거) | `hedge_fund/features/snapshot.py:221-224`, `snapshot.py:139-144` | 코드 확인 |
| 시장 크기 분위 | 시총을 미국 상장주 시총 5분위 단계(최대 95)로 변환. **blind 모드에서만** | Ken French ME Breakpoints CSV(`mba.tuck.dartmouth.edu`) | 아니오 | blind 프롬프트의 `Size:` 줄 | `hedge_fund/features/breakpoints.py:32-36`, `breakpoints.py:77-94`, `snapshot.py:214-216` | 코드 확인 |
| 수급·자금흐름 | 없음 | - | - | - | `hedge_fund/data/protocol.py:33-88`에 해당 메서드 없음 | 코드 확인 |
| 뉴스 | 없음(판단 경로에 미연결, 정의만 존재) | FD `/news/` | 예 | 호출처 없음 | `hedge_fund/data/client.py:126-138` | 코드 확인 |
| 감성·소셜 | 없음 | - | - | - | `hedge_fund/data/protocol.py:33-88`에 메서드 없음 | 코드 확인 |
| 거시 | 없음. Druckenmiller 프롬프트도 "no macro or price-action data"라고 명시 | - | - | - | `hedge_fund/signals/druckenmiller.py:6-8`, `druckenmiller.py:60-61` | 코드 확인 |
| 코인 전용 | 없음 (미국 주식 전용) | - | - | - | `hedge_fund/data/client.py:45` (FD는 주식 API) | 코드 확인 |
| 포트폴리오·보유 현황 | 브로커 장부(`broker.json`: cash, shares)와 ledger에서 재생한 `FundState`(positions, cash, pending decision). **LLM 프롬프트에는 들어가지 않고** 사이징/주문에만 쓰임 | 로컬 파일 | 아니오 | `advance`, `execute_decision`, `build_orders` | `hedge_fund/brokers/paper.py:26-74`, `hedge_fund/pipeline/session.py:64-77`, `session.py:185-198` | 코드 확인 |
| 과거 판단과 메모리 | 이전 판단은 ledger(hash chain)로 보존되지만 **다음 판단의 입력이 되지 않는다.** LLM 프롬프트에 과거 판단·교훈이 없다. 유일한 재사용은 "같은 프롬프트면 캐시된 응답 재사용" | 로컬 파일 | 아니오 | `PromptCache` | `hedge_fund/llm/cache.py:1-48`, `hedge_fund/signals/llm_agent.py:78-80` | 코드 확인 |

핵심 시사점:
- **LLM은 현재가를 보지 못한다.** 프롬프트에 들어가는 시총·P/E는 "가장 최근에 공시된 ttm 행"의 값이다(`snapshot.py:204-207` 주석: `get_market_cap()`은 최신 값이라 lookahead이므로 일부러 피함). `snapshot.render()`의 컬럼 목록에 가격 필드가 없다(`snapshot.py:109-136`). (`코드 확인`. 다만 "밸류에이션이 최대 한 분기쯤 낡을 수 있다"는 해석은 `추론`: ttm 행이 공시 시점에 고정된다는 `snapshot.py:204-206` 주석에 근거)
- **가격은 사이징에만 쓰인다.** 판단(Signal)은 공시 기반 펀더멘털(LLM)·EPS 서프라이즈(PEAD)에서만 나온다.

### Q1-2. 정의만 있고 쓰이지 않는 데이터 소스 (호출처 grep 후 확인)

`hedge_fund/` 전체를 grep한 뒤 해당 파일을 열어 확인했다. 판단 경로(`signals/`, `features/`, `pipeline/`, `portfolio/`, `risk/`)에서 호출되지 않는 항목이다.

| 항목 | 정의 위치 | 판단 경로 호출 | 비고 | 검증 |
|---|---|---|---|---|
| `get_news()` / `CompanyNews` | `hedge_fund/data/protocol.py:62-68`, `data/client.py:126-138`, `data/models.py:138-147` | 없음 | 캐시 래퍼까지 구현(`data/cached.py:73-78`)했으나 소비자 없음 | 코드 확인 |
| `get_insider_trades()` / `InsiderTrade` | `data/protocol.py:70-76`, `data/client.py:144-156`, `data/models.py:113-131` | 없음 | 동일 | 코드 확인 |
| `get_earnings()` (최신 1건) | `data/client.py:174-184` | 없음 | PEAD는 `get_earnings_history()`만 사용(`pead.py:120`) | 코드 확인 |
| `get_market_cap()` | `data/client.py:207-215` | 없음 | `snapshot.py:204-207`이 lookahead 때문에 일부러 배제 | 코드 확인 |
| `Price.volume`, `open/high/low` | `data/models.py:19-29` | 없음(종가만) | 거래량은 어디서도 쓰지 않음 | 코드 확인 |
| `FinancialMetrics`의 나머지 ~40개 필드 (`price_to_book_ratio`, `peg_ratio`, `free_cash_flow_yield`, `interest_coverage`, `quick_ratio`, `earnings_growth`, `payout_ratio` 등) | `data/models.py:36-110` | 없음 | `PeriodFundamentals`는 14개만 `include`(`snapshot.py:210`). 프롬프트에는 14개만 노출 | 코드 확인 |
| `QuantModel._compute_rsi`, `_percentile_rank`, `_sigmoid` | `signals/base.py:57-97` | 없음(PEAD가 쓰지 않음, `pead.py` 전체 확인) | 향후 퀀트용 헬퍼 | 코드 확인 |
| `Filing` 모델(SEC filings) | `data/models.py:262-275` | 없음 | 클라이언트 메서드도 없음 | 코드 확인 |
| `event_study/`, `backtesting/engine.py`(`BacktestEngine`) | `hedge_fund/event_study/`, `hedge_fund/backtesting/engine.py:41` | 펀드 판단 경로에서 호출 없음 | 단일 모델 연구용 별도 하네스. `run.py`/`tui`는 `backtest_fund`만 사용 | 코드 확인 |
| `validation/`(CPCV/PBO) | `hedge_fund/validation/__init__.py:1-5` | - | docstring만 있는 빈 패키지 | 코드 확인 |

시장별 차이: 시장 구분 없음. 미국 주식(FD) 단일. 한국/코인 지원 코드 없음(`추론`: 공급자 하드코딩 `data/client.py:45`, 종목 정규화가 대문자 티커뿐 `fund/spec.py:110-122`).

## Q2. 수집 방식 {#q2}

### 수집 계층 구조

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 추상화 | `DataClient` 구조적 Protocol(`get_prices/get_financial_metrics/get_news/get_insider_trades/get_company_facts/get_earnings/get_earnings_history/get_market_cap`). 상속 불필요 | `hedge_fund/data/protocol.py:33-88` | 코드 확인 |
| 구현체 | `FDClient`(HTTP) 1개 + `CachedDataClient`(디스크 캐시 래퍼). 벤더 라우터/폴백 체인은 **없음** | `data/client.py:36-303`, `data/cached.py:40-174` | 코드 확인 |
| 우선순위 설정 | 없음(단일 공급자). 공급자 교체는 Protocol 구현으로 가능하다고 docstring에 명시 | `data/protocol.py:1-16` | 코드 확인 |
| 조립 위치 | CLI: `CachedDataClient(FDClient())` | `hedge_fund/run.py:196-197`, `run.py:257-258` | 코드 확인 |

### 가져오는 방식 (pre-fetch vs tool call)

- **전부 pre-fetch + 결정적 코드.** LLM은 도구를 호출하지 않는다. `LLMClient.complete(system, user) -> str` 한 번 호출이 전부이고(`hedge_fund/llm/client.py:55-68`), 데이터는 `build_snapshot()`이 먼저 수집해 `render()`한 텍스트로 `user` 프롬프트에 넣는다(`signals/llm_agent.py:65-93`, `features/snapshot.py:87-137`). tool-calling/langchain structured-output을 의도적으로 쓰지 않는다고 명시(`llm/client.py:7-11`). (`코드 확인`)
- 가격: pre-fetch(코드가 mark 계산). PEAD: 코드가 `get_earnings_history` 호출 후 규칙 계산(`pead.py:103-153`).

### 원시 데이터 가공

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 지표 계산 | 집계(평균, 추세, CAGR, YoY)는 코드가 계산하고 LLM은 산술을 하지 않는다("so the LLM reasons over facts instead of re-deriving arithmetic") | `features/snapshot.py:3-7`, `snapshot.py:259-298` | 코드 확인 |
| 결측치 | `None`은 `-`로 표시(`_fmt`), 평균/추세는 None 제외, per-share 지수화는 기준이 None/<=0이면 `-` | `snapshot.py:270-298`, `snapshot.py:247-256` | 코드 확인 |
| 단위 표기 | 절대값 ≥1e9는 `B`, ≥1e6는 `M`, 그 외 소수 2자리 | `snapshot.py:270-277` | 코드 확인 |
| 데이터 부족 | 공시 기간 4개 미만이면 `InsufficientData` → 에이전트가 abstain | `snapshot.py:198-202`, `llm_agent.py:68-69` | 코드 확인 |
| NaN/Inf | 서버 측에서 null로 정리한다고 모델 docstring에 명시. 코드로 직접 검증 불가 | `data/models.py:36-43` | 추론 (docstring 근거) |
| 종가 검증 | 종가가 유한하지 않거나 ≤0이면 `ValueError`(분석용·정확 종가 모두) | `stages.py:188-189`, `stages.py:114-116`, `sessions.py:27-29` | 코드 확인 |
| 거래 불가 종목 | lookback 7일 내 bar가 없으면 `TickerSkip`으로 분석에서만 제외. 체결 단계에서 정확 종가가 없으면 **실행 전체 실패** | `stages.py:190-194`, `stages.py:111-112` | 코드 확인 |

### 캐시

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 위치 | `~/.hedge-fund/cache/data/<sha256[:24]>.json`, LLM은 `~/.hedge-fund/cache/llm/` | `data/cached.py:35-37`, `paths.py:23-28`, `llm/cache.py:22` | 코드 확인 |
| 키 | `sha256(method + JSON(params, sort_keys))[:24]`. `get_financial_metrics`의 params에 `end_date`가 있어 **기준일마다 별도 키** | `data/cached.py:116-118`, `cached.py:66-71` | 코드 확인 |
| 만료 | 일봉 가격만 특수 처리: 캐시 시점(뉴욕 날짜) > `end_date`일 때만 재사용(장중 불완전 봉 방지). 그 외 항목은 **만료 없음**(`refresh=True`로만 무효화) | `data/cached.py:135-156`, `cached.py:120-122` | 코드 확인 |
| 실패 캐싱 | 성공 응답만 캐시, 예외는 그대로 전파 | `data/cached.py:11-14`, `cached.py:150-156` | 코드 확인 |
| 운영 시 주의 | `get_company_facts`/`get_earnings_history`는 TTL이 없어 장기 paper 운영에서 `sector`·EPS 이력이 오래 고정될 수 있다. 근거: `_cached_item`/`_cached_list`에 가격 외 TTL 검사가 없음(`cached.py:135-165`). 단, 키에 `end_date`가 없는 항목이 실제로 오래된 값을 반환하는 것은 실행하지 않아 확인 못 함 | `data/cached.py:94-104`, `cached.py:135-174` | 추론 |
| LLM 캐시 | 키 = `sha256(agent|model|system|user)[:24]`. 응답/파싱 실패/호출 오류 모두 파일로 보존(감사·디버그) | `llm/cache.py:25-48`, `signals/llm_agent.py:78-115` | 코드 확인 |

### 미래 데이터 차단 (look-ahead 방지)

| 장치 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 공시일 기준 필터 | 재무지표는 `filing_date_lte=기준일`로 요청. `report_period`가 아니라 공시일 기준. 공시일을 모르는 행은 서버에서 제외된다고 문서화 | `data/client.py:98-120`, `data/protocol.py:42-43` | 코드 확인(요청 파라미터) / 서버 동작은 추론 |
| 최신 값 배제 | `get_market_cap()`/`company_facts.market_cap`은 최신 값이라 의도적으로 사용하지 않음 | `features/snapshot.py:204-207` | 코드 확인 |
| sector/industry | 최신 값 사용을 "허용된 PIT 근사"로 문서화(누수 가능성 인정) | `features/snapshot.py:221-223` | 코드 확인 |
| PEAD 이벤트 | `filing_date <= 기준일`만 고려, 기준일로부터 4일 초과 시 신호 없음, 보고기간 대비 공시 지연 45일 이상은 폐기(회고성 행) | `signals/pead.py:64-75`, `pead.py:133-136` | 코드 확인 |
| 완료된 일봉만 | `completed_through()` = 뉴욕 오늘-1일(장 마감 후에도 오늘은 제외). 이후 세션 요청은 `ValueError` | `data/sessions.py:12-14`, `stages.py:44-45`, `session.py:132-133` | 코드 확인 |
| 결정 T → 체결 T+1 | 같은 종가로 평가와 체결을 하지 않음 | `pipeline/session.py:11-15`, `stages.py:125-126` | 코드 확인 |
| 시총 분위 PIT | 공시 월 M은 M 이전 마지막 게시 행과만 비교 | `features/breakpoints.py:67-75` | 코드 확인 |
| **blind 모드(LLM 사후 기억 누수 방지)** | 백테스트에서는 티커·산업·달력 날짜·절대 시총·주당 달러값을 숨김. 기간은 t-0, t-1…로 표기, per-share는 가장 오래된 기간=100으로 지수화, 크기는 시총 분위로만 표기 | `features/snapshot.py:95-105`, `snapshot.py:139-175`, `run.py:190-194`, `signals/llm_agent.py:52-60` | 코드 확인 |
| blind의 한계 | docstring이 "누수를 제거하지 않고 줄일 뿐"이라고 명시(독특한 비율 프로필로 대형주는 식별 가능). `industry`는 숨기지만 `sector`는 노출 | `snapshot.py:102-105`, `snapshot.py:143-144` | 코드 확인 |
| 프롬프트 지침 | 모든 페르소나에 "가장 최근 공시일을 현재로 간주하고 이후 지식을 쓰지 말라" 규칙 | `signals/buffett.py:48-52` 외 4개 페르소나 파일의 Hard rules | 코드 확인 |
| 라이브 모드는 unblind | paper/live는 `Fund(spec)`로 blind 없음(티커 노출) | `paper/tick.py:132`, `fund/spec.py:171-201` | 코드 확인 |

### 호출 제한과 실패 처리

| 대상 | 정책 | 근거 | 검증 |
|---|---|---|---|
| FD HTTP | 429만 재시도(대기 5s→15s→30s, 최대 3회) 후 `FDClientError`. 네트워크 오류·4xx/5xx는 즉시 `FDClientError`. **404만 "데이터 없음"(None)**. 페이지네이션(`next_page_url`)은 끝까지 추적, 도중 404는 누적분 유지 | `data/client.py:46`, `client.py:221-303` | 코드 확인 |
| 철학 | "fail loud": 인프라 실패는 예외, 진짜 "데이터 없음"만 빈 결과. 조용한 빈값은 백테스트를 오염시킨다 | `data/protocol.py:36-40`, `data/client.py:24-28`, `hedge_fund/README.md:135-136` | 코드 확인 |
| 실패 시 | 데이터 계층 예외는 에이전트에서 전파 → `advance` 실패 → paper는 **펀드 halt**(킬스위치 자동 설정) | `signals/llm_agent.py:70`, `paper/tick.py:133-142` | 코드 확인 |
| LLM | 호출/파싱 실패는 **abstain**(value 0.0, `abstained=True`)으로 처리 → 블렌딩에서 제외 | `signals/llm_agent.py:92-112`, `portfolio/construction.py:69-70` | 코드 확인 |
| LLM 호출 제한 | ChatLLM 계열 `timeout=60`, `max_tokens=4096`, `max_retries=1`; Jev는 429/5xx 1회 재시도 | `llm/client.py:225-229`, `client.py:258-281`, `client.py:115`, `client.py:156-170` | 코드 확인 |
| 사전 스로틀 | FD 쪽 rate limit 사전 스로틀은 없음(429 사후 대응뿐). TUI 사전 warm은 `ThreadPoolExecutor(max_workers=8)` | `tui/app.py:2992`, `data/client.py:281-287` | 코드 확인(스로틀 부재는 grep 결과 근거) |

## 근거 표 (요약)

| 구분 | 위치 | 식별자 | 설명 | 검증 |
|---|---|---|---|---|
| 데이터 Protocol | `hedge_fund/data/protocol.py:33-88` | `DataClient` | 공급자 인터페이스 | 코드 확인 |
| HTTP 클라이언트 | `hedge_fund/data/client.py:36-303` | `FDClient` | FD API, 재시도, 페이지네이션 | 코드 확인 |
| 디스크 캐시 | `hedge_fund/data/cached.py:40-174` | `CachedDataClient` | 응답 캐시, 일봉 완료성 검사 | 코드 확인 |
| 스냅샷 | `hedge_fund/features/snapshot.py:53-175` | `FundamentalsSnapshot.render` | 프롬프트 입력 생성(unblind/blind) | 코드 확인 |
| 스냅샷 빌더 | `hedge_fund/features/snapshot.py:178-234` | `build_snapshot()` | PIT 재무지표 + 집계 | 코드 확인 |
| 분위 테이블 | `hedge_fund/features/breakpoints.py:42-145` | `MEBreakpoints`, `load_breakpoints()` | blind용 시총 분위, 35일 캐시 갱신 | 코드 확인 |
| 세션 달력 | `hedge_fund/data/sessions.py:12-30` | `completed_through()`, `session_closes()` | 완료 세션, 벤치마크 그리드 | 코드 확인 |

permalink:
- https://github.com/virattt/ai-hedge-fund/blob/78b779c1389e2d1452dc29606d2c4126d859b964/hedge_fund/features/snapshot.py#L178-L234
- https://github.com/virattt/ai-hedge-fund/blob/78b779c1389e2d1452dc29606d2c4126d859b964/hedge_fund/data/client.py#L253-L303
