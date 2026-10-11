# TradingAgents — 다음 세션 메모

- 분석 SHA: `1394a3f72aa4393e1a98f51b382434c4b4c2d972` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: 전체
- 검증 수준 요약: 코드 확인 0 / 추론 1 / 미확인 3

## 확인한 범위

정독(전체 열람, 라인 번호 확인):
- `tradingagents/graph/` : `setup.py`, `conditional_logic.py`, `trading_graph.py`, `analyst_execution.py`, `propagation.py`, `checkpointer.py`(앞 80줄)
- `tradingagents/agents/` : 분석가 4종 + `turn.py`, 불/베어, `research_manager.py`, `trader.py`, `portfolio_manager.py`, 리스크 3인(공격적 전문, 나머지는 프롬프트 첫 문장), `schemas.py`, `rating.py`, `structured.py`, `state.py`, `context.py`, `tools.py`, `post_screen.py`
- `tradingagents/memory/` 3개 전부, `tradingagents/backtest.py`, `tradingagents/portfolio.py`
- `tradingagents/dataflows/` : `router.py`, `date_window.py`, `errors.py`, `config.py`, `symbols.py`, `net.py`, `vendors/yahoo/*`(전부), `sec_edgar.py`, `fred.py`(핵심 구간), `polymarket.py`(핵심 구간), `stocktwits.py`, `reddit.py`
- `default_config.py`, `main.py`, `cli/main.py`·`cli/run.py`(진입·REVIEW 처리), `cli/models.py`, `cli/prompts.py`(분석가 필터), `reporting.py`(앞부분), `README.md`, `CHANGELOG.md`(앞부분), `pyproject.toml`, `.github/workflows/ci.yml`
- grep 근거: 스케줄러·WebSocket·주문·한도·코인 전용 지표·미사용 함수

## 미확인 항목 체크리스트

- [ ] Alpha Vantage 벤더 내부(`dataflows/vendors/alpha_vantage/*.py` 5개): 캐시 유무, look-ahead 필터 구현(CHANGELOG는 있다고 함)
- [ ] LangGraph `ToolNode`의 도구 예외 기본 처리(예외가 런을 끝내는지) — 라이브러리 소관, 설치 금지라 미열람
- [ ] stockstats 지표 기본 파라미터(RSI 14, boll 20/2σ, ATR 14, MACD 12/26/9) — 라이브러리 소관(추론으로만 표기)
- [ ] `llm_clients/*`(공급자별 구조화 출력 지원, temperature·재시도 전달, `capabilities.py`/`model_catalog.py`) 내부
- [ ] `cli/prompts.py`·`cli/selections.py`·`cli/display.py` 전체(UI는 패널 이름 수준만 확인)
- [ ] `report_html.py` 렌더링 세부
- [ ] `tests/`의 의도 문서화 가치가 큰 테스트(`test_rating_integrity.py`, `test_memory_pointintime.py`, `test_structured_agents.py`, `test_graph_end_to_end.py`)로 동작 보증 범위 교차 확인
- [ ] 보수적·중립 리스크 토론 프롬프트 전문(첫 문장과 상태 갱신만 확인)
- [ ] Jev(TypeSafe) 외부 API 실제 응답 형식(레포 코드 기준으로만 확인)
- [ ] 실행 검증은 하지 않음(설치·실행 금지). 모든 "실행 확인"은 0건

## 다음에 볼 파일과 함수

| 목적 | 파일 / 함수 |
|---|---|
| 한국 벤더 삽입 프로토타입 설계 | `tradingagents/dataflows/router.py` `VENDOR_METHODS`·`route_to_vendor`, `tradingagents/dataflows/errors.py`, `tradingagents/dataflows/symbols.py` `normalize_symbol` |
| 정산 가격 소스 교체 | `tradingagents/memory/settlement.py` `fetch_returns`, `tradingagents/dataflows/vendors/yahoo/market.py` `get_closes` |
| 코드 게이트를 붙일 위치 | `tradingagents/graph/trading_graph.py` `_run_graph`→`record_decision` 직전, 또는 `portfolio_manager.py:80-86` 직후 |
| 비용 정밀화 | `cli/stats_handler.py`(`StatsCallbackHandler`)로 실제 호출 수 측정 방식 확인 |
| 다른 레포 비교용 | `agents/schemas.py`(출력 스키마), `agents/rating.py`(`REVIEW` 규약) |

## 분석 중 생긴 질문

1. RM·Trader·PM 등급이 충돌한 실제 빈도는? (코드는 강제하지 않음. 백테스트 로그로 측정 가능한지)
2. 5거래일 알파 정산이 5일 짜리 교훈을 PM에 주입하는 것이 의사결정 품질에 도움이 되는가? 레포는 창이 짧다고 인정만 함.
3. Sentiment의 point-in-time 불가를 인정하는데, 백테스트에서 소셜을 끄는 공식 권장 방법은? (`--analysts market,news,fundamentals` 사용 가능은 코드로 확인, 권장 여부는 미확인)
4. `get_stock_data`(비캐시)와 지표(캐시) 간 장중 불일치가 실제로 문제가 되는가?
5. 프롬프트 인젝션 방어를 위해 레포가 의도적으로 안 한 것인가, 아직 없는 것인가? (이슈 트래커는 미확인)
