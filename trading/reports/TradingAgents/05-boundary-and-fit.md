# TradingAgents — 경계와 적용 의견

- 분석 SHA: `1394a3f72aa4393e1a98f51b382434c4b4c2d972` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q6, Q7
- 검증 수준 요약: 코드 확인 12 / 추론 0 / 미확인 0

<a id="q6"></a>
## Q6. 경계 기록 (짧게)

### 판단 → 주문 경계

| 질문 | 답 | 근거 | 검증 |
|---|---|---|---|
| 판단 결과를 주문으로 바꾸는 코드가 있는가 | **없다.** 출력은 등급(+선택적 진입가·손절가·목표가·비중 문자열)과 마크다운뿐이다. 주문·수량·체결·현금 장부 코드가 없고 레포가 스스로 "수량·체결가·현금 장부가 시스템에 없다"고 밝힌다 | `backtest.py:9-15`, `agents/schemas.py:155-183,221-265`, 주문 관련 grep 0건 | 코드 확인 |
| 반환 형식 | `propagate()`는 `(final_state, signal)`, `signal`은 5등급 문자열 또는 `"REVIEW"` | `trading_graph.py:167-182,404`, `rating.py:22-30` | 코드 확인 |
| REVIEW 가드 | 호출자는 `is_review(signal)`로 먼저 거른 뒤 enum에 매핑하라고 docstring이 요구. CLI는 경고만 표시 | `trading_graph.py:177-181`, `rating.py:115-117`, `cli/run.py:377-384` | 코드 확인 |
| 비중을 정하는 코드 | 없음. 비중은 Trader/PM의 자유 문자열(예: "5% of portfolio") | `schemas.py:180-183,240-245` | 코드 확인 |
| 포트폴리오 인지 | 호출자가 `PortfolioContext`(현금, 통화, 종목별 수량·평단)를 넘기면 Trader·리스크 3인·PM이 참고. 안 넘기면 "모름"으로 명시(빈 계좌 가정 금지) | `portfolio.py:23-64`, `context.py:204-218`, `trading_graph.py:305`, 체크포인트 서명 포함 `trading_graph.py:157-158` | 코드 확인 |
| 사람 승인 단계 | 없음(승인 개념 자체가 없음). 대신 `REVIEW` 표식이 "사람이 봐야 함"의 유일한 신호 | `rating.py:26-30` | 코드 확인 |
| 하드 리스크 한도(종목당 상한·일일 한도·킬스위치) | **없음** | `agents/`, `graph/` 전수 확인에서 한도 로직 0건 | 코드 확인(부재) |
| README와의 차이 | README는 "PM이 승인/거절하면 승인 시 주문이 시뮬레이션 거래소로 전송·체결된다"(`README.md:108`)고 쓰지만 코드에 시뮬레이션 거래소나 주문 모듈이 없다. 코드를 기준으로 삼는다 | `README.md:107-108` vs `backtest.py:9-15` | 코드 확인 |

### 판단 근거를 보여주는 UI

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| CLI 라이브 화면(rich) | 에이전트별 진행 상태 표(Progress), "Messages & Tools" 로그, "Current Report" 패널, 호출·토큰 통계 푸터 | `cli/display.py:266,310-332,376` | 코드 확인 |
| 완료 후 보고서 | I.분석가 / II.연구팀(불·베어·RM) / III.Trader / IV.리스크 3인 / V.PM 결정을 패널로 순서대로 출력 | `cli/display.py:395-437`, `reporting.py:50-73` | 코드 확인 |
| 저장물 | 섹션별 `.md`, `complete_report.md`, 한 장짜리 `complete_report.html`(목차 포함), 헤더에 등급·모델·분석가·데이터 벤더·메모리 노트 기록. 상태 로그 JSON `full_states_log_<날짜>.json` | `reporting.py:20-46,92-120`, `report_html.py:248`, `trading_graph.py:437-475` | 코드 확인 |

<a id="q7"></a>
## Q7. 우리 시스템에 적용 (분석자 의견)

> 이 절은 코드 근거가 아니라 **분석자 의견**이다. 근거 위치는 의견의 출처가 되는 코드를 가리킨다.

### 의견 1. 가져갈 것

| 가져갈 요소 | 이유 | 출처 코드 |
|---|---|---|
| **point-in-time 유틸**(`as_of`·`as_of_window`·`in_window`·`coverage_gap` 및 "withhold" 패턴) | 백테스트 신뢰성의 핵심. LLM이 날짜를 마음대로 넣어도 코드가 상태의 `trade_date`로 클램프하고, 피드가 못 본 구간은 "없음"이 아니라 "관측 불가"로 표기 | `dataflows/date_window.py:18-170`, `tools.py:1-5` |
| **벤더 라우터 + 3종 예외 + 센티널 문자열** | 폴백과 "장애 vs 데이터 없음" 구분을 한 곳에서 처리, LLM에는 "추정 금지" 문구로 전달 | `router.py:200-297`, `errors.py:21-58` |
| **검증 스냅샷 패턴**(코드가 계산한 가격·지표 표를 "진실원"으로 두고 LLM 주장과 충돌 시 표시) | 숫자 환각 억제. 우리 키움·업비트 일봉에도 그대로 적용 가능 | `snapshot.py:66-127`, `market_analyst.py:48` |
| **분석가 서브그래프 + 도구 라운드 상한 + WRAP_UP** | 도구 루프 폭주 방지의 단순하고 검증된 구현 | `graph/setup.py:53-90`, `turn.py:7-42` |
| **구조화 출력 + 자유텍스트 폴백 + `REVIEW` 센티널** | 파싱 불가를 Hold로 둔갑시키지 않는 설계. 주문 계층에 넘기기 전 "거래 불가" 분기로 직결 가능 | `structured.py:42-95`, `rating.py:26-30,96-103` |
| **메모리 로그: pending 저장 → N거래일 후 알파 정산 → 성찰 → point-in-time 필터 주입** | 사후 채점 루프 구조 자체가 재사용 가치. 단, 5거래일 한 창은 짧다(레포도 성찰 프롬프트에서 인정) | `memory/log.py:32-201`, `settlement.py:52-155`, `reflection.py:13-63` |
| **PortfolioContext 3상태**(보유/빈 계좌/정보 없음) | 보유 현황을 모른 채 비중을 말하지 않게 하는 계약. 키움·업비트 잔고를 이 모양으로 변환해 넣으면 된다 | `portfolio.py:23-64`, `context.py:204-218` |
| 병렬 분석가 + 조인(LangGraph fan-out) | 지연을 가장 느린 분석가로 한정 | `setup.py:157-166` |

### 의견 2. 버릴 것 / 조심할 것

| 항목 | 이유 | 근거 |
|---|---|---|
| 불·베어 / 리스크 3자 토론 전체 | LLM 호출이 기본 15-40회이고 상위 에이전트가 4개 보고서를 5번 재수신해 토큰 비용이 크다. 규칙 기반 점수 + 1회 LLM 종합으로 대체 검토가 비용 대비 낫다(의견) | `03-decision.md` 4-8, `bull_researcher.py:42-48` |
| 최종 등급을 LLM 단독으로 정하는 구조 | RM·Trader·PM 불일치를 잡는 코드와 하드 한도가 없다. 우리는 주문 계층 앞에 **코드 게이트(종목당 상한·일일 한도·킬스위치)** 를 별도로 두어야 한다 | `portfolio_manager.py:80-104`, `setup.py:175-185` |
| 비중·진입가·손절가 문자열 | 파싱·검증 없는 자유 텍스트라 주문에 직접 쓸 수 없다. 우리 스키마는 수치 필드로 강제해야 한다 | `schemas.py:164-183` |
| StockTwits·Reddit 소셜 | 미국 중심이고 과거 데이터가 보관되지 않아 백테스트에 쓸 수 없다. 한국 커뮤니티·업비트 맥락과 맞지 않는다 | `sentiment_analyst.py:10-13`, `stocktwits.py:30`, `reddit.py:79-93` |
| Yahoo 의존 전반 | 비공식 라이브러리(yfinance)이고 개요·재무제표는 과거 날짜 런에서 보류된다. 한국 종목 재무는 EDGAR 대상이 아니다 | `yahoo/fundamentals.py:37-39`, `sec_edgar.py:135-142` |
| 외부 텍스트의 프롬프트 직주입 | 인젝션 방어가 없다(`03-decision.md` 4-9 참고). 뉴스·게시글은 지시를 무력화하는 격리 구분자와 출력 검증이 필요 | `sentiment_analyst.py:154-170` |

### 의견 3. 업비트·키움 데이터로 대체할 항목

| 이 레포의 항목 | 대체 후보 | 삽입 위치 |
|---|---|---|
| OHLCV(`get_stock_data`) | 키움 일봉 REST(국내·미국), 업비트 캔들 API | `router.py:99-102`의 `VENDOR_METHODS["get_stock_data"]`에 벤더 함수 추가, `default_config.py:159`에 체인 `"kiwoom,yfinance"` 식으로 지정 |
| 기술지표 | 위 일봉으로 stockstats 그대로 계산 | `yahoo/ohlcv.py`의 `load_ohlcv` 대응 함수를 새 벤더에 구현(통일된 DataFrame 규약: `Date, Open, High, Low, Close, Volume`) |
| 수급(레포에는 없음) | 키움 `ka10059` 등 | 새 도구 + 새 `TOOLS_CATEGORIES` 항목(`router.py:45-87`) + Market/Fundamentals 분석가 `TOOLS` 튜플(`market_analyst.py:8-12`) |
| 재무제표·펀더멘털 | DART(공시일 기준 as-filed — SEC 구현이 설계 선례) | `sec_edgar.py`의 "공시일≤기준일" 구조를 DART 접수일에 대응 |
| 코인 심볼 | 업비트 `KRW-BTC` 형식 | `symbols.py:79`의 `_CRYPTO_QUOTES`에 KRW 없음, `_CRYPTO_BASES` 11개 제한(`symbols.py:43-45`) → 확장 필요 |
| 지역 벤치마크 | 한국은 `.KS`→`^KS11`, `.KQ`→`^KQ11` 이미 있음. 코인 벤치마크(BTC 등)는 `benchmark_ticker` 직접 지정 | `default_config.py:181-190` |
| 정산 가격 | `settlement.py`가 `yahoo.market.get_closes`에 하드 결합 → 키움/업비트 종가로 교체 필요. 코인은 24/7이라 "5거래일" 정의를 재검토 | `settlement.py:9,73-76`, `yahoo/market.py:268-272` |
| 뉴스 | 네이버·DART 공시 피드 등 별도 구현 | `get_news` 벤더 추가(`router.py:129-136`) |

### 의견 4. 라이선스

- 레포 라이선스는 **Apache-2.0**(`LICENSE:1`의 "Apache License", `repos.lock.tsv`와 GUIDE §2.1 표기 일치). 코드 확인(LICENSE 헤더). 상용 포함 코드 재사용 가능하며, 사용 시 라이선스 사본 포함·변경 표시·저작권 고지 유지 의무가 있다(일반 Apache-2.0 조건, 법률 자문 아님).
- 의견: 아이디어 참고뿐 아니라 `date_window.py`·`router.py`·`errors.py`처럼 의존성이 가벼운 모듈은 고지를 유지한 채 직접 가져와도 된다. 다만 `yfinance`·`langgraph` 결합이 강한 부분(`ohlcv.py`, `setup.py`)은 아이디어만 가져오고 새로 쓰는 편이 유지보수에 유리하다.
