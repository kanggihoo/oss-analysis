# QuantDinger — 판단→주문 경계와 우리 시스템 적용 (Q6, Q7)

- 분석 SHA: `ba8cd667acca3e934bbc1cb354922eff413393dc` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q6, Q7
- 검증 수준 요약: 코드 확인 13 / 추론 2 / 미확인 0 (본문 표기 건수 기준)

> 약어: `BE` = `backend_api_python/app`. 브로커 연동·주문 실행 내부 구현은 GUIDE 0절에 따라 조사하지 않았다. 경계만 짧게 기록한다.

---

## Q6. 경계 기록 {#q6}

### Q6-1. 판단 → 주문 경계

| 질문 | 답 | 근거 | 검증 |
|---|---|---|---|
| fast_analysis 결과를 주문으로 바꾸는 코드가 있는가 | **없음.** `get_fast_analysis_service`/`FastAnalysisService`를 쓰는 곳은 `routes/fast_analysis.py`, `services/portfolio_monitor.py`, Celery 태스크 래퍼뿐이고 모두 결과를 저장·표시·보고서로만 돌린다 | grep: `BE/routes/fast_analysis.py`, `BE/services/portfolio_monitor.py:295-347`, `BE/tasks/fast_analysis.py:8-13`, `BE/services/fast_analysis_tasks.py:90-149` | 코드 확인 |
| 판단 결과의 형식 | `trading_plan{entry_price, stop_loss, take_profit, position_size_pct, timeframe, risk_reward_ratio, rr_warning, source}` + `professional_report.risk_plan{recommended_position_pct, max_position_pct, net_risk_reward, valid, warnings}` + `decision_profile{decision, confidence…}` | `BE/services/fast_analysis.py:1093-1107`, `BE/professional_report/risk.py:199-213` | 코드 확인 |
| 비중을 정하는 코드 | `risk.py`: 위험예산(기본 1% 계좌)÷손절거리 → 상품 상한(암호화폐 30%, 그 외 50%)×품질 점수 → LLM 제안 크기와 `min`. **계좌 잔고와는 연결되지 않은 "% of equity" 값**이며 수량 환산은 소비자 몫 | `BE/professional_report/risk.py:171-188` | 코드 확인 |
| 사람 승인 단계 | fast_analysis 자체에는 주문이 없어 승인 단계도 없다. 주문은 (a) 전략 런타임, (b) Quick Trade, (c) Agent Gateway에서 나가며 AI는 **선택적 진입 필터**로만 끼어든다 | `BE/services/strategy_v2/live_execution.py:234-276`, `BE/routes/quick_trade_ai.py:15-70` | 코드 확인 |
| AI 필터 기본값 | **꺼짐**: 스키마 기본 `ai_decision_filter=False`, 전략 설정도 `bool(trading_config.get("ai_decision_filter"))` | `BE/openapi/schemas/high_risk.py:136`, `BE/services/trading_executor.py:1733` | 코드 확인 |
| AI 필터가 막는 방식 | 거부되면 주문 의도를 `ai_rejected`로 바꾸고 거래소로 보내지 않음(래치). 청산·SL/TP·긴급 액션은 필터를 우회(README 주장은 코드와 일치: 진입 액션만 평가) | `BE/services/strategy_v2/live_execution.py:262-276`, `BE/services/ai_decision_filter.py:141-150` | 코드 확인 |
| 에이전트(MCP) 주문 | 기본 **paper-only**. 실거래는 토큰 스코프 T + `paper_only=false` + 서버 환경변수 `AGENT_LIVE_TRADING_ENABLED=true` 3중 조건. 별도 킬스위치 엔드포인트가 에이전트 주문 취소 + T 토큰 폐기 | `BE/routes/agent_v1/quick_trade.py:1-11,40-41,456-464,515-521` | 코드 확인 |
| 하드 리스크 한도 | ① 전략 주문 예산: 주문·예상 총 노셔널 ≤ `자본×레버리지×(1+버퍼, 상한 10%)`. 검증 불가(자본·가격 0)이면 **거부(fail-closed)**. AI 필터보다 **먼저** 실행. ② 종목당 상한·일일 손실 한도·전역 킬스위치는 이 경로에서 확인하지 못함(`max_daily_loss`/`kill_switch` grep 결과는 에이전트 킬스위치와 리스크 플랜 필드뿐) | `BE/services/pending_orders/order_budget.py:11-64`, `BE/services/trading_executor.py:1733-1762` | 코드 확인(① 확인, ②는 범위 밖이라 미확인) |
| 전략 코드용 AI 평가 | `ai.evaluate(...)` → `action(buy/sell/hold)`, `score(−100~100)`, `confidence(0~1)`. 실패·미설정은 `hold`, 호출 예산 `max_calls_per_run`(기본 25), 입력 100KB·프롬프트 4,000자 제한, 비밀키 이름 필드 마스킹, 결정 키로 **멱등 캐시**(`qd_ai_strategy_decisions`) | `BE/services/ai_decision.py:34-45,152-303,416-425` | 코드 확인 |

### Q6-2. 판단 근거를 보여주는 UI

- 프론트엔드는 **이 레포에 없다**(README: 별도 저장소 `QuantDinger-Vue`, `-Mobile`, source-available 라이선스). 화면 이름과 표시 항목은 **미확인**이다.
- 백엔드가 UI에 내려주는 근거 필드(코드 확인): `professional_report.decision_profile`(원 결정/게이트 후 결정, 게이트 사유), `dimensions[]`(기술·펀더멘털·뉴스감성·매크로·시장특화, 각 증거 ID·누락 데이터), `claims[]`(증거 ID가 붙은 주장), `scenarios`(bull/base/bear), `risk_plan`, `data_quality`, `evidence_snapshot`, `warnings`(`BE/professional_report/builder.py:691-738`).
- 주문 필터는 "공급자, 체크 항목, 결과, 확신도, 지연시간, 사유"를 타임라인으로 저장해 보여준다고 README가 설명하고, 저장 코드는 `AIDecisionFilter._persist`/`list_ai_decisions`로 존재한다(`BE/services/ai_decision_filter.py`의 `_persist`는 본문 일부만 읽음 — 표시 화면은 미확인).

---

## Q7. 우리 시스템에 적용 (분석자 의견) {#q7}

> **이 절 전체가 분석자 의견이다.** 코드 근거가 필요한 부분은 위 문서의 `파일:라인`을 참조한다. 업비트·키움 API 세부는 코드로 확인한 것이 아니라 일반 지식과 GUIDE 예시에 근거한다(키움 `ka10059`, DART는 GUIDE 7절 예시).

### Q7-1. 가져갈 것 / 버릴 것

| 구분 | 항목 | 이유 | 원본 위치 |
|---|---|---|---|
| **가져갈 것(핵심)** | 증거 스냅샷 + `evidence_id` + 매니페스트 프롬프트 + 주장 필터 | 데이터 출처·시점·단위를 LLM과 감사 로그가 공유하는 구조. 어댑터만 우리 데이터로 새로 쓰면 됨 | `BE/professional_report/snapshot.py`, `prompt.py:56-70`, `llm_contract.py:56-101` |
| 가져갈 것 | 데이터 품질 게이트(커버리지·신선도·충돌 → HOLD·확신도 상한) | 결정적이고 단순함. 필수 메트릭 목록만 시장별로 교체 | `BE/professional_report/quality.py:66-186` |
| 가져갈 것 | 리스크 플랜(위험예산÷손절거리, 상품 상한×품질, 비용 가정, 기하 검증) | "LLM 포지션은 상한 이하로 제한" 원칙. 단 수수료·세금·호가단위·최소주문금액을 한국 시장에 맞게 교체 | `BE/professional_report/risk.py:89-213` |
| 가져갈 것 | "코드가 LLM을 덮어쓰는" 구조(다중 TF 합의·가드·계획 재검증) | LLM 환각이 주문 크기로 새는 것을 막는 가장 직접적인 장치 | `BE/services/fast_analysis.py:970-1003,1337-1482`, `fast_analysis_plan.py:22-112` |
| 가져갈 것 | 지표 계산 모듈(RSI14·MACD12/26/9·ATR14·BB20·MA·피벗) | 의존성 없는 순수 파이썬 279줄 | `BE/services/market/technical_indicators.py` |
| 가져갈 것 | 펀더멘털 point-in-time 스냅샷(`available_at`)과 24시간 DB 캐시·write-back | 백테스트 누수 방지 + API 호출 절감. DART 공시일을 `available_at`으로 | `BE/services/fundamental_data.py:201-379` |
| 가져갈 것 | 주문 직전 필터 구조: **하드 한도 → AI 필터 → 주문**, 청산은 필터 우회, 판단 기록 저장, 멱등 키 | 순서와 감사 기록이 좋다. fail-open/closed 정책은 우리가 정함 | `BE/services/ai_decision_filter.py`, `BE/services/ai_decision.py:152-303` |
| 가져갈 것 | 연구 에이전트의 방어 장치(도구 화이트리스트, 이전 증거 URL만 읽기, 재호출 금지, 시간·호출 예산, DNS 고정 HTTPS 리더) | Q&A형 리서치를 붙일 때 그대로 유용 | `BE/services/research_agent.py:186-266`, `BE/services/research_web.py:15-94` |
| 아이디어만 | 사후 채점 + 임계값 자기 보정 | 구조는 좋으나 채점 기준이 약함(고정 ±2/±5%, 보유기간 비고정, 벤치마크·비용 없음). **5거래일 고정 + KOSPI/BTC 대비 초과수익 + 비용 반영**으로 다시 설계 | `BE/services/analysis_memory.py:766-846`, `ai_calibration.py:163-310` |
| 아이디어만 | 객관 점수 공식(RSI/MACD/MA 가중, 패닉 붕괴 정의) | 임계값은 검증 안 된 휴리스틱. 우리 데이터로 백테스트 후 조정 필요 | `BE/services/fast_analysis_scoring.py:191-350` |
| **버릴 것** | 죽은 코드(`_format_*`, `_build_decision_guidance`, FA `_calculate_indicators`), 미사용 `decision_votes`, Finnhub 소셜 감성 수집 | 유지 가치 없음 | 01-data Q1-2 |
| 버릴 것 | 감성 점수 25% 가중(사실상 지정학 정규식 패널티) | 신호 품질 낮음(추론). 한국어 뉴스 감성은 별도 설계 | `BE/services/fast_analysis_scoring.py:557-625` |
| 버릴 것 | **LLM 실패 시에도 합의만으로 방향 결정이 나오는 흐름**, 전문 보고서 예외 시 게이트 우회(fail-open) | 개인 자금 시스템에서는 LLM 실패=거래 불가(fail-closed)가 안전 | 03-decision 4-6 |
| 버릴 것 | 크레딧 과금·Jev(외부 SaaS)·Flask/Celery/PostgreSQL 전체 결합, 중국어 하드코딩 문자열, 6개 코인 하드코딩 설명 | 우리에게 불필요하거나 결합도가 높음 | — |
| 재설계 | `SELL`=숏 의미 | 업비트 현물·키움 국내주식은 숏이 없음 → `EXIT`(청산)/`REDUCE`/`AVOID`로 의미 분리 | `BE/professional_report/prompt.py:123` |

### Q7-2. 업비트·키움 데이터로 대체할 항목

| QuantDinger 항목 | 현재 제공자 | 우리 시스템 대체(의견) | 비고 |
|---|---|---|---|
| 암호화폐 시세·K선 | 6개 거래소 REST(기본 binance) | **업비트 공개 REST**(티커·분봉/일봉 캔들) | KRW 마켓 단위·호가단위 처리 필요. `quote_currency`는 `KRW` |
| 국내 주식 시세·K선 | 없음(KRX 미지원) | **키움 REST**(시세·일봉·분봉) | 상장 휴장일·장 운영시간 캘린더 필요(QD는 분석에서 캘린더 미사용) |
| 수급·자금흐름(국내) | HK 남향 프록시 등 | 키움 `ka10059`(GUIDE 예시: 투자자별 수급) | QD의 "프록시를 순매수로 부르지 말라" 류 규칙을 우리 항목 정의에 그대로 적용 |
| 재무·펀더멘털(국내) | CN/HK용 AkShare 등 | **DART** 재무제표·공시(공시일 → `available_at`) | 분기/TTM/연간 분리 원칙(QD의 `financial.latest_quarter/ttm/latest_annual`)을 그대로 따름 |
| 미국 주식 시세·펀더멘털 | Finnhub·yfinance·SEC EDGAR | 키움 해외주식 시세(가능 범위) + SEC EDGAR 재사용 | QD의 `us_research.py`(SEC 공시 목록·Form4 건수) 아이디어 재사용 |
| 코인 펀딩비·OI·롱숏비 | CoinGlass(유료) → Gate/OKX/Binance 공개 | 업비트는 현물이라 파생 데이터가 없음 → **참고 지표**로 Binance 선물 공개 API만 사용하되 "venue=binance, product=perpetual"을 명시(QD의 단위·거래소 혼용 금지 규칙 유지) | 업비트 가격과 직접 비교 시 김치 프리미엄 지표를 별도 추가 |
| 공포탐욕지수 | alternative.me | 그대로 사용 가능 | 코인 전용 |
| 거시(VIX·DXY·TNX) | yfinance | 유지 + **USD/KRW, 한국 기준금리, KOSPI/KOSDAQ 지수** 추가 | QD 매크로 점수는 미국 중심 |
| 뉴스 | Finnhub + 검색(Tavily 등) | DART 공시 + 국내 뉴스 검색. 검색 결과 날짜 누락 시 "오늘"로 채우는 동작은 제거 | `BE/services/market_data_collector.py:2600` |
| 언어 | zh-CN/zh-TW/en-US/ja-JP | 한국어 규칙 문구 추가 | `BE/professional_report/prompt.py:11-16` |

### Q7-3. 라이선스·재사용 가능성

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 백엔드 코드 | Apache License 2.0 → 코드 복사·수정·재배포 가능. 조건: 라이선스·저작권 고지 유지, 변경 사실 표기, 특허 조항 준수. 루트에 `NOTICE` 파일은 없음 | `LICENSE`, `README.md:697-700` | 코드 확인(루트 목록에서 NOTICE 부재 확인) |
| 상표 | 이름·로고·브랜드는 Apache가 허가하지 않으며 `TRADEMARKS.md`가 별도로 통제 → 재사용 코드에서 "QuantDinger" 명칭·로고 제거 | `TRADEMARKS.md:1-20`, `README.md:697-708` | 코드 확인 |
| 프론트엔드·모바일 | 별도 저장소·**source-available** 라이선스. 이 레포에 없고 이번 분석 범위 밖. 화면 코드 재사용은 해당 라이선스를 따로 확인해야 함 | `README.md:701-708` | 코드 확인 |
| 권장(의견) | 코드 직접 복사는 `professional_report/{quality,risk,snapshot,llm_contract}.py`와 `technical_indicators.py` 수준의 **자기완결 모듈**로 제한하고, 나머지는 설계 아이디어를 참고해 새로 작성 — 결합도(Flask·PostgreSQL·billing)와 중국어/Jev 의존 때문 | — | 추론 |
