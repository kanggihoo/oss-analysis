---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/agents/researchers/bull_researcher.py
  - tradingagents/agents/researchers/bear_researcher.py
  - tradingagents/agents/managers/research_manager.py
  - tradingagents/agents/trader/trader.py
  - tradingagents/agents/context.py
  - tradingagents/graph/conditional_logic.py
  - tradingagents/graph/setup.py
depends:
  - run-state.md
  - configuration.md
  - run-input.md
  - decision-contract.md
status: ready
---

# 투자 토론·계획·트레이더 제안

> 선택 분석가의 보고서를 Bull/Bear 토론과 매니저 계획으로 종합하고 트레이더 제안으로 변환한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 보고서가 합류하면 Bull이 먼저 발언한다.
2. Bull/Bear가 최신 상대 발언과 누적 이력을 읽고 번갈아 논거를 추가한다.
3. 발언 수가 종료 기준에 도달하면 Research Manager가 이력으로 투자 계획을 만든다.
4. Trader가 계획·선택적 시장 보고서·보유 문맥으로 Buy/Hold/Sell 제안을 만든다.
5. 제안을 메시지와 trader_investment_plan으로 반환하고 리스크 토론으로 전달한다.

### 1.2 범위·통합 지점

- 제공: 토론·투자 계획·트레이더 제안.
- 제외: 최종 등급은 리스크 판단, 입력 보고서 품질은 각 분석가 소관. 주문·잔고 갱신 없음.
- 선행: 공유 실행 상태·설정·구조화 판단 계약. 분석 보고서의 내용은 실행 상태의 문자열로 받으며 모든 분석가의 구현을 의존하지 않는다.
- 상태: investment_debate_state와 investment_plan, trader_investment_plan 및 Trader 메시지.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 투자 토론 | 4개 report string + debate map → 갱신 debate map | bull_history, bear_history, history, current_response, count |
| Research Manager | debate history + 종목 문맥 → investment_plan string | deep 모델. 보유 현황·과거 교훈을 직접 읽지 않는다 |
| Trader | investment_plan + optional market_report + portfolio_context → string | quick 모델. 출력 스키마/문자열 렌더링은 S2 |
| max_debate_rounds | 정수 설정 | 기본1. 전체 발언 count를 2×라운드 수와 비교한다 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 토론 시작·상대 발언/보고서 공백 | 공백 상대는 아직 발언하지 않았다는 표식, 공백 보고서는 unavailable 표식으로 치환한다. 빈 문자열을 실제 중립 의견으로 취급하지 않는다. 동작은 C-03. | 코드 확인 |
| R-02 | Bull 또는 Bear 발언 | 각각 성장·경쟁우위·긍정 지표 또는 리스크·경쟁약점·부정 지표를 중심으로 반박하도록 지시한다. 한 번의 quick invoke 뒤 역할 접두사를 붙여 자신의 history와 전체 history에 추가, count+1, current_response를 교체하고 상대 history는 보존한다. | 코드 확인 |
| R-03 | 발언 완료 | count≥2×max_debate_rounds면 Research Manager로, 아니면 current_response가 Bull로 시작하면 Bear, 나머지는 Bull. 첫 Bull 실행 뒤 검사하므로 라운드가 0이어도 Bull 한 번은 실행한다. | 코드 확인 |
| R-04 | Research Manager | deep 모델이 debate history·종목 문맥으로 5등급 recommendation/rationale/strategic_actions를 생성한다. 논쟁 존재만으로 Hold를 택하지 말고 증거가 비슷하거나 부족할 때 Hold라는 지시. 과거 토론 이력·count는 유지, current_response는 계획으로 교체한다. | 코드 확인 |
| R-05 | Trader | 시장 보고서가 공백이면 기술적 수치 근거 섹션을 넣지 않는다. 계획·종목·보유 문맥을 넣고 절대 가격의 entry/stop을 지시한다. Overweight→Buy·Underweight→Sell은 프롬프트 지시이고 코드 강제 변환은 아니다. | 코드 확인 |
| R-06 | 구조화 생성 실패 | S2의 bind/invoke fallback으로 한 번 자유텍스트 생성한다. 자유텍스트마저 실패하면 전파한다. 토론자 invoke는 별도 catch가 없다. 등급 일치·수량·한도를 검증해 덮어쓰지 않는다. | 코드 확인 |
| R-07 | Trader 반환 | 제안 문자열을 trader_investment_plan과 새 AIMessage 양쪽에 넣는다. 필수 가격·비중 숫자를 만들어 채우거나 현금·보유 수량을 갱신하지 않는다. | 코드 확인 |

- 미결정: 없음. 선행 스펙을 대조했고 선언한 범위의 원본 경계는 정해져 있다.
- 확인 한계: 설치·실행 및 실제 모델·외부 API 응답 검증은 하지 않았다. 프롬프트 지시가 모델 응답에 항상 지켜진다는 보장은 없다.

### 1.5 필수 코드 참조

기준은 frontmatter SHA이며 경로는 원본 레포 상대 경로다. 호출한 공통 helper는 위 선행 계약에서 정의한다.
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/agents/researchers/bull_researcher.py:9-65 create_bull_researcher` | Bull 전체 노드·프롬프트·상태 변경 | R-01, R-02 |
| C-02 | `tradingagents/agents/researchers/bear_researcher.py:9-67 create_bear_researcher` | Bear 전체 노드·프롬프트·상태 변경 | R-01, R-02 |
| C-03 | `tradingagents/agents/context.py:37-48 opponent_argument_or_opening; tradingagents/agents/context.py:190-201 report_or_absent` | 공백·누락 표식의 순수 변환 | R-01 |
| C-04 | `tradingagents/graph/conditional_logic.py:12-21 should_continue_debate; tradingagents/graph/setup.py:164-176 setup_graph` | 시작 노드·토론 종료·RM→Trader | R-03 |
| C-05 | `tradingagents/agents/managers/research_manager.py:14-74 create_research_manager` | RM 프롬프트·호출·부분 상태 반환 | R-04, R-06 |
| C-06 | `tradingagents/agents/trader/trader.py:20-98 create_trader` | Trader 조건부 시장 자료 삽입·프롬프트·반환 | R-05, R-06, R-07 |
| C-07 | `tradingagents/graph/setup.py:132-140 setup_graph` | 토론자·Trader quick, RM·PM deep 모델 조립 | R-02, R-04 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 모델·네트워크를 대체 응답으로 바꿔 분기를 검증하는 사례이며 모델 품질이나 실제 제공자 가용성을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | Bull 시작, 상대 발언과 sentiment_report 공백 | 아직 발언하지 않았음·보고서 없음 표식 포함 |
| T-02 | R-03 | 기본 라운드1, count0부터 실행 | Bull(count1)→Bear(count2)→RM→Trader |
| T-03 | R-05 | market_report 공백·portfolio_context 미제공 | 기술적 섹션 생략, 보유현황을 모른다는 안내 포함 |
| T-04 | R-05 | RM Overweight, Trader 대체모델 Sell 반환 | 코드가 Buy로 강제 수정하지 않는다 |
| T-05 | R-06 | 구조화 호출 실패 후 자유텍스트 invoke도 예외 | 예외 전파, Hold 제안으로 대체하지 않는다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, R-02 | C-01 | 원본 코드 직접 열람, 실행하지 않음 |
| R-01, R-02 | C-02 | 원본 코드 직접 열람, 실행하지 않음 |
| R-01 | C-03 | 원본 코드 직접 열람, 실행하지 않음 |
| R-03 | C-04 | 원본 코드 직접 열람, 실행하지 않음 |
| R-04, R-06 | C-05 | 원본 코드 직접 열람, 실행하지 않음 |
| R-05, R-06, R-07 | C-06 | 원본 코드 직접 열람, 실행하지 않음 |

모델 계층은 C-07에서 확인했다.

T-ID의 기대 결과는 해당 R-ID 및 C-ID의 분기에서 도출했다. 테스트는 이름 검색까지만 참고했으며 수락 사례의 출처로 삼지 않았다.

판단 기준 원문(R-04): “conflict alone is not a reason to Hold.”

번역: “의견 충돌 자체는 Hold를 선택할 이유가 아니다.” 매니저 프롬프트의 판단 지침이며 결정적 수치 공식이 아니다.

[핵심 원본](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/agents/researchers/bull_researcher.py#L9-L65).

## 적용 메모

분석자 의견: 미국 종목에도 현재 원본 흐름을 그대로 사용한다. 국장용 수량·비중·주문 한도를 도입하려면 이 자연어 제안 뒤에 별도의 결정적 주문 계약이 필요하다.
