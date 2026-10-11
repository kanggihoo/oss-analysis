# daily_stock_analysis — 확인 범위와 다음 작업

- 분석 SHA: `ce364e457aab288863a5707e7b3df79786ad07f2` (repos.lock.tsv와 일치해야 함)
- 분석일: 2026-10-09
- 관련 공통 항목: 전체
- 검증 수준 요약: 코드 확인 0 / 추론 0 / 미확인 1 (실행 확인 0; 본문 내 표기 횟수 기준 근사치)

경로 약어: `analyzer.py`=`src/analyzer.py`, `pipeline.py`=`src/core/pipeline.py`, `base.py`=`data_provider/base.py`, `config.py`=`src/config.py`, `search_service.py`=`src/search_service.py`, `storage.py`=`src/storage.py`, `orchestrator.py`/`runner.py`/`executor.py`/`factory.py`/`protocols.py`=`src/agent/…`, `defaults.py`/`aggregator.py`/`router.py`/`deliberation.py`=`src/agent/skills/…`, `agents/*_agent.py`=`src/agent/agents/…`, `search_tools.py`/`data_tools.py`=`src/agent/tools/…`, `stock_analyzer.py`=`src/stock_analyzer.py`. 그 외는 레포 루트 기준 상대경로를 그대로 적었다.

---

## 1. 확인한 범위 (직접 열어 읽은 파일)

| 영역 | 파일 | 범위 |
|---|---|---|
| 진입점/스케줄 | `main.py`, `src/scheduler.py`, `src/services/runtime_scheduler.py`, `.github/workflows/00-daily-analysis.yml` | 인자, 거래일 필터, 스케줄 루프, 워크플로 전체 흐름 |
| 파이프라인 | `src/core/pipeline.py` | `analyze_stock`, `_analyze_with_agent`, `process_single_stock`, `run`, 수집·가드레일 호출 순서 |
| 판단(레거시) | `src/analyzer.py` | 프롬프트(레거시/스킬형), `_format_prompt`, `analyze`, 가드레일 전부, 파서, 무결성 |
| 판단(Agent) | `src/agent/orchestrator.py`(실행 루프·체인·risk override·점수 보정), `agents/{technical,intel,risk,decision}_agent.py`, `risk_override.py`, `factory.py`, `executor.py`(프롬프트), `skills/{defaults,aggregator,router}.py`, `protocols.py` | 프롬프트 원문, 체인, 임계값 |
| 가드레일/스키마 | `src/phase_decision_guardrail.py`, `src/daily_market_context_guardrail.py`, `src/schemas/{decision_scale,decision_action,report_schema}.py`, `src/stock_analyzer.py` | 전체 |
| 데이터 | `data_provider/base.py`(핵심 경로), `realtime_types.py`, `fundamental_adapter.py`(`get_fundamental_bundle`, `get_capital_flow`), `tw_institutional_fetcher.py`(머리말) | 우선순위, 폴백, 한국 경로, 서킷브레이커 |
| 검색 | `src/search_service.py`(생성자, `search_comprehensive_intel`, `search_stock_news`, 필터/랭킹 요약), `src/agent/tools/search_tools.py`, `src/services/intelligence_service.py`(머리말·갱신), `social_sentiment_service.py`(머리말) | 쿼리 템플릿, 제공자 |
| 경계/평가 | `src/services/decision_signal_*`(extractor 일부, service 일부, reassess), `decision_profile_policy.py`, `portfolio_risk_service.py`, `src/core/backtest_engine.py`, `src/services/skill_opinion_weight_service.py`, `src/core/etf_rotation.py`, `src/services/etf_rotation_service.py`, `src/brokers/futu/portfolio.py`(머리말) | 규칙·임계값 |
| 시장/설정 | `src/core/trading_calendar.py`, `src/market_context.py`, `src/market_phase_prompt.py`, `src/core/market_profile.py`, `src/core/market_strategy.py`(KR), `src/config.py`(관련 기본값), `docs/market-support.md`(한국 부분) | 한국 경로 |
| 문서 | `README.md`(요약 일부), `LICENSE` | README↔코드 차이 확인용 |

## 2. 미확인 항목 체크리스트

- [ ] 개별 fetcher 내부 구현(efinance/akshare/pytdx/baostock/yfinance/tencent/tushare/tickflow/longbridge/futu): 요청 URL, 레이트리밋, 재시도 세부
- [ ] `GeminiAnalyzer._call_litellm_impl`(`analyzer.py:3604-3880`): 모델 폴백 순서, 스트리밍·비스트리밍 전환, 사용량 기록 세부
- [ ] `strategies/*.yaml` 15개 중 `bull_trend` 외 14개의 `instructions`와 `sentiment_score` 조정 폭
- [ ] `src/agent/skills/skill_agent.py` 프롬프트, `agent/disagreement.py`, `final_explanation.py`, `skills/deliberation.py`의 LLM/멀티라운드 중재자(기본 경로 미연결로 확인했으나 활성화 설정은 못 찾음)
- [ ] `src/agent/orchestrator.py:1370-1660` `_finalize_dashboard_payload` 전체 규칙(대시보드 보정 로직 중 점수·액션을 코드가 더 바꾸는 곳이 있는지)
- [ ] `src/services/decision_signal_outcome_service.py`(신호 단위 사후 채점), `decision_signal_summary.py`, 신호 `plan_quality` 계산
- [ ] `src/services/screening/*`(종목 스크리닝 10개 YAML 전략: `balanced_alpha, dual_low, momentum_quality` 등): 이번 범위(판단 파이프라인) 밖이라 미열람
- [ ] `src/services/scheduled_analysis_claim.py` 중복 실행 claim 구현
- [ ] `src/market_analyzer.py`의 시장 복기 프롬프트 원문(`generate_market_review`), 복기 요약이 `daily_market_context`로 전달되는 정확한 규칙(`risk_tags` 생성 패턴은 `services/daily_market_context.py:50-60`에서 일부만 확인)
- [ ] 웹 UI 컴포넌트 내부(`ReportOverview`, `ReportDetails`, `ReportDiagnostics`, `DecisionSignalsPage`): 표시 필드
- [ ] `analyzer.py:5427-5530` `_parse_response` 후반(필드 매핑)과 `apply_placeholder_fill`의 구체 문구
- [ ] Longbridge `push_candlestick_mode` 푸시가 판단 경로에 쓰이는지
- [ ] 한국 종목의 실제 실행 결과(실행 검증 없음 — 이번 분석은 정적 코드 추적): 특히 "자금흐름 미지원 → 항상 buy 강등"은 정적 추적으로만 확인했고, 실제 한국 종목 입력으로 재현하지 않았다
- [ ] `tests/`(296개 파일): 가드레일 동작 예시를 더 모으면 규칙의 의도 확인에 도움(예: `tests/test_decision_stability.py`는 일부만 확인)

## 3. 다음에 볼 파일과 함수

1. `src/agent/skills/deliberation.py`의 `LLMDeliberationMediator`/`MultiRoundDeliberationMediator`를 켜는 설정이 있는지(없다면 현재 "LLM 토론 없음" 결론 유지)
2. `src/agent/orchestrator.py:1370-1660` `_finalize_dashboard_payload` — Agent 경로의 추가 코드 보정
3. `src/core/market_review.py`, `src/market_analyzer.py:779-904` — 대시장 복기 프롬프트와 가드레일 입력
4. `data_provider/yfinance_fetcher.py`의 `get_realtime_quote`·`get_daily_data`(한국 종목 필드 품질, `missing_fields` 처리)
5. `src/services/decision_signal_outcome_service.py` — 신호 단위 채점 공식(우리 사후 평가 설계에 참고)
6. `tests/test_decision_stability.py`, `tests/test_phase_decision_guardrail.py`, `tests/test_daily_market_context_guardrail.py` — 가드레일 의도와 예외 사례

## 4. 분석 중 생긴 질문

1. 한국 종목에서 buy가 항상 hold로 강등된다면(03 문서 4-5 (1)), 이 레포 사용자는 한국 종목을 어떻게 쓰는가? 의도된 동작인가, 미처리 가장자리 케이스인가? (`docs/market-support.md`는 "완전한 기본면/업종/시장 폭은 약속하지 않음"이라고 명시)
2. GitHub Actions 실행에서는 DB가 비영속인데 자동 백테스트(`BACKTEST_ENABLED` 기본 true)는 실질적으로 아무 것도 평가하지 못한다. 의도된 구성인가?
3. `AGENT_MODE=false` 기본값이 사실상 "단일 LLM 호출 + 규칙 프롬프트"이므로 Agent/스킬/오케스트레이션은 선택 기능이다. 프로젝트의 주력 사용 방식은 어느 쪽인가(README는 둘 다 소개)?
4. 코드 점수(`系统评分`)와 LLM 점수가 충돌할 때 LLM이 따르는가? 프롬프트에 "코드 점수를 따르라"는 직접 지시는 찾지 못했다(참고 표로만 제공). 실제 일치율은 `analysis_history`가 있어야 측정 가능.
