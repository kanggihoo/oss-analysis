# TradingAgents — 최신화와 스케줄링

- 분석 SHA: `1394a3f72aa4393e1a98f51b382434c4b4c2d972` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q3
- 검증 수준 요약: 코드 확인 20 / 추론 0 / 미확인 0

<a id="q3"></a>
## Q3. 최신화와 스케줄링

**요약: 이 레포에는 스케줄러가 없다.** 모든 분석은 사람이 CLI/파이썬 API를 호출할 때만 시작되고, 데이터를 미리 쌓아 두는 사전 동기화 작업도 없다(판단할 때마다 가져온다). 주기 실행은 사용자가 cron 등으로 직접 감싸야 하며, 레포는 그걸 위한 비대화형 CLI 플래그와 `settle_all_pending()` API만 제공한다.

### Q3-1. 트리거

| 트리거 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 대화형 CLI | `tradingagents` 또는 `python -m cli.main` | `pyproject.toml:43-44`의 `[project.scripts] tradingagents = "cli.main:app"`, `cli/main.py:25-100` | 코드 확인 |
| 비대화형 CLI | `--ticker --date --analysts --save --no-show` 등 플래그와 `TRADINGAGENTS_*` 환경변수만으로 무질문 실행("scheduled job or a script" 용도). 터미널이 없으면 빠진 답을 나열하고 종료 | `cli/main.py:52-66`, `cli/run.py:98-108`, `README.md:208-214` | 코드 확인 |
| 파이썬 API | `TradingAgentsGraph.propagate(ticker, date)` | `graph/trading_graph.py:167-190`, `main.py:12-16` | 코드 확인 |
| 백테스트 | `tradingagents backtest NVDA,AAPL --start --end --every 7` → 티커×날짜 격자 순차 실행 | `cli/main.py:103-140`, `backtest.py:129-181` | 코드 확인 |
| 정산 전용 | `settle_all_pending()` — 분석 없이 만기 지난 결정만 정산(스케줄러용 API라고 docstring 명시) | `trading_graph.py:348-356`, `memory/settlement.py:158-169`, `README.md:339` | 코드 확인 |
| cron / GitHub Actions / APScheduler / Celery / 이벤트(가격 조건) | **없음**. `cron|schedul|apscheduler|celery|websocket`를 `*.py,*.md,*.yml,*.toml`(tests 제외)에서 grep 시 문서의 "scheduled job" 언급과 docstring만 나옴. `.github/workflows/ci.yml`은 테스트·설치 스모크 전용 | grep 결과, `.github/workflows/ci.yml:1-50` | 코드 확인(부재) |

### Q3-2. 주기와 시점

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 기본 주기 | 없음(호출 시 1회). 사용자가 `--date`를 직접 지정 | `cli/main.py:53` | 코드 확인 |
| 거래일 캘린더 확인 | **없음**. 휴장일이면 그 날 이전 마지막 바를 쓰고(OHLCV `<= as_of`), 10일 넘게 비어 있으면 stale 오류 | `yahoo/ohlcv.py:229-255` | 코드 확인 |
| 장 마감 후 판단 가정 | 분석일 종가를 포함해 판단하고(`Date <= as_of`), 정산 시 진입가는 분석일 종가 | `ohlcv.py:230`, `memory/settlement.py:73,83,91` | 코드 확인 (진입=당일 종가라는 의미는 코드에서 도출) |
| 당일 장중 실행 | 당일 요청은 캐시를 900초만 신뢰(장중 미확정 일봉이 종가로 오인되는 것 방지) | `ohlcv.py:20-24,146-158` | 코드 확인 |
| 체크포인트 재개 | 옵트인. 같은 티커+날짜+그래프 설정이면 마지막 성공 노드부터 재개 | `trading_graph.py:192-245`, `graph/checkpointer.py:28-65` | 코드 확인 |

### Q3-3. 사전 동기화

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 데이터 사전 적재 | **없음**. DB도 없다. 영속 저장은 (a) 종목별 OHLCV CSV 캐시, (b) SEC JSON 캐시, (c) 마크다운 메모리 로그, (d) 체크포인트 SQLite, (e) 실행 결과 JSON/리포트뿐 | `ohlcv.py:190-224`, `sec_edgar.py:122-132`, `memory/log.py:11-60`, `checkpointer.py:19-51`, `trading_graph.py:437-475` | 코드 확인 |
| 유일한 "백그라운드성" 작업 | 런 도중 `Memory Log` 노드가 분석가와 **병렬로** 모든 종목의 만기 도래 결정을 정산(가격 조회 + 성찰 LLM 호출). 실패해도 런은 계속 | `graph/setup.py:157-166`, `trading_graph.py:308-335` | 코드 확인 |
| 다음 런에서야 반영되는 구조 | 한 런의 자기 결정은 다음 런에서야 정산됨. 백테스트는 마지막에 `settle_pending`을 한 번 더 호출 | `trading_graph.py:337-346`, `backtest.py:173-180` | 코드 확인 |

### Q3-4. 데이터 신선도(stale) 관리

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| OHLCV stale 감지 | 최신 행이 요청일보다 10일 초과 과거면 `NoMarketDataError` → 폴백/센티널 | `ohlcv.py:18,109-143` | 코드 확인 |
| stale 시 판단 반영 | **확신도 하향 같은 코드 처리 없음.** "데이터 없음" 센티널이 도구 결과로 LLM에 전달되고, LLM이 보고서에 "데이터 없음"을 쓰게 프롬프트로 유도할 뿐 | `router.py:185-197`, `turn.py:7-10`(WRAP_UP: "어떤 데이터를 못 가져왔는지 말하라") | 코드 확인 |
| 소셜·뉴스 신선도 | 피드가 윈도를 관측 못하면 "공백"이 아닌 `<... unavailable ...: not an absence>` 표기 | `date_window.py:44-68` | 코드 확인 |
| 센티먼트 확신도 | 소스가 placeholder거나 5건 미만이면 `confidence=low`로 쓰라고 **스키마 설명에서 안내**(LLM이 채움, 코드 강제 아님) | `agents/schemas.py:342-349`, `sentiment_analyst.py:184` | 코드 확인 |
| 캐시 만료 | OHLCV 당일치만 유효, SEC 24h | `ohlcv.py:146-158`, `sec_edgar.py:41` | 코드 확인 |

### Q3-5. 실시간 스트림

- WebSocket·구독 방식 데이터 스트림은 **없다**(위 grep). 코드에 보이는 "stream"은 LangGraph 진행 상황 스트리밍(`trading_graph.py:406-435`)이며 CLI 화면 갱신용이다. 코드 확인.
- 즉 실시간 시세·체결 스트림은 판단에도 화면에도 쓰이지 않는다.

### Q3-6. 우리 시스템 관점 메모 (의견)

- 의견: 스케줄링은 우리가 직접 만들어야 한다. 이 레포에서 가져올 것은 "만기 도래 결정을 별도 작업으로 정산"하는 `settle_all_pending()` 계약과, 비대화형 실행용 환경변수 설계 정도다.
