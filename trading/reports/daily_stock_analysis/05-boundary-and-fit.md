# daily_stock_analysis — 판단→주문 경계와 우리 시스템 적용

- 분석 SHA: `ce364e457aab288863a5707e7b3df79786ad07f2` (repos.lock.tsv와 일치해야 함)
- 분석일: 2026-10-09
- 관련 공통 항목: Q6, Q7
- 검증 수준 요약: 코드 확인 13 / 추론 3 / 미확인 1 (실행 확인 0; 본문 내 표기 횟수 기준 근사치)

경로 약어: `analyzer.py`=`src/analyzer.py`, `pipeline.py`=`src/core/pipeline.py`, `base.py`=`data_provider/base.py`, `config.py`=`src/config.py`, `search_service.py`=`src/search_service.py`, `storage.py`=`src/storage.py`, `orchestrator.py`/`runner.py`/`executor.py`/`factory.py`/`protocols.py`=`src/agent/…`, `defaults.py`/`aggregator.py`/`router.py`/`deliberation.py`=`src/agent/skills/…`, `agents/*_agent.py`=`src/agent/agents/…`, `search_tools.py`/`data_tools.py`=`src/agent/tools/…`, `stock_analyzer.py`=`src/stock_analyzer.py`. 그 외는 레포 루트 기준 상대경로를 그대로 적었다.

---

## Q6. 경계 기록 {#q6}

### 6-1. 판단 → 주문 경계

| 질문 | 답 | 근거 | 검증 |
|---|---|---|---|
| 판단 결과를 주문으로 바꾸는 코드가 있는가 | **없다.** `src data_provider api bot main.py` 전체에서 `place_order|submit_order|create_order|unlock_trade|order_id` 등을 대소문자 무시로 검색해 주문 실행 코드 일치가 없었다. 브로커 코드는 Futu 보유 조회 하나뿐이며 `OpenSecTradeContext`를 쓰지만 호출은 `position_list_query`(보유 조회)다 | `src/brokers/futu/portfolio.py:1-3`, `:249-255` | 코드 확인 |
| 판단 결과의 형식 | `AnalysisResult` → `analysis_history`(원본 JSON+컨텍스트 스냅샷) 저장 후 **DecisionSignal** 행으로 추출: `action(8상태), confidence(0-1), score, horizon, entry_low/high, stop_loss, target_price, invalidation, watch_conditions, reason, risk_summary, catalyst_summary, evidence_json, data_quality_summary_json, plan_quality, status(active), expires_at, market_phase, decision_profile` | `src/storage.py:1034-1075`, `src/services/decision_signal_extractor.py:43-176`, `pipeline.py:957-1000` | 코드 확인 |
| 가격·수량 필드의 출처 | LLM이 쓴 문장형(`"理想入场位：XX元（…）"`)에서 숫자를 추출. **수량·비중을 계산하는 코드는 없다** (`suggested_position`은 "X成" 문자열) | `analyzer.py:2209-2229`, `decision_signal_extractor.py:368-377`(entry 범위) | 코드 확인 |
| 신호 수명 | 만료시각(`expires_at`) 부여, 반대 방향 활성 신호는 새 신호가 나오면 무효화(`_invalidate_opposing_active_signals`), 상태 `active/…` | `src/services/decision_signal_service.py:883-1011` | 코드 확인 |
| 사후 평가 | 신호별 결과(`decision_signal_outcomes`), 분석 단위 백테스트 | `storage.py:1128`, `services/decision_signal_outcome_service.py` | 코드 확인(테이블·서비스 존재), 내부 미열람 |
| 사람 승인 단계 / 기본값 | 주문 자체가 없으므로 해당 없음. 신호는 "참고용 조언"으로 알림·웹에 표시. 재평가 API(`reassess`)는 사람이 호출 | `decision_signal_reassess_service.py:59-89` | 코드 확인 |
| 하드 리스크 한도(종목당 상한, 일일 한도, 킬스위치) | **없다.** 포트폴리오 서비스는 집중도·낙폭 임계 **경고**(`concentration_alert_pct`, `drawdown_alert_pct`)와 손절 모니터링 리포트를 만들 뿐 주문을 막지 않는다 | `src/services/portfolio_risk_service.py:39-100`, `:282-320`, `:466-520` | 코드 확인 |
| 결정적 "플랜 품질" 게이트(재평가 경로 한정) | 매수/추가 신호를 `watch`/`alert`로 낮추는 조건: horizon 없음, `invalidation`·`stop_loss` 모두 없음, 데이터 품질 `poor/unknown`, `confidence` 없음 또는 `< 0.5`(`MIN_ACTIONABLE_CONFIDENCE`), 공격형 프로필에서 invalidation 없음·장기 horizon, 가격 관계 위반(`entry_low>entry_high`, `stop_loss>=target`, `stop_loss>=entry_high`, `target<=entry_low` 계열). 이 정책은 `reassess`에서만 호출됨(기본 파이프라인 저장 경로에서는 호출처 없음) | `src/services/decision_profile_policy.py:13-23`, `:129-205`, 호출 `decision_signal_reassess_service.py:85-89`(grep) | 코드 확인 |
| 규칙 기반 비중 산출(LLM 없음) | ETF 이중 모멘텀 로테이션(`--etf-rotation`): 매주/매월 마지막 거래일 종가로 `lookback_days`(기본 60) 모멘텀 계산 → 양(+)인 상위 `top_n`개(코드 기본 2, 모듈 기본 1)에 각 `1/top_n`, 빈 슬롯은 안전자산/현금, 기존 보유는 `switch_buffer_pct`(2%) 이내 열세면 유지, 비용 단방향 10bp. 하루 후 종가 체결(T → T+1) 가정 | `src/core/etf_rotation.py:43-58`, `:116-148`, `src/services/etf_rotation_service.py:333-346`, `src/config.py:1239-1246` | 코드 확인 |

### 6-2. 판단 근거를 보여주는 UI

- 보고서 화면(`apps/dsa-web/src/components/report/`): `ReportStrategy`가 저격 구간 4칸(매수/손절/목표 등)을 격자로 표시(`ReportStrategy.tsx:55-85`), `ReportOverview/Summary/Details`가 점수·핵심 결론·세부 서술, `ReportNews`가 뉴스. `코드 확인`(ReportStrategy), `추론`(나머지는 파일명과 `ls` 결과 기준, 내부 미열람)
- `AnalysisContextSummary`는 "입력 데이터 블록(quote/daily_bars/technical/chip/fundamentals/news)별 상태와 개수"를 중/영/한 3개 언어로 표시(`AnalysisContextSummary.tsx:68,100,132`), `ReportDiagnostics`는 진단 정보. `코드 확인`(AnalysisContextSummary 문자열), `추론`(Diagnostics)
- 별도 페이지: `DecisionSignalsPage`(신호 목록), `BacktestPage`(사후 성과), `PortfolioPage`, `AlertsPage`, `StockScreeningPage`. `코드 확인`(파일 존재) — 표시 항목은 미열람

---

## Q7. 우리 시스템에 적용 (분석자 의견) {#q7}

> **이 절은 코드 근거가 아니라 분석자 의견이다.** 위 사실(Q1~Q6)을 전제로 한 설계 제안이며 실행 검증을 하지 않았다.

### 7-1. 가져갈 것 / 버릴 것 (의견)

| 구분 | 항목 | 이유 | 출처 |
|---|---|---|---|
| 가져갈 것 | **점수↔액션 정본표와 `guardrail_reason` 계약**(80/60/40/20 구간, 괴리 시 사유 필수) | 단순하고 감사 가능. 최종 `action`과 점수가 따로 놀 때 사유가 남는다 | `src/schemas/decision_scale.py:25-43`, `:158-171` |
| 가져갈 것 | **"LLM 초안 → 결정적 코드가 하향만 하는" 후처리 구조** (자금흐름 확인 없는 매수 강등, 장단계, 대시장 환경) | LLM의 과도한 낙관을 코드로 제한하는 가장 값싼 안전장치. 방향이 하향 전용이라 사고 위험이 낮다 | `analyzer.py:1043-1218`, `phase_decision_guardrail.py:116-205`, `daily_market_context_guardrail.py:62-112` |
| 가져갈 것 | **입력 데이터 품질 블록(AnalysisContextPack)과 degrade 시 신뢰도 상한** | 시세 지연·폴백·결측을 판단에 반영하는 방식이 명시적이다 | `analysis_context_builder.py:504-551`, `phase_decision_guardrail.py:159-168` |
| 가져갈 것 | **주문 직전 하드 게이트로 쓸 플랜 품질 검사** (손절<진입<목표, 신뢰도≥0.5, 데이터 품질, invalidation 필수) | 우리 주문 계층 바로 앞에 붙이기 좋은 결정적 검증. 이 레포는 재평가에만 쓰므로 우리는 기본 경로에 넣는다 | `decision_profile_policy.py:129-205` |
| 가져갈 것 | **뉴스 검색 파이프라인**: 차원별 템플릿, 날짜 엄격 필터, 관련도 랭킹, 스팸/저품질 필터, 3상태 증거 공개(미설정/0건/정상) | 재사용 가치 높음. 단 쿼리는 한국어/영어로 새로 작성 | `search_service.py:3186-3491`, `:4384-4693`, `agent/news_evidence.py` |
| 가져갈 것 | **사후 평가 엔진**(advice→방향 분류, ±2% 중립 밴드, 손절/목표 선도달 시뮬레이션, 일봉 한계 명시) | 판단 품질 피드백 루프의 뼈대. 우리는 벤치마크(KOSPI, BTC) 초과수익과 거래비용을 추가해야 한다 | `core/backtest_engine.py:158-275` |
| 가져갈 것 | **기술지표 점수 모듈** `StockTrendAnalyzer`(추세 30+乖离 20+거래량 15+지지 10+MACD 15+RSI 10) | pandas 전용이라 이식이 쉽다. 단 임계값은 재튜닝 필요 | `stock_analyzer.py:585-754` |
| 가져갈 것 | **규칙 기반 ETF 로테이션**(LLM 없이 비중 `1/top_n`) | "결정은 코드" 패턴의 가장 깨끗한 예. 코인/ETF 자산배분 모듈로 참고 | `core/etf_rotation.py` |
| 가져갈 것(아이디어) | 스킬 의견의 사후 성과 → 가중치(0.83~1.2배, 표본 ≥30) | 표본이 쌓인 뒤에만 영향이 생기는 보수적 설계 | `skill_opinion_weight_service.py:28-35` |
| 버릴 것 | A주 전용 데이터·개념(용호방, 북향자금, 칩 분포, 涨跌停, T+1), 중국어 프롬프트 원문 | 키움·업비트와 무관. 프롬프트는 번역이 아니라 재작성해야 의미 보존 | `defaults.py`, `analyzer.py:1949-2320` |
| 버릴 것 | **문장형 가격 필드**(`"XX元（…）"`)를 사후 파싱하는 방식 | 우리는 JSON 숫자 필드(진입/손절/목표/비중)로 강제해야 주문 계층에 안전하게 연결된다 | `analyzer.py:2209-2229` |
| 버릴 것 | **키워드 매칭 기반 가드레일**(부정어 접두어 탐지 등)과 텍스트 파싱 폴백(키워드 개수로 buy/sell 생성) | 취약하고 언어 의존적. 구조화된 필드로 판정해야 한다 | `daily_market_context_guardrail.py:16-47`, `analyzer.py:5592-5659` |
| 버릴 것 | 5천 줄급 단일 클래스 구조(`analyzer.py`)를 통째 복사 | 유지보수 비용. 아이디어(함수 단위)만 발췌 | `analyzer.py` |
| 주의 | `get_analysis_context`가 `target_date`를 무시하고 DB 최신 2행을 씀 → 과거 시점 재현 불가 | 우리는 모든 데이터 호출에 `as_of`를 필수 인자로 둘 것 | `storage.py:3483-3515` |
| 주의 | 한국 `.KS` 경로는 자금흐름이 항상 `not_supported`라 **매수가 항상 hold로 강등**된다 | 우리가 이 가드레일을 이식하면 키움 수급 데이터를 먼저 채워야 매수가 나온다 | `analyzer.py:1093-1117`, `base.py:4057-4075` |

### 7-2. 업비트·키움 데이터로 대체할 항목 (의견)

| 이 레포의 항목 | 우리 시스템 대체 후보 | 비고 |
|---|---|---|
| 일봉/실시간(efinance, akshare, yfinance 등 폴백 체인) | 키움 REST 일봉·현재가, 업비트 캔들·티커. 폴백 구조(우선순위+서킷브레이커 3회/5분)는 아이디어만 차용 | 한국 종목은 이 레포도 yfinance 단일이라 폴백이 없음 |
| 주력 자금흐름(`main_net_inflow`, 5일/10일) | 키움 `ka10059`(종목별 투자자·기관별 매매) 등 수급 TR을 같은 필드명(`main_net_inflow`, `inflow_5d`, `inflow_10d`)으로 매핑 | TR 필드 세부는 확인하지 않았음(가이드 예시 기준) |
| 재무/배당(akshare) | DART 재무제표·배당 | 이 레포의 프롬프트용 필드(`revenue, net_profit_parent, operating_cash_flow, roe, ttm_dividend_yield`)를 그대로 매핑 가능 |
| 칩 분포 | 대체 데이터 없음 → 제거 | 한국 시장에서 같은 지표를 얻기 어려움(미확인) |
| 뉴스 검색(Bocha/Tavily 등) | 네이버 뉴스 검색 API, Tavily/SearXNG(한국어 쿼리) | 이 레포는 한국어 템플릿이 없다. 공시는 검색 대신 DART 공시 목록 API |
| 3대 법인(대만) | 한국 외국인·기관 순매수(키움 수급) | 같은 형식 블록으로 프롬프트에 주입하는 패턴 참고(`analyzer.py:4629-4690`) |
| 시장 단계(장전·장중·종가 단일가) | KRX 09:00-15:30, 종가 단일가 15:20-15:30(이 레포 설정 참고) | `trading_calendar.py:60-67` |
| 코인 전용(펀딩비, OI, 온체인, 공포탐욕) | **이 레포에는 없음** | 코인은 다른 레포(예: 코인 지표가 있는 레포)에서 보완해야 함. 24/7 시장이라 "장단계" 대신 일봉 마감 시각(UTC 00:00=KST 09:00) 기준이 필요 |
| 스케줄 | 한국: 장 마감 15:30 이후 + 시간대 맞춘 cron(Actions의 UTC 10:00은 KST 19:00) | `00-daily-analysis.yml:6` |

### 7-3. 라이선스 (의견 + 코드 사실)

- 저장소 라이선스는 **MIT**(`LICENSE:1-3`, "Copyright (c) 2026 ZhuLinsen"). 코드·프롬프트·YAML 스킬 재사용이 가능하다(저작권·허가 고지 유지). `코드 확인`
- 단, 데이터 제공자(AkShare 스크래핑 대상 사이트, 검색 API, yfinance 등)의 **이용약관은 별개**이며 이 레포 라이선스가 면제해 주지 않는다. 키움·업비트 데이터로 대체하면 문제가 줄어든다. `추론`
- 권장 방식: 코드 통째 복사 대신 (1) 점수 정본표, (2) 가드레일 함수 3개, (3) 뉴스 필터/랭킹, (4) 백테스트 엔진을 **함수 단위로 발췌**하고 출처·MIT 고지를 주석으로 남긴다. (의견)
