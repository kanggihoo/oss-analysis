---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/agents/state.py
  - tradingagents/graph/propagation.py
depends: []
status: ready
---

# S1 실행 상태·보고서·문맥

> 종목 분석 1회의 상태 필드와 초기값, 단계 사이에 주고받는 보고서·토론 기록을 정의한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 호출자가 종목, 기준일, 자산 유형, 종목 설명·보유 현황 텍스트를 제공한다.
2. 초기화는 매 호출마다 새 map과 토론 map을 만든다.
3. 분석가는 자기 보고서를, 토론 단계는 해당 토론 map을 갱신한다.
4. 매니저·트레이더가 계획·최종 결과를 추가한다.
5. 메시지 누적 정책은 MessagesState를 제공하는 LangGraph에 위임한다.

### 1.2 범위·통합 지점

- 제공: 공통 상태 필드·초기화·그래프 호출 인자.
- 제외: 종목 조회·포트폴리오 렌더링은 [입력](run-input.md), 구조화 결과는 [S2](decision-contract.md), 상태 저장·체크포인트는 각 기능 소유.
- 외부 경계: LangGraph MessagesState는 messages를 관리한다. 이 문서는 라이브러리 reducer 구현을 복제하지 않는다.
- 소유 상태·부작용: 초기 map은 실행 단위이며 파일·네트워크 I/O 없음. TypedDict 선언은 런타임 검증기가 아니다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| create_initial_state | company_name:string, trade_date:any→string, asset_type:string="stock", past_context/instrument_context/portfolio_context:string="" → map | 날짜 유효성은 호출자 입력 기능 소유. ticker 정규화하지 않음 |
| 보고서 | market_report, sentiment_report, news_report, fundamentals_report:string | 초기 빈 문자열; 미선택/빈 응답을 정상 분석 결과로 추정하면 안 됨 |
| 문맥 | company_of_interest, trade_date, asset_type, instrument_context, portfolio_context, past_context, memory_note | 초기 memory_note=""; 나머지는 전달값. 보유 문맥 빈 문자열은 미제공 |
| 토론 상태 | investment_debate_state, risk_debate_state:map | 필드 전체와 초기값은 C-01·C-02; count는 각 발언 누적 수이며 라운드 수와 다름 |
| 후속 필드 | investment_plan, trader_investment_plan, final_trade_decision, final_rating:string | 타입 선언에는 있지만 초기화 map에는 없음. 소비 전 생산 단계 필요 |
| get_graph_args | callbacks:optional list → map | stream_mode="values"; config.recursion_limit=생성자 max_recur_limit(기본100), truthy callbacks만 config에 포함 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 새 실행 상태 생성 | company_of_interest와 messages의 첫 human 내용에 동일 원본 company_name 사용. trade_date는 str 변환만 한다. | 코드 확인 |
| R-02 | 보고서·토론 초기값 | C-02대로 네 보고서는 빈 문자열, 토론 모든 텍스트는 빈 문자열, count=0. 계획·최종 결과 키는 아직 만들지 않는다. | 코드 확인 |
| R-03 | 메모리·문맥 전달 | past_context/instrument_context/portfolio_context를 가공 없이 넣고 memory_note만 빈 값으로 초기화한다. | 코드 확인 |
| R-04 | 타입·호출 인자 | C-01의 선언이 상태 교환 계약. 초기화는 입력 형식·필수키를 별도 검증하지 않고 그래프 호출 인자는 C-03을 따른다. | 코드 확인 |

- 미결정: 없음(선언한 범위의 원본 경계).
- 확인 한계: 외부 API·모델·LangGraph를 실행하지 않았다. 아래 사례는 구현에서 도출했으며 테스트 실행 결과가 아니다.

### 1.5 필수 코드 참조

기준은 frontmatter의 SHA이며 원본 레포 루트 상대 경로다. C-ID가 지시하는 표·포맷·분기·알고리즘은 해당 범위를 함께 읽는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/agents/state.py:8-73` · `InvestDebateState`, `RiskDebateState`, `AgentState` | 모든 상태 필드와 중립 타입 대응; messages는 MessagesState 경계 | R-02, R-03, R-04 |
| C-02 | `tradingagents/graph/propagation.py:13-65` · `create_initial_state` | 독립 map 생성·초기값 전부; 내부 TypedDict는 C-01 | R-01, R-02, R-03 |
| C-03 | `tradingagents/graph/propagation.py:9-11,67-80` · `Propagator`, `get_graph_args` | 재귀 한도·callbacks·stream_mode | R-04 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 외부 모델·SDK·네트워크는 정상/오류를 반환하는 대체물로 가정하며 실제 서비스 호환성을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-02 | company_name=AAPL, date=2026-10-26, 선택 분석가와 무관하게 초기화 | messages=[human AAPL], 네 보고서="", 두 count=0, final_rating 키 없음 |
| T-02 | R-02 | 두 번 초기화한 뒤 첫 실행 debate.count 갱신 | 두 번째 실행 count=0 유지 |
| T-03 | R-03 | portfolio_context 생략 | 빈 문자열이며 현금0/보유0으로 바꾸지 않음 |
| T-04 | R-04 | max_recur_limit=100, callbacks=[] | values 모드와 recursion_limit=100, callbacks 키 생략 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-02, R-03, R-04 | C-01 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-01, R-02, R-03 | C-02 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-04 | C-03 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
