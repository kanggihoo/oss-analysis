# QuantDinger — 확인한 범위, 미확인, 다음에 볼 것

- 분석 SHA: `ba8cd667acca3e934bbc1cb354922eff413393dc` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1~Q7 전체
- 검증 수준 요약: 코드 확인 6(차이 표 행) / 추론 3(재현 필요 항목) / 미확인 13(체크리스트 항목)

> 약어: `BE` = `backend_api_python/app`. 실행·설치·빌드는 하지 않았다(GUIDE 2.2). 모든 라인 번호는 위 SHA에서 직접 연 파일 기준이다.

## 1. 확인한 범위

| 영역 | 읽은 정도 | 파일 |
|---|---|---|
| 분석 오케스트레이션 | **전체 정독** | `BE/services/fast_analysis.py`(1~1644), `fast_analysis_scoring.py`(전체), `fast_analysis_policy.py`, `fast_analysis_plan.py`, `fast_analysis_fundamentals.py`, `fast_analysis_tasks.py`, `routes/fast_analysis.py:25-305` |
| 전문 보고서 계층 | **전체 정독(contracts·features 일부 제외)** | `BE/professional_report/{llm_contract,prompt,snapshot,builder,quality,risk}.py`, `narrative.py` 일부, `contracts.py:1-175`, `features/crypto.py:640-760`, `features/equity.py:1-60`, `providers/catalog.py` 일부 |
| 데이터 수집 | collect_all·가격·K선·펀더멘털 계층·암호화폐 팩터·뉴스·매크로 정독. 미국 펀더멘털 1060행 이후, CN/HK 세부는 일부만 | `BE/services/market_data_collector.py`, `market/technical_indicators.py`, `kline.py`, `data_sources/factory.py`, `us_stock.py`(일부), `crypto.py`(일부), `data_providers/{us_research,hk_research,sentiment}.py`(일부) |
| 스케줄·동기화 | **정독** | `BE/celery_app.py`, `tasks/*.py`, `startup.py`, `commands/scheduler.py`, `services/{portfolio_monitor(1~460,1288~1560,1747~),fundamental_sync,fundamental_data,reflection,ai_calibration,analysis_memory}.py` |
| 검색·리서치 | **정독** | `BE/services/{research_agent,research_web,search}.py`, `data_providers/company_research.py`, `routes/ai_chat.py`(리서치 관련 구간만: 1380~1530, 2198~2260, 2394~2560, 3170~3275) |
| 주문 경계 | 짧게 | `BE/services/{ai_decision_filter,ai_decision,ai_decision_context}.py`, `pending_orders/order_budget.py`, `trading_executor.py:1725-1800`, `strategy_v2/live_execution.py:225-290`, `routes/{quick_trade_ai,agent_v1/quick_trade}.py` 일부 |
| 문서 | README 일부, `docs/product/AI_RESEARCH.md`, LICENSE/TRADEMARKS | — |

## 2. README(및 GUIDE)와 코드가 다른 곳

| 항목 | 문서의 주장 | 코드 | 근거 |
|---|---|---|---|
| Celery 정기 모니터링 | GUIDE 5절: "Celery 정기 모니터링" | 포트폴리오 모니터는 스케줄러 프로세스(또는 단일 프로세스)의 **데몬 스레드**. Celery Beat은 펀더멘털 동기화·사후검증·보정·카탈로그 동기화 등 유지보수만 | `BE/celery_app.py:62-91`, `BE/startup.py:60-71,261-278`, `BE/services/portfolio_monitor.py:1830-1841` |
| LLM의 역할 | 보고서 `methodology.llm_role="evidence_explanation_only"`, 프롬프트 "You do not decide … final execution eligibility" | 합의가 중립이면 LLM의 BUY/SELL이 가드를 통과해 최종 결정이 됨 | `BE/professional_report/builder.py:727-730`, `BE/services/fast_analysis.py:997-1003` |
| 대칭 원칙 | 프롬프트 "Apply BUY and SELL symmetrically" | 합의 덮어쓰기 문턱 상향은 "합의 BUY vs LLM SELL/HOLD + 약세 맥락"에만 존재 | `BE/professional_report/prompt.py:116`, `BE/services/fast_analysis.py:963-968` |
| 단일 LLM | 클래스 docstring "单次LLM调用" | 환경변수로 2~3모델 앙상블 가능(기본 꺼짐) | `BE/services/fast_analysis.py:31-36,491-526` |
| 점수→결정 임계 | `_score_to_decision` docstring: 고정 ±20 | 실제는 DB 보정 행(`buy_threshold/sell_threshold`)이 있으면 그 값 | `BE/services/fast_analysis.py:1494-1514` |
| README 주문 필터 흐름 | Jev 실패 시 LLM, 둘 다 불가 시 fail-open, 청산은 우회 | **코드와 일치**(차이 없음). 단 `ENTRY_ACTIONS`에 일반 `buy/sell`이 들어 있어 호출자가 그대로 넘기면 `sell`도 진입으로 취급됨 | `README.md:449,458-505`, `BE/services/ai_decision_filter.py:21,141-150` |

## 3. 미확인 항목 체크리스트

- [ ] 프론트엔드(Vue/모바일)의 화면 이름·표시 항목 — 이 레포에 없음(별도 저장소, source-available)
- [ ] 미국 펀더멘털 `_get_financial_statements`·`_get_earnings_data`(`BE/services/market_data_collector.py:1133-1405`)의 세부 계산
- [ ] CN/HK 펀더멘털 티어별 병합 로직(`:577-970`), `data_sources/{cn_stock,hk_stock,asia_stock_kline,tencent}.py`
- [ ] 암호화폐 `CryptoDataSource`의 거래소별 심볼 정규화·실패 분류(`BE/data_sources/crypto.py`, `native_crypto.py`)
- [ ] `LLMService.call_llm_api`의 폴백 모델·대체 제공자 재시도 세부(`BE/services/llm.py:1136-1330`)
- [ ] 홍콩 리서치 캐시 TTL 값(`BE/data_providers/hk_research.py:226-229` ↔ `data_providers/__init__.py` TTL 테이블)
- [ ] 사용자 피드백(`user_feedback`)이 점수·프롬프트에 쓰이는지
- [ ] AI 진입 필터 `_persist`·`list_ai_decisions`(`BE/services/ai_decision_filter.py:560-743`) 및 UI 타임라인
- [ ] `ai_chat.py`의 의도 분류 LLM 호출 수와 최종 답변 단계(4,727줄 중 리서치 구간 외)
- [ ] `routes/agent_v1/research.py`·`mcp_server/`가 fast_analysis/research_agent를 노출하는지
- [ ] `strategy_ai_capabilities.py`(1,415줄)·`ai_skill_registry.py`·`ai_tool_registry.py`의 전략용 AI 프로필 정의
- [ ] **실행 재현이 필요한 추론 3건**: (a) CN/FX/선물에서 전문 보고서가 `professional_report_error`로 빠지는지, (b) LLM 완전 실패 시 합의만으로 BUY/SELL이 나오는지, (c) 증거 ID 중복 시 보고서 빌드 예외 여부. 실행은 합의 후 진행(GUIDE 2.2)
- [ ] `tests/`(예: `test_fast_analysis_plan_contract.py`, `test_professional_report_*`)가 위 동작을 어떻게 고정하는지

## 4. 다음에 볼 파일과 함수

1. `BE/services/llm.py:1136-1330` `call_llm_api` — 재시도·폴백·JSON 모드 처리
2. `BE/services/market_data_collector.py:1133-1405` `_get_financial_statements`, `_get_earnings_data`
3. `BE/data_sources/crypto.py` `CryptoDataSource.get_kline`/`for_exchange` — 업비트 어댑터를 끼울 위치 판단
4. `BE/services/ai_decision_filter.py:560-743` `_persist`, `list_ai_decisions`
5. `BE/routes/ai_chat.py` 의도 분류(`agent_intent`)와 `_build_research_context` 전체
6. `BE/services/strategy_ai_capabilities.py` — 전략 코드에서 `ai.evaluate`를 쓰는 방식
7. `BE/professional_report/features/crypto.py` 전체 — 거래소·상품 혼용 금지 검증 규칙(우리 업비트 규칙 설계에 참고)
8. `tests/test_professional_report_builder.py`, `tests/test_fast_analysis_plan_contract.py`

## 5. 분석 중 생긴 질문

- 합의 오버라이드 문턱 15와 매수/매도 임계 20이 겹치는 이유는? 보정 임계값이 15 아래로 내려갈 때만 의미가 있는가(보정 후보 격자는 10~30).
- 보조 TF를 `collect_all` 전체로 수집하는 이유(기술 점수만 필요한데 펀더멘털·리서치까지 병렬 호출)가 성능 문제를 만들지 않는가.
- `quality_multiplier`의 매크로·뉴스 감점이 사실상 발동하지 않는 것(헬퍼가 예외를 삼킴)은 의도인가.
- 검색 결과의 누락된 날짜를 "오늘"로 채우는 동작이 뉴스 신선도 검사를 무력화하지 않는가.
- 사후 채점에서 보유기간이 고정되지 않은 점이 보정(`ai_calibration`)의 정확도 추정을 얼마나 왜곡하는가.
