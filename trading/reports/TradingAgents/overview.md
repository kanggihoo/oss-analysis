---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-03
---
# TradingAgents — 최신 feature map

## 1. 기본 정보

- URL: https://github.com/TauricResearch/TradingAgents
- 기준: v0.7.1 · `c4544913a14ed3df5f1ed7b9e8483270ce20682a` · 커밋 2026-10-27. 2026-11-02 원격 `main` fetch 결과로 고정, detached HEAD·clean (Git 확인).
- 목적: 업비트·키움 기반 개인 AI 트레이딩 시스템의 데이터 수집·시점 제한·AI 판단·사후 평가 설계 및 후속 기능 스펙의 작업 단위 선정. [GUIDE](../../GUIDE.md)의 우선순위 적용.
- 라이선스: Apache License Version 2.0 (`LICENSE:1-4`, 코드 확인). 추적 파일에서 하위 LICENSE는 발견하지 못했다.
- 제품: `tradingagents` Python 라이브러리와 같은 배포물의 `cli` 패키지. `pyproject.toml`의 `[project.scripts]`는 `cli.main:app`, 패키지 탐색은 `tradingagents*`, `cli*` (코드 확인). 중첩 매니페스트·별도 웹 서버 배포 입구는 추적 파일 목록에서 발견하지 못했다.
- 스펙 범위: **2026-11-02 사용자 진행 승인: 행 1~14 + S1·S2**. 앞서 제안한 메인·서브 3개 배분으로 원본 동작을 분석한다. 부속 15~17은 앞선 기본 제외안을 유지한다. 미국주식 사용도 고려해 국장용 구현으로 변경하지 않는다.
- 실행 한계: 원본 설치·실행·외부 API 호출 없이 코드와 Git만 확인했다. 외부 제공자의 실제 응답·인증 성공 여부는 미확인.

### 이전 기준 대비 변경

| 영역 | 이전 `1394a3f` → 현재 `c454491` | 근거·검증 |
|---|---|---|
| 인증 | `chatgpt_auth.py`와 CLI `login/logout` 추가 | `cli/main.py:167-194`, `chatgpt_auth.py:324-345` · 코드 확인 |
| CLI 설정 | `cli/config.py`, `announcements.py` 삭제, prefs 변경·updates 추가 | [변경 파일 목록](../../artifacts/TradingAgents/update-files.tsv), `cli/prefs.py:28-85`, `cli/updates.py:30-65` · 코드 확인 |
| 날짜 제한 | 날짜 표준화와 시작일>종료일 거부 추가 | `dataflows/date_window.py:79-111` · 코드 확인 |
| 재무표 | 항목별 행에서 기간별 행으로 전환, 소액 백만 USD 표시 보정 | `dataflows/vendors/sec_edgar.py:217-250` · 코드 확인 |
| 사후 평가 | 분석일 이후 첫 종가를 진입가로 사용, 진행 중인 당일 봉 제외 | `memory/settlement.py:44-100` · 코드 확인 |
| 판단 골격 | 병렬 분석·투자 토론·트레이더·리스크 토론·PM 연결 유지 | `graph/setup.py:125-185` · 코드 확인 |

## 2. Feature map

선행은 재구현에 필요한 계약이며 실행 순서 전체가 아니다. 아래 번호·핵심/부속 분류·묶음은 분석자 제안이다. 승인된 행1~14와 S1·S2는 기능 스펙의 행동 규칙·코드 참조·수락 사례까지 작성했다. 부속 행15~17은 진입점 수준의 미작성 상태로 남긴다.

| # · 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 (레포 상대 경로) | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 1 · 실행 설정·모델 계층 | 설정과 quick/deep 공급자를 선택한다 | tradingagents/llm_clients/factory.py:137-156 create_tier_client |  | 핵심 | [configuration](capabilities/configuration.md) · ready | 코드 확인(진입점·호출) |
| 2 · 종목·보유 현황 입력 | 종목·날짜·자산 유형과 선택적 보유 현황을 상태로 조립한다 | tradingagents/graph/trading_graph.py create_run_state; tradingagents/portfolio.py:25-79 PortfolioContext | 1, S1 | 핵심 | [run-input](capabilities/run-input.md) · ready | 코드 확인(진입점·호출) |
| 3 · 데이터 벤더 라우팅 | 가격·지표·재무·뉴스·거시·예측시장 벤더의 명시적 폴백 체인을 선택한다 | tradingagents/dataflows/router.py:97-149,200-297 route_to_vendor | 1, 4, 2 | 핵심 | [vendor-routing](capabilities/vendor-routing.md) · ready | 코드 확인(진입점·호출) |
| 4 · 분석 기준일 제한 | LLM이 요청한 날짜를 기준일 이하로 제한하고 잘못된 기간을 거부한다 | tradingagents/dataflows/date_window.py:79-111 as_of, as_of_window; tradingagents/agents/tools.py | S1 | 핵심 | [point-in-time](capabilities/point-in-time.md) · ready | 코드 확인(진입점·호출) |
| 5 · 가격·기술 분석 | OHLCV·지표·검증 스냅샷으로 시장 보고서를 만든다. 스냅샷은 Yahoo 직접 경로다 | tradingagents/agents/analysts/market_analyst.py:8-84 TOOLS, create_market_analyst; tradingagents/dataflows/vendors/yahoo/snapshot.py build_verified_market_snapshot | S1, 1, 2, 3, 4, 9 | 핵심 | [market-analysis](capabilities/market-analysis.md) · ready | 코드 확인(진입점·호출) |
| 6 · 기업·재무 분석 | 기업 개요·재무제표·내부자 거래로 재무 보고서를 만든다 | tradingagents/agents/analysts/fundamentals_analyst.py:14-64 create_fundamentals_analyst; tradingagents/dataflows/vendors/sec_edgar.py:191-268 _statement | S1, 1, 2, 3, 4, 9 | 핵심 | [fundamentals-analysis](capabilities/fundamentals-analysis.md) · ready | 코드 확인(진입점·호출) |
| 7 · 뉴스·거시·이벤트 분석 | 뉴스·FRED·Polymarket 도구 결과를 뉴스 보고서로 만든다 | tradingagents/agents/analysts/news_analyst.py:13-63 create_news_analyst | S1, 1, 2, 3, 4, 9 | 핵심 | [news-analysis](capabilities/news-analysis.md) · ready | 코드 확인(진입점·호출) |
| 8 · 소셜 감성 분석 | 뉴스·StockTwits·Reddit을 사전 수집해 감성 보고서를 만든다 | tradingagents/agents/analysts/sentiment_analyst.py:55-105 create_sentiment_analyst | S1, 1, 3, 4, S2, 2 | 핵심 | [sentiment-analysis](capabilities/sentiment-analysis.md) · ready | 코드 확인(진입점·호출) |
| 9 · 병렬 분석·도구 루프 | 선택 분석가와 메모리를 병렬 실행하고 보고서를 합류시킨다. 도구 라운드 상한 포함 | tradingagents/graph/setup.py:49-89,109-166 _analyst_graph, setup_graph | 1, S1, S2, 2 | 핵심 | [analysis-orchestration](capabilities/analysis-orchestration.md) · ready | 코드 확인(진입점·호출) |
| 10 · 투자 토론·계획·트레이더 제안 | Bull/Bear 토론 뒤 매니저 계획과 트레이더 제안을 만든다 | tradingagents/graph/setup.py:132-135,168-176 setup_graph; tradingagents/graph/conditional_logic.py:12-21 should_continue_debate | S1, 1, 2, S2 | 핵심 | [investment-decision](capabilities/investment-decision.md) · ready | 코드 확인(진입점·호출) |
| 11 · 리스크 토론·최종 판단 | 3자 토론 뒤 PM이 5등급을 결정한다. 파싱 불가 시 REVIEW 경로 | tradingagents/graph/setup.py:137-140,177-185; tradingagents/agents/managers/portfolio_manager.py:23-106 create_portfolio_manager | S1, 1, 2, S2, 10 | 핵심 | [risk-decision](capabilities/risk-decision.md) · ready | 코드 확인(진입점·호출) |
| 12 · 판단 기록·정산·교훈 | 과거 결정의 수익률·벤치마크 대비 성과를 평가하고 교훈을 PM 입력으로 돌린다 | tradingagents/graph/trading_graph.py _memory_step, record_decision; tradingagents/memory/settlement.py:44-100 fetch_returns; tradingagents/memory/reflection.py:13-63 | 1, S1, S2, 2 | 핵심 | [decision-memory](capabilities/decision-memory.md) · ready | 코드 확인(진입점·호출) |
| 13 · 중단 실행 재개 | 설정·종목·날짜·보유 현황에 맞는 SQLite 체크포인트로 재개한다 | tradingagents/graph/trading_graph.py begin_checkpoint, checkpoint_input, clear_checkpoint_on_success | 1, S1, 2 | 핵심 | [checkpoint-resume](capabilities/checkpoint-resume.md) · ready | 코드 확인(진입점·호출) |
| 14 · 판단 품질 백테스트 | 종목×날짜별 분석과 정산 결과를 집계한다. 주문 체결·잔고 시뮬레이션은 범위 밖 | cli/main.py:107-160 backtest; tradingagents/backtest.py run_backtest, summarize | 1, 2, S1, S2, 9, 12 | 핵심 | [decision-backtest](capabilities/decision-backtest.md) · ready | 코드 확인(진입점·호출) |
| 15 · CLI·보고서 표시 | 대화형/비대화형 분석과 진행 표시, Markdown·HTML 판단 근거 저장 | `cli/main.py:36-104 `analyze`; tradingagents/reporting.py:92-136 `write_report_tree`` | 2, 9~12 | 부속 | `capabilities/cli-reporting.md` · 미작성 | 코드 확인(진입점·호출) |
| 16 · ChatGPT 로그인·로그아웃 | 구독 인증 정보를 저장·갱신해 chatgpt 공급자에 전달한다 | `cli/main.py:167-194 `login`, `logout`; tradingagents/llm_clients/chatgpt_auth.py `sign_in`, `access_token`, `sign_out`` | 1 | 부속 | `capabilities/chatgpt-auth.md` · 미작성 | 코드 확인(진입점·호출) |
| 17 · CLI 선택 기억·업데이트 안내 | 이전 선택을 다음 입력 기본값으로 제시하고 릴리스·공지 캐시를 표시한다 | `cli/prefs.py:28-85 `load_last_run`, `save_last_run`; cli/updates.py:30-65 `enabled`, `read_cache`` | 1 | 부속 | `capabilities/cli-convenience.md` · 미작성 | 코드 확인(진입점·호출) |

### 공유 계약

| 계약 | 소비 행 | 근거·처음 읽을 코드 | 스펙·상태 | 검증 |
|---|---|---|---|---|
| S1 실행 상태·보고서·문맥 | 2, 4~13 | `tradingagents/agents/state.py:AgentState`, `graph/propagation.py:Propagator`, `portfolio.py:PortfolioContext` | [run-state](capabilities/run-state.md) · ready | 코드 확인 |
| S2 구조화 판단·등급 | 10~12 | `tradingagents/agents/schemas.py:PortfolioDecision`, `agents/rating.py:parse_rating`, `agents/structured.py:invoke_structured` | [decision-contract](capabilities/decision-contract.md) · ready | 코드 확인 |

벤더 구현은 행3의 패밀리로 Yahoo·Alpha Vantage·SEC EDGAR·FRED·Polymarket을 묶었다. 분석가는 입력 소스와 결과 보고서가 달라 행5~8로 나눴다.

### 대조한 범위와 미탐색 영역

- 대조: Git 추적 파일 전체 이름 → README·pyproject·LICENSE → CLI 공개 명령 `analyze/backtest/login/logout` → 분석가 TOOLS와 `ANALYST_NODE_SPECS` → 벤더 등록부 → 그래프 연결 → PM·메모리·보고서 진입점(코드 확인).
- 데이터 수집은 시장·재무·뉴스 분석가의 도구 호출과 감성 분석가의 사전 수집으로 나뉜다. 검증 스냅샷은 벤더 라우터에 등록된 도구들과 달리 Yahoo 구현을 직접 사용한다(`market_analyst.py:5-12`, `sentiment_analyst.py:63-85`, `tools.py:get_verified_market_snapshot`, 코드 확인).
- UI는 CLI 진행 표시와 저장된 Markdown/HTML 보고서 범위로만 조사했다. 브로커·주문 구현은 GUIDE 제외 범위이고, 백테스트 자체도 체결 모델을 제공하지 않는다고 명시한다(`backtest.py:9-14`, 코드 확인).
- 미탐색: 모든 LLM 공급자별 내부 처리, 벤더별 세부 캐시·재시도, 전체 테스트, CI·릴리스 자산·Docker 내부, 실제 네트워크 응답. 행3·16의 코드 확인을 모든 공급자 동작 검증으로 확대해 읽지 않는다.
- 기존 Q1~Q7 문서는 이전 SHA의 상세 분석이다. 새 feature map의 근거로 그대로 전용하지 않았다. 상세 내용의 최신 재검증은 후속 작업으로 남긴다.

## 3. 구조도와 그림 해설

[구조도 HTML](diagrams/structure.html) · [원본 JSON](diagrams/structure.json)

읽는 순서는 실행 입력 → 그래프 → 병렬 분석과 메모리 → 투자 판단 → 리스크 판단이다. 화살표는 모듈 호출·조립 의존이며, 모든 분석가 노드를 각각 그린 실행 순서도가 아니다.

| 모듈 | 역할·주고받는 것 | 근거·검증 |
|---|---|---|
| 실행 입력 | 종목·날짜·보유 JSON을 실행 요청으로 전달 | `cli/main.py:analyze`, `graph/trading_graph.py:propagate` · 코드 확인 |
| 그래프 | 초기 상태·체크포인트·모델을 준비하고 각 단계 연결 | `graph/trading_graph.py:create_run_state`, `graph/setup.py:setup_graph` · 코드 확인 |
| 병렬 분석 | 시장·재무·뉴스 도구와 소셜 사전 수집으로 보고서 작성 | `graph/setup.py:144-166`, `graph/analyst_execution.py:ANALYST_NODE_SPECS` · 코드 확인 |
| 데이터 접근 | 명시적 벤더 폴백과 날짜 제한, Yahoo 스냅샷 직접 호출 | `dataflows/router.py:route_to_vendor`, `agents/tools.py:get_verified_market_snapshot` · 코드 확인 |
| 투자 판단 | Bull/Bear → Research Manager → Trader | `graph/setup.py:168-176`, `conditional_logic.py:should_continue_debate` · 코드 확인 |
| 리스크 판단 | 3자 토론 → PM, 최종 5등급 또는 REVIEW | `graph/setup.py:177-185`, `portfolio_manager.py:78-103` · 코드 확인 |
| 메모리 | 과거 결정 정산·교훈 반환. 이번 결정은 실행 종료 후 기록 | `graph/trading_graph.py:_memory_step`, `record_decision` · 코드 확인 |

PM 판단 기준 원문: “Ground every conclusion in specific evidence from the analysts.” — “모든 결론은 분석가가 제시한 구체적 근거에 기반하라.” (`agents/managers/portfolio_manager.py:66`, 코드 확인). 구조화 등급은 `decision.rating.value`에서 가져온다. 이 코드만으로 주문 체결이나 수치 리스크 한도를 추정하지 않는다.

구조도 자동 검증: validate·deliver·check·browser-check 모두 통과. 브라우저 자동 확인을 했으며 캡처를 통한 육안 검토는 하지 않았다. 실제 서비스·모델 실행은 하지 않았다. [검증 영수증](diagrams/structure.finalize-summary.json).

## 4. 기존 질문·상세 분석

- 기존 개요와 Q1~Q7 보고서(`00-overview.md`~`05-boundary-and-fit.md`, `1394a3f` 기준)는 2026-11-03 사용자 결정으로 삭제했다. 내용은 Git 기록(`2b66149` 이전)에 남아 있다.
- [질문 검증 기록](qa.md): 이전 SHA 기준이며 새 코드에서 전부 재검증하지 않았다.

## 5. 다음 작업

[next.md](next.md). 현재 **ready 16 / draft 0 / 미작성 3(부속 행15~17)**. 기능14개+공유계약2개를 합산했다. 승인 범위의 문서·코드 참조는 재현 준비 완료이며 실제 서비스 구동·성능 검증은 수행하지 않았다.

핵심 원본 링크: [그래프 연결](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/graph/setup.py#L157-L185), [정산 진입 시점](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/memory/settlement.py#L60-L94).

## 6. 기능 스펙 통합 검토 (2026-11-02)

### 대표 흐름: 미국주식 AAPL의 과거일 분석

다음은 코드로 확인한 연결이며 실행 결과 예시가 아니다. 입력 날짜가 호스트 오늘 이하인 정규 날짜이고 필요한 외부 모델·데이터가 응답한다는 전제다.

1. [설정](capabilities/configuration.md)에서 원본 기본값 또는 호출자 설정을 읽고 quick/deep 공급자를 준비한다. [입력](capabilities/run-input.md)이 AAPL·기준일·optional 보유 객체를 받아 [S1](capabilities/run-state.md) 상태를 만든다. 보유 미제공은 빈 계좌로 추정하지 않는다(코드 확인).
2. [실행 구조](capabilities/analysis-orchestration.md)가 선택 분석가와 Memory Log를 병렬 실행한다. 시장·재무·뉴스는 도구를 호출하고 감성은 자료를 순차 사전 수집한다. 도구가 요청한 날짜는 [기준일 제한](capabilities/point-in-time.md)을 거쳐 [데이터 계층](capabilities/vendor-routing.md)에 전달된다(코드 확인).
3. 데이터 계층은 설정에 명시된 공급자만 순서대로 시도한다. 예외면 폴백하지만 과거 자료 보류문도 정상 반환이면 체인을 끝낸다. 검증 스냅샷·종목 식별·정산 종가는 Yahoo 직접 경로라는 예외가 있다(코드 확인).
4. 모든 보고서와 메모리 단계가 끝나면 [투자 판단](capabilities/investment-decision.md)의 Bull/Bear 토론→Research Manager 계획→Trader 제안이 이어진다. 등급 변환과 비중은 지시·서술이지 확정적 주문 코드가 아니다(코드 확인).
5. [리스크 판단](capabilities/risk-decision.md)이 3자 토론 후 PM 판단을 만든다. [S2](capabilities/decision-contract.md)의 typed 등급이 성공하면 그대로 쓰고 자유텍스트만 파싱한다. 판별 불가면 REVIEW, 일반 모델 호출 자체의 오류는 전파한다(코드 확인).
6. [메모리](capabilities/decision-memory.md)가 실행 JSON과 pending 결정을 기록한다. 정산은 분석일 이후 첫 완결 종가부터 기본5거래봉 뒤의 성과를 평가한다. 현재 시계로 계산한 결과라도 과거 PM에 넣는 교훈은 resolved<=기준일이어야 한다(코드 확인).
7. [체크포인트](capabilities/checkpoint-resume.md)는 활성화한 경우 같은 실행을 재개하며 기록까지 성공하면 해당 thread를 정리한다. [백테스트](capabilities/decision-backtest.md)는 이 흐름을 종목×날짜별 순차 호출하고 전용 원장으로 평가한다. REVIEW는 기록·정산될 수 있지만 성과 집계에서는 unscored다(코드 확인).

### 규칙 간 대조 결과

- 상태 소유자: 분석가별 보고서/메시지와 부모 상태의 경계는 S1·행9, 판단 스키마·파서는 S2, 계좌 입력·정규화는 행2로 모았다. 공백 보고서/상대 발언 helper는 행10이 소유하고 행11이 참조한다(코드 확인).
- 선행 보정: 데이터 수집은 설정·정규화·날짜 유틸, 분석가는 실행 구조·입력 문맥, 메모리는 종목 정규화 계약을 추가 선행으로 연결했다. 단순 런타임 호출은 입출력/오류 경계로 정의하여 depends 순환을 피했다(분석 설계).
- 단위: raw/alpha는 계산 중 비율, 원장에는 소수점 한 자리 백분율로 저장된다. PM/Trader optional 가격은 호가 통화 절대값이라는 지시이고 하드 가격·비중 검증이 아니다(코드 확인).
- 스펙 범위는 원본이다. 국장 API·DART·수급·국내 커뮤니티 대체는 각 적용 메모의 분석자 의견으로 남겼으며 구현하지 않았다. 미국주식 수집·판단 경로를 제거하지 않았다.

### 호출 비용의 코드 기반 근사

fresh 실행에서 분석가별 tool-call 메시지 수를 t_i, 선택된 tool 분석가 집합을 A, 감성 선택 여부를 S(0/1), 투자/리스크 라운드를 R/Q, 정산 교훈 호출 수를 L이라 하면 모델 invoke 수는 `Σ(i∈A)(t_i+1)+S+max(1,2R)+max(1,3Q)+3+L`이다(코드 확인으로 도출한 근사). 마지막3은 RM·Trader·PM이며 structured→일반 폴백마다1회 추가, SDK 재시도와 게시물별 선택적 Jev HTTP 요청은 별도다. 기본 분석가4명·R=Q=1·교훈0이면 도구 호출0회 기준12회, tool 분석가3명이20라운드를 모두 소진하면72회다. 실제 모델 출력에 따라 달라지며 비용 금액은 측정하지 않았다. 근거: 행9 C-02·C-03, 행10 C-04~C-07, 행11 C-04·C-05, 행12 C-11.

### 검증 한계

문서 정합·SHA·링크·상태·코드 범위·선행 순환을 검사한다. 외부 SDK/서비스는 원본이 호출하는 인터페이스 경계로 명시했으며 설치·원본 실행·실제 API 응답·모델 성능·주문 연계는 검증하지 않았다. ready는 이 선언 범위의 동작·참조가 해소됐다는 뜻이다.

문서 정합 검사 결과: `python3 scripts/check.py TradingAgents` → ERROR 0 / NOTE 0. [스펙 감사 기록](../../artifacts/TradingAgents/spec-audit.json): 16개 스펙·152개 인용 범위의 경계, sources 존재, depends 존재·비순환 확인. 범위 의미는 자동 검사와 별도로 직접 열람·교차검토했다.
